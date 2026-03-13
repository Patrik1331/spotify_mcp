"""Playlist MCP tools — read, create, add items."""

from __future__ import annotations

import json
from typing import Any

from ..app import mcp
from ..client import SpotifyClient


@mcp.tool()
async def get_my_playlists(limit: int = 50, offset: int = 0) -> str:
    """List the current user's playlists.

    Args:
        limit: Max number of playlists to return (1-50, default 50).
        offset: Index of first playlist to return (default 0).

    Returns a JSON list of playlists with id, name, track count, and owner.
    """
    async with SpotifyClient() as sp:
        data = await sp.get("me/playlists", params={"limit": limit, "offset": offset})

    playlists: list[dict[str, Any]] = []
    for item in data.get("items", []):
        playlists.append({
            "id": item["id"],
            "name": item["name"],
            "tracks_total": item.get("items", {}).get("total", 0) if isinstance(item.get("items"), dict) else 0,
            "owner": item.get("owner", {}).get("display_name"),
            "public": item.get("public"),
            "uri": item.get("uri"),
            "external_url": item.get("external_urls", {}).get("spotify"),
        })

    return json.dumps({
        "playlists": playlists,
        "total": data.get("total", 0),
        "offset": offset,
    }, indent=2)


@mcp.tool()
async def get_playlist(playlist_id: str) -> str:
    """Get details of a specific playlist.

    Args:
        playlist_id: The Spotify playlist ID.

    Returns playlist name, description, track count, and owner info.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(f"playlists/{playlist_id}")

    return json.dumps({
        "id": data["id"],
        "name": data.get("name"),
        "description": data.get("description"),
        "tracks_total": data.get("items", {}).get("total", 0) if isinstance(data.get("items"), dict) else 0,
        "owner": data.get("owner", {}).get("display_name"),
        "public": data.get("public"),
        "uri": data.get("uri"),
        "external_url": data.get("external_urls", {}).get("spotify"),
    }, indent=2)


async def fetch_all_playlist_items(sp: SpotifyClient, playlist_id: str) -> list[dict[str, Any]]:
    """Fetch ALL tracks from a playlist, handling pagination.

    Returns list of items with track info and added_at timestamp.
    """
    items: list[dict[str, Any]] = []
    offset = 0
    limit = 100  # Spotify max per request

    while True:
        data = await sp.get(
            f"playlists/{playlist_id}/items",
            params={
                "limit": limit,
                "offset": offset,
                "additional_types": "track",
            },
        )

        for entry in data.get("items", []):
            # Post-Feb 2026 API: track data is under "item", not "track"
            track = entry.get("item") or entry.get("track")
            if track is None:
                continue  # Skip removed/unavailable tracks
            items.append({
                "added_at": entry.get("added_at"),
                "track_id": track.get("id"),
                "track_name": track.get("name"),
                "track_uri": track.get("uri"),
                "artists": [a.get("name") for a in track.get("artists", [])],
                "album": track.get("album", {}).get("name"),
                "duration_ms": track.get("duration_ms"),
            })

        if data.get("next") is None:
            break
        offset += limit

    return items


@mcp.tool()
async def get_playlist_items(playlist_id: str, limit: int = 100, offset: int = 0) -> str:
    """Get tracks from a playlist with added_at timestamps.

    Args:
        playlist_id: The Spotify playlist ID.
        limit: Max tracks to return (1-100, default 100).
        offset: Index of first track (default 0).

    Returns track names, artists, URIs, and when each was added.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(
            f"playlists/{playlist_id}/items",
            params={
                "limit": limit,
                "offset": offset,
                "additional_types": "track",
            },
        )

    items: list[dict[str, Any]] = []
    for entry in data.get("items", []):
        # Post-Feb 2026 API: track data is under "item", not "track"
        track = entry.get("item") or entry.get("track")
        if track is None:
            continue
        items.append({
            "added_at": entry.get("added_at"),
            "track_id": track.get("id"),
            "track_name": track.get("name"),
            "track_uri": track.get("uri"),
            "artists": [a.get("name") for a in track.get("artists", [])],
            "album": track.get("album", {}).get("name"),
            "duration_ms": track.get("duration_ms"),
        })

    return json.dumps({
        "items": items,
        "total": data.get("total", 0),
        "has_next": data.get("next") is not None,
    }, indent=2)


