# syntax=docker/dockerfile:1.7

FROM node:22-alpine AS ui
WORKDIR /ui
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# yt-dlp needs a JavaScript runtime to solve YouTube's player challenges.
FROM denoland/deno:bin-2.5.6 AS deno

FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DATA_DIR=/data \
    STATIC_DIR=/app/static \
    PORT=8080 \
    TZ=Europe/Paris \
    YTDLP_AUTO_UPDATE=true

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 yotube \
    && mkdir -p /data \
    && chown yotube:yotube /data

COPY --from=deno /deno /usr/local/bin/deno

WORKDIR /app
COPY backend/pyproject.toml ./
COPY backend/app ./app
RUN pip install . && rm -rf /root/.cache

COPY --from=ui /ui/dist ./static
COPY --chmod=755 docker/entrypoint.sh /usr/local/bin/entrypoint.sh

USER yotube
VOLUME ["/data"]
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\", \"8080\")}/api/health', timeout=4)"
ENTRYPOINT ["entrypoint.sh"]
