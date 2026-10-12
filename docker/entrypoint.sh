#!/bin/sh
set -eu

# YouTube changes often; a fresh yt-dlp avoids most download failures.
if [ "${YTDLP_AUTO_UPDATE:-true}" = "true" ]; then
  echo "Updating yt-dlp..."
  pip install --user --quiet --upgrade "yt-dlp[default]" \
    || echo "yt-dlp update failed; using the version bundled in the image"
fi

exec uvicorn app.main:create_app --factory \
  --host 0.0.0.0 --port "${PORT:-8080}" --proxy-headers --forwarded-allow-ips='*'
