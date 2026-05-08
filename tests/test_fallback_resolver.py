from __future__ import annotations

import time

import httpx
import pytest
import respx

from banger_link.services.fallback_resolver import (
    FallbackResolver,
    ITunesSearchClient,
    SpotifyAnonymousClient,
    YouTubeSearchClient,
    _spotify_totp,
)
from banger_link.services.songlink import ResolvedSong


def _resolved(**platform_links: str) -> ResolvedSong:
    return ResolvedSong(
        entity_id="x",
        title="Lust for Life",
        artist="Iggy Pop",
        thumbnail_url=None,
        page_url="https://song.link/s/x",
        platform_links=dict(platform_links) or {"appleMusic": "https://a"},
    )


# ---------------------------------------------------------------------------
# Spotify anonymous-token client
# ---------------------------------------------------------------------------


def test_spotify_totp_is_deterministic_and_six_digits() -> None:
    # Same `now` → same code; different 30 s window → potentially different code.
    code_a = _spotify_totp(1_700_000_000.0)
    code_b = _spotify_totp(1_700_000_000.5)
    code_c = _spotify_totp(1_700_000_030.0)
    assert code_a == code_b  # same 30 s window
    assert len(code_a) == 6 and code_a.isdigit()
    assert len(code_c) == 6 and code_c.isdigit()


@respx.mock
async def test_spotify_token_request_carries_totp_params() -> None:
    token_route = respx.get("https://open.spotify.com/api/token").respond(
        json={
            "accessToken": "tok",
            "accessTokenExpirationTimestampMs": int((time.time() + 3600) * 1000),
            "isAnonymous": True,
        }
    )
    respx.get("https://api.spotify.com/v1/search").respond(
        json={
            "tracks": {
                "items": [{"external_urls": {"spotify": "https://open.spotify.com/track/x"}}]
            }
        }
    )
    client = SpotifyAnonymousClient()
    try:
        await client.search(title="a", artist="b")
    finally:
        await client.aclose()
    sent = token_route.calls.last.request
    assert "totp=" in sent.url.query.decode()
    assert "totpVer=" in sent.url.query.decode()
    assert "ts=" in sent.url.query.decode()


@respx.mock
async def test_spotify_happy_path() -> None:
    respx.get("https://open.spotify.com/api/token").respond(
        json={
            "accessToken": "tok-123",
            "accessTokenExpirationTimestampMs": int((time.time() + 3600) * 1000),
            "isAnonymous": True,
        }
    )
    respx.get("https://api.spotify.com/v1/search").respond(
        json={
            "tracks": {
                "items": [
                    {
                        "id": "abc",
                        "external_urls": {"spotify": "https://open.spotify.com/track/abc"},
                    }
                ]
            }
        }
    )
    client = SpotifyAnonymousClient()
    try:
        url = await client.search(title="Lust for Life", artist="Iggy Pop")
        assert url == "https://open.spotify.com/track/abc"
    finally:
        await client.aclose()


@respx.mock
async def test_spotify_empty_results_returns_none() -> None:
    respx.get("https://open.spotify.com/api/token").respond(
        json={
            "accessToken": "tok-1",
            "accessTokenExpirationTimestampMs": int((time.time() + 3600) * 1000),
            "isAnonymous": True,
        }
    )
    respx.get("https://api.spotify.com/v1/search").respond(json={"tracks": {"items": []}})
    client = SpotifyAnonymousClient()
    try:
        assert await client.search(title="x", artist="y") is None
    finally:
        await client.aclose()


@respx.mock
async def test_spotify_token_refresh_on_expiry() -> None:
    near_expiry = int((time.time() + 5) * 1000)  # within the 30s refresh-buffer
    fresh_expiry = int((time.time() + 3600) * 1000)
    token_route = respx.get("https://open.spotify.com/api/token").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "accessToken": "old",
                    "accessTokenExpirationTimestampMs": near_expiry,
                    "isAnonymous": True,
                },
            ),
            httpx.Response(
                200,
                json={
                    "accessToken": "new",
                    "accessTokenExpirationTimestampMs": fresh_expiry,
                    "isAnonymous": True,
                },
            ),
        ]
    )
    respx.get("https://api.spotify.com/v1/search").respond(
        json={
            "tracks": {
                "items": [{"external_urls": {"spotify": "https://open.spotify.com/track/x"}}]
            }
        }
    )
    client = SpotifyAnonymousClient()
    try:
        await client.search(title="a", artist="b")
        await client.search(title="a", artist="b")
        assert token_route.call_count == 2
    finally:
        await client.aclose()


@respx.mock
async def test_spotify_search_401_invalidates_token() -> None:
    respx.get("https://open.spotify.com/api/token").mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "accessToken": "tok",
                    "accessTokenExpirationTimestampMs": int((time.time() + 3600) * 1000),
                    "isAnonymous": True,
                },
            )
        ]
    )
    respx.get("https://api.spotify.com/v1/search").respond(status_code=401)
    client = SpotifyAnonymousClient()
    try:
        assert await client.search(title="a", artist="b") is None
        assert client._token is None
    finally:
        await client.aclose()


@respx.mock
async def test_spotify_token_endpoint_failure_returns_none() -> None:
    respx.get("https://open.spotify.com/api/token").respond(status_code=500)
    client = SpotifyAnonymousClient()
    try:
        assert await client.search(title="a", artist="b") is None
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# iTunes Search
# ---------------------------------------------------------------------------


