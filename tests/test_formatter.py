from __future__ import annotations

from banger_link.db.repo import ChatSongView, MentionResult, ReactionState
from banger_link.services.formatter import (
    help_message,
    leaderboard_message,
    platform_lines,
    reaction_keyboard,
    reaction_toast,
    share_message,
)
from banger_link.services.songlink import ResolvedSong


def _resolved() -> ResolvedSong:
    return ResolvedSong(
        entity_id="x",
        title="Lust for Life",
        artist="Iggy <Pop>",
        thumbnail_url=None,
        page_url="https://song.link/s/x",
        platform_links={
            "spotify": "https://open.spotify.com/track/x",
            "appleMusic": "https://music.apple.com/track/x",
            "tidal": "https://tidal.com/track/x",
        },
    )


def _view(**kwargs: object) -> ChatSongView:
    base: dict[str, object] = {
        "chat_song_id": 1,
        "chat_id": -1,
        "title": "Lust for Life",
        "artist": "Iggy Pop",
        "thumbnail_url": None,
        "platform_links": {"spotify": "https://x"},
        "mentions": 1,
        "first_user_name": "Alice",
        "first_seen_at": "2025-01-01 12:00:00",
        "last_seen_at": "2025-01-02 12:00:00",
        "likes": 0,
        "dislikes": 0,
    }
    base.update(kwargs)
    return ChatSongView(**base)  # type: ignore[arg-type]


def test_share_message_first_time_shows_celebration() -> None:
    text = share_message(
        song=_resolved(),
        mention=MentionResult(
            chat_song_id=1,
            song_id=1,
            mentions=1,
            first_user_name="Alice",
            first_seen_at="2025-01-01 12:00:00",
            is_first_time=True,
        ),
    )
    assert "First time in this chat" in text
    assert "Lust for Life" in text
    # HTML escaping of artist name with angle brackets
    assert "Iggy &lt;Pop&gt;" in text


def test_share_message_repeat_shows_recap() -> None:
    text = share_message(
        song=_resolved(),
        mention=MentionResult(
            chat_song_id=1,
            song_id=1,
            mentions=4,
            first_user_name="Alice",
            first_seen_at="2025-01-01 12:00:00",
            is_first_time=False,
        ),
    )
    assert "4×" in text
    assert "first by <i>Alice</i>" in text


def test_share_message_renders_platform_links_in_order() -> None:
    text = share_message(
        song=_resolved(),
        mention=MentionResult(
            chat_song_id=1,
            song_id=1,
            mentions=1,
            first_user_name="A",
            first_seen_at="x",
            is_first_time=True,
        ),
    )
    spotify_pos = text.index("Spotify")
    apple_pos = text.index("Apple Music")
    tidal_pos = text.index("Tidal")
    assert spotify_pos < apple_pos < tidal_pos


def test_reaction_keyboard_callback_data_is_short() -> None:
    kb = reaction_keyboard(chat_song_id=1234567890, likes=12, dislikes=3)
    button_l, button_d = kb.inline_keyboard[0]
    assert button_l.callback_data == "r:1234567890:l"
    assert button_d.callback_data == "r:1234567890:d"
    assert len(button_l.callback_data.encode()) <= 64


def test_leaderboard_message_handles_empty() -> None:
    text = leaderboard_message(title="Top", rows=[])
    assert "No bangers yet" in text


def test_leaderboard_message_uses_medals() -> None:
    rows = [_view(title=f"S{i}", likes=10 - i) for i in range(5)]
    text = leaderboard_message(title="Top", rows=rows)
    assert "🥇" in text
    assert "🥈" in text
    assert "🥉" in text
    # Rank 4 falls back to "4."
    assert "4." in text


def test_reaction_toast_messages() -> None:
    state_added = ReactionState(likes=1, dislikes=0, user_reaction="like")
    state_removed = ReactionState(likes=0, dislikes=0, user_reaction=None)
    assert reaction_toast(state_added, "like") == "You liked this song! 👍"
    assert reaction_toast(state_removed, "like") == "Reaction removed"


def test_platform_lines_includes_unknown_platforms_last() -> None:
    text = platform_lines({"spotify": "https://s", "weirdplatform": "https://w"})
    assert text.index("Spotify") < text.index("Weirdplatform")


def test_help_message_lists_commands() -> None:
    text = help_message()
    for cmd in ("/top", "/weekly", "/monthly", "/search", "/help"):
        assert cmd in text
