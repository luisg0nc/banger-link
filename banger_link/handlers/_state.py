from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from telegram.ext import Application

    from banger_link.db.repo import Repo
    from banger_link.services.songlink import SonglinkClient


REPO_KEY = "banger:repo"
SONGLINK_KEY = "banger:songlink"


def install(
    application: "Application",  # noqa: UP037
    *,
    repo: Repo,
    songlink: SonglinkClient,
) -> None:
    application.bot_data[REPO_KEY] = repo
    application.bot_data[SONGLINK_KEY] = songlink


def get_repo(bot_data: dict[str, object]) -> Repo:
    repo = bot_data.get(REPO_KEY)
    if repo is None:
        raise RuntimeError("Repo not installed in bot_data")
    return repo  # type: ignore[return-value]


def get_songlink(bot_data: dict[str, object]) -> SonglinkClient:
    client = bot_data.get(SONGLINK_KEY)
    if client is None:
        raise RuntimeError("SonglinkClient not installed in bot_data")
    return client  # type: ignore[return-value]
