<p align="center">
  <a>
    <img src="./docs/logo.png" alt="Logo" >
  </a>
</p>

# banger-link

![License: MIT](https://shields.io/badge/license-MIT-green)

This is a Telegram bot that helps you find YouTube links for music from Apple Music and Spotify. Simply send a link to a song from either service, and the bot will find a YouTube link for the same song.
It also allows users to request to extract the audio from the youtube link, uploaded as a file in the chat. 💃

## Requirements

- Python 3.8 or higher
- Libraries:
  - `beautifulsoup4`: A library for parsing HTML and XML documents.
  - `python-telegram-bot`: A library for building Telegram bots.
  - `requests`: A library for making HTTP requests.
  - `pytube`: Library to interface with youtube, necessary to extract audio.
- API keys:
  - Telegram Bot
  - Youtube

## Running the bot

To run the bot, you'll need to set the `API_KEY` environment variable to your Telegram API key, as well as your Youtube API key. You can then run the `bot.py` script to start the bot.

## Docker

You can also run the provided docker-compose to easily launch it on docker. Just fill the API keys on the docker-compose:

```
    environment:
      YOUTUBE_API_KEY: your_youtube_api_key
      TELEGRAM_API_KEY: your_telegram_api_key
```

To build and run the Docker container, run the following command:

```
docker-compose build && \
docker-compose up -d
```

This will build the Docker image and run the container in detached mode.

## How to use

1. Add the bot to a group chat or talk directly to it.
2. Send a link to a song from Apple Music or Spotify
3. The bot will send back a YouTube link for the same song
   1. User may click Download
   2. Bot will download audio from youtube and upload to chat

## Credits

Thanks to everyone who has worked on these two libraries, they are amazing! 😎

[python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
[pytube](https://github.com/pytube/pytube)