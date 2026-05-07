<p align="center">
  <img src="./docs/logo.png" alt="Banger Link Logo" width="180">
</p>

<h1 align="center">Banger Link</h1>

<p align="center">
  <em>Drop a music link in your group chat. The bot replies with links for every other major streaming service, so nobody has to leave their app.</em>
</p>

<p align="center">
  <a href="https://github.com/luisg0nc/banger-link/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/luisg0nc/banger-link/ci.yml?branch=main&label=tests&style=flat-square" alt="CI"></a>
  <a href="https://github.com/luisg0nc/banger-link/pkgs/container/banger-link"><img src="https://img.shields.io/badge/ghcr.io-banger--link-2496ED?style=flat-square&logo=docker&logoColor=white" alt="Container image"></a>
  <a href="https://github.com/luisg0nc/banger-link/blob/main/LICENSE"><img src="https://img.shields.io/github/license/luisg0nc/banger-link?style=flat-square" alt="License"></a>
  <img src="https://img.shields.io/badge/python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.12">
  <img src="https://img.shields.io/badge/python--telegram--bot-22-26A5E4?style=flat-square&logo=telegram&logoColor=white" alt="python-telegram-bot 22">
</p>

---

## The problem

You're in a group chat with friends. Someone shares a Spotify link. Half the chat is on Apple Music, two people are on YouTube Music, one holdout uses Tidal. To play the song, everyone copy-pastes the title into their own app.

## The fix

Banger Link sits in your chat and watches for music links. When it sees one, it replies with the song laid out for every service:

```
🎵 Lust for Life — Iggy Pop

🟢 Spotify        🍎 Apple Music    ▶️ YouTube
🎶 YouTube Music  🌊 Tidal          🎧 Deezer
☁️ SoundCloud    🛒 Amazon Music

✨ First time in this chat! 🎉
[👍 0]  [👎 0]
```

Tap 👍 or 👎 to vote — the counts update live and the bot remembers your reactions so it can build leaderboards. Re-shares show *"Shared 4× — first by Alice on Mar 12"*.

## Features

