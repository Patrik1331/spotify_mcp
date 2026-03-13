"""Unified library MCP tools (Feb 2026 API).

The post-Feb 2026 unified library endpoints use full Spotify URIs
(e.g., "spotify:track:xxx") passed as query parameters.
"""

from __future__ import annotations

import json

from ..app import mcp
from ..client import SpotifyClient

# Map short type names to Spotify URI prefixes
_TYPE_PREFIX = {
    "tracks": "spotify:track:",
    "albums": "spotify:album:",
    "episodes": "spotify:episode:",
    "shows": "spotify:show:",
    "audiobooks": "spotify:audiobook:",
}


def _to_uris(ids: list[str], item_type: str) -> list[str]:
    """Convert plain IDs to full Spotify URIs if needed."""
    prefix = _TYPE_PREFIX.get(item_type, f"spotify:{item_type.rstrip('s')}:")
    return [
        uri if uri.startswith("spotify:") else f"{prefix}{uri}"
        for uri in ids[:50]
    ]


@mcp.tool()
async def save_to_library(ids: list[str], item_type: str = "tracks") -> str:
    """Save items to the current user's library.

    Args:
        ids: List of Spotify IDs or URIs to save (max 50).
             Can be plain IDs (e.g., "6habFhsOp2NvshLv26DqMb") or
             full URIs (e.g., "spotify:track:6habFhsOp2NvshLv26DqMb").
        item_type: Type of items — "tracks", "albums", "episodes", "shows", or "audiobooks".

    Returns confirmation of items saved.
    """
    uris = _to_uris(ids, item_type)

    async with SpotifyClient() as sp:
        await sp.put("me/library", params={"uris": ",".join(uris)})

    return json.dumps({"status": "saved", "count": len(uris), "type": item_type})


@mcp.tool()
async def remove_from_library(ids: list[str], item_type: str = "tracks") -> str:
    """Remove items from the current user's library.

    Args:
        ids: List of Spotify IDs or URIs to remove (max 50).
        item_type: Type of items — "tracks", "albums", "episodes", "shows", or "audiobooks".

    Returns confirmation of items removed.
    """
    uris = _to_uris(ids, item_type)

    async with SpotifyClient() as sp:
        await sp.delete("me/library", params={"uris": ",".join(uris)})

    return json.dumps({"status": "removed", "count": len(uris), "type": item_type})


@mcp.tool()
async def check_saved(ids: list[str], item_type: str = "tracks") -> str:
    """Check if items are saved in the current user's library.

    Args:
        ids: List of Spotify IDs or URIs to check (max 50).
        item_type: Type of items — "tracks", "albums", "episodes", "shows", or "audiobooks".

    Returns a map of ID to saved status (true/false).
    """
    uris = _to_uris(ids, item_type)

    async with SpotifyClient() as sp:
        data = await sp.get(
            "me/library/contains",
            params={"uris": ",".join(uris)},
        )

    results = {}
    if isinstance(data, list):
        for item_id, is_saved in zip(ids[:50], data):
            results[item_id] = is_saved
    else:
        results = data

    return json.dumps({"results": results, "type": item_type}, indent=2)
