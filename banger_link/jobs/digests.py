from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Literal

from telegram.constants import ParseMode
from telegram.error import Forbidden, TelegramError
from telegram.ext import Application, ContextTypes

from banger_link.config import settings
from banger_link.handlers._state import get_repo
from banger_link.services.formatter import leaderboard_message

logger = logging.getLogger(__name__)

DIGEST_LIMIT = 5


async def _post_digest(
    context: ContextTypes.DEFAULT_TYPE,
    *,
    kind: Literal["weekly", "monthly"],
    days_back: int,
    title_template: str,
) -> None:
    repo = get_repo(context.bot_data)
    chat_ids = await repo.chats_with_digest(kind=kind)
    if not chat_ids:
        logger.info("No chats opted into the %s digest.", kind)
        return

    since = datetime.now(tz=UTC) - timedelta(days=days_back)
    posted = 0
    for chat_id in chat_ids:
        rows = await repo.top_for_chat(chat_id=chat_id, since=since, limit=DIGEST_LIMIT)
        if not rows:
            continue
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=leaderboard_message(title=title_template, rows=rows),
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            posted += 1
        except Forbidden:
            logger.info("Bot was kicked from chat %s; skipping digest.", chat_id)
        except TelegramError as exc:
            logger.warning("Failed to post %s digest in %s: %s", kind, chat_id, exc)
    logger.info("Posted %s digests to %d chat(s).", kind, posted)


async def post_weekly_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    await _post_digest(
        context,
        kind="weekly",
        days_back=7,
        title_template="📅 Weekly bangers — last 7 days",
    )


async def post_monthly_digest(context: ContextTypes.DEFAULT_TYPE) -> None:
    # run_daily gives no monthly knob — gate on day-of-month inside the callback.
    if datetime.now(tz=UTC).day != 1:
        return
    await _post_digest(
        context,
        kind="monthly",
        days_back=30,
        title_template="🗓 Monthly bangers — last 30 days",
    )


def schedule_digests(application: Application) -> None:
    job_queue = application.job_queue
    if job_queue is None:
        logger.warning(
            "JobQueue is not available — install the [job-queue] extra to enable digests."
        )
        return
    # Weekly: every Monday at the configured local hour.
    job_queue.run_daily(
        post_weekly_digest,
        time=settings.digest_post_time,
        days=(0,),
        name="weekly-digest",
    )
    # Monthly: every day, but the callback no-ops unless it's the 1st.
    job_queue.run_daily(
        post_monthly_digest,
        time=settings.digest_post_time,
        name="monthly-digest",
    )
    logger.info(
        "Digest jobs scheduled at %s (%s).",
        settings.digest_post_time,
        settings.digest_timezone,
    )
