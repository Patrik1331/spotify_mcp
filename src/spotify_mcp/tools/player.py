"""Playback control MCP tools."""

from __future__ import annotations

import json
from typing import Any

from ..app import mcp
from ..client import SpotifyClient


@mcp.tool()
async def get_playback_state() -> str:
    """Get the current playback state (device, track, progress, shuffle, repeat).

    Returns current playback info or a message if nothing is playing.
    """
    async with SpotifyClient() as sp:
        data = await sp.get("me/player")

    if not data:
        return json.dumps({"playing": False, "message": "No active playback session."})

    item = data.get("item", {})
    device = data.get("device", {})

    return json.dumps({
        "playing": data.get("is_playing", False),
        "track": {
            "id": item.get("id"),
            "name": item.get("name"),
            "artists": [a["name"] for a in item.get("artists", [])],
            "album": item.get("album", {}).get("name"),
            "uri": item.get("uri"),
            "duration_ms": item.get("duration_ms"),
        },
        "progress_ms": data.get("progress_ms"),
        "device": {
            "id": device.get("id"),
            "name": device.get("name"),
            "type": device.get("type"),
            "volume_percent": device.get("volume_percent"),
        },
        "shuffle": data.get("shuffle_state"),
        "repeat": data.get("repeat_state"),
    }, indent=2)


@mcp.tool()
async def get_devices() -> str:
    """Get the user's available Spotify playback devices.

    Returns list of devices with name, type, volume, and active status.
    """
    async with SpotifyClient() as sp:
        data = await sp.get("me/player/devices")

    devices = [
        {
            "id": d.get("id"),
            "name": d.get("name"),
            "type": d.get("type"),
            "is_active": d.get("is_active"),
            "volume_percent": d.get("volume_percent"),
        }
        for d in data.get("devices", [])
    ]

    return json.dumps({"devices": devices}, indent=2)


@mcp.tool()
async def get_currently_playing() -> str:
    """Get the currently playing track.

    Returns the current track info or a message if nothing is playing.
    """
    async with SpotifyClient() as sp:
        data = await sp.get("me/player/currently-playing")

    if not data or not data.get("item"):
        return json.dumps({"playing": False, "message": "Nothing currently playing."})

    item = data["item"]

    return json.dumps({
        "playing": data.get("is_playing", False),
        "track": {
            "id": item.get("id"),
            "name": item.get("name"),
            "artists": [a["name"] for a in item.get("artists", [])],
            "album": item.get("album", {}).get("name"),
            "uri": item.get("uri"),
            "duration_ms": item.get("duration_ms"),
        },
        "progress_ms": data.get("progress_ms"),
    }, indent=2)


@mcp.tool()
async def play(
    device_id: str = "",
    context_uri: str = "",
    uris: list[str] | None = None,
    offset_position: int = -1,
    position_ms: int = 0,
) -> str:
    """Start or resume playback.

    Args:
        device_id: Optional device ID to play on. If empty, uses the active device.
        context_uri: Optional Spotify URI of context to play (album, artist, playlist).
                     e.g., "spotify:album:xxx" or "spotify:playlist:xxx".
        uris: Optional list of track URIs to play (e.g., ["spotify:track:xxx"]).
              Cannot be used with context_uri.
        offset_position: Position in the context to start at (0-based index). -1 to ignore.
        position_ms: Position in the track to start at in milliseconds (default 0).

    Returns confirmation of playback started.
    """
    params: dict[str, Any] = {}
    if device_id:
        params["device_id"] = device_id

    body: dict[str, Any] = {}
    if context_uri:
        body["context_uri"] = context_uri
    if uris:
        body["uris"] = uris
    if offset_position >= 0:
        body["offset"] = {"position": offset_position}
    if position_ms > 0:
        body["position_ms"] = position_ms

    async with SpotifyClient() as sp:
        await sp.put("me/player/play", params=params or None, json=body or None)

    return json.dumps({"status": "playing"})


@mcp.tool()
async def pause(device_id: str = "") -> str:
    """Pause playback.

    Args:
        device_id: Optional device ID. If empty, pauses the active device.

    Returns confirmation of playback paused.
    """
    params: dict[str, Any] = {}
    if device_id:
        params["device_id"] = device_id

    async with SpotifyClient() as sp:
        await sp.put("me/player/pause", params=params or None)

    return json.dumps({"status": "paused"})


@mcp.tool()
async def next_track(device_id: str = "") -> str:
    """Skip to the next track.

    Args:
        device_id: Optional device ID. If empty, uses the active device.
    """
    params: dict[str, Any] = {}
    if device_id:
        params["device_id"] = device_id

    async with SpotifyClient() as sp:
        await sp.post("me/player/next", params=params or None)

    return json.dumps({"status": "skipped_to_next"})


@mcp.tool()
async def previous_track(device_id: str = "") -> str:
    """Skip to the previous track.

    Args:
        device_id: Optional device ID. If empty, uses the active device.
    """
    params: dict[str, Any] = {}
    if device_id:
        params["device_id"] = device_id

    async with SpotifyClient() as sp:
        await sp.post("me/player/previous", params=params or None)

    return json.dumps({"status": "skipped_to_previous"})


