from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

import httpx

from banger_link.config import settings

logger = logging.getLogger(__name__)

# Platforms we display, in the order we want them rendered.
PLATFORM_DISPLAY_ORDER: tuple[str, ...] = (
    "spotify",
    "appleMusic",
    "youtube",
    "youtubeMusic",
    "tidal",
    "deezer",
    "amazonMusic",
    "soundcloud",
    "pandora",
    "anghami",
    "audiomack",
    "boomplay",
    "yandex",
    "napster",
)


@dataclass(frozen=True, slots=True)
class ResolvedSong:
    """Normalized output of Songlink/Odesli for a single song URL."""

    entity_id: str
    title: str
    artist: str
    thumbnail_url: str | None
    page_url: str  # song.link landing page, useful as a fallback share link
    platform_links: dict[str, str] = field(default_factory=dict)

    def primary_link(self) -> str:
        """First available platform link in our display order, falling back to song.link."""
        for platform in PLATFORM_DISPLAY_ORDER:
            if url := self.platform_links.get(platform):
                return url
        return self.page_url


class SonglinkError(Exception):
    """Raised on unrecoverable Songlink errors (after retries)."""


class SonglinkClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        client: httpx.AsyncClient | None = None,
        user_country: str = "US",
        timeout_seconds: float = 8.0,
        max_retries: int = 2,
    ) -> None:
        self._base_url = base_url or str(settings.songlink_api_url)
        self._user_country = user_country
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            headers={"User-Agent": "banger-link/2.0 (+https://github.com/luisg0nc/banger-link)"},
        )
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def resolve(self, url: str) -> ResolvedSong | None:
        """Resolve a single share URL into a ResolvedSong, or None if not a known song."""
        params = {"url": url, "userCountry": self._user_country}

        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.get(self._base_url, params=params)
            except httpx.TimeoutException:
                if attempt == self._max_retries:
                    logger.warning("Songlink timeout after %d attempts: %s", attempt + 1, url)
                    return None
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            except httpx.HTTPError as exc:
                logger.warning("Songlink transport error for %s: %s", url, exc)
                return None

            if response.status_code == 404:
                logger.info("Songlink does not recognise URL: %s", url)
                return None
            if response.status_code == 429:
                if attempt == self._max_retries:
                    logger.warning("Songlink rate-limited for %s, giving up", url)
                    return None
                await asyncio.sleep(1.5 * (2**attempt))
                continue
            if 500 <= response.status_code < 600:
                if attempt == self._max_retries:
                    logger.warning("Songlink %s for %s, giving up", response.status_code, url)
                    return None
                await asyncio.sleep(0.5 * (2**attempt))
                continue
            if not response.is_success:
                logger.warning("Songlink %s for %s", response.status_code, url)
                return None

            try:
                payload = response.json()
            except ValueError:
                logger.warning("Songlink returned non-JSON for %s", url)
                return None
            return _parse(payload)
        return None


def _parse(payload: dict[str, object]) -> ResolvedSong | None:
    entity_id = payload.get("entityUniqueId")
    if not isinstance(entity_id, str) or not entity_id:
        return None

    entities = payload.get("entitiesByUniqueId")
    if not isinstance(entities, dict):
        return None
    entity = entities.get(entity_id)
    if not isinstance(entity, dict):
        # Fall back to the first available entity if the canonical one is missing.
        entity = next((e for e in entities.values() if isinstance(e, dict)), None)
        if entity is None:
            return None

    # Songlink occasionally returns episodes for podcast URLs — those aren't
    # songs and we don't want to spam the chat with podcast share blocks.
    if entity.get("type") == "podcastEpisode":
        return None

    title = entity.get("title")
    artist = entity.get("artistName")
    if not isinstance(title, str) or not isinstance(artist, str):
        return None

    thumbnail = entity.get("thumbnailUrl")
    thumbnail_url = thumbnail if isinstance(thumbnail, str) else None

    page_url_raw = payload.get("pageUrl")
    page_url = page_url_raw if isinstance(page_url_raw, str) else ""

    links_raw = payload.get("linksByPlatform")
    platform_links: dict[str, str] = {}
    if isinstance(links_raw, dict):
        for platform, link_obj in links_raw.items():
            if not isinstance(link_obj, dict):
                continue
            url = link_obj.get("url")
            if isinstance(url, str) and url:
                platform_links[str(platform)] = url

    if not platform_links and not page_url:
        return None

    return ResolvedSong(
        entity_id=entity_id,
        title=title.strip(),
        artist=artist.strip(),
        thumbnail_url=thumbnail_url,
        page_url=page_url,
        platform_links=platform_links,
    )
