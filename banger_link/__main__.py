"""Main application entry point for the Banger Link bot."""
import logging
import asyncio
import signal
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import Application, MessageHandler, CallbackQueryHandler

from banger_link.config import (
    TELEGRAM_TOKEN, LOG_LEVEL, LOG_FORMAT, DATA_DIR, DOWNLOAD_DIR
)
from banger_link.handlers.message import message_handler
from banger_link.handlers.callbacks import callback_query_handler
from banger_link.health import run_health_check

# Configure logging
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO)
)
logger = logging.getLogger(__name__)

class BangerLinkBot:
    """Main application class for the Banger Link bot."""
    
    def __init__(self):
        """Initialize the bot application."""
        self.application: Optional[Application] = None
        self.health_thread = None
        self.stop_event = asyncio.Event()
    
    async def start(self) -> None:
        """Start the bot and all its services."""
        logger.info("Starting Banger Link bot...")
        
        # Ensure data directories exist
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
        
        try:
            # Start health check server
            self.health_thread = run_health_check(port=8080)
            
            # Create the Application
            self.application = Application.builder().token(TELEGRAM_TOKEN).build()
            
            # Add handlers
            self.application.add_handler(message_handler)
            self.application.add_handler(callback_query_handler)
            
            # Set up signal handlers for graceful shutdown
            for sig in (signal.SIGINT, signal.SIGTERM):
                signal.signal(sig, self._handle_shutdown_signal)
            
            # Start the Bot
            logger.info("Starting bot...")
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            
            logger.info("Bot is running. Press Ctrl+C to stop.")
            
            # Keep the application running until stop event is set
            await self.stop_event.wait()
            
            logger.info("Shutting down...")
            
        except Exception as e:
            logger.critical(f"Fatal error: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Shut down the bot and clean up resources."""
        logger.info("Shutting down Banger Link bot...")
        
        if self.application:
            if self.application.updater.running:
                await self.application.updater.stop()
            if self.application.running:
                await self.application.stop()
            if self.application.initialized:
                await self.application.shutdown()
            await self.application.update_queue.put(None)  # Signal the worker to exit
        
        logger.info("Bot has been stopped.")
    
    def _handle_shutdown_signal(self, signum, frame) -> None:
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop_event.set()

def main() -> None:
    """Entry point for the Banger Link bot."""
    # Set up asyncio event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    bot = BangerLinkBot()
    
    try:
        loop.run_until_complete(bot.start())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
    finally:
        # Ensure proper cleanup
        if not bot.stop_event.is_set():
            loop.run_until_complete(bot.shutdown())
        
        # Close the event loop
        pending = asyncio.all_tasks(loop=loop)
        for task in pending:
            task.cancel()
        
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        
        loop.close()
        logger.info("Application shutdown complete.")

if __name__ == "__main__":
    main()
