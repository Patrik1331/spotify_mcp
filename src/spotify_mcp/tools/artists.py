"""Artist MCP tools."""

from __future__ import annotations

import json
from typing import Any

from ..app import mcp
from ..client import SpotifyClient


@mcp.tool()
async def get_artist(artist_id: str) -> str:
    """Get details for a Spotify artist.

    Args:
        artist_id: The Spotify artist ID.

    Returns artist name, genres, images, and URI.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(f"artists/{artist_id}")

    return json.dumps({
        "id": data["id"],
        "name": data.get("name"),
        "genres": data.get("genres", []),
        "uri": data.get("uri"),
        "external_url": data.get("external_urls", {}).get("spotify"),
        "images": data.get("images", []),
    }, indent=2)


@mcp.tool()
async def get_artist_albums(
    artist_id: str,
    include_groups: str = "album,single",
    limit: int = 50,
    offset: int = 0,
) -> str:
    """Get an artist's albums.

    Args:
        artist_id: The Spotify artist ID.
        include_groups: Comma-separated album types to include.
                        Valid values: album, single, appears_on, compilation.
                        Default: "album,single".
        limit: Max albums to return (1-50, default 50).
        offset: Index of first album (default 0).

    Returns list of albums with release dates and track counts.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(
            f"artists/{artist_id}/albums",
            params={
                "include_groups": include_groups,
                "limit": limit,
                "offset": offset,
            },
        )

    albums: list[dict[str, Any]] = []
    for a in data.get("items", []):
        albums.append({
            "id": a["id"],
            "name": a.get("name"),
            "album_type": a.get("album_type"),
            "release_date": a.get("release_date"),
            "total_tracks": a.get("total_tracks"),
            "uri": a.get("uri"),
        })

    return json.dumps({
        "albums": albums,
        "total": data.get("total", 0),
        "has_next": data.get("next") is not None,
    }, indent=2)


