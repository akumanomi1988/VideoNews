FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg imagemagick \
    && rm -rf /var/lib/apt/lists/*

# The editable package requires pyproject.toml AND package sources at install time.
COPY pyproject.toml README.md requirements.txt ./
COPY bot/ ./bot/
COPY scripts/ ./scripts/
COPY news_video_processor.py telegram_bot.py ./
COPY Resources/ ./Resources/
COPY settings.runtime.example.json ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

# Real credentials must be supplied via environment or mounted secret files.
# Run one worker: the rendering pipeline is resource intensive.
CMD ["python", "telegram_bot.py"]
