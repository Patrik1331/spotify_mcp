"""Dance Mix Generator — 3-3 pattern playlist builder.

Creates playlists that alternate between two genres (e.g., bachata and kizomba)
in configurable block sizes, mixing old favorites with recently added tracks.
"""

from __future__ import annotations

import json
import random
from typing import Any

from ..client import SpotifyClient
from ..app import mcp
from .playlists import _fetch_all_playlist_items


def _split_old_new(
    items: list[dict[str, Any]],
    split_ratio: float = 0.5,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split playlist items into 'old' and 'new' based on added_at order.

    Items are sorted by added_at ascending (oldest first).
    The split_ratio determines what fraction is considered "old" (default 50%).
    """
    sorted_items = sorted(items, key=lambda x: x.get("added_at", ""))
    split_index = int(len(sorted_items) * split_ratio)

    old = sorted_items[:split_index]
    new = sorted_items[split_index:]
    return old, new


def _build_3_3_sequence(
    old_a: list[dict[str, Any]],
    new_a: list[dict[str, Any]],
    old_b: list[dict[str, Any]],
    new_b: list[dict[str, Any]],
    block_size: int = 3,
) -> list[dict[str, Any]]:
    """Build the alternating block sequence.

    Pattern: [block_size old_a, block_size new_b, block_size new_a, block_size old_b, ...]
    Repeats until all buckets are exhausted. Shuffles within each bucket first.

    This creates variety: old favorites of genre A followed by fresh genre B tracks,
    then fresh genre A followed by old favorites of genre B.
    """
    # Shuffle within each bucket for variety
    random.shuffle(old_a)
    random.shuffle(new_a)
    random.shuffle(old_b)
    random.shuffle(new_b)

    # Build iterators for each bucket
    buckets = [
        iter(old_a),
        iter(new_b),
        iter(new_a),
        iter(old_b),
    ]
    bucket_names = ["old_a", "new_b", "new_a", "old_b"]

    sequence: list[dict[str, Any]] = []
    bucket_index = 0
    empty_count = 0

    while empty_count < len(buckets):
        bucket = buckets[bucket_index]
        block: list[dict[str, Any]] = []

        for _ in range(block_size):
            try:
                item = next(bucket)
                block.append(item)
            except StopIteration:
                break

        if block:
            # Tag each item with its source bucket for transparency
            for item in block:
                item["_source"] = bucket_names[bucket_index]
            sequence.extend(block)
            empty_count = 0
        else:
            empty_count += 1

        bucket_index = (bucket_index + 1) % len(buckets)

    return sequence


@mcp.tool()
async def generate_dance_mix(
    playlist_a_id: str,
    playlist_b_id: str,
    name: str,
    block_size: int = 3,
    old_ratio: float = 0.5,
    description: str = "",
) -> str:
    """Generate a dance mix playlist alternating between two source playlists in blocks.

    Creates a new playlist that alternates tracks from playlist A and playlist B
    in groups of `block_size` (default 3), mixing old favorites with recently added
    tracks. Perfect for bachata/kizomba dance nights with 3-3 patterns.

    Pattern: 3 old from A → 3 new from B → 3 new from A → 3 old from B → repeat

    Args:
        playlist_a_id: Spotify ID of the first source playlist (e.g., your Bachata playlist).
        playlist_b_id: Spotify ID of the second source playlist (e.g., your Kizomba playlist).
        name: Name for the new playlist (e.g., "Dance Night 2026-03-11").
        block_size: Number of songs per block (default 3).
        old_ratio: Fraction of each playlist considered "old" (0.0-1.0, default 0.5).
                   0.5 means the older half are "old", newer half are "new".
        description: Optional description for the new playlist.

    Returns the new playlist URL, track count, and block breakdown.
    """
    async with SpotifyClient() as sp:
        # Fetch all tracks from both playlists
        items_a = await _fetch_all_playlist_items(sp, playlist_a_id)
        items_b = await _fetch_all_playlist_items(sp, playlist_b_id)

        if not items_a:
            return json.dumps({"error": f"Playlist A ({playlist_a_id}) is empty or has no tracks."})
        if not items_b:
            return json.dumps({"error": f"Playlist B ({playlist_b_id}) is empty or has no tracks."})

        # Split each into old/new
        old_a, new_a = _split_old_new(items_a, old_ratio)
        old_b, new_b = _split_old_new(items_b, old_ratio)

        # Build the alternating sequence
        sequence = _build_3_3_sequence(old_a, new_a, old_b, new_b, block_size)

        if not sequence:
            return json.dumps({"error": "Could not build a sequence — source playlists may be too small."})

        # Create the new playlist
        me = await sp.get("me")
        user_id = me["id"]

        playlist_data = await sp.post(
            f"users/{user_id}/playlists",
            json={
                "name": name,
                "description": description or f"Dance mix: {block_size}-{block_size} pattern",
                "public": False,
            },
        )
        new_playlist_id = playlist_data["id"]

        # Add tracks in order (max 100 per request)
        track_uris = [item["track_uri"] for item in sequence if item.get("track_uri")]
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i + 100]
            await sp.post(f"playlists/{new_playlist_id}/items", json={"uris": batch})

    # Build summary
    source_counts = {}
    for item in sequence:
        src = item.get("_source", "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    return json.dumps({
        "playlist_id": new_playlist_id,
        "playlist_url": playlist_data.get("external_urls", {}).get("spotify"),
        "playlist_uri": playlist_data.get("uri"),
        "name": name,
        "total_tracks": len(track_uris),
        "block_size": block_size,
        "source_a_total": len(items_a),
        "source_b_total": len(items_b),
        "breakdown": {
            "old_from_a": source_counts.get("old_a", 0),
            "new_from_a": source_counts.get("new_a", 0),
            "old_from_b": source_counts.get("old_b", 0),
            "new_from_b": source_counts.get("new_b", 0),
        },
    }, indent=2)


@mcp.tool()
async def list_source_playlists(search_name: str = "") -> str:
    """List your playlists, optionally filtering by name.

    Useful for finding the playlist IDs needed for generate_dance_mix.

    Args:
        search_name: Optional text to filter playlist names (case-insensitive).
                     Leave empty to list all playlists.

    Returns matching playlists with their IDs and track counts.
    """
    async with SpotifyClient() as sp:
        all_playlists: list[dict[str, Any]] = []
        offset = 0

        while True:
            data = await sp.get("me/playlists", params={"limit": 50, "offset": offset})
            items = data.get("items", [])
            if not items:
                break

            for item in items:
                playlist_info = {
                    "id": item["id"],
                    "name": item["name"],
                    "tracks_total": item.get("tracks", {}).get("total", 0),
                    "owner": item.get("owner", {}).get("display_name"),
                    "external_url": item.get("external_urls", {}).get("spotify"),
                }

                if search_name:
                    if search_name.lower() in item["name"].lower():
                        all_playlists.append(playlist_info)
                else:
                    all_playlists.append(playlist_info)

            if data.get("next") is None:
                break
            offset += 50

    return json.dumps({
        "playlists": all_playlists,
        "count": len(all_playlists),
        "filter": search_name or "(none)",
    }, indent=2)
