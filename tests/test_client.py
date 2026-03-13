"""Tests for SpotifyClient — response handling edge cases."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from spotify_mcp.client import SpotifyClient, SpotifyAPIError


@pytest.fixture()
def mock_tokens():
    """Patch get_tokens to return fake tokens."""
    with patch("spotify_mcp.client.get_tokens", return_value={"access_token": "fake_token"}):
        yield


@pytest.mark.asyncio
async def test_handles_204_no_content(mock_tokens):
    """204 responses (no body) should return empty dict."""
    response = httpx.Response(204, content=b"")

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        async with SpotifyClient() as sp:
            result = await sp.put("me/player/pause")

    assert result == {}


@pytest.mark.asyncio
async def test_handles_200_empty_body(mock_tokens):
    """200 with empty body (library PUT/DELETE) should return empty dict."""
    response = httpx.Response(200, content=b"")

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        async with SpotifyClient() as sp:
            result = await sp.put("me/library", params={"uris": "spotify:track:abc"})

    assert result == {}


@pytest.mark.asyncio
async def test_handles_200_json_body(mock_tokens):
    """200 with JSON body should parse and return."""
    response = httpx.Response(200, json={"id": "abc"})

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        async with SpotifyClient() as sp:
            result = await sp.get("me")

    assert result == {"id": "abc"}


@pytest.mark.asyncio
async def test_raises_on_400(mock_tokens):
    """400 errors should raise SpotifyAPIError."""
    response = httpx.Response(400, json={"error": {"message": "Bad request"}})

    with patch("httpx.AsyncClient.request", new_callable=AsyncMock, return_value=response):
        async with SpotifyClient() as sp:
            with pytest.raises(SpotifyAPIError) as exc_info:
                await sp.get("bad/path")

    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_retries_on_401(mock_tokens):
    """401 should trigger token refresh and retry once."""
    response_401 = httpx.Response(401, json={"error": {"message": "Expired"}})
    response_200 = httpx.Response(200, json={"id": "ok"})

    mock_request = AsyncMock(side_effect=[response_401, response_200])

    with patch("httpx.AsyncClient.request", mock_request):
        with patch("spotify_mcp.client.refresh_access_token", return_value={"access_token": "new_token"}):
            async with SpotifyClient() as sp:
                result = await sp.get("me")

    assert result == {"id": "ok"}
    assert mock_request.call_count == 2
