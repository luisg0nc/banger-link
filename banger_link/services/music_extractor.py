"""Service for extracting music information from various sources."""
import re
import logging
from typing import Tuple, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class MusicExtractor:
    """Extracts song information from various music service URLs."""
    
    @staticmethod
    def extract_from_apple_music(link: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts song title and artist from an Apple Music link.
        
        Args:
            link: The Apple Music URL
            
        Returns:
            Tuple of (song_title, artist) or (None, None) if extraction fails
        """
        try:
            # Extract the title from the URL path
            protocol, resource_name_and_rest = link.split('://')
            *_, title = resource_name_and_rest.split('/')
            
            # Fetch the webpage
            response = requests.get(link, timeout=10)
            response.raise_for_status()
            
            # Parse the response
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find the artist element
            artist_element = soup.find('a', class_='click-action')
            if not artist_element:
                logger.warning(f"Could not find artist in Apple Music link: {link}")
                return title.strip(), None
                
            return title.strip(), artist_element.text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting from Apple Music link {link}: {e}")
            return None, None
    
    @staticmethod
    def extract_from_spotify(link: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts song title and artist from a Spotify link.
        
        Args:
            link: The Spotify URL
            
        Returns:
            Tuple of (song_title, artist) or (None, None) if extraction fails
        """
        try:
            # Convert to embed URL for better parsing
            if 'open.spotify.com' in link and '/embed/' not in link:
                parts = link.split('spotify.com')
                link = f"{parts[0]}open.spotify.com/embed{parts[1].split('?')[0]}"
            
            # Fetch the webpage
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(link, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the response
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find all the anchor elements in the webpage
            anchors = soup.find_all('a')
            
            if len(anchors) < 2:
                logger.warning(f"Could not find song and artist in Spotify link: {link}")
                return None, None
                
            return anchors[0].text.strip(), anchors[1].text.strip()
            
        except Exception as e:
            logger.error(f"Error extracting from Spotify link {link}: {e}")
            return None, None
    
    @classmethod
    def extract_song_info(cls, link: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Extract song information from a music service URL.
        
        Args:
            link: The music service URL
            
        Returns:
            Tuple of (service_name, song_title, artist) or (None, None, None) if extraction fails
        """
        if 'apple.com' in link:
            song, artist = cls.extract_from_apple_music(link)
            return 'apple_music', song, artist
        elif 'spotify.com' in link:
            song, artist = cls.extract_from_spotify(link)
            return 'spotify', song, artist
        else:
            return None, None, None
