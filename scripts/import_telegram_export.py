"""One-shot backfill: replay a Telegram chat HTML export into Banger Link's SQLite DB.

The Telegram Desktop "Export chat history (HTML)" feature dumps message bubbles
with timestamps, sender display names, and the link previews users posted. This
script walks those exports in chronological order, resolves each music URL
through Songlink, and writes `songs` + `chat_songs` rows with the *original*
timestamps so the bot's leaderboards reflect history.

Run locally against a copy of the bot's DB (see README at the bottom of this
file for the cluster swap dance). Idempotency is partial: re-running without
clearing the DB will increment `mentions` again, so do it once.

Notes on identity:
  * Telegram HTML exports do NOT include user IDs — only display names. We
    derive a stable synthetic user_id from the sender's name (FNV-1a hash);
    historical reactions can't be carried over (the export doesn't include
    them) so the `reactions` table stays untouched.
  * Joined-bubble continuations (same sender as previous message) inherit the
    last seen sender.

Usage:
  uv run --with beautifulsoup4 python scripts/import_telegram_export.py \\
      --db /tmp/banger.db \\
      --chat-id -1001985181835 \\
      --chat-title "BangersSociety" \\
      --files "/path/to/messages.html" "/path/to/messages2.html" "/path/to/messages3.html" \\
      --cache /tmp/songlink-cache.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup, Tag

# Make the project root importable so we can reuse the parsed-payload helpers
# from banger_link.services.songlink. Settings instantiates eagerly on import —
# feed it a stub token long enough to pass pydantic's min_length check, since
# this script doesn't talk to Telegram.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("TELEGRAM_TOKEN", "stub:token-for-importer")

from banger_link.handlers.messages import MUSIC_DOMAIN_SUFFIXES  # noqa: E402
from banger_link.services.songlink import ResolvedSong, _parse  # noqa: E402

logger = logging.getLogger("banger_link.import")

# Same shape Connection.connect() applies on bot startup; importing the schema
# directly keeps the script free of an aiosqlite dependency for the writes.
SCHEMA_PATH = ROOT / "banger_link" / "db" / "schema.sql"

DATE_FORMATS = (
    "%d.%m.%Y %H:%M:%S %z",
    "%d.%m.%Y %H:%M:%S",
)


@dataclass(slots=True)
class HistoricalShare:
    timestamp: datetime
    sender_name: str
    url: str
    msg_id: str  # for log/dedup, not stored


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


def _parse_timestamp(raw: str) -> datetime | None:
    # Telegram exports look like "23.11.2020 22:34:04 UTC+00:00".
    # strptime needs %z without the colon, so normalize.
    cleaned = re.sub(r"UTC([+\-]\d{2}):(\d{2})$", r"\1\2", raw.strip())
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def _is_music_url(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return bool(host) and any(host == d or host.endswith("." + d) for d in MUSIC_DOMAIN_SUFFIXES)


def parse_export(paths: list[Path]) -> list[HistoricalShare]:
    shares: list[HistoricalShare] = []
    for path in paths:
        logger.info("Reading %s", path)
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        last_sender: str | None = None
        for msg in soup.select("div.message.default"):
            assert isinstance(msg, Tag)
            from_name_el = msg.select_one("div.from_name")
            if from_name_el is not None:
                last_sender = from_name_el.get_text(strip=True)
            sender = last_sender or "Anonymous"

            date_el = msg.select_one("div.pull_right.date.details")
            ts: datetime | None = None
            if date_el is not None:
                title = date_el.get("title")
                if isinstance(title, str):
                    ts = _parse_timestamp(title)
            if ts is None:
                continue

            msg_id = str(msg.get("id", ""))
            text_el = msg.select_one("div.text")
            if text_el is None:
                continue
            for a in text_el.select("a[href]"):
                href = a.get("href")
                if not isinstance(href, str):
                    continue
                if not _is_music_url(href):
                    continue
                shares.append(
                    HistoricalShare(timestamp=ts, sender_name=sender, url=href, msg_id=msg_id)
                )
    shares.sort(key=lambda s: s.timestamp)
    logger.info("Parsed %d music shares from %d files", len(shares), len(paths))
    return shares


# ---------------------------------------------------------------------------
# Songlink resolution with disk cache
# ---------------------------------------------------------------------------


SONGLINK_URL = "https://api.song.link/v1-alpha.1/links"


class CachedResolver:
    """Resolves Songlink URLs with a disk cache and a 429-aware backoff.

    Talks to the Songlink API directly (instead of going through SonglinkClient)
    so the importer can react to status codes — long backoff on 429 (rate
    limit), no backoff on 404 (real "not on Songlink"), short backoff on other
    transient errors. Successful resolutions and definitive 404s are cached;
    transient failures are retried.
    """

    def __init__(
        self,
        cache_path: Path,
        client: httpx.AsyncClient,
        *,
        throttle_seconds: float,
        rate_limit_cool_down: float,
        cache_only: bool = False,
    ) -> None:
        self._path = cache_path
        self._client = client
        self._throttle = throttle_seconds
        self._rate_limit_cool_down = rate_limit_cool_down
        self._cache_only = cache_only
        self._last_call_at: float = 0.0
        self._consecutive_429s: int = 0
        self._cache: dict[str, dict | str] = {}
        if cache_path.exists():
            raw = json.loads(cache_path.read_text())
            # We allow two cache shapes: dict (resolved song) or "404" sentinel
            # (definitively not on Songlink — skip on resume).
            self._cache = {k: v for k, v in raw.items() if v is not None}
            logger.info("Loaded %d cached entries from %s", len(self._cache), cache_path)

    async def resolve(self, url: str) -> ResolvedSong | None:
        if url in self._cache:
            cached = self._cache[url]
            if cached == "404":
                return None
            assert isinstance(cached, dict)
            return ResolvedSong(
                entity_id=cached["entity_id"],
                title=cached["title"],
                artist=cached["artist"],
                thumbnail_url=cached.get("thumbnail_url"),
                page_url=cached.get("page_url", ""),
                platform_links=cached.get("platform_links", {}),
            )

        if self._cache_only:
            return None

        await self._wait_for_slot()

        try:
            response = await self._client.get(
                SONGLINK_URL,
                params={"url": url, "userCountry": "US"},
            )
        except httpx.HTTPError as exc:
            logger.warning("transport error for %s: %s — pausing %.0fs", url, exc, self._throttle)
            await asyncio.sleep(self._throttle)
            return None

        status = response.status_code
        if status == 200:
            self._consecutive_429s = 0
            try:
                payload = response.json()
            except ValueError:
                logger.warning("non-JSON 200 for %s", url)
                return None
            resolved = _parse(payload)
            if resolved is None:
                logger.info("Songlink returned a non-song payload for %s", url)
                self._cache[url] = "404"
                self._flush()
                return None
            self._cache[url] = {
                "entity_id": resolved.entity_id,
                "title": resolved.title,
                "artist": resolved.artist,
                "thumbnail_url": resolved.thumbnail_url,
                "page_url": resolved.page_url,
                "platform_links": resolved.platform_links,
            }
            self._flush()
            return resolved

        if status == 404:
            # Definitive — Songlink doesn't know this URL. Cache so we don't
            # keep retrying on resume.
            self._consecutive_429s = 0
            logger.info("404 for %s (cached as not-found)", url)
            self._cache[url] = "404"
            self._flush()
            return None

        if status == 429:
            self._consecutive_429s += 1
            # Exponential within reason — 60s, 120s, 240s, then capped at 5 min.
            backoff = min(
                self._rate_limit_cool_down * (2 ** (self._consecutive_429s - 1)),
                300.0,
            )
            logger.warning(
                "429 for %s (streak=%d) — sleeping %.0fs",
                url,
                self._consecutive_429s,
                backoff,
            )
            await asyncio.sleep(backoff)
            return None

        # 4xx (other) / 5xx — log and short-pause. Don't cache; retry on resume.
        logger.warning("HTTP %d for %s — pausing %.0fs", status, url, self._throttle)
        await asyncio.sleep(self._throttle)
        return None

    async def _wait_for_slot(self) -> None:
        loop = asyncio.get_event_loop()
        wait = self._throttle - (loop.time() - self._last_call_at)
        if wait > 0:
            await asyncio.sleep(wait)
        self._last_call_at = loop.time()

    def _flush(self) -> None:
        self._path.write_text(json.dumps(self._cache, indent=2, sort_keys=True))


# ---------------------------------------------------------------------------
# DB writes
# ---------------------------------------------------------------------------


def _fnv1a_64(name: str) -> int:
    """Stable 64-bit synthetic user id derived from a display name."""
    h = 0xCBF29CE484222325
    for byte in name.encode("utf-8"):
        h ^= byte
        h = (h * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
    # SQLite INTEGER is signed 64-bit; map into the negative half so we don't
    # collide with real Telegram user IDs (which are positive small ints).
    return -((h % (2**62)) + 1)


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.execute("PRAGMA user_version")
    if cur.fetchone()[0] >= 1:
        return
    conn.executescript(SCHEMA_PATH.read_text())
    conn.execute("PRAGMA user_version = 1")
    conn.commit()


def upsert_song(
    conn: sqlite3.Connection,
    *,
    resolved: ResolvedSong,
    when: datetime,
) -> int:
    iso = when.strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """
        INSERT INTO songs (entity_id, title, artist, thumbnail_url, platform_links, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(entity_id) DO UPDATE SET
            title          = excluded.title,
            artist         = excluded.artist,
            thumbnail_url  = excluded.thumbnail_url,
            platform_links = excluded.platform_links
        """,
        (
            resolved.entity_id,
            resolved.title,
            resolved.artist,
            resolved.thumbnail_url,
            json.dumps(resolved.platform_links),
            iso,
        ),
    )
    row = conn.execute("SELECT id FROM songs WHERE entity_id = ?", (resolved.entity_id,)).fetchone()
    assert row is not None
    return int(row[0])


def record_mention(
    conn: sqlite3.Connection,
    *,
    chat_id: int,
    song_id: int,
    user_id: int,
    user_name: str,
    when: datetime,
) -> tuple[int, bool]:
    """Returns (chat_song_id, is_first_time)."""
    iso = when.strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """
        INSERT INTO chat_songs (chat_id, song_id, first_user_id, first_user_name, mentions, first_seen_at, last_seen_at)
        VALUES (?, ?, ?, ?, 1, ?, ?)
        ON CONFLICT(chat_id, song_id) DO UPDATE SET
            mentions     = chat_songs.mentions + 1,
            last_seen_at = CASE
                WHEN excluded.last_seen_at > chat_songs.last_seen_at THEN excluded.last_seen_at
                ELSE chat_songs.last_seen_at
            END
        RETURNING id, mentions
        """,
        (chat_id, song_id, user_id, user_name, iso, iso),
    )
    row = cur.fetchone()
    assert row is not None
    return int(row[0]), int(row[1]) == 1


def touch_chat(conn: sqlite3.Connection, *, chat_id: int, title: str | None) -> None:
    conn.execute(
        """
        INSERT INTO chats (chat_id, title)
        VALUES (?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            title          = COALESCE(excluded.title, chats.title),
            last_active_at = datetime('now')
        """,
        (chat_id, title),
    )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


async def run(
    *,
    files: list[Path],
    db_path: Path,
    chat_id: int,
    chat_title: str | None,
    cache_path: Path,
    throttle: float,
    cool_down: float,
    cache_only: bool,
    dry_run: bool,
) -> None:
    shares = parse_export(files)
    if not shares:
        logger.warning("No music shares found in any input file. Nothing to do.")
        return

    unique_urls = {s.url for s in shares}
    logger.info("Unique URLs: %d (across %d shares)", len(unique_urls), len(shares))

    client = httpx.AsyncClient(
        timeout=httpx.Timeout(15.0),
        headers={"User-Agent": "banger-link-importer/2.0"},
    )
    resolver = CachedResolver(
        cache_path,
        client,
        throttle_seconds=throttle,
        rate_limit_cool_down=cool_down,
        cache_only=cache_only,
    )

    try:
        # Resolve all unique URLs up front so DB writes happen in one fast loop.
        resolved_by_url: dict[str, ResolvedSong | None] = {}
        for i, url in enumerate(sorted(unique_urls), start=1):
            resolved = await resolver.resolve(url)
            if resolved is None:
                logger.warning("[%d/%d] could not resolve %s", i, len(unique_urls), url)
            else:
                logger.info("[%d/%d] %s — %s", i, len(unique_urls), resolved.title, resolved.artist)
            resolved_by_url[url] = resolved
    finally:
        await client.aclose()

    if dry_run:
        skipped = sum(1 for v in resolved_by_url.values() if v is None)
        logger.info(
            "DRY RUN: would replay %d shares (%d unique URLs, %d unresolved). Exiting without writes.",
            len(shares),
            len(unique_urls),
            skipped,
        )
        return

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    ensure_schema(conn)

    inserted_songs: set[int] = set()
    new_chat_songs = 0
    repeat_mentions = 0
    skipped = 0

    try:
        touch_chat(conn, chat_id=chat_id, title=chat_title)
        for share in shares:
            resolved = resolved_by_url.get(share.url)
            if resolved is None:
                skipped += 1
                continue
            song_id = upsert_song(conn, resolved=resolved, when=share.timestamp)
            inserted_songs.add(song_id)
            user_id = _fnv1a_64(share.sender_name)
            _, first_time = record_mention(
                conn,
                chat_id=chat_id,
                song_id=song_id,
                user_id=user_id,
                user_name=share.sender_name,
                when=share.timestamp,
            )
            if first_time:
                new_chat_songs += 1
            else:
                repeat_mentions += 1
        conn.commit()
    finally:
        conn.close()

    logger.info(
        "Done. shares=%d  unique_songs=%d  new_chat_songs=%d  repeat_mentions=%d  unresolved=%d",
        len(shares),
        len(inserted_songs),
        new_chat_songs,
        repeat_mentions,
        skipped,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--files", nargs="+", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--chat-id", type=int, required=True)
    parser.add_argument("--chat-title", type=str, default=None)
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path("/tmp/songlink-cache.json"),
        help="Disk cache for Songlink resolutions (resume-safe).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve URLs and print stats without writing the DB.",
    )
    parser.add_argument(
        "--throttle",
        type=float,
        default=8.0,
        help="Min seconds between successful Songlink API calls.",
    )
    parser.add_argument(
        "--cool-down",
        type=float,
        default=60.0,
        help="Base seconds to sleep after a 429 (doubles on consecutive 429s, capped at 300).",
    )
    parser.add_argument(
        "--cache-only",
        action="store_true",
        help="Only use already-cached resolutions; never call Songlink. Cache misses count as unresolved.",
    )
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    asyncio.run(
        run(
            files=args.files,
            db_path=args.db,
            chat_id=args.chat_id,
            chat_title=args.chat_title,
            cache_path=args.cache,
            throttle=args.throttle,
            cool_down=args.cool_down,
            cache_only=args.cache_only,
            dry_run=args.dry_run,
        )
    )


if __name__ == "__main__":
    main()
