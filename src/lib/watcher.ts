import { watch, type UnwatchFn } from "@tauri-apps/plugin-fs";
import type Database from "@tauri-apps/plugin-sql";
import { parseSlpFile } from "./parser";
import {
  insertGame,
  getGames,
  insertSnapshot,
  getSnapshots,
  insertSeason,
  getSeasons,
  markFilesScanned,
} from "./db";
import { fetchRatingSnapshot } from "./api";
import { games, snapshots, seasons, watcherActive } from "./store";

let _unwatch: UnwatchFn | null = null;
let _snapshotTimer: ReturnType<typeof setTimeout> | null = null;

export async function startWatcher(
  dir: string,
  connectCode: string,
  db: Database
): Promise<void> {
  if (_unwatch) return; // already running

  _unwatch = await watch(
    dir,
    async (event) => {
      // Only care about file creation events (type can be a string like "any" or an object)
      if (typeof event.type === "string" || !("create" in event.type)) return;

      const newSlpPaths = event.paths.filter((p) => p.endsWith(".slp"));
      if (newSlpPaths.length === 0) return;

      let addedRanked = false;
      const scanned: string[] = [];

      for (const filepath of newSlpPaths) {
        try {
          const parsed = await parseSlpFile(filepath, connectCode);
          for (const g of parsed) {
            await insertGame(db, g);
            if (g.match_type === "ranked") addedRanked = true;
          }
          scanned.push(filepath.split(/[/\\]/).pop()!);
        } catch {
          // Skip files that can't be parsed (still mark them scanned)
          scanned.push(filepath.split(/[/\\]/).pop()!);
        }
      }

      // Mark files as scanned so they're skipped on next manual scan
      await markFilesScanned(scanned.filter(Boolean));

      // Refresh the games store
      const loaded = await getGames(db);
      games.set(loaded);

      // If a ranked game was detected, wait 60s then fetch a fresh snapshot
      if (addedRanked) {
        scheduleSnapshotFetch(connectCode, db);
      }
    },
    { recursive: true }
  );

  watcherActive.set(true);
}

export async function stopWatcher(): Promise<void> {
  if (_unwatch) {
    _unwatch();
    _unwatch = null;
  }
  if (_snapshotTimer) {
    clearTimeout(_snapshotTimer);
    _snapshotTimer = null;
  }
  watcherActive.set(false);
}

// Debounced: if multiple ranked games come in rapid succession (e.g. set
// ending), we only fetch one snapshot after the last one settles.
function scheduleSnapshotFetch(connectCode: string, db: Database): void {
  if (_snapshotTimer) clearTimeout(_snapshotTimer);
  _snapshotTimer = setTimeout(async () => {
    _snapshotTimer = null;
    try {
      const { snapshot: snap, seasons: fetchedSeasons } = await fetchRatingSnapshot(connectCode);
      await insertSnapshot(db, { ...snap, connect_code: connectCode });

      for (const s of fetchedSeasons) {
        await insertSeason(db, { ...s, connect_code: connectCode });
      }

      const loadedSnaps = await getSnapshots(db, connectCode);
      snapshots.set(loadedSnaps);
      const loadedSeasons = await getSeasons(db, connectCode);
      seasons.set(loadedSeasons);
    } catch {
      // Silently fail — user can always manually fetch the snapshot
    }
  }, 60_000);
}
