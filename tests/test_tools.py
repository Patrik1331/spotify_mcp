"""Tests for search, tracks, albums, artists, users, player, shows, audiobooks tools."""

from __future__ import annotations

import json

import pytest


# ═══════════════════════════════════════════════════════════════════════════
# Search
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_search_tracks(mock_spotify_client):
    mock_spotify_client.set_response("search", {
        "tracks": {
            "items": [
                {
                    "id": "t1",
                    "name": "Despacito",
                    "artists": [{"name": "Luis Fonsi"}],
                    "album": {"name": "VIDA"},
                    "uri": "spotify:track:t1",
                    "duration_ms": 229000,
                },
            ],
        },
    })

    from spotify_mcp.tools.search import search
    result = json.loads(await search("Despacito", types="track", limit=5))

    assert result["query"] == "Despacito"
    assert len(result["results"]["tracks"]) == 1
    assert result["results"]["tracks"][0]["name"] == "Despacito"


@pytest.mark.asyncio
async def test_search_clamps_limit_to_10(mock_spotify_client):
    """Post-Feb 2026 API max limit is 10."""
    mock_spotify_client.set_response("search", {"tracks": {"items": []}})

    from spotify_mcp.tools.search import search
    await search("test", limit=50)

    get_calls = [c for c in mock_spotify_client.calls if c[0] == "GET"]
    assert get_calls[0][2]["limit"] == 10


@pytest.mark.asyncio
async def test_search_multiple_types(mock_spotify_client):
    mock_spotify_client.set_response("search", {
        "tracks": {"items": []},
        "artists": {"items": [{"id": "a1", "name": "Bad Bunny", "genres": [], "uri": "spotify:artist:a1"}]},
    })

    from spotify_mcp.tools.search import search
    result = json.loads(await search("Bad Bunny", types="track,artist"))

    assert "tracks" in result["results"]
    assert "artists" in result["results"]


# ═══════════════════════════════════════════════════════════════════════════
# Tracks
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_track(mock_spotify_client):
    mock_spotify_client.set_response("tracks/t1", {
        "id": "t1",
        "name": "Test Track",
        "artists": [{"name": "Artist A"}, {"name": "Artist B"}],
        "album": {"name": "Album X", "id": "alb1"},
        "duration_ms": 200000,
        "explicit": False,
        "track_number": 3,
        "disc_number": 1,
        "uri": "spotify:track:t1",
        "external_urls": {"spotify": "https://open.spotify.com/track/t1"},
        "preview_url": None,
    })

    from spotify_mcp.tools.tracks import get_track
    result = json.loads(await get_track("t1"))

    assert result["name"] == "Test Track"
    assert result["artists"] == ["Artist A", "Artist B"]
    assert result["album"] == "Album X"
    assert result["duration_ms"] == 200000


# ═══════════════════════════════════════════════════════════════════════════
# Albums
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_album(mock_spotify_client):
    mock_spotify_client.set_response("albums/alb1", {
        "id": "alb1",
        "name": "Test Album",
        "artists": [{"name": "Artist"}],
        "release_date": "2025-06-01",
        "total_tracks": 12,
        "album_type": "album",
        "label": "Label X",
        "uri": "spotify:album:alb1",
        "external_urls": {"spotify": "..."},
        "images": [],
    })

    from spotify_mcp.tools.albums import get_album
    result = json.loads(await get_album("alb1"))

    assert result["name"] == "Test Album"
    assert result["total_tracks"] == 12


@pytest.mark.asyncio
async def test_get_saved_albums_parses_added_at(mock_spotify_client):
    mock_spotify_client.set_response("me/albums", {
        "items": [
            {
                "added_at": "2025-11-19T06:31:08Z",
                "album": {
                    "id": "alb1",
                    "name": "Saved Album",
                    "artists": [{"name": "A"}],
                    "release_date": "2020-01-01",
                    "total_tracks": 10,
                    "uri": "spotify:album:alb1",
                },
            },
        ],
        "total": 1,
        "next": None,
    })

    from spotify_mcp.tools.albums import get_saved_albums
    result = json.loads(await get_saved_albums())

    assert result["albums"][0]["added_at"] == "2025-11-19T06:31:08Z"
    assert result["albums"][0]["name"] == "Saved Album"


# ═══════════════════════════════════════════════════════════════════════════
# Artists
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_artist(mock_spotify_client):
    mock_spotify_client.set_response("artists/a1", {
        "id": "a1",
        "name": "Bad Bunny",
        "genres": ["reggaeton", "latin"],
        "uri": "spotify:artist:a1",
        "external_urls": {"spotify": "..."},
        "images": [],
    })

    from spotify_mcp.tools.artists import get_artist
    result = json.loads(await get_artist("a1"))

    assert result["name"] == "Bad Bunny"
    assert "reggaeton" in result["genres"]


