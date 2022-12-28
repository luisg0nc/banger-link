import logging
import os
import re

from bs4 import BeautifulSoup
import requests
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Updater, InlineQueryHandler, MessageHandler, Filters

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Define the API key for YouTube
YOUTUBE_API_KEY = os.environ['YOUTUBE_API_KEY']

# Define the API key for Telegram
TELEGRAM_API_KEY = os.environ['TELEGRAM_API_KEY']


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

    ## Split the URL into the resource name and the rest of the path
    protocol, resource_name_and_rest = link.split('://')
    resource_name, language, album, title, *rest = resource_name_and_rest.split('/')
    
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

def search_song(bot, update):
    """
    Handler function that is called when a message containing an Apple Music or Spotify link is received.
    Searches YouTube for the song and returns the first result.
    """
    # Get the message and extract the link
    message = update.message.text
    link = re.search(r"(https?://[^\s]+)", message).group(0)
    
    # Extract the song title and artist from the link
    if "apple.com" in link:
        song_title, artist = extract_song_info_from_apple_music_link(link)
    elif "spotify.com" in link:
        song_title, artist = extract_song_info_from_spotify_link(link)
    elif "youtube.com" in link:
        return
    else:
        update.message.reply_text("Sorry, I only support Apple Music (apple.com) and Spotify links (spotify.com), tell Luis to not be lazy and grow my code.")
        return
    
    # Search YouTube for the song
    youtube_url = search_song_on_youtube(song_title, artist)
    
    # Send the YouTube link as a message
    update.message.reply_text(f'Here is the Youtube Link, keep on bangin\' 😎\n{youtube_url}')

def main():
    # Create the Updater and pass it the API key
    updater = Updater(os.environ['TELEGRAM_API_KEY'])

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # Add the message handler
    dp.add_handler(MessageHandler(Filters.text, search_song))

    # Start the bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()

if __name__ == '__main__':
    main()
