"""
Slippi GraphQL API client.
Rate-limited to 1 RPS per community convention.
No auth required — same API the slippi.gg website uses.
"""

import time
from datetime import datetime, timezone

import requests

SLIPPI_GQL_URL = "https://internal.slippi.gg/graphql"

HEADERS = {
    "content-type": "application/json",
    "accept": "*/*",
    "apollographql-client-name": "slippi-web",
}

PROFILE_QUERY = """
fragment profileFields on NetplayProfile {
  ratingOrdinal ratingUpdateCount wins losses
  dailyGlobalPlacement dailyRegionalPlacement continent
  characters { character gameCount }
}

fragment userProfilePage on User {
  displayName
  connectCode { code }
  rankedNetplayProfile { ...profileFields }
  rankedNetplayProfileHistory {
    ...profileFields
    season { id startedAt endedAt name status }
  }
}

query UserProfilePageQuery($cc: String, $uid: String) {
  getUser(fbUid: $uid, connectCode: $cc) {
    ...userProfilePage
  }
}
"""

_last_call_time: float = 0.0


def _rate_limit() -> None:
    global _last_call_time
    elapsed = time.time() - _last_call_time
    if elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_call_time = time.time()


def fetch_player_profile(connect_code: str) -> dict | None:
    """
    Fetch current ranked profile + season history for a player.
    Returns a normalized dict or None on failure.
    """
    _rate_limit()
    normalized = connect_code.upper().replace("/", "#")

    try:
        resp = requests.post(
            SLIPPI_GQL_URL,
            json={"query": PROFILE_QUERY, "variables": {"cc": normalized, "uid": None}},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        return {"error": str(exc)}

    try:
        body = resp.json()
    except Exception:
        return {"error": f"HTTP {resp.status_code} — non-JSON response: {resp.text[:300]}"}


    if "errors" in body:
        return {"error": body["errors"][0].get("message", "API error")}

    try:
        user = body["data"]["getUser"]
    except (KeyError, TypeError):
        return {"error": "Connect code not found"}

    if user is None:
        return {"error": "Connect code not found"}

    profile = user.get("rankedNetplayProfile") or {}
    history = user.get("rankedNetplayProfileHistory") or []

    # Normalize season history
    seasons = []
    for entry in history:
        season = entry.get("season") or {}
        seasons.append({
            "season_id": season.get("id"),
            "season_name": season.get("name"),
            "season_start": season.get("startedAt"),
            "season_end": season.get("endedAt"),
            "rating": entry.get("ratingOrdinal"),
            "wins": entry.get("wins"),
            "losses": entry.get("losses"),
        })

    return {
        "display_name": user.get("displayName", ""),
        "connect_code": connect_code.upper().replace("/", "#"),
        "snapshot": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "rating": profile.get("ratingOrdinal"),
            "wins": profile.get("wins"),
            "losses": profile.get("losses"),
            "global_rank": profile.get("dailyGlobalPlacement"),
            "regional_rank": profile.get("dailyRegionalPlacement"),
            "continent": profile.get("continent"),
        },
        "seasons": seasons,
    }