# ═══════════════════════════════════════════════════════════════════════════
# Users
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_current_user(mock_spotify_client):
    mock_spotify_client.set_response("me", {
        "id": "user123",
        "display_name": "Patrik",
        "uri": "spotify:user:user123",
        "external_urls": {"spotify": "..."},
        "images": [],
    })

    from spotify_mcp.tools.users import get_current_user
    result = json.loads(await get_current_user())

    assert result["id"] == "user123"
    assert result["display_name"] == "Patrik"


@pytest.mark.asyncio
async def test_get_top_tracks(mock_spotify_client):
    mock_spotify_client.set_response("me/top/tracks", {
        "items": [
            {
                "id": "t1",
                "name": "Top Song",
                "artists": [{"name": "A"}],
                "album": {"name": "Alb"},
                "duration_ms": 180000,
                "uri": "spotify:track:t1",
                "external_urls": {"spotify": "..."},
            },
        ],
        "total": 1,
    })

    from spotify_mcp.tools.users import get_top_tracks
    result = json.loads(await get_top_tracks(time_range="short_term", limit=1))

    assert result["tracks"][0]["name"] == "Top Song"
    assert result["time_range"] == "short_term"


@pytest.mark.asyncio
async def test_get_top_artists(mock_spotify_client):
    mock_spotify_client.set_response("me/top/artists", {
        "items": [
            {
                "id": "a1",
                "name": "Top Artist",
                "genres": ["latin"],
                "uri": "spotify:artist:a1",
                "external_urls": {"spotify": "..."},
            },
        ],
        "total": 1,
    })

    from spotify_mcp.tools.users import get_top_artists
    result = json.loads(await get_top_artists())

    assert result["artists"][0]["name"] == "Top Artist"


# ═══════════════════════════════════════════════════════════════════════════
# Player
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_playback_state_active(mock_spotify_client):
    mock_spotify_client.set_response("me/player", {
        "is_playing": True,
        "item": {
            "id": "t1",
            "name": "Now Playing",
            "artists": [{"name": "A"}],
            "album": {"name": "Alb"},
            "uri": "spotify:track:t1",
            "duration_ms": 200000,
        },
        "progress_ms": 50000,
        "device": {
            "id": "dev1",
            "name": "My Speaker",
            "type": "Speaker",
            "volume_percent": 50,
        },
        "shuffle_state": True,
        "repeat_state": "off",
    })

    from spotify_mcp.tools.player import get_playback_state
    result = json.loads(await get_playback_state())

    assert result["playing"] is True
    assert result["track"]["name"] == "Now Playing"
    assert result["device"]["name"] == "My Speaker"
    assert result["shuffle"] is True


@pytest.mark.asyncio
async def test_get_playback_state_inactive(mock_spotify_client):
    """When no playback, API returns empty dict (204 -> {})."""
    mock_spotify_client.set_response("me/player", {})

    from spotify_mcp.tools.player import get_playback_state
    result = json.loads(await get_playback_state())

    assert result["playing"] is False
    assert "No active" in result["message"]


@pytest.mark.asyncio
async def test_play_with_context(mock_spotify_client):
    mock_spotify_client.set_put_response("me/player/play", {})

    from spotify_mcp.tools.player import play
    result = json.loads(await play(context_uri="spotify:playlist:pl1", offset_position=5))

    put_calls = [c for c in mock_spotify_client.calls if c[0] == "PUT"]
    assert len(put_calls) == 1
    body = put_calls[0][3]
    assert body["context_uri"] == "spotify:playlist:pl1"
    assert body["offset"] == {"position": 5}


@pytest.mark.asyncio
async def test_play_with_track_uris(mock_spotify_client):
    mock_spotify_client.set_put_response("me/player/play", {})

    from spotify_mcp.tools.player import play
    await play(uris=["spotify:track:t1", "spotify:track:t2"])

    put_calls = [c for c in mock_spotify_client.calls if c[0] == "PUT"]
    assert len(put_calls) == 1
    body = put_calls[0][3]
    assert body["uris"] == ["spotify:track:t1", "spotify:track:t2"]
    assert "context_uri" not in body


@pytest.mark.asyncio
async def test_set_volume_clamps(mock_spotify_client):
    mock_spotify_client.set_put_response("me/player/volume", {})

    from spotify_mcp.tools.player import set_volume
    result = json.loads(await set_volume(150))

    assert result["volume_percent"] == 100
    put_calls = [c for c in mock_spotify_client.calls if c[0] == "PUT"]
    assert put_calls[0][2]["volume_percent"] == 100


@pytest.mark.asyncio
async def test_add_to_queue(mock_spotify_client):
    mock_spotify_client.set_post_response("me/player/queue", {})

    from spotify_mcp.tools.player import add_to_queue
    result = json.loads(await add_to_queue("spotify:track:t1"))

    assert result["status"] == "queued"
    post_calls = [c for c in mock_spotify_client.calls if c[0] == "POST"]
    assert post_calls[0][2]["uri"] == "spotify:track:t1"


