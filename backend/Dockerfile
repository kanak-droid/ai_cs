# Build context MUST be the repo root, not backend/ — this image now also
# builds and serves the chat-app SPA from the same process (see the SPA
# catch-all route at the bottom of app/main.py), which needs npm workspaces
# resolved from the root package.json/package-lock.json + packages/shared.
# e.g., from the repo root:
#   docker build -f backend/Dockerfile -t astrohelp-backend .
#
# VITE_API_BASE_URL is baked into the chat-app bundle at build time. Leave it
# empty (the default) — same-origin, since this one process now serves both
# the API and the chat webview. Only set it if chat-app is ever split back
# out to call this backend cross-origin.
FROM node:20-alpine AS frontend-builder
WORKDIR /repo

COPY package.json package-lock.json ./
COPY chat-app chat-app
COPY packages packages
RUN npm ci

ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build --workspace chat-app

FROM python:3.12-slim
WORKDIR /app

# Postgres client headers for psycopg2-binary's build (most wheels are
# prebuilt, but slim base images sometimes still need this at import time).
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/. .
COPY --from=frontend-builder /repo/chat-app/dist ./app/chat_static

EXPOSE 8000

# Migrations run on every boot, before serving. Alembic migrations are
# idempotent once applied (upgrade head is a no-op if already there), so
# this is safe even if >1 replica starts concurrently against the same DB.
#
# ${PORT:-8000}, not a hardcoded port — platforms like Railway assign a
# port dynamically via the PORT env var and route traffic to whatever that
# is; hardcoding 8000 here means the app listens on the wrong port the
# moment PORT is anything else, and the platform reports it unhealthy even
# though the process actually started fine. Falls back to 8000 for local
# `docker run` / docker-compose, where nothing sets PORT.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
