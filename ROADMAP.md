# Spotify MCP Server — Roadmap

> **Spotify Web API version:** v1 (post-February 2026 consolidation, March 2026 revision)
> **Base URL:** `https://api.spotify.com/v1/`
> **MCP SDK:** Python (`mcp` package)
> **Language:** Python 3.12+
> **License:** MIT (public repo)
> **Repository:** https://github.com/Patrik1331/spotify_mcp.git

---

## Project Overview

A local MCP (Model Context Protocol) server that exposes the full Spotify Web API as MCP tools.
Claude (or any MCP-compatible client) can search music, control playback, manage playlists,
browse the library, and more — all through natural language.

### Priority Feature: Dance Mix Generator (3-3 Pattern)

The primary use case driving Phase 1: generate dance playlists that alternate between
bachata and kizomba in groups of 3, mixing old favorites with recently added tracks.
This solves the problem of shuffle breaking genre grouping patterns.

**How it works:**
1. User specifies two source playlists (e.g., "Bachata" and "Kizomba")
2. Songs in each playlist are split into "old" (added earlier) and "new" (recently added)
3. A new playlist is created with a user-provided name (typically includes date)
4. Tracks are arranged in 3-3 blocks, e.g.:
   - 3 old bachata → 3 new kizomba → 3 new bachata → 3 old kizomba → repeat
5. The mix varies old/new distribution to keep it fresh

---

## Architecture

```
spotify_mcp/
├── src/
│   └── spotify_mcp/
│       ├── __init__.py
│       ├── server.py          # MCP server entry point
│       ├── auth.py            # Spotify OAuth (Authorization Code + PKCE)
│       ├── client.py          # Spotify API HTTP client (httpx)
│       ├── tools/             # MCP tool definitions (one module per domain)
│       │   ├── __init__.py
│       │   ├── search.py      # Search tool
│       │   ├── tracks.py      # Track tools
│       │   ├── albums.py      # Album tools
│       │   ├── artists.py     # Artist tools
│       │   ├── playlists.py   # Playlist tools
│       │   ├── dance_mix.py   # 3-3 dance mix generator (priority feature)
│       │   ├── player.py      # Playback control tools
│       │   ├── library.py     # Unified library tools (Feb 2026 API)
│       │   ├── users.py       # User profile tools
│       │   ├── shows.py       # Shows & episodes tools
│       │   ├── audiobooks.py  # Audiobooks & chapters tools
│       │   └── browse.py      # Categories & recommendations
│       ├── resources/         # MCP resources (read-only data)
│       │   ├── __init__.py
│       │   └── now_playing.py # Current track as resource
│       └── models.py          # Pydantic models / typed dicts
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Fixtures (mock Spotify responses)
│   ├── test_auth.py
│   ├── test_tools/
│   │   ├── test_search.py
│   │   ├── test_tracks.py
│   │   ├── test_playlists.py
│   │   ├── test_player.py
│   │   └── test_library.py
│   └── test_server.py
├── docs/
│   ├── ROADMAP.md             # ← This file
│   └── FEATURE-CHECKLIST.md   # All tools with status
├── .claude/
│   └── settings.json          # Claude Code hooks (block .env editing)
├── CLAUDE.md                  # Project intelligence for Claude Code
├── README.md                  # Public docs, setup guide, usage
├── pyproject.toml             # Project metadata, dependencies, scripts
├── .env.example               # Required env vars template
├── .gitignore
├── LICENSE                    # MIT
└── uv.lock                   # Lock file (uv package manager)
```

---

## Tech Stack

| Layer              | Choice                                            |
|--------------------|---------------------------------------------------|
| Language           | Python 3.12+                                      |
| MCP SDK            | `mcp` (official Python MCP SDK)                   |
| HTTP client        | `httpx` (async)                                   |
| Validation         | `pydantic` v2                                     |
| Auth               | Spotify OAuth 2.0 Authorization Code + PKCE flow  |
| Token storage      | Local JSON file (`~/.spotify_mcp/tokens.json`)    |
| Package manager    | `uv` (preferred) or `pip`                         |
| Testing            | `pytest` + `pytest-asyncio`                       |
| Linting            | `ruff`                                            |
| Type checking      | `pyright`                                         |

---

## Spotify API Reference (Post-Feb 2026)

### Available Endpoints (grouped by domain)

**Search**
- `GET /search` — Search for tracks, albums, artists, playlists, shows, episodes, audiobooks (limit max: 10, default: 5)

**Tracks**
- `GET /tracks/{id}` — Get track
- `GET /audio-features/{id}` — Get audio features
- `GET /audio-analysis/{id}` — Get audio analysis
- `GET /recommendations` — Get recommendations (seed artists/tracks/genres)

