<script lang="ts">
  import { rankedGames, sets } from "../../lib/store";
  import BarChart from "../charts/BarChart.svelte";

  const MIN_GAMES_HOUR = 3;

  // Set stats
  let totalSets = $derived($sets.length);
  let setWins = $derived($sets.filter((s) => s.result === "win").length);
  let setLosses = $derived(totalSets - setWins);
  let setWinPct = $derived(totalSets > 0 ? (setWins / totalSets) * 100 : 0);

  // Game stats
  let totalGames = $derived($rankedGames.length);
  let gameWins = $derived($rankedGames.filter((g) => g.result === "win" || g.result === "lras_win").length);
  let gameLosses = $derived(totalGames - gameWins);
  let gameWinPct = $derived(totalGames > 0 ? (gameWins / totalGames) * 100 : 0);

  // Comeback rate: sets won after losing game 1
  let comebackRate = $derived((() => {
    const lostG1 = $sets.filter((s) => {
      const g1 = s.games[0];
      return g1 && (g1.result === "loss" || g1.result === "lras_loss");
    });
    if (lostG1.length === 0) return null;
    const won = lostG1.filter((s) => s.result === "win").length;
    return { pct: (won / lostG1.length) * 100, won, total: lostG1.length };
  })());

  // Deciding game win %: win rate in game 3 of sets with exactly 3 games
  let decidingRate = $derived((() => {
    const went3 = $sets.filter((s) => s.games.length === 3);
    if (went3.length === 0) return null;
    const won = went3.filter((s) => s.result === "win").length;
    return { pct: (won / went3.length) * 100, won, total: went3.length };
  })());

  // Time-of-day win % by hour
  let hourStats = $derived((() => {
    const m = new Map<number, { wins: number; total: number }>();
    for (const g of $rankedGames) {
      const hour = new Date(g.timestamp).getHours();
      const e = m.get(hour) ?? { wins: 0, total: 0 };
      e.total++;
      if (g.result === "win" || g.result === "lras_win") e.wins++;
      m.set(hour, e);
    }
    return [...m.entries()]
      .filter(([, v]) => v.total >= MIN_GAMES_HOUR)
      .map(([h, v]) => ({
        hour: `${h}:00`,
        wins: v.wins,
        total: v.total,
        pct: (v.wins / v.total) * 100,
      }))
      .sort((a, b) => parseInt(a.hour) - parseInt(b.hour));
  })());
</script>

<!-- Summary cards row -->
<div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(150px,1fr)); gap:12px; margin-bottom:16px">
  <div class="stat-card">
    <div class="label">Set Win %</div>
    <div class="value">{setWinPct.toFixed(1)}%</div>
    <div class="sub">{setWins}W – {setLosses}L ({totalSets} sets)</div>
  </div>

  <div class="stat-card">
    <div class="label">Game Win %</div>
    <div class="value">{gameWinPct.toFixed(1)}%</div>
    <div class="sub">{gameWins}W – {gameLosses}L ({totalGames} games)</div>
  </div>

  {#if comebackRate}
    <div class="stat-card">
      <div class="label">Comeback Rate</div>
      <div class="value">{comebackRate.pct.toFixed(1)}%</div>
      <div class="sub">{comebackRate.won}/{comebackRate.total} sets after losing G1</div>
    </div>
  {/if}

  {#if decidingRate}
    <div class="stat-card">
      <div class="label">Deciding Game Win %</div>
      <div class="value">{decidingRate.pct.toFixed(1)}%</div>
      <div class="sub">{decidingRate.won}/{decidingRate.total} game 3s</div>
    </div>
  {/if}
</div>

<!-- Time of day chart -->
{#if hourStats.length > 0}
  <div class="card">
    <div class="section-title">Win % by Time of Day (min {MIN_GAMES_HOUR} games per hour)</div>
    <BarChart
      categories={hourStats.map((h) => `${h.hour} (${h.total})`)}
      values={hourStats.map((h) => h.pct)}
      label="Win %"
      color="#2ecc71"
      horizontal={false}
    />
  </div>
{:else}
  <p class="muted">Not enough data yet for time-of-day analysis.</p>
{/if}
