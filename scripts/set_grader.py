#!/usr/bin/env python3
"""
set_grader.py — Set grading diagnostic tool.

Loads grade_baselines.json and grades sets from the SQLite DB, mirroring
the algorithm in src/lib/grading.ts exactly.

Usage:
    # Grade ALL sets and print distribution analysis:
    python set_grader.py --db-path "C:/Users/You/AppData/.../JOEY_290.db" --all

    # Grade N random sets with per-set detail:
    python set_grader.py --db-path "C:/..." --n 10 --verbose
"""

import argparse
import json
import os
import random
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from baseline_generator import CHARACTERS, compute_game_stats

# -- Constants (mirror grading.ts) -----------------------------------------

BASELINES_PATH = os.path.join(os.path.dirname(__file__), "grade_baselines.json")

CATEGORY_DEFS: dict[str, list[str]] = {
    "neutral":   ["neutral_win_ratio", "counter_hit_rate"],
    "punish":    ["damage_per_opening", "openings_per_kill", "avg_kill_percent"],
    "defense":   ["avg_death_percent", "defensive_option_rate"],
    "execution": ["l_cancel_ratio", "inputs_per_minute"],
}

ALL_STATS = [s for stats in CATEGORY_DEFS.values() for s in stats]

# Lower raw value = better performance
INVERTED_STATS = {"openings_per_kill", "avg_kill_percent", "defensive_option_rate"}

# Skipped when baseline source is "overall" — symmetric pooling makes them
# identical for both players in the _overall bucket, so scores are meaningless.
SKIP_ON_OVERALL = {"avg_kill_percent", "avg_death_percent"}

GRADE_COLORS = {
    "S": "\033[93m",   # bright yellow
    "A": "\033[92m",   # bright green
    "B": "\033[94m",   # bright blue
    "C": "\033[93m",   # yellow
    "D": "\033[91m",   # red
    "F": "\033[91m",   # red
}
RESET = "\033[0m"

STAT_LABELS = {
    "neutral_win_ratio":     "Neutral Win Rate",
    "counter_hit_rate":      "Counter Hit Rate",
    "damage_per_opening":    "Damage / Opening",
    "openings_per_kill":     "Openings / Kill",
    "avg_kill_percent":      "Avg Kill %",
    "avg_death_percent":     "Avg Death %",
    "defensive_option_rate": "Def Options / Min",
    "l_cancel_ratio":        "L-Cancel %",
    "inputs_per_minute":     "Inputs / Min",
}

# -- Grading logic (mirrors grading.ts) ------------------------------------

def load_baselines(path: str = BASELINES_PATH) -> dict:
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"grade_baselines.json not found at: {path}\n"
            "Run baseline_generator.py or fetch_slippilab_replays.py first."
        )
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def percentile_score(value: float, thresholds: dict, inverted: bool = False) -> float:
    """Map a raw stat value to a 0–100 performance score via linear interpolation."""
    p50 = thresholds.get("p50")
    if p50 is None:
        return 50.0

    if not inverted:
        p25 = thresholds.get("p25", p50 * 0.75)
        p75 = thresholds.get("p75")
        p90 = thresholds.get("p90")
        p95 = thresholds.get("p95")
        if any(v is None for v in [p75, p90, p95]):
            return 50.0

        if   value >= p95: score = 95.0 + min((value - p95) / max(p95 - p90, 0.001) * 5, 5.0)
        elif value >= p90: score = 90.0 + (value - p90) / max(p95 - p90, 0.001) * 5
        elif value >= p75: score = 75.0 + (value - p75) / max(p90 - p75, 0.001) * 15
        elif value >= p50: score = 50.0 + (value - p50) / max(p75 - p50, 0.001) * 25
        elif value >= p25: score = 25.0 + (value - p25) / max(p50 - p25, 0.001) * 25
        else:              score = max(0.0, value / max(p25, 0.001) * 25)
    else:
        p5  = thresholds.get("p5")
        p10 = thresholds.get("p10")
        p25 = thresholds.get("p25")
        p75 = thresholds.get("p75")
        if any(v is None for v in [p5, p10, p25, p75]):
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
    if   score >= 95: return "S"
    elif score >= 90: return "A"
    elif score >= 75: return "B"
    elif score >= 50: return "C"
    elif score >= 25: return "D"
    else:             return "F"


