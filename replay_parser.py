"""
Binary .slp replay parser.

Parses the Slippi replay file format directly without relying on py-slippi's
frame iteration. Metadata (connect codes, characters, timestamp) is extracted
directly from the UBJSON block at the end of the file — avoiding a full
SlippiGame parse that would iterate every frame.

Key Slippi event command bytes (spec 3.x):
  0x35 = Event Payloads    0x36 = Game Start
  0x37 = Pre-Frame Update  0x38 = Post-Frame Update
  0x39 = Game End          0x3A = Frame Start
  0x3B = Item Update       0x3C = Frame Bookend
  0x3D = Gecko List        0x10 = Message Splitter
"""

import os
import struct
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


# ---------------------------------------------------------------------------
# Minimal pure-Python UBJSON parser
# ---------------------------------------------------------------------------
# Replaces the 'ubjson' C-extension package, which has no Python 3.13 wheels.
# Covers only the type markers Slippi actually uses in its metadata block.

def _load_ubjson(data: bytes):
    """Parse a UBJSON byte string and return a Python dict/list/scalar."""
    pos = [0]  # wrapped in a list so nested closures can mutate it

    def read(n: int) -> bytes:
        chunk = data[pos[0]: pos[0] + n]
        pos[0] += n
        return chunk

    def read_byte() -> int:
        b = data[pos[0]]
        pos[0] += 1
        return b

    def read_length() -> int:
        """Read a UBJSON integer that encodes an array/string length."""
        m = chr(read_byte())
        if m == 'i':  return struct.unpack('b',  read(1))[0]   # int8
        if m == 'U':  return read(1)[0]                         # uint8
        if m == 'I':  return struct.unpack('>h', read(2))[0]   # int16
        if m == 'l':  return struct.unpack('>i', read(4))[0]   # int32
        if m == 'L':  return struct.unpack('>q', read(8))[0]   # int64
        raise ValueError(f"Unexpected length marker: {m!r}")

    def parse():
        m = chr(read_byte())
        if m == '{':                          # object
            obj = {}
            while chr(data[pos[0]]) != '}':
                key_len = read_length()
                key = read(key_len).decode('utf-8', errors='replace')
                obj[key] = parse()
            pos[0] += 1  # consume '}'
            return obj
        if m == '[':                          # array
            arr = []
            while chr(data[pos[0]]) != ']':
                arr.append(parse())
            pos[0] += 1  # consume ']'
            return arr
        if m == 'S':                          # string
            return read(read_length()).decode('utf-8', errors='replace')
        if m == 'i':  return struct.unpack('b',  read(1))[0]
        if m == 'U':  return read(1)[0]
        if m == 'I':  return struct.unpack('>h', read(2))[0]
        if m == 'l':  return struct.unpack('>i', read(4))[0]
        if m == 'L':  return struct.unpack('>q', read(8))[0]
        if m == 'd':  return struct.unpack('>f', read(4))[0]   # float32
        if m == 'D':  return struct.unpack('>d', read(8))[0]   # float64
        if m == 'T':  return True
        if m == 'F':  return False
        if m == 'Z':  return None
        raise ValueError(f"Unknown UBJSON type marker: {m!r}")

    return parse()

# ---------------------------------------------------------------------------
# Lookup tables
# ---------------------------------------------------------------------------

CHARACTER_NAMES: dict[int, str] = {
    0:  "Mario",
    1:  "Fox",
    2:  "Captain Falcon",
    3:  "Donkey Kong",
    4:  "Kirby",
    5:  "Bowser",
    6:  "Link",
    7:  "Sheik",
    8:  "Ness",
    9:  "Peach",
    10: "Ice Climbers",
    12: "Pikachu",
    13: "Samus",
    14: "Yoshi",
    15: "Jigglypuff",
    16: "Mewtwo",
    17: "Luigi",
    18: "Marth",
    19: "Zelda",
    20: "Young Link",
    21: "Dr. Mario",
    22: "Falco",
    23: "Pichu",
    24: "Mr. Game & Watch",
    25: "Ganondorf",
    26: "Roy",
}

STAGE_NAMES: dict[int, str] = {
    2:  "Fountain of Dreams",
    3:  "Pokémon Stadium",
    4:  "Kongo Jungle N64",
    5:  "Jungle Japes",
    6:  "Great Bay",
    7:  "Hyrule Temple",
    8:  "Yoshi's Story",
    9:  "Yoshi's Island (Melee)",
    12: "Mushroom Kingdom",
    13: "Brinstar",
    14: "Onett",
    15: "Mute City",
    20: "Corneria",
    22: "Yoshi's Island N64",
    24: "Mushroom Kingdom II",
    28: "Dream Land N64",
    31: "Battlefield",
    32: "Final Destination",
}

