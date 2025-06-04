"""Callback query handlers for the Telegram bot."""
import logging
from typing import Optional, Tuple

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from banger_link.handlers.base import BaseHandler

logger = logging.getLogger(__name__)

class CallbackHandlers:
    """Handles all callback queries from inline buttons."""
    
    @classmethod
    def parse_callback_data(cls, data: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse callback data in the format 'action:type:data'.
        
        Args:
            data: The callback data string
            
        Returns:
            Tuple of (action, action_type, data)
        """
        if not data or ':' not in data:
            return None, None, None
            
        parts = data.split(':', 2)
        if len(parts) == 2:
            return parts[0], None, parts[1]
        return parts[0], parts[1], parts[2] if len(parts) > 2 else None
    
    @classmethod
    async def handle_callback_query(cls, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle all callback queries."""
        query = update.callback_query
        
        # Parse the callback data
        action, action_type, data = cls.parse_callback_data(query.data)
        
        if not action:
            await query.answer("Invalid action")
            return
        
        try:
            # Route to the appropriate handler
            if action == 'reaction' and action_type in ['like', 'dislike'] and data:
                await BaseHandler.handle_reaction(update, context, action_type, data)
            elif action == 'download' and data:
                await BaseHandler.handle_download(update, context, data)
            else:
                await query.answer("Unknown action")
                
        except Exception as e:
            logger.error(f"Error handling callback query {query.data}: {e}")
            await query.answer("An error occurred. Please try again.")

# Create callback handler instance
callback_handlers = CallbackHandlers()

# Export the callback query handler for use in the application
callback_query_handler = CallbackQueryHandler(callback_handlers.handle_callback_query)
