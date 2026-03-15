"""
SQLite persistence layer. One file per user (keyed by connect code).
"""

import sqlite3
from pathlib import Path

DATA_DIR = Path.home() / "Documents" / "Slippi Ranked Stats" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

_SCANNED_DB = DATA_DIR / "scanned.db"


def _connect(path) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def get_scanned_filenames() -> set[str]:
    """Return all .slp filenames that have been processed by scan_directory."""
    conn = _connect(_SCANNED_DB)
    conn.execute("CREATE TABLE IF NOT EXISTS scanned_files (filename TEXT PRIMARY KEY)")
    rows = conn.execute("SELECT filename FROM scanned_files").fetchall()
    conn.close()
    return {r[0] for r in rows}


def mark_files_scanned(filenames: list[str]) -> None:
    """Record filenames as processed so future scans skip them."""
    if not filenames:
        return
    conn = _connect(_SCANNED_DB)
    conn.execute("CREATE TABLE IF NOT EXISTS scanned_files (filename TEXT PRIMARY KEY)")
    conn.executemany(
        "INSERT OR IGNORE INTO scanned_files (filename) VALUES (?)",
        [(f,) for f in filenames],
    )
    conn.commit()
    conn.close()


def seed_scanned_from_existing_dbs() -> None:
    """
    One-time migration: populate scanned.db from all existing per-player DBs
    so users don't have to rescan files that were already processed.
    """
    all_filenames: set[str] = set()
    for db_file in DATA_DIR.glob("*.db"):
        if db_file.name == "scanned.db":
            continue
        try:
            c = _connect(db_file)
            rows = c.execute("SELECT filename FROM games").fetchall()
            all_filenames.update(r[0] for r in rows)
            c.close()
        except Exception:
            pass
    mark_files_scanned(list(all_filenames))

SCHEMA = """
CREATE TABLE IF NOT EXISTS games (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    filename         TEXT    UNIQUE NOT NULL,
    timestamp        TEXT    NOT NULL,
    match_type       TEXT    NOT NULL,
    player_port      INTEGER NOT NULL,
    player_char_id   INTEGER,
    opponent_code    TEXT,
    opponent_char_id INTEGER,
    stage_id         INTEGER,
    result           TEXT    NOT NULL,
    duration_frames  INTEGER,
    match_id         TEXT,
    filepath         TEXT
);

CREATE TABLE IF NOT EXISTS rating_snapshots (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    connect_code  TEXT    NOT NULL,
    timestamp     TEXT    NOT NULL,
    rating        REAL,
    wins          INTEGER,
    losses        INTEGER,
    global_rank   INTEGER,
    regional_rank INTEGER,
    continent     TEXT,
    UNIQUE(connect_code, timestamp)
);

CREATE TABLE IF NOT EXISTS season_history (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    connect_code  TEXT NOT NULL,
    season_id     TEXT,
    season_name   TEXT,
    season_start  TEXT,
    season_end    TEXT,
    rating        REAL,
    wins          INTEGER,
    losses        INTEGER,
    UNIQUE(connect_code, season_id)
);
"""


def _db_path(connect_code: str) -> Path:
    safe = connect_code.upper().replace("#", "_").replace("/", "_")
    return DATA_DIR / f"{safe}.db"


def get_conn(connect_code: str) -> sqlite3.Connection:
    conn = _connect(_db_path(connect_code))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # Migration: add filepath column if it doesn't exist yet (existing DBs)
    try:
        conn.execute("ALTER TABLE games ADD COLUMN filepath TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    return conn


# ---------------------------------------------------------------------------
# Games
# ---------------------------------------------------------------------------

def insert_game(conn: sqlite3.Connection, game: dict) -> bool:
    """Insert a single parsed game. Returns True if new, False if already exists."""
    try:
        conn.execute(
            """
            INSERT INTO games
              (filename, timestamp, match_type, player_port, player_char_id,
               opponent_code, opponent_char_id, stage_id, result, duration_frames, match_id,
               filepath)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                game["filename"],
                game["timestamp"],
                game["match_type"],
                game["player_port"],
                game["player_char_id"],
                game["opponent_code"],
                game["opponent_char_id"],
                game["stage_id"],
                game["result"],
                game["duration_frames"],
                game["match_id"],
                game.get("filepath"),
            ),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # duplicate


def get_known_filenames(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT filename FROM games").fetchall()
    return {r["filename"] for r in rows}


def get_games(
    conn: sqlite3.Connection,
    match_type: str | list[str] = "ranked",
    since: str | None = None,
) -> list[sqlite3.Row]:
    if isinstance(match_type, list):
        placeholders = ",".join("?" * len(match_type))
        query = f"SELECT * FROM games WHERE match_type IN ({placeholders})"
        params: list = list(match_type)
    else:
        query = "SELECT * FROM games WHERE match_type = ?"
        params = [match_type]
    if since:
        query += " AND timestamp >= ?"
        params.append(since)
    query += " ORDER BY timestamp ASC"
    return conn.execute(query, params).fetchall()


# ---------------------------------------------------------------------------
# Rating snapshots
# ---------------------------------------------------------------------------

def upsert_snapshot(conn: sqlite3.Connection, connect_code: str, snap: dict) -> bool:
    """Insert a new rating snapshot. Skips if identical to most recent."""
    last = conn.execute(
        "SELECT rating, wins, losses FROM rating_snapshots "
        "WHERE connect_code = ? ORDER BY timestamp DESC LIMIT 1",
        (connect_code,),
    ).fetchone()
    if last and last["rating"] == snap.get("rating") and last["wins"] == snap.get("wins"):
        return False  # no change
    conn.execute(
        """
        INSERT OR IGNORE INTO rating_snapshots
          (connect_code, timestamp, rating, wins, losses, global_rank, regional_rank, continent)
        VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            connect_code,
            snap["timestamp"],
            snap.get("rating"),
            snap.get("wins"),
            snap.get("losses"),
            snap.get("global_rank"),
            snap.get("regional_rank"),
            snap.get("continent"),
        ),
    )
    conn.commit()
    return True


def get_snapshots(conn: sqlite3.Connection, connect_code: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM rating_snapshots WHERE connect_code = ? ORDER BY timestamp ASC",
        (connect_code,),
    ).fetchall()


# ---------------------------------------------------------------------------
# Season history
# ---------------------------------------------------------------------------

def upsert_seasons(conn: sqlite3.Connection, connect_code: str, seasons: list[dict]) -> None:
    for s in seasons:
        conn.execute(
            """
            INSERT OR REPLACE INTO season_history
              (connect_code, season_id, season_name, season_start, season_end, rating, wins, losses)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                connect_code,
                s.get("season_id"),
                s.get("season_name"),
                s.get("season_start"),
                s.get("season_end"),
                s.get("rating"),
                s.get("wins"),
                s.get("losses"),
            ),
        )
    conn.commit()


def get_season_history(conn: sqlite3.Connection, connect_code: str) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM season_history WHERE connect_code = ? ORDER BY season_start ASC",
        (connect_code,),
    ).fetchall()
