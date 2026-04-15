#!/usr/bin/env python3
"""
global_baseline_parser.py — Phase 3 of the Set Grading System.

Streams a massive JSON file (up to 140 GB) of global Slippi match data using
ijson to avoid loading the entire file into memory. Extracts per-game stats,
computes percentile distributions grouped by both player character AND
opponent character, and overwrites scripts/grade_baselines.json with
globally-accurate data.

CRITICAL: Do NOT use json.load() on this file — it will OOM. This script
uses ijson for streaming, processing one game record at a time.

Output schema matches fetch_slippilab_replays.py exactly so the resulting
grade_baselines.json is a drop-in replacement that grade-benchmarks.ts
consumes without any code changes.

== Supported JSON formats ==

  1. JSON array of objects (most common large dump format):
       [{"player_character": "Fox", "opponent_character": "Falco",
         "neutral_win_ratio": 0.54, ...}, ...]
     → Use: --format array   (uses ijson path 'item')

  2. Newline-delimited JSON / NDJSON (one JSON object per line):
       {"player_character": "Fox", "opponent_character": "Falco", ...}
       {"player_character": "Marth", ...}
     → Use: --format ndjson

  3. Nested JSON object with a top-level key holding the array:
       {"games": [...], "metadata": {...}}
     → Use: --format nested --array-key games   (ijson path 'games.item')

The script auto-detects NDJSON vs array by peeking at the first byte.

== Expected fields per game record ==
  player_character    (str)    — character used by the player (for by_player_char grouping)
  opponent_character  (str)    — opposing character (for by_opponent_char grouping)
  neutral_win_ratio   (float)  0–1
  openings_per_kill   (float)  typically 1–10
  damage_per_opening  (float)  typically 5–60
  l_cancel_ratio      (float)  0–1
  avg_kill_percent    (float)  typically 40–200
  avg_death_percent   (float)  typically 40–200

Field names can be remapped via --player-char-field / --opponent-char-field.
Records missing a character field go into an "_unknown" bucket and are
excluded from the final output.

** DO NOT EXECUTE until the global JSON's format is confirmed. **

Usage:
    python global_baseline_parser.py \\
        --input /path/to/global_data.json \\
        --output scripts/grade_baselines.json \\
        [--format array|ndjson|nested|auto] \\
        [--array-key games] \\
        [--progress-every 100000]
"""

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np

try:
    import ijson
except ImportError:
    print("ERROR: ijson is not installed. Run: pip install ijson", file=sys.stderr)
    sys.exit(1)

# ── Constants ──────────────────────────────────────────────────────────────

# Must match STAT_KEYS in fetch_slippilab_replays.py so the two pipelines
# produce drop-in compatible output.
STAT_KEYS = [
    "neutral_win_ratio",
    "openings_per_kill",
    "damage_per_opening",
    "l_cancel_ratio",
    "avg_kill_percent",
    "avg_death_percent",
]

# ── Percentile helpers ─────────────────────────────────────────────────────

def compute_percentiles(values: list) -> dict:
    """Return avg + P5/P10/P25/P50/P75/P90/P95 for a list of floats.

    Both tails are computed so that inverted stats (openings_per_kill,
    avg_kill_percent) can be graded against their low-end percentiles.
    """
    if not values:
        return {"sample_size": 0, "avg": None,
                "p5": None, "p10": None, "p25": None, "p50": None,
                "p75": None, "p90": None, "p95": None}
    arr = np.array(values, dtype=float)
    pcts = np.percentile(arr, [5, 10, 25, 50, 75, 90, 95])
    return {
        "sample_size": len(values),
        "avg":  round(float(np.mean(arr)), 4),
        "p5":   round(float(pcts[0]),      4),
        "p10":  round(float(pcts[1]),      4),
        "p25":  round(float(pcts[2]),      4),
        "p50":  round(float(pcts[3]),      4),
        "p75":  round(float(pcts[4]),      4),
        "p90":  round(float(pcts[5]),      4),
        "p95":  round(float(pcts[6]),      4),
    }

# ── Streaming helpers ──────────────────────────────────────────────────────

def stream_array(f, array_key=None):
    """
    Stream records from a JSON array using ijson (constant memory).
    array_key=None  → root-level array (ijson path 'item')
    array_key='foo' → nested array at obj['foo'] (ijson path 'foo.item')
    """
    path = f"{array_key}.item" if array_key else "item"
    yield from ijson.items(f, path)


def stream_ndjson(f):
    """Stream records from a newline-delimited JSON file."""
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError as e:
            print(f"  [WARN] Skipping malformed line: {e}", file=sys.stderr)


def detect_format(input_path: str) -> str:
    """Peek at the first non-whitespace byte to guess JSON format."""
    with open(input_path, "rb") as f:
        # Skip leading whitespace
        while True:
            b = f.read(1)
            if not b or b not in b" \t\r\n":
                break
    if b == b"[":
        return "array"
    if b == b"{":
        return "ndjson"
    return "array"  # default

# ── Validation ─────────────────────────────────────────────────────────────

