#!/usr/bin/env python3
"""
set_grader.py — Phase 2 of the Set Grading System.

Loads grade_baselines.json and provides a grading function that takes a set's
averaged stats and returns a letter grade (S → F) per stat and overall.

Also includes a test function that pulls 5 random sets from the SQLite DB,
re-parses their .slp files, and prints grades to the terminal.

Usage (test mode):
    python set_grader.py --test --db-path "C:/Users/You/AppData/Roaming/Slippi Ranked Stats/data/JOEY_290.db"
"""

import argparse
import json
import os
import random
import sqlite3
import sys
from collections import defaultdict
from itertools import groupby

# Import the stat computation logic from baseline_generator
sys.path.insert(0, os.path.dirname(__file__))
from baseline_generator import CHARACTERS, compute_game_stats

# ── Constants ──────────────────────────────────────────────────────────────

BASELINES_PATH = os.path.join(os.path.dirname(__file__), "grade_baselines.json")

# Stat weights for the overall grade (must sum to 1.0)
# Stats that are None for a game are excluded and weight is redistributed.
WEIGHTS = {
    "neutral_win_ratio":  0.40,
    "openings_per_kill":  0.30,
    "damage_per_opening": 0.20,
    "l_cancel_ratio":     0.10,
}

# For openings_per_kill, LOWER is better — so we invert the percentile ranking.
INVERTED_STATS = {"openings_per_kill"}

# Numeric score per letter grade (used for weighted average → final letter)
GRADE_SCORES = {"S": 6, "A": 5, "B": 4, "C": 3, "D": 2, "F": 1}

# Grade display colors (ANSI terminal codes)
GRADE_COLORS = {
    "S": "\033[93m",   # bright yellow (gold)
    "A": "\033[92m",   # bright green
    "B": "\033[94m",   # bright blue
    "C": "\033[93m",   # yellow
    "D": "\033[91m",   # red
    "F": "\033[91m",   # red
}
RESET = "\033[0m"

# ── Grading logic ──────────────────────────────────────────────────────────

