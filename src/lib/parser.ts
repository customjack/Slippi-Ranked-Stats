import { readFile, readDir } from "@tauri-apps/plugin-fs";
import { parseSlpBytes } from "./slp_parser";
import { getScannedFilenames, markFilesScanned, insertGame, type GameRow } from "./db";
import type Database from "@tauri-apps/plugin-sql";

// ── Lookup tables ──────────────────────────────────────────────────────────
// .slp metadata uses Melee's INTERNAL character IDs (CSS selection order).
// These differ from slippi-js's external enum — verified empirically via v1 Python.
// Key difference: Falco=22, Young Link=20 (internal) vs Falco=20 (external).

export const CHARACTERS: Record<number, string> = {
  0:  "Mario",             1:  "Fox",        2:  "Captain Falcon", 3:  "Donkey Kong",
  4:  "Kirby",             5:  "Bowser",     6:  "Link",           7:  "Sheik",
  8:  "Ness",              9:  "Peach",      10: "Ice Climbers",   12: "Pikachu",
  13: "Samus",             14: "Yoshi",      15: "Jigglypuff",     16: "Mewtwo",
  17: "Luigi",             18: "Marth",      19: "Zelda",          20: "Young Link",
  21: "Dr. Mario",         22: "Falco",      23: "Pichu",          24: "Mr. Game & Watch",
  25: "Ganondorf",         26: "Roy",
};

// Stage IDs from the Game Start event (0x36), matching v1 empirical values.
export const STAGES: Record<number, string> = {
  2:  "Fountain of Dreams", 3:  "Pokémon Stadium",   4:  "Kongo Jungle N64",
  5:  "Jungle Japes",       6:  "Great Bay",          7:  "Hyrule Temple",
  8:  "Yoshi's Story",      9:  "Yoshi's Island",     12: "Mushroom Kingdom",
  13: "Brinstar",           14: "Onett",              15: "Mute City",
  20: "Corneria",           22: "Yoshi's Island N64", 24: "Mushroom Kingdom II",
  28: "Dream Land N64",     31: "Battlefield",        32: "Final Destination",
};

// ── Rank tiers ─────────────────────────────────────────────────────────────

const RANK_TIERS = [
  { name: "Grandmaster", min: 2359.10, color: "#ff4444" },
  { name: "Master III",  min: 2296.59, color: "#b44fff" },
  { name: "Master II",   min: 2232.49, color: "#b44fff" },
  { name: "Master I",    min: 2165.25, color: "#b44fff" },
  { name: "Diamond III", min: 2098.01, color: "#a78bfa" },
  { name: "Diamond II",  min: 2026.37, color: "#a78bfa" },
  { name: "Diamond I",   min: 1950.01, color: "#a78bfa" },
  { name: "Platinum III",min: 1878.68, color: "#22d3ee" },
  { name: "Platinum II", min: 1800.01, color: "#22d3ee" },
  { name: "Platinum I",  min: 1716.15, color: "#22d3ee" },
  { name: "Gold III",    min: 1625.45, color: "#fbbf24" },
  { name: "Gold II",     min: 1530.76, color: "#fbbf24" },
  { name: "Gold I",      min: 1430.73, color: "#fbbf24" },
  { name: "Silver III",  min: 1322.69, color: "#94a3b8" },
  { name: "Silver II",   min: 1188.76, color: "#94a3b8" },
  { name: "Silver I",    min: 1055.50, color: "#94a3b8" },
  { name: "Bronze III",  min: 913.72,  color: "#cd7f32" },
  { name: "Bronze II",   min: 765.42,  color: "#cd7f32" },
  { name: "Bronze I",    min: 0,       color: "#cd7f32" },
] as const;

