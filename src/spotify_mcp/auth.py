"""Spotify OAuth 2.0 Authorization Code + PKCE flow for MCP server."""

import base64
import hashlib
import json
import os
import secrets
import ssl
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from dotenv import load_dotenv

CONFIG_DIR = Path.home() / ".spotify_mcp"

# An MCP client launches this server from an arbitrary working directory, so a
# bare load_dotenv() cannot find the credentials. Read them from a fixed path
# instead; the repo-local .env stays as a development fallback (load_dotenv
# never overrides values that are already set).
load_dotenv(CONFIG_DIR / ".env")
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


def get_tokens() -> dict[str, Any]:
    """Load tokens and refresh if expired. Raises if no tokens found.

    Returns a dict with keys: access_token, refresh_token, expires_at, token_type.
    """
    tokens = _load_tokens()
    if tokens is None:
        raise RuntimeError(
            "No Spotify tokens found. Run the auth flow first: spotify-mcp-auth"
        )

    # Refresh if expired (with 60s buffer)
    if tokens.get("expires_at", 0) < time.time() + 60:
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise RuntimeError(
                "Token expired and no refresh_token available. Re-run: spotify-mcp-auth"
            )
        tokens = _refresh_access_token(refresh_token)

    return tokens


def refresh_access_token() -> dict[str, Any]:
    """Public wrapper: reload tokens from disk and refresh them.

    Used by the HTTP client when a 401 is received.
    """
    tokens = _load_tokens()
    if tokens is None or "refresh_token" not in tokens:
        raise RuntimeError("No refresh token available. Re-run: spotify-mcp-auth")
    return _refresh_access_token(tokens["refresh_token"])


def run_auth_flow() -> None:
    """Run the full OAuth 2.0 Authorization Code + PKCE flow.

    Opens the browser for user authorization, starts a local server to receive
    the callback, exchanges the code for tokens, and persists them to disk.
    """
    if not SPOTIFY_CLIENT_ID:
        raise RuntimeError("SPOTIFY_CLIENT_ID not set. Add it to your .env file.")

    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(32)

    # Build authorization URL
    auth_params = urlencode({
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": SPOTIFY_REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge_method": "S256",
        "code_challenge": code_challenge,
    })
    auth_url = f"{SPOTIFY_AUTH_URL}?{auth_params}"

    # Container for the authorization code received via callback
    auth_result: dict[str, str | None] = {"code": None, "error": None}

    # Parse redirect URI to determine server port
    parsed_redirect = urlparse(SPOTIFY_REDIRECT_URI)
    default_port = 443 if parsed_redirect.scheme == "https" else 80
    server_port = parsed_redirect.port or default_port

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
                auth_result["error"] = params["error"][0]
                self._respond("Authorization failed. You can close this window.")
                return

            received_state = params.get("state", [None])[0]
            if received_state != state:
                auth_result["error"] = "State mismatch"
                self._respond("State mismatch error. You can close this window.")
                return

            code = params.get("code", [None])[0]
            if code:
                auth_result["code"] = code
                self._respond("Authorization successful! You can close this window.")
            else:
                auth_result["error"] = "No authorization code received"
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

    # Start local server, open browser, wait for callback
    server = HTTPServer(("localhost", server_port), CallbackHandler)

    # Wrap with SSL if redirect URI uses HTTPS
    if SPOTIFY_REDIRECT_URI.startswith("https://"):
        cert_dir = TOKEN_DIR / "certs"
        certfile = cert_dir / "localhost.crt"
        keyfile = cert_dir / "localhost.key"
        if not certfile.exists() or not keyfile.exists():
            raise RuntimeError(
                f"HTTPS redirect requires SSL certs at {cert_dir}/. "
                "Generate with: openssl req -x509 -newkey rsa:2048 "
                "-keyout localhost.key -out localhost.crt -days 365 -nodes -subj '/CN=localhost'"
            )
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=str(certfile), keyfile=str(keyfile))
        server.socket = ctx.wrap_socket(server.socket, server_side=True)

    print("Opening browser for Spotify authorization...")
    print(f"If it doesn't open automatically, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Handle requests until we get the OAuth callback (code or error)
    server.timeout = 120  # 2 minute timeout
    while auth_result["code"] is None and auth_result["error"] is None:
        server.handle_request()
    server.server_close()

    if auth_result["error"]:
        raise RuntimeError(f"Authorization failed: {auth_result['error']}")

    if not auth_result["code"]:
        raise RuntimeError("No authorization code received.")

    # Exchange authorization code for tokens
    token_payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": auth_result["code"],
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

    print("Tokens saved to", TOKEN_FILE)
    print("Authentication complete!")


if __name__ == "__main__":
    run_auth_flow()
