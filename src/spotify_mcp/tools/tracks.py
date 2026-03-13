"""Track MCP tools."""

from __future__ import annotations

import json

from ..app import mcp
from ..client import SpotifyClient


@mcp.tool()
async def get_track(track_id: str) -> str:
    """Get details for a Spotify track.

    Args:
        track_id: The Spotify track ID.

    Returns track name, artists, album, duration, and URI.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(f"tracks/{track_id}")

    return json.dumps({
        "id": data["id"],
        "name": data.get("name"),
        "artists": [a["name"] for a in data.get("artists", [])],
        "album": data.get("album", {}).get("name"),
        "album_id": data.get("album", {}).get("id"),
        "duration_ms": data.get("duration_ms"),
        "explicit": data.get("explicit"),
        "track_number": data.get("track_number"),
        "disc_number": data.get("disc_number"),
        "uri": data.get("uri"),
        "external_url": data.get("external_urls", {}).get("spotify"),
        "preview_url": data.get("preview_url"),
    }, indent=2)
