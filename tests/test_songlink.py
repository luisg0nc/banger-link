from __future__ import annotations

import httpx
import pytest
import respx

from banger_link.services.songlink import SonglinkClient

API = "https://api.song.link/v1-alpha.1/links"

SAMPLE_PAYLOAD = {
    "entityUniqueId": "SPOTIFY_SONG::abc",
    "userCountry": "US",
    "pageUrl": "https://song.link/s/abc",
    "entitiesByUniqueId": {
        "SPOTIFY_SONG::abc": {
            "id": "abc",
            "type": "song",
            "title": "Lust for Life",
            "artistName": "Iggy Pop",
            "thumbnailUrl": "https://thumb",
        }
    },
    "linksByPlatform": {
        "spotify": {"url": "https://open.spotify.com/track/abc"},
        "appleMusic": {"url": "https://music.apple.com/track/abc"},
        "youtube": {"url": "https://youtu.be/abc"},
    },
}


@pytest.fixture
async def client():
    transport = httpx.AsyncHTTPTransport()
    async_client = httpx.AsyncClient(transport=transport, timeout=httpx.Timeout(2.0))
    songlink = SonglinkClient(client=async_client, max_retries=1)
    yield songlink
    await async_client.aclose()


@respx.mock
async def test_resolve_happy_path(client: SonglinkClient) -> None:
    respx.get(API).respond(json=SAMPLE_PAYLOAD)
    result = await client.resolve("https://open.spotify.com/track/abc")
    assert result is not None
    assert result.entity_id == "SPOTIFY_SONG::abc"
    assert result.title == "Lust for Life"
    assert result.artist == "Iggy Pop"
    assert result.thumbnail_url == "https://thumb"
    assert result.platform_links["spotify"].endswith("/abc")
    assert "appleMusic" in result.platform_links
    assert "youtube" in result.platform_links


@respx.mock
async def test_resolve_returns_none_on_404(client: SonglinkClient) -> None:
    respx.get(API).respond(status_code=404)
    result = await client.resolve("https://open.spotify.com/track/missing")
    assert result is None


@respx.mock
async def test_resolve_retries_on_5xx(client: SonglinkClient) -> None:
    route = respx.get(API).mock(
        side_effect=[
            httpx.Response(500),
            httpx.Response(200, json=SAMPLE_PAYLOAD),
        ]
    )
    result = await client.resolve("https://open.spotify.com/track/abc")
    assert result is not None
    assert route.call_count == 2


@respx.mock
async def test_resolve_returns_none_after_retries_exhausted(client: SonglinkClient) -> None:
    respx.get(API).respond(status_code=500)
    result = await client.resolve("https://open.spotify.com/track/abc")
    assert result is None


@respx.mock
async def test_resolve_returns_none_on_malformed_payload(client: SonglinkClient) -> None:
    respx.get(API).respond(json={"foo": "bar"})  # no entityUniqueId
    result = await client.resolve("https://open.spotify.com/track/abc")
    assert result is None


@respx.mock
async def test_resolve_returns_none_on_non_json(client: SonglinkClient) -> None:
    respx.get(API).respond(text="not json")
    result = await client.resolve("https://open.spotify.com/track/abc")
    assert result is None


@respx.mock
async def test_resolve_skips_podcasts(client: SonglinkClient) -> None:
    payload = {
        **SAMPLE_PAYLOAD,
        "entitiesByUniqueId": {
            "SPOTIFY_SONG::abc": {
                **SAMPLE_PAYLOAD["entitiesByUniqueId"]["SPOTIFY_SONG::abc"],
                "type": "podcastEpisode",
            }
        },
    }
    respx.get(API).respond(json=payload)
    result = await client.resolve("https://open.spotify.com/episode/abc")
    assert result is None


def test_primary_link_prefers_display_order() -> None:
    from banger_link.services.songlink import ResolvedSong

    rs = ResolvedSong(
        entity_id="x",
        title="t",
        artist="a",
        thumbnail_url=None,
        page_url="https://song.link/x",
        platform_links={"deezer": "https://d", "spotify": "https://s"},
    )
    assert rs.primary_link() == "https://s"
