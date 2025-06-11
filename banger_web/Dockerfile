# Build stage
FROM node:18-alpine AS build

# Install build dependencies
RUN apk add --no-cache \
    python3 \
    make \
    g++

WORKDIR /app

# Copy package files and config
COPY package*.json ./
COPY svelte.config.js ./
COPY tailwind.config.js ./
COPY postcss.config.js ./
COPY vite.config.js ./

# Install dependencies with legacy peer deps to resolve conflicts
RUN npm install --legacy-peer-deps && \
    npm install --save-dev lucide-svelte @sveltejs/adapter-node

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p src/routes src/lib src/app

# Ensure app.html exists
RUN if [ ! -f src/app.html ]; then \
      mkdir -p src && \
      echo '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">%sveltekit.head%</head><body>%sveltekit.body%</body></html>' > src/app.html; \
    fi

# Generate SvelteKit build files
RUN npx svelte-kit sync

# Build the application
RUN npm run build

# Production stage
FROM node:18-alpine

# Install runtime dependencies
RUN apk add --no-cache \
    util-linux \
    file \
    flock

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install production dependencies with legacy peer deps
RUN npm install --omit=dev --legacy-peer-deps && \
    npm install lucide-svelte

# Copy built application from build stage
COPY --from=build /app/build /app/build
COPY --from=build /app/node_modules /app/node_modules
COPY --from=build /app/package*.json /app/

# Create data directory and set permissions
RUN mkdir -p /data && chown -R node:node /data && chmod 755 /data

# Expose the port the app runs on
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/ || exit 1

# Run as non-root user (node user comes with the node image)
USER node

# Start the application
CMD ["node", "build"]
