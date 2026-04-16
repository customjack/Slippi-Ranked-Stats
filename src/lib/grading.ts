/**
 * grading.ts — Set Grading System logic.
 *
 * !! DEV ONLY — not shipped to users yet !!
 *
 * Grades a completed set across four equally-weighted categories:
 *   Neutral   (neutral_win_ratio, counter_hit_rate)
 *   Punish    (damage_per_opening, openings_per_kill, avg_kill_percent*)
 *   Defense   (avg_death_percent*, defensive_option_rate)
 *   Execution (l_cancel_ratio, inputs_per_minute)
 *
 * * avg_kill_percent and avg_death_percent are only scored when a character-
 *   specific or matchup-specific baseline is available. The _overall bucket
 *   has identical values for both by construction (symmetric pooling), so
 *   scoring them against _overall would produce misleading results.
 *
 * Benchmark lookup priority:
 *   1. by_matchup[playerChar][oppChar]  — matchup-specific (most precise)
 *   2. by_player_char[playerChar]       — character only
 *   3. by_player_char["_overall"]       — cross-character fallback
 *
 * Each stat is scored 0–100 via percentile interpolation. Category score =
 * equal-weight average of its non-null stats. Overall score = equal-weight
 * average of the four category scores, plus a +5 win bonus (capped at 100).
 */

import type { LiveGameStats } from "./store";
import { BENCHMARKS, type StatThresholds } from "./grade-benchmarks";

// ── Types ──────────────────────────────────────────────────────────────────

export type GradeLetter = "S" | "A" | "B" | "C" | "D" | "F";
export type CategoryKey  = "neutral" | "punish" | "defense" | "execution";

export interface StatGrade {
  value:     number | null;
  score:     number | null;   // 0–100 performance score
  grade:     GradeLetter | null;
  label:     string;
  formatted: string;
}

export interface CategoryGrade {
  label:  string;
  letter: GradeLetter | null;
  score:  number | null;
}

export interface SetGrade {
  letter:     GradeLetter;
  score:      number;           // 0–100 weighted composite
  categories: Record<CategoryKey, CategoryGrade>;
  breakdown: {
    neutral_win_ratio:     StatGrade;
    counter_hit_rate:      StatGrade;
    openings_per_kill:     StatGrade;
    damage_per_opening:    StatGrade;
    avg_kill_percent:      StatGrade;
    avg_death_percent:     StatGrade;
    defensive_option_rate: StatGrade;
    l_cancel_ratio:        StatGrade;
    inputs_per_minute:     StatGrade;
  };
  playerChar:     string;
  opponentChar:   string;
  baselineSource: "matchup" | "character" | "overall";
  setResult:      "win" | "loss";
  wins:           number;
  losses:         number;
}

// ── Stat configuration ─────────────────────────────────────────────────────

/** Stats where LOWER raw value = BETTER performance. */
const INVERTED_STATS = new Set([
  "openings_per_kill",
  "avg_kill_percent",
  "defensive_option_rate",
]);

/** Category definitions — stats listed in display order within each category.
 *  Exported so the display component can iterate the same mapping (avoids
 *  the previous duplicated list in SetGradeDisplay.svelte that drifted on
 *  category changes). */
export const CATEGORY_DEFS: Record<CategoryKey, { label: string; stats: (keyof SetGrade["breakdown"])[] }> = {
  neutral:   { label: "Neutral",   stats: ["neutral_win_ratio", "counter_hit_rate"]                                    },
  punish:    { label: "Punish",    stats: ["damage_per_opening", "openings_per_kill", "avg_kill_percent"]              },
  defense:   { label: "Defense",   stats: ["avg_death_percent", "defensive_option_rate"]                               },
  execution: { label: "Execution", stats: ["l_cancel_ratio", "inputs_per_minute"]                                      },
};

