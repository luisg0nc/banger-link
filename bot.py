import logging
import os
import re
import pymongo
import random
from datetime import datetime
from pytube import YouTube

from bs4 import BeautifulSoup
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the API key for YouTube
YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']

# Define the API key for Telegram
TELEGRAM_API_KEY = os.environ['TELEGRAM_API_KEY']

# Domains divided by ;
IGNORED_DOMAINS = os.environ['IGNORED_DOMAINS']

# Mongo for data persistance
MONGO_HOST = os.environ['MONGO_HOST']
MONGO_PORT = os.environ['MONGO_PORT']

DOWNLOAD_DIR = os.environ['DOWNLOAD_DIR']

def extract_audio(youtube_url, output_path):
    try:
        # Create a YouTube object using the provided URL
        yt = YouTube(youtube_url)

        title = re.sub("[!@#$%^&*()[]{};:,./<>?\|`~-=_+]", " ", yt.title).replace(" ", "_")

        audio_stream = yt.streams.get_audio_only()

        # Download the audio stream to the specified output path
        audio_path = audio_stream.download(output_path=output_path, filename=f'{title}.mp4')

        logger.info(f'Audio {youtube_url} extraction successful!')

        return audio_path
    
    except Exception as e:
        logger.error(f'Error during audio extraction from {youtube_url}: {e}')

def search_song_on_youtube(song_title, artist):
    """
    Searches YouTube for a song with the given title and artist and returns the first result.
    """
    # Build the query string
    query = song_title + " " + artist
    query = query.replace(" ", "+")

    # Make the request to the YouTube API
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&key={YOUTUBE_API_KEY}"
    response = requests.get(url)
    data = response.json()

    # Get the first result
    result = data['items'][0]
    youtube_url = f"https://www.youtube.com/watch?v={result['id']['videoId']}"

    return youtube_url


def extract_song_info_from_apple_music_link(link):
    """
    Extracts the song title and artist from an Apple Music link.
    """

    # Split the URL into the resource name and the rest of the path
    protocol, resource_name_and_rest = link.split('://')
    resource_name, language, album, title, * \
        rest = resource_name_and_rest.split('/')

    # Fetch the webpage
    response = requests.get(link)

    # Parse the response
    soup = BeautifulSoup(response.text, "html.parser")

    title_element = title

    # Find the anchor element with the class "metadata-lockup__subheadline"
    artist_element = soup.find('a', class_='click-action')

    song_title = title_element.strip()
    artist = artist_element.text.strip()

    return song_title, artist


def extract_song_info_from_spotify_link(link):
    """
    Extracts the song title and artist from a Spotify link.
    """

    # Split the URL into the resource name and the rest of the path
    protocol, resource_name_and_rest = link.split('://')
    resource_name, *rest = resource_name_and_rest.split('/')

    # Construct the modified URL with /embed after the resource name
    modified_link = f'{protocol}://{resource_name}/embed/{"/".join(rest)}'

    # Fetch the webpage
    response = requests.get(modified_link)

    # Parse the response
    soup = BeautifulSoup(response.text, "html.parser")

    # Find all the anchor elements in the webpage
    anchors = soup.find_all('a')

    # Extract the text from the first two anchor elements
    song = anchors[0].text
    artist = anchors[1].text

    return song, artist


async def search_song(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handler function that is called when a message containing an Apple Music or Spotify link is received.
    Searches YouTube for the song and returns the first result.
    """
    # Get the message and extract the link
    message = update.message.text
    user = update.message.from_user
    chat_id = update.message.chat_id

    link = re.search(r"(https?://[^\s]+)", message).group(0)

    # Extract the song title and artist from the link
    if "apple.com" in link:
        song_title, artist = extract_song_info_from_apple_music_link(link)
    elif "spotify.com" in link:
        song_title, artist = extract_song_info_from_spotify_link(link)
    elif any(domain in link for domain in IGNORED_DOMAINS.split(";")):
        return
    else:
        await update.message.reply_text(
            f"Sorry {user.first_name}, I only support Apple Music (apple.com) and Spotify links (spotify.com), tell Luis to not be lazy and grow my code.")
        return

    # Search YouTube for the song
    youtube_url = search_song_on_youtube(song_title, artist)

    keyboard = [[InlineKeyboardButton("Download 🚀", callback_data=youtube_url)]]
    download_markup = InlineKeyboardMarkup(keyboard)

    # Send the YouTube link as a message
    await update.message.reply_text(f'Here is the Youtube Link, keep on bangin\' 😎\n{youtube_url}', reply_markup=download_markup)

async def download_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query

    # await for someone to click button
    await query.answer()

    youtube_url = query.data

    # Edit message so that button disappears
    await query.edit_message_text(text=f'Download started, audio will be coming shortly, keep on scratchin\' 😘\n{youtube_url}')

    path = extract_audio(youtube_url,DOWNLOAD_DIR)

    # Upload file
    await context.bot.send_document(chat_id=query.message.chat_id, document=open(path, 'rb'))

    # Clean file
    os.remove(path)
def main():
    # Create the Updater and pass it the API key
    application = Application.builder().token(os.environ['TELEGRAM_API_KEY']).build()

    # Add the message handler
    application.add_handler(MessageHandler(filters.TEXT, search_song))
    application.add_handler(CallbackQueryHandler(download_button))

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()
