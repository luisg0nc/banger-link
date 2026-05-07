from __future__ import annotations

import logging
from importlib import resources
from pathlib import Path
from typing import Self

import aiosqlite

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def _load_schema() -> str:
    return resources.files("banger_link.db").joinpath("schema.sql").read_text(encoding="utf-8")


class Database:
    """Thin async wrapper around a single aiosqlite connection.

    The bot is a single-process app, so a single connection with WAL mode is
    enough — readers don't block the writer and SQLite's own locking covers
    cross-coroutine writes.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._conn

    async def connect(self) -> Self:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA journal_mode = WAL")
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.execute("PRAGMA synchronous = NORMAL")
        await self._apply_schema()
        return self

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def _apply_schema(self) -> None:
        assert self._conn is not None
        async with self._conn.execute("PRAGMA user_version") as cur:
            row = await cur.fetchone()
        current = int(row[0]) if row else 0
        if current >= SCHEMA_VERSION:
            return
        logger.info("Applying schema (current=%d, target=%d)", current, SCHEMA_VERSION)
        await self._conn.executescript(_load_schema())
        await self._conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        await self._conn.commit()

    async def healthcheck(self) -> bool:
        if self._conn is None:
            return False
        try:
            async with self._conn.execute("SELECT 1") as cur:
                await cur.fetchone()
        except Exception:
            return False
        return True
