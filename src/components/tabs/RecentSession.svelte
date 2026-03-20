<script lang="ts">
  import { sessions, rankedGames } from "../../lib/store";
  import { CHARACTERS, STAGES } from "../../lib/parser";
  import LineChart from "../charts/LineChart.svelte";
  import BarChart from "../charts/BarChart.svelte";

  // Most recent session
  let session = $derived($sessions.at(-1));
  let sessionGames = $derived(session?.sets.flatMap((s) => s.games) ?? []);

  // Characters faced (win rates vs each opponent char)
  let charStats = $derived((() => {
    const m = new Map<number, { wins: number; total: number }>();
    for (const s of session?.sets ?? []) {
      for (const g of s.games) {
        const e = m.get(g.opponent_char_id) ?? { wins: 0, total: 0 };
        e.total++;
        if (g.result === "win" || g.result === "lras_win") e.wins++;
        m.set(g.opponent_char_id, e);
      }
    }
    return [...m.entries()]
      .map(([id, v]) => ({ name: CHARACTERS[id] ?? `Char ${id}`, ...v, pct: (v.wins / v.total) * 100 }))
      .sort((a, b) => b.total - a.total);
  })());

  // Stage stats for this session
  let stageStats = $derived((() => {
    const m = new Map<number, { wins: number; total: number }>();
    for (const g of sessionGames) {
      const e = m.get(g.stage_id) ?? { wins: 0, total: 0 };
      e.total++;
      if (g.result === "win" || g.result === "lras_win") e.wins++;
      m.set(g.stage_id, e);
    }
    return [...m.entries()]
      .map(([id, v]) => ({ name: STAGES[id] ?? `Stage ${id}`, ...v, pct: (v.wins / v.total) * 100 }))
      .sort((a, b) => b.total - a.total);
  })());

  // Momentum data: cumulative W/L balance over games in this session
  let momentumData = $derived((() => {
    let bal = 0;
    return sessionGames.map((g, i) => {
      if (g.result === "win" || g.result === "lras_win") bal++;
      else bal--;
      return { x: i + 1, y: bal };
    });
  })());

  function fmt(min: number): string {
    const h = Math.floor(min / 60);
    const m = min % 60;
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  }
</script>

{#if !session}
  <p class="muted" style="padding: 24px">No session data yet — scan replays to get started.</p>
{:else}
  <!-- Session summary cards -->
  <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(120px,1fr)); gap:10px; margin-bottom:16px">
    <div class="stat-card">
      <div class="label">Duration</div>
      <div class="value">{fmt(session.durationMin)}</div>
    </div>
    <div class="stat-card">
      <div class="label">Sets</div>
      <div class="value">{session.sets.length}</div>
    </div>
    <div class="stat-card">
      <div class="label">Games</div>
      <div class="value">{sessionGames.length}</div>
    </div>
    <div class="stat-card">
      <div class="label">Set W/L</div>
      <div class="value">
        <span class="win-text">{session.setWins}</span>
        –
        <span class="loss-text">{session.setLosses}</span>
      </div>
    </div>
    <div class="stat-card">
      <div class="label">Set Win %</div>
      <div class="value">
        {session.sets.length > 0
          ? ((session.setWins / session.sets.length) * 100).toFixed(1) + "%"
          : "—"}
      </div>
    </div>
  </div>

  <!-- Sets list -->
  <div class="section-title">Sets This Session</div>
  <div class="card" style="margin-bottom:16px; padding:0; overflow:hidden">
    <table>
      <thead>
        <tr>
          <th>Result</th>
          <th>Opponent</th>
          <th>Score</th>
          <th>Characters</th>
          <th>Stages</th>
        </tr>
      </thead>
      <tbody>
        {#each session.sets as s}
          <tr>
            <td>
              <span class={s.result === "win" ? "win-text" : "loss-text"}>
                {s.result === "win" ? "Win" : "Loss"}
              </span>
            </td>
            <td>{s.opponent_code}</td>
            <td>{s.wins}–{s.losses}</td>
            <td>
              {s.opponent_char_ids.map((id) => CHARACTERS[id] ?? id).join(", ")}
            </td>
            <td>
              {s.stage_ids.map((id) => STAGES[id] ?? id).join(", ")}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>

  <!-- Charts row -->
  <div style="display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-bottom:16px">
    {#if charStats.length > 0}
      <div class="card">
        <div class="section-title">Characters Faced</div>
        <BarChart
          categories={charStats.map((c) => c.name)}
          values={charStats.map((c) => c.pct)}
          label="Win %"
          horizontal={true}
          paired={true}
        />
      </div>
    {/if}

    {#if stageStats.length > 0}
      <div class="card">
        <div class="section-title">Stage Win %</div>
        <BarChart
          categories={stageStats.map((s) => s.name)}
          values={stageStats.map((s) => s.pct)}
          label="Win %"
          horizontal={true}
          paired={true}
        />
      </div>
    {/if}
  </div>

  <!-- Momentum chart -->
  {#if momentumData.length > 1}
    <div class="card">
      <div class="section-title">Momentum</div>
      <LineChart
        xData={momentumData.map((d) => d.x)}
        yData={momentumData.map((d) => d.y)}
        label="W/L Balance"
        color="#2ecc71"
        fill={true}
        height={200}
      />
    </div>
  {/if}
{/if}
