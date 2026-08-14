# Build context: backend/ (self-contained — no npm workspace dependency
# like the two frontend Dockerfiles have).
FROM python:3.12-slim

WORKDIR /app

# Postgres client headers for psycopg2-binary's build (most wheels are
# prebuilt, but slim base images sometimes still need this at import time).
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Migrations run on every boot, before serving. Alembic migrations are
# idempotent once applied (upgrade head is a no-op if already there), so
# this is safe even if >1 replica starts concurrently against the same DB.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