const STAT_LABELS: Record<string, string> = {
  neutral_win_ratio:     "Neutral Win Rate",
  counter_hit_rate:      "Counter Hit Rate",
  openings_per_kill:     "Openings / Kill",
  damage_per_opening:    "Damage / Opening",
  avg_kill_percent:      "Avg Kill %",
  avg_death_percent:     "Avg Death %",
  defensive_option_rate: "Def. Options / Min",
  l_cancel_ratio:        "L-Cancel %",
  inputs_per_minute:     "Inputs / Min",
};

// ── Percentile scoring ─────────────────────────────────────────────────────

function percentileScore(value: number, t: StatThresholds, inverted: boolean): number {
  let score: number;

  if (!inverted) {
    if      (value >= t.p95) score = 95 + Math.min((value - t.p95) / Math.max(t.p95 - t.p90, 0.001) * 5, 5);
    else if (value >= t.p90) score = 90 + (value - t.p90) / Math.max(t.p95 - t.p90, 0.001) * 5;
    else if (value >= t.p75) score = 75 + (value - t.p75) / Math.max(t.p90 - t.p75, 0.001) * 15;
    else if (value >= t.p50) score = 50 + (value - t.p50) / Math.max(t.p75 - t.p50, 0.001) * 25;
    else if (value >= t.p25) score = 25 + (value - t.p25) / Math.max(t.p50 - t.p25, 0.001) * 25;
    else                     score = Math.max(0, (value / Math.max(t.p25, 0.001)) * 25);
  } else {
    if      (value <= t.p5)  score = 95 + Math.min((t.p5  - value) / Math.max(t.p5,        0.001) * 5, 5);
    else if (value <= t.p10) score = 90 + (t.p10 - value) / Math.max(t.p10 - t.p5,  0.001) * 5;
    else if (value <= t.p25) score = 75 + (t.p25 - value) / Math.max(t.p25 - t.p10, 0.001) * 15;
    else if (value <= t.p50) score = 50 + (t.p50 - value) / Math.max(t.p50 - t.p25, 0.001) * 25;
    else if (value <= t.p75) score = 25 + (t.p75 - value) / Math.max(t.p75 - t.p50, 0.001) * 25;
    else                     score = Math.max(0, 25 * (1 - (value - t.p75) / Math.max(t.p75, 0.001)));
  }

  return Math.min(100, Math.max(0, score));
}

function scoreToGrade(score: number): GradeLetter {
  if (score >= 95) return "S";
  if (score >= 90) return "A";
  if (score >= 75) return "B";
  if (score >= 50) return "C";
  if (score >= 25) return "D";
  return "F";
}

function formatStatValue(key: string, value: number | null): string {
  if (value === null) return "—";
  if (key === "neutral_win_ratio" || key === "l_cancel_ratio" || key === "counter_hit_rate")
    return (value * 100).toFixed(0) + "%";
  if (key === "damage_per_opening")    return value.toFixed(1);
  if (key === "openings_per_kill")     return value.toFixed(2);
  if (key === "avg_kill_percent" || key === "avg_death_percent") return value.toFixed(0) + "%";
  if (key === "inputs_per_minute")     return Math.round(value).toString();
  if (key === "defensive_option_rate") return value.toFixed(1);
  return value.toFixed(2);
}

// ── Average stats across set games ────────────────────────────────────────

function averageSetStats(games: LiveGameStats[]): Record<string, number | null> {
  const allKeys = Object.keys(STAT_LABELS);
  const accum: Record<string, number[]> = {};
  for (const key of allKeys) accum[key] = [];

  for (const g of games) {
    for (const key of allKeys) {
      const val = (g as unknown as Record<string, unknown>)[key] as number | null;
      if (val !== null && val !== undefined && isFinite(val)) accum[key].push(val);
    }
  }

  const result: Record<string, number | null> = {};
  for (const key of allKeys) {
    const vals = accum[key];
    result[key] = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
  }
  return result;
}

// ── Main grading function ──────────────────────────────────────────────────

