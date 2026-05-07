from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from banger_link.db.connection import Database
from banger_link.db.repo import Repo


@pytest.fixture
async def repo(tmp_path: Path):
    db = await Database(tmp_path / "test.db").connect()
    try:
        yield Repo(db)
    finally:
        await db.close()


async def _seed_song(repo: Repo, *, entity_id: str = "SPOTIFY_SONG::abc") -> int:
    return await repo.upsert_song(
        entity_id=entity_id,
        title="Lust for Life",
        artist="Iggy Pop",
        thumbnail_url="https://thumb",
        platform_links={
            "spotify": "https://open.spotify.com/track/abc",
            "youtube": "https://youtu.be/abc",
        },
    )


async def test_record_mention_marks_first_time_then_increments(repo: Repo) -> None:
    song_id = await _seed_song(repo)
    first = await repo.record_mention(chat_id=-100, song_id=song_id, user_id=1, user_name="Alice")
    assert first.is_first_time
    assert first.mentions == 1

    second = await repo.record_mention(chat_id=-100, song_id=song_id, user_id=2, user_name="Bob")
    assert not second.is_first_time
    assert second.mentions == 2
    assert second.first_user_name == "Alice"  # original sharer is preserved
    assert second.chat_song_id == first.chat_song_id


async def test_toggle_reaction_full_cycle(repo: Repo) -> None:
    song_id = await _seed_song(repo)
    mention = await repo.record_mention(chat_id=-100, song_id=song_id, user_id=1, user_name="Alice")

    s1 = await repo.toggle_reaction(chat_song_id=mention.chat_song_id, user_id=99, kind="like")
    assert s1.likes == 1 and s1.dislikes == 0 and s1.user_reaction == "like"

    s2 = await repo.toggle_reaction(chat_song_id=mention.chat_song_id, user_id=99, kind="like")
    assert s2.likes == 0 and s2.user_reaction is None

    await repo.toggle_reaction(chat_song_id=mention.chat_song_id, user_id=99, kind="like")
    s3 = await repo.toggle_reaction(chat_song_id=mention.chat_song_id, user_id=99, kind="dislike")
    assert s3.likes == 0 and s3.dislikes == 1 and s3.user_reaction == "dislike"


async def test_top_for_chat_orders_by_score(repo: Repo) -> None:
    song_a = await repo.upsert_song(
        entity_id="A", title="A", artist="X", thumbnail_url=None, platform_links={"spotify": "a"}
    )
    song_b = await repo.upsert_song(
        entity_id="B", title="B", artist="Y", thumbnail_url=None, platform_links={"spotify": "b"}
    )
    cs_a = await repo.record_mention(chat_id=-1, song_id=song_a, user_id=1, user_name="Alice")
    cs_b = await repo.record_mention(chat_id=-1, song_id=song_b, user_id=1, user_name="Alice")

    # A: +2 likes, B: +1 like, -1 dislike → A is on top.
    await repo.toggle_reaction(chat_song_id=cs_a.chat_song_id, user_id=10, kind="like")
    await repo.toggle_reaction(chat_song_id=cs_a.chat_song_id, user_id=11, kind="like")
    await repo.toggle_reaction(chat_song_id=cs_b.chat_song_id, user_id=10, kind="like")
    await repo.toggle_reaction(chat_song_id=cs_b.chat_song_id, user_id=11, kind="dislike")

    top = await repo.top_for_chat(chat_id=-1, limit=10)
    assert [r.title for r in top] == ["A", "B"]


async def test_top_for_chat_skips_unreacted_songs(repo: Repo) -> None:
    song_id = await _seed_song(repo)
    await repo.record_mention(chat_id=-1, song_id=song_id, user_id=1, user_name="Alice")
    # No reactions on this song.
    rows = await repo.top_for_chat(chat_id=-1, limit=10)
    assert rows == []


async def test_top_for_chat_respects_since(repo: Repo) -> None:
    song_id = await _seed_song(repo)
    cs = await repo.record_mention(chat_id=-1, song_id=song_id, user_id=1, user_name="Alice")
    await repo.toggle_reaction(chat_song_id=cs.chat_song_id, user_id=10, kind="like")

    future = datetime.now(tz=UTC) + timedelta(days=1)
    assert await repo.top_for_chat(chat_id=-1, since=future, limit=10) == []
    past = datetime.now(tz=UTC) - timedelta(days=1)
    assert len(await repo.top_for_chat(chat_id=-1, since=past, limit=10)) == 1


async def test_search_chat_matches_title_and_artist(repo: Repo) -> None:
    song_id = await _seed_song(repo)
    await repo.record_mention(chat_id=-1, song_id=song_id, user_id=1, user_name="Alice")

    by_title = await repo.search_chat(chat_id=-1, query="lust")
    by_artist = await repo.search_chat(chat_id=-1, query="iggy")
    none = await repo.search_chat(chat_id=-1, query="zzz")

    assert len(by_title) == 1 and by_title[0].title == "Lust for Life"
    assert len(by_artist) == 1
    assert none == []


async def test_upsert_song_dedupes_on_entity_id(repo: Repo) -> None:
    a = await _seed_song(repo, entity_id="SAME")
    b = await repo.upsert_song(
        entity_id="SAME",
        title="Updated Title",
        artist="Updated Artist",
        thumbnail_url=None,
        platform_links={"spotify": "https://x"},
    )
    assert a == b


async def test_chats_with_digest_returns_active_chats(repo: Repo) -> None:
    await repo.touch_chat(chat_id=-1, title="Chat A")
    await repo.touch_chat(chat_id=-2, title="Chat B")

    weekly = await repo.chats_with_digest(kind="weekly")
    assert set(weekly) == {-1, -2}
