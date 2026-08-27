"""MCP server entry point for spotify-mcp."""

from .app import mcp  # noqa: F401 — re-export for convenience

# Import tools modules to trigger @mcp.tool() registration
from .tools import account as account  # noqa: F401
from .tools import albums as albums  # noqa: F401
from .tools import artists as artists  # noqa: F401
from .tools import audiobooks as audiobooks  # noqa: F401
from .tools import bpm as bpm  # noqa: F401
from .tools import library as library  # noqa: F401
from .tools import player as player  # noqa: F401
from .tools import playlists as playlists  # noqa: F401
from .tools import search as search  # noqa: F401
from .tools import shows as shows  # noqa: F401
from .tools import tracks as tracks  # noqa: F401
from .tools import users as users  # noqa: F401


def main():
    """Start the MCP server with stdio transport."""
    mcp.run(transport="stdio")
