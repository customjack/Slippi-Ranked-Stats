<script lang="ts">
  import Sidebar from "./components/Sidebar.svelte";
  import Header from "./components/Header.svelte";
  import RecentSession from "./components/tabs/RecentSession.svelte";
  import MatchupStats from "./components/tabs/MatchupStats.svelte";
  import StageStats from "./components/tabs/StageStats.svelte";
  import RatingProgression from "./components/tabs/RatingProgression.svelte";
  import AllTimeStats from "./components/tabs/AllTimeStats.svelte";
  import { activeTab, connectCode, replayDir, games, snapshots, seasons, isScanning, scanProgress, statusMessage } from "./lib/store";
  import { getDb, getGames, getSnapshots, getSeasons } from "./lib/db";
  import { scanDirectory } from "./lib/parser";
  import { onMount } from "svelte";
  import { check } from "@tauri-apps/plugin-updater";
  import { relaunch } from "@tauri-apps/plugin-process";
  import { get } from "svelte/store";

  let updateAvailable = $state(false);
  let updateVersion = $state("");
  let isUpdating = $state(false);
  let updateError = $state("");

  onMount(async () => {
    // Check for updates
    try {
      const update = await check();
      if (update?.available) {
        updateAvailable = true;
        updateVersion = update.version;
      }
    } catch {
      // Silently ignore — no network or no release yet
    }

    // Load saved data and auto-scan on startup
    const code = get(connectCode);
    const dir = get(replayDir);
    if (!code) return;

    try {
      const db = await getDb(code);

      // Load existing data from DB immediately so stats show right away
      const loadedGames = await getGames(db);
      games.set(loadedGames);
      const loadedSnaps = await getSnapshots(db, code);
      snapshots.set(loadedSnaps);
      const loadedSeasons = await getSeasons(db, code);
      seasons.set(loadedSeasons);

      // Auto-scan for new replays if a folder is configured
      if (dir) {
        isScanning.set(true);
        scanProgress.set(null);
        statusMessage.set("Auto-scanning for new replays…");
        try {
          const { gamesInserted } = await scanDirectory(dir, code, db, (p) => scanProgress.set(p));
          if (gamesInserted > 0) {
            const refreshed = await getGames(db);
            games.set(refreshed);
          }
          statusMessage.set(gamesInserted > 0 ? `Auto-scan found ${gamesInserted} new game(s).` : "");
        } catch {
          statusMessage.set("");
        } finally {
          isScanning.set(false);
          scanProgress.set(null);
        }
      }
    } catch {
      // DB not ready yet — user hasn't scanned before
    }
  });

  async function installUpdate() {
    isUpdating = true;
    updateError = "";
    try {
      const update = await check();
      if (update?.available) {
        await update.downloadAndInstall();
        await relaunch();
      }
    } catch (e: any) {
      updateError = e?.message ?? String(e);
      isUpdating = false;
    }
  }

  const TABS = [
    { label: "⚡ Last Session" },
    { label: "🎮 Matchup Stats" },
    { label: "🗺️ Stage Stats" },
    { label: "📊 All-Time" },
    { label: "📈 Rating Progression" },
  ];
</script>

<div class="layout">
  <Sidebar />

  <div class="main">
    {#if updateAvailable}
      <div style="background:#f39c12; color:#000; padding:8px 16px; display:flex; align-items:center; gap:12px; font-size:13px; font-weight:600">
        <span>Update available: v{updateVersion}</span>
        <button
          onclick={installUpdate}
          disabled={isUpdating}
          style="background:#000; color:#f39c12; border:none; padding:4px 12px; border-radius:4px; cursor:pointer; font-weight:700; font-size:12px"
        >
          {isUpdating ? "Installing…" : "Install & Restart"}
        </button>
        {#if updateError}
          <span style="color:#c0392b">{updateError}</span>
        {/if}
      </div>
    {/if}
    <Header />

    <div class="tabs">
      {#each TABS as tab, i}
        <button
          class="tab-btn"
          class:active={$activeTab === i}
          onclick={() => activeTab.set(i)}
        >
          {tab.label}
        </button>
      {/each}
    </div>

    <div class="tab-content">
      {#if $activeTab === 0}
        <RecentSession />
      {:else if $activeTab === 1}
        <MatchupStats />
      {:else if $activeTab === 2}
        <StageStats />
      {:else if $activeTab === 3}
        <AllTimeStats />
      {:else if $activeTab === 4}
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:300px; gap:12px">
          <div style="font-size:48px">📈</div>
          <div style="font-size:22px; font-weight:700; color:var(--text)">Rating Progression</div>
          <div style="font-size:14px; color:var(--muted)">Coming Soon!</div>
        </div>
      {/if}
    </div>
  </div>
</div>
