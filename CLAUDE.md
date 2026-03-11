# Spotify MCP Server — Project Intelligence

## Shared Profile
At session start, read: `C:\Users\Patri\OneDrive\AI Tools\AI-USER-PROFILE.md`

## Overview
MCP server exposing Spotify Web API as tools for Claude Code.
Python 3.12+, runs locally via stdio transport.

**Spotify Web API:** v1 (post-February 2026 consolidation, March 2026 revision)
**Repository:** https://github.com/Patrik1331/spotify_mcp.git (public, MIT)

## Key Documents
- `ROADMAP.md` — Phased implementation plan (source of truth for scope)
- `README.md` — Public setup guide
- `pyproject.toml` — Dependencies and scripts

## Stack
- Python 3.12+, `mcp` SDK (official), `httpx` (async HTTP), `pydantic` v2
- OAuth 2.0 Authorization Code + PKCE flow
- Token storage: `~/.spotify_mcp/tokens.json`
- Package manager: `uv`

## Architecture
```
src/spotify_mcp/
├── server.py      — MCP server entry (stdio transport, tool registration)
├── auth.py        — OAuth PKCE flow, token refresh, persistence
├── client.py      — httpx wrapper (auth headers, 401 retry, 429 backoff)
├── models.py      — Pydantic models
└── tools/         — One module per Spotify domain
    ├── playlists.py   — Playlist CRUD
    ├── dance_mix.py   — 3-3 pattern generator (priority feature)
    ├── search.py, tracks.py, albums.py, artists.py
    ├── player.py, library.py, users.py
    ├── shows.py, audiobooks.py, browse.py
    └── __init__.py    — Tool registration
```

## Priority Feature: Dance Mix Generator
Creates playlists alternating genres in blocks of 3 (e.g., 3 bachata → 3 kizomba).
Mixes old favorites with recently added tracks to avoid repetition.
See ROADMAP.md Phase 1 for full spec.

## Development Rules
- **Security first:** No secrets in repo, `.env.example` pattern, PKCE (no client_secret in auth flow)
- **Git:** Feature branches, conventional commits (`feat(scope): description`)
- **Python:** async/await, type hints, strict pyright
- **No unrequested features** — implement what's in the roadmap phase

## Coding Style
- async/await everywhere (httpx is async)
- Type hints on all function signatures
- Pydantic for request/response validation
- Comments for "why" not "what"
- f-strings over .format()

## Current Phase
Phase 0 — Skeleton + Auth (v0.1.0)
Then immediately Phase 1 — Dance Mix Generator (v0.2.0)

## Spotify API Notes (Post-Feb 2026)
- Search limit max reduced to 10 (default 5)
- Playlist items path: `/playlists/{id}/items` (not `/tracks`)
- Unified library: `PUT/DELETE /me/library` (replaces individual endpoints)
- Removed fields: available_markets, popularity, followers
- Removed: batch GET endpoints, Artist's Top Tracks, public user endpoints
