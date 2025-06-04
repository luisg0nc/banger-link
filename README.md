<p align="center">
  <a>
    <img src="./docs/logo.png" alt="Banger Link Logo" width="200">
  </a>
  <h1 align="center">Banger Link</h1>
  <p align="center">
    Your music companion on Telegram 🎵
    <br>
    <a href="#-features">Features</a> •
    <a href="#-installation">Installation</a> •
    <a href="#-usage">Usage</a> •
    <a href="#-deployment">Deployment</a>
  </p>
  <p align="center">
    <a href="https://github.com/luisg0nc/banger-link/actions">
      <img src="https://img.shields.io/github/actions/workflow/status/luisg0nc/banger-link/tests.yml?style=flat-square" alt="Build Status">
    </a>
    <a href="https://pypi.org/project/banger-link/">
      <img src="https://img.shields.io/pypi/v/banger-link?style=flat-square" alt="PyPI">
    </a>
    <a href="https://github.com/luisg0nc/banger-link/blob/main/LICENSE">
      <img src="https://img.shields.io/github/license/luisg0nc/banger-link?style=flat-square" alt="License">
    </a>
    <a href="https://python-telegram-bot.org">
      <img src="https://img.shields.io/badge/python--telegram--bot-20.0-blue?style=flat-square" alt="python-telegram-bot">
    </a>
  </p>
</p>

## 💬 What is Banger Link?

Banger Link is a Telegram bot that bridges the gap between different music streaming services. Share a song link from Apple Music or Spotify, and the bot will find the corresponding YouTube video and let you download the audio.

Perfect for group chats where friends use different music platforms!

## ✨ Features

- 🔄 Convert Apple Music and Spotify links to YouTube
- ⬇️ Download audio directly in your chat
- 👍👎 Like/Dislike tracks to rate the best bangers
- 📊 Track how many times a song has been shared
- 🗂️ Persistent storage of shared songs
- 🚀 Fast and responsive with modern async code
- 🔒 Privacy-focused (no data collection)

## 🚀 Installation

### Prerequisites

- Python 3.8 or higher
- A [Telegram bot token](https://core.telegram.org/bots#6-botfather)
- A [YouTube Data API key](https://developers.google.com/youtube/registering_an_application)

### Local Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/luisg0nc/banger-link.git
   cd banger-link
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Copy the example environment file and update it with your credentials:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## 🎮 Usage

### Running the Bot

```bash
python -m banger_link
```

### Bot Commands

Just send a link to a song from Apple Music or Spotify, and the bot will handle the rest!

- Share a music link in any chat where the bot is added
- Use the buttons to like/dislike tracks
- Download the audio with a single click

## 🐳 Deployment

### Docker

1. Build and run with Docker Compose:
   ```bash
   docker-compose up -d --build
   ```

2. Or build manually:
   ```bash
   docker build -t banger-link .
   docker run -d --env-file .env banger-link
   ```

### Hosting

For production deployment, consider using:

- [Heroku](https://www.heroku.com/)
- [Railway](https://railway.app/)
- [PythonAnywhere](https://www.pythonanywhere.com/)
- A VPS with Docker

## 🤝 Contributing

Contributions are welcome! Please read our [contributing guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

- [python-telegram-bot](https://python-telegram-bot.org/) - The best Python library for Telegram bots
- [pytube](https://github.com/pytube/pytube) - For YouTube video downloads
- [TinyDB](https://tinydb.readthedocs.io/) - For simple JSON-based storage

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/luisg0nc">Luis Gonçalves</a>
</p>