@mcp.tool()
async def create_playlist(name: str, description: str = "", public: bool = False) -> str:
    """Create a new playlist for the current user.

    Args:
        name: The name for the new playlist.
        description: Optional playlist description.
        public: Whether the playlist should be public (default False).

    Returns the new playlist's ID, URL, and URI.
    """
    async with SpotifyClient() as sp:
        data = await sp.post(
            "me/playlists",
            json={
                "name": name,
                "description": description,
                "public": public,
            },
        )

    return json.dumps({
        "id": data["id"],
        "name": data.get("name"),
        "uri": data.get("uri"),
        "external_url": data.get("external_urls", {}).get("spotify"),
    }, indent=2)


@mcp.tool()
async def add_items_to_playlist(playlist_id: str, uris: list[str]) -> str:
    """Add tracks to a playlist.

    Args:
        playlist_id: The Spotify playlist ID to add tracks to.
        uris: List of Spotify track URIs (e.g., ["spotify:track:xxx", ...]).
              Max 100 per call. For more, call multiple times.

    Returns confirmation with snapshot_id.
    """
    async with SpotifyClient() as sp:
        # Spotify allows max 100 URIs per request
        results: list[Any] = []
        for i in range(0, len(uris), 100):
            batch = uris[i:i + 100]
            data = await sp.post(
                f"playlists/{playlist_id}/items",
                json={"uris": batch},
            )
            results.append(data.get("snapshot_id"))

    return json.dumps({
        "added": len(uris),
        "snapshot_ids": results,
    }, indent=2)


@mcp.tool()
async def update_playlist_details(
    playlist_id: str,
    name: str = "",
    description: str = "",
    public: bool | None = None,
) -> str:
    """Update a playlist's name, description, or visibility.

    Args:
        playlist_id: The Spotify playlist ID.
        name: New name for the playlist (leave empty to keep current).
        description: New description (leave empty to keep current).
        public: Set to True for public, False for private, or omit to keep current.

    Returns confirmation of update.
    """
    body: dict[str, Any] = {}
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    if public is not None:
        body["public"] = public

    if not body:
        return json.dumps({"error": "No fields to update. Provide name, description, or public."})

    async with SpotifyClient() as sp:
        await sp.put(f"playlists/{playlist_id}", json=body)

    return json.dumps({"status": "updated", "playlist_id": playlist_id, "updated_fields": list(body.keys())})


@mcp.tool()
async def remove_items_from_playlist(playlist_id: str, uris: list[str]) -> str:
    """Remove tracks from a playlist.

    Args:
        playlist_id: The Spotify playlist ID.
        uris: List of Spotify track URIs to remove (e.g., ["spotify:track:xxx"]).

    Returns confirmation with snapshot_id.
    """
    items = [{"uri": uri} for uri in uris]

    async with SpotifyClient() as sp:
        data = await sp.delete(
            f"playlists/{playlist_id}/items",
            json={"items": items},
        )

    return json.dumps({
        "removed": len(uris),
        "snapshot_id": data.get("snapshot_id"),
    }, indent=2)


@mcp.tool()
async def reorder_playlist_items(
    playlist_id: str,
    range_start: int,
    insert_before: int,
    range_length: int = 1,
) -> str:
    """Reorder tracks in a playlist.

    Args:
        playlist_id: The Spotify playlist ID.
        range_start: Position of the first item to move (0-based).
        insert_before: Position to insert the items before (0-based).
        range_length: Number of items to move (default 1).

    Returns confirmation with snapshot_id.
    """
    async with SpotifyClient() as sp:
        data = await sp.put(
            f"playlists/{playlist_id}/items",
            json={
                "range_start": range_start,
                "insert_before": insert_before,
                "range_length": range_length,
            },
        )

    return json.dumps({
        "status": "reordered",
        "snapshot_id": data.get("snapshot_id"),
    }, indent=2)
