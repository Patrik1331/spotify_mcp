"""Tests for playlist tools — validates post-Feb 2026 API format."""

from __future__ import annotations

import json

import pytest


# ── Post-Feb 2026 API: "tracks" field renamed to "items" ────────────────────


@pytest.mark.asyncio
async def test_get_my_playlists_uses_items_field(mock_spotify_client):
    """Track count must come from 'items.total', NOT 'tracks.total'."""
    mock_spotify_client.set_response("me/playlists", {
        "items": [
            {
                "id": "pl1",
                "name": "My Playlist",
                "items": {"href": "...", "total": 42},
                "owner": {"display_name": "Patrik"},
                "public": False,
                "uri": "spotify:playlist:pl1",
                "external_urls": {"spotify": "https://open.spotify.com/playlist/pl1"},
            },
        ],
        "total": 1,
    })

    from spotify_mcp.tools.playlists import get_my_playlists
    result = json.loads(await get_my_playlists(limit=50, offset=0))

    assert result["playlists"][0]["tracks_total"] == 42
    assert result["playlists"][0]["name"] == "My Playlist"


@pytest.mark.asyncio
async def test_get_my_playlists_handles_missing_items_field(mock_spotify_client):
    """If 'items' is None (shouldn't happen but safety), tracks_total should be 0."""
    mock_spotify_client.set_response("me/playlists", {
        "items": [
            {
                "id": "pl2",
                "name": "Empty",
                "items": None,
                "owner": {"display_name": "Patrik"},
                "public": False,
                "uri": "spotify:playlist:pl2",
                "external_urls": {"spotify": "..."},
            },
        ],
        "total": 1,
    })

    from spotify_mcp.tools.playlists import get_my_playlists
    result = json.loads(await get_my_playlists())

    assert result["playlists"][0]["tracks_total"] == 0


@pytest.mark.asyncio
async def test_get_playlist_uses_items_field(mock_spotify_client):
    """get_playlist must read track count from 'items.total'."""
    mock_spotify_client.set_response("playlists/abc123", {
        "id": "abc123",
        "name": "Test Playlist",
        "description": "Desc",
        "items": {"href": "...", "total": 99},
        "owner": {"display_name": "Patrik"},
        "public": True,
        "uri": "spotify:playlist:abc123",
        "external_urls": {"spotify": "https://open.spotify.com/playlist/abc123"},
    })

    from spotify_mcp.tools.playlists import get_playlist
    result = json.loads(await get_playlist("abc123"))

    assert result["tracks_total"] == 99


# ── Playlist items parsing (post-Feb 2026: "item" not "track") ──────────────


@pytest.mark.asyncio
async def test_get_playlist_items_parses_item_field(mock_spotify_client):
    """Post-Feb 2026 API uses 'item' key, not 'track', for playlist entries."""
    mock_spotify_client.set_response("playlists/pl1/items", {
        "items": [
            {
                "added_at": "2026-01-15T10:00:00Z",
                "item": {
                    "id": "t1",
                    "name": "Song One",
                    "uri": "spotify:track:t1",
                    "artists": [{"name": "Artist A"}],
                    "album": {"name": "Album X"},
                    "duration_ms": 200000,
                },
            },
        ],
        "total": 1,
        "next": None,
    })

    from spotify_mcp.tools.playlists import get_playlist_items
    result = json.loads(await get_playlist_items("pl1"))

    assert len(result["items"]) == 1
    assert result["items"][0]["track_name"] == "Song One"
    assert result["items"][0]["track_uri"] == "spotify:track:t1"
    assert result["items"][0]["added_at"] == "2026-01-15T10:00:00Z"
    assert result["items"][0]["artists"] == ["Artist A"]


@pytest.mark.asyncio
async def test_get_playlist_items_skips_null_tracks(mock_spotify_client):
    """Removed/unavailable tracks (item=None) should be skipped."""
    mock_spotify_client.set_response("playlists/pl1/items", {
        "items": [
            {"added_at": "2026-01-01T00:00:00Z", "item": None},
            {
                "added_at": "2026-02-01T00:00:00Z",
                "item": {
                    "id": "t2",
                    "name": "Valid Track",
                    "uri": "spotify:track:t2",
                    "artists": [{"name": "B"}],
                    "album": {"name": "Alb"},
                    "duration_ms": 180000,
                },
            },
        ],
        "total": 2,
        "next": None,
    })

    from spotify_mcp.tools.playlists import get_playlist_items
    result = json.loads(await get_playlist_items("pl1"))

    assert len(result["items"]) == 1
    assert result["items"][0]["track_name"] == "Valid Track"


# ── Remove items (post-Feb 2026: uses "items" array, not "uris") ───────────


