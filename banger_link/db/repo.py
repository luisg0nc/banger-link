from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from banger_link.db.connection import Database

ReactionKind = Literal["like", "dislike"]


@dataclass(frozen=True, slots=True)
class MentionResult:
    chat_song_id: int
    song_id: int
    mentions: int
    first_user_name: str
    first_seen_at: str
    is_first_time: bool


@dataclass(frozen=True, slots=True)
class ChatSongView:
    """Read-side projection of a chat-song row joined with the song and reaction counts."""

    chat_song_id: int
    chat_id: int
    title: str
    artist: str
    thumbnail_url: str | None
    platform_links: dict[str, str]
    mentions: int
    first_user_name: str
    first_seen_at: str
    last_seen_at: str
    likes: int
    dislikes: int


@dataclass(frozen=True, slots=True)
class ReactionState:
    likes: int
    dislikes: int
    user_reaction: ReactionKind | None


_VIEW_SELECT = """
SELECT
    cs.id              AS chat_song_id,
    cs.chat_id         AS chat_id,
    s.title            AS title,
    s.artist           AS artist,
    s.thumbnail_url    AS thumbnail_url,
    s.platform_links   AS platform_links,
    cs.mentions        AS mentions,
    cs.first_user_name AS first_user_name,
    cs.first_seen_at   AS first_seen_at,
    cs.last_seen_at    AS last_seen_at,
    COALESCE(SUM(CASE WHEN r.kind = 'like'    THEN 1 ELSE 0 END), 0) AS likes,
    COALESCE(SUM(CASE WHEN r.kind = 'dislike' THEN 1 ELSE 0 END), 0) AS dislikes
FROM chat_songs cs
JOIN songs s ON s.id = cs.song_id
LEFT JOIN reactions r ON r.chat_song_id = cs.id
"""


def _as_int(value: Any) -> int:
    return int(value)


def _row_to_view(row: dict[str, Any]) -> ChatSongView:
    raw_links = row["platform_links"]
    assert isinstance(raw_links, str)
    thumbnail = row["thumbnail_url"]
    return ChatSongView(
        chat_song_id=_as_int(row["chat_song_id"]),
        chat_id=_as_int(row["chat_id"]),
        title=str(row["title"]),
        artist=str(row["artist"]),
        thumbnail_url=None if thumbnail is None else str(thumbnail),
        platform_links=json.loads(raw_links),
        mentions=_as_int(row["mentions"]),
        first_user_name=str(row["first_user_name"]),
        first_seen_at=str(row["first_seen_at"]),
        last_seen_at=str(row["last_seen_at"]),
        likes=_as_int(row["likes"]),
        dislikes=_as_int(row["dislikes"]),
    )


