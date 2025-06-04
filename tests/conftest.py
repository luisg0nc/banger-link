"""Pytest configuration and fixtures for Banger Link tests."""
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Mock environment variables for testing
os.environ["TELEGRAM_API_KEY"] = "test_telegram_token"
os.environ["YOUTUBE_API_KEY"] = "test_youtube_key"
os.environ["DATA_DIR"] = "/tmp/banger_link_test_data"
os.environ["DOWNLOAD_DIR"] = "/tmp/banger_link_test_downloads"

@pytest.fixture
def mock_requests():
    """Fixture to mock requests.get."""
    with patch('requests.get') as mock_get:
        yield mock_get

@pytest.fixture
def mock_telegram_update():
    """Fixture to create a mock Telegram update."""
    update = MagicMock()
    update.message = MagicMock()
    update.message.from_user = MagicMock()
    update.message.from_user.id = 12345
    update.message.from_user.first_name = "Test"
    update.message.from_user.last_name = "User"
    update.message.from_user.username = "testuser"
    update.message.chat_id = 67890
    return update

@pytest.fixture
def mock_telegram_context():
    """Fixture to create a mock Telegram context."""
    context = MagicMock()
    context.bot = MagicMock()
    return context

@pytest.fixture(autouse=True)
def setup_test_directories():
    """Create test directories and clean up afterward."""
    # Setup - create directories
    data_dir = Path(os.environ["DATA_DIR"])
    download_dir = Path(os.environ["DOWNLOAD_DIR"])
    
    data_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)
    
    yield  # Test runs here
    
    # Teardown - clean up test directories
    # Note: In a real test environment, you might want to clean up test files
    # But be careful not to delete important data in development
