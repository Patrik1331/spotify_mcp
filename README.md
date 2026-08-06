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

### 1. Create a Spotify App

1. Go to the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Click **Create app**
3. Fill in the app details:
   - **App name**: Choose any name (e.g., `spotify-mcp`)
   - **App description**: MCP server for Spotify
   - **Redirect URIs**: `http://127.0.0.1:8888/callback` (see below)
   - **Which API/SDKs are you planning to use?**: Select **Web API**
4. Click **Save**
5. Go to **Settings** and note your **Client ID** and **Client Secret**

#### Redirect URI Configuration

Spotify enforces strict rules for redirect URIs ([documentation](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri)):

- **HTTPS is required** for all redirect URIs, **except** loopback IP addresses
- **`localhost` is not allowed** — you must use the IP address `127.0.0.1` instead
- Loopback addresses (`http://127.0.0.1`) are the only exception where HTTP is permitted

Set your redirect URI to:

```
http://127.0.0.1:8888/callback
```

> **Important:** Do not use `localhost`, `https://localhost`, or any variation with `localhost`. Spotify will reject these with "Invalid redirect URI" or "Insecure redirect URI" errors.

### 2. Install

```bash
git clone https://github.com/Patrik1331/spotify_mcp.git
cd spotify_mcp
uv sync
```

### 3. Configure

Create `~/.spotify_mcp/.env` (`C:\Users\<you>\.spotify_mcp\.env` on Windows):

```env
SPOTIFY_CLIENT_ID=your_client_id_here
SPOTIFY_CLIENT_SECRET=your_client_secret_here
SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
```

This is the only file you need to create. The server reads it from that fixed
path, so it works no matter which directory the MCP client launches it from —
credentials never belong in your MCP client's config file.

For local development you can instead keep a `.env` in the repo root
(`cp .env.example .env`); `~/.spotify_mcp/.env` takes precedence.

### 4. Authenticate

```bash
uv run spotify-mcp-auth
```

This opens your browser for Spotify authorization. After approving, tokens are saved to `~/.spotify_mcp/tokens.json` and refreshed automatically.

### 5. Add to Claude Code

One command, no credentials in the config:

```bash
claude mcp add spotify --scope user -- \
  uvx --python 3.12 --from git+https://github.com/Patrik1331/spotify_mcp.git spotify-mcp
```

`--scope user` registers the server for every directory. Credentials come from
`~/.spotify_mcp/.env` (step 3) — do not add an `env` block here.

Restart Claude Code afterwards; MCP servers are loaded at startup.

## Usage Examples

**Dance Mix:**
> "Create a bachata-kizomba mix called 'Dance Night 2026-03-11' using my Bachata and Kizomba playlists, 3 songs per block"

**Search:**
> "Search for bachata tracks by Romeo Santos"

**Playback:**
> "Play my new dance mix playlist"

## License

MIT