@pytest.mark.asyncio
async def test_remove_items_sends_items_format(mock_spotify_client):
    """Must send {"items": [{"uri": "..."}]}, NOT {"uris": [...]}."""
    mock_spotify_client.set_delete_response("playlists/pl1/items", {"snapshot_id": "snap1"})

    from spotify_mcp.tools.playlists import remove_items_from_playlist
    result = json.loads(await remove_items_from_playlist("pl1", [
        "spotify:track:aaa",
        "spotify:track:bbb",
    ]))

    assert result["removed"] == 2
    assert result["snapshot_id"] == "snap1"

    # Verify the exact body format sent
    delete_calls = [c for c in mock_spotify_client.calls if c[0] == "DELETE"]
    assert len(delete_calls) == 1
    _, path, _, body = delete_calls[0]
    assert path == "playlists/pl1/items"
    assert body == {"items": [{"uri": "spotify:track:aaa"}, {"uri": "spotify:track:bbb"}]}


# ── Create and add items ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_playlist(mock_spotify_client):
    mock_spotify_client.set_post_response("me/playlists", {
        "id": "new_pl",
        "name": "My New Playlist",
        "uri": "spotify:playlist:new_pl",
        "external_urls": {"spotify": "https://open.spotify.com/playlist/new_pl"},
    })

    from spotify_mcp.tools.playlists import create_playlist
    result = json.loads(await create_playlist("My New Playlist", public=False))

    assert result["id"] == "new_pl"
    assert result["name"] == "My New Playlist"


@pytest.mark.asyncio
async def test_add_items_batches_over_100(mock_spotify_client):
    """URIs should be sent in batches of 100."""
    mock_spotify_client.set_post_response("playlists/pl1/items", {"snapshot_id": "s"})

    uris = [f"spotify:track:t{i}" for i in range(150)]

    from spotify_mcp.tools.playlists import add_items_to_playlist
    result = json.loads(await add_items_to_playlist("pl1", uris))

    assert result["added"] == 150
    post_calls = [c for c in mock_spotify_client.calls if c[0] == "POST"]
    assert len(post_calls) == 2  # 100 + 50
    assert len(post_calls[0][3]["uris"]) == 100
    assert len(post_calls[1][3]["uris"]) == 50


# ── Update and reorder ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_playlist_details(mock_spotify_client):
    mock_spotify_client.set_put_response("playlists/pl1", {})

    from spotify_mcp.tools.playlists import update_playlist_details
    result = json.loads(await update_playlist_details("pl1", name="New Name"))

    assert result["status"] == "updated"
    assert "name" in result["updated_fields"]


@pytest.mark.asyncio
async def test_update_playlist_no_fields_returns_error(mock_spotify_client):
    from spotify_mcp.tools.playlists import update_playlist_details
    result = json.loads(await update_playlist_details("pl1"))

    assert "error" in result


@pytest.mark.asyncio
async def test_reorder_playlist_items(mock_spotify_client):
    mock_spotify_client.set_put_response("playlists/pl1/items", {"snapshot_id": "snap2"})

    from spotify_mcp.tools.playlists import reorder_playlist_items
    result = json.loads(await reorder_playlist_items("pl1", range_start=3, insert_before=0))

    assert result["status"] == "reordered"
    put_calls = [c for c in mock_spotify_client.calls if c[0] == "PUT"]
    body = put_calls[0][3]
    assert body["range_start"] == 3
    assert body["insert_before"] == 0
    assert body["range_length"] == 1


# ── fetch_all_playlist_items pagination ─────────────────────────────────────


@pytest.mark.asyncio
async def test_fetch_all_handles_pagination(mock_spotify_client):
    """fetch_all_playlist_items must follow 'next' links until None."""
    page1 = {
        "items": [
            {
                "added_at": "2026-01-01T00:00:00Z",
                "item": {
                    "id": "t1", "name": "Track 1", "uri": "spotify:track:t1",
                    "artists": [{"name": "A"}], "album": {"name": "Alb"}, "duration_ms": 100000,
                },
            },
        ],
        "next": "https://api.spotify.com/v1/playlists/pl1/items?offset=100",
    }
    page2 = {
        "items": [
            {
                "added_at": "2026-02-01T00:00:00Z",
                "item": {
                    "id": "t2", "name": "Track 2", "uri": "spotify:track:t2",
                    "artists": [{"name": "B"}], "album": {"name": "Alb2"}, "duration_ms": 200000,
                },
            },
        ],
        "next": None,
    }

    call_count = 0

    async def mock_get(path, *, params=None):
        nonlocal call_count
        call_count += 1
        return page1 if call_count == 1 else page2

    mock_spotify_client.get = mock_get

    from spotify_mcp.tools.playlists import fetch_all_playlist_items
    items = await fetch_all_playlist_items(mock_spotify_client, "pl1")

    assert len(items) == 2
    assert items[0]["track_name"] == "Track 1"
    assert items[1]["track_name"] == "Track 2"
