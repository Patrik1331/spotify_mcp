"""Album MCP tools."""

from __future__ import annotations

import json
from typing import Any

from ..app import mcp
from ..client import SpotifyClient


@mcp.tool()
async def get_album(album_id: str) -> str:
    """Get details for a Spotify album.

    Args:
        album_id: The Spotify album ID.

    Returns album name, artists, release date, tracks, and URI.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(f"albums/{album_id}")

    return json.dumps({
        "id": data["id"],
        "name": data.get("name"),
        "artists": [a["name"] for a in data.get("artists", [])],
        "release_date": data.get("release_date"),
        "total_tracks": data.get("total_tracks"),
        "album_type": data.get("album_type"),
        "label": data.get("label"),
        "uri": data.get("uri"),
        "external_url": data.get("external_urls", {}).get("spotify"),
        "images": data.get("images", []),
    }, indent=2)


@mcp.tool()
async def get_album_tracks(album_id: str, limit: int = 50, offset: int = 0) -> str:
    """Get tracks from an album.

    Args:
        album_id: The Spotify album ID.
        limit: Max tracks to return (1-50, default 50).
        offset: Index of first track (default 0).

    Returns list of tracks with name, artists, duration, and track number.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(
            f"albums/{album_id}/tracks",
            params={"limit": limit, "offset": offset},
        )

    tracks: list[dict[str, Any]] = []
    for t in data.get("items", []):
        tracks.append({
            "id": t["id"],
            "name": t.get("name"),
            "artists": [a["name"] for a in t.get("artists", [])],
            "track_number": t.get("track_number"),
            "disc_number": t.get("disc_number"),
            "duration_ms": t.get("duration_ms"),
            "uri": t.get("uri"),
        })

    return json.dumps({
        "tracks": tracks,
        "total": data.get("total", 0),
        "has_next": data.get("next") is not None,
    }, indent=2)


@mcp.tool()
async def get_saved_albums(limit: int = 50, offset: int = 0) -> str:
    """Get albums saved in the current user's library.

    Args:
        limit: Max albums to return (1-50, default 50).
        offset: Index of first album (default 0).

    Returns list of saved albums with added_at timestamps.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(
            "me/albums",
            params={"limit": limit, "offset": offset},
        )

    albums: list[dict[str, Any]] = []
    for item in data.get("items", []):
        album = item.get("album", {})
        albums.append({
            "added_at": item.get("added_at"),
            "id": album.get("id"),
            "name": album.get("name"),
            "artists": [a["name"] for a in album.get("artists", [])],
            "release_date": album.get("release_date"),
            "total_tracks": album.get("total_tracks"),
            "uri": album.get("uri"),
        })

    return json.dumps({
        "albums": albums,
        "total": data.get("total", 0),
        "has_next": data.get("next") is not None,
    }, indent=2)
