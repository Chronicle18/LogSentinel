# ----- LogSentinel API image -----
# Targets Railway (single service, Nixpacks disabled via Dockerfile detection).
# Dashboard is a separate deploy target — build it with `npm run build` and
# host the static `dashboard/dist/` on any CDN (or a second Railway service).

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps for psycopg2-binary wheel + build basics (kept minimal).
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy only what the API needs at runtime.
COPY api ./api
COPY parser ./parser
COPY ingestion ./ingestion
COPY configs ./configs
COPY alembic ./alembic
COPY alembic.ini ./alembic.ini
COPY scripts ./scripts

# Railway injects $PORT; default to 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000

# Run migrations, then boot uvicorn. `sh -c` so $PORT expands at runtime.
CMD ["sh", "-c", "alembic upgrade head && uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
