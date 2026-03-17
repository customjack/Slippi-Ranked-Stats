"""
Slippi Ranked Stats
"""

import os
import queue
import threading
import time as _time
import tkinter as tk
from tkinter import filedialog
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import api
import db
import replay_parser
from replay_parser import character_name, stage_name

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_SLIPPI_DIR = str(Path.home() / "Documents" / "Slippi")
_SAVED_CODE_FILE = db.DATA_DIR / "last_connect_code.txt"


def _load_saved_code() -> str:
    try:
        return _SAVED_CODE_FILE.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _save_code(code: str) -> None:
    _SAVED_CODE_FILE.write_text(code, encoding="utf-8")
ACCENT      = "#2d872d"   # Slippi signature green (header bar)
WIN_COLOR   = "#2ecc71"   # win bars / positive indicators
BG          = "#1e1e1e"   # main dark background
PAPER       = "#2b2b2b"   # chart / card background
SIDEBAR     = "#141414"   # sidebar near-black
THEME       = "plotly_dark"

# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Slippi Ranked Stats",
    page_icon=Image.open(Path(__file__).parent / "Slippi Ranked Stats Crest.png"),
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Rubik:wght@400;500;700&display=swap');

html, body { font-family: 'Rubik', sans-serif; }

/* ── Page & sidebar ───────────────────────────────────── */
.stApp { background-color: #1e1e1e; }
[data-testid="stSidebar"] { background-color: #141414; }
[data-testid="stSidebar"] hr { border-color: #333; }
/* Always show the collapse arrow when sidebar is open */
[data-testid="stSidebarCollapseButton"]         { display: flex !important; opacity: 1 !important; visibility: visible !important; }
[data-testid="stSidebarCollapseButton"]:hover   { background-color: #2d0a4e !important; }

/* ── Header: hide clutter, keep sidebar toggle ─ */
#MainMenu                              { display: none !important; }
[data-testid="stAppDeployButton"]      { display: none !important; }
[data-testid="stStatusWidget"]         { display: none !important; }
footer                                 { display: none !important; }
[data-testid="stHeader"]               { background-color: #0e0618 !important; }
/* Sidebar toggle styling */
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"]        { background-color: #2d0a4e !important; border-radius: 0 6px 6px 0; }
[data-testid="collapsedControl"]:hover,
[data-testid="stSidebarCollapsedControl"]:hover  { background-color: #3d1468 !important; }

/* ── Hide section anchor link icons ──────────────────── */
[data-testid="stHeaderActionElements"] { display: none !important; }

/* ── Tabs ─────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    background-color: #141414;
    border-radius: 8px 8px 0 0;
    padding: 6px 6px 0 6px;
    gap: 4px;
    border-bottom: 2px solid #2d0a4e;
}
.stTabs [data-baseweb="tab"] {
    background-color: transparent;
    color: #777;
    border-radius: 6px 6px 0 0;
    padding: 8px 22px;
    font-weight: 500;
    font-size: 0.88rem;
    border: none;
    transition: color 0.15s;
}
.stTabs [data-baseweb="tab"]:hover             { color: #ccc; }
.stTabs [aria-selected="true"]                 { color: #c084fc !important; background-color: #1e1e1e !important; }
.stTabs [data-baseweb="tab-highlight"]         { background-color: #7c3aed !important; height: 2px; }
.stTabs [data-baseweb="tab-border"]            { display: none; }

/* ── Metrics ──────────────────────────────────────────── */
.stMetric label { font-size: 0.75rem; color: #aaa; }

/* ── Responsive stat card grid ────────────────────────── */
.stat-card-row { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 4px; }
.stat-card-row > div { flex: 1 1 120px; min-width: 100px; }

@media (max-width: 900px) {
    .stat-card-row > div      { flex: 1 1 90px; }
    [data-testid="stSidebar"] { min-width: 220px !important; }
}


/* ── Overflow guard ───────────────────────────────────── */
[data-testid="stPlotlyChart"],
[data-testid="stDataFrame"] { max-width: 100%; overflow-x: auto; }
</style>
<script>
(function() {
    function expandSidebar() {
        var btn = document.querySelector('[data-testid="stSidebarCollapsedControl"]');
        if (btn) { btn.click(); return true; }
        return false;
    }
    // Retry until the element is available (Streamlit renders async)
    var attempts = 0;
    var interval = setInterval(function() {
        if (expandSidebar() || ++attempts > 20) clearInterval(interval);
    }, 100);
})();
</script>
""", unsafe_allow_html=True)

st.markdown(
    '<a href="https://www.patreon.com/joeydonuts" target="_blank" style="'
    'position:fixed;top:10px;right:16px;z-index:999999;'
    'display:flex;align-items:center;gap:7px;'
    'background:#000000;color:#ffffff;'
    'font-family:Rubik,sans-serif;font-size:1.1rem;font-weight:600;'
    'text-decoration:none;padding:11px 20px;border-radius:6px;opacity:0.92;">'
    '<svg role="img" xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="white">'
    '<path d="M22.957 7.21c-.004-3.064-2.391-5.576-5.191-6.482-3.478-1.125-8.064-.962-11.384.604C2.357 3.231 1.093 7.391 1.046 11.54c-.039 3.411.302 12.396 5.369 12.46 3.765.047 4.326-4.804 6.068-7.141 1.24-1.662 2.836-2.132 4.801-2.618 3.376-.836 5.678-3.501 5.673-7.031Z"/>'
    '</svg>Support on Patreon</a>',
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("Slippi Ranked Stats")
    st.markdown("---")

    connect_code = st.text_input(
        "Connect Code",
        value=_load_saved_code(),
        placeholder="e.g. JOEY#870",
        help="Your Slippi connect code.",
    ).strip().upper().replace("/", "#")

    if connect_code:
        _save_code(connect_code)

    if st.button("📁 Browse for Replay Folder", width='stretch'):
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        chosen = filedialog.askdirectory(title="Select Slippi Replay Folder")
        root.destroy()
        if chosen:
            st.session_state["replay_dir"] = chosen

    replay_dir = st.text_input(
        "Replay Directory",
        value=st.session_state.get("replay_dir", DEFAULT_SLIPPI_DIR),
        help="Path to your Slippi replays folder.",
    ).strip()
    st.session_state["replay_dir"] = replay_dir

    date_range = st.selectbox(
        "Date Range",
        ["Last 30 Days", "Last 90 Days", "All Time"],
        index=2,
    )

    st.markdown("---")
    scan_btn   = st.button("📂 Scan Replays", width='stretch')
    fetch_btn  = st.button("📡 Fetch Rating Snapshot", width='stretch')
    st.caption("Scan reads new .slp files from your replay folder. "
               "Fetch Rating calls the Slippi API (once per click).")

    st.markdown("---")
    with st.expander("🔒 Privacy & Security"):
        st.caption(
            "**What this app does:**\n"
            "- Reads your .slp files locally — replays never leave your computer\n"
            "- Sends your connect code to slippi.gg's API to fetch your rating\n"
            "- Saves your stats to **Documents/Slippi Ranked Stats/** on your PC\n\n"
            "**What this app does NOT do:**\n"
            "- Upload your replays or personal data anywhere\n"
            "- Connect to any server other than slippi.gg\n"
            "- Require an account, login, or internet connection to view stats"
        )


if not connect_code:
    st.title("Slippi Ranked Stats")
    st.info("Enter your connect code in the sidebar to get started.")
    st.stop()

# ---------------------------------------------------------------------------
# Database connection
# ---------------------------------------------------------------------------

_conn_key = f"db_conn_{connect_code}"
if _conn_key not in st.session_state:
    st.session_state[_conn_key] = db.get_conn(connect_code)
conn = st.session_state[_conn_key]

# ---------------------------------------------------------------------------
# Background watcher
# ---------------------------------------------------------------------------

def _is_ranked_replay(path: Path) -> bool:
    """Quick header check — avoids full parse just to filter match type."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(4096)
        return b"mode.ranked" in chunk
    except Exception:
        return False


def _watcher_loop(
    replay_dir: str,
    connect_code: str,
    result_queue: "queue.Queue[dict]",
    stop_event: threading.Event,
) -> None:
    """
    Polls the replay directory every 30 s for new ranked games.
    When found, waits 60 s for Slippi's servers to update the rating,
    then fetches one API snapshot and puts it on the result queue.
    """
    known = {p.name for p in Path(replay_dir).rglob("*.slp")}
    while not stop_event.wait(30):
        try:
            current = {p.name for p in Path(replay_dir).rglob("*.slp")}
            new_names = current - known
            if new_names:
                known = current
                new_paths = [
                    p for p in Path(replay_dir).rglob("*.slp")
                    if p.name in new_names
                ]
                if any(_is_ranked_replay(p) for p in new_paths):
                    # Give Slippi's servers time to settle the rating
                    if stop_event.wait(60):
                        break
                    result = api.fetch_player_profile(connect_code)
                    if result and "error" not in result:
                        result_queue.put(result)
        except Exception:
            pass


def _start_watcher(replay_dir: str, connect_code: str) -> None:
    """Start the background watcher thread if not already running."""
    key = f"watcher_{connect_code}"
    thread: threading.Thread | None = st.session_state.get(key)
    if thread and thread.is_alive():
        return

    q: queue.Queue = queue.Queue()
    stop = threading.Event()
    t = threading.Thread(
        target=_watcher_loop,
        args=(replay_dir, connect_code, q, stop),
        daemon=True,
    )
    t.start()
    st.session_state[key] = t
    st.session_state["watcher_queue"] = q
    st.session_state["watcher_stop"] = stop


def _drain_watcher_queue() -> int:
    """Save any snapshots the watcher queued. Returns count saved."""
    q: queue.Queue | None = st.session_state.get("watcher_queue")
    if not q:
        return 0
    saved = 0
    while True:
        try:
            result = q.get_nowait()
            if db.upsert_snapshot(conn, connect_code, result["snapshot"]):
                saved += 1
            db.upsert_seasons(conn, connect_code, result["seasons"])
        except queue.Empty:
            break
    return saved


# Start watcher if replay dir exists
if os.path.isdir(replay_dir):
    _start_watcher(replay_dir, connect_code)

# Surface any auto-captured snapshots
auto_saved = _drain_watcher_queue()
if auto_saved:
    st.toast(f"📡 Rating snapshot auto-captured ({auto_saved} new)!")

# ---------------------------------------------------------------------------
# Scan replays
# ---------------------------------------------------------------------------

if scan_btn:
    if not os.path.isdir(replay_dir):
        st.sidebar.error(f"Directory not found:\n{replay_dir}")
    else:
        # One-time migration: seed scanned.db from any existing per-player DBs
        # so previously scanned files aren't re-read after this code update.
        if not st.session_state.get("scanned_migration_done"):
            st.session_state["scanned_migration_done"] = True
            if not db.get_scanned_filenames():
                db.seed_scanned_from_existing_dbs()

        known = db.get_scanned_filenames()
        already_scanned = len(known)
        progress_bar = st.sidebar.progress(0, text="Scanning…")
        status_text  = st.sidebar.empty()

        def _progress(cur, total, fname):
            pct = cur / total if total > 0 else 0.0
            already_note = f" ({already_scanned:,} already processed)" if already_scanned else ""
            progress_bar.progress(pct, text=f"Scanning {cur}/{total}{already_note}")
            if fname:
                status_text.caption(fname[:40])

        parsed, all_scanned = replay_parser.scan_directory(
            replay_dir, known, _progress
        )

        # Group games by player_code and insert into each player's own DB.
        # Open one connection per unique player code, close all when done.
        new_games_for_current = 0
        extra_conns: dict = {}
        try:
            for game in parsed:
                if game["match_type"] != "ranked":
                    continue
                player_code = game.get("player_code", "")
                if not player_code:
                    continue
                if player_code == connect_code:
                    target_conn = conn
                else:
                    if player_code not in extra_conns:
                        extra_conns[player_code] = db.get_conn(player_code)
                    target_conn = extra_conns[player_code]
                inserted = db.insert_game(target_conn, game)
                if inserted and player_code == connect_code:
                    new_games_for_current += 1
        finally:
            for c in extra_conns.values():
                c.close()
            # Mark files scanned in finally so they're always recorded,
            # even if the insert loop errored — prevents full rescan on retry
            db.mark_files_scanned(list(all_scanned))

        progress_bar.empty()
        status_text.empty()
        mode_label = "ranked game(s)"
        st.sidebar.success(
            f"Added {new_games_for_current} new {mode_label} for {connect_code}. "
            f"({len(all_scanned)} files processed)"
        )

# ---------------------------------------------------------------------------
# Fetch rating snapshot (manual)
# ---------------------------------------------------------------------------

if fetch_btn:
    with st.sidebar:
        with st.spinner("Querying Slippi API…"):
            result = api.fetch_player_profile(connect_code)

    if result is None or "error" in result:
        st.sidebar.error(result.get("error", "Unknown API error") if result else "No response")
    else:
        saved = db.upsert_snapshot(conn, connect_code, result["snapshot"])
        db.upsert_seasons(conn, connect_code, result["seasons"])
        if saved:
            st.sidebar.success("Rating snapshot saved.")
        else:
            st.sidebar.info("No new games since last snapshot.")

# ---------------------------------------------------------------------------
# Startup auto-fetch: if new replays exist since last snapshot, capture now
# ---------------------------------------------------------------------------

if (
    not fetch_btn
    and not scan_btn
    and os.path.isdir(replay_dir)
    and not st.session_state.get("startup_fetch_done")
):
    st.session_state["startup_fetch_done"] = True
    last_snaps = db.get_snapshots(conn, connect_code)
    if last_snaps:
        last_ts = pd.to_datetime(last_snaps[-1]["timestamp"], utc=True)
        try:
            newest_mtime = max(
                p.stat().st_mtime for p in Path(replay_dir).rglob("*.slp")
            )
            newest_dt = datetime.fromtimestamp(newest_mtime, tz=timezone.utc)
            if newest_dt > last_ts:
                result = api.fetch_player_profile(connect_code)
                if result and "error" not in result:
                    if db.upsert_snapshot(conn, connect_code, result["snapshot"]):
                        db.upsert_seasons(conn, connect_code, result["seasons"])
                        st.toast("📡 New replays detected — rating snapshot updated!")
        except (ValueError, OSError):
            pass

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------

def _cutoff(date_range: str) -> str | None:
    if date_range == "Last 30 Days":
        return (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    if date_range == "Last 90 Days":
        return (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    return None

cutoff = _cutoff(date_range)
ranked_games   = db.get_games(conn, match_type="ranked", since=cutoff)
snapshots      = db.get_snapshots(conn, connect_code)
season_hist    = db.get_season_history(conn, connect_code)

if not ranked_games and not snapshots and not season_hist:
    st.title(f"No data yet for **{connect_code}**")
    col1, col2 = st.columns(2)
    col1.info("Click **Scan Replays** to import your ranked games from .slp files.")
    col2.info("Click **Fetch Rating Snapshot** to pull your current rating from the API.")
    st.stop()

# ---------------------------------------------------------------------------
# Build DataFrames
# ---------------------------------------------------------------------------

# Games
games_df = pd.DataFrame([dict(r) for r in ranked_games]) if ranked_games else pd.DataFrame()
if not games_df.empty:
    games_df["timestamp"] = pd.to_datetime(games_df["timestamp"], utc=True, errors="coerce")
    games_df["won"] = games_df["result"].isin(["win", "lras_win"]).astype(int)
    games_df["char_name"] = games_df["opponent_char_id"].apply(character_name)
    games_df["stage_name"] = games_df["stage_id"].apply(stage_name)
    games_df["player_char_name"] = games_df["player_char_id"].apply(character_name)

# Snapshots
snap_df = pd.DataFrame([dict(r) for r in snapshots]) if snapshots else pd.DataFrame()
if not snap_df.empty:
    snap_df["timestamp"] = pd.to_datetime(snap_df["timestamp"], utc=True, errors="coerce")
    snap_df = snap_df.sort_values("timestamp").reset_index(drop=True)
    snap_df["rating_delta"] = snap_df["rating"].diff().fillna(0).round(1)

# Season history
season_df = pd.DataFrame([dict(r) for r in season_hist]) if season_hist else pd.DataFrame()
if not season_df.empty:
    season_df["season_start"] = pd.to_datetime(season_df["season_start"], utc=True, errors="coerce")

# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------

total_games  = len(games_df)
total_wins   = int(games_df["won"].sum()) if not games_df.empty else 0
total_losses = total_games - total_wins
win_pct      = total_wins / total_games * 100 if total_games > 0 else 0.0

latest_rating = snap_df.iloc[-1]["rating"] if not snap_df.empty else None
rating_delta  = (
    snap_df.iloc[-1]["rating"] - snap_df.iloc[0]["rating"]
    if len(snap_df) >= 2 else 0.0
)
global_rank = snap_df.iloc[-1]["global_rank"] if not snap_df.empty else None

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.title(connect_code)
st.caption(f"Date range: **{date_range}**  ·  "
           f"{len(games_df)} ranked games  ·  "
           f"{len(snap_df)} rating snapshots")

def _stat_card(label: str, value: str, subvalue: str = "", color: str = "#ffffff") -> str:
    sub_html = f'<div style="font-size:0.8rem;color:#aaa;margin-top:2px;">{subvalue}</div>' if subvalue else ""
    return f"""
    <div style="background:#2b2b2b;border-radius:10px;padding:18px 16px;text-align:center;border:1px solid #3a3a3a;">
        <div style="font-size:0.72rem;color:#888;letter-spacing:0.06em;text-transform:uppercase;margin-bottom:6px;">{label}</div>
        <div style="font-size:1.9rem;font-weight:700;color:{color};line-height:1.1;">{value}</div>
        {sub_html}
    </div>"""

def _calc_streaks(df: pd.DataFrame) -> tuple[int, int]:
    """Return (current_streak, longest_win_streak).
    current_streak: positive = win streak, negative = loss streak.
    """
    if df.empty:
        return 0, 0
    ordered = df.sort_values("timestamp")["won"].tolist()
    # Current streak
    if not ordered:
        return 0, 0
    last = ordered[-1]
    current = 0
    for val in reversed(ordered):
        if val == last:
            current += 1
        else:
            break
    current_streak = current if last == 1 else -current
    # Longest win streak
    longest = cur_run = 0
    for val in ordered:
        if val == 1:
            cur_run += 1
            longest = max(longest, cur_run)
        else:
            cur_run = 0
    return current_streak, longest


current_streak, longest_win_streak = _calc_streaks(games_df) if not games_df.empty else (0, 0)

# Set win/loss counts for header cards
_hdr_set_wins = _hdr_set_losses = 0
if not games_df.empty and "match_id" in games_df.columns:
    for _mid, _sg in games_df.groupby("match_id"):
        if not _mid:
            continue
        _sw = int(_sg["won"].sum())
        _sl = len(_sg) - _sw
        if max(_sw, _sl) < 2:
            continue
        if _sw > _sl:
            _hdr_set_wins += 1
        else:
            _hdr_set_losses += 1
_hdr_set_total = _hdr_set_wins + _hdr_set_losses
_hdr_set_win_pct = _hdr_set_wins / _hdr_set_total * 100 if _hdr_set_total > 0 else 0.0

if current_streak > 0:
    streak_val = f"+{current_streak} 🔥"
    streak_color = WIN_COLOR
elif current_streak < 0:
    streak_val = str(current_streak)
    streak_color = "#e74c3c"
else:
    streak_val = "0"
    streak_color = "#aaa"

delta_str = f"{rating_delta:+.1f}" if rating_delta else ""
m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
m1.markdown(_stat_card("Rating",       f"{latest_rating:.1f}" if latest_rating else "—", delta_str, "#ffffff"), unsafe_allow_html=True)
m2.markdown(_stat_card("Set Win %",    f"{_hdr_set_win_pct:.1f}%",                      color=WIN_COLOR if _hdr_set_win_pct >= 50 else "#e74c3c"), unsafe_allow_html=True)
m3.markdown(_stat_card("Set Wins",     str(_hdr_set_wins),                              color=WIN_COLOR), unsafe_allow_html=True)
m4.markdown(_stat_card("Set Losses",   str(_hdr_set_losses),                            color="#e74c3c"), unsafe_allow_html=True)
m5.markdown(_stat_card("Global Rank",  f"#{global_rank:,}" if global_rank else "—"), unsafe_allow_html=True)
m6.markdown(_stat_card("Streak",       streak_val,                                      color=streak_color), unsafe_allow_html=True)
m7.markdown(_stat_card("Best Streak",  str(longest_win_streak),                         color=WIN_COLOR), unsafe_allow_html=True)

st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

# Recent Form — set results as colored dots, newest on the right
if not games_df.empty and "match_id" in games_df.columns:
    # Build complete sets in chronological order
    _set_results = []
    for _mid, _sg in games_df.sort_values("timestamp").groupby("match_id", sort=False):
        if not _mid:
            continue
        _sw = int(_sg["won"].sum())
        _sl = len(_sg) - _sw
        if max(_sw, _sl) < 2:
            continue
        _opp = _sg["opponent_code"].mode().iloc[0] if not _sg["opponent_code"].empty else "?"
        _set_results.append({"result": "W" if _sw > _sl else "L", "score": f"{_sw}-{_sl}", "opp": _opp})

    _sel_col, _dots_col = st.columns([1, 10])
    with _sel_col:
        form_n = st.selectbox("Number of recent sets", [5, 10, 25], index=1, key="recent_form_n", label_visibility="collapsed")

    recent_sets = _set_results[-form_n:]
    dots = []
    for _s in recent_sets:
        _color = WIN_COLOR if _s["result"] == "W" else "#e74c3c"
        dots.append(
            f'<span title="{_s["result"]} {_s["score"]} vs {_s["opp"]}" '
            f'style="display:inline-block;width:18px;height:18px;border-radius:50%;'
            f'background:{_color};margin:0 3px;"></span>'
        )
    with _dots_col:
        st.markdown(
            f'<div style="margin-top:8px;display:flex;align-items:center;gap:8px;">'
            f'<span style="font-size:0.75rem;color:#888;text-transform:uppercase;letter-spacing:0.06em;">Recent Form</span>'
            f'<div>{"".join(dots)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("---")

# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------

def build_rating_chart() -> go.Figure | None:
    fig = go.Figure()
    has_data = False

    if not season_df.empty and "season_start" in season_df.columns:
        valid = season_df.dropna(subset=["season_start", "rating"])
        if not valid.empty:
            fig.add_trace(go.Scatter(
                x=valid["season_start"],
                y=valid["rating"],
                mode="markers+text",
                name="Season End Rating",
                marker=dict(size=14, color="#f0a500", symbol="diamond"),
                text=valid["season_name"],
                textposition="top center",
                hovertemplate="<b>%{text}</b><br>Rating: %{y:.1f}<extra></extra>",
            ))
            has_data = True

    if not snap_df.empty:
        fig.add_trace(go.Scatter(
            x=snap_df["timestamp"],
            y=snap_df["rating"],
            mode="lines+markers",
            name="Rating Snapshot",
            line=dict(color=WIN_COLOR, width=2.5),
            marker=dict(size=6, color=WIN_COLOR),
            hovertemplate=(
                "<b>%{x|%b %d %H:%M}</b><br>"
                "Rating: %{y:.1f}<br>"
                "Change: %{customdata:+.1f}<extra></extra>"
            ),
            customdata=snap_df["rating_delta"],
        ))
        has_data = True

    if not has_data:
        return None

    fig.update_layout(
        title="Rating Over Time",
        xaxis_title="Date",
        yaxis_title="Rating",
        template=THEME,
        paper_bgcolor=PAPER,
        plot_bgcolor=BG,
        hovermode="x unified",
        margin=dict(l=50, r=30, t=50, b=50),
        legend=dict(orientation="h", y=-0.15),
    )
    return fig


def build_matchup_chart(df=None) -> go.Figure | None:
    if df is None:
        df = games_df
    if df.empty:
        return None

    matchup = (
        df.groupby("char_name")
        .agg(wins=("won", "sum"), total=("won", "count"))
        .reset_index()
    )
    matchup["losses"] = matchup["total"] - matchup["wins"]
    matchup["win_pct"] = matchup["wins"] / matchup["total"] * 100
    # Min 3 games, sorted ascending so best matchups render at top (Plotly
    # draws the last DataFrame row at the top)
    matchup = (
        matchup[matchup["total"] >= 3]
        .sort_values("win_pct", ascending=True)
    )

    if matchup.empty:
        return None

    label = matchup.apply(
        lambda r: f"{r['win_pct']:.0f}%  ({int(r['wins'])}W/{int(r['losses'])}L)", axis=1
    )

    fig = go.Figure()

    # Green segment = wins
    fig.add_trace(go.Bar(
        x=matchup["win_pct"],
        y=matchup["char_name"],
        orientation="h",
        name="Wins",
        marker_color=WIN_COLOR,
        legendrank=1,
        hovertemplate="<b>%{y}</b><br>Win rate: %{x:.1f}%<extra></extra>",
    ))

    # Red segment = losses — text goes outside the full stacked bar (always at 100%)
    fig.add_trace(go.Bar(
        x=100 - matchup["win_pct"],
        y=matchup["char_name"],
        orientation="h",
        name="Losses",
        marker_color="#e74c3c",
        legendrank=2,
        text=label,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Loss rate: %{x:.1f}%<extra></extra>",
    ))

    fig.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        barmode="stack",
        title="Game Win % by Matchup (min. 3 games)",
        xaxis=dict(title="", range=[0, 130]),
        yaxis=dict(title="", tickfont=dict(size=12)),
        template=THEME,
        paper_bgcolor=PAPER,
        plot_bgcolor=BG,
        margin=dict(l=140, r=100, t=50, b=40),
        legend=dict(orientation="h", y=-0.08, traceorder="normal"),
        height=max(350, len(matchup) * 50),
    )
    return fig


def build_stage_chart() -> go.Figure | None:
    if games_df.empty:
        return None
    stage = (
        games_df.groupby("stage_name")
        .agg(wins=("won", "sum"), total=("won", "count"))
        .reset_index()
    )
    stage["losses"] = stage["total"] - stage["wins"]
    stage["win_pct"] = stage["wins"] / stage["total"] * 100
    stage = stage[stage["total"] >= 2].sort_values("win_pct", ascending=False)
    if stage.empty:
        return None

    label = stage.apply(
        lambda r: f"{r['win_pct']:.0f}%  ({int(r['wins'])}W/{int(r['losses'])}L)", axis=1
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=stage["win_pct"],
        y=stage["stage_name"],
        orientation="h",
        name="Wins",
        marker_color=WIN_COLOR,
        legendrank=1,
        hovertemplate="<b>%{y}</b><br>Win rate: %{x:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=100 - stage["win_pct"],
        y=stage["stage_name"],
        orientation="h",
        name="Losses",
        marker_color="#e74c3c",
        legendrank=2,
        text=label,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Loss rate: %{x:.1f}%<extra></extra>",
    ))
    fig.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        barmode="stack",
        title="Game Win % by Stage",
        xaxis=dict(title="", range=[0, 130]),
        yaxis_title="",
        template=THEME,
        paper_bgcolor=PAPER,
        plot_bgcolor=BG,
        margin=dict(l=140, r=100, t=50, b=40),
        legend=dict(orientation="h", y=-0.08, traceorder="normal"),
    )
    return fig


def build_player_char_chart() -> go.Figure | None:
    if games_df.empty or "player_char_name" not in games_df.columns:
        return None

    char_stats = (
        games_df.groupby("player_char_name")
        .agg(wins=("won", "sum"), total=("won", "count"))
        .reset_index()
    )
    char_stats["losses"] = char_stats["total"] - char_stats["wins"]
    char_stats["win_pct"] = char_stats["wins"] / char_stats["total"] * 100
    char_stats = char_stats.sort_values("win_pct")

    label = char_stats.apply(
        lambda r: f"{r['win_pct']:.0f}%  ({int(r['wins'])}W/{int(r['losses'])}L)", axis=1
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=char_stats["win_pct"],
        y=char_stats["player_char_name"],
        orientation="h",
        name="Wins",
        marker_color=WIN_COLOR,
        legendrank=1,
        hovertemplate="<b>%{y}</b><br>Win rate: %{x:.1f}%<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=100 - char_stats["win_pct"],
        y=char_stats["player_char_name"],
        orientation="h",
        name="Losses",
        marker_color="#e74c3c",
        legendrank=2,
        text=label,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Loss rate: %{x:.1f}%<extra></extra>",
    ))
    fig.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        barmode="stack",
        title="Your Game Win % by Character Played (ranked)",
        xaxis=dict(title="", range=[0, 130]),
        yaxis_title="",
        template=THEME,
        paper_bgcolor=PAPER,
        plot_bgcolor=BG,
        margin=dict(l=140, r=100, t=50, b=40),
        legend=dict(orientation="h", y=-0.08, traceorder="normal"),
    )
    return fig


def build_winrate_chart() -> go.Figure | None:
    """Rolling 20-game win rate over time."""
    if games_df.empty or len(games_df) < 5:
        return None
    df = games_df.sort_values("timestamp").copy()
    df["rolling_win_pct"] = df["won"].rolling(window=20, min_periods=5).mean() * 100
    df = df.dropna(subset=["rolling_win_pct"])
    fig = go.Figure()
    fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)
    fig.add_trace(go.Scatter(
        x=df["timestamp"],
        y=df["rolling_win_pct"],
        mode="lines",
        name="Rolling Win Rate",
        line=dict(color=WIN_COLOR, width=2.5),
        fill="tozeroy",
        fillcolor="rgba(46,204,113,0.1)",
        hovertemplate="<b>%{x|%b %d}</b><br>Win Rate: %{y:.1f}%<extra></extra>",
    ))
    fig.update_layout(
        title="Rolling Win Rate (20-game window)",
        xaxis_title="Date",
        yaxis=dict(title="Win %", range=[0, 100]),
        template=THEME,
        paper_bgcolor=PAPER,
        plot_bgcolor=BG,
        margin=dict(l=50, r=30, t=50, b=50),
    )
    return fig



def build_time_of_day_chart() -> go.Figure | None:
    """Win rate by hour of day (hours with at least 3 games)."""
    if games_df.empty:
        return None
    df = games_df.copy()
    df["hour"] = df["timestamp"].dt.hour
    hourly = (
        df.groupby("hour")
        .agg(wins=("won", "sum"), total=("won", "count"))
        .reset_index()
    )
    hourly = hourly[hourly["total"] >= 3].copy()
    if hourly.empty:
        return None
    hourly["win_pct"] = hourly["wins"] / hourly["total"] * 100
    colors = [WIN_COLOR if p >= 50 else "#e74c3c" for p in hourly["win_pct"]]
    # Format hour labels as "12am", "3pm", etc.
    def _fmt_hour(h):
        if h == 0:
            return "12am"
        elif h < 12:
            return f"{h}am"
        elif h == 12:
            return "12pm"
        else:
            return f"{h - 12}pm"
    hourly["hour_label"] = hourly["hour"].apply(_fmt_hour)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=hourly["hour_label"],
        y=hourly["win_pct"],
        marker_color=colors,
        hovertemplate="<b>%{x}</b><br>Win Rate: %{y:.1f}%<br>Games: %{customdata}<extra></extra>",
        customdata=hourly["total"],
    ))
    fig.add_hline(y=50, line_dash="dash", line_color="gray", opacity=0.5)
    fig.update_layout(
        title="Win Rate by Time of Day",
        xaxis_title="Hour",
        yaxis=dict(title="Win %", range=[0, 100]),
        template=THEME,
        paper_bgcolor=PAPER,
        plot_bgcolor=BG,
        margin=dict(l=50, r=30, t=50, b=50),
    )
    return fig


def build_sessions_df(snap_df: pd.DataFrame | None = None) -> pd.DataFrame:
    """Group games into play sessions (2-hour idle gap = new session)."""
    if games_df.empty:
        return pd.DataFrame()
    df = games_df.sort_values("timestamp").copy()
    df["gap"] = df["timestamp"].diff()
    df["new_session"] = df["gap"].isna() | (df["gap"] > pd.Timedelta(hours=2))
    df["session_id"] = df["new_session"].cumsum()
    rows = []
    for _, grp in df.groupby("session_id"):
        w = int(grp["won"].sum())
        l = len(grp) - w
        start = grp["timestamp"].min()
        end = grp["timestamp"].max()
        sets = sum(
            1 for mid, sg in grp.groupby("match_id")
            if mid and max(int(sg["won"].sum()), len(sg) - int(sg["won"].sum())) >= 2
        )
        # Rating delta for this session
        rating_delta_str = "—"
        if snap_df is not None and not snap_df.empty and pd.notna(start):
            window_start = start - pd.Timedelta(minutes=5)
            window_end = end + pd.Timedelta(hours=2)
            in_window = snap_df[
                (snap_df["timestamp"] >= window_start) &
                (snap_df["timestamp"] <= window_end)
            ]
            if len(in_window) >= 2:
                delta = in_window.iloc[-1]["rating"] - in_window.iloc[0]["rating"]
                rating_delta_str = f"{delta:+.1f}"
            elif len(in_window) == 1:
                before = snap_df[snap_df["timestamp"] < window_start]
                if not before.empty:
                    delta = in_window.iloc[0]["rating"] - before.iloc[-1]["rating"]
                    rating_delta_str = f"{delta:+.1f}"
        rows.append({
            "_ts": start,
            "Date": start.strftime("%b %d, %Y") if pd.notna(start) else "?",
            "Sets": sets,
            "Games": len(grp),
            "W": w,
            "L": l,
            "Win %": f"{w / len(grp) * 100:.0f}%",
            "±Rating": rating_delta_str,
            "Result": "Positive" if w > l else ("Negative" if l > w else "Even"),
        })
    return (
        pd.DataFrame(rows)
        .sort_values("_ts", ascending=False)
        .drop(columns=["_ts"])
        .reset_index(drop=True)
    )


def build_clutch_stats() -> dict:
    """
    Two clutch metrics derivable from existing data:
    - Deciding game win %: win rate in games 3 of a set (set went to a decider)
    - Comeback rate: % of sets won after losing game 1
    """
    if games_df.empty or "match_id" not in games_df.columns:
        return {}

    decider_wins = decider_total = 0
    comeback_wins = comeback_total = 0

    for match_id, grp in games_df.groupby("match_id"):
        if not match_id or len(grp) < 2:
            continue
        grp = grp.sort_values("timestamp")
        w = int(grp["won"].sum())
        l = len(grp) - w
        if max(w, l) < 2:
            continue  # incomplete set
        game_results = list(grp["won"])  # ordered list of 1/0 per game

        # Comeback: lost game 1, count whether set was won overall
        if game_results[0] == 0 and len(game_results) >= 2:
            comeback_total += 1
            set_wins = sum(game_results)
            set_losses = len(game_results) - set_wins
            if set_wins > set_losses:
                comeback_wins += 1

        # Deciding game: set went to game 3+ (scores tied at some point going into last game)
        # Simplified: any set with exactly 2W/1L or 1W/2L qualifies
        set_wins = sum(game_results)
        set_losses = len(game_results) - set_wins
        if len(game_results) >= 3 and abs(set_wins - set_losses) <= 1:
            decider_total += 1
            if set_wins > set_losses:
                decider_wins += 1

    return {
        "comeback_wins": comeback_wins,
        "comeback_total": comeback_total,
        "comeback_pct": comeback_wins / comeback_total * 100 if comeback_total else None,
        "decider_wins": decider_wins,
        "decider_total": decider_total,
        "decider_pct": decider_wins / decider_total * 100 if decider_total else None,
    }


def build_opponent_history(opponent_code: str) -> pd.DataFrame:
    """All sets vs a specific opponent, with game-by-game breakdown."""
    if games_df.empty or "match_id" not in games_df.columns:
        return pd.DataFrame()
    opp_games = games_df[games_df["opponent_code"].str.upper() == opponent_code.upper()]
    if opp_games.empty:
        return pd.DataFrame()
    rows = []
    for match_id, grp in opp_games.groupby("match_id"):
        grp = grp.sort_values("timestamp")
        w = int(grp["won"].sum())
        l = len(grp) - w
        if max(w, l) < 2:
            continue  # incomplete set
        ts = grp["timestamp"].min()
        game_seq = " ".join("W" if r else "L" for r in grp["won"])
        opp_char = character_name(
            int(grp["opponent_char_id"].mode().iloc[0])
            if not grp["opponent_char_id"].dropna().empty else None
        )
        rows.append({
            "_ts": ts,
            "Date": ts.strftime("%b %d, %Y %H:%M") if pd.notna(ts) else "?",
            "Opp Char": opp_char,
            "Games": game_seq,
            "W": w, "L": l,
            "Result": "Win" if w > l else "Loss",
        })
    return pd.DataFrame(rows).sort_values("_ts", ascending=False).drop(columns=["_ts"])


def build_sets_df(since: pd.Timestamp | None = None) -> pd.DataFrame:
    if games_df.empty or "match_id" not in games_df.columns:
        return pd.DataFrame()

    src = games_df if since is None else games_df[games_df["timestamp"] >= since]
    sets = []
    for match_id, grp in src.groupby("match_id"):
        if not match_id:
            continue
        w = int(grp["won"].sum())
        l = len(grp) - w
        if max(w, l) < 2:
            continue  # incomplete set (disconnect before anyone won 2 games)
        opp = grp["opponent_code"].mode().iloc[0] if not grp["opponent_code"].empty else "?"
        opp_char = character_name(
            int(grp["opponent_char_id"].mode().iloc[0])
            if not grp["opponent_char_id"].dropna().empty else None
        )
        ts = grp["timestamp"].min()
        result = "Win" if w > l else "Loss"
        sets.append({
            "_ts": ts,
            "Date": ts.strftime("%b %d %H:%M") if pd.notna(ts) else "?",
            "Opponent": opp,
            "Opp Char": opp_char,
            "Game W": w, "Game L": l,
            "Result": result,
        })

    return (
        pd.DataFrame(sets)
        .sort_values("_ts", ascending=False)
        .drop(columns=["_ts"])
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------------
# Layout — tabbed
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚡ Most Recent Session",
    "🎮 Matchup Stats",
    "🗺️ Stage Stats",
    "📈 Rating Progression",
    "📊 All-Time Stats",
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Session Summary
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    def _get_last_session() -> pd.DataFrame:
        if games_df.empty:
            return pd.DataFrame()
        df = games_df.sort_values("timestamp").copy()
        df["gap"] = df["timestamp"].diff()
        df["new_session"] = df["gap"].isna() | (df["gap"] > pd.Timedelta(hours=2))
        df["session_id"] = df["new_session"].cumsum()
        last_id = df["session_id"].iloc[-1]
        return df[df["session_id"] == last_id].copy()

    last_sess = _get_last_session()

    if last_sess.empty:
        st.info("No session data yet — scan your replay directory to get started.")
    else:
        sess_start = last_sess["timestamp"].min()
        sess_end   = last_sess["timestamp"].max()
        duration_min = int((sess_end - sess_start).total_seconds() / 60)
        duration_str = f"{duration_min // 60}h {duration_min % 60}m" if duration_min >= 60 else f"{duration_min}m"
        sess_w = int(last_sess["won"].sum())
        sess_l = len(last_sess) - sess_w
        sess_wr = sess_w / len(last_sess) * 100

        sess_sets_count = sum(
            1 for mid, sg in last_sess.groupby("match_id")
            if mid and max(int(sg["won"].sum()), len(sg) - int(sg["won"].sum())) >= 2
        )

        s1, s2, s3, s4, s5 = st.columns(5)
        s1.markdown(_stat_card(
            "Date",
            sess_start.strftime("%b %d") if pd.notna(sess_start) else "?",
            sess_start.strftime("%I:%M %p").lstrip("0") if pd.notna(sess_start) else "",
        ), unsafe_allow_html=True)
        s2.markdown(_stat_card("Duration", duration_str), unsafe_allow_html=True)
        s3.markdown(_stat_card("Sets", str(sess_sets_count)), unsafe_allow_html=True)
        sess_games_html = f'<span style="color:{WIN_COLOR}">{sess_w}W</span> / <span style="color:#e74c3c">{sess_l}L</span>'
        s4.markdown(_stat_card("Games", sess_games_html), unsafe_allow_html=True)
        s5.markdown(_stat_card(
            "Game Win %", f"{sess_wr:.0f}%",
            color=WIN_COLOR if sess_wr >= 50 else "#e74c3c",
        ), unsafe_allow_html=True)

        st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

        sess_sets = []
        for mid, sg in last_sess.groupby("match_id"):
            if not mid:
                continue
            sw = int(sg["won"].sum())
            sl = len(sg) - sw
            if max(sw, sl) < 2:
                continue
            opp = sg["opponent_code"].mode().iloc[0] if not sg["opponent_code"].empty else "?"
            opp_char = character_name(
                int(sg["opponent_char_id"].mode().iloc[0])
                if not sg["opponent_char_id"].dropna().empty else None
            )
            ts = sg["timestamp"].min()
            result = "Win" if sw > sl else "Loss"
            sess_sets.append({"opp": opp, "char": opp_char, "w": sw, "l": sl, "result": result, "ts": ts})

        if sess_sets:
            sess_sets.sort(key=lambda x: x["ts"])
            st.markdown("##### Sets This Session")
            cols_per_row = 4
            for i in range(0, len(sess_sets), cols_per_row):
                row_sets = sess_sets[i:i + cols_per_row]
                cols = st.columns(cols_per_row)
                for col, s in zip(cols, row_sets):
                    res_color = WIN_COLOR if s["result"] == "Win" else "#e74c3c"
                    col.markdown(f"""
<div style="background:#2b2b2b;border-radius:10px;padding:14px 12px;text-align:center;border:1px solid #3a3a3a;border-top:3px solid {res_color};">
  <div style="font-size:0.7rem;color:#888;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">{s["char"]}</div>
  <div style="font-size:1.1rem;font-weight:700;color:#fff;margin-bottom:2px;">{s["opp"]}</div>
  <div style="font-size:1.4rem;font-weight:700;color:{res_color};">{s["w"]}-{s["l"]}</div>
  <div style="font-size:0.75rem;color:{res_color};margin-top:2px;">{s["result"]}</div>
</div>""", unsafe_allow_html=True)
            st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

        st.markdown("---")
        left_col, right_col = st.columns(2)

        with left_col:
            st.markdown("##### Characters Faced")
            sess_char = (
                last_sess.groupby("char_name")
                .agg(wins=("won", "sum"), total=("won", "count"))
                .reset_index()
            )
            sess_char["losses"] = sess_char["total"] - sess_char["wins"]
            sess_char["win_pct"] = sess_char["wins"] / sess_char["total"] * 100
            sess_char = sess_char.sort_values("win_pct", ascending=True)
            if not sess_char.empty:
                label_char = sess_char.apply(
                    lambda r: f"{r['win_pct']:.0f}%  ({int(r['wins'])}W/{int(r['losses'])}L)", axis=1
                )
                fig_sc = go.Figure()
                fig_sc.add_trace(go.Bar(
                    x=sess_char["win_pct"], y=sess_char["char_name"],
                    orientation="h", name="Wins", marker_color=WIN_COLOR,
                    hovertemplate="<b>%{y}</b><br>Win rate: %{x:.1f}%<extra></extra>",
                ))
                fig_sc.add_trace(go.Bar(
                    x=100 - sess_char["win_pct"], y=sess_char["char_name"],
                    orientation="h", name="Losses", marker_color="#e74c3c",
                    text=label_char, textposition="outside",
                    hovertemplate="<b>%{y}</b><br>Loss rate: %{x:.1f}%<extra></extra>",
                ))
                fig_sc.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
                fig_sc.update_layout(
                    barmode="stack", xaxis=dict(title="", range=[0, 130]),
                    yaxis=dict(title="", tickfont=dict(size=12)),
                    template=THEME, paper_bgcolor=PAPER, plot_bgcolor=BG,
                    margin=dict(l=140, r=100, t=20, b=30),
                    height=max(200, len(sess_char) * 45),
                    legend=dict(orientation="h", y=-0.15, traceorder="normal"),
                    showlegend=False,
                )
                st.plotly_chart(fig_sc, width='stretch')

        with right_col:
            st.markdown("##### Stages")
            sess_stage = (
                last_sess.groupby("stage_name")
                .agg(wins=("won", "sum"), total=("won", "count"))
                .reset_index()
            )
            sess_stage["losses"] = sess_stage["total"] - sess_stage["wins"]
            sess_stage["win_pct"] = sess_stage["wins"] / sess_stage["total"] * 100
            sess_stage = sess_stage.sort_values("win_pct", ascending=True)
            if not sess_stage.empty:
                label_st = sess_stage.apply(
                    lambda r: f"{r['win_pct']:.0f}%  ({int(r['wins'])}W/{int(r['losses'])}L)", axis=1
                )
                fig_ss = go.Figure()
                fig_ss.add_trace(go.Bar(
                    x=sess_stage["win_pct"], y=sess_stage["stage_name"],
                    orientation="h", name="Wins", marker_color=WIN_COLOR,
                    hovertemplate="<b>%{y}</b><br>Win rate: %{x:.1f}%<extra></extra>",
                ))
                fig_ss.add_trace(go.Bar(
                    x=100 - sess_stage["win_pct"], y=sess_stage["stage_name"],
                    orientation="h", name="Losses", marker_color="#e74c3c",
                    text=label_st, textposition="outside",
                    hovertemplate="<b>%{y}</b><br>Loss rate: %{x:.1f}%<extra></extra>",
                ))
                fig_ss.add_vline(x=50, line_dash="dash", line_color="gray", opacity=0.5)
                fig_ss.update_layout(
                    barmode="stack", xaxis=dict(title="", range=[0, 130]),
                    yaxis=dict(title="", tickfont=dict(size=12)),
                    template=THEME, paper_bgcolor=PAPER, plot_bgcolor=BG,
                    margin=dict(l=140, r=100, t=20, b=30),
                    height=max(200, len(sess_stage) * 45),
                    legend=dict(orientation="h", y=-0.15, traceorder="normal"),
                    showlegend=False,
                )
                st.plotly_chart(fig_ss, width='stretch')

        st.markdown("---")
        st.markdown("##### Momentum")
        ordered_sess = last_sess.sort_values("timestamp").reset_index(drop=True)
        ordered_sess["game_num"] = range(1, len(ordered_sess) + 1)
        ordered_sess["result_val"] = ordered_sess["won"].apply(lambda x: 1 if x else -1)
        ordered_sess["cumulative"] = ordered_sess["result_val"].cumsum()
        mom_colors = [WIN_COLOR if v >= 0 else "#e74c3c" for v in ordered_sess["cumulative"]]
        fig_mom = go.Figure()
        fig_mom.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig_mom.add_trace(go.Scatter(
            x=ordered_sess["game_num"], y=ordered_sess["cumulative"],
            mode="lines+markers",
            line=dict(color=WIN_COLOR, width=2.5),
            marker=dict(size=10, color=mom_colors, line=dict(width=1, color="#1e1e1e")),
            hovertemplate="Game %{x}<br>Score: %{y:+d}<extra></extra>",
        ))
        fig_mom.update_layout(
            xaxis=dict(title="Game #", dtick=1),
            yaxis=dict(title="W/L Balance"),
            template=THEME, paper_bgcolor=PAPER, plot_bgcolor=BG,
            margin=dict(l=50, r=30, t=20, b=50), height=220,
        )
        st.plotly_chart(fig_mom, width='stretch')


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Matchup Breakdown
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    if not games_df.empty:
        all_chars = sorted(games_df["char_name"].dropna().unique())
        included = st.multiselect(
            "Characters to include in matchup chart:",
            options=all_chars,
            default=all_chars,
            key="matchup_include",
        )
        filtered_games = games_df[games_df["char_name"].isin(included)] if included else games_df
    else:
        filtered_games = games_df

    matchup_fig = build_matchup_chart(filtered_games)
    if matchup_fig:
        st.plotly_chart(matchup_fig, width='stretch')
    else:
        st.info("No ranked replay data yet — scan your replay directory.")

    if not games_df.empty:
        matchup_summary = (
            filtered_games.groupby("char_name")
            .agg(wins=("won", "sum"), total=("won", "count"))
            .reset_index()
        )
        matchup_summary["win_pct"] = matchup_summary["wins"] / matchup_summary["total"] * 100
        matchup_summary = matchup_summary[matchup_summary["total"] >= 3].sort_values("win_pct", ascending=False)

        if not matchup_summary.empty:
            st.markdown("---")
            col_best, col_bad = st.columns(2)
            with col_best:
                st.markdown("##### ✅ Best Matchups")
                for _, row in matchup_summary.head(3).iterrows():
                    l = int(row['total'] - row['wins'])
                    st.markdown(
                        f"**{row['char_name']}** — "
                        f"<span style='color:{WIN_COLOR}'>{row['win_pct']:.0f}%</span> "
                        f"({int(row['wins'])}W / {l}L in {int(row['total'])} games)",
                        unsafe_allow_html=True,
                    )
            with col_bad:
                st.markdown("##### ⚠️ Problem Matchups")
                for _, row in matchup_summary.tail(3).iloc[::-1].iterrows():
                    l = int(row['total'] - row['wins'])
                    st.markdown(
                        f"**{row['char_name']}** — "
                        f"<span style='color:#e74c3c'>{row['win_pct']:.0f}%</span> "
                        f"({int(row['wins'])}W / {l}L in {int(row['total'])} games)",
                        unsafe_allow_html=True,
                    )

    st.markdown("---")
    player_char_fig = build_player_char_chart()
    if player_char_fig:
        st.plotly_chart(player_char_fig, width='stretch')

    st.markdown("---")
    _sets_range_col, _ = st.columns([2, 5])
    with _sets_range_col:
        _sets_range = st.selectbox(
            "Recent Sets — time range",
            ["Last 7 Days", "Last 30 Days", "Last 90 Days", "All Time"],
            index=1,
            key="recent_sets_range",
        )
    _sets_since = None
    if _sets_range == "Last 7 Days":
        _sets_since = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)
    elif _sets_range == "Last 30 Days":
        _sets_since = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=30)
    elif _sets_range == "Last 90 Days":
        _sets_since = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=90)

    st.subheader("Recent Sets")
    sets_df = build_sets_df(since=_sets_since)
    if not sets_df.empty:
        def color_result(val):
            color = WIN_COLOR if val == "Win" else "#e74c3c"
            return f"color: {color}; font-weight: bold"
        styled = sets_df.style.map(color_result, subset=["Result"])
        st.dataframe(styled, hide_index=True, width='stretch')
        st.download_button("⬇ Export Recent Sets (CSV)", sets_df.to_csv(index=False), "recent_sets.csv", "text/csv", key="dl_recent_sets")
    else:
        st.info("No sets to display yet.")

    st.markdown("---")
    st.subheader("Replay Lookup")
    if not games_df.empty:
        all_chars = sorted(games_df["char_name"].dropna().unique())
        selected_char = st.selectbox(
            "Browse replays by opponent character:",
            ["— select a character —"] + all_chars,
            key="replay_lookup_char",
        )
        if selected_char != "— select a character —":
            char_games = games_df[games_df["char_name"] == selected_char].copy()
            char_games["Date"] = char_games["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
            char_games["Result"] = char_games["result"].map({
                "win": "Win", "loss": "Loss",
                "lras_win": "Win (quit)", "lras_loss": "Loss (quit)",
            })
            char_games["Duration"] = char_games["duration_frames"].apply(
                lambda f: f"{int(f // 60 // 60)}:{int(f // 60 % 60):02d}" if pd.notna(f) else "—"
            )
            char_games["File Path"] = char_games["filepath"].fillna("(path not recorded — rescan to populate)")
            display_df = char_games[[
                "Date", "opponent_code", "stage_name", "Result", "Duration", "File Path"
            ]].rename(columns={"opponent_code": "Opponent", "stage_name": "Stage"}).sort_values("Date", ascending=False)
            def _color_result(val):
                if val in ("Win", "Win (quit)"):
                    return "color: #2ecc71; font-weight: bold"
                if val in ("Loss", "Loss (quit)"):
                    return "color: #e74c3c; font-weight: bold"
                return ""
            st.caption(f"{len(char_games)} games vs {selected_char} in this date range")
            styled = display_df.style.map(_color_result, subset=["Result"])
            st.dataframe(styled, hide_index=True, width='stretch')
            st.download_button("⬇ Export (CSV)", display_df.to_csv(index=False), f"replays_{selected_char}.csv", "text/csv", key="dl_replay_lookup")

    st.markdown("---")
    st.subheader("Opponent History")
    if not games_df.empty:
        all_opponents = sorted(games_df["opponent_code"].dropna().unique())
        opp_summary = (
            games_df.groupby("opponent_code")
            .agg(wins=("won", "sum"), total=("won", "count"))
            .reset_index()
        )
        opp_summary["losses"] = opp_summary["total"] - opp_summary["wins"]
        opp_summary["win_pct"] = opp_summary["wins"] / opp_summary["total"] * 100
        set_counts: dict = {}
        for mid, sg in games_df.groupby("match_id"):
            if not mid:
                continue
            sw = int(sg["won"].sum())
            sl = len(sg) - sw
            if max(sw, sl) < 2:
                continue
            opp = sg["opponent_code"].mode().iloc[0] if not sg["opponent_code"].empty else None
            if opp:
                set_counts[opp] = set_counts.get(opp, 0) + 1
        opp_summary["sets"] = opp_summary["opponent_code"].map(set_counts).fillna(0).astype(int)
        opp_summary = opp_summary.sort_values("total", ascending=False).rename(columns={
            "opponent_code": "Opponent", "wins": "Game W", "losses": "Game L",
            "total": "Games", "win_pct": "Game Win %", "sets": "Sets",
        })[["Opponent", "Sets", "Games", "Game W", "Game L", "Game Win %"]]
        def _color_winpct(val):
            try:
                return f"color: {WIN_COLOR}" if float(val) >= 50 else "color: #e74c3c"
            except (ValueError, TypeError):
                return ""
        styled_opp = opp_summary.style.format({"Game Win %": "{:.1f}%"}).map(_color_winpct, subset=["Game Win %"])
        st.dataframe(styled_opp, hide_index=True, width='stretch')
        st.download_button("⬇ Export Opponent History (CSV)", opp_summary.to_csv(index=False), "opponent_history.csv", "text/csv", key="dl_opp_history")

        st.markdown("##### Set History vs Specific Opponents")
        selected_opp = st.selectbox("Select opponent:", ["— select —"] + all_opponents, key="opp_history_select")
        if selected_opp != "— select —":
            opp_sets = build_opponent_history(selected_opp)
            if not opp_sets.empty:
                total_sets = len(opp_sets)
                set_wins = int((opp_sets["Result"] == "Win").sum())
                st.caption(f"**{selected_opp}** — {set_wins}W / {total_sets - set_wins}L in sets")
                def _color_set_result(val):
                    return f"color: {WIN_COLOR}; font-weight: bold" if val == "Win" else "color: #e74c3c; font-weight: bold"
                styled_sets = opp_sets.style.map(_color_set_result, subset=["Result"])
                st.dataframe(styled_sets, hide_index=True, width='stretch')
                st.download_button("⬇ Export (CSV)", opp_sets.to_csv(index=False), f"sets_vs_{selected_opp}.csv", "text/csv", key="dl_opp_sets")
    else:
        st.info("Opponent history appears after ranked replays are scanned.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Stage Analytics
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    stage_fig = build_stage_chart()
    if stage_fig:
        st.plotly_chart(stage_fig, width='stretch')
    else:
        st.info("Stage data appears after replays are scanned.")

    if not games_df.empty:
        stage_summary = (
            games_df.groupby("stage_name")
            .agg(wins=("won", "sum"), total=("won", "count"))
            .reset_index()
        )
        stage_summary["win_pct"] = stage_summary["wins"] / stage_summary["total"] * 100
        stage_summary = stage_summary[stage_summary["total"] >= 2].sort_values("win_pct", ascending=False)

        if not stage_summary.empty:
            st.markdown("---")
            col_best, col_worst = st.columns(2)
            with col_best:
                st.markdown("##### 🏆 Best Stages")
                for _, row in stage_summary.head(3).iterrows():
                    st.markdown(
                        f"**{row['stage_name']}** — "
                        f"<span style='color:{WIN_COLOR}'>{row['win_pct']:.0f}%</span> "
                        f"({int(row['wins'])}W / {int(row['total'] - row['wins'])}L)",
                        unsafe_allow_html=True,
                    )
            with col_worst:
                st.markdown("##### 💀 Worst Stages")
                for _, row in stage_summary.tail(3).iloc[::-1].iterrows():
                    st.markdown(
                        f"**{row['stage_name']}** — "
                        f"<span style='color:#e74c3c'>{row['win_pct']:.0f}%</span> "
                        f"({int(row['wins'])}W / {int(row['total'] - row['wins'])}L)",
                        unsafe_allow_html=True,
                    )

    st.markdown("---")
    st.subheader("Session History")
    sessions_df = build_sessions_df(snap_df=snap_df)
    if not sessions_df.empty:
        def _color_session(val):
            if val == "Positive":
                return f"color: {WIN_COLOR}; font-weight: bold"
            if val == "Negative":
                return "color: #e74c3c; font-weight: bold"
            return "color: #aaa"
        styled_sessions = sessions_df.style.map(_color_session, subset=["Result"])
        st.dataframe(styled_sessions, hide_index=True, width='stretch')
        st.download_button("⬇ Export Session History (CSV)", sessions_df.to_csv(index=False), "session_history.csv", "text/csv", key="dl_sessions")
    else:
        st.info("Session data appears after ranked replays are scanned.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — Rating Progression
# ══════════════════════════════════════════════════════════════════════════════

with tab4:
    rating_fig = build_rating_chart()
    if rating_fig:
        st.plotly_chart(rating_fig, width='stretch')
    else:
        st.info("No rating data yet — fetch a snapshot or keep the app open while playing ranked.")

    st.markdown("---")

    r1, r2 = st.columns(2)
    r1.markdown(_stat_card("Current Rating", f"{latest_rating:.1f}" if latest_rating else "—", delta_str), unsafe_allow_html=True)
    r2.markdown(_stat_card("Ranked Games",   str(total_games)), unsafe_allow_html=True)

    watcher_alive = (
        st.session_state.get(f"watcher_{connect_code}") is not None
        and st.session_state[f"watcher_{connect_code}"].is_alive()
    )
    if watcher_alive:
        st.caption("🟢 Live watcher active — rating snapshots will be captured automatically after each ranked set.")
    else:
        st.caption("⚪ Watcher inactive (replay directory not found or not set).")

    st.markdown("---")
    winrate_fig = build_winrate_chart()
    if winrate_fig:
        st.plotly_chart(winrate_fig, width='stretch')
    else:
        st.info("Not enough games yet for rolling win rate (need at least 5).")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — All-Time Stats
# ══════════════════════════════════════════════════════════════════════════════

with tab5:
    if not games_df.empty:
        set_wins_count = set_total_count = 0
        for mid, sg in games_df.groupby("match_id"):
            if not mid:
                continue
            sw = int(sg["won"].sum())
            sl = len(sg) - sw
            if max(sw, sl) < 2:
                continue
            set_total_count += 1
            if sw > sl:
                set_wins_count += 1
        set_win_pct = set_wins_count / set_total_count * 100 if set_total_count > 0 else None

        ov1, ov2 = st.columns(2)
        ov1.markdown(_stat_card(
            "Set Win %",
            f"{set_win_pct:.1f}%" if set_win_pct is not None else "—",
            f"{set_wins_count}W / {set_total_count - set_wins_count}L in sets" if set_total_count > 0 else "No complete sets",
            WIN_COLOR if set_win_pct and set_win_pct >= 50 else "#e74c3c",
        ), unsafe_allow_html=True)
        ov2.markdown(_stat_card(
            "Game Win %", f"{win_pct:.1f}%",
            f"{total_wins}W / {total_losses}L",
            WIN_COLOR if win_pct >= 50 else "#e74c3c",
        ), unsafe_allow_html=True)
        st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

        clutch = build_clutch_stats()
        if clutch:
            c1, c2 = st.columns(2)
            cb_pct   = clutch.get("comeback_pct")
            cb_total = clutch.get("comeback_total", 0)
            cb_wins  = clutch.get("comeback_wins", 0)
            dc_pct   = clutch.get("decider_pct")
            dc_total = clutch.get("decider_total", 0)
            dc_wins  = clutch.get("decider_wins", 0)
            c1.markdown(_stat_card(
                "Comeback Rate",
                f"{cb_pct:.1f}%" if cb_pct is not None else "—",
                f"{cb_wins}W / {cb_total - cb_wins}L after going down 0-1",
                WIN_COLOR if cb_pct and cb_pct >= 50 else "#e74c3c",
            ), unsafe_allow_html=True)
            c2.markdown(_stat_card(
                "Deciding Game Win %",
                f"{dc_pct:.1f}%" if dc_pct is not None else "—",
                f"{dc_wins}W / {dc_total - dc_wins}L in game 3s",
                WIN_COLOR if dc_pct and dc_pct >= 50 else "#e74c3c",
            ), unsafe_allow_html=True)
        else:
            st.info("Not enough set data for clutch stats yet.")
    else:
        st.info("All-time stats appear after ranked replays are scanned.")

    st.markdown("---")
    tod_fig = build_time_of_day_chart()
    if tod_fig:
        st.plotly_chart(tod_fig, width='stretch')
    else:
        st.info("Time-of-day chart needs at least 3 games in a single hour.")


# ---------------------------------------------------------------------------
# Keyboard zoom (Ctrl+/- adjusts page zoom; Ctrl+0 resets)
# ---------------------------------------------------------------------------

import streamlit.components.v1 as _components
_components.html("""
<script>
window.parent.document.addEventListener('keydown', function(e) {
    if (!e.ctrlKey) return;
    var doc = window.parent.document;
    var cur = parseFloat(doc.body.style.zoom) || 1;
    if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        doc.body.style.zoom = Math.min(+(cur + 0.1).toFixed(1), 2.0);
    } else if (e.key === '-') {
        e.preventDefault();
        doc.body.style.zoom = Math.max(+(cur - 0.1).toFixed(1), 0.5);
    } else if (e.key === '0') {
        e.preventDefault();
        doc.body.style.zoom = 1;
    }
});
</script>
""", height=0)

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

st.markdown("---")
st.caption(
    "Data sources: `.slp` replay files (matchup stats) + Slippi API (rating snapshots)  ·  "
    "Stored locally in `data/`"
)
