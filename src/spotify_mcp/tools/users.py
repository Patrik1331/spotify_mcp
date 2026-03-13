"""User profile MCP tools."""

from __future__ import annotations

import json
from typing import Any

from ..app import mcp
from ..client import SpotifyClient


@mcp.tool()
async def get_current_user() -> str:
    """Get the current user's Spotify profile.

    Returns the user's display name, ID, and profile URL.
    """
    async with SpotifyClient() as sp:
        data = await sp.get("me")

    return json.dumps({
        "id": data.get("id"),
        "display_name": data.get("display_name"),
        "uri": data.get("uri"),
        "external_urls": data.get("external_urls"),
        "images": data.get("images"),
    }, indent=2)


@mcp.tool()
async def get_top_artists(
    time_range: str = "medium_term", limit: int = 20, offset: int = 0,
) -> str:
    """Get the current user's top artists.

    Args:
        time_range: Time range — "short_term" (last 4 weeks), "medium_term"
                    (last 6 months, default), or "long_term" (all time).
        limit: Max artists to return (1-50, default 20).
        offset: Index of first artist (default 0).

    Returns list of top artists with genres.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(
            "me/top/artists",
            params={"time_range": time_range, "limit": limit, "offset": offset},
        )

    artists: list[dict[str, Any]] = []
    for a in data.get("items", []):
        artists.append({
            "id": a["id"],
            "name": a.get("name"),
            "genres": a.get("genres", []),
            "uri": a.get("uri"),
            "external_url": a.get("external_urls", {}).get("spotify"),
        })

    return json.dumps({
        "artists": artists,
        "total": data.get("total", 0),
        "time_range": time_range,
    }, indent=2)


@mcp.tool()
async def get_top_tracks(
    time_range: str = "medium_term", limit: int = 20, offset: int = 0,
) -> str:
    """Get the current user's top tracks.

    Args:
        time_range: Time range — "short_term" (last 4 weeks), "medium_term"
                    (last 6 months, default), or "long_term" (all time).
        limit: Max tracks to return (1-50, default 20).
        offset: Index of first track (default 0).

    Returns list of top tracks with artists and albums.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(
            "me/top/tracks",
            params={"time_range": time_range, "limit": limit, "offset": offset},
        )

    tracks: list[dict[str, Any]] = []
    for t in data.get("items", []):
        tracks.append({
            "id": t["id"],
            "name": t.get("name"),
            "artists": [a["name"] for a in t.get("artists", [])],
            "album": t.get("album", {}).get("name"),
            "duration_ms": t.get("duration_ms"),
            "uri": t.get("uri"),
            "external_url": t.get("external_urls", {}).get("spotify"),
        })

    return json.dumps({
        "tracks": tracks,
        "total": data.get("total", 0),
        "time_range": time_range,
    }, indent=2)
