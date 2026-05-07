from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import Application, ApplicationBuilder

from banger_link.config import settings
from banger_link.db.connection import Database
from banger_link.db.repo import Repo
from banger_link.handlers import _state
from banger_link.handlers.callbacks import callback_query_handler
from banger_link.handlers.commands import HANDLERS as COMMAND_HANDLERS
from banger_link.handlers.commands import register_commands
from banger_link.handlers.inline import inline_query_handler
from banger_link.handlers.messages import message_handler
from banger_link.health import HealthServer
from banger_link.jobs.digests import schedule_digests
from banger_link.services.fallback_resolver import (
    FallbackResolver,
    ITunesSearchClient,
    SpotifyAnonymousClient,
    YouTubeSearchClient,
)
from banger_link.services.songlink import SonglinkClient

logger = logging.getLogger(__name__)

LIFECYCLE_KEY_DB = "banger:_db"
LIFECYCLE_KEY_HEALTH = "banger:_health"


def _configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    )
    # httpx logs request URLs at INFO, which would leak the bot token into logs
    # (the token is in the path of every Telegram API call). Keep it at WARNING.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    for noisy in ("telegram.ext.Application", "telegram.Bot", "apscheduler"):
        logging.getLogger(noisy).setLevel(logging.INFO)


async def _on_startup(application: Application) -> None:
    db = await Database(settings.db_path).connect()
    repo = Repo(db)
    songlink = SonglinkClient()
    fallback = FallbackResolver(
        spotify=SpotifyAnonymousClient(),
        itunes=ITunesSearchClient(country=settings.fallback_user_country),
        youtube=YouTubeSearchClient(api_key=settings.youtube_api_key),
    )
    _state.install(application, repo=repo, songlink=songlink, fallback=fallback)

    health = HealthServer(db, port=settings.health_port)
    await health.start()

    application.bot_data[LIFECYCLE_KEY_DB] = db
    application.bot_data[LIFECYCLE_KEY_HEALTH] = health

    await register_commands(application)
    schedule_digests(application)
    logger.info("Banger Link is up and running.")


async def _on_shutdown(application: Application) -> None:
    songlink = application.bot_data.get(_state.SONGLINK_KEY)
    if songlink is not None:
        await songlink.aclose()

    fallback = application.bot_data.get(_state.FALLBACK_KEY)
    if fallback is not None:
        await fallback.aclose()

    health = application.bot_data.get(LIFECYCLE_KEY_HEALTH)
    if health is not None:
        await health.stop()

    db = application.bot_data.get(LIFECYCLE_KEY_DB)
    if db is not None:
        await db.close()


def build_application() -> Application:
    application = (
        ApplicationBuilder()
        .token(settings.telegram_token)
        .post_init(_on_startup)
        .post_shutdown(_on_shutdown)
        .build()
    )
    for handler in COMMAND_HANDLERS:
        application.add_handler(handler)
    application.add_handler(callback_query_handler)
    application.add_handler(inline_query_handler)
    application.add_handler(message_handler)
    return application


def main() -> None:
    _configure_logging()
    application = build_application()
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
