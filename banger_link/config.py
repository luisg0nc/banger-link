"""Configuration settings for the Banger Link bot."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Telegram Bot Token
TELEGRAM_TOKEN = os.getenv('TELEGRAM_API_KEY')
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_API_KEY environment variable is not set")

# YouTube API Key
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
if not YOUTUBE_API_KEY:
    raise ValueError("YOUTUBE_API_KEY environment variable is not set")

# File paths
DATA_DIR = Path(os.getenv('DATA_DIR', str(BASE_DIR / 'data')))
DOWNLOAD_DIR = Path(os.getenv('DOWNLOAD_DIR', str(DATA_DIR / 'downloads')))
DB_PATH = DATA_DIR / 'db_music.json'

# Create directories if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Other settings
IGNORED_DOMAINS = os.getenv('IGNORED_DOMAINS', '').split(';') if os.getenv('IGNORED_DOMAINS') else []
WHITELISTED_CHAT_IDS = [int(x.strip()) for x in os.getenv('WHITELISTED_CHAT_IDS', '').split(',') if x.strip().isdigit()]

# Logging configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
