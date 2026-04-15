/**
 * grade-benchmarks.ts — Placeholder stat percentile thresholds for the Set Grading System.
 *
 * !! DEV ONLY — not shipped to users yet !!
 *
 * Replace BENCHMARKS with the "by_player_char" field from grade_baselines.json
 * after running scripts/fetch_slippilab_replays.py.
 *
 * Schema:
 *   p5/p10/p25 = low-end percentiles (used for inverted stats: openings_per_kill, avg_kill_percent)
 *   p50        = median
 *   p75/p90/p95 = high-end percentiles (used for normal stats)
 *
 * Grading dimension: benchmarks are keyed by the PLAYER'S character so that
 * a Fox player's damage/opening is compared against other Fox players, not
 * against Jigglypuff players whose kit produces fundamentally different numbers.
 * Use "_overall" as the cross-character fallback for universal stats (neutral win ratio).
 */

export interface StatThresholds {
  p5:  number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  p95: number;
}

export interface CharacterBenchmarks {
  // Neutral category
  neutral_win_ratio:  StatThresholds;
  openings_per_kill:  StatThresholds;  // inverted: lower = better
  // Punish category
  damage_per_opening: StatThresholds;
  avg_kill_percent:   StatThresholds;  // inverted: lower = better (killing early)
  // Defense category
  avg_death_percent:  StatThresholds;
  // Execution category
  l_cancel_ratio:     StatThresholds;
  inputs_per_minute:  StatThresholds;
}

/**
 * Benchmarks keyed by player character name (matching CHARACTERS in parser.ts).
 * "_overall" is the character-agnostic fallback.
 *
 * Replace this object with the "by_player_char" field from grade_baselines.json
 * after running scripts/fetch_slippilab_replays.py.
 */
export const BENCHMARKS: Record<string, CharacterBenchmarks> = {
  _overall: {
    neutral_win_ratio:  { p5: 0.33, p10: 0.38, p25: 0.44, p50: 0.50, p75: 0.57, p90: 0.63, p95: 0.67 },
    openings_per_kill:  { p5: 2.0,  p10: 2.3,  p25: 2.8,  p50: 3.3,  p75: 4.1,  p90: 5.2,  p95: 6.0  },
    damage_per_opening: { p5: 8.0,  p10: 10.2, p25: 13.5, p50: 19.2, p75: 24.1, p90: 29.4, p95: 34.0 },
    avg_kill_percent:   { p5: 58,   p10: 68,   p25: 82,   p50: 98,   p75: 118,  p90: 138,  p95: 152  },
    avg_death_percent:  { p5: 52,   p10: 65,   p25: 80,   p50: 98,   p75: 118,  p90: 138,  p95: 152  },
    l_cancel_ratio:     { p5: 0.40, p10: 0.55, p25: 0.68, p50: 0.78, p75: 0.87, p90: 0.93, p95: 0.97 },
    inputs_per_minute:  { p5: 90,   p10: 130,  p25: 185,  p50: 260,  p75: 340,  p90: 410,  p95: 460  },
  },
};