def grade_set(
    set_stats: dict,
    player_char: str,
    opponent_char: str,
    set_result: str,
    baselines: dict,
) -> dict:
    """
    Grade a set against community benchmarks.

    Three-tier lookup: by_matchup[playerChar][oppChar]
                       → by_player_char[playerChar]
                       → by_player_char["_overall"]

    Win bonus: +5 to composite score for a set win, capped at 100.
    avg_kill_percent / avg_death_percent skipped when baseline is "_overall"
    (symmetric pooling makes those stats identical for both players).
    """
    by_matchup  = baselines.get("by_matchup", {})
    by_player   = baselines.get("by_player_char", {})

    matchup_bench = by_matchup.get(player_char, {}).get(opponent_char)
    char_bench    = by_player.get(player_char)
    overall_bench = by_player.get("_overall", {})

    if matchup_bench:
        bench           = matchup_bench
        baseline_source = "matchup"
    elif char_bench:
        bench           = char_bench
        baseline_source = "character"
    else:
        bench           = overall_bench
        baseline_source = "overall"

    skip = SKIP_ON_OVERALL if baseline_source == "overall" else set()

    cat_scores: dict[str, dict] = {}
    breakdown:  dict[str, dict] = {}

    for cat_name, stat_list in CATEGORY_DEFS.items():
        cat_stat_scores: list[float] = []
        for stat in stat_list:
            if stat in skip:
                continue
            value = set_stats.get(stat)
            if value is None:
                continue
            thresholds = bench.get(stat, {})
            inverted   = stat in INVERTED_STATS
            score      = percentile_score(value, thresholds, inverted=inverted)
            breakdown[stat] = {
                "value": round(value, 4),
                "score": round(score, 1),
                "grade": score_to_grade(score),
            }
            cat_stat_scores.append(score)

        if cat_stat_scores:
            cat_avg = sum(cat_stat_scores) / len(cat_stat_scores)
            cat_scores[cat_name] = {
                "score": round(cat_avg, 1),
                "grade": score_to_grade(cat_avg),
            }

    if cat_scores:
        raw_overall = sum(c["score"] for c in cat_scores.values()) / len(cat_scores)
    else:
        raw_overall = 50.0

    win_bonus     = 5.0 if set_result == "win" else 0.0
    overall_score = min(100.0, raw_overall + win_bonus)
    overall_grade = score_to_grade(overall_score)

    return {
        "overall":         overall_grade,
        "overall_score":   round(overall_score, 1),
        "categories":      cat_scores,
        "breakdown":       breakdown,
        "player_char":     player_char,
        "opponent_char":   opponent_char,
        "baseline_source": baseline_source,
        "win_bonus":       win_bonus,
    }


def average_game_stats(game_stats_list: list[dict]) -> dict:
    """Average per-game stats into a single set-level stat dict."""
    accum: dict[str, list[float]] = defaultdict(list)
    for gs in game_stats_list:
        for key in ALL_STATS:
            val = gs.get(key)
            if val is not None:
                accum[key].append(val)
    return {key: (sum(vals) / len(vals) if vals else None) for key, vals in accum.items()}


# -- Display helpers --------------------------------------------------------

def print_grade(grade_result: dict, set_info: dict) -> None:
    """Pretty-print a single set's grade to the terminal."""
    overall     = grade_result["overall"]
    color       = GRADE_COLORS.get(overall, "")
    player_char = grade_result["player_char"]
    opp_char    = grade_result["opponent_char"]
    score       = grade_result["overall_score"]
    wins        = set_info.get("wins", "?")
    losses      = set_info.get("losses", "?")
    set_result  = "WIN" if set_info.get("result") == "win" else "LOSS"
    bonus_str   = "  [+5 win bonus]" if grade_result.get("win_bonus") else ""

    print(f"\n{'-'*62}")
    print(f"  {player_char} vs {opp_char:<20}  [{wins}-{losses}] {set_result}")
    print(f"  Overall: {color}{overall}{RESET}  ({score:.1f}/100)"
          f"  [baseline: {grade_result['baseline_source']}]{bonus_str}")

    for cat_name, cat_info in grade_result.get("categories", {}).items():
        cat_color = GRADE_COLORS.get(cat_info["grade"], "")
        print(f"\n  {cat_name.upper():<12} {cat_color}{cat_info['grade']}{RESET}"
              f"  ({cat_info['score']:.1f})")
        print(f"  {'Stat':<24} {'Value':>10}  {'Score':>7}  {'Grade':>5}")
        print(f"  {'-'*24}  {'-'*10}  {'-'*7}  {'-'*5}")

        for stat in CATEGORY_DEFS[cat_name]:
            info = grade_result["breakdown"].get(stat)
            if info is None:
                continue
            label   = STAT_LABELS.get(stat, stat)
            val     = info["value"]
            sc      = info["score"]
            gr      = info["grade"]
            g_color = GRADE_COLORS.get(gr, "")

            if stat in ("neutral_win_ratio", "l_cancel_ratio", "counter_hit_rate"):
                val_str = f"{val * 100:.1f}%"
            elif stat in ("avg_kill_percent", "avg_death_percent", "damage_per_opening"):
                val_str = f"{val:.1f}"
            elif stat == "inputs_per_minute":
                val_str = f"{val:.0f} ipm"
            elif stat == "defensive_option_rate":
                val_str = f"{val:.2f}/min"
            else:
                val_str = f"{val:.2f}"

            print(f"  {label:<24}  {val_str:>10}  {sc:>6.1f}%  {g_color}{gr:>5}{RESET}")


