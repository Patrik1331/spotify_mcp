"""Tests for setup diagnostics and the authorization request builder.

The point of these is that a missing client id and a missing token produce
*different* guidance — conflating them is what made the server look healthy
while being unusable.
"""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest

from spotify_mcp import auth


@pytest.fixture()
def configured(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Credentials present, token file redirected into a temp dir."""
    monkeypatch.setattr(auth, "SPOTIFY_CLIENT_ID", "test-client-id")
    monkeypatch.setattr(auth, "SPOTIFY_CLIENT_SECRET", "")
    monkeypatch.setattr(auth, "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    monkeypatch.setattr(auth, "TOKEN_FILE", tmp_path / "tokens.json")
    return tmp_path


def test_missing_credentials_lists_empty_vars(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(auth, "SPOTIFY_CLIENT_ID", "")
    monkeypatch.setattr(auth, "SPOTIFY_REDIRECT_URI", "")

    assert auth.missing_credentials() == ["SPOTIFY_CLIENT_ID", "SPOTIFY_REDIRECT_URI"]


def test_missing_credentials_empty_when_configured(configured):
    assert auth.missing_credentials() == []


def test_client_secret_is_not_required(monkeypatch: pytest.MonkeyPatch):
    """PKCE does not need a secret, so an empty one must not be reported missing."""
    monkeypatch.setattr(auth, "SPOTIFY_CLIENT_ID", "id")
    monkeypatch.setattr(auth, "SPOTIFY_CLIENT_SECRET", "")
    monkeypatch.setattr(auth, "SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")

    assert "SPOTIFY_CLIENT_SECRET" not in auth.missing_credentials()


def test_setup_hint_points_at_env_file_when_unconfigured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(auth, "SPOTIFY_CLIENT_ID", "")

    hint = auth.setup_hint()

    assert "SPOTIFY_CLIENT_ID" in hint
    assert str(auth.ENV_FILE) in hint
    assert "authenticate" not in hint  # signing in cannot help without credentials


def test_setup_hint_points_at_authenticate_when_configured(configured):
    hint = auth.setup_hint()

    assert "authenticate" in hint
    assert str(auth.TOKEN_FILE) in hint


def test_has_tokens_false_without_file(configured):
    assert auth.has_tokens() is False


def test_has_tokens_false_without_refresh_token(configured):
    auth.TOKEN_FILE.write_text(json.dumps({"access_token": "a"}), encoding="utf-8")

    assert auth.has_tokens() is False


def test_has_tokens_true_with_refresh_token(configured):
    auth.TOKEN_FILE.write_text(
        json.dumps({"access_token": "a", "refresh_token": "r"}), encoding="utf-8"
    )

    assert auth.has_tokens() is True


def test_get_tokens_error_names_the_env_file_when_unconfigured(
    monkeypatch: pytest.MonkeyPatch, configured
):
    monkeypatch.setattr(auth, "SPOTIFY_CLIENT_ID", "")

    with pytest.raises(RuntimeError, match="SPOTIFY_CLIENT_ID"):
        auth.get_tokens()


def test_build_authorization_request_uses_pkce(configured):
    url, verifier, state = auth.build_authorization_request()
    params = parse_qs(urlparse(url).query)

    assert params["client_id"] == ["test-client-id"]
    assert params["response_type"] == ["code"]
    assert params["code_challenge_method"] == ["S256"]
    assert params["state"] == [state]
    # The verifier itself must never leave the process
    assert verifier not in url
    assert params["code_challenge"][0] == auth._generate_code_challenge(verifier)


def test_build_authorization_request_refuses_without_credentials(
    monkeypatch: pytest.MonkeyPatch, configured
):
    monkeypatch.setattr(auth, "SPOTIFY_CLIENT_ID", "")

    with pytest.raises(RuntimeError, match="not configured"):
        auth.build_authorization_request()


@pytest.mark.asyncio
async def test_authorize_stops_when_user_declines(configured):
    """A declined prompt must fail fast, not hang on the callback server."""

    async def decline(url: str) -> bool:
        return False

    with pytest.raises(RuntimeError, match="declined"):
        await auth.authorize(decline, timeout=5.0)