**Albums**
- `GET /albums/{id}` — Get album
- `GET /albums/{id}/tracks` — Get album tracks
- `GET /me/albums` — Get saved albums

**Artists**
- `GET /artists/{id}` — Get artist
- `GET /artists/{id}/albums` — Get artist's albums
- `GET /artists/{id}/related-artists` — Get related artists

**Playlists**
- `GET /playlists/{id}` — Get playlist
- `GET /playlists/{id}/items` — Get playlist items (new path)
- `POST /users/{user_id}/playlists` — Create playlist
- `PUT /playlists/{id}` — Update playlist details
- `POST /playlists/{id}/items` — Add items
- `DELETE /playlists/{id}/items` — Remove items
- `GET /me/playlists` — Get current user's playlists

**Player / Playback**
- `GET /me/player` — Get playback state
- `PUT /me/player` — Transfer playback
- `GET /me/player/devices` — Get available devices
- `GET /me/player/currently-playing` — Get currently playing
- `PUT /me/player/play` — Start/resume playback
- `PUT /me/player/pause` — Pause playback
- `POST /me/player/next` — Skip to next
- `POST /me/player/previous` — Skip to previous
- `PUT /me/player/seek` — Seek to position
- `PUT /me/player/repeat` — Set repeat mode
- `PUT /me/player/volume` — Set volume
- `PUT /me/player/shuffle` — Toggle shuffle
- `GET /me/player/queue` — Get queue
- `POST /me/player/queue` — Add to queue
- `GET /me/player/recently-played` — Get recently played

**Library (Unified — Feb 2026)**
- `PUT /me/library` — Save items to library (albums, tracks, episodes, shows, audiobooks)
- `DELETE /me/library` — Remove items from library
- `GET /me/library/contains` — Check if items are saved

**Users**
- `GET /me` — Get current user profile
- `GET /me/top/artists` — Get user's top artists
- `GET /me/top/tracks` — Get user's top tracks

**Shows & Episodes**
- `GET /shows/{id}` — Get show
- `GET /shows/{id}/episodes` — Get show episodes
- `GET /episodes/{id}` — Get episode

**Audiobooks & Chapters**
- `GET /audiobooks/{id}` — Get audiobook
- `GET /audiobooks/{id}/chapters` — Get audiobook chapters
- `GET /chapters/{id}` — Get chapter

**Browse**
- `GET /browse/categories` — Get browse categories
- `GET /browse/categories/{id}` — Get single category

### Removed Endpoints (Feb 2026 — do NOT implement)
- Batch GET endpoints (Get Several Albums/Artists/Tracks/etc.)
- Get Artist's Top Tracks
- Get Available Markets
- Get New Releases
- Get User's Profile (public), Get User's Playlists (public)
- Individual save/remove/follow/unfollow (replaced by unified `/me/library`)

### Removed Fields (Feb 2026 — do NOT expect in responses)
- `available_markets` (all objects)
- `popularity` (albums, artists, tracks)
- `followers` (artists, users)
- `country`, `email`, `explicit_content`, `product` (user profile)

---

## Phases

### Phase 0 — Project Skeleton + Auth + Playlist Read (v0.1.0)
> Foundation: repo, auth, server boots, can read user's playlists end-to-end.

- [ ] Initialize git repo, push to GitHub
- [ ] Create `pyproject.toml` with metadata and dependencies
- [ ] Create `.gitignore` (Python + .env + tokens)
- [ ] Create `CLAUDE.md` (project intelligence)
- [ ] Create `README.md` (public setup guide)
- [ ] Create `.env.example` with `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI`
- [ ] Create `LICENSE` (MIT)
- [ ] Implement `auth.py` — Spotify OAuth 2.0 Authorization Code + PKCE flow
  - Local callback server (localhost) for token exchange
  - Token persistence in `~/.spotify_mcp/tokens.json`
  - Automatic token refresh
- [ ] Implement `client.py` — async httpx wrapper
  - Base URL: `https://api.spotify.com/v1/`
  - Auto-attach Bearer token
  - Handle 401 → refresh → retry
  - Handle 429 → respect Retry-After header
- [ ] Implement `server.py` — MCP server entry point (stdio transport)
- [ ] Implement `users.py` — get_current_user (needed for playlist creation)
- [ ] Implement `playlists.py` (partial — read tools needed for dance mix):
  - get_my_playlists — list user's playlists
  - get_playlist — get playlist details
  - get_playlist_items — get all tracks with `added_at` timestamps (with pagination)
  - create_playlist — create new playlist
  - add_items_to_playlist — add tracks to playlist
