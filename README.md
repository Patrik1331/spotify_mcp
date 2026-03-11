# Spotify MCP Server

> Spotify Web API v1 (post-February 2026) as MCP tools for Claude Code

Control Spotify from Claude — search, manage playlists, control playback, and generate dance mix playlists with genre-alternating patterns.

## Features

- **Dance Mix Generator** — Create playlists alternating genres in blocks (e.g., 3 bachata → 3 kizomba), mixing old favorites with new tracks
- **Playlist Management** — Read, create, and modify playlists
- **Search** — Search tracks, albums, artists
- **Playback Control** — Play, pause, skip, volume, queue
- **Library** — Save/remove items from your library
- **Browse** — Categories, recommendations

## Setup

### 1. Create Spotify App

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Set redirect URI to `http://localhost:8888/callback`
4. Note your Client ID and Client Secret

### 2. Install

```bash
git clone https://github.com/Patrik1331/spotify_mcp.git
cd spotify_mcp
uv sync
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your Spotify credentials
```

### 4. Authenticate

```bash
uv run spotify-mcp-auth
```

This opens your browser for Spotify login. Tokens are saved to `~/.spotify_mcp/tokens.json`.

### 5. Add to Claude Code

Add to your Claude Code MCP settings (`~/.claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "spotify": {
      "command": "uv",
      "args": ["--directory", "/path/to/spotify_mcp", "run", "spotify-mcp"]
    }
  }
}
```

## Usage Examples

**Dance Mix:**
> "Create a bachata-kizomba mix called 'Dance Night 2026-03-11' using my Bachata and Kizomba playlists, 3 songs per block"

**Search:**
> "Search for bachata tracks by Romeo Santos"

**Playback:**
> "Play my new dance mix playlist"

## License

MIT
