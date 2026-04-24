<script lang="ts">
  import { sessions, type Session } from "../../lib/store";
  import SessionView from "../SessionView.svelte";

  let selectedSession = $state<Session | null>($sessions.at(-1) ?? null);

  // Keep default selection in sync when sessions load/change
  $effect(() => {
    if (!selectedSession && $sessions.length > 0) {
      selectedSession = $sessions.at(-1)!;
    }
  });

  function fmt(min: number): string {
    const h = Math.floor(min / 60);
    const m = min % 60;
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  }

  let reversedSessions = $derived([...$sessions].reverse());
</script>

{#if $sessions.length === 0}
  <p class="muted" style="padding: 24px">No session data yet — scan replays to get started.</p>
{:else}
  <div style="display: grid; grid-template-columns: 220px 1fr; gap: 0; align-items: start">

    <!-- Session list -->
    <div style="
      border-right: 1px solid var(--border);
      overflow-y: auto;
      max-height: calc(100vh - 160px);
      padding-right: 0;
    ">
      {#each reversedSessions as s, i}
        {@const winPct = s.sets.length > 0 ? (s.setWins / s.sets.length) * 100 : 0}
        {@const isSelected = s === selectedSession}
        <button
          onclick={() => selectedSession = s}
          style="
            width: 100%; text-align: left; padding: 10px 12px;
            background: {isSelected ? 'var(--card)' : 'transparent'};
            border: none;
            border-left: 3px solid {isSelected ? '#7c3aed' : 'transparent'};
            border-bottom: 1px solid var(--border);
            cursor: pointer;
            transition: background 0.1s;
          "
          onmouseenter={(e) => { if (!isSelected) (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg)'; }}
          onmouseleave={(e) => { if (!isSelected) (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; }}
        >
          <div style="font-size: 12px; font-weight: 400; color: var(--muted); margin-bottom: 3px">
            {new Date(s.start).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}
          </div>
          <div style="display: flex; gap: 8px; align-items: center; font-size: 11px; color: var(--muted)">
            <span>
              <span class="win-text">{s.setWins}</span>–<span class="loss-text">{s.setLosses}</span>
            </span>
            <span>{s.sets.length} set{s.sets.length !== 1 ? "s" : ""}</span>
            <span class={winPct >= 50 ? "win-text" : "loss-text"}>{winPct.toFixed(0)}%</span>
          </div>
          <div style="font-size: 10px; color: var(--muted); margin-top: 2px">{fmt(s.durationMin)}</div>
        </button>
      {/each}
    </div>

    <!-- Session detail -->
    <div style="padding-left: 20px; min-width: 0">
      {#if selectedSession}
        <SessionView session={selectedSession} />
      {/if}
    </div>

  </div>
{/if}