def print_distribution(results: list[dict]) -> None:
    """Print grade distribution and per-stat/category analysis across all graded sets."""
    grades = [r["overall"] for r in results]
    total  = len(grades)

    print(f"\n{'='*62}")
    print(f"  GRADE DISTRIBUTION  ({total} sets)")
    print(f"{'='*62}")

    for letter in ["S", "A", "B", "C", "D", "F"]:
        count = grades.count(letter)
        bar   = "#" * (count * 32 // max(total, 1))
        pct   = count / total * 100
        color = GRADE_COLORS.get(letter, "")
        print(f"  {color}{letter}{RESET}  {bar:<32}  {count:>4} ({pct:.0f}%)")

    avg_score = sum(r["overall_score"] for r in results) / total
    print(f"\n  Average score: {avg_score:.1f}/100")

    wins   = [r for r in results if r.get("set_result") == "win"]
    losses = [r for r in results if r.get("set_result") == "loss"]
    if wins:
        win_avg = sum(r["overall_score"] for r in wins) / len(wins)
        print(f"  Win avg score:  {win_avg:.1f}  ({len(wins)} sets)")
    if losses:
        loss_avg = sum(r["overall_score"] for r in losses) / len(losses)
        print(f"  Loss avg score: {loss_avg:.1f}  ({len(losses)} sets)")

    # Per-category
    print(f"\n{'-'*62}")
    print(f"  PER-CATEGORY AVERAGES")
    print(f"{'-'*62}")
    print(f"  {'Category':<14}  {'Avg Score':>9}  {'Grade':>5}  {'N':>5}")
    print(f"  {'-'*14}  {'-'*9}  {'-'*5}  {'-'*5}")

    for cat_name in CATEGORY_DEFS:
        scores = [r["categories"][cat_name]["score"]
                  for r in results if cat_name in r.get("categories", {})]
        if not scores:
            continue
        avg   = sum(scores) / len(scores)
        grade = score_to_grade(avg)
        color = GRADE_COLORS.get(grade, "")
        print(f"  {cat_name.capitalize():<14}  {avg:>9.1f}  {color}{grade:>5}{RESET}  {len(scores):>5}")

    # Per-stat
    print(f"\n{'-'*62}")
    print(f"  PER-STAT AVERAGES")
    print(f"{'-'*62}")
    print(f"  {'Stat':<24}  {'Avg Score':>9}  {'Grade':>5}  {'N':>5}")
    print(f"  {'-'*24}  {'-'*9}  {'-'*5}  {'-'*5}")

    for stat in ALL_STATS:
        scores = [r["breakdown"][stat]["score"]
                  for r in results if stat in r.get("breakdown", {})]
        if not scores:
            continue
        avg   = sum(scores) / len(scores)
        grade = score_to_grade(avg)
        color = GRADE_COLORS.get(grade, "")
        label = STAT_LABELS.get(stat, stat)
        inv   = " (inv)" if stat in INVERTED_STATS else ""
        print(f"  {label:<24}  {avg:>9.1f}  {color}{grade:>5}{RESET}  {len(scores):>5}{inv}")

    # Baseline source breakdown
    sources: dict[str, int] = defaultdict(int)
    for r in results:
        sources[r.get("baseline_source", "unknown")] += 1
    print(f"\n{'-'*62}")
    print(f"  BASELINE USAGE")
    print(f"{'-'*62}")
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {src:<16}  {count:>4} sets ({count/total*100:.0f}%)")

    print(f"\n{'='*62}\n")


# -- DB helpers -------------------------------------------------------------

def load_sets_from_db(db_path: str) -> list[dict]:
    """Load all ranked sets from the DB, grouped by match_id."""
    db_path = os.path.expanduser(db_path)
    if not os.path.exists(db_path):
        print(f"ERROR: DB not found at: {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT match_id, filepath, player_port, player_char_id, opponent_char_id, result "
        "FROM games WHERE match_type='ranked' AND filepath IS NOT NULL "
        "ORDER BY match_id"
    ).fetchall()
    conn.close()

    sets_by_id: dict[str, list] = defaultdict(list)
    for match_id, filepath, player_port, player_char_id, opp_char_id, result in rows:
        sets_by_id[match_id].append({
            "filepath":       filepath,
            "player_port":    player_port,
            "player_char_id": player_char_id,
            "opp_char_id":    opp_char_id,
            "result":         result,
        })

    return [
        {"match_id": mid, "games": games}
        for mid, games in sets_by_id.items()
        if len(games) >= 2
    ]


def run_grading(
    sets: list[dict],
    baselines: dict,
    verbose: bool = False,
) -> list[dict]:
    """Parse and grade a list of sets. Returns enriched result dicts."""
    results = []
    total   = len(sets)

    for i, s in enumerate(sets):
        games = s["games"]

        accessible = [g for g in games if os.path.exists(g["filepath"])]
        if not accessible:
            continue

        if (i + 1) % 50 == 0 or (i + 1) == total:
            print(f"  Progress: {i+1}/{total} sets graded...", end="\r", flush=True)

        game_stats_list = []
        for g in accessible:
            stats = compute_game_stats(g["filepath"], g["player_port"])
            if stats:
                game_stats_list.append(stats)

        if not game_stats_list:
            continue

        wins        = sum(1 for g in games if g["result"] in ("win", "lras_win"))
        losses      = sum(1 for g in games if g["result"] in ("loss", "lras_loss"))
        set_result  = "win" if wins > losses else "loss"

        player_char = CHARACTERS.get(games[0]["player_char_id"], f"Unknown_{games[0]['player_char_id']}")
        opp_char    = CHARACTERS.get(games[0]["opp_char_id"],    f"Unknown_{games[0]['opp_char_id']}")

        set_stats    = average_game_stats(game_stats_list)
        grade_result = grade_set(set_stats, player_char, opp_char, set_result, baselines)
        grade_result["set_result"] = set_result

        if verbose:
            print_grade(grade_result, {"wins": wins, "losses": losses, "result": set_result})

        results.append(grade_result)

    print()  # clear progress line
    return results


# -- Main -------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Grade Melee sets against community baselines and analyze calibration"
    )
    parser.add_argument("--baselines", default=BASELINES_PATH,
                        help="Path to grade_baselines.json")
    parser.add_argument("--db-path", required=True,
                        help="Path to the SQLite DB")
    parser.add_argument("--all", action="store_true",
                        help="Grade ALL sets and print distribution analysis")
    parser.add_argument("--n", type=int, default=10,
                        help="Number of random sets to grade when not using --all (default: 10)")
    parser.add_argument("--verbose", action="store_true",
                        help="Print per-set detail for every graded set")
    args = parser.parse_args()

    baselines = load_baselines(args.baselines)
    print(f"Loaded baselines — {baselines.get('sample_size', '?')} games, "
          f"generated {baselines.get('generated_at', 'unknown')}")

    all_sets = load_sets_from_db(args.db_path)
    print(f"Found {len(all_sets)} ranked sets in DB.")

    if args.all:
        target = all_sets
    else:
        target = random.sample(all_sets, min(args.n, len(all_sets)))
        print(f"Sampling {len(target)} random sets...")

    print(f"Grading {len(target)} sets...\n")
    results = run_grading(target, baselines, verbose=args.verbose)

    if not results:
        print("No sets could be graded — check that .slp files are accessible.")
        sys.exit(1)

    if args.all or not args.verbose:
        print_distribution(results)

    print(f"Done. Graded {len(results)}/{len(target)} sets "
          f"({len(target) - len(results)} skipped — missing files).")


if __name__ == "__main__":
    main()