# Game-end method values
METHOD_GAME        = 2  # stocks ran out — use final stocks to determine winner
METHOD_NO_CONTEST  = 7  # someone quit mid-game (LRAS)


# ---------------------------------------------------------------------------
# Core binary parser
# ---------------------------------------------------------------------------

def _parse_event_stream(raw: bytes) -> dict:
    """
    Walk the raw Slippi event stream and extract:
      - match_id (str)
      - stage_id (int)
      - game_end_method (int)
      - lras_initiator (int, -1 = none)
      - final_stocks (dict port → stocks)
      - duration_frames (int)
    """
    raw_len = struct.unpack_from(">i", raw, 11)[0]
    events_start = 15
    events_end = events_start + raw_len

    # Parse payload sizes from the Event Payloads event (0x35)
    assert raw[events_start] == 0x35, f"Expected 0x35 at byte 15, got {hex(raw[events_start])}"
    ep_size = raw[events_start + 1]
    pair_count = (ep_size - 1) // 3
    payload_sizes: dict[int, int] = {}
    for i in range(pair_count):
        off = events_start + 2 + i * 3
        cmd = raw[off]
        size = struct.unpack_from(">H", raw, off + 1)[0]
        payload_sizes[cmd] = size

    # Walk the stream starting AFTER the 0x35 event
    pos = events_start + 1 + ep_size
    match_id = ""
    stage_id = -1
    game_end_method = -1
    lras_initiator = -1
    final_stocks: dict[int, int] = {}
    duration_frames = 0

    while pos < events_end:
        cmd = raw[pos]
        if cmd not in payload_sizes:
            pos += 1
            continue
        size = payload_sizes[cmd]
        payload = raw[pos + 1 : pos + 1 + size]

        if cmd == 0x36:  # GAME_START
            # stage_id is a uint8 at payload byte 19 (not uint16 — reading as
            # uint16 big-endian multiplies the value by 256)
            if size >= 20:
                stage_id = payload[19]
            # match_id: search for 'mode.' string within the payload
            mi_idx = payload.find(b"mode.")
            if mi_idx != -1:
                match_id = payload[mi_idx : mi_idx + 60].split(b"\x00")[0].decode(
                    "utf-8", errors="replace"
                )

        elif cmd == 0x38:  # POST_FRAME — track last known stocks per port
            # Offset 0x04 = player index, 0x05 = is_follower, 0x20 (32) = stocks remaining
            # (0x06 is internal_char_id — an earlier version of this code read that by
            # mistake, making win/loss depend on char ID rather than actual stocks)
            if size >= 33:
                port = payload[4]
                is_follower = payload[5]
                stocks = payload[32]  # 0x20 = stocks remaining
                if not is_follower and 0 <= port <= 3:
                    final_stocks[port] = stocks
                    frame_num = struct.unpack_from(">i", payload, 0)[0]
                    duration_frames = max(duration_frames, frame_num)

        elif cmd == 0x39:  # GAME_END
            if size >= 2:
                game_end_method = payload[0]
                lras_initiator = struct.unpack_from("b", payload, 1)[0]

        pos += 1 + size

    return {
        "match_id": match_id,
        "stage_id": stage_id,
        "game_end_method": game_end_method,
        "lras_initiator": lras_initiator,
        "final_stocks": final_stocks,
        "duration_frames": duration_frames,
    }


