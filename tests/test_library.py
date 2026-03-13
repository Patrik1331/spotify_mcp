"""Tests for library tools — validates post-Feb 2026 unified library API."""

from __future__ import annotations

import json

import pytest


# ── URI conversion (must use full spotify URIs, not plain IDs) ──────────────


@pytest.mark.asyncio
async def test_save_to_library_sends_uris_as_params(mock_spotify_client):
    """save_to_library must send URIs as query params, not JSON body."""
    mock_spotify_client.set_put_response("me/library", {})

    from spotify_mcp.tools.library import save_to_library
    result = json.loads(await save_to_library(["abc123"], "tracks"))

    assert result["status"] == "saved"
    assert result["count"] == 1

    put_calls = [c for c in mock_spotify_client.calls if c[0] == "PUT"]
    assert len(put_calls) == 1
    _, path, params, json_body = put_calls[0]
    assert path == "me/library"
    assert params == {"uris": "spotify:track:abc123"}
    assert json_body is None  # Must NOT send as JSON body


@pytest.mark.asyncio
async def test_save_to_library_converts_ids_to_uris(mock_spotify_client):
    """Plain IDs must be converted to full spotify:type:id URIs."""
    mock_spotify_client.set_put_response("me/library", {})

    from spotify_mcp.tools.library import save_to_library
    await save_to_library(["id1", "id2"], "albums")

    put_calls = [c for c in mock_spotify_client.calls if c[0] == "PUT"]
    params = put_calls[0][2]
    assert params["uris"] == "spotify:album:id1,spotify:album:id2"


@pytest.mark.asyncio
async def test_save_to_library_preserves_full_uris(mock_spotify_client):
    """Already-full URIs should not get double-prefixed."""
    mock_spotify_client.set_put_response("me/library", {})

    from spotify_mcp.tools.library import save_to_library
    await save_to_library(["spotify:track:abc"], "tracks")

    put_calls = [c for c in mock_spotify_client.calls if c[0] == "PUT"]
    params = put_calls[0][2]
    assert params["uris"] == "spotify:track:abc"  # Not spotify:track:spotify:track:abc


@pytest.mark.asyncio
async def test_remove_from_library_sends_uris_as_params(mock_spotify_client):
    mock_spotify_client.set_delete_response("me/library", {})

    from spotify_mcp.tools.library import remove_from_library
    result = json.loads(await remove_from_library(["abc123"], "tracks"))

    assert result["status"] == "removed"

    delete_calls = [c for c in mock_spotify_client.calls if c[0] == "DELETE"]
    _, path, params, json_body = delete_calls[0]
    assert path == "me/library"
    assert params == {"uris": "spotify:track:abc123"}
    assert json_body is None


@pytest.mark.asyncio
async def test_check_saved_sends_uris_as_params(mock_spotify_client):
    """check_saved must send URIs as comma-separated query param."""
    mock_spotify_client.set_response("me/library/contains", [True, False])

    from spotify_mcp.tools.library import check_saved
    result = json.loads(await check_saved(["id1", "id2"], "tracks"))

    assert result["results"]["id1"] is True
    assert result["results"]["id2"] is False

    get_calls = [c for c in mock_spotify_client.calls if c[0] == "GET"]
    params = get_calls[0][2]
    assert params["uris"] == "spotify:track:id1,spotify:track:id2"


@pytest.mark.asyncio
async def test_library_max_50_items(mock_spotify_client):
    """Library operations must cap at 50 items."""
    mock_spotify_client.set_put_response("me/library", {})

    ids = [f"id{i}" for i in range(60)]

    from spotify_mcp.tools.library import save_to_library
    result = json.loads(await save_to_library(ids, "tracks"))

    assert result["count"] == 50

    put_calls = [c for c in mock_spotify_client.calls if c[0] == "PUT"]
    uri_count = len(put_calls[0][2]["uris"].split(","))
    assert uri_count == 50


@pytest.mark.asyncio
async def test_library_supports_all_types(mock_spotify_client):
    """Verify URI prefix mapping for all supported item types."""
    from spotify_mcp.tools.library import _to_uris

    assert _to_uris(["x"], "tracks") == ["spotify:track:x"]
    assert _to_uris(["x"], "albums") == ["spotify:album:x"]
    assert _to_uris(["x"], "episodes") == ["spotify:episode:x"]
    assert _to_uris(["x"], "shows") == ["spotify:show:x"]
    assert _to_uris(["x"], "audiobooks") == ["spotify:audiobook:x"]
