"""Setup and sign-in tools.

A stdio MCP server has no protocol-level way to report "I am connected but not
configured" — the client shows it as healthy either way. These tools make that
state inspectable and fixable from inside the client.
"""

from __future__ import annotations

import json
import secrets

from mcp.server.mcpserver import Context

from ..app import mcp
from ..auth import (
    ENV_FILE,
    TOKEN_FILE,
    authorize,
    has_tokens,
    missing_credentials,
    setup_hint,
)
from ..client import SpotifyClient


def _client_supports_url_elicitation(ctx: Context) -> bool:
    """Whether the connected client can show a URL-mode elicitation prompt."""
    capabilities = ctx.client_capabilities
    elicitation = getattr(capabilities, "elicitation", None) if capabilities else None
    return getattr(elicitation, "url", None) is not None


@mcp.tool()
async def auth_status() -> str:
    """Check whether this server is configured and signed in to Spotify.

    Use this when a Spotify tool fails, or to verify setup after installing.

    Returns the credential and sign-in state plus the exact next step to take.
    """
    missing = missing_credentials()
    if missing:
        return json.dumps({
            "configured": False,
            "signed_in": False,
            "env_file": str(ENV_FILE),
            "missing": missing,
            "next_step": setup_hint(),
        }, indent=2)

    if not has_tokens():
        return json.dumps({
            "configured": True,
            "signed_in": False,
            "env_file": str(ENV_FILE),
            "next_step": "Call the `authenticate` tool to sign in to Spotify.",
        }, indent=2)

    async with SpotifyClient() as sp:
        me = await sp.get("me")

    return json.dumps({
        "configured": True,
        "signed_in": True,
        "display_name": me.get("display_name"),
        "user_id": me.get("id"),
        "token_file": str(TOKEN_FILE),
    }, indent=2)


@mcp.tool()
async def authenticate(ctx: Context) -> str:
    """Sign in to Spotify, or re-authorize if the stored login stopped working.

    Opens Spotify's authorization page in your browser and waits for you to
    approve. Credentials never pass through the client — only the URL does.

    Returns the signed-in account, or what to fix if sign-in is not possible.
    """
    missing = missing_credentials()
    if missing:
        return json.dumps({
            "status": "not_configured",
            "env_file": str(ENV_FILE),
            "missing": missing,
            "next_step": setup_hint(),
        }, indent=2)

    elicitation_id = f"spotify-auth-{secrets.token_urlsafe(8)}"
    declined: dict[str, str] = {}

    async def present(url: str) -> bool:
        # Clients that don't implement URL mode must not be sent the request at
        # all, so fall back to handing the URL back as text.
        if not _client_supports_url_elicitation(ctx):
            declined["reason"] = (
                "This client cannot open authorization URLs for a server. "
                f"Open this URL manually to finish signing in:\n{url}"
            )
            return False
        result = await ctx.elicit_url(
            message="Authorize spotify-mcp to access your Spotify account.",
            url=url,
            elicitation_id=elicitation_id,
        )
        if result.action != "accept":
            declined["reason"] = f"Authorization was {result.action}ed."
            return False
        return True

    try:
        await authorize(present)
    except RuntimeError as exc:
        return json.dumps({
            "status": "failed",
            "reason": declined.get("reason") or str(exc),
        }, indent=2)
    finally:
        if _client_supports_url_elicitation(ctx):
            await ctx.session.send_elicit_complete(elicitation_id)

    async with SpotifyClient() as sp:
        me = await sp.get("me")

    return json.dumps({
        "status": "signed_in",
        "display_name": me.get("display_name"),
        "user_id": me.get("id"),
        "token_file": str(TOKEN_FILE),
    }, indent=2)