def load_baselines(path: str = BASELINES_PATH) -> dict:
    """Load grade_baselines.json. Raises FileNotFoundError if missing."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"grade_baselines.json not found at: {path}\n"
            "Run baseline_generator.py first to generate it."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def percentile_score(value: float, thresholds: dict, inverted: bool = False) -> float:
    """
    Map a raw stat value to a 0–100 performance score using linear interpolation.

    For normal stats (higher = better), uses the HIGH-end percentiles:
        p95 threshold → S tier, p90 → A, p75 → B, p50 → C, p25 → D, below → F

    For inverted stats (lower = better, e.g. openings_per_kill), uses the
    LOW-end percentiles from the raw distribution:
        p5 threshold → S tier, p10 → A, p25 → B, p50 → C, p75 → D, above → F

    Returns a float in [0, 100].
    """
    p50 = thresholds.get("p50")

    if p50 is None:
        return 50.0  # fallback if thresholds are missing

    if not inverted:
        p25 = thresholds.get("p25", p50 * 0.75)
        p75 = thresholds.get("p75")
        p90 = thresholds.get("p90")
        p95 = thresholds.get("p95")

        if any(v is None for v in [p75, p90, p95]):
            return 50.0

        # Higher value = higher score
        if   value >= p95: score = 95.0 + min((value - p95) / max(p95 - p90, 0.001) * 5, 5.0)
        elif value >= p90: score = 90.0 + (value - p90) / max(p95 - p90, 0.001) * 5
        elif value >= p75: score = 75.0 + (value - p75) / max(p90 - p75, 0.001) * 15
        elif value >= p50: score = 50.0 + (value - p50) / max(p75 - p50, 0.001) * 25
        elif value >= p25: score = 25.0 + (value - p25) / max(p50 - p25, 0.001) * 25
        else:              score = max(0.0, value / max(p25, 0.001) * 25)
    else:
        # Lower value = higher score.
        # Use the low-end raw percentiles as high-performance thresholds:
        #   p5 raw → only 5% of players are this good → S tier
        #   p10 raw → top 10% → A tier
        #   p25 raw → top 25% → B tier
        #   p50 raw → average → C tier
        #   p75 raw → worse than average → D tier
        #   above p75 → F tier
        p5  = thresholds.get("p5")
        p10 = thresholds.get("p10")
        p25 = thresholds.get("p25")
        p75 = thresholds.get("p75")

        if any(v is None for v in [p5, p10, p25, p75]):
            # Fallback: no low-end percentiles → estimate from p50 mirror
            score = max(0.0, min(100.0, (1.0 - value / max(p50, 0.001)) * 100 + 50))
            return min(100.0, max(0.0, score))

        if   value <= p5:  score = 95.0 + min((p5 - value)  / max(p5,        0.001) * 5, 5.0)
        elif value <= p10: score = 90.0 + (p10 - value) / max(p10 - p5,  0.001) * 5
        elif value <= p25: score = 75.0 + (p25 - value) / max(p25 - p10, 0.001) * 15
        elif value <= p50: score = 50.0 + (p50 - value) / max(p50 - p25, 0.001) * 25
        elif value <= p75: score = 25.0 + (p75 - value) / max(p75 - p50, 0.001) * 25
        else:              score = max(0.0, 25.0 * (1.0 - (value - p75) / max(p75, 0.001)))

    return min(100.0, max(0.0, score))


def score_to_grade(score: float) -> str:
    """Map a 0–100 percentile score to a letter grade."""
    if   score >= 95: return "S"
    elif score >= 90: return "A"
    elif score >= 75: return "B"
    elif score >= 50: return "C"
    elif score >= 25: return "D"
    else:             return "F"


def grade_set(set_stats: dict, opponent_char: str, baselines: dict) -> dict:
    """
    Grade a set given averaged per-set stats.

    Args:
        set_stats: dict with keys from WEIGHTS (any may be None)
        opponent_char: character name string, e.g. "Falco"
        baselines: loaded grade_baselines.json dict

    Returns:
        {
            "overall": "A",
            "overall_score": 82.4,
            "breakdown": {
                "neutral_win_ratio":  {"value": 0.58, "score": 87.2, "grade": "A"},
                "openings_per_kill":  {"value": 2.9,  "score": 78.1, "grade": "B"},
                "damage_per_opening": {"value": 22.1, "score": 72.3, "grade": "B"},
                "l_cancel_ratio":     {"value": 0.91, "score": 91.0, "grade": "A"},
            },
            "opponent_char": "Falco",
            "baseline_source": "by_character" | "_overall"
        }
    """
    by_char = baselines.get("by_character", {})

    # Prefer character-specific baselines, fall back to overall
    if opponent_char in by_char:
        char_baselines = by_char[opponent_char]
        baseline_source = "by_character"
    else:
        char_baselines = by_char.get("_overall", {})
        baseline_source = "_overall"

    breakdown = {}
    weighted_score = 0.0
    total_weight   = 0.0

    for stat, weight in WEIGHTS.items():
        value = set_stats.get(stat)
        if value is None:
            continue  # stat not available — skip and redistribute weight

        thresholds = char_baselines.get(stat, {})
        inverted   = stat in INVERTED_STATS
        score      = percentile_score(value, thresholds, inverted=inverted)
        grade      = score_to_grade(score)

        breakdown[stat] = {
            "value": round(value, 4),
            "score": round(score, 1),
            "grade": grade,
        }
        weighted_score += score * weight
        total_weight   += weight

    # Normalize weighted score if some stats were None
    overall_score  = (weighted_score / total_weight) if total_weight > 0 else 0.0
    overall_grade  = score_to_grade(overall_score)

    return {
        "overall":        overall_grade,
        "overall_score":  round(overall_score, 1),
        "breakdown":      breakdown,
        "opponent_char":  opponent_char,
        "baseline_source": baseline_source,
    }


def average_game_stats(game_stats_list: list[dict]) -> dict:
    """Average a list of per-game stat dicts into a single per-set stat dict."""
    accum: dict[str, list[float]] = defaultdict(list)
    for gs in game_stats_list:
        for key in WEIGHTS:
            val = gs.get(key)
            if val is not None:
                accum[key].append(val)

    return {key: (sum(vals) / len(vals) if vals else None) for key, vals in accum.items()}


# ── Test function ──────────────────────────────────────────────────────────

def print_grade(grade_result: dict, set_info: dict) -> None:
    """Pretty-print a grade result to the terminal."""
    overall    = grade_result["overall"]
    color      = GRADE_COLORS.get(overall, "")
    opp_char   = grade_result["opponent_char"]
    score      = grade_result["overall_score"]
    wins       = set_info.get("wins", "?")
    losses     = set_info.get("losses", "?")
    set_result = "WIN" if set_info.get("result") == "win" else "LOSS"

    print(f"\n{'─'*55}")
    print(f"  Set vs {opp_char:<20}  [{wins}-{losses}] {set_result}")
    print(f"  Overall Grade: {color}{overall}{RESET}  (score: {score:.1f}/100)")
    print(f"  Baseline: {grade_result['baseline_source']}")
    print(f"  {'Stat':<22} {'Value':>9}  {'Score':>7}  {'Grade':>5}")
    print(f"  {'─'*22}  {'─'*9}  {'─'*7}  {'─'*5}")

    stat_labels = {
        "neutral_win_ratio":  "Neutral Win Rate",
        "openings_per_kill":  "Openings / Kill",
        "damage_per_opening": "Damage / Opening",
        "l_cancel_ratio":     "L-Cancel %",
    }

    for stat, info in grade_result["breakdown"].items():
        label = stat_labels.get(stat, stat)
        val   = info["value"]
        sc    = info["score"]
        gr    = info["grade"]
        g_color = GRADE_COLORS.get(gr, "")

        # Format value nicely
        if stat in ("neutral_win_ratio", "l_cancel_ratio"):
            val_str = f"{val * 100:.1f}%"
        elif stat == "damage_per_opening":
            val_str = f"{val:.1f} dmg"
        elif stat == "openings_per_kill":
            val_str = f"{val:.2f}"
        else:
            val_str = f"{val:.2f}"

        print(f"  {label:<22}  {val_str:>9}  {sc:>6.1f}%  {g_color}{gr:>5}{RESET}")


def run_test(db_path: str, baselines: dict, n: int = 5) -> None:
    """Pull n random sets from the DB, grade them, and print results."""
    db_path = os.path.expanduser(db_path)
    if not os.path.exists(db_path):
        print(f"ERROR: DB not found at: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT match_id, filepath, player_port, opponent_char_id, result "
        "FROM games WHERE match_type='ranked' AND filepath IS NOT NULL "
        "ORDER BY RANDOM()"
    ).fetchall()
    conn.close()

    # Group into sets by match_id
    sets_by_id: dict[str, list] = defaultdict(list)
    for match_id, filepath, player_port, opp_char_id, result in rows:
        sets_by_id[match_id].append({
            "filepath": filepath,
            "player_port": player_port,
            "opp_char_id": opp_char_id,
            "result": result,
        })

    # Filter to valid sets (≥2 games with accessible files)
    valid_sets = [
        (mid, games) for mid, games in sets_by_id.items()
        if len(games) >= 2 and all(os.path.exists(g["filepath"]) for g in games)
    ]

    if not valid_sets:
        print("ERROR: No valid sets found with accessible .slp files.", file=sys.stderr)
        print("Make sure you run this script on the same machine as your replays.", file=sys.stderr)
        sys.exit(1)

    sample = random.sample(valid_sets, min(n, len(valid_sets)))
    print(f"\nGrading {len(sample)} random sets from your DB...\n")

    for match_id, games in sample:
        game_stats_list = []
        for g in games:
            stats = compute_game_stats(g["filepath"], g["player_port"])
            if stats:
                game_stats_list.append(stats)

        if not game_stats_list:
            print(f"  [SKIP] {match_id} — no parseable games")
            continue

        wins   = sum(1 for g in games if g["result"] in ("win", "lras_win"))
        losses = sum(1 for g in games if g["result"] in ("loss", "lras_loss"))
        result = "win" if wins > losses else "loss"

        opp_char_id = games[0]["opp_char_id"]
        opp_char    = CHARACTERS.get(opp_char_id, f"Unknown_{opp_char_id}")

        set_stats    = average_game_stats(game_stats_list)
        grade_result = grade_set(set_stats, opp_char, baselines)

        print_grade(grade_result, {"wins": wins, "losses": losses, "result": result})

    print(f"\n{'─'*55}\n")


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Set Grader — assign S→F grades to Melee sets")
    parser.add_argument("--baselines", default=BASELINES_PATH,
                        help="Path to grade_baselines.json (default: scripts/grade_baselines.json)")
    parser.add_argument("--test", action="store_true",
                        help="Run test mode: grade 5 random sets from the DB and print results")
    parser.add_argument("--db-path",
                        help="Path to SQLite DB (required for --test mode)")
    parser.add_argument("--n", type=int, default=5,
                        help="Number of sets to test (default: 5)")
    args = parser.parse_args()

    baselines = load_baselines(args.baselines)
    print(f"Loaded baselines — {baselines.get('sample_size', '?')} games, "
          f"generated at {baselines.get('generated_at', 'unknown')}")

    if args.test:
        if not args.db_path:
            print("ERROR: --db-path is required for --test mode", file=sys.stderr)
            sys.exit(1)
        run_test(args.db_path, baselines, n=args.n)
    else:
        print("\nNo action specified. Use --test to grade random sets.")
        print("Import grade_set() from this module to use grading in other scripts.")


if __name__ == "__main__":
    main()
