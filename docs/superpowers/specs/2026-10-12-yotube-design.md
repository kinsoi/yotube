# Yotube — Design Spec

**Date:** 2026-10-12
**Status:** Draft, awaiting review

## 1. Purpose

Yotube is a self-hosted web app that turns YouTube Music content into Yoto
"Make Your Own" (MYO) playlists. A parent builds a playlist either by
searching tracks or by importing an existing YouTube Music playlist; the
result lands in the Yoto library, where it plays from the Yoto app or from a
physical MYO card linked to it.

It runs as a single small Docker image on a home machine, serves one Yoto
account, and is published on GitHub (`kinsoi/yotube`) so family members can
run their own instance.

### Success criteria

- Paste a YouTube Music playlist URL (or pick ~10 searched tracks), click one
  button, and see the playlist in the Yoto app a few minutes later, with live
  progress in the UI.
- Imported playlists stay mirrored with YouTube Music: on demand and nightly.
- Each track gets a meaningful 16×16 pixel-art icon on the player screen.
- `docker compose up` plus a one-time Yoto login is all a family member
  needs, guided by the README.

### Decisions taken

| Topic | Decision |
|---|---|
| Hosting | Local Docker container, one image, `/data` volume |
| Accounts | One Yoto account per instance, no in-app auth |
| Playlist sources | Search ("compose") and YouTube Music playlist import |
| Sync | Mirror exact (adds, removals, order); manual button + scheduled nightly sync, per-playlist toggle |
| Unavailable tracks | Keep the already-uploaded Yoto version, flag it in the UI |
| Shuffle | Per-playlist option: native Yoto `config.shuffle` (player) + reshuffled chapter order at each sync (app) |
| Icons | Claude picks a public Yoto icon → keyword match fallback → default music-note icon; manual override |
| UI languages | English, French, Russian; browser language by default |
| Stack | Python 3.12 / FastAPI backend, Svelte + Vite frontend built into the image |
| Code language | English (code, comments, README; short French README section) |

### Out of scope (YAGNI)

Multiple accounts, in-app login/password, direct streaming tracks, non-YouTube
audio sources, managing physical cards through the API, pixelated cover art
icons.

## 2. Architecture

One process inside one container:

- **FastAPI** serves the REST API, a Server-Sent Events (SSE) progress stream,
  and the compiled Svelte UI as static files.
- **SQLite** (SQLAlchemy 2.x) in `/data/yotube.db`.
- **APScheduler** (in-process) triggers the scheduled sync.
- **yt-dlp** downloads the best native audio stream (m4a/opus). No ffmpeg: Yoto
  transcodes uploads itself, which keeps the image small (~150 MB target).

```
yotube/
├── backend/
│   ├── app/
│   │   ├── main.py          FastAPI app factory, routers, static UI, SSE
│   │   ├── config.py        Settings from env (pydantic-settings)
│   │   ├── api/             HTTP routers (playlists, search, auth, settings, icons, events)
│   │   ├── db/              SQLAlchemy models, session, repositories
│   │   ├── yoto/            Yoto API client (auth, media upload, content, icons)
│   │   ├── youtube/         ytmusicapi search/import, yt-dlp download
│   │   ├── icons/           Icon selection strategies
│   │   ├── sync/            Sync engine (diff, upload, content build)
│   │   └── scheduler.py     Scheduled sync
│   ├── tests/
│   └── pyproject.toml
├── frontend/                Svelte + Vite + TypeScript, i18n (en/fr/ru)
├── Dockerfile               Multi-stage: node build → python:3.12-slim runtime
├── docker-compose.yml
├── .env.example
└── .github/workflows/ci.yml
```

### Module boundaries

- **`yoto/`** is the only code talking to Yoto. Public interface (a
  `YotoClient` protocol):
  - `upload_audio(path) -> UploadedMedia` (sha256, duration, file size, channels, format)
  - `upload_icon(png_bytes) -> str` (media id)
  - `list_public_icons() -> list[PublicIcon]` (id, title, tags), cached
  - `save_content(content: YotoContent, card_id: str | None) -> str` (returns card id)
  - `delete_content(card_id)`
  Token refresh is transparent. Refresh tokens are single-use: every refresh
  persists the new refresh token atomically.
- **`youtube/`** is the only code talking to YouTube. Interface (a
  `MusicSource` protocol):
  - `search(query) -> list[TrackInfo]`
  - `get_playlist(url_or_id) -> PlaylistInfo` (title, thumbnail, ordered tracks)
  - `download_audio(video_id, dest_dir) -> Path`, raising `TrackUnavailable`
