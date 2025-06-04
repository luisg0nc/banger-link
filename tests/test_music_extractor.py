"""Tests for the music extractor module."""
import pytest
from unittest.mock import patch, MagicMock

from banger_link.services.music_extractor import MusicExtractor

@pytest.mark.asyncio
async def test_extract_from_apple_music():
    """Test extracting song info from Apple Music links."""
    with patch('requests.get') as mock_get:
        # Mock the response from Apple Music
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <head><title>Test Song - Artist | Apple Music</title></head>
            <body>
                <a class="click-action">Artist Name</a>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        service, title, artist = MusicExtractor.extract_song_info(
            "https://music.apple.com/us/album/test-song/123456789"
        )
        
        assert service == "apple_music"
        assert title == "test-song"
        assert artist == "Artist Name"

@pytest.mark.asyncio
async def test_extract_from_spotify():
    """Test extracting song info from Spotify links."""
    with patch('requests.get') as mock_get:
        # Mock the response from Spotify
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <body>
                <a>Song Title</a>
                <a>Artist Name</a>
            </body>
        </html>
        """
        mock_get.return_value = mock_response
        
        service, title, artist = MusicExtractor.extract_song_info(
            "https://open.spotify.com/track/1234567890"
        )
        
        assert service == "spotify"
        assert title == "Song Title"
        assert artist == "Artist Name"

@pytest.mark.asyncio
async def test_extract_unsupported_link():
    """Test extracting from an unsupported link."""
    service, title, artist = MusicExtractor.extract_song_info(
        "https://example.com/unsupported"
    )
    
    assert service is None
    assert title is None
    assert artist is None