def is_valid_value(key: str, val) -> bool:
    """Sanity-check a stat value before including it."""
    if not isinstance(val, (int, float)):
        return False
    if val != val:  # NaN check
        return False
    if key in ("neutral_win_ratio", "l_cancel_ratio"):
        return 0.0 <= val <= 1.0
    if key == "openings_per_kill":
        return 0.0 < val < 100.0
    if key == "damage_per_opening":
        return 0.0 < val < 1000.0
    if key in ("avg_kill_percent", "avg_death_percent"):
        return 0.0 < val < 1000.0
    return True

# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Stream a massive Slippi JSON file and generate grade baselines"
    )
    parser.add_argument("--input", required=True,
                        help="Path to the global JSON file (up to 140 GB)")
    parser.add_argument("--output", default=os.path.join(os.path.dirname(__file__), "grade_baselines.json"),
                        help="Output path (default: scripts/grade_baselines.json)")
    parser.add_argument("--format", choices=["array", "ndjson", "nested", "auto"], default="auto",
                        help="JSON format (default: auto-detect)")
    parser.add_argument("--array-key", default=None,
                        help="For --format nested: the key holding the games array (e.g. 'games')")
    parser.add_argument("--progress-every", type=int, default=100_000,
                        help="Print a progress line every N records (default: 100000)")
    parser.add_argument("--player-char-field", default="player_character",
                        help="JSON field for player character (default: 'player_character')")
    parser.add_argument("--opponent-char-field", default="opponent_character",
                        help="JSON field for opponent character (default: 'opponent_character')")
    args = parser.parse_args()

    input_path = os.path.expanduser(args.input)
    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    file_size_gb = os.path.getsize(input_path) / (1024 ** 3)
    print(f"Input file: {input_path}")
    print(f"File size:  {file_size_gb:.1f} GB")

    fmt = args.format
    if fmt == "auto":
        fmt = detect_format(input_path)
        print(f"Auto-detected format: {fmt}")

    # Dual grouping — same structure as fetch_slippilab_replays.py.
    by_player_char:   dict = defaultdict(lambda: defaultdict(list))
    by_opponent_char: dict = defaultdict(lambda: defaultdict(list))
    overall:          dict = defaultdict(list)

    total_records = 0
    skipped       = 0

    print(f"\nStreaming records (progress every {args.progress_every:,})...")

    # ijson wants binary for array/nested; NDJSON reads text.
    if fmt == "ndjson":
        f = open(input_path, "r", encoding="utf-8", errors="replace")
        records = stream_ndjson(f)
    elif fmt == "nested":
        f = open(input_path, "rb")
        records = stream_array(f, array_key=args.array_key)
    else:  # array
        f = open(input_path, "rb")
        records = stream_array(f, array_key=None)

    try:
        for record in records:
            total_records += 1

            if total_records % args.progress_every == 0:
                print(f"  Processed {total_records:>12,} | "
                      f"Skipped: {skipped:,} | "
                      f"Players: {len(by_player_char)}  Opponents: {len(by_opponent_char)}",
                      flush=True)

            player_char = record.get(args.player_char_field)
            opp_char    = record.get(args.opponent_char_field)

            # At least one grouping field must be present and be a non-empty string.
            if not isinstance(player_char, str) or not player_char:
                player_char = None
            if not isinstance(opp_char, str) or not opp_char:
                opp_char = None
            if player_char is None and opp_char is None:
                skipped += 1
                continue

            added_any = False
            for key in STAT_KEYS:
                val = record.get(key)
                if val is None or not is_valid_value(key, val):
                    continue
                if player_char is not None:
                    by_player_char[player_char][key].append(float(val))
                if opp_char is not None:
                    by_opponent_char[opp_char][key].append(float(val))
                overall[key].append(float(val))
                added_any = True

            if not added_any:
                skipped += 1
    finally:
        f.close()

    valid = total_records - skipped
    print(f"\nStreaming complete.")
    print(f"  Total records:     {total_records:,}")
    print(f"  Skipped:           {skipped:,}")
    print(f"  Valid records:     {valid:,}")
    print(f"  Player chars:      {len(by_player_char)}")
    print(f"  Opponent chars:    {len(by_opponent_char)}")

    def build_char_section(accum: dict) -> dict:
        section = {}
        for char_name in sorted(accum.keys()):
            char_data = accum[char_name]
            n = max((len(char_data[k]) for k in STAT_KEYS if char_data[k]), default=0)
            section[char_name] = {"sample_size": n}
            for key in STAT_KEYS:
                section[char_name][key] = compute_percentiles(char_data[key])
        return section

    overall_entry = {"sample_size": valid}
    for key in STAT_KEYS:
        overall_entry[key] = compute_percentiles(overall[key])

    output = {
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "source":           "global",
        "replay_count":     valid,
        "by_player_char":   build_char_section(by_player_char),
        "by_opponent_char": build_char_section(by_opponent_char),
    }
    output["by_player_char"]["_overall"]   = overall_entry
    output["by_opponent_char"]["_overall"] = overall_entry

    with open(args.output, "w", encoding="utf-8") as f_out:
        json.dump(output, f_out, indent=2)

    player_chars   = sorted(k for k in output["by_player_char"]   if k != "_overall")
    opponent_chars = sorted(k for k in output["by_opponent_char"] if k != "_overall")
    print(f"\nBaselines written to: {args.output}")
    print(f"Player chars  ({len(player_chars)}):   {player_chars}")
    print(f"Opponent chars ({len(opponent_chars)}): {opponent_chars}")


if __name__ == "__main__":
    main()