@pytest.mark.asyncio
async def test_transfer_playback(mock_spotify_client):
    mock_spotify_client.set_put_response("me/player", {})

    from spotify_mcp.tools.player import transfer_playback
    result = json.loads(await transfer_playback("dev1", force_play=True))

    assert result["status"] == "transferred"
    put_calls = [c for c in mock_spotify_client.calls if c[0] == "PUT"]
    body = put_calls[0][3]
    assert body["device_ids"] == ["dev1"]
    assert body["play"] is True


# ═══════════════════════════════════════════════════════════════════════════
# Shows
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_show(mock_spotify_client):
    mock_spotify_client.set_response("shows/s1", {
        "id": "s1",
        "name": "Test Podcast",
        "publisher": "Host",
        "description": "A podcast",
        "total_episodes": 50,
        "languages": ["en"],
        "uri": "spotify:show:s1",
        "external_urls": {"spotify": "..."},
        "images": [],
    })

    from spotify_mcp.tools.shows import get_show
    result = json.loads(await get_show("s1"))

    assert result["name"] == "Test Podcast"
    assert result["total_episodes"] == 50


@pytest.mark.asyncio
async def test_get_episode(mock_spotify_client):
    mock_spotify_client.set_response("episodes/e1", {
        "id": "e1",
        "name": "Episode 1",
        "description": "First episode",
        "duration_ms": 3600000,
        "release_date": "2026-01-01",
        "show": {"id": "s1", "name": "Test Podcast", "publisher": "Host"},
        "uri": "spotify:episode:e1",
        "external_urls": {"spotify": "..."},
    })

    from spotify_mcp.tools.shows import get_episode
    result = json.loads(await get_episode("e1"))

    assert result["name"] == "Episode 1"
    assert result["show"]["name"] == "Test Podcast"


# ═══════════════════════════════════════════════════════════════════════════
# Audiobooks
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_get_audiobook(mock_spotify_client):
    mock_spotify_client.set_response("audiobooks/ab1", {
        "id": "ab1",
        "name": "Test Book",
        "authors": [{"name": "Author A"}],
        "narrators": [{"name": "Narrator B"}],
        "description": "A book",
        "total_chapters": 20,
        "languages": ["en"],
        "uri": "spotify:audiobook:ab1",
        "external_urls": {"spotify": "..."},
    })

    from spotify_mcp.tools.audiobooks import get_audiobook
    result = json.loads(await get_audiobook("ab1"))

    assert result["name"] == "Test Book"
    assert result["authors"] == ["Author A"]
    assert result["total_chapters"] == 20


@pytest.mark.asyncio
async def test_get_chapter(mock_spotify_client):
    mock_spotify_client.set_response("chapters/ch1", {
        "id": "ch1",
        "name": "Chapter 1",
        "chapter_number": 1,
        "duration_ms": 1800000,
        "audiobook": {"id": "ab1", "name": "Test Book"},
        "uri": "spotify:chapter:ch1",
        "external_urls": {"spotify": "..."},
    })

    from spotify_mcp.tools.audiobooks import get_chapter
    result = json.loads(await get_chapter("ch1"))

    assert result["name"] == "Chapter 1"
    assert result["audiobook"]["name"] == "Test Book"


# ═══════════════════════════════════════════════════════════════════════════
# Server — all tools register
# ═══════════════════════════════════════════════════════════════════════════


def test_all_expected_tools_registered():
    """Verify every tool from the roadmap is registered (minus removed endpoints)."""
    from spotify_mcp.server import mcp

    tools = set(mcp._tool_manager._tools.keys())

    expected = {
        # Users
        "get_current_user", "get_top_artists", "get_top_tracks",
        # Search
        "search",
        # Tracks
        "get_track",
        # Albums
        "get_album", "get_album_tracks", "get_saved_albums",
        # Artists
        "get_artist", "get_artist_albums",
        # Player
        "get_playback_state", "get_devices", "get_currently_playing",
        "play", "pause", "next_track", "previous_track", "seek",
        "set_repeat", "set_volume", "toggle_shuffle",
        "get_queue", "add_to_queue", "get_recently_played", "transfer_playback",
        # Playlists
        "get_my_playlists", "get_playlist", "get_playlist_items",
        "create_playlist", "add_items_to_playlist",
        "update_playlist_details", "remove_items_from_playlist", "reorder_playlist_items",
        # Library
        "save_to_library", "remove_from_library", "check_saved",
        # Shows
        "get_show", "get_show_episodes", "get_episode",
        # Audiobooks
        "get_audiobook", "get_audiobook_chapters", "get_chapter",
        # Account / setup
        "auth_status", "authenticate",
    }

    missing = expected - tools
    assert not missing, f"Missing tools: {missing}"

    # No removed/dead endpoints should be registered
    removed = {"get_audio_features", "get_audio_analysis", "get_related_artists",
               "get_categories", "get_category", "get_recommendations",
               "generate_dance_mix", "list_source_playlists"}
    unexpected = removed & tools
    assert not unexpected, f"Removed endpoints still registered: {unexpected}"
