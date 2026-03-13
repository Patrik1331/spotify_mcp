"""Shows & episodes MCP tools."""

from __future__ import annotations

import json
from typing import Any

from ..app import mcp
from ..client import SpotifyClient


@mcp.tool()
async def get_show(show_id: str) -> str:
    """Get details for a Spotify show (podcast).

    Args:
        show_id: The Spotify show ID.

    Returns show name, publisher, description, total episodes, and URI.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(f"shows/{show_id}")

    return json.dumps({
        "id": data["id"],
        "name": data.get("name"),
        "publisher": data.get("publisher"),
        "description": data.get("description"),
        "total_episodes": data.get("total_episodes"),
        "languages": data.get("languages", []),
        "uri": data.get("uri"),
        "external_url": data.get("external_urls", {}).get("spotify"),
        "images": data.get("images", []),
    }, indent=2)


@mcp.tool()
async def get_show_episodes(show_id: str, limit: int = 50, offset: int = 0) -> str:
    """Get episodes of a show.

    Args:
        show_id: The Spotify show ID.
        limit: Max episodes to return (1-50, default 50).
        offset: Index of first episode (default 0).

    Returns list of episodes with name, description, duration, and release date.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(
            f"shows/{show_id}/episodes",
            params={"limit": limit, "offset": offset},
        )

    episodes: list[dict[str, Any]] = []
    for e in data.get("items", []):
        episodes.append({
            "id": e["id"],
            "name": e.get("name"),
            "description": e.get("description", "")[:200],
            "duration_ms": e.get("duration_ms"),
            "release_date": e.get("release_date"),
            "uri": e.get("uri"),
        })

    return json.dumps({
        "episodes": episodes,
        "total": data.get("total", 0),
        "has_next": data.get("next") is not None,
    }, indent=2)


@mcp.tool()
async def get_episode(episode_id: str) -> str:
    """Get details for a specific episode.

    Args:
        episode_id: The Spotify episode ID.

    Returns episode name, show, description, duration, and release date.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(f"episodes/{episode_id}")

    return json.dumps({
        "id": data["id"],
        "name": data.get("name"),
        "description": data.get("description", "")[:500],
        "duration_ms": data.get("duration_ms"),
        "release_date": data.get("release_date"),
        "show": {
            "id": data.get("show", {}).get("id"),
            "name": data.get("show", {}).get("name"),
            "publisher": data.get("show", {}).get("publisher"),
        },
        "uri": data.get("uri"),
        "external_url": data.get("external_urls", {}).get("spotify"),
    }, indent=2)
