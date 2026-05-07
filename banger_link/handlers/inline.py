from __future__ import annotations

import logging
from html import escape
from uuid import uuid4

from telegram import (
    InlineQueryResultArticle,
    InputTextMessageContent,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, InlineQueryHandler

from banger_link.handlers._state import get_repo
from banger_link.services.formatter import platform_lines

logger = logging.getLogger(__name__)

INLINE_RESULT_LIMIT = 20


async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.inline_query
    if query is None:
        return

    text = (query.query or "").strip()
    if len(text) < 2:
        await query.answer(
            results=[],
            cache_time=10,
            is_personal=True,
        )
        return

    repo = get_repo(context.bot_data)
    rows = await repo.search_global(query=text, limit=INLINE_RESULT_LIMIT)

    results: list[InlineQueryResultArticle] = []
    for row in rows:
        message_text = (
            f"🎵 <b>{escape(row.title)}</b> — <i>{escape(row.artist)}</i>\n\n"
            f"{platform_lines(row.platform_links)}"
        )
        results.append(
            InlineQueryResultArticle(
                id=str(uuid4()),
                title=row.title,
                description=f"{row.artist} · 👍 {row.likes} · 👎 {row.dislikes}",
                thumbnail_url=row.thumbnail_url,
                input_message_content=InputTextMessageContent(
                    message_text=message_text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True,
                ),
            )
        )

    await query.answer(
        results=results,
        cache_time=15,
        is_personal=True,
    )


inline_query_handler = InlineQueryHandler(handle_inline_query)