def _parse_metadata(raw: bytes) -> dict:
    """
    Extract connect codes, character IDs, and timestamp directly from the
    UBJSON metadata block at the end of the .slp file bytes.

    .slp file layout (top-level UBJSON object):
      Bytes  0-14 : UBJSON header + raw event stream length (4-byte big-endian at 11-14)
      Bytes 15 to 15+raw_len-1 : raw event stream
      Bytes 15+raw_len to +9   : UBJSON key "U\x08metadata" (10 bytes)
      Bytes 15+raw_len+10 : start of metadata UBJSON value
      Last byte              : closing '}' of the top-level object

    By slicing directly to the metadata value we skip all frame data, which
    is what made SlippiGame slow.
    """
    raw_len = struct.unpack_from(">i", raw, 11)[0]
    meta_start = 15 + raw_len + 10  # skip event stream + 10-byte "metadata" key
    meta_bytes = raw[meta_start:-1]  # -1 strips the top-level closing '}'

    try:
        meta = _load_ubjson(meta_bytes)
    except Exception:
        return {"players": {}, "timestamp": ""}

    players: dict[int, dict] = {}
    for port_str, pdata in meta.get("players", {}).items():
        port = int(port_str)
        chars = pdata.get("characters", {})
        # Primary character = the one played for the most frames
        primary_char_id = max(chars, key=lambda k: chars[k]) if chars else None
        players[port] = {
            "connect_code": pdata.get("names", {}).get("code", ""),
            "display_name": pdata.get("names", {}).get("netplay", ""),
            "char_id": int(primary_char_id) if primary_char_id is not None else None,
        }

    return {"players": players, "timestamp": meta.get("startAt", "")}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_replay(path: str) -> list[dict]:
    """
    Parse a single .slp file. Returns a list of game dicts — one per player
    with a connect code — ready for DB insertion. Returns an empty list if the
    file should be skipped (no match_id, parse error, ambiguous result, etc.).

    Both players' perspectives are returned so a single scan populates every
    connect code's DB without needing to re-read files.
    """
    filename = os.path.basename(path)

    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError:
        return []

    # --- Quick binary scan for match_id (cheap filter before full parse) ---
    mi_idx = raw.find(b"mode.")
    if mi_idx == -1:
        return []  # pre-ranked file, no match_id
    match_id_quick = raw[mi_idx : mi_idx + 60].split(b"\x00")[0].decode("utf-8", errors="replace")
    match_type_raw = match_id_quick.split("-")[0]  # e.g. "mode.ranked"
    match_type = match_type_raw.replace("mode.", "")  # "ranked", "unranked", "direct", "teams"

    # --- Full event stream parse ---
    try:
        stream = _parse_event_stream(raw)
    except Exception:
        return []

    # --- Metadata (connect codes, characters, timestamp) ---
    try:
        meta = _parse_metadata(raw)
    except Exception:
        return []

    players = meta["players"]
    ports = list(players.keys())
    if len(ports) < 2:
        return []

    method = stream["game_end_method"]
    lras = stream["lras_initiator"]
    final_stocks = stream["final_stocks"]

    games = []
    for player_port in ports:
        opp_port = next((p for p in ports if p != player_port), None)
        if opp_port is None:
            continue

        player_stocks = final_stocks.get(player_port, -1)
        opp_stocks = final_stocks.get(opp_port, -1)

        if method == METHOD_GAME:
            if player_stocks > opp_stocks:
                result = "win"
            elif player_stocks < opp_stocks:
                result = "loss"
            else:
                result = "unknown"
        elif method == METHOD_NO_CONTEST:
            if lras == player_port:
                result = "lras_loss"
            elif lras >= 0:
                result = "lras_win"
            else:
                result = "unknown"
        else:
            result = "unknown"

        if result == "unknown":
            continue

        player_data = players[player_port]
        opp_data = players[opp_port]
        player_code = player_data.get("connect_code", "")
        if not player_code:
            continue

        games.append({
            "filename": filename,
            "filepath": path,
            "timestamp": meta["timestamp"] or "",
            "match_type": match_type,
            "player_code": player_code,
            "player_port": player_port,
            "player_char_id": player_data.get("char_id"),
            "opponent_code": opp_data.get("connect_code", ""),
            "opponent_char_id": opp_data.get("char_id"),
            "stage_id": stream["stage_id"],
            "result": result,
            "duration_frames": stream["duration_frames"],
            "match_id": stream["match_id"],
        })

    return games


def scan_directory(
    directory: str,
    known_filenames: set[str],
    progress_callback=None,
) -> tuple[list[dict], set[str]]:
    """
    Scan a directory for new .slp files and parse both players' perspectives
    from each game. Returns (game_dicts, processed_filenames).

    - game_dicts: one dict per player per game, ready for DB insertion
    - processed_filenames: every filename that was read (used to update the
      shared scanned-files tracker so future scans skip them)

    Only processes files not already in known_filenames.
    Uses a thread pool to parallelize file I/O across CPU cores.
    progress_callback(current, total, filename) is called as files complete.
    """
    slp_files = [
        f for f in Path(directory).rglob("*.slp")
        if f.name not in known_filenames
    ]
    slp_files.sort()  # chronological by filename

    results: list[dict] = []
    processed: set[str] = set()
    total = len(slp_files)
    if total == 0:
        return results, processed

    # Show total count immediately so the user sees it found files
    if progress_callback:
        progress_callback(0, total, "")

    # Cap workers — too many threads doing disk I/O simultaneously causes thrashing
    workers = min(8, os.cpu_count() or 4)
    completed = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_path = {
            executor.submit(parse_replay, str(p)): p
            for p in slp_files
        }
        for future in as_completed(future_to_path):
            completed += 1
            fname = future_to_path[future].name
            processed.add(fname)
            try:
                games = future.result()
            except Exception:
                games = []
            results.extend(games)
            if progress_callback:
                progress_callback(completed, total, fname)

    return results, processed


def character_name(char_id: int | None) -> str:
    if char_id is None:
        return "Unknown"
    return CHARACTER_NAMES.get(char_id, f"Char #{char_id}")


def stage_name(stage_id: int | None) -> str:
    if stage_id is None:
        return "Unknown"
    return STAGE_NAMES.get(stage_id, f"Stage #{stage_id}")
