"""BPM lookup tools via the GetSongBPM third-party API.

Spotify retired its own tempo data (the old `/audio-features` endpoint —
see ROADMAP.md's removed-endpoints list); it exposes no BPM/tempo field for
any app anymore. This module matches each track's title/primary artist
against GetSongBPM (https://getsongbpm.com) instead, since no Spotify
alternative exists.
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from dotenv import load_dotenv

from ..app import mcp
from ..auth import CONFIG_DIR
from ..client import SpotifyClient
from .playlists import fetch_all_playlist_items

load_dotenv(CONFIG_DIR / ".env")
load_dotenv()

GETSONGBPM_API_KEY = os.getenv("GETSONGBPM_API_KEY", "")
GETSONGBPM_BASE_URL = "https://api.getsong.co/"


class BpmLookupError(Exception):
    """Raised when the BPM lookup cannot be performed (e.g. missing API key)."""


async def _getsongbpm_search(lookup: str) -> dict[str, Any]:
    """Raw call to the GetSongBPM search endpoint. Split out for testability."""
    async with httpx.AsyncClient(base_url=GETSONGBPM_BASE_URL, timeout=15.0) as client:
        response = await client.get(
            "search/",
            params={"api_key": GETSONGBPM_API_KEY, "type": "both", "lookup": lookup},
        )
        response.raise_for_status()
        return response.json()


async def _lookup_bpm(title: str, artist: str) -> dict[str, Any] | None:
    """Look up BPM for a single title/artist pair. Returns None if no match found."""
    if not GETSONGBPM_API_KEY:
        raise BpmLookupError(
            "GETSONGBPM_API_KEY is not set. Get a free key at "
            "https://getsongbpm.com/api and add it to "
            f"{CONFIG_DIR / '.env'}"
        )

    data = await _getsongbpm_search(f"song:{title} artist:{artist}")

    results: list[dict[str, Any]] = data.get("search", [])
    if not results:
        return None

    match = results[0]
    tempo = match.get("tempo")
    return {
        "bpm": float(tempo) if tempo is not None else None,
        "matched_title": match.get("title"),
        "matched_artist": match.get("artist", {}).get("name"),
        "source_url": match.get("uri"),
    }


@mcp.tool()
async def get_track_bpm(track_id: str) -> str:
    """Look up the BPM (tempo) of a Spotify track via an external BPM database.

    Spotify no longer exposes tempo data itself, so this matches the track's
    title and primary artist against GetSongBPM (https://getsongbpm.com).
    Requires GETSONGBPM_API_KEY to be set. Matching is by name, not audio
    fingerprint, so always check `matched_title`/`matched_artist` against
    what you expected.

    Args:
        track_id: The Spotify track ID.

    Returns BPM plus the matched title/artist, or found: false if no match.
    """
    async with SpotifyClient() as sp:
        track = await sp.get(f"tracks/{track_id}")

    title = track.get("name", "")
    track_artists: list[dict[str, Any]] = track.get("artists", [{}])
    artist = (track_artists[0] if track_artists else {}).get("name", "")

    try:
        match = await _lookup_bpm(title, artist)
    except BpmLookupError as e:
        return json.dumps({"error": str(e)})

    if match is None:
        return json.dumps({
            "track_id": track_id,
            "title": title,
            "artist": artist,
            "found": False,
            "bpm": None,
        })

    return json.dumps({
        "track_id": track_id,
        "title": title,
        "artist": artist,
        "found": True,
        **match,
    }, indent=2)


@mcp.tool()
async def get_playlist_bpm(playlist_id: str) -> str:
    """Look up BPM for every track in a playlist via an external BPM database.

    Spotify no longer exposes tempo data itself, so each track is matched by
    title/primary artist against GetSongBPM (https://getsongbpm.com).
    Requires GETSONGBPM_API_KEY to be set. Makes one lookup call per track,
    so large playlists take a while.

    Args:
        playlist_id: The Spotify playlist ID.

    Returns each track with its BPM (null if unmatched), plus a summary
    count of matched vs. unmatched tracks.
    """
    async with SpotifyClient() as sp:
        tracks = await fetch_all_playlist_items(sp, playlist_id)

    results: list[dict[str, Any]] = []
    matched = 0
    for t in tracks:
        title = t.get("track_name") or ""
        track_artists: list[str] = t.get("artists", [])
        artist = track_artists[0] if track_artists else ""

        try:
            match = await _lookup_bpm(title, artist)
        except BpmLookupError as e:
            return json.dumps({"error": str(e)})

        found = match is not None
        if found:
            matched += 1
        results.append({
            "track_id": t.get("track_id"),
            "title": title,
            "artist": artist,
            "found": found,
            "bpm": match["bpm"] if match else None,
        })

    return json.dumps({
        "tracks": results,
        "total": len(results),
        "matched": matched,
        "unmatched": len(results) - matched,
    }, indent=2)
