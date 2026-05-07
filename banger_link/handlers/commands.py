from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from html import escape

from telegram import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
    Update,
)
from telegram.ext import Application, CommandHandler, ContextTypes

from banger_link.handlers._state import get_repo
from banger_link.services.formatter import help_message, leaderboard_message

logger = logging.getLogger(__name__)

DEFAULT_LIMIT = 10
MAX_LIMIT = 25


def _parse_limit(args: list[str] | None) -> int:
    if not args:
        return DEFAULT_LIMIT
    try:
        n = int(args[0])
    except ValueError:
        return DEFAULT_LIMIT
    return max(1, min(MAX_LIMIT, n))


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    await message.reply_html(help_message(), disable_web_page_preview=True)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def _send_leaderboard(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    title: str,
    since: datetime | None,
) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    repo = get_repo(context.bot_data)
    limit = _parse_limit(context.args)
    rows = await repo.top_for_chat(chat_id=chat.id, since=since, limit=limit)
    await message.reply_html(
        leaderboard_message(title=title, rows=rows),
        disable_web_page_preview=True,
    )


async def cmd_top(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_leaderboard(update, context, title="🏆 Top bangers (all time)", since=None)


async def cmd_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_leaderboard(
        update,
        context,
        title="📅 Top bangers — last 7 days",
        since=datetime.now(tz=UTC) - timedelta(days=7),
    )


async def cmd_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send_leaderboard(
        update,
        context,
        title="🗓 Top bangers — last 30 days",
        since=datetime.now(tz=UTC) - timedelta(days=30),
    )


async def cmd_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    chat = update.effective_chat
    if message is None or chat is None:
        return
    if not context.args:
        await message.reply_text("Usage: /search <song or artist>")
        return
    query = " ".join(context.args).strip()
    repo = get_repo(context.bot_data)
    rows = await repo.search_chat(chat_id=chat.id, query=query, limit=10)

    if not rows:
        await message.reply_html(
            f"<i>No bangers found in this chat for</i> <b>{escape(query)}</b>."
        )
        return

    lines = [f"🔎 <b>Results for</b> <i>{escape(query)}</i>:", ""]
    for row in rows:
        lines.append(
            f"• <b>{escape(row.title)}</b> — <i>{escape(row.artist)}</i> "
            f"(👍 {row.likes} · 👎 {row.dislikes} · 🔁 {row.mentions})"
        )
    await message.reply_html("\n".join(lines), disable_web_page_preview=True)


async def register_commands(application: Application) -> None:
    """Publish the slash-command menu to Telegram. Called from post_init."""
    commands = [
        BotCommand("top", "Top bangers in this chat (all-time)"),
        BotCommand("weekly", "Top of the last 7 days"),
        BotCommand("monthly", "Top of the last 30 days"),
        BotCommand("search", "Search this chat's history"),
        BotCommand("help", "How this bot works"),
    ]
    await application.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())
    await application.bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())
    logger.info("Bot commands registered with Telegram.")


HANDLERS = (
    CommandHandler("start", cmd_start),
    CommandHandler("help", cmd_help),
    CommandHandler("top", cmd_top),
    CommandHandler("weekly", cmd_weekly),
    CommandHandler("monthly", cmd_monthly),
    CommandHandler("search", cmd_search),
)
