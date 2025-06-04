"""Base handlers for the Telegram bot."""
import logging
from typing import Dict, Any, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from banger_link.models import db
from banger_link.services.music_extractor import MusicExtractor
from banger_link.services.youtube_service import youtube_service

logger = logging.getLogger(__name__)

class BaseHandler:
    """Base handler class with common functionality."""
    
    @staticmethod
    def create_user_dict(user) -> Dict[str, Any]:
        """Convert a Telegram user object to a dictionary."""
        return {
            'id': user.id,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'username': user.username,
        }
    
    @staticmethod
    def create_song_keyboard(youtube_url: str, likes: int = 0, dislikes: int = 0, 
                           user_reaction: Optional[str] = None) -> InlineKeyboardMarkup:
        """Create an inline keyboard for a song message."""
        like_emoji = '👍' if user_reaction == 'like' else '👍'
        dislike_emoji = '👎' if user_reaction == 'dislike' else '👎'
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"{like_emoji} {likes}", 
                    callback_data=f"reaction:like:{youtube_url}"
                ),
                InlineKeyboardButton(
                    f"{dislike_emoji} {dislikes}", 
                    callback_data=f"reaction:dislike:{youtube_url}"
                ),
                InlineKeyboardButton(
                    "Download 🚀", 
                    callback_data=f"download:{youtube_url}"
                )
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @classmethod
    async def handle_music_link(cls, update: Update, context: ContextTypes.DEFAULT_TYPE, link: str) -> None:
        """Handle a music link from any supported service."""
        user = update.message.from_user
        chat_id = update.message.chat_id
        
        # Extract song info
        service, song_title, artist = MusicExtractor.extract_song_info(link)
        
        if not all([service, song_title, artist]):
            await update.message.reply_text(
                "Sorry, I couldn't extract song information from that link. "
                "I support Apple Music and Spotify links."
            )
            return
        
        # Search YouTube for the song
        youtube_url = youtube_service.search_song(song_title, artist)
        
        if not youtube_url:
            await update.message.reply_text(
                "Sorry, I couldn't find that song on YouTube. "
                "Please try a different song or check the spelling."
            )
            return
        
        # Save to database
        user_dict = cls.create_user_dict(user)
        entry = db.save_song(chat_id, youtube_url, song_title, artist, user_dict)
        
        # Prepare response
        if entry['mentions'] == 1:
            message = (
                f"🎵 *{song_title}* by *{artist}*\n\n"
                f"First time shared by {user.first_name}! 🎉\n"
                f"{youtube_url}"
            )
        else:
            message = (
                f"🎵 *{song_title}* by *{artist}*\n\n"
                f"Shared {entry['mentions']} times. "
                f"First shared by {entry['user']['first_name']}.\n"
                f"{youtube_url}"
            )
        
        # Send message with reaction buttons
        keyboard = cls.create_song_keyboard(
            youtube_url, 
            entry.get('likes', 0), 
            entry.get('dislikes', 0),
            entry.get('user_reaction')
        )
        
        await update.message.reply_text(
            message, 
            reply_markup=keyboard,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
    
    @classmethod
    async def handle_download(cls, update: Update, context: ContextTypes.DEFAULT_TYPE, youtube_url: str) -> None:
        """Handle download button click."""
        query = update.callback_query
        await query.answer()
        
        # Edit message to show download started
        await query.edit_message_text(
            text=('🎵 Downloading audio... This may take a moment. 🎵\n\n'
                  f'*YouTube Link:* {youtube_url}'),
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
        try:
            # Download the audio
            audio_path = youtube_service.download_audio(youtube_url)
            
            if not audio_path:
                raise Exception("Failed to download audio")
            
            # Send the audio file
            with open(audio_path, 'rb') as audio_file:
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=audio_file,
                    title=f"Downloaded from {youtube_url}"
                )
            
            # Update message to show completion
            await query.edit_message_text(
                text=('✅ Download complete! Enjoy your music! 🎧\n\n'
                      f'*YouTube Link:* {youtube_url}'),
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"Error in download handler: {e}")
            await query.edit_message_text(
                text=('❌ Sorry, there was an error downloading the audio. '
                      'Please try again later.\n\n'
                      f'*YouTube Link:* {youtube_url}'),
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        finally:
            # Clean up the downloaded file if it exists
            if 'audio_path' in locals() and audio_path:
                try:
                    import os
                    os.remove(audio_path)
                except Exception as e:
                    logger.error(f"Error cleaning up audio file {audio_path}: {e}")
    
    @classmethod
    async def handle_reaction(cls, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                            reaction_type: str, youtube_url: str) -> None:
        """Handle like/dislike reactions."""
        query = update.callback_query
        user = query.from_user
        chat_id = query.message.chat_id
        
        # Update reaction in database
        entry = db.update_reaction(chat_id, youtube_url, reaction_type)
        
        if not entry:
            await query.answer("Error: Song not found")
            return
        
        # Update the message with new reaction counts
        keyboard = cls.create_song_keyboard(
            youtube_url, 
            entry.get('likes', 0), 
            entry.get('dislikes', 0),
            entry.get('user_reaction')
        )
        
        # Edit the message to update the keyboard
        await query.edit_message_reply_markup(reply_markup=keyboard)
        
        # Send a small feedback to the user
        reaction_emoji = '👍' if reaction_type == 'like' else '👎'
        await query.answer(f"You {reaction_type}d this song! {reaction_emoji}")
