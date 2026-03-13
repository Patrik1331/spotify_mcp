"""Audiobooks & chapters MCP tools."""

from __future__ import annotations

import json
from typing import Any

from ..app import mcp
from ..client import SpotifyClient


@mcp.tool()
async def get_audiobook(audiobook_id: str) -> str:
    """Get details for a Spotify audiobook.

    Args:
        audiobook_id: The Spotify audiobook ID.

    Returns audiobook name, authors, narrators, description, and URI.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(f"audiobooks/{audiobook_id}")

    return json.dumps({
        "id": data["id"],
        "name": data.get("name"),
        "authors": [a.get("name") for a in data.get("authors", [])],
        "narrators": [n.get("name") for n in data.get("narrators", [])],
        "description": data.get("description", "")[:500],
        "total_chapters": data.get("total_chapters"),
        "languages": data.get("languages", []),
        "uri": data.get("uri"),
        "external_url": data.get("external_urls", {}).get("spotify"),
    }, indent=2)


@mcp.tool()
async def get_audiobook_chapters(
    audiobook_id: str, limit: int = 50, offset: int = 0,
) -> str:
    """Get chapters of an audiobook.

    Args:
        audiobook_id: The Spotify audiobook ID.
        limit: Max chapters to return (1-50, default 50).
        offset: Index of first chapter (default 0).

    Returns list of chapters with name, duration, and chapter number.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(
            f"audiobooks/{audiobook_id}/chapters",
            params={"limit": limit, "offset": offset},
        )

    chapters: list[dict[str, Any]] = []
    for c in data.get("items", []):
        chapters.append({
            "id": c["id"],
            "name": c.get("name"),
            "chapter_number": c.get("chapter_number"),
            "duration_ms": c.get("duration_ms"),
            "uri": c.get("uri"),
        })

    return json.dumps({
        "chapters": chapters,
        "total": data.get("total", 0),
        "has_next": data.get("next") is not None,
    }, indent=2)


@mcp.tool()
async def get_chapter(chapter_id: str) -> str:
    """Get details for a specific audiobook chapter.

    Args:
        chapter_id: The Spotify chapter ID.

    Returns chapter name, audiobook info, duration, and chapter number.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(f"chapters/{chapter_id}")

    return json.dumps({
        "id": data["id"],
        "name": data.get("name"),
        "chapter_number": data.get("chapter_number"),
        "duration_ms": data.get("duration_ms"),
        "audiobook": {
            "id": data.get("audiobook", {}).get("id"),
            "name": data.get("audiobook", {}).get("name"),
        },
        "uri": data.get("uri"),
        "external_url": data.get("external_urls", {}).get("spotify"),
    }, indent=2)
