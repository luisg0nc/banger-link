# Banger Link 

![License: MIT](https://shields.io/badge/license-MIT-green)

Your music companion on Telegram and the Web. 🎵

## 💬 What is Banger Link?

Banger Link is a powerful music sharing platform that comes with both a Telegram bot and a modern web interface. It helps you discover, share, and enjoy music across different platforms.

### Components:
1. **Banger Link (Telegram Bot)**: A bot that helps you find YouTube links for music from Apple Music and Spotify, and even lets you download audio from YouTube.
2. **Banger Web**: A modern web interface to browse and discover trending, popular, and recent music shared through the platform.

## 🚀 Features

### Banger Link (Telegram Bot)
- Find YouTube links for music from Apple Music and Spotify
- Extract audio from YouTube links and upload to chat
- Keep track of shared links and provide statistics
- Group chat integration for collaborative music discovery

### Banger Web
- View trending, popular, and recent bangers
- Search functionality across shared music
- Responsive design that works on all devices
- Dark theme support
- Real-time updates

# 🛠️ Installation & Setup

## Prerequisites

- Docker and Docker Compose (recommended)
- Or:
  - Python 3.8+ for the Telegram bot
  - Node.js 18+ for the web interface

## Docker Setup (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/banger-link.git
   cd banger-link
   ```

2. Copy the example environment file and update with your API keys:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. Start the services:
   ```bash
   docker compose up -d --build
   ```

4. Access the services:
   - Telegram Bot: Search for your bot on Telegram
   - Web Interface: http://localhost:3000
   - Health Check: http://localhost:8080/health

## Manual Setup

### Banger Link (Telegram Bot)

1. Install Python dependencies:
   ```bash
   cd banger_link
   pip install -r requirements.txt
   ```

2. Set up environment variables (or create a `.env` file):
   ```
   TELEGRAM_TOKEN=your_telegram_token
   YOUTUBE_API_KEY=your_youtube_api_key
   ```

3. Run the bot:
   ```bash
   python -m banger_link
   ```

### Banger Web

1. Install Node.js dependencies:
   ```bash
   cd banger_web
   npm install
   ```

2. Configure environment variables if needed (defaults should work with Docker):
   ```
   NODE_ENV=development
   DB_PATH=/data/db_music.json
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

4. Open http://localhost:5173 in your browser

# 📊 Database

Banger Link uses a JSON database to track shared music and statistics. By default, it's stored in the `data` directory.

- The database is managed using `tinyDB` for the Python backend
- The web interface reads from the same database file
- In Docker, the database is persisted in a named volume

# 🤖 Using the Telegram Bot

1. Add the bot to a group chat or start a direct message
2. Share a music link from Apple Music or Spotify
3. The bot will respond with a YouTube link to the same song
4. Click "Download" to have the bot extract and upload the audio

# 🌐 Using the Web Interface

1. **Home Page**: Browse trending, popular, and recent music
2. **Search**: Find specific tracks or artists
3. **Dark Mode**: Toggle between light and dark themes

# 🔧 Configuration

## Environment Variables

### Banger Link (Backend)
- `TELEGRAM_TOKEN`: Your Telegram bot token
- `YOUTUBE_API_KEY`: YouTube Data API v3 key
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)
- `DATA_DIR`: Directory to store data (default: `./data`)

### Banger Web (Frontend)
- `NODE_ENV`: Environment (development/production)
- `DB_PATH`: Path to the database file (default: `/data/db_music.json`)

# 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

# 🙏 Credits

Thanks to the amazing open source projects that make Banger Link possible:

- [Python Telegram Bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [PyTube](https://github.com/pytube/pytube)
- [SvelteKit](https://kit.svelte.dev/)
- [Tailwind CSS](https://tailwindcss.com/)
- And all other dependencies listed in `requirements.txt` and `package.json`