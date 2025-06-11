import { json } from '@sveltejs/kit';
import fs from 'fs-extra';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Read from the same database file that banger-link uses
const DB_PATH = process.env.DB_PATH || path.join(process.cwd(), '..', '..', 'data', 'db_music.json');

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
    
    throw error;
  }
}

export async function GET() {
  try {
    const db = await readDatabase();
    
    // Get songs from the _default object
    const songs = db._default ? Object.values(db._default) : [];
    
    // Calculate statistics
    const totalSongs = songs.length;
    const userStats = {};
    
    // Count songs per user
    songs.forEach(song => {
      if (!song || !song.user) return;
      
      const username = song.user.username || `${song.user.first_name} ${song.user.last_name || ''}`.trim();
      if (!userStats[username]) {
        userStats[username] = { shares: 0 };
      }
      
      userStats[username].shares++;
    });
    
    // Convert to array and sort by number of shares
    const sortedUserStats = Object.entries(userStats)
      .map(([username, stats]) => ({
        username,
        shares: stats.shares
      }))
      .sort((a, b) => b.shares - a.shares);
    
    return json({
      totalSongs,
      userStats: sortedUserStats
    });
  } catch (error) {
    console.error('Error generating stats:', error);
    return json(
      { error: 'Failed to generate statistics' },
      { status: 500 }
    );
  }
}