export function getRankTier(rating: number): { name: string; color: string } {
  return RANK_TIERS.find((t) => rating >= t.min) ?? { name: "Unranked", color: "#666" };
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface ParsedGame {
  filename: string;
  filepath: string;
  timestamp: string;
  match_type: string;
  player_port: number;
  player_char_id: number;
  opponent_code: string;
  opponent_char_id: number;
  stage_id: number;
  result: string; // "win" | "loss" | "lras_win" | "lras_loss"
  duration_frames: number;
  match_id: string;
}

export interface ScanProgress {
  scanned: number;
  total: number;
  alreadyProcessed: number;
}

// ── Main scan ──────────────────────────────────────────────────────────────

export interface ScanResult {
  filesScanned: number;
  gamesInserted: number;
  totalSlpFound: number;
  debugPath: string;
  firstError: string | null;
}

export async function scanDirectory(
  dirPath: string,
  connectCode: string,
  db: Database,
  onProgress?: (p: ScanProgress) => void
): Promise<ScanResult> {
  const slpFiles = await collectSlpFiles(dirPath);
  const already = await getScannedFilenames();

  const toProcess = slpFiles.filter((f) => !already.has(f.name));
  const alreadyCount = slpFiles.length - toProcess.length;

  let scanned = 0;
  let gamesInserted = 0;
  const newlyScanned: string[] = [];
  const debugPath = dirPath;
  let firstError: string | null = null;

  // Process in batches — keep concurrency low to avoid flooding the Rust IPC
  // layer with simultaneous readFile calls (causes heap corruption at 50+).
  // DB writes are serialized after each batch so tauri-plugin-sql isn't hit
  // concurrently from multiple tasks.
  const CONCURRENCY = 8;

  for (let i = 0; i < toProcess.length; i += CONCURRENCY) {
    const batch = toProcess.slice(i, i + CONCURRENCY);

    // Parse files concurrently (bounded by CONCURRENCY)
    const results = await Promise.all(
      batch.map(async (entry) => {
        try {
          const games = await parseSlpFile(entry.path, connectCode);
          return { name: entry.name, games, error: null };
        } catch (e: any) {
          return { name: entry.name, games: [], error: String(e?.message ?? e) };
        }
      })
    );

    // Write to DB serially — tauri-plugin-sql doesn't support concurrent writes
    for (const r of results) {
      if (r.error) {
        if (!firstError) firstError = r.error;
        // do NOT mark as scanned so they can be retried
        continue;
      }
      for (const g of r.games) {
        await insertGame(db, g);
        gamesInserted++;
      }
      newlyScanned.push(r.name);
    }

    scanned += batch.length;
    onProgress?.({ scanned, total: toProcess.length, alreadyProcessed: alreadyCount });
  }

  await markFilesScanned(newlyScanned);
  return { filesScanned: newlyScanned.length, gamesInserted, totalSlpFound: slpFiles.length, debugPath, firstError };
}

// ── File collection ────────────────────────────────────────────────────────

interface FileEntry {
  name: string;
  path: string;
}

async function walkDir(dirPath: string, results: FileEntry[], isRoot = false): Promise<void> {
  try {
    const entries = await readDir(dirPath);
    for (const entry of entries) {
      if (entry.isDirectory) {
        await walkDir(`${dirPath}/${entry.name}`, results);
      } else if (entry.name?.endsWith(".slp")) {
        results.push({ name: entry.name, path: `${dirPath}/${entry.name}` });
      }
    }
  } catch (e) {
    if (isRoot) throw e; // surface errors on the root dir so the caller can report them
    // Skip unreadable subdirectories silently
  }
}

async function collectSlpFiles(dirPath: string): Promise<FileEntry[]> {
  const results: FileEntry[] = [];
  await walkDir(dirPath, results, true);
  return results;
}

// ── Single file parse ──────────────────────────────────────────────────────

export async function parseSlpFile(
  filepath: string,
  connectCode: string
): Promise<Omit<GameRow, "id">[]> {
  const bytes = await readFile(filepath);
  return parseSlpBytes(bytes, filepath, connectCode);
}
