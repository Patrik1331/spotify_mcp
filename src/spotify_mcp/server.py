"""MCP server entry point for spotify-mcp."""

from .app import mcp  # noqa: F401 — re-export for convenience

# Import tools modules to trigger @mcp.tool() registration
from .tools import playlists  # noqa: F401, E402
from .tools import users  # noqa: F401, E402
from .tools import dance_mix  # noqa: F401, E402


def main():
    """Start the MCP server with stdio transport."""
    mcp.run(transport="stdio")
