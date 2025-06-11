# Banger Web

A modern web interface for Banger Link, built with SvelteKit and Tailwind CSS.

## Features

- View trending, popular, and recent bangers
- Search functionality
- Responsive design
- Dark theme
- Real-time updates

## Prerequisites

- Node.js 18 or later
- npm or yarn
- Docker (optional)

## Development

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open [http://localhost:5173](http://localhost:5173) in your browser.

## Building for Production

1. Build the application:
   ```bash
   npm run build
   ```

2. Start the production server:
   ```bash
   npm run preview
   ```

## Docker

Build and run with Docker Compose:

```bash
docker-compose -f ../docker-compose.yml up -d --build banger_web
```

The web interface will be available at [http://localhost:3000](http://localhost:3000).

## Environment Variables

- `NODE_ENV`: Environment (development/production)
- `DB_PATH`: Path to the database file (default: `/data/db_music.json`)

## License

MIT
