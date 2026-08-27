"""Tests for BPM lookup tools (GetSongBPM third-party API)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from spotify_mcp.tools import bpm as bpm_module


@pytest.fixture()
def mock_bpm_search(monkeypatch):
    """Patch the raw GetSongBPM HTTP call and ensure an API key is set."""
    monkeypatch.setattr(bpm_module, "GETSONGBPM_API_KEY", "test-key")
    mock = AsyncMock()
    monkeypatch.setattr(bpm_module, "_getsongbpm_search", mock)
    return mock


@pytest.mark.asyncio
async def test_get_track_bpm_found(mock_spotify_client, mock_bpm_search):
    mock_spotify_client.set_response("tracks/t1", {
        "id": "t1",
        "name": "Loca",
        "artists": [{"name": "Fonseca"}],
    })
    mock_bpm_search.return_value = {
        "search": [{"title": "Loca", "artist": {"name": "Fonseca"}, "tempo": "128", "uri": "https://getsongbpm.com/x"}],
    }

    result = json.loads(await bpm_module.get_track_bpm("t1"))

    assert result["found"] is True
    assert result["bpm"] == 128.0
    assert result["matched_artist"] == "Fonseca"
    mock_bpm_search.assert_awaited_once_with("song:Loca artist:Fonseca")


@pytest.mark.asyncio
async def test_get_track_bpm_no_match(mock_spotify_client, mock_bpm_search):
    mock_spotify_client.set_response("tracks/t1", {
        "id": "t1", "name": "Obscure Track", "artists": [{"name": "Unknown"}],
    })
    mock_bpm_search.return_value = {"search": []}

    result = json.loads(await bpm_module.get_track_bpm("t1"))

    assert result["found"] is False
    assert result["bpm"] is None


@pytest.mark.asyncio
async def test_get_track_bpm_missing_api_key(mock_spotify_client, monkeypatch):
    monkeypatch.setattr(bpm_module, "GETSONGBPM_API_KEY", "")
    mock_spotify_client.set_response("tracks/t1", {
        "id": "t1", "name": "Loca", "artists": [{"name": "Fonseca"}],
    })

    result = json.loads(await bpm_module.get_track_bpm("t1"))

    assert "GETSONGBPM_API_KEY" in result["error"]


@pytest.mark.asyncio
async def test_get_playlist_bpm_summarizes_matches(mock_spotify_client, mock_bpm_search):
    mock_spotify_client.set_response("playlists/pl1/items", {
        "items": [
            {"added_at": "2026-01-01T00:00:00Z", "item": {
                "id": "t1", "name": "Song A", "uri": "spotify:track:t1",
                "artists": [{"name": "Artist A"}], "album": {"name": "Alb"}, "duration_ms": 200000,
            }},
            {"added_at": "2026-01-02T00:00:00Z", "item": {
                "id": "t2", "name": "Song B", "uri": "spotify:track:t2",
                "artists": [{"name": "Artist B"}], "album": {"name": "Alb"}, "duration_ms": 200000,
            }},
        ],
        "next": None,
    })
    mock_bpm_search.side_effect = [
        {"search": [{"title": "Song A", "artist": {"name": "Artist A"}, "tempo": "100"}]},
        {"search": []},
    ]

    result = json.loads(await bpm_module.get_playlist_bpm("pl1"))

    assert result["total"] == 2
    assert result["matched"] == 1
    assert result["unmatched"] == 1
    assert result["tracks"][0]["bpm"] == 100.0
    assert result["tracks"][1]["found"] is False