- [ ] Verify end-to-end: Claude Code → MCP server → Spotify API → playlist data returned
- [ ] Add Claude Code MCP config example for `claude_desktop_config.json`

**Deliverable:** Server boots, authenticates, can read & create playlists from Claude.

---

### Phase 1 — Dance Mix Generator (v0.2.0) ⭐ PRIMARY FEATURE
> The 3-3 pattern playlist generator for bachata/kizomba dance nights.

- [ ] Implement `dance_mix.py` — MCP tools:
  - `generate_dance_mix` — Main tool:
    - Input: playlist_a_id, playlist_b_id, name, old_new_ratio (default 50/50), block_size (default 3)
    - Fetches all tracks from both playlists (with `added_at` timestamps)
    - Splits each into old/new halves (by added_at median or configurable split point)
    - Shuffles within each bucket (old_a, new_a, old_b, new_b)
    - Builds sequence: [3 old_a, 3 new_b, 3 new_a, 3 old_b, ...] repeating
    - Creates new playlist with given name
    - Adds tracks in order
    - Returns: playlist URL, track count, summary
  - `list_source_playlists` — Helper to find source playlists by name search
- [ ] Tests for dance mix logic (pattern generation, edge cases)
- [ ] Update README with dance mix usage examples

**Deliverable:** "Create me a bachata-kizomba mix for today" works end-to-end.

---

### Phase 2 — Search + Core Read Tools (v0.3.0)
> Search and read-only metadata tools.

- [ ] `search.py` — search for tracks/albums/artists/playlists
- [ ] `tracks.py` — get_track, get_audio_features, get_audio_analysis
- [ ] `albums.py` — get_album, get_album_tracks, get_saved_albums
- [ ] `artists.py` — get_artist, get_artist_albums, get_related_artists
- [ ] `users.py` — get_top_artists, get_top_tracks (extend existing)
- [ ] `browse.py` — get_categories, get_category, get_recommendations
- [ ] Unit tests with mocked Spotify responses for all tools
- [ ] Update README with available tools list

**Deliverable:** All read-only music metadata tools available.

---

### Phase 3 — Playback Control (v0.4.0)
> Full player control — play, pause, skip, queue, volume, shuffle, repeat.

- [ ] `player.py` — All playback tools:
  - get_playback_state
  - get_devices
  - get_currently_playing
  - play (with context URI or track URIs)
  - pause
  - next_track
  - previous_track
  - seek
  - set_repeat
  - set_volume
  - toggle_shuffle
  - get_queue
  - add_to_queue
  - get_recently_played
  - transfer_playback
- [ ] MCP resource: `now_playing` — current track as a readable resource
- [ ] Tests for all player tools
- [ ] Handle edge cases: no active device, premium-only features

**Deliverable:** Full playback control from Claude.

---

### Phase 4 — Full Playlist CRUD + Library & Shows (v0.5.0)
> Complete playlist management + unified library + shows/audiobooks.

- [ ] `playlists.py` — Remaining playlist tools (extend Phase 0):
  - update_playlist_details (name, description, public/private)
  - remove_items_from_playlist
  - reorder_playlist_items
- [ ] Tests for playlist CRUD operations
- [ ] Handle pagination for large playlists
- [ ] `library.py` — Unified library tools (Feb 2026 API):
  - save_to_library (albums, tracks, episodes, shows, audiobooks)
  - remove_from_library
  - check_saved
- [ ] `shows.py` — get_show, get_show_episodes, get_episode
- [ ] `audiobooks.py` — get_audiobook, get_audiobook_chapters, get_chapter
- [ ] Tests for library and content tools
- [ ] Update README

**Deliverable:** Complete Spotify API coverage.

---

### Phase 5 — Polish & Release (v1.0.0)
> Production quality, docs, publish.

- [ ] Comprehensive error handling with user-friendly messages
- [ ] Input validation (Pydantic) on all tool parameters
- [ ] Rate limit handling with backoff
- [ ] Full test suite (>80% coverage)
- [ ] `ruff` linting + `pyright` type checking — clean
- [ ] CI: GitHub Actions (lint, type check, test on push)
- [ ] README: badges, screenshots/examples, MCP config, troubleshooting
- [ ] `FEATURE-CHECKLIST.md` — all tools documented with status
- [ ] Publish to PyPI as `spotify-mcp`
- [ ] Tag v1.0.0 release on GitHub

**Deliverable:** Public, production-ready MCP server on PyPI.

---

## MCP Tool Summary (48 tools across 11 domains)

