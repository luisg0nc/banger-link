import { json } from '@sveltejs/kit';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';

export const prerender = false;

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Read from the same database file that banger-link uses
const DB_PATH = process.env.DB_PATH || path.join(process.cwd(), '..', 'data', 'db.json');

// Function to safely read the database file
async function readDatabase() {
  try {
    // Check if file exists
    const exists = await fs.pathExists(DB_PATH);
    if (!exists) {
      console.log('Database file does not exist, returning empty object');
      return {};
    }

    // Read the file with retry logic
    const maxRetries = 3;
    let lastError;

    for (let i = 0; i < maxRetries; i++) {
      try {
        // Read the file with a short delay between retries
        if (i > 0) {
          console.log(`Retry ${i + 1} of ${maxRetries}...`);
          await new Promise(resolve => setTimeout(resolve, 100 * i));
        }

        // Read the file with explicit UTF-8 encoding
        const data = await fs.readFile(DB_PATH, { encoding: 'utf-8' });
        return JSON.parse(data);
      } catch (error) {
        lastError = error;
        console.error(`Attempt ${i + 1} failed:`, error.message);
      }
    }

    // If we get here, all retries failed
    console.error('All read attempts failed');
    throw lastError;
  } catch (error) {
    console.error('Error reading database:', error);
    
    // Return empty object if file doesn't exist or is invalid
    if (error.code === 'ENOENT' || error.code === 'ENOTDIR') {
      return {};
    }
    
    // If it's a JSON parse error, try to read the file as text and log the content
    if (error instanceof SyntaxError) {
      try {
        const rawContent = await fs.readFile(DB_PATH, 'utf8');
        console.error('Invalid JSON content:', rawContent.substring(0, 500));
      } catch (e) {
        console.error('Could not read file content for debugging:', e);
      }
    }
    
    throw new Error(`Failed to read database file: ${error.message}`);
  }
}

// Helper function to safely extract and decode text
function decodeText(text) {
  if (!text || typeof text !== 'string') return '';
  
  // If the text is already properly encoded, return as is
  if (/^[\x00-\x7F]*$/.test(text)) {
    return text;
  }
  
  // Try to fix double-encoded UTF-8
  try {
    // First, try to decode as URI component
    try {
      const decoded = decodeURIComponent(text);
      if (decoded !== text) {
        return decoded;
      }
    } catch (e) {
      // If that fails, try with escape/unescape for older encodings
      try {
        const decoded = unescape(encodeURIComponent(text));
        if (decoded !== text) {
          return decoded;
        }
      } catch (e) {
        console.warn('Failed to decode text with escape/unescape:', text);
      }
    }
    
    // If we get here, return the original text
    return text;
  } catch (e) {
    console.warn('Failed to decode text, using as-is:', text);
    return text;
  }
}

export async function GET() {
  try {
    console.log('Reading database from:', DB_PATH);
    
    // Check if database file exists
    const exists = await fs.pathExists(DB_PATH);
    if (!exists) {
      console.error('Database file does not exist at:', DB_PATH);
      return json({ error: 'Database file not found' }, { status: 404 });
    }
    
    // Read the database file
    const db = await readDatabase();
    
    // If the database is empty or not in the expected format
    if (!db || typeof db !== 'object') {
      console.error('Invalid database format:', { type: typeof db, value: db });
      return json({ error: 'Invalid database format' }, { status: 500 });
    }
    
    // Handle nested structure where songs are under _default
    const songsData = db._default || db;
    
    // Transform the data to match our frontend format
    const songs = [];
    let validCount = 0;
    let invalidCount = 0;
    
    // Get all song entries from the nested structure
    const songEntries = [];
    
    // First, try to get songs from the _default object if it exists
    if (songsData._default && typeof songsData._default === 'object') {
      Object.entries(songsData._default).forEach(([key, song]) => {
        if (song && typeof song === 'object' && song.youtube_url) {
          songEntries.push(song);
        }
      });
    }
    
    // Then try to get songs from the root level
    Object.entries(songsData).forEach(([key, value]) => {
      // Skip the _default key as we've already processed it
      if (key === '_default') return;
      
      // If the value is a song object
      if (value && typeof value === 'object' && value.youtube_url) {
        songEntries.push(value);
      } 
      // If the value is another object that might contain songs
      else if (value && typeof value === 'object') {
        Object.values(value).forEach(item => {
          if (item && typeof item === 'object') {
            if (item.youtube_url) {
              songEntries.push(item);
            } else {
              // Look for nested songs one more level deep
              Object.values(item).forEach(nestedItem => {
                if (nestedItem && typeof nestedItem === 'object' && nestedItem.youtube_url) {
                  songEntries.push(nestedItem);
                }
              });
            }
          }
        });
      }
    });
    
    console.log(`Found ${songEntries.length} potential song entries`);
    
    for (const [index, song] of songEntries.entries()) {
      if (!song || !song.youtube_url) {
        invalidCount++;
        continue;
      }
      
      // Skip entries with missing required fields
      const songTitle = song.song_title || song.title;
      if (!songTitle) {
        invalidCount++;
        continue;
      }
      
      // Extract video ID from YouTube URL and generate thumbnail URL
      let videoId = '';
      let thumbnailUrl = '';
      try {
        const url = new URL(song.youtube_url);
        if (url.hostname.includes('youtu.be')) {
          videoId = url.pathname.slice(1);
        } else {
          videoId = url.searchParams.get('v');
        }
        
        if (videoId) {
          // Using hqdefault.jpg for a good balance of quality and load time
          thumbnailUrl = `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;
        }
      } catch (e) {
        console.error('Error parsing YouTube URL:', song.youtube_url, e);
      }

      // Extract YouTube video ID
      let youtubeId = '';
      try {
        const url = new URL(song.youtube_url);
        youtubeId = url.searchParams.get('v') || '';
      } catch (e) {
        // If URL parsing fails, try simple string extraction
        const match = song.youtube_url.match(/(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})/);
        youtubeId = match ? match[1] : '';
      }
      
      // Clean and decode the song data
      const cleanSong = {
        id: song.youtube_url,
        title: decodeText(songTitle),
        artist: decodeText(song.artist) || 'Unknown Artist',
        youtubeId,
        thumbnailUrl,
        plays: song.mentions || 0,
        likes: song.likes || 0,
        dislikes: song.dislikes || 0,
        date: song.last_mentioned || song.date_added || new Date().toISOString(),
        // Include full name if available, otherwise first name, otherwise 'Unknown'
        addedBy: song.user?.first_name && song.user?.last_name 
          ? `${song.user.first_name} ${song.user.last_name}`
          : song.user?.first_name || 'Unknown'
      };
      
      songs.push(cleanSong);
      validCount++;
    }
    
    console.log(`Processed ${validCount} valid songs, skipped ${invalidCount} invalid entries`);
    
    if (validCount === 0) {
      console.error('No valid songs found in database');
    }
    
    return json(songs);
  } catch (error) {
    console.error('Error in API endpoint:', error);
    return json(
      { error: 'Failed to process request', details: error.message },
      { status: 500 }
    );
  }
}
