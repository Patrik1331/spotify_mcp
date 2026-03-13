"""Shared test fixtures — mock SpotifyClient to avoid real API calls."""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest


@pytest.fixture()
def mock_spotify_client():
    """Provide a mock SpotifyClient that returns configurable responses.

    Patches SpotifyClient in ALL tool modules so any tool call uses the mock.
    """
    client = MockSpotifyClient()

    # Patch in every module that imports SpotifyClient
    modules = [
        "spotify_mcp.tools.playlists",
        "spotify_mcp.tools.users",
        "spotify_mcp.tools.search",
        "spotify_mcp.tools.tracks",
        "spotify_mcp.tools.albums",
        "spotify_mcp.tools.artists",
        "spotify_mcp.tools.player",
        "spotify_mcp.tools.library",
        "spotify_mcp.tools.shows",
        "spotify_mcp.tools.audiobooks",
    ]

    patches = [patch(f"{mod}.SpotifyClient", return_value=client) for mod in modules]
    for p in patches:
        p.start()
    yield client
    for p in patches:
        p.stop()


class MockSpotifyClient:
    """In-memory mock that records calls and returns preset responses."""

    def __init__(self) -> None:
        self._responses: dict[str, Any] = {}
        self._calls: list[tuple[str, str, dict[str, Any] | None, dict[str, Any] | None]] = []
        self._delete_responses: dict[str, Any] = {}
        self._put_responses: dict[str, Any] = {}
        self._post_responses: dict[str, Any] = {}

    def set_response(self, path: str, data: Any) -> None:
        """Set GET response for a path (exact match)."""
        self._responses[path] = data

    def set_post_response(self, path: str, data: Any) -> None:
        self._post_responses[path] = data

    def set_put_response(self, path: str, data: Any) -> None:
        self._put_responses[path] = data

    def set_delete_response(self, path: str, data: Any) -> None:
        self._delete_responses[path] = data

    @property
    def calls(self) -> list[tuple[str, str, dict[str, Any] | None, dict[str, Any] | None]]:
        return self._calls

    def _find_response(self, store: dict[str, Any], path: str) -> Any:
        if path in store:
            return store[path]
        # Longest prefix match (for dynamic paths like playlists/{id}/items)
        best_key = ""
        for key in store:
            if path.startswith(key) and len(key) > len(best_key):
                best_key = key
        if best_key:
            return store[best_key]
        return {}

    async def get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self._calls.append(("GET", path, params, None))
        return self._find_response(self._responses, path)

    async def post(self, path: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None) -> dict[str, Any]:
        self._calls.append(("POST", path, params, json))
        return self._find_response(self._post_responses, path)

    async def put(self, path: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None) -> dict[str, Any]:
        self._calls.append(("PUT", path, params, json))
        return self._find_response(self._put_responses, path)

    async def delete(self, path: str, *, params: dict[str, Any] | None = None, json: dict[str, Any] | None = None) -> dict[str, Any]:
        self._calls.append(("DELETE", path, params, json))
        return self._find_response(self._delete_responses, path)

    async def __aenter__(self) -> MockSpotifyClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        pass
