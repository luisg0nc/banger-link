# Contributing to Banger Link

Thanks for considering a contribution! This guide is short — most of the project's conventions live in the code itself.

## Code of Conduct

This project is governed by the [Code of Conduct](CODE_OF_CONDUCT.md).

## Reporting bugs / suggesting features

Open an issue on GitHub. For bugs, include the reproduction steps, the bot's log output (with secrets redacted), and the Telegram client/version if relevant.

## Development setup

Prerequisites:

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/)
- A Telegram bot token (get one from [@BotFather](https://t.me/BotFather))

Clone, install, and run:

```bash
git clone https://github.com/luisg0nc/banger-link.git
cd banger-link
uv sync --extra dev
cp .env.example .env       # edit TELEGRAM_TOKEN
uv run python -m banger_link
```

## Quality bar

Before opening a PR, run:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy banger_link
uv run pytest
```

CI runs the same commands. If you change the public Telegram-facing behavior (commands, callback patterns, reply formatting), update the README and add or adjust a test.

## Pull requests

- Branch off `main`, keep your branch focused on a single change.
- Use [Conventional Commits](https://www.conventionalcommits.org/) for the title (`feat:`, `fix:`, `refactor:`, etc.) — the existing history follows this style.
- Use [Semantic Versioning](https://semver.org/) when bumping `pyproject.toml`.
- Describe what changed and why; link any related issue.

## Architecture pointers

If you're new to the codebase, read [CLAUDE.md](CLAUDE.md) — it's a tight summary of the package layout, the inbound update flow, and the storage invariants. Then read `banger_link/__main__.py` to see how the application is wired up.

## License

By contributing, you agree that your contributions will be licensed under the MIT License (see [LICENSE](LICENSE)).
