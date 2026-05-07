from __future__ import annotations

import logging
import re
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from banger_link.config import settings
from banger_link.handlers._state import get_repo, get_songlink
from banger_link.services.formatter import reaction_keyboard, share_message

logger = logging.getLogger(__name__)

URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)

# Domains we'll send to Songlink. We keep this list narrow so we don't waste
# requests (and risk rate-limiting) on unrelated links.
MUSIC_DOMAIN_SUFFIXES: tuple[str, ...] = (
    "spotify.com",
    "music.apple.com",
    "youtube.com",
    "youtu.be",
    "music.youtube.com",
    "tidal.com",
    "deezer.com",
    "soundcloud.com",
    "music.amazon.com",
    "music.amazon.co.uk",
    "music.amazon.de",
    "pandora.com",
    "anghami.com",
    "audiomack.com",
    "boomplay.com",
    "music.yandex.com",
    "music.yandex.ru",
    "napster.com",
    "song.link",
)


def _extract_url(text: str) -> str | None:
    match = URL_RE.search(text)
    return match.group(0).rstrip(").,;:!?]\"'") if match else None


def _is_music_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in MUSIC_DOMAIN_SUFFIXES)


def _is_ignored(url: str) -> bool:
    return any(d in url for d in settings.ignored_domains)


def _user_display_name(user_first: str | None, user_last: str | None) -> str:
    parts = [p for p in (user_first, user_last) if p]
    return " ".join(parts) or "Anonymous"


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        return

    if settings.whitelisted_chat_ids and chat.id not in settings.whitelisted_chat_ids:
        logger.info(
            "Dropping message from non-whitelisted chat_id=%s (user=%s)",
            chat.id,
            user.id,
        )
        return

    url = _extract_url(message.text)
    if not url:
        return
    if _is_ignored(url):
        logger.info("Dropping URL on ignored-domain list: %s", url)
        return
    if not _is_music_url(url):
        return

    songlink = get_songlink(context.bot_data)
    repo = get_repo(context.bot_data)

    resolved = await songlink.resolve(url)
    if resolved is None:
        logger.info("Could not resolve %s — staying silent", url)
        return

    song_id = await repo.upsert_song(
        entity_id=resolved.entity_id,
        title=resolved.title,
        artist=resolved.artist,
        thumbnail_url=resolved.thumbnail_url,
        platform_links=resolved.platform_links,
    )
    mention = await repo.record_mention(
        chat_id=chat.id,
        song_id=song_id,
        user_id=user.id,
        user_name=_user_display_name(user.first_name, user.last_name),
    )
    await repo.touch_chat(chat_id=chat.id, title=chat.title)

    text = share_message(song=resolved, mention=mention)
    keyboard = reaction_keyboard(chat_song_id=mention.chat_song_id, likes=0, dislikes=0)
    await message.reply_html(
        text,
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


message_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
