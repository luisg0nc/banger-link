FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_USER=appuser

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY pyproject.toml requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir -e .

# Copy the rest of the application
COPY . .

# Create app user and directories with correct permissions
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser && \
    mkdir -p /app/data/downloads && \
    chown -R 1000:1000 /app && \
    chmod -R 755 /app && \
    chmod 777 /app/data

# Set volume for persistent data
VOLUME ["/app/data"]

# Set environment variables for data directories
ENV DATA_DIR=/app/data \
    DOWNLOAD_DIR=/app/data/downloads

# Run as non-root user
USER appuser

# Run the bot
CMD ["python", "-m", "banger_link"]
