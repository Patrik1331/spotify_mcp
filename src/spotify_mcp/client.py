"""Async httpx wrapper for the Spotify Web API v1."""

from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any

import httpx

from .auth import get_tokens, refresh_access_token

BASE_URL = "https://api.spotify.com/v1/"


class SpotifyAPIError(Exception):
    """Raised when a Spotify API call fails with a non-recoverable status."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"Spotify API {status_code}: {message}")


class SpotifyClient:
    """Thin async wrapper around the Spotify Web API.

    Usage::

        async with SpotifyClient() as sp:
            me = await sp.get("me")
    """

    def __init__(self) -> None:
        self._client: httpx.AsyncClient | None = None

    # -- async context manager ------------------------------------------------

    async def __aenter__(self) -> SpotifyClient:
        tokens = get_tokens()
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
            timeout=httpx.Timeout(30.0),
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # -- public HTTP helpers --------------------------------------------------

    async def get(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a GET request and return parsed JSON."""
        return await self._request("GET", path, params=params)

    async def post(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a POST request and return parsed JSON."""
        return await self._request("POST", path, params=params, json=json)

    async def put(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a PUT request and return parsed JSON."""
        return await self._request("PUT", path, params=params, json=json)

    async def delete(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a DELETE request and return parsed JSON."""
        return await self._request("DELETE", path, params=params, json=json)

    # -- internals ------------------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute *method* against *path*, handling 401 refresh and 429 back-off."""
        if self._client is None:
            raise RuntimeError("SpotifyClient must be used as an async context manager")

        response = await self._client.request(method, path, params=params, json=json)

        # -- 401: refresh the access token and retry once ---------------------
        if response.status_code == 401:
            tokens = refresh_access_token()
            self._client.headers["Authorization"] = f"Bearer {tokens['access_token']}"
            response = await self._client.request(method, path, params=params, json=json)

        # -- 429: respect Retry-After and retry once --------------------------
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "1"))
            await asyncio.sleep(retry_after)
            response = await self._client.request(method, path, params=params, json=json)

        # -- raise on any remaining error -------------------------------------
        if response.status_code >= 400:
            try:
                body = response.json()
                message = body.get("error", {}).get("message", response.text)
            except Exception:
                message = response.text
            raise SpotifyAPIError(response.status_code, message)

        # Some Spotify endpoints return 200/204 with no body
        if response.status_code == 204 or not response.content:
            return {}

        return response.json()  # type: ignore[no-any-return]
