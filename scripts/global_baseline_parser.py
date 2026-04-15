#!/usr/bin/env python3
"""
global_baseline_parser.py — Phase 3 of the Set Grading System.

Streams a massive JSON file (up to 140 GB) of global Slippi match data using
ijson to avoid loading the entire file into memory. Extracts per-game stats
grouped by opponent character, computes new percentile distributions, and
overwrites grade_baselines.json with globally-accurate data.

CRITICAL: Do NOT use json.load() on this file — it will cause an OOM crash.
This script uses ijson for streaming, processing one game record at a time.

== Supported JSON formats ==

  1. JSON array of objects (most common large dump format):
       [{"opponent_character": "Falco", "neutral_win_ratio": 0.54, ...}, ...]
     → Use: --format array   (uses ijson path 'item')

  2. Newline-delimited JSON / NDJSON (one JSON object per line):
       {"opponent_character": "Falco", "neutral_win_ratio": 0.54, ...}
       {"opponent_character": "Fox", ...}
     → Use: --format ndjson

  3. Nested JSON object with a top-level "games" key:
       {"games": [...], "metadata": {...}}
     → Use: --format nested --array-key games   (uses ijson path 'games.item')

The script will auto-detect NDJSON if the file starts with '{' instead of '['.

== Expected fields per game record ==
  opponent_character  (string, e.g. "Falco") — REQUIRED for grouping
  neutral_win_ratio   (float, 0–1)
  openings_per_kill   (float, typically 1–10)
  damage_per_opening  (float, typically 5–50)
  l_cancel_ratio      (float, 0–1)
  total_damage        (float)

Missing fields are skipped gracefully; records missing opponent_character go
into an "_unknown" bucket that is excluded from the final output.

DO NOT EXECUTE THIS SCRIPT until Phase 2 is complete and you have confirmed
the format of your global JSON file.

Usage:
    python global_baseline_parser.py \\
        --input /path/to/global_data.json \\
        --output scripts/grade_baselines.json \\
        [--format array|ndjson|nested] \\
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

STAT_KEYS = [
    "neutral_win_ratio",
    "openings_per_kill",
    "damage_per_opening",
    "l_cancel_ratio",
    "total_damage",
]

# ── Percentile helpers ─────────────────────────────────────────────────────

def compute_percentiles(values: list[float]) -> dict:
    """Return avg + P5/P10/P25/P50/P75/P90/P95 for a list of floats.

    Both tails are computed so that inverted stats (lower = better) can be
    graded correctly using the low-end percentiles.
    """
    if not values:
        return {
            "sample_size": 0,
            "avg": None,
            "p5": None, "p10": None, "p25": None,
            "p50": None,
            "p75": None, "p90": None, "p95": None,
        }
    arr = np.array(values, dtype=float)
    pcts = np.percentile(arr, [5, 10, 25, 50, 75, 90, 95])
    return {
        "sample_size": len(values),
        "avg":  round(float(np.mean(arr)),  4),
        "p5":   round(float(pcts[0]),       4),
        "p10":  round(float(pcts[1]),       4),
        "p25":  round(float(pcts[2]),       4),
        "p50":  round(float(pcts[3]),       4),
        "p75":  round(float(pcts[4]),       4),
        "p90":  round(float(pcts[5]),       4),
        "p95":  round(float(pcts[6]),       4),
    }

# ── Streaming helpers ──────────────────────────────────────────────────────

def stream_array(f, array_key=None):
    """
    Stream game records from a JSON array using ijson.
    array_key=None  → root-level array (ijson path 'item')
    array_key='foo' → nested array at obj['foo'] (ijson path 'foo.item')
    """
    path = f"{array_key}.item" if array_key else "item"
    for record in ijson.items(f, path):
        yield record


def stream_ndjson(f):
    """Stream game records from a newline-delimited JSON file."""
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError as e:
            print(f"  [WARN] Skipping malformed line: {e}", file=sys.stderr)


def detect_format(input_path: str) -> str:
    """Peek at the first byte to guess JSON format."""
    with open(input_path, "rb") as f:
        first = f.read(1)
    if first == b"[":
        return "array"
    elif first == b"{":
        return "ndjson"
    else:
        return "array"  # default guess

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
    if key in ("damage_per_opening", "total_damage"):
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
                        help="JSON format: array (default), ndjson, nested, or auto-detect")
    parser.add_argument("--array-key", default=None,
                        help="For --format nested: the key containing the games array (e.g. 'games')")
    parser.add_argument("--progress-every", type=int, default=100_000,
                        help="Print a progress line every N records (default: 100000)")
    parser.add_argument("--char-field", default="opponent_character",
                        help="JSON field name for opponent character (default: 'opponent_character')")
    args = parser.parse_args()

    input_path = os.path.expanduser(args.input)
    if not os.path.exists(input_path):
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    file_size_gb = os.path.getsize(input_path) / (1024 ** 3)
    print(f"Input file: {input_path}")
    print(f"File size:  {file_size_gb:.1f} GB")

    # Auto-detect format
    fmt = args.format
    if fmt == "auto":
        fmt = detect_format(input_path)
        print(f"Auto-detected format: {fmt}")

    # Accumulators
    by_char: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    overall: dict[str, list[float]] = defaultdict(list)
    total_records = 0
    skipped = 0

    print(f"\nStreaming records (progress every {args.progress_every:,})...")

    with open(input_path, "rb") as f:
        if fmt == "ndjson":
            # py-slippi uses text mode for NDJSON; re-open in text mode
            f.close()
            f = open(input_path, "r", encoding="utf-8", errors="replace")
            records = stream_ndjson(f)
        elif fmt == "nested":
            records = stream_array(f, array_key=args.array_key)
        else:  # array
            records = stream_array(f, array_key=None)

        for record in records:
            total_records += 1

            if total_records % args.progress_every == 0:
                print(f"  Processed {total_records:>10,} records | "
                      f"Skipped: {skipped:,} | "
                      f"Characters: {len(by_char)}")

            char_name = record.get(args.char_field)
            if not char_name or not isinstance(char_name, str):
                skipped += 1
                continue

            added_any = False
            for key in STAT_KEYS:
                val = record.get(key)
                if val is not None and is_valid_value(key, val):
                    by_char[char_name][key].append(float(val))
                    overall[key].append(float(val))
                    added_any = True

            if not added_any:
                skipped += 1

    print(f"\nStreaming complete.")
    print(f"  Total records read:  {total_records:,}")
    print(f"  Skipped (no data):   {skipped:,}")
    print(f"  Valid records:       {total_records - skipped:,}")
    print(f"  Unique characters:   {len(by_char)}")

    # Build output
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "global",
        "sample_size": total_records - skipped,
        "by_character": {},
    }

    for char_name in sorted(by_char.keys()):
        char_data = by_char[char_name]
        n = max((len(char_data[k]) for k in STAT_KEYS if char_data[k]), default=0)
        output["by_character"][char_name] = {"sample_size": n}
        for key in STAT_KEYS:
            output["by_character"][char_name][key] = compute_percentiles(char_data[key])

    # Overall fallback
    overall_n = total_records - skipped
    output["by_character"]["_overall"] = {"sample_size": overall_n}
    for key in STAT_KEYS:
        output["by_character"]["_overall"][key] = compute_percentiles(overall[key])

    with open(args.output, "w", encoding="utf-8") as f_out:
        json.dump(output, f_out, indent=2)

    print(f"\nBaselines written to: {args.output}")
    print(f"Characters in output: {sorted(k for k in output['by_character'] if k != '_overall')}")


if __name__ == "__main__":
    main()
