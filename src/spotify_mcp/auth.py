"""Spotify OAuth 2.0 Authorization Code + PKCE flow for MCP server."""

import asyncio
import base64
import hashlib
import json
import os
import secrets
import ssl
import threading
import time
import webbrowser
from collections.abc import Awaitable, Callable
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from dotenv import load_dotenv

CONFIG_DIR = Path.home() / ".claude-mcp" / "spotify-mcp"
ENV_FILE = CONFIG_DIR / ".env"

ENV_TEMPLATE = """\
# Spotify credentials for spotify-mcp.
# Get them at https://developer.spotify.com/dashboard (Settings -> Client ID).
# The redirect URI must match your Spotify app exactly; Spotify rejects
# `localhost`, so use the loopback IP: http://127.0.0.1:8888/callback
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=

# Optional: enables get_track_bpm / get_playlist_bpm (Spotify has no tempo
# data of its own). Free key at https://getsongbpm.com/api
GETSONGBPM_API_KEY=
"""


def _ensure_env_file() -> None:
    """Create an empty .env template on first run so there is something to fill in.

    Never raises: a read-only home directory must not stop the server from
    starting, since the credentials may also come from the process environment.
    """
    try:
        if ENV_FILE.exists():
            return
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        ENV_FILE.write_text(ENV_TEMPLATE, encoding="utf-8")
    except OSError:
        pass


# An MCP client launches this server from an arbitrary working directory, so a
# bare load_dotenv() cannot find the credentials. Read them from a fixed path
# instead; the repo-local .env stays as a development fallback (load_dotenv
# never overrides values that are already set).
_ensure_env_file()
load_dotenv(ENV_FILE)
load_dotenv()

SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
SPOTIFY_CLIENT_SECRET: str = os.getenv("SPOTIFY_CLIENT_SECRET", "")
SPOTIFY_REDIRECT_URI: str = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

SCOPES = " ".join([
    "user-read-private",
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "user-read-recently-played",
    "user-top-read",
    "user-library-read",
    "user-library-modify",
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
])

TOKEN_DIR = CONFIG_DIR
TOKEN_FILE = TOKEN_DIR / "tokens.json"


def _generate_code_verifier() -> str:
    """Generate a random code verifier for PKCE (43-128 chars, URL-safe)."""
    return secrets.token_urlsafe(64)[:128]


def _generate_code_challenge(verifier: str) -> str:
    """Generate S256 code challenge from the verifier."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _save_tokens(tokens: dict[str, Any]) -> None:
    """Persist tokens to ~/.spotify_mcp/tokens.json."""
    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tokens, indent=2), encoding="utf-8")


def _load_tokens() -> dict[str, Any] | None:
    """Load tokens from disk. Returns None if file doesn't exist."""
    if not TOKEN_FILE.exists():
        return None
    try:
        return json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _refresh_access_token(refresh_token: str) -> dict[str, Any]:
    """Use the refresh_token to obtain a new access_token."""
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": SPOTIFY_CLIENT_ID,
    }
    # Include client_secret if available (required for non-PKCE refresh in some cases)
    if SPOTIFY_CLIENT_SECRET:
        payload["client_secret"] = SPOTIFY_CLIENT_SECRET

    with httpx.Client() as client:
        resp = client.post(SPOTIFY_TOKEN_URL, data=payload)
        resp.raise_for_status()
        data = resp.json()

    tokens: dict[str, Any] = {
        "access_token": data["access_token"],
        "refresh_token": data.get("refresh_token", refresh_token),
        "expires_at": int(time.time()) + data["expires_in"],
        "token_type": data["token_type"],
    }
    _save_tokens(tokens)
    return tokens


def missing_credentials() -> list[str]:
    """Return the names of the credential variables that are not set."""
    required = {
        "SPOTIFY_CLIENT_ID": SPOTIFY_CLIENT_ID,
        "SPOTIFY_REDIRECT_URI": SPOTIFY_REDIRECT_URI,
    }
    return [name for name, value in required.items() if not value]


