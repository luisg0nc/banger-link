"""Service for extracting music information from various sources."""
import re
import json
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
            # Fetch the webpage with a browser-like user agent
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(link, headers=headers, timeout=10)
            response.raise_for_status()
            # Force UTF-8 encoding
            response.encoding = 'utf-8'
            
            # Parse the response
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find the JSON-LD script tag
            script_tag = soup.find('script', {'type': 'application/ld+json'})
            if not script_tag:
                logger.warning(f"Could not find JSON-LD data in Apple Music link: {link}")
                # Try to extract from meta tags as fallback
                return MusicExtractor._extract_from_meta_tags(soup)
                
            try:
                # Parse the JSON data
                json_data = json.loads(script_tag.string)
                
                # Extract song title
                song_title = json_data.get('name')
                if not song_title:
                    logger.warning(f"Could not find song title in JSON-LD: {link}")
                    return None, None
                
                # Extract artist
                artist = None
                audio_section = json_data.get('audio', {})
                if isinstance(audio_section, dict):
                    artists = audio_section.get('byArtist', [])
                    if isinstance(artists, list) and artists:
                        artist = artists[0].get('name')
                
                if not artist:
                    logger.warning(f"Could not find artist in JSON-LD: {link}")
                    return None, None
                    
                logger.info(f"Extracted from Apple Music - Title: {song_title}, Artist: {artist}")
                return song_title, artist
                
            except (json.JSONDecodeError, AttributeError) as e:
                logger.warning(f"Failed to parse JSON-LD data: {e}")
                # Try to extract from meta tags as fallback
                return MusicExtractor._extract_from_meta_tags(soup)
            
        except Exception as e:
            logger.error(f"Error extracting from Apple Music link {link}: {e}")
            return None, None
    
    @staticmethod
    def _extract_from_meta_tags(soup) -> Tuple[Optional[str], Optional[str]]:
        """Extract song info from meta tags as a fallback method."""
        try:
            # Try to get title from og:title or twitter:title
            title_tag = soup.find('meta', property='og:title') or soup.find('meta', {'name': 'twitter:title'})
            artist_tag = soup.find('meta', property='og:description') or soup.find('meta', {'name': 'twitter:description'})
            
            if not title_tag or not artist_tag:
                return None, None
                
            song_title = title_tag.get('content', '').split(' - ')[0].strip()
            artist = artist_tag.get('content', '').split(' · ')[0].strip()
            
            if song_title and artist:
                logger.info(f"Extracted from meta tags - Title: {song_title}, Artist: {artist}")
                return song_title, artist
                
        except Exception as e:
            logger.warning(f"Error extracting from meta tags: {e}")
            
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
                link = f"{parts[0]}spotify.com/embed{parts[1].split('?')[0]}"
            
            # Fetch the webpage
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9'
            }
            response = requests.get(link, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the response
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Try to find JSON data in the script tag
            script_tag = soup.find('script', {'id': '__NEXT_DATA__', 'type': 'application/json'})
            if script_tag:
                try:
                    json_data = json.loads(script_tag.string)
                    entity_data = json_data.get('props', {}).get('pageProps', {}).get('state', {}).get('data', {}).get('entity', {})
                    
                    # Extract song title and artist
                    song_title = entity_data.get('name')
                    artists = entity_data.get('artists', [])
                    artist = ", ".join([a.get('name', '') for a in artists]) if artists else None
                    
                    if song_title and artist:
                        logger.info(f"Extracted from Spotify JSON - Title: {song_title}, Artist: {artist}")
                        return song_title, artist
                        
                except (json.JSONDecodeError, AttributeError) as e:
                    logger.warning(f"Failed to parse Spotify JSON data: {e}")
            
            # Fallback to meta tags
            title_tag = soup.find('meta', property='og:title')
            desc_tag = soup.find('meta', property='og:description')
            
            if title_tag and desc_tag:
                title = title_tag.get('content', '')
                artist = desc_tag.get('content', '').split(' · ')[0].strip()
                
                if 'by ' in title:
                    parts = title.split(' by ')
                    song_title = parts[0].strip()
                    artist = parts[1].split(' | ')[0].strip() if len(parts) > 1 else artist
                else:
                    song_title = title.split(' | ')[0].strip()
                
                if song_title and artist:
                    logger.info(f"Extracted from Spotify meta tags - Title: {song_title}, Artist: {artist}")
                    return song_title, artist
            
            # Last resort: try to extract from page title
            title = soup.title.string if soup.title else ''
            if ' - song by ' in title:
                parts = title.split(' - song by ')
                if len(parts) == 2:
                    song_title = parts[0].strip()
                    artist = parts[1].split(' | ')[0].strip()
                    logger.info(f"Extracted from Spotify title - Title: {song_title}, Artist: {artist}")
                    return song_title, artist
            
            logger.warning(f"Could not extract song info from Spotify link: {link}")
            return None, None
            
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
