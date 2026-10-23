FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# FFmpeg for rendering, ImageMagick for optional text effects, OpenCV shared libraries.
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg imagemagick libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY . /app/
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/.temp /app/output /app/metrics /app/.secrets
CMD ["python", "telegram_bot.py"]