- 🔁 **Any-to-any link conversion** for ten+ streaming services, powered by [Songlink/Odesli](https://song.link). No per-platform scrapers to break.
- 👍 / 👎 **Per-user reactions** with toggle, change-vote, and live count updates.
- 🏆 **Per-chat leaderboards** via `/top`, `/weekly`, `/monthly`.
- 🔎 **Search** this chat's history with `/search <query>`, or fire off `@bangerbot <query>` from any chat to share a tune inline.
- 📅 **Weekly + monthly digests** posted automatically — recap the chat's bangers without anyone asking.
- 📜 **Native Telegram slash-command menu** (registered via `setMyCommands`).
- 🐳 **Multi-arch Docker image** (`linux/amd64` + `linux/arm64`) on GHCR.
- 🩺 **HTTP healthcheck** for container orchestration.

## Bot commands

| Command | What it does |
| --- | --- |
| `/help`, `/start` | Onboarding. |
| `/top [N]` | Top bangers in this chat (all-time, by `likes − dislikes`). |
| `/weekly [N]` | Top of the last 7 days. |
| `/monthly [N]` | Top of the last 30 days. |
| `/search <query>` | Title/artist search across this chat's history. |
| `@bangerbot <query>` | Inline mode — pick a known banger and share it into the current chat. |

## Run it

### Docker (recommended)

A pre-built multi-arch image is published to GHCR on every push to `main`.

```bash
docker run -d --name banger-link \
  --restart unless-stopped \
  -e TELEGRAM_TOKEN=<your-bot-token> \
  -v $(pwd)/data:/app/data \
  ghcr.io/luisg0nc/banger-link:latest
```

Or use the included compose file:

```bash
cp .env.example .env  # set TELEGRAM_TOKEN
docker compose up -d
```

State is one SQLite file under the bound `data/` directory.

### From source

Requires [`uv`](https://docs.astral.sh/uv/) and Python 3.12.

```bash
git clone https://github.com/luisg0nc/banger-link.git
cd banger-link
uv sync --extra dev
cp .env.example .env  # set TELEGRAM_TOKEN
uv run python -m banger_link
```

### Telegram bot setup

1. Create a bot with [@BotFather](https://t.me/BotFather) and copy the token into `TELEGRAM_TOKEN`.
2. Send `/setinline` to BotFather to enable `@yourbot` inline queries.
3. Add the bot to your group(s). For best UX, give it permission to read all messages (BotFather → `/setprivacy` → Disable). Otherwise it can only see commands and messages that mention it.
4. Optional: lock the bot to specific chats via `WHITELISTED_CHAT_IDS`.

## Configuration

All settings come from env vars (or `.env`). See [`.env.example`](.env.example) for the full list.

| Variable | Default | Meaning |
| --- | --- | --- |
| `TELEGRAM_TOKEN` | *(required)* | Token from BotFather. |
| `WHITELISTED_CHAT_IDS` | empty | Comma-separated chat IDs. Empty = answer everywhere. |
| `IGNORED_DOMAINS` | empty | Semicolon-separated domain substrings to skip. |
| `DATA_DIR` | `./data` | Where the SQLite DB lives. |
| `HEALTH_PORT` | `8080` | Port for the `/health` endpoint. |
| `LOG_LEVEL` | `INFO` | Standard Python log levels. |
| `DIGEST_TIMEZONE` | `UTC` | IANA name (e.g. `Europe/Lisbon`). |
| `DIGEST_HOUR` | `12` | Hour-of-day in `DIGEST_TIMEZONE` when digests are posted. |

## Architecture

```
Telegram update
  ├── MessageHandler → SonglinkClient → Repo (upsert song + record mention) → reply with reaction keyboard
  ├── CallbackQueryHandler (^r:)        → Repo.toggle_reaction → edit reply_markup
  ├── CommandHandlers                    → Repo.top_for_chat / search_chat
  └── InlineQueryHandler                 → Repo.search_global → InlineQueryResultArticle list

JobQueue
  ├── weekly-digest  (Mondays at DIGEST_HOUR) → leaderboard posted into each active chat
  └── monthly-digest (every day, no-ops unless day-of-month == 1)

aiohttp on :8080
  └── /health → SELECT 1 against the DB
```

Storage is a single SQLite database (WAL mode) with three tables:

- `songs` — global catalog, deduplicated by Songlink's `entityUniqueId`.
- `chat_songs` — one row per `(chat, song)` with first-sharer info and mention count.
- `reactions` — one row per `(chat_song, user)`. Likes/dislikes are computed at read time, no denormalized counters.

`callback_data` for the reaction buttons is `r:<chat_song_id>:<l|d>` — well under Telegram's 64-byte cap.

## Tech stack

- [python-telegram-bot](https://python-telegram-bot.org/) v22 (async)
- [Songlink/Odesli](https://song.link) for cross-platform link resolution
- SQLite via [aiosqlite](https://github.com/omnilib/aiosqlite) for state
- [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) for config
- [httpx](https://www.python-httpx.org/) for outbound HTTP
- [uv](https://docs.astral.sh/uv/) + [ruff](https://docs.astral.sh/ruff/) + [mypy](https://www.mypy-lang.org/) + [pytest](https://docs.pytest.org/) for the dev loop

## Development

```bash
uv run pytest                                # full suite with coverage
uv run pytest -k toggle --no-cov             # filter, no coverage report
uv run pytest tests/test_repo.py::test_toggle_reaction_full_cycle
uv run ruff check . && uv run ruff format .
uv run mypy banger_link
```

There's a [CLAUDE.md](CLAUDE.md) at the root that summarises the package layout, inbound flow, and storage invariants in a couple of pages — read that before making non-trivial changes.

## Contributing

Issues and PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow and quality bar. The repo follows [Conventional Commits](https://www.conventionalcommits.org/) and [Semantic Versioning](https://semver.org/).

## Acknowledgements

- [Songlink/Odesli](https://song.link) — the heavy lifting behind the cross-platform link resolution.
- [python-telegram-bot](https://python-telegram-bot.org/) — fantastic async Telegram bindings.

## License

MIT — see [LICENSE](LICENSE).
