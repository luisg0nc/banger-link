from __future__ import annotations

import logging

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, ContextTypes

from banger_link.handlers._state import get_repo
from banger_link.services.formatter import reaction_keyboard, reaction_toast

logger = logging.getLogger(__name__)

KIND_FROM_LETTER = {"l": "like", "d": "dislike"}


async def handle_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return

    parts = query.data.split(":")
    if len(parts) != 3 or parts[0] != "r":
        await query.answer("Unknown action.")
        return

    try:
        chat_song_id = int(parts[1])
    except ValueError:
        await query.answer("Invalid action.")
        return

    kind = KIND_FROM_LETTER.get(parts[2])
    if kind is None:
        await query.answer("Invalid reaction.")
        return

    user = query.from_user
    if user is None:
        await query.answer()
        return

    repo = get_repo(context.bot_data)
    state = await repo.toggle_reaction(
        chat_song_id=chat_song_id,
        user_id=user.id,
        kind=kind,  # type: ignore[arg-type]
    )

    keyboard = reaction_keyboard(
        chat_song_id=chat_song_id, likes=state.likes, dislikes=state.dislikes
    )
    try:
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except BadRequest as exc:
        # Telegram returns "Message is not modified" if the keyboard happens to
        # match — harmless, just log and continue.
        if "not modified" not in str(exc).lower():
            logger.warning("Could not edit reply markup: %s", exc)

    await query.answer(reaction_toast(state, kind))


callback_query_handler = CallbackQueryHandler(handle_reaction, pattern=r"^r:")
