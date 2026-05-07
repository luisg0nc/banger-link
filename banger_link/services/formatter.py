from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from html import escape

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from banger_link.db.repo import ChatSongView, MentionResult, ReactionState
from banger_link.services.songlink import PLATFORM_DISPLAY_ORDER, ResolvedSong

PLATFORM_LABELS: dict[str, tuple[str, str]] = {
    # platform -> (emoji, display name)
    "spotify": ("🟢", "Spotify"),
    "appleMusic": ("🍎", "Apple Music"),
    "youtube": ("▶️", "YouTube"),
    "youtubeMusic": ("🎶", "YouTube Music"),
    "tidal": ("🌊", "Tidal"),
    "deezer": ("🎧", "Deezer"),
    "amazonMusic": ("🛒", "Amazon Music"),
    "soundcloud": ("☁️", "SoundCloud"),
    "pandora": ("🅿️", "Pandora"),
    "anghami": ("🎙", "Anghami"),
    "audiomack": ("🎼", "Audiomack"),
    "boomplay": ("💥", "Boomplay"),
    "yandex": ("🇷🇺", "Yandex Music"),
    "napster": ("🔵", "Napster"),
}

# Platforms whose absence we explicitly call out under a share — Songlink has
# real catalog gaps for these (especially Spotify and YouTube on niche tracks),
# and silently dropping them looks like a bot bug to users.
EXPECTED_PLATFORMS: tuple[str, ...] = ("spotify", "appleMusic", "youtube")


def platform_lines(links: dict[str, str]) -> str:
    """Render a multi-line list of platform → hyperlinked label entries."""
    return _platform_lines_str(links)


def reaction_keyboard(*, chat_song_id: int, likes: int, dislikes: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(f"👍 {likes}", callback_data=f"r:{chat_song_id}:l"),
                InlineKeyboardButton(f"👎 {dislikes}", callback_data=f"r:{chat_song_id}:d"),
            ]
        ]
    )


def share_message(
    *,
    song: ResolvedSong,
    mention: MentionResult,
) -> str:
    header = f"🎵 <b>{escape(song.title)}</b> — <i>{escape(song.artist)}</i>"
    lines = [header, ""]
    lines.extend(_platform_lines(song.platform_links))

    if footer := _missing_platforms_footer(song.platform_links):
        lines.append("")
        lines.append(footer)

    if mention.is_first_time:
        lines.append("")
        lines.append("✨ First time in this chat! 🎉")
    else:
        lines.append("")
        lines.append(
            f"🔁 Shared <b>{mention.mentions}×</b> in this chat — "
            f"first by <i>{escape(mention.first_user_name)}</i> "
            f"on {_format_date(mention.first_seen_at)}."
        )
    return "\n".join(lines)


def leaderboard_message(*, title: str, rows: Iterable[ChatSongView]) -> str:
    lines = [f"<b>{escape(title)}</b>", ""]
    rows = list(rows)
    if not rows:
        lines.append("<i>No bangers yet — get reacting.</i>")
        return "\n".join(lines)
    medals = ("🥇", "🥈", "🥉")
    for idx, row in enumerate(rows, start=1):
        prefix = medals[idx - 1] if idx <= 3 else f"{idx}."
        score = row.likes - row.dislikes
        lines.append(
            f"{prefix} <b>{escape(row.title)}</b> — <i>{escape(row.artist)}</i> "
            f"(👍 {row.likes} · 👎 {row.dislikes}{' · score ' + _signed(score) if idx > 3 else ''})"
        )
    return "\n".join(lines)


def search_result_text(row: ChatSongView) -> str:
    return (
        f"🎵 <b>{escape(row.title)}</b> — <i>{escape(row.artist)}</i>\n"
        f"👍 {row.likes} · 👎 {row.dislikes} · 🔁 {row.mentions}\n"
        f"\n{_platform_lines_str(row.platform_links)}"
    )


def help_message() -> str:
    return (
        "🎧 <b>Banger Link</b> — your music companion.\n\n"
        "Drop a link from <b>Spotify</b>, <b>Apple Music</b>, <b>YouTube</b>, "
        "<b>Tidal</b>, <b>Deezer</b>, <b>SoundCloud</b> (and more) and I'll reply "
        "with links for every other major service so everyone in the chat can play it.\n\n"
        "<b>Commands</b>\n"
        "• /top [N] — top bangers in this chat (all-time)\n"
        "• /weekly [N] — top of the last 7 days\n"
        "• /monthly [N] — top of the last 30 days\n"
        "• /search &lt;query&gt; — search this chat's history\n"
        "• /help — show this message\n\n"
        "Tap 👍 or 👎 on any shared song to vote. You can change your vote any time."
    )


def reaction_toast(state: ReactionState, applied_kind: str) -> str:
    if state.user_reaction is None:
        return "Reaction removed"
    return f"You {applied_kind}d this song! {'👍' if applied_kind == 'like' else '👎'}"


# ---- helpers --------------------------------------------------------------


def _platform_lines(links: dict[str, str]) -> list[str]:
    return [_platform_lines_str(links)]


def _missing_platforms_footer(links: dict[str, str]) -> str | None:
    missing = [p for p in EXPECTED_PLATFORMS if p not in links]
    if not missing:
        return None
    names = ", ".join(PLATFORM_LABELS[p][1] for p in missing)
    return f"⚠️ Not on: <i>{escape(names)}</i>"


def _platform_lines_str(links: dict[str, str]) -> str:
    rendered: list[str] = []
    seen: set[str] = set()
    for platform in PLATFORM_DISPLAY_ORDER:
        if url := links.get(platform):
            seen.add(platform)
            rendered.append(_platform_line(platform, url))
    # Show unknown platforms last so we don't drop anything Songlink added.
    for platform, url in links.items():
        if platform in seen:
            continue
        rendered.append(_platform_line(platform, url))
    return "\n".join(rendered)


def _platform_line(platform: str, url: str) -> str:
    emoji, label = PLATFORM_LABELS.get(platform, ("🔗", platform.title()))
    return f'{emoji} <a href="{escape(url, quote=True)}">{escape(label)}</a>'


def _format_date(iso_timestamp: str) -> str:
    try:
        return datetime.fromisoformat(iso_timestamp.replace(" ", "T")).strftime("%b %d, %Y")
    except ValueError:
        return iso_timestamp


def _signed(n: int) -> str:
    return f"+{n}" if n > 0 else str(n)
