"""Message handlers for the Telegram bot."""
import re
import logging
from typing import Optional

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from banger_link.config import IGNORED_DOMAINS, WHITELISTED_CHAT_IDS
from banger_link.handlers.base import BaseHandler

logger = logging.getLogger(__name__)

class MessageHandlers:
    """Handles all message-related bot commands."""
    
    @staticmethod
    def extract_link(text: str) -> Optional[str]:
        """Extract the first URL from a message."""
        # Simple URL regex pattern
        url_pattern = r'https?://\S+'
        match = re.search(url_pattern, text)
        return match.group(0) if match else None
    
    @classmethod
    def is_ignored_domain(cls, url: str) -> bool:
        """Check if a URL is from an ignored domain."""
        return any(domain in url for domain in IGNORED_DOMAINS if domain)
    
    @classmethod
    async def handle_message(cls, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming messages."""
        # Ignore messages without text
        if not update.message or not update.message.text:
            return
            
        # Check if chat is whitelisted (if whitelist is not empty)
        if WHITELISTED_CHAT_IDS and update.message.chat_id not in WHITELISTED_CHAT_IDS:
            logger.debug(f"Ignored message from non-whitelisted chat ID: {update.message.chat_id}")
            return
        
        # Extract URL from message
        url = cls.extract_link(update.message.text)
        if not url:
            return
            
        # Check if URL is from an ignored domain
        if cls.is_ignored_domain(url):
            logger.debug(f"Ignored message with URL from ignored domain: {url}")
            return
        
        # Check if it's a supported music service
        if 'apple.com' in url or 'spotify.com' in url:
            await BaseHandler.handle_music_link(update, context, url)

# Create message handler instance
message_handlers = MessageHandlers()

# Export the message handler function for use in the application
message_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    message_handlers.handle_message
)
