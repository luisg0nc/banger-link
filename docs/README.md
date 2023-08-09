# Banger Link 

![License: MIT](https://shields.io/badge/license-MIT-green)

Your music companion on Telegram. 🎵

## 💬 What is Banger Link?

This is a Telegram bot that helps you find YouTube links for music from Apple Music and Spotify. Simply send a link to a song from either service, and the bot will retrieve a YouTube link for the same song.

This is great for groups of friends who use different music services, as it allows them to share music with each other.

## 🔥 Features
- Find YouTube links for music from Apple Music and Spotify.
- Extract audio from YouTube links and upload to chat.
- Keep track of links already processed.

# ✨ Quickstart

To run the bot, you'll need to set the `API_KEY` environment variable to your Telegram API key, as well as your Youtube API key. You can then run the `bot.py` script to start the bot.

## Talk with the botFather

1. **Open Telegram App:** Open the Telegram app on your device or visit the [Telegram Web](https://web.telegram.org/) version.

2. **Search for BotFather:** In the Telegram search bar, type "BotFather" and select the official BotFather account.

3. **Start a Chat:** Start a chat with BotFather by sending a message like `/start`.

4. **Create a New Bot:** To create a new bot, send the command `/newbot`. BotFather will guide you through the process and ask for a name for your bot.

5. **Choose a Username:** After naming your bot, choose a unique username that ends with "bot" (e.g., MyAwesomeBot).

6. **Get API Key (Token):** Once you've created the bot and chosen a username, BotFather will provide you with the API key (token) for your bot. This token is required to authenticate your bot with the Telegram API.

7. **Copy the API Key:** Copy the provided API key (token) and store it in a safe place. This token is like a password for your bot and should be kept confidential.


## Docker

You can also run the provided docker-compose to easily launch it on docker. Just fill the API keys on the docker-compose:

```
    environment:
      YOUTUBE_API_KEY: your_youtube_api_key
      TELEGRAM_API_KEY: your_telegram_api_key
```

To build and run the Docker container, run the following command:

```
docker compose build && \
docker compose up -d
```

This will build the Docker image and run the container in detached mode.

## How to use

1. Add the bot to a group chat or talk directly to it.
2. Send a link to a song from Apple Music or Spotify
3. The bot will send back a YouTube link for the same song
   1. User may click Download
   2. Bot will download audio from youtube and upload to chat

## Env File

You can also use an env file to set the API keys. Just copy .env.example to .env and fill the keys.

In order to use the env file in docker-compose, you need to add the following line to the docker-compose.yml file:

```
docker compose --env-file .env up -d
```

## Requirements

- Python 3.8 or higher
- Libraries:
  - `beautifulsoup4`: A library for parsing HTML and XML documents.
  - `python-telegram-bot`: Base library for Telegram bot.
  - `requests`: Library HTTP requests.
  - `pytube`: Library to interface with youtube, necessary to extract audio.
  - `tinyDB`: Small database to keep track of entries 
- API keys:
  - Telegram Bot
  - Youtube

## Data

This bot will keep track of the links it has already processed, so that it can keep track of mentions in a chat. This is done using a database, which is stored in the `data` folder. The database is a JSON file, and is managed using the `tinyDB` library.

# 🙇‍♂️ Credits

Thanks to everyone who has worked on these two libraries, they are amazing! 😎

[python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
[pytube](https://github.com/pytube/pytube)