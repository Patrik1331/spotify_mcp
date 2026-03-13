"""Search MCP tools."""

from __future__ import annotations

import json
from typing import Any

from ..app import mcp
from ..client import SpotifyClient


@mcp.tool()
async def search(
    query: str,
    types: str = "track",
    limit: int = 5,
    offset: int = 0,
) -> str:
    """Search Spotify for tracks, albums, artists, playlists, shows, episodes, or audiobooks.

    Args:
        query: Search query (e.g., "Despacito", "artist:Bad Bunny", "genre:bachata").
        types: Comma-separated list of item types to search for.
               Valid values: track, album, artist, playlist, show, episode, audiobook.
               Default: "track".
        limit: Max results per type (1-10, default 5).
        offset: Index of first result (default 0).

    Returns matching items grouped by type.
    """
    limit = min(max(limit, 1), 10)

    async with SpotifyClient() as sp:
        data = await sp.get(
            "search",
            params={
                "q": query,
                "type": types,
                "limit": limit,
                "offset": offset,
            },
        )

    results: dict[str, Any] = {}

    if "tracks" in data:
        results["tracks"] = [
            {
                "id": t["id"],
                "name": t["name"],
                "artists": [a["name"] for a in t.get("artists", [])],
                "album": t.get("album", {}).get("name"),
                "uri": t["uri"],
                "duration_ms": t.get("duration_ms"),
            }
            for t in data["tracks"].get("items", [])
        ]

    if "albums" in data:
        results["albums"] = [
            {
                "id": a["id"],
                "name": a["name"],
                "artists": [ar["name"] for ar in a.get("artists", [])],
                "release_date": a.get("release_date"),
                "total_tracks": a.get("total_tracks"),
                "uri": a["uri"],
            }
            for a in data["albums"].get("items", [])
        ]

    if "artists" in data:
        results["artists"] = [
            {
                "id": a["id"],
                "name": a["name"],
                "genres": a.get("genres", []),
                "uri": a["uri"],
            }
            for a in data["artists"].get("items", [])
        ]

    if "playlists" in data:
        results["playlists"] = [
            {
                "id": p["id"],
                "name": p["name"],
                "owner": p.get("owner", {}).get("display_name"),
                "tracks_total": p.get("items", {}).get("total", 0) if isinstance(p.get("items"), dict) else 0,
                "uri": p["uri"],
            }
            for p in data["playlists"].get("items", [])
        ]

    if "shows" in data:
        results["shows"] = [
            {
                "id": s["id"],
                "name": s["name"],
                "publisher": s.get("publisher"),
                "uri": s["uri"],
            }
            for s in data["shows"].get("items", [])
        ]

    if "episodes" in data:
        results["episodes"] = [
            {
                "id": e["id"],
                "name": e["name"],
                "duration_ms": e.get("duration_ms"),
                "uri": e["uri"],
            }
            for e in data["episodes"].get("items", [])
        ]

    if "audiobooks" in data:
        results["audiobooks"] = [
            {
                "id": ab["id"],
                "name": ab["name"],
                "authors": [a.get("name") for a in ab.get("authors", [])],
                "uri": ab["uri"],
            }
            for ab in data["audiobooks"].get("items", [])
        ]

    return json.dumps({"query": query, "results": results}, indent=2)
