#!/usr/bin/env python3
"""
regen_benchmarks.py — Regenerate src/lib/grade-benchmarks.ts from the
current scripts/grade_baselines.json.

Reads the by_player_char section, emits one BENCHMARKS entry per character
with sample_size >= MIN_SAMPLES, plus an _overall fallback. Skips
"Unknown_*" buckets (parser couldn't map the internal char ID).

inputs_per_minute is carried forward as a placeholder — py-slippi's frame
API doesn't surface pre-frame button bytes, so the Python pipeline can't
compute it. The in-app TS parser computes IPM live; baseline TBD.

Usage:
    python3 scripts/regen_benchmarks.py
"""

import json
import os
import sys

REPO_ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_PATH    = os.path.join(REPO_ROOT, "scripts", "grade_baselines.json")
OUTPUT_PATH   = os.path.join(REPO_ROOT, "src", "lib", "grade-benchmarks.ts")
MIN_SAMPLES   = 20

STAT_KEYS = [
    "neutral_win_ratio",
    "openings_per_kill",
    "damage_per_opening",
    "avg_kill_percent",
    "avg_death_percent",
    "l_cancel_ratio",
]

# IPM placeholder — kept in sync with grade-benchmarks.ts header notes.
IPM_PLACEHOLDER = (
    "{ p5: 90, p10: 130, p25: 185, p50: 260, p75: 340, p90: 410, p95: 460 }"
)


def fmt_thresholds(t: dict) -> str:
    """{ p5: X, p10: X, p25: X, p50: X, p75: X, p90: X, p95: X }"""
    parts = [f"p{n}: {round(t[f'p{n}'], 4)}" for n in (5, 10, 25, 50, 75, 90, 95)]
    return "{ " + ", ".join(parts) + " }"


def emit_char_entry(name: str, data: dict, *, indent: int = 2) -> str:
    pad  = " " * indent
    pad2 = " " * (indent + 2)
    key  = json.dumps(name)  # safe quoting for any char name
    lines = [f"{pad}{key}: {{"]
    for stat in STAT_KEYS:
        thr = data[stat]
        line = f"{pad2}{stat:18s}:  {fmt_thresholds(thr)},"
        lines.append(line)
    lines.append(f"{pad2}{'inputs_per_minute':18s}:  {IPM_PLACEHOLDER},")
    lines.append(f"{pad}}},")
    return "\n".join(lines)


HEADER = '''/**
 * grade-benchmarks.ts — Stat percentile thresholds for the Set Grading System.
 *
 * !! DEV ONLY — not shipped to users yet !!
 *
 * Generated from scripts/grade_baselines.json via scripts/regen_benchmarks.py.
 * Characters with fewer than {min_samples} samples in the source dataset fall back to _overall.
 * inputs_per_minute is a placeholder — py-slippi's frame API doesn't expose pre-frame
 * button states, so the Python pipeline can't compute it; the in-app parser computes
 * it live but we have no community baseline for it yet.
 */

export interface StatThresholds {{
  p5:  number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  p95: number;
}}

export interface CharacterBenchmarks {{
  neutral_win_ratio:  StatThresholds;
  openings_per_kill:  StatThresholds;  // inverted: lower = better
  damage_per_opening: StatThresholds;
  avg_kill_percent:   StatThresholds;  // inverted: lower = better (killing early)
  avg_death_percent:  StatThresholds;
  l_cancel_ratio:     StatThresholds;
  inputs_per_minute:  StatThresholds;
}}

export const BENCHMARKS: Record<string, CharacterBenchmarks> = {{
'''


def main():
    if not os.path.exists(INPUT_PATH):
        print(f"ERROR: {INPUT_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    by_player = data.get("by_player_char", {})
    if "_overall" not in by_player:
        print("ERROR: _overall bucket missing from grade_baselines.json", file=sys.stderr)
        sys.exit(1)

    overall_n = by_player["_overall"].get("sample_size", 0)
    print(f"Source: {data.get('source', '?')} · {data.get('replay_count', 0)} replays")
    print(f"Overall sample_size: {overall_n}")

    eligible = []
    excluded = []
    for name in sorted(k for k in by_player if k != "_overall"):
        n = by_player[name].get("sample_size", 0)
        if name.startswith("Unknown_"):
            excluded.append((name, n, "unmapped char id"))
            continue
        if n < MIN_SAMPLES:
            excluded.append((name, n, f"< {MIN_SAMPLES}"))
            continue
        eligible.append((name, n))

    parts = [HEADER.format(min_samples=MIN_SAMPLES)]
    parts.append(emit_char_entry("_overall", by_player["_overall"]))
    parts.append("")
    for name, _ in eligible:
        parts.append(emit_char_entry(name, by_player[name]))
    parts.append("};")
    parts.append("")
    output = "\n".join(parts)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(output)

    print()
    print(f"Wrote {OUTPUT_PATH}")
    print(f"Included {len(eligible)} chars (>= {MIN_SAMPLES} samples) + _overall:")
    for name, n in eligible:
        print(f"  {name:20s}  n={n}")
    if excluded:
        print(f"\nExcluded {len(excluded)} chars:")
        for name, n, reason in excluded:
            print(f"  {name:20s}  n={n}  ({reason})")


if __name__ == "__main__":
    main()
