<p align="center">
  <img src="./docs/logo.png" alt="Banger Link Logo" width="200">
</p>

<h1 align="center">Banger Link</h1>

<p align="center">
  Drop a music link in your Telegram chat. Get it back as links for every other major streaming service.
</p>

<p align="center">
  <a href="https://github.com/luisg0nc/banger-link/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/luisg0nc/banger-link?style=flat-square" alt="License">
  </a>
  <img src="https://img.shields.io/badge/python-3.12-blue?style=flat-square" alt="Python 3.12">
  <img src="https://img.shields.io/badge/python--telegram--bot-22-blue?style=flat-square" alt="python-telegram-bot 22">
</p>

## What it does

Share an Apple Music / Spotify / YouTube / Tidal / Deezer / SoundCloud (and more) link in any chat the bot is in. Banger Link replies with the song's title and artist plus a link for each service everyone else uses, so nobody has to copy-paste between apps.

It also keeps a per-chat history with 👍 / 👎 reactions, so over time the bot can answer "what were the bangers we shared this month?" via slash commands and inline mode.

## Features

- 🔁 **Any-to-any link conversion** via [Songlink/Odesli](https://song.link). One scraper-free dependency replaces the legacy per-platform scrapers.
- 👍👎 **Per-user, per-chat reactions** stored in SQLite. Toggle on/off, switch between like and dislike.
- 🏆 **Leaderboards** with `/top`, `/weekly`, `/monthly`.
- 🔎 **Search** this chat's history with `/search <query>` or globally via inline mode (`@bangerbot oasis`).
- 📅 **Weekly + monthly digests** posted automatically into active chats.
- 📜 **Slash command menu** registered with Telegram so users see suggestions.
- 🩺 **Healthcheck** on `:8080/health` for container orchestration.

## Quick start

### Prerequisites

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) for dependency management
- A Telegram bot token from [@BotFather](https://t.me/BotFather)

### Local development

```bash
uv sync --extra dev               # creates .venv and installs deps
cp .env.example .env              # then edit TELEGRAM_TOKEN
uv run python -m banger_link
```

For inline mode to work, send `/setinline` to BotFather.

### Tests

```bash
uv run pytest                     # full suite with coverage
uv run pytest -k toggle --no-cov  # single test, no coverage report
uv run ruff check . && uv run ruff format --check .
uv run mypy banger_link
```

### Docker

```bash
docker compose up -d --build
docker compose logs -f banger-link
```

The container persists state under `./data/banger.db` (bind-mounted into `/app/data`).

## Configuration

All configuration is read from environment variables (or `.env`). See [`.env.example`](.env.example) for the full list. The most useful knobs:

| Variable | Default | Meaning |
| --- | --- | --- |
| `TELEGRAM_TOKEN` | *(required)* | BotFather token. |
| `WHITELISTED_CHAT_IDS` | empty | Comma-separated chat IDs. Empty = bot answers everywhere. |
| `IGNORED_DOMAINS` | empty | Semicolon-separated domain substrings to skip. |
| `DATA_DIR` | `./data` | Where the SQLite DB lives. |
| `HEALTH_PORT` | `8080` | Port for `/health`. |
| `LOG_LEVEL` | `INFO` | Standard Python log levels. |
| `DIGEST_TIMEZONE` | `UTC` | IANA name (e.g. `Europe/Lisbon`). |
| `DIGEST_HOUR` | `12` | Local hour at which digests are posted. |

## Bot commands

| Command | What it does |
| --- | --- |
| `/help`, `/start` | Onboarding. |
| `/top [N]` | Top N bangers in this chat (all-time, by `likes − dislikes`). |
| `/weekly [N]` | Top of the last 7 days. |
| `/monthly [N]` | Top of the last 30 days. |
| `/search <query>` | Title/artist search across this chat's history. |
| `@bangerbot <query>` | Inline mode — search the global song catalog from any chat. |

## Architecture

```
Telegram update
  ├── MessageHandler → SonglinkClient → Repo (upsert song + record mention) → reply with reaction keyboard
  ├── CallbackQueryHandler (pattern ^r:) → Repo.toggle_reaction → edit reply_markup
  ├── CommandHandler(/top, /weekly, /monthly, /search, /help) → Repo.top_for_chat / search_chat
  └── InlineQueryHandler → Repo.search_global → InlineQueryResultArticle list

JobQueue
  ├── weekly-digest  (Mondays at DIGEST_HOUR) → leaderboards posted into active chats
  └── monthly-digest (every day, no-ops unless day == 1)

Health server (aiohttp on :8080)
  └── /health → SELECT 1 against the DB
```

Storage is a single SQLite database (WAL mode) with three tables: `songs` (global, dedup by Songlink `entityUniqueId`), `chat_songs` (one row per chat × song), and `reactions` (one row per chat_song × user). Likes/dislikes are computed at read time from `reactions` — no denormalized counters to keep in sync.

## License

MIT — see [LICENSE](LICENSE).
