<script lang="ts">
  import { activeSet, liveSessionStartRating, snapshots, sessions, watcherActive } from "../../lib/store";
  import { CHARACTERS, getRankTier } from "../../lib/parser";

  // Rating delta since the watcher session started
  let sessionDelta = $derived(
    $liveSessionStartRating !== null && $snapshots.length > 0
      ? ($snapshots.at(-1)!.rating - $liveSessionStartRating)
      : null
  );

  let currentSession = $derived($sessions.at(-1));

  function fmtDelta(d: number): string {
    return (d >= 0 ? "+" : "") + d.toFixed(1);
  }
</script>

{#if !$watcherActive}
  <p class="muted" style="margin-bottom: 16px">
    Monitoring will begin automatically when a ranked game is detected.
  </p>

{:else}
  <!-- NOW PLAYING card (visible while a set is in progress) -->
  {#if $activeSet}
    {@const oppTier = $activeSet.opponent_tier
      ? { name: $activeSet.opponent_tier, color: getRankTier($activeSet.opponent_rating ?? 0).color }
      : null}
    <div style="
      background: var(--card);
      border: 1px solid var(--border);
      border-left: 3px solid #2ecc71;
      border-radius: 8px;
      padding: 14px 16px;
      margin-bottom: 16px;
    ">
      <div style="font-size: 10px; font-weight: 700; letter-spacing: 0.08em; color: #2ecc71; margin-bottom: 10px">
        NOW PLAYING
      </div>

      <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px">

        <!-- Opponent info -->
        <div>
          <div style="font-size: 18px; font-weight: 700">{$activeSet.opponent_code}</div>
          {#if $activeSet.opponent_rating !== null}
            <div style="font-size: 12px; color: {oppTier?.color ?? 'var(--muted)'}">
              {oppTier?.name ?? ""} &middot; {$activeSet.opponent_rating.toFixed(0)}
            </div>
          {:else}
            <div style="font-size: 12px; color: var(--muted)">Fetching rating…</div>
          {/if}
          {#if $activeSet.opponent_char_id != null}
            <div style="font-size: 12px; color: var(--muted)">
              {CHARACTERS[$activeSet.opponent_char_id] ?? `Char ${$activeSet.opponent_char_id}`}
            </div>
          {/if}
        </div>

        <!-- Score -->
        <div style="text-align: center">
          <div style="font-size: 30px; font-weight: 700; letter-spacing: 4px; line-height: 1">
            <span class="win-text">{$activeSet.games_won}</span>
            <span style="color: var(--muted)">–</span>
            <span class="loss-text">{$activeSet.games_lost}</span>
          </div>
          <div style="font-size: 10px; color: var(--muted); margin-top: 2px">Current Set</div>
        </div>

        <!-- All-time record -->
        <div style="text-align: right">
          {#if $activeSet.all_time_wins + $activeSet.all_time_losses > 0}
            <div style="font-size: 13px">
              All-time:
              <span class="win-text">{$activeSet.all_time_wins}W</span>–<span class="loss-text">{$activeSet.all_time_losses}L</span>
            </div>
            <div style="font-size: 11px; color: var(--muted)">vs this opponent</div>
          {:else}
            <div style="font-size: 13px; color: var(--muted)">First match vs<br/>this opponent</div>
          {/if}
          {#if $activeSet.session_already_faced}
            <div style="font-size: 11px; color: #f39c12; margin-top: 4px">⚠ Rematch this session</div>
          {/if}
        </div>

      </div>
    </div>
  {/if}

  <!-- Session overview -->
  {#if currentSession || sessionDelta !== null}
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr)); gap: 10px; margin-bottom: 16px">
      {#if currentSession}
        <div class="stat-card">
          <div class="label">Session Sets</div>
          <div class="value">
            <span class="win-text">{currentSession.setWins}</span>–<span class="loss-text">{currentSession.setLosses}</span>
          </div>
        </div>
        <div class="stat-card">
          <div class="label">Win Rate</div>
          <div class="value">
            {currentSession.sets.length > 0
              ? ((currentSession.setWins / currentSession.sets.length) * 100).toFixed(1) + "%"
              : "—"}
          </div>
        </div>
      {/if}
      {#if sessionDelta !== null}
        <div class="stat-card">
          <div class="label">Rating Change</div>
          <div class="value" class:win-text={sessionDelta > 0} class:loss-text={sessionDelta < 0}>
            {fmtDelta(sessionDelta)}
          </div>
        </div>
      {/if}
      {#if $liveSessionStartRating !== null}
        <div class="stat-card">
          <div class="label">Session Start</div>
          <div class="value">{$liveSessionStartRating.toFixed(1)}</div>
        </div>
      {/if}
      {#if $snapshots.at(-1)}
        <div class="stat-card">
          <div class="label">Current Rating</div>
          <div class="value">{$snapshots.at(-1)!.rating.toFixed(1)}</div>
          {#if $snapshots.length >= 2}
            {@const delta = $snapshots.at(-1)!.rating - $snapshots.at(0)!.rating}
            <div class="sub" class:win-text={delta >= 0} class:loss-text={delta < 0}>
              {delta >= 0 ? "+" : ""}{delta.toFixed(1)} all-time
            </div>
          {/if}
        </div>
      {/if}
    </div>
  {/if}

{/if}
