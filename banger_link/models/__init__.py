"""Database models for the Banger Link bot."""
from tinydb import TinyDB, Query, JSONStorage
from datetime import datetime
from typing import Dict, Optional, List, Any
from pathlib import Path
from banger_link.config import DB_PATH
import json
import logging
import threading

logger = logging.getLogger(__name__)

class UTF8JSONStorage(JSONStorage):
    """Custom JSON storage that ensures UTF-8 encoding."""
    
    def __init__(self, path, **kwargs):
        """Initialize the storage with UTF-8 encoding."""
        kwargs['encoding'] = 'utf-8'
        kwargs['ensure_ascii'] = False  # Preserve non-ASCII characters
        kwargs['sort_keys'] = True      # For consistent output
        kwargs['indent'] = 2            # Pretty print for better readability
        kwargs['separators'] = (',', ': ')  # More compact JSON
        super().__init__(path, **kwargs)
    
    def write(self, data):
        """Write data to the file with proper encoding."""
        try:
            with open(self._handle.name, 'w', encoding='utf-8') as handle:
                json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
        except Exception as e:
            logger.error(f"Error writing to database: {e}")
            raise

class Database:
    """Wrapper around TinyDB for our application."""
    
    def __init__(self, db_path: Path):
        """Initialize the database with thread safety and UTF-8 encoding."""
        # Ensure the parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize TinyDB with our custom storage
        self.db = TinyDB(
            str(db_path),
            storage=UTF8JSONStorage,  # Use our custom storage class
            encoding='utf-8',
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            separators=(',', ': ')
        )
        
        self.query = Query()
        self._lock = threading.Lock()  # Lock for thread safety
        
    def save_song(self, chat_id: int, youtube_url: str, song_title: str, 
                     artist: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Save or update a song in the database in a thread-safe manner."""
        with self._lock:
            # Ensure all string fields are properly encoded as UTF-8
            if isinstance(song_title, str):
                song_title = song_title.encode('utf-8').decode('utf-8')
            if isinstance(artist, str):
                artist = artist.encode('utf-8').decode('utf-8')
            if isinstance(user, dict) and 'first_name' in user and isinstance(user['first_name'], str):
                user['first_name'] = user['first_name'].encode('utf-8').decode('utf-8')
            if isinstance(user, dict) and 'last_name' in user and isinstance(user['last_name'], str):
                user['last_name'] = user['last_name'].encode('utf-8').decode('utf-8')
            
            # Check if the entry already exists
            existing = self.db.get(
                (self.query.chat_id == chat_id) & 
                (self.query.youtube_url == youtube_url)
            )
            
            if existing:
                # Update existing entry
                doc_id = existing.doc_id
                update_data = {
                    'mentions': existing.get('mentions', 0) + 1,
                    'last_mentioned': datetime.now().isoformat()
                }
                
                # Preserve existing reactions if they exist
                if 'reactions' not in existing:
                    update_data['reactions'] = {}
                    
                self.db.update(update_data, doc_ids=[doc_id])
                return self.db.get(doc_id=doc_id)
            else:
                # Create new entry
                doc_id = self.db.insert({
                    'chat_id': chat_id,
                    'youtube_url': youtube_url,
                    'song_title': song_title,
                    'artist': artist,
                    'user': user,
                    'mentions': 1,
                    'likes': 0,
                    'dislikes': 0,
                    'reactions': {},
                    'date_added': datetime.now().isoformat(),
                    'last_mentioned': datetime.now().isoformat()
                })
                return self.db.get(doc_id=doc_id)
    
    def get_song(self, chat_id: int, youtube_url: str) -> Optional[Dict[str, Any]]:
        """
        Get a song by chat ID and YouTube URL.
        
        Args:
            chat_id: The chat ID
            youtube_url: The YouTube URL of the song
            
        Returns:
            The song document with ensured 'reactions' field, or None if not found
        """
        with self._lock:
            song = self.db.get(
                (self.query.chat_id == chat_id) & 
                (self.query.youtube_url == youtube_url)
            )
            
            # Ensure the song has a reactions field for backward compatibility
            if song and 'reactions' not in song:
                song['reactions'] = {}
                self.db.update({'reactions': {}}, doc_ids=[song.doc_id])
                
            return song
    
    def get_songs_by_chat(self, chat_id: int) -> List[Dict[str, Any]]:
        """
        Get all songs for a specific chat.
        
        Args:
            chat_id: The chat ID to get songs for
            
        Returns:
            List of song documents, each with ensured 'reactions' field
        """
        with self._lock:
            songs = self.db.search(self.query.chat_id == chat_id)
            
            # Ensure all songs have a reactions field
            updated = False
            for song in songs:
                if 'reactions' not in song:
                    song['reactions'] = {}
                    self.db.update({'reactions': {}}, doc_ids=[song.doc_id])
                    updated = True
            
            return songs
    
    def update_reaction(self, doc_id: int, reaction: str, user_id: int) -> bool:
        """
        Update the reaction for a song by a specific user.
        
        Args:
            doc_id: The document ID of the song
            reaction: The reaction type ('like' or 'dislike')
            user_id: The ID of the user reacting
            
        Returns:
            bool: True if the update was successful, False otherwise
        """
        with self._lock:
            song = self.db.get(doc_id=doc_id)
            if not song:
                return False
                
            # Initialize reactions dictionary if it doesn't exist
            if 'reactions' not in song:
                song['reactions'] = {}
            
            user_id_str = str(user_id)
            current_reaction = song['reactions'].get(user_id_str)
            updates = {}
            likes = song.get('likes', 0)
            dislikes = song.get('dislikes', 0)
            
            if reaction == 'like':
                if current_reaction == 'like':
                    # Remove like if already liked
                    updates['reactions.' + user_id_str] = None
                    updates['likes'] = max(0, likes - 1)
                else:
                    # Add like and remove previous dislike if exists
                    updates['reactions.' + user_id_str] = 'like'
                    if current_reaction == 'dislike':
                        updates['dislikes'] = max(0, dislikes - 1)
                    updates['likes'] = likes + (0 if current_reaction == 'like' else 1)
                    
            elif reaction == 'dislike':
                if current_reaction == 'dislike':
                    # Remove dislike if already disliked
                    updates['reactions.' + user_id_str] = None
                    updates['dislikes'] = max(0, dislikes - 1)
                else:
                    # Add dislike and remove previous like if exists
                    updates['reactions.' + user_id_str] = 'dislike'
                    if current_reaction == 'like':
                        updates['likes'] = max(0, likes - 1)
                    updates['dislikes'] = dislikes + (0 if current_reaction == 'dislike' else 1)
            
            # Clean up None values in reactions
            if updates.get('reactions.' + user_id_str) is None:
                updates['$unset'] = {'reactions.' + user_id_str: ""}
            
            if updates:
                self.db.update(updates, doc_ids=[doc_id])
                return True
            return False

# Initialize the database
db = Database(DB_PATH)
