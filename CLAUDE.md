# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A single-process Telegram bot built on `python-telegram-bot` v22+. It detects music URLs in chat messages, resolves them through Songlink/Odesli into per-platform links (Spotify, Apple Music, YouTube, Tidal, Deezer, SoundCloud, …), and tracks per-chat 👍/👎 reactions in SQLite so it can power leaderboards, inline mode and weekly/monthly digests.

There is **no web frontend** and **no audio download** path. Both were intentionally dropped in the v2 rewrite.

## Commands

```bash
uv sync --extra dev                                    # create venv + install deps
uv run python -m banger_link                           # run the bot (reads .env)

uv run pytest                                          # full suite (coverage on)
uv run pytest -k toggle --no-cov                       # filter + skip coverage
uv run pytest tests/test_repo.py::test_toggle_cycle    # single test

uv run ruff check . && uv run ruff format --check .    # lint + format
uv run mypy banger_link                                # types

docker compose up -d --build                           # single-container deploy
```

## Required environment

`TELEGRAM_TOKEN` is validated at import time in `banger_link/config.py` (a `pydantic-settings` `BaseSettings`). The module instantiates the singleton `settings = Settings()` on import, so any test that imports `banger_link.*` needs the env var set first — `tests/conftest.py` does this with stub values before any imports.

`WHITELISTED_CHAT_IDS` (comma-separated, supports negative group IDs) gates which chats the bot answers; empty = all chats. `IGNORED_DOMAINS` (semicolon-separated substrings) suppresses link processing entirely.

## Architecture

```
banger_link/
├── __main__.py            ApplicationBuilder, post_init/post_shutdown lifecycle, run_polling
├── config.py              pydantic-settings Settings singleton + .env parsing
├── db/
│   ├── schema.sql         CREATE TABLE statements; applied via PRAGMA user_version
│   ├── connection.py      Database — single aiosqlite conn, WAL, schema-on-startup, healthcheck()
│   └── repo.py            Repo — typed methods + ChatSongView/ReactionState/MentionResult dataclasses
├── services/
│   ├── songlink.py        SonglinkClient over httpx; ResolvedSong dataclass; retries on 5xx/429/timeouts
│   └── formatter.py       HTML message templates + reaction_keyboard / leaderboard_message / help_message
├── handlers/
│   ├── _state.py          REPO_KEY / SONGLINK_KEY: install + getter helpers around application.bot_data
│   ├── messages.py        URL extract → music-domain check → resolve → upsert + record_mention → reply
│   ├── callbacks.py       parses `r:<chat_song_id>:<l|d>`, repo.toggle_reaction, edits reply_markup
│   ├── commands.py        /start /help /top /weekly /monthly /search + register_commands(post_init)
│   └── inline.py          @bot inline query → repo.search_global → InlineQueryResultArticle list
├── jobs/
│   └── digests.py         JobQueue.run_daily for weekly + monthly leaderboards (monthly gates on day==1)
└── health.py              aiohttp /health on settings.health_port; returns 503 if DB ping fails
```

### Inbound flow

```
Telegram update
  ├── MessageHandler (TEXT & ~COMMAND)
  │     handlers/messages.py: extract URL → MUSIC_DOMAIN_SUFFIXES gate → SonglinkClient.resolve
  │     → Repo.upsert_song / record_mention / touch_chat → reply_html with reaction_keyboard
  ├── CallbackQueryHandler(pattern=r"^r:")
  │     handlers/callbacks.py: split "r:<id>:<l|d>" → Repo.toggle_reaction → edit_message_reply_markup
  ├── CommandHandlers (start, help, top, weekly, monthly, search)
  └── InlineQueryHandler — searches the global songs table (chat-where-typing is unknown to inline mode)
```

### Storage invariants

- `reactions` is the source of truth; `likes` / `dislikes` are computed at read time with `SUM(CASE WHEN kind='like' …)`. Don't add denormalized counters.
- `chat_songs` is keyed by `UNIQUE(chat_id, song_id)`; `record_mention` upserts via `ON CONFLICT … RETURNING` to atomically increment `mentions` and stamp `last_seen_at`.
- `songs.entity_id` is Songlink's `entityUniqueId`, stable across services. `upsert_song` uses `ON CONFLICT(entity_id) DO UPDATE` so re-resolving a song refreshes its title/artist/links without duplicating rows.
- `callback_data` format is `r:<chat_song_id>:<l|d>` — well under the 64-byte Telegram cap. Never put URLs in callback payloads.

### Cross-cutting

- **App lifecycle** runs through PTB's `post_init` (`_on_startup`) and `post_shutdown` (`_on_shutdown`) in `__main__.py`. The DB connection, `SonglinkClient`, and `HealthServer` all live for the duration of the bot process and are stored on `application.bot_data` under namespaced keys (see `handlers/_state.py`).
- **State injection**: handlers never import the singleton db/songlink directly — they pull them from `context.bot_data` via `_state.get_repo` / `_state.get_songlink`. This keeps tests able to swap implementations.
- **JobQueue requires the `[job-queue]` extra** on `python-telegram-bot`; it's already in `pyproject.toml` dependencies. If `application.job_queue` is `None`, `schedule_digests` logs a warning and no-ops — the rest of the bot still works.

## Conventions worth knowing

- **Async everywhere.** No sync HTTP clients, no `threading`. SQLite goes through `aiosqlite`; HTTP through `httpx.AsyncClient`.
- **HTML formatting**, not Markdown — `reply_html` and `ParseMode.HTML` everywhere. All user-supplied text is run through `html.escape` in the formatter.
- **Music-domain whitelist** lives in `handlers/messages.py:MUSIC_DOMAIN_SUFFIXES`. Songlink handles a lot of URL shapes, but we don't want to call it on every random URL — add a domain there if you want to extend coverage.
- **Single-connection SQLite** is fine for this workload (one process, low write rate). Don't add a connection pool unless you also add a writer queue, since a second writer connection negates WAL's read-while-write benefit and adds locking surprises.

## Memory & user context

The user did a deliberate ground-up rewrite from a Copilot/GPT-4-era v1 to this v2 with Opus 4.7. The legacy frontend (`banger_web/`), the `pytube` download path, the TinyDB store, and the per-service HTML scrapers have all been removed and should not be re-introduced. If you're tempted to bring any of them back, ask first.