class Repo:
    def __init__(self, db: Database) -> None:
        self._db = db

    @property
    def _conn(self):  # type: ignore[no-untyped-def]
        return self._db.conn

    # ---- writes ---------------------------------------------------------

    async def upsert_song(
        self,
        *,
        entity_id: str,
        title: str,
        artist: str,
        thumbnail_url: str | None,
        platform_links: dict[str, str],
    ) -> int:
        await self._conn.execute(
            """
            INSERT INTO songs (entity_id, title, artist, thumbnail_url, platform_links)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(entity_id) DO UPDATE SET
                title          = excluded.title,
                artist         = excluded.artist,
                thumbnail_url  = excluded.thumbnail_url,
                platform_links = excluded.platform_links
            """,
            (entity_id, title, artist, thumbnail_url, json.dumps(platform_links)),
        )
        async with self._conn.execute(
            "SELECT id FROM songs WHERE entity_id = ?", (entity_id,)
        ) as cur:
            row = await cur.fetchone()
        await self._conn.commit()
        assert row is not None
        return int(row["id"])

    async def record_mention(
        self,
        *,
        chat_id: int,
        song_id: int,
        user_id: int,
        user_name: str,
    ) -> MentionResult:
        async with self._conn.execute(
            """
            INSERT INTO chat_songs (chat_id, song_id, first_user_id, first_user_name)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(chat_id, song_id) DO UPDATE SET
                mentions     = chat_songs.mentions + 1,
                last_seen_at = datetime('now')
            RETURNING id, mentions, first_user_name, first_seen_at
            """,
            (chat_id, song_id, user_id, user_name),
        ) as cur:
            row = await cur.fetchone()
        await self._conn.commit()
        assert row is not None
        return MentionResult(
            chat_song_id=int(row["id"]),
            song_id=song_id,
            mentions=int(row["mentions"]),
            first_user_name=str(row["first_user_name"]),
            first_seen_at=str(row["first_seen_at"]),
            is_first_time=int(row["mentions"]) == 1,
        )

    async def touch_chat(self, *, chat_id: int, title: str | None) -> None:
        await self._conn.execute(
            """
            INSERT INTO chats (chat_id, title)
            VALUES (?, ?)
            ON CONFLICT(chat_id) DO UPDATE SET
                title          = COALESCE(excluded.title, chats.title),
                last_active_at = datetime('now')
            """,
            (chat_id, title),
        )
        await self._conn.commit()

    async def toggle_reaction(
        self,
        *,
        chat_song_id: int,
        user_id: int,
        kind: ReactionKind,
    ) -> ReactionState:
        async with self._conn.execute(
            "SELECT kind FROM reactions WHERE chat_song_id = ? AND user_id = ?",
            (chat_song_id, user_id),
        ) as cur:
            existing_row = await cur.fetchone()
        existing: ReactionKind | None = existing_row["kind"] if existing_row is not None else None

        if existing == kind:
            await self._conn.execute(
                "DELETE FROM reactions WHERE chat_song_id = ? AND user_id = ?",
                (chat_song_id, user_id),
            )
            new_user_reaction: ReactionKind | None = None
        elif existing is not None:
            await self._conn.execute(
                "UPDATE reactions SET kind = ?, reacted_at = datetime('now') "
                "WHERE chat_song_id = ? AND user_id = ?",
                (kind, chat_song_id, user_id),
            )
            new_user_reaction = kind
        else:
            await self._conn.execute(
                "INSERT INTO reactions (chat_song_id, user_id, kind) VALUES (?, ?, ?)",
                (chat_song_id, user_id, kind),
            )
            new_user_reaction = kind

        async with self._conn.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN kind = 'like'    THEN 1 ELSE 0 END), 0) AS likes,
                COALESCE(SUM(CASE WHEN kind = 'dislike' THEN 1 ELSE 0 END), 0) AS dislikes
            FROM reactions WHERE chat_song_id = ?
            """,
            (chat_song_id,),
        ) as cur:
            counts = await cur.fetchone()
        await self._conn.commit()
        assert counts is not None
        return ReactionState(
            likes=int(counts["likes"]),
            dislikes=int(counts["dislikes"]),
            user_reaction=new_user_reaction,
        )

    # ---- reads ----------------------------------------------------------

    async def get_chat_song(self, chat_song_id: int) -> ChatSongView | None:
        async with self._conn.execute(
            f"{_VIEW_SELECT} WHERE cs.id = ? GROUP BY cs.id",
            (chat_song_id,),
        ) as cur:
            row = await cur.fetchone()
        return _row_to_view(dict(row)) if row else None

    async def get_user_reaction(self, *, chat_song_id: int, user_id: int) -> ReactionKind | None:
        async with self._conn.execute(
            "SELECT kind FROM reactions WHERE chat_song_id = ? AND user_id = ?",
            (chat_song_id, user_id),
        ) as cur:
            row = await cur.fetchone()
        return row["kind"] if row else None

    async def top_for_chat(
        self,
        *,
        chat_id: int,
        since: datetime | None = None,
        limit: int = 10,
    ) -> list[ChatSongView]:
        params: list[object] = [chat_id]
        clause = ""
        if since is not None:
            clause = "AND cs.last_seen_at >= ?"
            params.append(since.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S"))
        params.append(limit)
        sql = f"""
            {_VIEW_SELECT}
            WHERE cs.chat_id = ? {clause}
            GROUP BY cs.id
            HAVING (likes + dislikes) > 0
            ORDER BY (likes - dislikes) DESC, cs.mentions DESC, cs.last_seen_at DESC
            LIMIT ?
        """
        async with self._conn.execute(sql, params) as cur:
            rows = await cur.fetchall()
        return [_row_to_view(dict(r)) for r in rows]

    async def search_chat(self, *, chat_id: int, query: str, limit: int = 20) -> list[ChatSongView]:
        like = f"%{query.strip()}%"
        sql = f"""
            {_VIEW_SELECT}
            WHERE cs.chat_id = ?
              AND (s.title LIKE ? OR s.artist LIKE ?)
            GROUP BY cs.id
            ORDER BY cs.last_seen_at DESC
            LIMIT ?
        """
        async with self._conn.execute(sql, (chat_id, like, like, limit)) as cur:
            rows = await cur.fetchall()
        return [_row_to_view(dict(r)) for r in rows]

    async def search_global(self, *, query: str, limit: int = 20) -> list[ChatSongView]:
        """Search across the global songs table (used by inline mode where the
        chat where the user is typing is unknown)."""
        like = f"%{query.strip()}%"
        sql = f"""
            {_VIEW_SELECT}
            WHERE (s.title LIKE ? OR s.artist LIKE ?)
            GROUP BY cs.id
            ORDER BY cs.last_seen_at DESC
            LIMIT ?
        """
        async with self._conn.execute(sql, (like, like, limit)) as cur:
            rows = await cur.fetchall()
        return [_row_to_view(dict(r)) for r in rows]

    # ---- digest helpers ------------------------------------------------

    async def chats_with_digest(self, *, kind: Literal["weekly", "monthly"]) -> list[int]:
        col = f"digest_{kind}"
        # Only chats that have had activity recently — avoids posting to dead chats.
        cutoff = datetime.now(tz=UTC) - timedelta(days=60)
        async with self._conn.execute(
            f"SELECT chat_id FROM chats WHERE {col} = 1 AND last_active_at >= ?",
            (cutoff.strftime("%Y-%m-%d %H:%M:%S"),),
        ) as cur:
            rows = await cur.fetchall()
        return [int(r["chat_id"]) for r in rows]