def has_tokens() -> bool:
    """Whether a stored token file with a refresh token exists."""
    tokens = _load_tokens()
    return tokens is not None and bool(tokens.get("refresh_token"))


def setup_hint() -> str:
    """Explain the current setup problem in terms of what to actually do next.

    A missing client id and a missing token look identical to a caller but need
    opposite fixes, so never collapse them into one message.
    """
    missing = missing_credentials()
    if missing:
        return (
            f"Spotify credentials are not configured: {', '.join(missing)} "
            f"{'is' if len(missing) == 1 else 'are'} empty in {ENV_FILE}. "
            "Fill the file in, then restart the MCP client so the server reloads it."
        )
    return (
        "Not signed in to Spotify. Call the `authenticate` tool to sign in "
        f"(or run `spotify-mcp-auth` from a shell). Tokens are stored in {TOKEN_FILE}."
    )


def get_tokens() -> dict[str, Any]:
    """Load tokens and refresh if expired. Raises if no tokens found.

    Returns a dict with keys: access_token, refresh_token, expires_at, token_type.
    """
    tokens = _load_tokens()
    if tokens is None:
        raise RuntimeError(setup_hint())

    # Refresh if expired (with 60s buffer)
    if tokens.get("expires_at", 0) < time.time() + 60:
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise RuntimeError(setup_hint())
        tokens = _refresh_access_token(refresh_token)

    return tokens


def refresh_access_token() -> dict[str, Any]:
    """Public wrapper: reload tokens from disk and refresh them.

    Used by the HTTP client when a 401 is received.
    """
    tokens = _load_tokens()
    if tokens is None or "refresh_token" not in tokens:
        raise RuntimeError(setup_hint())
    return _refresh_access_token(tokens["refresh_token"])


def build_authorization_request() -> tuple[str, str, str]:
    """Build the Spotify authorize URL for a fresh PKCE flow.

    Returns (auth_url, code_verifier, state). The caller must keep the verifier
    and state until the callback arrives.
    """
    if missing_credentials():
        raise RuntimeError(setup_hint())

    code_verifier = _generate_code_verifier()
    state = secrets.token_urlsafe(32)

    auth_params = urlencode({
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": _generate_code_challenge(code_verifier),
    })
    return f"{SPOTIFY_AUTH_URL}?{auth_params}", code_verifier, state