| Domain      | Tool                        | Phase | Spotify Scope Required            |
|-------------|-----------------------------|-------|-----------------------------------|
| Users       | get_current_user            | 0     | user-read-private                 |
| Playlists   | get_my_playlists            | 0     | playlist-read-private             |
| Playlists   | get_playlist                | 0     | —                                 |
| Playlists   | get_playlist_items          | 0     | —                                 |
| Playlists   | create_playlist             | 0     | playlist-modify-public/private    |
| Playlists   | add_items_to_playlist       | 0     | playlist-modify-public/private    |
| Dance Mix   | generate_dance_mix          | 1     | playlist-read + playlist-modify   |
| Dance Mix   | list_source_playlists       | 1     | playlist-read-private             |
| Search      | search                      | 2     | —                                 |
| Tracks      | get_track                   | 2     | —                                 |
| Tracks      | get_audio_features          | 2     | —                                 |
| Tracks      | get_audio_analysis          | 2     | —                                 |
| Albums      | get_album                   | 2     | —                                 |
| Albums      | get_album_tracks            | 2     | —                                 |
| Albums      | get_saved_albums            | 2     | user-library-read                 |
| Artists     | get_artist                  | 2     | —                                 |
| Artists     | get_artist_albums           | 2     | —                                 |
| Artists     | get_related_artists         | 2     | —                                 |
| Users       | get_top_artists             | 2     | user-top-read                     |
| Users       | get_top_tracks              | 2     | user-top-read                     |
| Browse      | get_categories              | 2     | —                                 |
| Browse      | get_category                | 2     | —                                 |
| Browse      | get_recommendations         | 2     | —                                 |
| Player      | get_playback_state          | 3     | user-read-playback-state          |
| Player      | get_devices                 | 3     | user-read-playback-state          |
| Player      | get_currently_playing       | 3     | user-read-currently-playing       |
| Player      | play                        | 3     | user-modify-playback-state        |
| Player      | pause                       | 3     | user-modify-playback-state        |
| Player      | next_track                  | 3     | user-modify-playback-state        |
| Player      | previous_track              | 3     | user-modify-playback-state        |
| Player      | seek                        | 3     | user-modify-playback-state        |
| Player      | set_repeat                  | 3     | user-modify-playback-state        |
| Player      | set_volume                  | 3     | user-modify-playback-state        |
| Player      | toggle_shuffle              | 3     | user-modify-playback-state        |
| Player      | get_queue                   | 3     | user-read-playback-state          |
| Player      | add_to_queue                | 3     | user-modify-playback-state        |
| Player      | get_recently_played         | 3     | user-read-recently-played         |
| Player      | transfer_playback           | 3     | user-modify-playback-state        |
| Playlists   | update_playlist_details     | 4     | playlist-modify-public/private    |
| Playlists   | remove_items_from_playlist  | 4     | playlist-modify-public/private    |
| Playlists   | reorder_playlist_items      | 4     | playlist-modify-public/private    |
| Library     | save_to_library             | 4     | user-library-modify               |
| Library     | remove_from_library         | 4     | user-library-modify               |
| Library     | check_saved                 | 4     | user-library-read                 |
| Shows       | get_show                    | 4     | —                                 |
| Shows       | get_show_episodes           | 4     | —                                 |
| Shows       | get_episode                 | 4     | —                                 |
| Audiobooks  | get_audiobook               | 4     | —                                 |
| Audiobooks  | get_audiobook_chapters      | 4     | —                                 |
| Audiobooks  | get_chapter                 | 4     | —                                 |

**Total: 48 tools, 6 phases (v0.1.0 → v1.0.0)**

---

## Required Spotify OAuth Scopes (all requested at auth time)

```
user-read-private
user-read-playback-state
user-modify-playback-state
user-read-currently-playing
user-read-recently-played
user-top-read
user-library-read
user-library-modify
playlist-read-private
playlist-read-collaborative
playlist-modify-public
playlist-modify-private
```

---

## Local Setup (for README)

```bash
# 1. Clone
git clone https://github.com/Patrik1331/spotify_mcp.git
cd spotify_mcp

# 2. Install (uv)
uv sync

# 3. Configure Spotify App
#    Go to https://developer.spotify.com/dashboard
#    Create app → set redirect URI to http://localhost:8888/callback
cp .env.example .env
# Edit .env with your SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET

# 4. Authenticate (opens browser)
uv run spotify-mcp-auth

# 5. Add to Claude Code config (~/.claude/claude_desktop_config.json)
{
  "mcpServers": {
    "spotify": {
      "command": "uv",
      "args": ["--directory", "/path/to/spotify_mcp", "run", "spotify-mcp"]
    }
  }
}
```

---

## Commit Format

```
<type>(<scope>): <short description>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`
Scopes: `auth`, `search`, `tracks`, `albums`, `artists`, `player`, `playlists`, `dance-mix`, `library`, `shows`, `audiobooks`, `browse`, `server`
