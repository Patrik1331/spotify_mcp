"""MCP server entry point for spotify-mcp."""

from .app import mcp  # noqa: F401 — re-export for convenience

# Import tools modules to trigger @mcp.tool() registration
from .tools import dance_mix as dance_mix  # noqa: F401
from .tools import playlists as playlists  # noqa: F401
from .tools import users as users  # noqa: F401


def main():
    """Start the MCP server with stdio transport."""
    mcp.run(transport="stdio")
