<script lang="ts">
  import { snapshots, seasons, rankedGames, watcherActive } from "../../lib/store";
  import LineChart from "../charts/LineChart.svelte";

  // Rating line data
  let ratingData = $derived($snapshots.map((s) => ({
    x: s.timestamp.slice(0, 16).replace("T", " "),
    y: s.rating,
  })));

  // Season end markers
  let seasonMarkers = $derived($seasons
    .filter((s) => s.rating > 0)
    .map((s) => ({ x: s.season_end?.slice(0, 16)?.replace("T", " ") ?? "", y: s.rating, name: s.season_name })));

  // Rolling 20-game win rate (using all ranked games)
  let rolling = $derived((() => {
    const WINDOW = 20;
    const games = $rankedGames;
    if (games.length < WINDOW) return [];
    return games.slice(WINDOW - 1).map((_, i) => {
      const window = games.slice(i, i + WINDOW);
      const wins = window.filter((g) => g.result === "win" || g.result === "lras_win").length;
      return { x: window.at(-1)!.timestamp.slice(0, 16).replace("T", " "), y: (wins / WINDOW) * 100 };
    });
  })());
</script>

<!-- Current rating + watcher status -->
<div style="display:flex; align-items:center; gap:16px; margin-bottom:16px">
  <div class="stat-card" style="min-width:140px">
    <div class="label">Current Rating</div>
    <div class="value">{$snapshots.at(-1)?.rating.toFixed(1) ?? "—"}</div>
    {#if $snapshots.length >= 2}
      {@const delta = ($snapshots.at(-1)?.rating ?? 0) - ($snapshots.at(0)?.rating ?? 0)}
      <div class="sub" class:win-text={delta >= 0} class:loss-text={delta < 0}>
        {delta >= 0 ? "+" : ""}{delta.toFixed(1)} all-time
      </div>
    {/if}
  </div>
  <span style="font-size:12px; color:var(--muted)">
    {$watcherActive ? "🟢 Watcher active — auto-fetching after new replays" : "⚪ Watcher inactive"}
  </span>
</div>

<!-- Rating over time -->
{#if ratingData.length > 1}
  <div class="card" style="margin-bottom:16px">
    <div class="section-title">Rating Over Time</div>
    <LineChart
      xData={ratingData.map((d) => d.x)}
      yData={ratingData.map((d) => d.y)}
      label="Rating"
      color="#2ecc71"
      fill={false}
      markers={seasonMarkers}
      height={280}
    />
  </div>
{:else}
  <p class="muted" style="margin-bottom:16px">Fetch a rating snapshot to see progression.</p>
{/if}

<!-- Rolling win rate -->
{#if rolling.length > 0}
  <div class="card">
    <div class="section-title">Rolling 20-Game Win Rate</div>
    <LineChart
      xData={rolling.map((d) => d.x)}
      yData={rolling.map((d) => d.y)}
      label="Win %"
      color="#7c3aed"
      fill={true}
      height={200}
    />
  </div>
{/if}