/**
 * Grade a completed set.
 *
 * @param games        All LiveGameStats entries for this set's match_id
 * @param playerChar   Player's character name (used for benchmark lookup)
 * @param opponentChar Opponent's character name (used for matchup benchmark lookup)
 * @param setResult    Whether the player won or lost the set
 * @param wins         Number of games won
 * @param losses       Number of games lost
 */
export function gradeSet(
  games: LiveGameStats[],
  playerChar: string,
  opponentChar: string,
  setResult: "win" | "loss",
  wins: number,
  losses: number,
): SetGrade {
  // ── Three-tier benchmark lookup ────────────────────────────────────────────
  // matchup (player × opp) → player char → _overall
  const matchupBenchmarks = BENCHMARKS.by_matchup?.[playerChar]?.[opponentChar];
  const charBenchmarks    = BENCHMARKS.by_player_char[playerChar];
  const overallBenchmarks = BENCHMARKS.by_player_char["_overall"];

  const benchmarks = matchupBenchmarks ?? charBenchmarks ?? overallBenchmarks;
  const baselineSource: "matchup" | "character" | "overall" =
    matchupBenchmarks ? "matchup" :
    charBenchmarks    ? "character" : "overall";

  // avg_kill% and avg_death% are heavily character-dependent. The _overall bucket
  // has identical values for both by construction (symmetric 1v1 pooling), making
  // scores misleading. Only score them when we have character-specific data.
  const SKIP_ON_OVERALL = new Set(
    baselineSource === "overall" ? ["avg_kill_percent", "avg_death_percent"] : []
  );

  const averaged = averageSetStats(games);

  // ── Score each stat ──────────────────────────────────────────────────────
  const breakdown = {} as SetGrade["breakdown"];

  for (const key of Object.keys(STAT_LABELS) as (keyof SetGrade["breakdown"])[]) {
    const value      = averaged[key] ?? null;
    const thresholds = (benchmarks as unknown as Record<string, StatThresholds>)[key];
    const inverted   = INVERTED_STATS.has(key);
    const skip       = SKIP_ON_OVERALL.has(key);

    let score: number | null = null;
    let grade: GradeLetter | null = null;

    if (!skip && value !== null && thresholds) {
      score = percentileScore(value, thresholds, inverted);
      grade = scoreToGrade(score);
    }

    breakdown[key] = {
      value,
      score,
      grade,
      label:     STAT_LABELS[key] ?? key,
      formatted: formatStatValue(key, value),
    };
  }

  // ── Score each category (equal weight among non-null stats) ──────────────
  const categories = {} as SetGrade["categories"];

  for (const [catKey, def] of Object.entries(CATEGORY_DEFS) as [CategoryKey, typeof CATEGORY_DEFS[CategoryKey]][]) {
    const scores = def.stats
      .map((s) => breakdown[s].score)
      .filter((s): s is number => s !== null);

    if (scores.length === 0) {
      categories[catKey] = { label: def.label, letter: null, score: null };
    } else {
      const catScore = scores.reduce((a, b) => a + b, 0) / scores.length;
      categories[catKey] = { label: def.label, letter: scoreToGrade(catScore), score: Math.round(catScore * 10) / 10 };
    }
  }

  // ── Overall score: equal weight across non-null categories + win bonus ────
  const catScores = Object.values(categories)
    .map((c) => c.score)
    .filter((s): s is number => s !== null);

  const rawScore = catScores.length > 0
    ? catScores.reduce((a, b) => a + b, 0) / catScores.length
    : 0;

  // +5 for a win — winning a set demonstrates adaptability and reads even when
  // raw metrics don't fully capture it.
  const winBonus    = setResult === "win" ? 5 : 0;
  const overallScore = Math.min(100, rawScore + winBonus);

  return {
    letter:     scoreToGrade(overallScore),
    score:      Math.round(overallScore * 10) / 10,
    categories,
    breakdown,
    playerChar,
    opponentChar,
    baselineSource,
    setResult,
    wins,
    losses,
  };
}
