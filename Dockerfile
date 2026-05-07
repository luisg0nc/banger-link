FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install uv from the official static binary image — small and reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.11.9 /uv /uvx /usr/local/bin/

# Install dependencies first to leverage the layer cache.
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-install-project --no-dev || uv sync --no-install-project --no-dev

# Copy source and install the project itself. README + LICENSE are required
# at build time because pyproject.toml references them.
COPY README.md LICENSE ./
COPY banger_link ./banger_link
RUN uv sync --no-dev

# Non-root runtime user owns /app/data so the bind-mounted volume is writable.
RUN groupadd -g 1000 app && \
    useradd -u 1000 -g app -s /usr/sbin/nologin -m app && \
    mkdir -p /app/data && \
    chown -R app:app /app

ENV DATA_DIR=/app/data
VOLUME ["/app/data"]
EXPOSE 8080

USER app
CMD ["python", "-m", "banger_link"]
