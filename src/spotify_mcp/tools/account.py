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


def _url_elicitation_refused(ctx: Context) -> bool:
    """Whether the client told us it does *not* handle URL-mode elicitation.

    Only an explicit `elicitation` declaration that omits `url` counts. A client
    that declares nothing has not refused anything: capabilities can arrive per
    request rather than at initialize, so treating silence as "unsupported"
    means never sending the prompt at all.
    """
    capabilities = ctx.client_capabilities
    if capabilities is None:
        return False
    elicitation = getattr(capabilities, "elicitation", None)
    if elicitation is None:
        return False
    return getattr(elicitation, "url", None) is None


def _manual_fallback(url: str, reason: str) -> RuntimeError:
    """Turn an unusable prompt into a tool error that still carries the URL."""
    return RuntimeError(
        f"{reason} Open this URL in your browser to finish signing in, then call "
        f"`auth_status` to confirm:\n{url}"
    )


@mcp.tool()
async def auth_status(ctx: Context) -> str:
    """Check whether this server is configured and signed in to Spotify.

    Use this when a Spotify tool fails, or to verify setup after installing.

    Returns the credential and sign-in state plus the exact next step to take.
    """
    # Reported because a silent fallback to "open this URL yourself" is
    # otherwise indistinguishable from the sign-in prompt simply not appearing.
    url_prompts = "refused by client" if _url_elicitation_refused(ctx) else "will be attempted"

    missing = missing_credentials()
    if missing:
        return json.dumps({
            "configured": False,
            "signed_in": False,
            "env_file": str(ENV_FILE),
            "missing": missing,
            "url_prompts": url_prompts,
            "next_step": setup_hint(),
        }, indent=2)

    if not has_tokens():
        return json.dumps({
            "configured": True,
            "signed_in": False,
            "env_file": str(ENV_FILE),
            "url_prompts": url_prompts,
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
    # Failures raise: a JSON body saying "failed" is still a successful tool
    # result, so the client reports the sign-in as having gone through.
    if missing_credentials():
        raise RuntimeError(setup_hint())

    elicitation_id = f"spotify-auth-{secrets.token_urlsafe(8)}"
    prompt_sent = False

    async def present(url: str) -> bool:
        nonlocal prompt_sent
        if _url_elicitation_refused(ctx):
            raise _manual_fallback(
                url, "This client does not support server-initiated URL prompts."
            )

        try:
            result = await ctx.elicit_url(
                message="Authorize spotify-mcp to access your Spotify account.",
                url=url,
                elicitation_id=elicitation_id,
            )
        except Exception as exc:  # noqa: BLE001 — any transport failure is the same to us
            raise _manual_fallback(
                url, f"Could not show the authorization prompt ({exc})."
            ) from exc

        prompt_sent = True
        if result.action != "accept":
            raise RuntimeError(
                f"Authorization was {result.action}ed. Call `authenticate` again "
                "to retry."
            )
        return True

    try:
        await authorize(present)
    finally:
        if prompt_sent:
            await ctx.session.send_elicit_complete(elicitation_id)

    async with SpotifyClient() as sp:
        me = await sp.get("me")

    return json.dumps({
        "status": "signed_in",
        "display_name": me.get("display_name"),
        "user_id": me.get("id"),
        "token_file": str(TOKEN_FILE),
    }, indent=2)