@respx.mock
async def test_itunes_happy_path() -> None:
    respx.get("https://itunes.apple.com/search").respond(
        json={
            "results": [
                {
                    "trackName": "Lust for Life",
                    "trackViewUrl": "https://music.apple.com/us/album/lust-for-life/1",
                }
            ]
        }
    )
    client = ITunesSearchClient(country="US")
    try:
        url = await client.search(title="Lust for Life", artist="Iggy Pop")
        assert url == "https://music.apple.com/us/album/lust-for-life/1"
    finally:
        await client.aclose()


@respx.mock
async def test_itunes_empty_results_returns_none() -> None:
    respx.get("https://itunes.apple.com/search").respond(json={"results": []})
    client = ITunesSearchClient()
    try:
        assert await client.search(title="x", artist="y") is None
    finally:
        await client.aclose()


@respx.mock
async def test_itunes_5xx_returns_none() -> None:
    respx.get("https://itunes.apple.com/search").respond(status_code=503)
    client = ITunesSearchClient()
    try:
        assert await client.search(title="x", artist="y") is None
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# YouTube Data API
# ---------------------------------------------------------------------------


@respx.mock
async def test_youtube_happy_path() -> None:
    respx.get("https://www.googleapis.com/youtube/v3/search").respond(
        json={"items": [{"id": {"videoId": "dQw4w9WgXcQ"}}]}
    )
    client = YouTubeSearchClient(api_key="dummy")
    try:
        url = await client.search(title="Lust for Life", artist="Iggy Pop")
        assert url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    finally:
        await client.aclose()


async def test_youtube_disabled_when_no_key() -> None:
    client = YouTubeSearchClient(api_key=None)
    try:
        assert client.enabled is False
        assert await client.search(title="x", artist="y") is None
    finally:
        await client.aclose()


@respx.mock
async def test_youtube_quota_exceeded_returns_none() -> None:
    respx.get("https://www.googleapis.com/youtube/v3/search").respond(status_code=403)
    client = YouTubeSearchClient(api_key="dummy")
    try:
        assert await client.search(title="x", artist="y") is None
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# FallbackResolver aggregator
# ---------------------------------------------------------------------------


class _StubClient:
    """Minimal sub-client double that records calls and returns a fixed URL."""

    def __init__(self, url: str | None = None) -> None:
        self.enabled = True
        self.url = url
        self.calls: list[tuple[str, str]] = []

    async def search(self, *, title: str, artist: str) -> str | None:
        self.calls.append((title, artist))
        return self.url

    async def aclose(self) -> None:
        pass


async def test_fill_only_calls_missing_platforms() -> None:
    spotify = _StubClient(url="https://open.spotify.com/track/A")
    itunes = _StubClient(url="https://music.apple.com/track/B")
    youtube = _StubClient(url="https://www.youtube.com/watch?v=C")

    resolver = FallbackResolver(spotify=spotify, itunes=itunes, youtube=youtube)  # type: ignore[arg-type]
    # Already has Spotify — fallback should leave that alone.
    result = await resolver.fill(_resolved(spotify="https://existing-spotify"))

    assert spotify.calls == []  # not invoked
    assert itunes.calls and youtube.calls  # invoked
    assert result.platform_links["spotify"] == "https://existing-spotify"
    assert result.platform_links["appleMusic"] == "https://music.apple.com/track/B"
    assert result.platform_links["youtube"] == "https://www.youtube.com/watch?v=C"


async def test_fill_returns_same_object_when_nothing_to_do() -> None:
    spotify = _StubClient(url="should-not-matter")
    itunes = _StubClient(url="should-not-matter")
    youtube = _StubClient(url="should-not-matter")
    resolver = FallbackResolver(spotify=spotify, itunes=itunes, youtube=youtube)  # type: ignore[arg-type]
    original = _resolved(
        spotify="https://s",
        appleMusic="https://a",
        youtube="https://y",
    )
    assert (await resolver.fill(original)) is original  # no work, identity preserved
    assert spotify.calls == itunes.calls == youtube.calls == []


async def test_fill_skips_disabled_subclients() -> None:
    spotify = _StubClient(url="https://s/")
    spotify.enabled = False
    itunes = _StubClient(url="https://music.apple.com/track/B")
    resolver = FallbackResolver(spotify=spotify, itunes=itunes, youtube=None)  # type: ignore[arg-type]

    result = await resolver.fill(_resolved())  # has only appleMusic by default
    assert spotify.calls == []  # disabled
    # appleMusic was already present, so itunes shouldn't be queried either
    assert itunes.calls == []
    assert "spotify" not in result.platform_links


async def test_fill_swallows_subclient_exceptions() -> None:
    class _RaisingClient(_StubClient):
        async def search(self, *, title: str, artist: str) -> str | None:
            raise RuntimeError("boom")

    spotify = _RaisingClient()
    resolver = FallbackResolver(spotify=spotify, itunes=None, youtube=None)  # type: ignore[arg-type]
    result = await resolver.fill(_resolved())
    # Spotify still missing, but the call returned without raising.
    assert "spotify" not in result.platform_links


async def test_fill_no_op_when_no_title_or_artist() -> None:
    spotify = _StubClient(url="https://s/")
    resolver = FallbackResolver(spotify=spotify, itunes=None, youtube=None)  # type: ignore[arg-type]
    bare = ResolvedSong(
        entity_id="x", title="", artist="", thumbnail_url=None, page_url="", platform_links={}
    )
    assert (await resolver.fill(bare)) is bare
    assert spotify.calls == []


@pytest.fixture(autouse=True)
def _reset_respx() -> None:
    # respx.mock decorator handles its own routes per test; this is just a
    # safety net so a hung mock from a previous test doesn't bleed into the
    # next one when respx is used outside the decorator.
    yield
