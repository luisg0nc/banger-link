"""Service for handling YouTube operations."""
import re
import logging
from typing import Optional, Tuple
import requests
from pytube import YouTube
from pytube.exceptions import PytubeError

from banger_link.config import YOUTUBE_API_KEY, DOWNLOAD_DIR

logger = logging.getLogger(__name__)

class YouTubeService:
    """Handles YouTube-related operations."""
    
    def __init__(self):
        """Initialize the YouTube service."""
        self.api_key = YOUTUBE_API_KEY
    
    def search_song(self, song_title: str, artist: str) -> Optional[str]:
        """
        Search YouTube for a song and return the first result URL.
        
        Args:
            song_title: The title of the song
            artist: The artist of the song
            
        Returns:
            YouTube URL or None if search fails
        """
        try:
            # Build the query string
            query = f"{song_title} {artist}"
            query = query.replace(" ", "+")

            # Make the request to the YouTube API
            url = (
                f"https://www.googleapis.com/youtube/v3/search?"
                f"part=snippet&q={query}&type=video&key={self.api_key}&maxResults=1"
            )
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if 'items' not in data or not data['items']:
                logger.warning(f"No results found for query: {query}")
                return None

            # Get the first result
            video_id = data['items'][0]['id']['videoId']
            return f"https://www.youtube.com/watch?v={video_id}"
            
        except Exception as e:
            logger.error(f"Error searching YouTube for {song_title} by {artist}: {e}")
            return None
    
    def download_audio(self, youtube_url: str) -> Optional[str]:
        """
        Download audio from a YouTube video.
        
        Args:
            youtube_url: The YouTube video URL
            
        Returns:
            Path to the downloaded audio file or None if download fails
        """
        try:
            # Create a YouTube object
            yt = YouTube(youtube_url)
            
            # Sanitize the title for use as a filename
            title = re.sub(r'[^\w\-_. ]', '_', yt.title)
            output_path = str(DOWNLOAD_DIR / f"{title}.mp4")
            
            # Get the audio stream and download
            audio_stream = yt.streams.get_audio_only()
            audio_stream.download(
                output_path=str(DOWNLOAD_DIR),
                filename=f"{title}.mp4"
            )
            
            logger.info(f"Successfully downloaded audio from {youtube_url}")
            return output_path
            
        except PytubeError as e:
            logger.error(f"Pytube error downloading {youtube_url}: {e}")
        except Exception as e:
            logger.error(f"Error downloading audio from {youtube_url}: {e}")
            
        return None

# Initialize the YouTube service
youtube_service = YouTubeService()