- **`icons/`**: `IconPicker.pick(title, artist) -> str` (Yoto icon id). Chain:
  `ClaudeIconPicker` (if `ANTHROPIC_API_KEY` set) → `KeywordIconPicker` →
  default icon.
- **`sync/`**: `SyncEngine.sync(playlist_id, progress_cb)`. Depends only on the
  protocols above and the repositories, so it is unit-tested with fakes.

## 3. Data model

- **`playlist`**: id, title, `source_type` (`youtube` | `manual`),
  `source_url` (nullable), `yoto_card_id` (nullable until first sync),
  `shuffle` (bool), `auto_sync` (bool), `color`, `cover_url`,
  `last_sync_at`, `last_sync_status` (`ok` | `partial` | `error` | `running`),
  `last_sync_error`, timestamps.
- **`track`**: id, playlist_id, `video_id`, title, artist, duration, position,
  `icon_id`, `icon_manual` (bool), `status` (`pending` | `uploaded` |
  `unavailable` | `error`), `error`.
- **`uploaded_media`**: `video_id` (PK), `sha256`, duration, file_size,
  channels, format, uploaded_at. Global cache: a video shared by several
  playlists is downloaded and uploaded once.
- **`oauth_token`**: single row; access token, refresh token, expiry.
- **`app_setting`**: key/value (e.g. UI default language).

Schema created on startup; Alembic migrations from the first release so
family instances upgrade cleanly.

## 4. Yoto integration

Based on the yoto.dev documentation; exact field names are verified against
the API reference during implementation.

- **Auth:** OAuth 2 Authorization Code + PKCE on `login.yotoplay.com`
  (`/authorize`, `/oauth/token`), audience `https://api.yotoplay.com`, scopes
  `user:content:manage offline_access` (plus whatever the icon endpoints
  require). Redirect URI `http://localhost:8080/auth/callback`, registered in
  the Yoto developer dashboard as a public client. PKCE verifier and `state`
  kept server-side for the duration of the login.
- **Audio upload:** `GET /media/transcode/audio/uploadUrl` → `PUT` file to
  `uploadUrl` → poll `GET /media/upload/{uploadId}/transcoded` until
  `transcodedSha256` is present (bounded polling with backoff, timeout).
- **Content:** `POST /content` with `title`, `content.chapters[]` (one chapter
  with one track per song; `trackUrl: "yoto:#<sha256>"`,
  `display.icon16x16: "yoto:#<iconId>"`), `content.config.shuffle` when
  enabled (`[{start: 0, end: n-1, limit: n}]`), `metadata.cover.imageL` and
  `metadata.media` totals. First sync creates the content; later syncs update
  the same `cardId`, so linked MYO cards follow automatically.
- **Cover:** playlist thumbnail uploaded via the cover image endpoint.
- **Icons:** public icon list fetched from the Yoto API and cached in memory
  (refreshed daily); icon chosen by id. Custom uploads via
  `/media/displayIcons/user/me/upload` are supported by the client but only
  used for the default icon asset.
- **Limits:** max 100 chapters per playlist; beyond that, keep the first 100
  and warn.

## 5. Sync engine

`sync(playlist)`:

1. Acquire the global sync lock (one sync at a time app-wide; a second
   request for the same playlist returns "already running").
2. **Resolve source.** YouTube playlists: fetch the ordered track list. Manual
   playlists: use the stored tracks.
3. **Diff** against stored tracks: insert new rows, delete removed ones (mirror
   exact), update positions. A source track that is now unavailable but has
   `uploaded_media` stays and is flagged `unavailable`.
4. **Upload missing media.** For each track without `uploaded_media`:
   download to a temp dir under `/data/tmp`, upload, poll transcoding, store
   in cache, delete temp file. Concurrency 2. Per-track retries (3, exponential
   backoff) for transient errors. `TrackUnavailable` → track status
   `unavailable`/`error`, sync continues.
5. **Pick icons** for tracks without one (manual choices never overwritten).
6. **Build and save Yoto content** from all tracks that have media, in source
   order, or freshly shuffled when `shuffle` is on. The Yoto write happens
   once, at the end, so an interrupted sync never leaves a half-built
   playlist.
7. Record status: `ok`, `partial` (some tracks failed), or `error`.

Progress events (`{playlist_id, phase, current, total, track_title, message}`)
are published to an in-memory broker and streamed to the UI over SSE.

**Scheduler:** cron from `SYNC_CRON` (default `0 3 * * *`, honouring `TZ`);
runs sequentially over playlists with `auto_sync = true`. A "reshuffle now"
action rebuilds and saves content without touching YouTube.

**Failure handling:**

