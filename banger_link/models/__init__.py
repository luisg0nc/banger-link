"""Database models for the Banger Link bot."""
from tinydb import TinyDB, Query, operations
from datetime import datetime
from typing import Dict, Optional, List, Any
from pathlib import Path
from banger_link.config import DB_PATH
import logging

logger = logging.getLogger(__name__)

class Database:
    """Wrapper around TinyDB for our application."""
    
    def __init__(self, db_path: Path):
        """Initialize the database."""
        self.db = TinyDB(db_path)
        self.query = Query()
        
    def save_song(self, chat_id: int, youtube_url: str, song_title: str, 
                 artist: str, user: Dict[str, Any]) -> Dict[str, Any]:
        """Save or update a song in the database."""
        # Check if the entry already exists
        existing = self.db.get(
            (self.query.chat_id == chat_id) & 
            (self.query.youtube_url == youtube_url)
        )
        
        if existing:
            # Update existing entry
            doc_id = existing.doc_id
            self.db.update(
                {
                    'mentions': existing['mentions'] + 1,
                    'likes': existing.get('likes', 0),
                    'dislikes': existing.get('dislikes', 0),
                    'last_mentioned': datetime.now().isoformat()
                },
                doc_ids=[doc_id]
            )
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
                'date_added': datetime.now().isoformat(),
                'last_mentioned': datetime.now().isoformat()
            })
            return self.db.get(doc_id=doc_id)
    
    def update_reaction(self, chat_id: int, youtube_url: str, reaction_type: str) -> Optional[Dict[str, Any]]:
        """Update like/dislike count for a song."""
        if reaction_type not in ['like', 'dislike']:
            return None
            
        entry = self.db.get(
            (self.query.chat_id == chat_id) & 
            (self.query.youtube_url == youtube_url)
        )
        
        if not entry:
            return None
            
        # Toggle reaction
        doc_id = entry.doc_id
        updates = {}
        
        if reaction_type == 'like':
            if entry.get('user_reaction') == 'like':
                # Remove like
                updates['likes'] = max(0, entry.get('likes', 0) - 1)
                updates['user_reaction'] = None
            else:
                # Add like, remove dislike if exists
                updates['likes'] = (entry.get('likes', 0) + 1)
                if entry.get('user_reaction') == 'dislike':
                    updates['dislikes'] = max(0, entry.get('dislikes', 0) - 1)
                updates['user_reaction'] = 'like'
        else:  # dislike
            if entry.get('user_reaction') == 'dislike':
                # Remove dislike
                updates['dislikes'] = max(0, entry.get('dislikes', 0) - 1)
                updates['user_reaction'] = None
            else:
                # Add dislike, remove like if exists
                updates['dislikes'] = (entry.get('dislikes', 0) + 1)
                if entry.get('user_reaction') == 'like':
                    updates['likes'] = max(0, entry.get('likes', 0) - 1)
                updates['user_reaction'] = 'dislike'
        
        self.db.update(updates, doc_ids=[doc_id])
        return self.db.get(doc_id=doc_id)
    
    def get_song(self, chat_id: int, youtube_url: str) -> Optional[Dict[str, Any]]:
        """Get a song by chat ID and YouTube URL."""
        return self.db.get(
            (self.query.chat_id == chat_id) & 
            (self.query.youtube_url == youtube_url)
        )

# Initialize the database
db = Database(DB_PATH)
