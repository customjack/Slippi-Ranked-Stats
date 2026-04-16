/**
 * grade-benchmarks.ts — Stat percentile thresholds for the Set Grading System.
 *
 * !! DEV ONLY — not shipped to users yet !!
 *
 * Generated from scripts/grade_baselines.json (5,000 SlippiLab replays, 4,951 parsed).
 * Characters with fewer than 20 samples fall back to by_player_char["_overall"].
 * Only Mr. Game & Watch (16 samples) still falls back.
 *
 * Benchmark lookup priority (grading.ts):
 *   1. by_matchup[playerChar][oppChar]  — matchup-specific (most precise)
 *   2. by_player_char[playerChar]       — player character only
 *   3. by_player_char["_overall"]       — cross-character fallback
 *
 * Placeholder notes:
 *   - inputs_per_minute: py-slippi can't compute it (no pre-frame button access).
 *     The in-app TS parser computes it live. Placeholder values used until we have
 *     community baselines from accumulated user data.
 *   - counter_hit_rate, defensive_option_rate: new stats. fetch_slippilab_replays.py
 *     now computes them; real data pending next fetch run.
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
  neutral_win_ratio:     StatThresholds;
  counter_hit_rate:      StatThresholds;  // placeholder: higher = better
  openings_per_kill:     StatThresholds;  // inverted: lower = better
  damage_per_opening:    StatThresholds;
  avg_kill_percent:      StatThresholds;  // inverted: lower = better (killing early)
  avg_death_percent:     StatThresholds;
  defensive_option_rate: StatThresholds;  // placeholder — inverted: lower = better (fewer rolls/dodges)
  l_cancel_ratio:        StatThresholds;
  inputs_per_minute:     StatThresholds;  // placeholder — character-specific once real data available
}

// Placeholder thresholds for stats not yet populated from community data.
const COUNTER_HIT_PLACEHOLDER: StatThresholds =
  { p5: 0.0,  p10: 0.05, p25: 0.15, p50: 0.30, p75: 0.45, p90: 0.60, p95: 0.70 };
const DEFENSIVE_RATE_PLACEHOLDER: StatThresholds =
  { p5: 0.3,  p10: 0.8,  p25: 1.8,  p50: 3.5,  p75: 6.5,  p90: 9.5,  p95: 12.0 };
const IPM_PLACEHOLDER: StatThresholds =
  { p5: 90,   p10: 130,  p25: 185,  p50: 260,  p75: 340,  p90: 410,  p95: 460 };

export const BENCHMARKS: {
  by_player_char: Record<string, CharacterBenchmarks>;
  by_matchup:     Record<string, Record<string, CharacterBenchmarks>>;
} = {
  // Populated by fetch_slippilab_replays.py as matchup data accumulates.
  by_matchup: {},

  by_player_char: {
    "_overall": {
      neutral_win_ratio:     { p5: 0.1852, p10: 0.2667, p25: 0.3846, p50: 0.5,      p75: 0.6154, p90: 0.7333, p95: 0.8148 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.25,   p10: 1.75,   p25: 2.5,    p50: 3.75,    p75: 5.25,   p90: 7.0,    p95: 9.0    },
      damage_per_opening:    { p5: 15.295, p10: 18.6612,p25: 23.8454,p50: 30.96,   p75: 41.5754,p90: 57.6007,p95: 73.0181 },
      avg_kill_percent:      { p5: 58.054, p10: 73.606, p25: 91.3833,p50: 110.5725,p75: 128.41, p90: 144.1668,p95: 156.3953 },
      avg_death_percent:     { p5: 58.054, p10: 73.606, p25: 91.3833,p50: 110.5725,p75: 128.41, p90: 144.1668,p95: 156.3953 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.1095, p25: 0.5,    p50: 0.75,    p75: 0.8718, p90: 0.9362, p95: 0.9706 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },

    "Bowser": {
      neutral_win_ratio:     { p5: 0.2031, p10: 0.2857, p25: 0.5,    p50: 0.5,     p75: 1.0,    p90: 1.0,    p95: 1.0    },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 0.25,   p10: 0.25,   p25: 0.25,   p50: 0.25,    p75: 3.0,    p90: 5.0,    p95: 6.85   },
      damage_per_opening:    { p5: 9.0,    p10: 10.5742,p25: 21.0129,p50: 62.6967, p75: 325.0,  p90: 325.0,  p95: 325.0  },
      avg_kill_percent:      { p5: 27.3575,p10: 47.685, p25: 86.0975,p50: 325.0,   p75: 325.0,  p90: 325.0,  p95: 325.0  },
      avg_death_percent:     { p5: 57.4038,p10: 67.528, p25: 97.6,   p50: 125.9375,p75: 147.1401,p90: 165.885,p95: 174.8647 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.2,    p25: 0.5946, p50: 0.7,     p75: 0.8333, p90: 0.9231, p95: 0.9231 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Captain Falcon": {
      neutral_win_ratio:     { p5: 0.211,  p10: 0.3,    p25: 0.4211, p50: 0.5263,  p75: 0.625,  p90: 0.7222, p95: 0.7917 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.0,    p10: 1.75,   p25: 2.5,    p50: 3.6667,  p75: 4.75,   p90: 6.0,    p95: 7.5    },
      damage_per_opening:    { p5: 16.9799,p10: 19.5452,p25: 23.734, p50: 30.4828, p75: 40.9175,p90: 54.0771,p95: 70.8101 },
      avg_kill_percent:      { p5: 64.5148,p10: 74.956, p25: 90.6211,p50: 107.3158,p75: 121.7893,p90: 134.6203,p95: 140.6994 },
      avg_death_percent:     { p5: 58.134, p10: 72.8234,p25: 90.2367,p50: 110.8567,p75: 127.8088,p90: 146.413,p95: 164.024 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.3333, p10: 0.5375, p25: 0.75,   p50: 0.8547,  p75: 0.9171, p90: 0.9615, p95: 0.9772 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Donkey Kong": {
      neutral_win_ratio:     { p5: 0.1286, p10: 0.2206, p25: 0.4914, p50: 0.6897,  p75: 1.0,    p90: 1.0,    p95: 1.0    },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 0.1625, p10: 0.825,  p25: 2.0625, p50: 3.375,   p75: 5.1875, p90: 6.6,    p95: 7.0    },
      damage_per_opening:    { p5: 10.269, p10: 10.8517,p25: 13.4598,p50: 20.255,  p75: 29.3404,p90: 43.7691,p95: 51.3735 },
      avg_kill_percent:      { p5: 6.075,  p10: 15.8372,p25: 50.4588,p50: 67.94,   p75: 110.4369,p90: 124.6755,p95: 131.2193 },
      avg_death_percent:     { p5: 53.676, p10: 62.0507,p25: 74.46,  p50: 95.3933, p75: 124.615,p90: 130.095,p95: 138.4462 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0191, p25: 0.2857, p50: 0.5679,  p75: 0.7825, p90: 0.8862, p95: 0.9157 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Dr. Mario": {
      neutral_win_ratio:     { p5: 0.214,  p10: 0.264,  p25: 0.3495, p50: 0.4336,  p75: 0.5179, p90: 0.5731, p95: 0.6085 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 2.0,    p10: 2.4333, p25: 3.25,   p50: 5.0,     p75: 6.5,    p90: 8.7,    p95: 10.0   },
      damage_per_opening:    { p5: 13.0528,p10: 16.5366,p25: 20.5176,p50: 28.6921, p75: 38.0058,p90: 51.922, p95: 66.4675 },
      avg_kill_percent:      { p5: 65.7735,p10: 81.244, p25: 107.2875,p50: 128.46, p75: 141.25, p90: 159.6065,p95: 165.3346 },
      avg_death_percent:     { p5: 78.7102,p10: 92.1795,p25: 103.4875,p50: 113.4575,p75: 126.6414,p90: 139.5293,p95: 152.8058 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.1658, p10: 0.2,    p25: 0.2662, p50: 0.3333,  p75: 0.433,  p90: 0.6155, p95: 0.8223 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Falco": {
      neutral_win_ratio:     { p5: 0.1222, p10: 0.2625, p25: 0.363,  p50: 0.4791,  p75: 0.5833, p90: 0.6858, p95: 0.8068 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.0,    p10: 2.0,    p25: 2.75,   p50: 3.6667,  p75: 5.125,  p90: 7.6667, p95: 8.0    },
      damage_per_opening:    { p5: 15.6211,p10: 18.0769,p25: 24.485, p50: 31.518,  p75: 41.702, p90: 54.6364,p95: 64.1975 },
      avg_kill_percent:      { p5: 51.33,  p10: 70.1167,p25: 93.2983,p50: 114.3289,p75: 130.913,p90: 147.1925,p95: 157.5762 },
      avg_death_percent:     { p5: 67.4334,p10: 78.9978,p25: 97.66,  p50: 119.1421,p75: 131.97, p90: 149.0647,p95: 156.2467 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0,    p25: 0.5,    p50: 0.7222,  p75: 0.8182, p90: 0.8889, p95: 0.9476 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Fox": {
      neutral_win_ratio:     { p5: 0.2593, p10: 0.3126, p25: 0.3864, p50: 0.4375,  p75: 0.5312, p90: 0.6,    p95: 0.7    },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.25,   p10: 1.75,   p25: 2.75,   p50: 4.0,     p75: 5.25,   p90: 7.0,    p95: 7.0    },
      damage_per_opening:    { p5: 21.7402,p10: 24.5391,p25: 29.48,  p50: 36.7044, p75: 44.7001,p90: 54.473, p95: 57.805 },
      avg_kill_percent:      { p5: 53.215, p10: 78.2325,p25: 96.035, p50: 117.6267,p75: 136.915,p90: 149.4319,p95: 153.57 },
      avg_death_percent:     { p5: 55.825, p10: 71.73,  p25: 81.24,  p50: 106.77,  p75: 133.6927,p90: 145.7525,p95: 153.5742 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0849, p10: 0.3566, p25: 0.5714, p50: 0.6875,  p75: 0.7826, p90: 0.9286, p95: 1.0    },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Ganondorf": {
      neutral_win_ratio:     { p5: 0.125,  p10: 0.2308, p25: 0.3333, p50: 0.45,    p75: 0.5613, p90: 0.6923, p95: 0.8286 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.0,    p10: 1.25,   p25: 1.6667, p50: 2.25,    p75: 3.25,   p90: 4.2,    p95: 5.0    },
      damage_per_opening:    { p5: 24.5824,p10: 26.2307,p25: 32.1271,p50: 44.424,  p75: 65.4454,p90: 88.3199,p95: 110.7882 },
      avg_kill_percent:      { p5: 57.7143,p10: 69.884, p25: 86.7138,p50: 98.9125, p75: 112.5025,p90: 126.9232,p95: 131.1083 },
      avg_death_percent:     { p5: 72.4354,p10: 84.9336,p25: 98.3574,p50: 122.2762,p75: 136.613,p90: 154.451,p95: 166.5233 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0524, p25: 0.3359, p50: 0.6481,  p75: 0.8,    p90: 0.8889, p95: 0.9365 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Ice Climbers": {
      neutral_win_ratio:     { p5: 0.0,    p10: 0.0,    p25: 0.087,  p50: 0.4792,  p75: 0.825,  p90: 1.0,    p95: 1.0    },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.4,    p10: 1.8,    p25: 4.0,    p50: 5.25,    p75: 7.25,   p90: 9.35,   p95: 10.85  },
      damage_per_opening:    { p5: 7.472,  p10: 8.1467, p25: 11.3361,p50: 16.3,    p75: 27.9418,p90: 40.695, p95: 49.0629 },
      avg_kill_percent:      { p5: 46.886, p10: 60.797, p25: 83.7494,p50: 102.8323,p75: 127.6604,p90: 139.2745,p95: 143.603 },
      avg_death_percent:     { p5: 43.668, p10: 75.8268,p25: 92.5469,p50: 114.2925,p75: 136.6562,p90: 143.8314,p95: 162.4585 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0,    p25: 0.0,    p50: 0.3859,  p75: 0.5778, p90: 0.6477, p95: 0.7522 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Jigglypuff": {
      neutral_win_ratio:     { p5: 0.25,   p10: 0.3153, p25: 0.44,   p50: 0.5625,  p75: 0.6875, p90: 0.8055, p95: 0.8961 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.25,   p10: 1.5,    p25: 2.25,   p50: 3.25,    p75: 4.75,   p90: 7.4167, p95: 9.3333 },
      damage_per_opening:    { p5: 7.0583, p10: 17.3917,p25: 23.6654,p50: 31.3431, p75: 43.4683,p90: 56.2781,p95: 76.8616 },
      avg_kill_percent:      { p5: 47.4369,p10: 59.475, p25: 75.595, p50: 95.7075, p75: 120.995,p90: 137.8779,p95: 151.7867 },
      avg_death_percent:     { p5: 75.1733,p10: 83.66,  p25: 95.0569,p50: 110.5271,p75: 126.8113,p90: 140.868,p95: 148.9143 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0,    p25: 0.0,    p50: 0.4603,  p75: 0.7943, p90: 0.9087, p95: 0.9667 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Kirby": {
      neutral_win_ratio:     { p5: 0.084,  p10: 0.2536, p25: 0.3784, p50: 0.6333,  p75: 0.7368, p90: 1.0,    p95: 1.0    },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 0.45,   p10: 1.9,    p25: 4.125,  p50: 5.4167,  p75: 6.25,   p90: 10.1,   p95: 11.0   },
      damage_per_opening:    { p5: 6.6615, p10: 9.4245, p25: 17.1477,p50: 22.4192, p75: 28.1295,p90: 38.0092,p95: 38.8401 },
      avg_kill_percent:      { p5: 10.0,   p10: 36.17,  p25: 64.9801,p50: 101.1833,p75: 123.06, p90: 130.805,p95: 143.0646 },
      avg_death_percent:     { p5: 49.992, p10: 63.573, p25: 103.56, p50: 116.09,  p75: 130.8129,p90: 156.632,p95: 165.864 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0,    p25: 0.0,    p50: 0.2667,  p75: 0.6,    p90: 0.725,  p95: 0.7976 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Link": {
      neutral_win_ratio:     { p5: 0.0316, p10: 0.2786, p25: 0.5294, p50: 0.6538,  p75: 0.7317, p90: 0.8619, p95: 1.0    },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 2.0625, p10: 2.625,  p25: 3.5,    p50: 4.5,     p75: 6.0,    p90: 7.5833, p95: 8.8333 },
      damage_per_opening:    { p5: 13.657, p10: 14.7107,p25: 19.6749,p50: 28.5279, p75: 32.4565,p90: 40.7084,p95: 53.7354 },
      avg_kill_percent:      { p5: 74.6885,p10: 80.9574,p25: 95.2002,p50: 125.3634,p75: 139.1002,p90: 145.8958,p95: 148.8998 },
      avg_death_percent:     { p5: 59.3146,p10: 69.195, p25: 94.9519,p50: 110.4818,p75: 135.4675,p90: 149.4617,p95: 152.9814 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0143, p25: 0.3333, p50: 0.7188,  p75: 0.8966, p90: 0.9675, p95: 0.9713 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Luigi": {
      neutral_win_ratio:     { p5: 0.045,  p10: 0.151,  p25: 0.2652, p50: 0.4,     p75: 0.5564, p90: 0.816,  p95: 1.0    },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 0.5,    p10: 1.0,    p25: 2.0,    p50: 3.3333,  p75: 5.5,    p90: 7.0,    p95: 9.0    },
      damage_per_opening:    { p5: 7.5383, p10: 8.4182, p25: 18.32,  p50: 26.1625, p75: 52.602, p90: 99.9324,p95: 106.2895 },
      avg_kill_percent:      { p5: 7.3395, p10: 20.148, p25: 56.1463,p50: 111.545, p75: 137.3529,p90: 159.4342,p95: 169.9211 },
      avg_death_percent:     { p5: 66.455, p10: 83.7275,p25: 107.9379,p50: 125.5225,p75: 143.9462,p90: 162.1716,p95: 175.8917 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0,    p25: 0.0556, p50: 0.4348,  p75: 0.8043, p90: 0.91,   p95: 0.955  },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Mario": {
      neutral_win_ratio:     { p5: 0.213,  p10: 0.3,    p25: 0.4167, p50: 0.5238,  p75: 0.6154, p90: 0.7143, p95: 0.7916 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.25,   p10: 1.95,   p25: 2.5,    p50: 3.25,    p75: 4.3333, p90: 5.75,   p95: 7.0    },
      damage_per_opening:    { p5: 17.4762,p10: 19.462, p25: 24.9987,p50: 31.8462, p75: 39.8238,p90: 58.465, p95: 71.3963 },
      avg_kill_percent:      { p5: 53.09,  p10: 65.7525,p25: 80.73,  p50: 98.8223, p75: 113.4794,p90: 130.7285,p95: 139.4133 },
      avg_death_percent:     { p5: 63.0,   p10: 77.6567,p25: 91.8525,p50: 115.56,  p75: 135.0393,p90: 149.3167,p95: 159.3813 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0736, p10: 0.3333, p25: 0.6154, p50: 0.7808,  p75: 0.8654, p90: 0.9219, p95: 0.9511 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Marth": {
      neutral_win_ratio:     { p5: 0.3333, p10: 0.4601, p25: 0.4688, p50: 0.6136,  p75: 0.6154, p90: 0.6471, p95: 0.989  },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 2.5,    p10: 3.4833, p25: 4.0,    p50: 5.0,     p75: 6.75,   p90: 6.75,   p95: 6.75   },
      damage_per_opening:    { p5: 6.0615, p10: 21.593, p25: 21.593, p50: 21.7488, p75: 26.1053,p90: 35.7673,p95: 42.2354 },
      avg_kill_percent:      { p5: 85.147, p10: 86.995, p25: 86.995, p50: 127.86,  p75: 145.7525,p90: 145.7525,p95: 145.7525 },
      avg_death_percent:     { p5: 104.7111,p10: 110.7931,p25: 117.6267,p50: 123.715,p75: 141.4192,p90: 182.17,p95: 182.17 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0909, p10: 0.36,   p25: 0.36,   p50: 0.5556,  p75: 0.6364, p90: 0.6929, p95: 0.8571 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Mewtwo": {
      neutral_win_ratio:     { p5: 0.1975, p10: 0.247,  p25: 0.3077, p50: 0.4167,  p75: 0.5,    p90: 0.5466, p95: 0.6    },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.3333, p10: 1.5,    p25: 2.0625, p50: 3.3333,  p75: 4.3333, p90: 6.3333, p95: 8.7833 },
      damage_per_opening:    { p5: 17.6863,p10: 20.031, p25: 29.9846,p50: 36.2315, p75: 49.7681,p90: 61.4365,p95: 74.9763 },
      avg_kill_percent:      { p5: 64.9198,p10: 79.0305,p25: 93.4417,p50: 108.9183,p75: 125.7908,p90: 141.7123,p95: 151.1974 },
      avg_death_percent:     { p5: 87.9401,p10: 97.5588,p25: 107.9467,p50: 122.1713,p75: 145.1835,p90: 156.3959,p95: 165.9634 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0,    p25: 0.0,    p50: 0.2143,  p75: 0.75,   p90: 0.8571, p95: 0.9247 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Ness": {
      neutral_win_ratio:     { p5: 0.1668, p10: 0.2346, p25: 0.4303, p50: 0.6,     p75: 0.6687, p90: 0.8141, p95: 1.0    },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.5,    p10: 2.5,    p25: 3.5,    p50: 4.5,     p75: 7.0,    p90: 9.0,    p95: 10.25  },
      damage_per_opening:    { p5: 6.2024, p10: 7.1255, p25: 16.1074,p50: 25.9881, p75: 35.431, p90: 42.6086,p95: 59.146 },
      avg_kill_percent:      { p5: 69.2015,p10: 81.462, p25: 91.7975,p50: 107.1525,p75: 136.6434,p90: 156.0072,p95: 167.2948 },
      avg_death_percent:     { p5: 45.9457,p10: 52.9737,p25: 91.1667,p50: 111.6547,p75: 134.4282,p90: 147.0155,p95: 155.5498 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0,    p25: 0.0,    p50: 0.2778,  p75: 0.6981, p90: 0.7437, p95: 0.7812 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Peach": {
      neutral_win_ratio:     { p5: 0.1667, p10: 0.2308, p25: 0.3158, p50: 0.4194,  p75: 0.52,   p90: 0.625,  p95: 0.7143 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.25,   p10: 1.5,    p25: 2.5,    p50: 3.6667,  p75: 5.0,    p90: 7.5,    p95: 9.85   },
      damage_per_opening:    { p5: 15.6719,p10: 19.1457,p25: 24.0775,p50: 31.6809, p75: 43.1151,p90: 59.2333,p95: 71.9752 },
      avg_kill_percent:      { p5: 53.7045,p10: 68.24,  p25: 88.34,  p50: 108.7691,p75: 128.81, p90: 151.06, p95: 169.1273 },
      avg_death_percent:     { p5: 62.6152,p10: 74.462, p25: 92.8483,p50: 109.6867,p75: 124.7575,p90: 138.45,p95: 147.1547 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.2,    p25: 0.5116, p50: 0.7143,  p75: 0.84,   p90: 0.9118, p95: 0.9474 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Pichu": {
      neutral_win_ratio:     { p5: 0.1693, p10: 0.222,  p25: 0.3062, p50: 0.467,   p75: 0.6875, p90: 0.8923, p95: 1.0    },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 2.0,    p10: 2.75,   p25: 3.3333, p50: 5.0,     p75: 7.3333, p90: 10.1667,p95: 12.0   },
      damage_per_opening:    { p5: 5.6891, p10: 7.8243, p25: 16.0033,p50: 22.315,  p75: 29.1239,p90: 38.8472,p95: 43.863 },
      avg_kill_percent:      { p5: 32.127, p10: 43.817, p25: 79.572, p50: 98.75,   p75: 130.1027,p90: 147.079,p95: 159.339 },
      avg_death_percent:     { p5: 97.0654,p10: 103.736,p25: 110.515,p50: 131.7842,p75: 137.1268,p90: 150.4585,p95: 166.1525 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.3,    p25: 0.4988, p50: 0.7889,  p75: 0.93,   p90: 1.0,    p95: 1.0    },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Pikachu": {
      neutral_win_ratio:     { p5: 0.2143, p10: 0.2826, p25: 0.3889, p50: 0.5,     p75: 0.625,  p90: 0.7273, p95: 0.7795 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.5,    p10: 1.75,   p25: 2.5,    p50: 3.6667,  p75: 4.6667, p90: 6.0,    p95: 7.0    },
      damage_per_opening:    { p5: 18.0003,p10: 22.5033,p25: 28.5806,p50: 36.1084, p75: 48.6175,p90: 66.0498,p95: 86.788 },
      avg_kill_percent:      { p5: 78.1155,p10: 89.5347,p25: 104.6507,p50: 120.842,p75: 132.0261,p90: 144.348,p95: 155.8115 },
      avg_death_percent:     { p5: 77.935, p10: 88.4353,p25: 104.82, p50: 119.41,  p75: 140.5967,p90: 157.883,p95: 169.036 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0,    p25: 0.2,    p50: 0.5,     p75: 0.6667, p90: 0.8452, p95: 1.0    },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Samus": {
      neutral_win_ratio:     { p5: 0.0,    p10: 0.189,  p25: 0.2614, p50: 0.4096,  p75: 0.6311, p90: 0.7143, p95: 0.7964 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.25,   p10: 1.5833, p25: 2.2708, p50: 4.0,     p75: 5.25,   p90: 8.0,    p95: 8.6667 },
      damage_per_opening:    { p5: 11.7603,p10: 14.2272,p25: 18.7161,p50: 28.2098, p75: 40.1735,p90: 57.0423,p95: 78.533 },
      avg_kill_percent:      { p5: 50.0753,p10: 63.3333,p25: 78.8331,p50: 99.1962, p75: 122.2439,p90: 140.4994,p95: 145.85 },
      avg_death_percent:     { p5: 16.9818,p10: 42.9755,p25: 91.8728,p50: 114.05,  p75: 132.2717,p90: 144.913,p95: 156.2497 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0,    p25: 0.1667, p50: 0.4,     p75: 0.8125, p90: 0.9019, p95: 0.9568 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Sheik": {
      neutral_win_ratio:     { p5: 0.2,    p10: 0.2649, p25: 0.3554, p50: 0.4545,  p75: 0.5625, p90: 0.6473, p95: 0.723  },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.1,    p10: 2.0,    p25: 2.6667, p50: 4.0,     p75: 5.5,    p90: 7.3333, p95: 8.3    },
      damage_per_opening:    { p5: 18.1638,p10: 21.9719,p25: 26.4512,p50: 33.8454, p75: 43.8158,p90: 59.7097,p95: 70.794 },
      avg_kill_percent:      { p5: 61.61,  p10: 83.977, p25: 100.6633,p50: 120.8367,p75: 133.115,p90: 142.3164,p95: 153.042 },
      avg_death_percent:     { p5: 71.5497,p10: 79.0485,p25: 94.0133,p50: 109.155, p75: 127.8162,p90: 143.287,p95: 152.3878 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0,    p25: 0.3,    p50: 0.5,     p75: 0.6819, p90: 0.8324, p95: 0.875  },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Yoshi": {
      neutral_win_ratio:     { p5: 0.0,    p10: 0.15,   p25: 0.2952, p50: 0.4419,  p75: 0.5371, p90: 0.6043, p95: 0.6529 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.35,   p10: 1.5,    p25: 2.125,  p50: 3.0,     p75: 4.125,  p90: 5.6333, p95: 7.9333 },
      damage_per_opening:    { p5: 15.9545,p10: 19.2866,p25: 25.6948,p50: 37.1078, p75: 54.5014,p90: 80.9052,p95: 94.8007 },
      avg_kill_percent:      { p5: 80.7047,p10: 84.078, p25: 98.315, p50: 109.3982,p75: 125.3569,p90: 136.8479,p95: 149.2957 },
      avg_death_percent:     { p5: 58.3631,p10: 65.0927,p25: 88.3737,p50: 110.6127,p75: 124.5943,p90: 143.3503,p95: 155.5627 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.0,    p25: 0.2857, p50: 0.6667,  p75: 0.8016, p90: 1.0,    p95: 1.0    },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Young Link": {
      neutral_win_ratio:     { p5: 0.2143, p10: 0.3043, p25: 0.4375, p50: 0.5556,  p75: 0.6789, p90: 0.7692, p95: 0.828  },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.6667, p10: 2.25,   p25: 3.25,   p50: 4.5,     p75: 6.0,    p90: 8.0,    p95: 10.2   },
      damage_per_opening:    { p5: 15.1042,p10: 17.7052,p25: 22.3867,p50: 28.082,  p75: 37.073, p90: 49.2054,p95: 62.2987 },
      avg_kill_percent:      { p5: 73.7033,p10: 84.3033,p25: 100.76, p50: 117.59,  p75: 134.92, p90: 149.9248,p95: 158.8834 },
      avg_death_percent:     { p5: 47.1476,p10: 62.594, p25: 84.3829,p50: 101.8367,p75: 118.6483,p90: 134.2004,p95: 141.8176 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0769, p10: 0.4372, p25: 0.7,    p50: 0.8235,  p75: 0.8966, p90: 0.9444, p95: 0.9697 },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
    "Zelda": {
      neutral_win_ratio:     { p5: 0.25,   p10: 0.3077, p25: 0.4,    p50: 0.5,     p75: 0.5953, p90: 0.697,  p95: 0.7565 },
      counter_hit_rate:      COUNTER_HIT_PLACEHOLDER,
      openings_per_kill:     { p5: 1.75,   p10: 2.125,  p25: 3.0,    p50: 4.0,     p75: 5.25,   p90: 7.0,    p95: 8.3333 },
      damage_per_opening:    { p5: 17.809, p10: 20.1673,p25: 24.8065,p50: 30.5772, p75: 39.3391,p90: 51.7428,p95: 60.8029 },
      avg_kill_percent:      { p5: 78.4981,p10: 87.805, p25: 101.59, p50: 114.785, p75: 129.0981,p90: 142.4425,p95: 153.6369 },
      avg_death_percent:     { p5: 74.2425,p10: 83.4872,p25: 98.06,  p50: 114.58,  p75: 130.31, p90: 144.7,  p95: 159.8953 },
      defensive_option_rate: DEFENSIVE_RATE_PLACEHOLDER,
      l_cancel_ratio:        { p5: 0.0,    p10: 0.1111, p25: 0.5,    p50: 0.75,    p75: 0.8718, p90: 0.9412, p95: 1.0    },
      inputs_per_minute:     IPM_PLACEHOLDER,
    },
  },
};
