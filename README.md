# banger-link
This is a Telegram bot that helps you find YouTube links for music from Apple Music and Spotify. Simply send a link to a song from either service, and the bot will find a YouTube link for the same song.

## How to use

1. Add the bot to a group chat or send it a message
2. Type /start to start using the bot
3. Send a link to a song from Apple Music or Spotify
4. The bot will send back a YouTube link for the same song

## Requirements

- Python 3.8 or higher
- Libraries:
  - `beautifulsoup4`: A library for parsing HTML and XML documents.
  - `python-telegram-bot`: A library for building Telegram bots.
  - `requests`: A library for making HTTP requests.
- API keys:
  - Telegram Bot
  - Youtube

## Running the bot

To run the bot, you'll need to set the API_KEY environment variable to your Telegram API key, as well as your Youtube API key. You can then run the bot.py script to start the bot.

## Docker

You can also run the provided docker-compose to easily launch it on docker. Just fill the API keys on the compose:

```
    environment:
      YOUTUBE_API_KEY: your_youtube_api_key
      TELEGRAM_API_KEY: your_telegram_api_key
```

To build and run the Docker container, run the following command:

```
docker-compose up -d
```

This will build the Docker image and run the container in detached mode.

## Credits

python-telegram-bot library