- Yoto auth expired/revoked → scheduled sync stops, a global "Reconnect to
  Yoto" banner appears.
- yt-dlp breakage → `YTDLP_AUTO_UPDATE=true` (default) runs
  `pip install -U yt-dlp` at container start.
- Container restart mid-sync → playlists left `running` are reset to `error`
  with a "interrupted" message at startup.

## 6. HTTP API (sketch)

- `GET /api/auth/status`, `GET /api/auth/login` (redirect), `GET /auth/callback`, `POST /api/auth/logout`
- `GET /api/search?q=` → tracks
- `GET /api/youtube/playlist?url=` → preview
- `GET/POST /api/playlists`, `GET/PATCH/DELETE /api/playlists/{id}`
- `PUT /api/playlists/{id}/tracks` (manual playlists: full ordered list)
- `PATCH /api/playlists/{id}/tracks/{track_id}` (icon override)
- `POST /api/playlists/{id}/sync`, `POST /api/playlists/{id}/reshuffle`
- `GET /api/icons?q=` → public icons (for the picker)
- `GET /api/settings`, `PATCH /api/settings`
- `GET /api/events` (SSE)

Deleting a playlist asks whether to delete it on Yoto too.

## 7. User interface

Svelte + Vite + TypeScript, `svelte-i18n` with `en`, `fr`, `ru` dictionaries.

**Look:** Yoto-inspired without Yoto branding or logo: bright saturated
colours (orange, yellow, blue, green) on a warm cream background, very
rounded corners, soft shadows, Nunito font, playlists drawn as portrait Yoto
cards, track icons rendered as enlarged crisp pixel art
(`image-rendering: pixelated`), gentle "card insert" and progress animations.
Responsive down to phone width.

**Screens:**

1. **Library** — grid of playlist cards with status badge, auto-sync and
   shuffle indicators; "New playlist" button; reconnect banner if needed.
2. **New playlist** — tabs *Import* (paste URL → preview → create) and
   *Compose* (search → basket → name → create). Creation starts the first
   sync immediately.
3. **Playlist detail** — tracks with pixel icons (click to open an icon picker
   with search), drag-and-drop reorder for manual playlists, add/remove tracks
   for manual playlists, toggles (shuffle, auto-sync), colour, "Sync now",
   "Reshuffle", live progress, per-track errors, and a hint on linking a MYO
   card in the Yoto app.
4. **Settings** — Yoto connection, language, sync schedule (read-only display
   of `SYNC_CRON`), icon AI status.

## 8. Configuration

| Variable | Default | Purpose |
|---|---|---|
| `YOTO_CLIENT_ID` | — (required) | Yoto developer app client id |
| `PUBLIC_URL` | `http://localhost:8080` | Base for the OAuth redirect URI |
| `ANTHROPIC_API_KEY` | empty | Enables Claude icon picking |
| `ANTHROPIC_MODEL` | `claude-haiku-5-5` | Model for icon picking |
| `SYNC_CRON` | `0 3 * * *` | Scheduled sync |
| `TZ` | `Europe/Paris` | Scheduler timezone |
| `PORT` | `8080` | HTTP port |
| `YTDLP_AUTO_UPDATE` | `true` | Update yt-dlp at start |
| `LOG_LEVEL` | `INFO` | Logging |

## 9. Quality and testing

- **Backend:** pytest. Sync engine against fake `YotoClient` / `MusicSource`
  (diff, cache reuse, mirror removals, unavailable tracks, shuffle config,
  interrupted sync, 100-track cap). Yoto client against `respx`-mocked HTTP
  (PKCE exchange, refresh rotation, transcode polling, retries). Icon pickers
  with a mocked Anthropic client. API routes with FastAPI `TestClient`.
- **Frontend:** Vitest for key components and a test asserting the three
  locale files share exactly the same keys.
- **Lint/types:** ruff, mypy (strict on `sync/`, `yoto/`), ESLint, Prettier,
  svelte-check.
- **CI (GitHub Actions):** lint + tests + Docker build on push/PR; on tags,
  publish a multi-arch image (amd64/arm64) to `ghcr.io/kinsoi/yotube`.
- **Security:** no secrets in the image or repo; `.env` git-ignored; README
  warns not to expose the app to the internet (no in-app auth).

## 10. Distribution

README (English, with a short French section): what it does, Yoto developer
app setup (public client, redirect URI, scopes), `.env` setup,
`docker compose up`, first login (from the host machine because of the
`localhost` redirect), linking a MYO card, updating, troubleshooting, and a
note that downloading from YouTube is for personal use and may conflict with
YouTube's terms of service.
