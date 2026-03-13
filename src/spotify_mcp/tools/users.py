"""User profile MCP tools."""

from __future__ import annotations

import json

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
