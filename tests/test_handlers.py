from __future__ import annotations

import pytest

from banger_link.handlers.callbacks import KIND_FROM_LETTER
from banger_link.handlers.commands import _parse_limit
from banger_link.handlers.messages import _extract_url, _is_ignored, _is_music_url


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://open.spotify.com/track/abc", True),
        ("https://music.apple.com/us/album/x/123", True),
        ("https://youtu.be/xYz", True),
        ("https://www.youtube.com/watch?v=abc", True),
        ("https://soundcloud.com/artist/track", True),
        ("https://song.link/s/abc", True),
        ("https://example.com/whatever", False),
        ("https://twitter.com/x/status/1", False),
        ("not a url", False),
    ],
)
def test_is_music_url(url: str, expected: bool) -> None:
    assert _is_music_url(url) is expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("plain message", None),
        ("listen https://x.test/song", "https://x.test/song"),
        ("at end: https://x.test/song.", "https://x.test/song"),  # trailing punctuation stripped
        ("(https://x.test/song)", "https://x.test/song"),
        ("first https://a.test/x and https://b.test/y", "https://a.test/x"),
    ],
)
def test_extract_url(text: str, expected: str | None) -> None:
    assert _extract_url(text) == expected


def test_is_ignored_uses_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    from banger_link import config

    monkeypatch.setattr(config.settings, "ignored_domains", ["badsite.test"])
    assert _is_ignored("https://badsite.test/x")
    assert not _is_ignored("https://goodsite.test/x")


@pytest.mark.parametrize(
    "args,expected",
    [
        (None, 10),
        ([], 10),
        (["5"], 5),
        (["100"], 25),  # capped
        (["0"], 1),  # floored
        (["abc"], 10),  # invalid → default
    ],
)
def test_parse_limit(args: list[str] | None, expected: int) -> None:
    assert _parse_limit(args) == expected


def test_callback_kind_letter_mapping() -> None:
    assert KIND_FROM_LETTER == {"l": "like", "d": "dislike"}