@mcp.tool()
async def seek(position_ms: int, device_id: str = "") -> str:
    """Seek to a position in the current track.

    Args:
        position_ms: Position in milliseconds to seek to.
        device_id: Optional device ID. If empty, uses the active device.
    """
    params: dict[str, Any] = {"position_ms": position_ms}
    if device_id:
        params["device_id"] = device_id

    async with SpotifyClient() as sp:
        await sp.put("me/player/seek", params=params)

    return json.dumps({"status": "seeked", "position_ms": position_ms})


@mcp.tool()
async def set_repeat(state: str, device_id: str = "") -> str:
    """Set the repeat mode.

    Args:
        state: Repeat mode — "track" (repeat current track), "context" (repeat
               album/playlist), or "off" (no repeat).
        device_id: Optional device ID. If empty, uses the active device.
    """
    params: dict[str, Any] = {"state": state}
    if device_id:
        params["device_id"] = device_id

    async with SpotifyClient() as sp:
        await sp.put("me/player/repeat", params=params)

    return json.dumps({"status": "repeat_set", "state": state})


@mcp.tool()
async def set_volume(volume_percent: int, device_id: str = "") -> str:
    """Set the playback volume.

    Args:
        volume_percent: Volume level (0-100).
        device_id: Optional device ID. If empty, uses the active device.
    """
    volume_percent = min(max(volume_percent, 0), 100)
    params: dict[str, Any] = {"volume_percent": volume_percent}
    if device_id:
        params["device_id"] = device_id

    async with SpotifyClient() as sp:
        await sp.put("me/player/volume", params=params)

    return json.dumps({"status": "volume_set", "volume_percent": volume_percent})


@mcp.tool()
async def toggle_shuffle(state: bool, device_id: str = "") -> str:
    """Toggle shuffle mode.

    Args:
        state: True to enable shuffle, False to disable.
        device_id: Optional device ID. If empty, uses the active device.
    """
    params: dict[str, Any] = {"state": str(state).lower()}
    if device_id:
        params["device_id"] = device_id

    async with SpotifyClient() as sp:
        await sp.put("me/player/shuffle", params=params)

    return json.dumps({"status": "shuffle_set", "enabled": state})


@mcp.tool()
async def get_queue() -> str:
    """Get the user's current playback queue.

    Returns the currently playing track and upcoming queue.
    """
    async with SpotifyClient() as sp:
        data = await sp.get("me/player/queue")

    currently = data.get("currently_playing")
    current_track = None
    if currently:
        current_track = {
            "id": currently.get("id"),
            "name": currently.get("name"),
            "artists": [a["name"] for a in currently.get("artists", [])],
            "uri": currently.get("uri"),
        }

    queue = [
        {
            "id": t.get("id"),
            "name": t.get("name"),
            "artists": [a["name"] for a in t.get("artists", [])],
            "uri": t.get("uri"),
        }
        for t in data.get("queue", [])
    ]

    return json.dumps({
        "currently_playing": current_track,
        "queue": queue,
        "queue_length": len(queue),
    }, indent=2)


@mcp.tool()
async def add_to_queue(uri: str, device_id: str = "") -> str:
    """Add a track to the end of the playback queue.

    Args:
        uri: Spotify URI of the track to queue (e.g., "spotify:track:xxx").
        device_id: Optional device ID. If empty, uses the active device.
    """
    params: dict[str, Any] = {"uri": uri}
    if device_id:
        params["device_id"] = device_id

    async with SpotifyClient() as sp:
        await sp.post("me/player/queue", params=params)

    return json.dumps({"status": "queued", "uri": uri})


@mcp.tool()
async def get_recently_played(limit: int = 20) -> str:
    """Get the user's recently played tracks.

    Args:
        limit: Max tracks to return (1-50, default 20).

    Returns list of recently played tracks with played_at timestamps.
    """
    async with SpotifyClient() as sp:
        data = await sp.get(
            "me/player/recently-played",
            params={"limit": limit},
        )

    items = [
        {
            "played_at": item.get("played_at"),
            "track": {
                "id": item.get("track", {}).get("id"),
                "name": item.get("track", {}).get("name"),
                "artists": [a["name"] for a in item.get("track", {}).get("artists", [])],
                "uri": item.get("track", {}).get("uri"),
            },
        }
        for item in data.get("items", [])
    ]

    return json.dumps({"items": items, "count": len(items)}, indent=2)


@mcp.tool()
async def transfer_playback(device_id: str, force_play: bool = False) -> str:
    """Transfer playback to a different device.

    Args:
        device_id: The ID of the device to transfer to.
        force_play: If True, start playing on the new device immediately.
                    If False, keep the current play state.
    """
    async with SpotifyClient() as sp:
        await sp.put(
            "me/player",
            json={
                "device_ids": [device_id],
                "play": force_play,
            },
        )

    return json.dumps({"status": "transferred", "device_id": device_id})
