"""Per-platform fallback search to fill in Spotify / Apple Music / YouTube
links that Songlink's free tier doesn't return.

Songlink's free API does single-provider lookups: an Apple Music URL gets back
the Apple/iTunes-network platforms (Tidal, Deezer, Pandora, Amazon, ...) but
never Spotify or YouTube — and similarly for Spotify- and YouTube-origin URLs.
This module fills those gaps by searching each platform's own catalog with
title + artist *after* Songlink has already given us those.

Failures degrade silently — if a sub-client times out or hits a non-success
status, the corresponding key just stays missing and the bot's "Not on:"
footer covers the user-facing UX.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import replace
from typing import Any
from urllib.parse import quote_plus

import httpx

from banger_link.services.songlink import ResolvedSong

logger = logging.getLogger(__name__)

# Platforms the resolver knows how to fill. The bot's `EXPECTED_PLATFORMS`
# (in formatter.py) is intentionally the same set — both surfaces care about
# the "big three" mainstream services.
FALLBACK_PLATFORMS: tuple[str, ...] = ("spotify", "appleMusic", "youtube")

# A browser-like UA helps with the Spotify anonymous-token endpoint, which
# 403s plain stdlib User-Agents in some regions.
DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


class _SubClient:
    """Common shape for fallback sub-clients: own `httpx.AsyncClient`, search."""

    enabled: bool

    async def search(self, *, title: str, artist: str) -> str | None:
        raise NotImplementedError

    async def aclose(self) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Spotify (anonymous-token scrape)
# ---------------------------------------------------------------------------


class SpotifyAnonymousClient(_SubClient):
    """Spotify search using the anonymous bearer token open.spotify.com hands out.

    The flow mirrors what the public web player does: fetch a token from
    `/get_access_token`, then use it on `api.spotify.com/v1/search`. No user
    auth, no Premium account needed. The token is anonymous-tier and is
    sufficient for read-only catalog endpoints.
    """

    TOKEN_URL = "https://open.spotify.com/get_access_token"
    SEARCH_URL = "https://api.spotify.com/v1/search"

    def __init__(self, *, client: httpx.AsyncClient | None = None) -> None:
        self.enabled = True
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(8.0),
            headers={"User-Agent": DEFAULT_UA, "Accept": "application/json"},
        )
        self._owns_client = client is None
        self._token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _bearer(self) -> str | None:
        async with self._lock:
            # Refresh ~30s before stated expiry so a request never lands on a
            # just-expired token.
            if self._token is not None and time.time() < self._expires_at - 30:
                return self._token
            try:
                response = await self._client.get(
                    self.TOKEN_URL,
                    params={"reason": "transport", "productType": "web_player"},
                )
            except httpx.HTTPError as exc:
                logger.warning("spotify token endpoint transport error: %s", exc)
                return None
            if not response.is_success:
                logger.warning(
                    "spotify token endpoint HTTP %d: %s",
                    response.status_code,
                    response.text[:200],
                )
                return None
            try:
                payload = response.json()
            except ValueError:
                logger.warning("spotify token endpoint returned non-JSON")
                return None
            access_token = payload.get("accessToken")
            expires_ms = payload.get("accessTokenExpirationTimestampMs")
            if not isinstance(access_token, str) or not isinstance(expires_ms, int):
                logger.warning("spotify token endpoint payload missing fields: %r", payload)
                return None
            self._token = access_token
            self._expires_at = expires_ms / 1000.0
            return self._token

    async def search(self, *, title: str, artist: str) -> str | None:
        token = await self._bearer()
        if token is None:
            return None
        query = f'track:"{title}" artist:"{artist}"'
        try:
            response = await self._client.get(
                self.SEARCH_URL,
                params={"q": query, "type": "track", "limit": "1"},
                headers={"Authorization": f"Bearer {token}"},
            )
        except httpx.HTTPError as exc:
            logger.warning("spotify search transport error for %r: %s", query, exc)
            return None
        if response.status_code == 401:
            # Token went bad early — invalidate and let the next call refresh.
            self._token = None
            self._expires_at = 0.0
            logger.info("spotify search 401, token invalidated")
            return None
        if not response.is_success:
            logger.warning("spotify search HTTP %d for %r", response.status_code, query)
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        items: list[dict[str, Any]] = payload.get("tracks", {}).get("items") or []
        if not items:
            return None
        external = items[0].get("external_urls", {}) or {}
        url = external.get("spotify")
        return url if isinstance(url, str) and url else None


# ---------------------------------------------------------------------------
# Apple Music via iTunes Search API
# ---------------------------------------------------------------------------


class ITunesSearchClient(_SubClient):
    """No-auth iTunes search; `trackViewUrl` is already a music.apple.com URL."""

    SEARCH_URL = "https://itunes.apple.com/search"

    def __init__(self, *, country: str = "US", client: httpx.AsyncClient | None = None) -> None:
        self.enabled = True
        self._country = country
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(8.0),
            headers={"User-Agent": DEFAULT_UA, "Accept": "application/json"},
        )
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search(self, *, title: str, artist: str) -> str | None:
        term = f"{title} {artist}".strip()
        try:
            response = await self._client.get(
                self.SEARCH_URL,
                params={
                    "term": term,
                    "entity": "song",
                    "limit": "1",
                    "country": self._country,
                },
            )
        except httpx.HTTPError as exc:
            logger.warning("itunes search transport error for %r: %s", term, exc)
            return None
        if not response.is_success:
            logger.warning("itunes search HTTP %d for %r", response.status_code, term)
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        results: list[dict[str, Any]] = payload.get("results") or []
        if not results:
            return None
        url = results[0].get("trackViewUrl")
        return url if isinstance(url, str) and url else None


# ---------------------------------------------------------------------------
# YouTube via Data API v3
# ---------------------------------------------------------------------------


class YouTubeSearchClient(_SubClient):
    SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

    def __init__(
        self,
        *,
        api_key: str | None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.enabled = bool(api_key)
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(8.0),
            headers={"User-Agent": DEFAULT_UA, "Accept": "application/json"},
        )
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def search(self, *, title: str, artist: str) -> str | None:
        if not self.enabled or self._api_key is None:
            return None
        query = f"{title} {artist}".strip()
        try:
            response = await self._client.get(
                self.SEARCH_URL,
                params={
                    "part": "snippet",
                    "q": query,
                    "type": "video",
                    "maxResults": "1",
                    "key": self._api_key,
                },
            )
        except httpx.HTTPError as exc:
            logger.warning("youtube search transport error for %r: %s", query, exc)
            return None
        if not response.is_success:
            logger.warning("youtube search HTTP %d for %r", response.status_code, query)
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        items: list[dict[str, Any]] = payload.get("items") or []
        if not items:
            return None
        video_id = (items[0].get("id") or {}).get("videoId")
        if not isinstance(video_id, str) or not video_id:
            return None
        return f"https://www.youtube.com/watch?v={quote_plus(video_id)}"


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------


class FallbackResolver:
    """Augment a `ResolvedSong` with whichever of spotify/appleMusic/youtube
    Songlink didn't return."""

    def __init__(
        self,
        *,
        spotify: SpotifyAnonymousClient | None = None,
        itunes: ITunesSearchClient | None = None,
        youtube: YouTubeSearchClient | None = None,
    ) -> None:
        self._spotify = spotify
        self._itunes = itunes
        self._youtube = youtube

    async def aclose(self) -> None:
        for sub in (self._spotify, self._itunes, self._youtube):
            if sub is not None:
                await sub.aclose()

    async def fill(self, resolved: ResolvedSong) -> ResolvedSong:
        title = resolved.title
        artist = resolved.artist
        if not title or not artist:
            return resolved

        # Run only the missing-platform searches, in parallel.
        wants: list[tuple[str, _SubClient]] = []
        if (
            "spotify" not in resolved.platform_links
            and self._spotify is not None
            and self._spotify.enabled
        ):
            wants.append(("spotify", self._spotify))
        if (
            "appleMusic" not in resolved.platform_links
            and self._itunes is not None
            and self._itunes.enabled
        ):
            wants.append(("appleMusic", self._itunes))
        if (
            "youtube" not in resolved.platform_links
            and self._youtube is not None
            and self._youtube.enabled
        ):
            wants.append(("youtube", self._youtube))
        if not wants:
            return resolved

        results = await asyncio.gather(
            *(client.search(title=title, artist=artist) for _, client in wants),
            return_exceptions=True,
        )

        new_links = dict(resolved.platform_links)
        for (platform, _), result in zip(wants, results, strict=True):
            if isinstance(result, BaseException):
                logger.warning("fallback %s raised: %s", platform, result)
                continue
            if isinstance(result, str) and result:
                new_links[platform] = result
                logger.info("filled %s via fallback for %s — %s", platform, title, artist)

        if new_links == resolved.platform_links:
            return resolved
        return replace(resolved, platform_links=new_links)