def _make_callback_server(state: str, result: dict[str, str | None]) -> HTTPServer:
    """Build the loopback HTTP server that catches Spotify's OAuth redirect.

    Writes the authorization code (or error) into *result*.
    """
    class CallbackHandler(BaseHTTPRequestHandler):
        """HTTP handler that captures the OAuth callback."""

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)

            # Ignore requests without OAuth params (favicon, preflight, etc.)
            if "code" not in params and "error" not in params:
                self._respond("Waiting for authorization...")
                return

            if "error" in params:
                result["error"] = params["error"][0]
                self._respond("Authorization failed. You can close this window.")
                return

            received_state = params.get("state", [None])[0]
            if received_state != state:
                result["error"] = "State mismatch"
                self._respond("State mismatch error. You can close this window.")
                return

            code = params.get("code", [None])[0]
            if code:
                result["code"] = code
                self._respond("Authorization successful! You can close this window.")
            else:
                result["error"] = "No authorization code received"
                self._respond("No code received. You can close this window.")

        def _respond(self, message: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            html = f"<html><body><h2>{message}</h2></body></html>"
            self.wfile.write(html.encode("utf-8"))

        def log_message(self, format: str, *args: Any) -> None:
            # Suppress default logging
            pass

    parsed_redirect = urlparse(SPOTIFY_REDIRECT_URI)
    default_port = 443 if parsed_redirect.scheme == "https" else 80
    server = HTTPServer(("localhost", parsed_redirect.port or default_port), CallbackHandler)

    # Wrap with SSL if redirect URI uses HTTPS
    if SPOTIFY_REDIRECT_URI.startswith("https://"):
        cert_dir = TOKEN_DIR / "certs"
        certfile = cert_dir / "localhost.crt"
        keyfile = cert_dir / "localhost.key"
        if not certfile.exists() or not keyfile.exists():
            server.server_close()
            raise RuntimeError(
                f"HTTPS redirect requires SSL certs at {cert_dir}/. "
                "Generate with: openssl req -x509 -newkey rsa:2048 "
                "-keyout localhost.key -out localhost.crt -days 365 -nodes -subj '/CN=localhost'"
            )
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.load_cert_chain(certfile=str(certfile), keyfile=str(keyfile))
        server.socket = ssl_ctx.wrap_socket(server.socket, server_side=True)

    return server


def exchange_code_for_tokens(code: str, code_verifier: str) -> dict[str, Any]:
    """Exchange an authorization code for tokens and persist them."""
    token_payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "client_id": SPOTIFY_CLIENT_ID,
        "code_verifier": code_verifier,
    }
    if SPOTIFY_CLIENT_SECRET:
        token_payload["client_secret"] = SPOTIFY_CLIENT_SECRET

    with httpx.Client() as client:
        resp = client.post(SPOTIFY_TOKEN_URL, data=token_payload)
        resp.raise_for_status()
        data = resp.json()

    tokens: dict[str, Any] = {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "expires_at": int(time.time()) + data["expires_in"],
        "token_type": data["token_type"],
    }
    _save_tokens(tokens)
    return tokens


async def authorize(
    present_url: Callable[[str], Awaitable[bool]],
    timeout: float = 300.0,
) -> dict[str, Any]:
    """Run the PKCE flow, delegating how the URL reaches the user to the caller.

    *present_url* receives the authorize URL and returns whether the user agreed
    to open it. This keeps the flow usable both from a terminal (open a browser)
    and from an MCP client (URL mode elicitation), without duplicating it.
    """
    auth_url, code_verifier, state = build_authorization_request()
    result: dict[str, str | None] = {"code": None, "error": None}
    server = _make_callback_server(state, result)
    server.timeout = 1.0  # poll, so the thread can notice `stop` and exit

    stop = threading.Event()
    loop = asyncio.get_running_loop()
    finished = asyncio.Event()

    def serve() -> None:
        while not stop.is_set() and result["code"] is None and result["error"] is None:
            server.handle_request()
        loop.call_soon_threadsafe(finished.set)

    thread = threading.Thread(target=serve, name="spotify-oauth-callback", daemon=True)
    thread.start()

    try:
        if not await present_url(auth_url):
            raise RuntimeError("Authorization was declined before the browser opened.")
        try:
            await asyncio.wait_for(finished.wait(), timeout)
        except TimeoutError:
            raise RuntimeError(
                f"Timed out after {int(timeout)}s waiting for the Spotify redirect. "
                "Make sure the redirect URI in your Spotify app matches "
                f"{SPOTIFY_REDIRECT_URI} exactly."
            ) from None
    finally:
        stop.set()
        server.server_close()

    if result["error"]:
        raise RuntimeError(f"Authorization failed: {result['error']}")
    if not result["code"]:
        raise RuntimeError("No authorization code received.")

    return exchange_code_for_tokens(result["code"], code_verifier)


def run_auth_flow() -> None:
    """Run the OAuth flow from a terminal, opening the browser directly."""

    async def open_in_browser(url: str) -> bool:
        print("Opening browser for Spotify authorization...")
        print(f"If it doesn't open automatically, visit:\n{url}\n")
        webbrowser.open(url)
        return True

    asyncio.run(authorize(open_in_browser))
    print("Tokens saved to", TOKEN_FILE)
    print("Authentication complete!")


if __name__ == "__main__":
    run_auth_flow()
