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
- **BPM Lookup** — Get the tempo of a track or every track in a playlist, via [GetSongBPM](https://getsongbpm.com) (Spotify no longer exposes tempo data itself)

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

All server data lives in one directory:

```
~/.claude-mcp/spotify-mcp/          (C:\Users\<you>\.claude-mcp\spotify-mcp\ on Windows)
├── .env          your credentials
├── tokens.json   written by the auth flow, refreshed automatically
└── certs/        only if you use an HTTPS redirect URI
```

The server creates `.env` with empty values on first run, so just start it once
and fill in the blanks:

```env
SPOTIFY_CLIENT_ID=
SPOTIFY_CLIENT_SECRET=
SPOTIFY_REDIRECT_URI=
```

Use `http://127.0.0.1:8888/callback` as the redirect URI, matching your Spotify
app. The server reads this fixed path, so it works no matter which directory the
MCP client launches it from — credentials never belong in your MCP client's
config file.

For local development you can instead keep a `.env` in the repo root
(`cp .env.example .env`); `~/.claude-mcp/spotify-mcp/.env` takes precedence.

### 4. Authenticate

Ask Claude to run the **`authenticate`** tool. It opens Spotify's authorization
page in your browser, waits for you to approve, and stores the tokens — no shell
command needed. Your credentials never pass through the client; only the URL does.

The **`auth_status`** tool reports whether the server is configured and signed
in, and what to fix if it isn't. A stdio MCP server always shows as connected,
even with an empty `.env`, so use this rather than trusting the green check.

From a terminal instead:

```bash
uv run spotify-mcp-auth
```

Either way, tokens are saved to `~/.claude-mcp/spotify-mcp/tokens.json` and refreshed automatically.

### 5. Add to Claude Code

One command, no credentials in the config:

```bash
claude mcp add spotify --scope user -- \
  uvx --python 3.12 --from git+https://github.com/Patrik1331/spotify_mcp.git spotify-mcp
```

`--scope user` registers the server for every directory. Credentials come from
`~/.claude-mcp/spotify-mcp/.env` (step 3) — do not add an `env` block here.

Restart Claude Code afterwards; MCP servers are loaded at startup.

### 6. Optional: BPM Lookup

Spotify retired its own tempo/audio-features endpoint, so `get_track_bpm` and
`get_playlist_bpm` look up BPM via the third-party
[GetSongBPM](https://getsongbpm.com) API instead. Without a key, every other
tool still works — these two just return an error telling you what's missing.

1. Go to [getsongbpm.com/api](https://getsongbpm.com/api) and fill in the form:
   - **Website URL or App ID/Package Name**: this repo's URL is fine —
     `https://github.com/Patrik1331/spotify_mcp`
   - **Backlink URL**: mandatory for a free key. This README's credit link
     below satisfies it.
   - **Email**: your key gets sent here.
2. Add the key to `~/.claude-mcp/spotify-mcp/.env` (same file as your Spotify
   credentials):

```env
GETSONGBPM_API_KEY=
```

## Usage Examples

**Dance Mix:**
> "Create a bachata-kizomba mix called 'Dance Night 2026-03-11' using my Bachata and Kizomba playlists, 3 songs per block"

**Search:**
> "Search for bachata tracks by Romeo Santos"

**Playback:**
> "Play my new dance mix playlist"

**BPM:**
> "What's the BPM of every song in my Bachata playlist?"

## License

MIT

---

BPM data powered by [GetSongBPM](https://getsongbpm.com).
