![Banner](https://img.shields.io/badge/Project%20Status-Active-green) ![Python Version](https://img.shields.io/badge/Python-3.12-blue) ![License](https://img.shields.io/badge/License-MIT-lightgrey)

# News to Video Generator

## Overview

This project generates videos based on trending news articles and uploads them to YouTube Shorts. It utilizes `NewsAPI` to fetch the latest news and uses `gTTS` to create Spanish voiceovers. The video is then created and prepared for YouTube Shorts. The TikTok integration is still under development.

## Features

- Fetches trending news articles from `NewsAPI`.
- Generates descriptive text for the news.
- Creates audio using `gTTS` in Spanish.
- Assembles the video with subtitles and voiceover.
- Uploads the video to YouTube Shorts.

## Requirements

- Python 3.12+
- API keys for NewsAPI, YouTube

## Installation

### Step 1: Install Python 3.12

1. Download Python 3.12 from the [official Python website](https://www.python.org/downloads/release/python-3120/).
2. Follow the installation instructions for your operating system.

### Step 2: Clone the Repository

```bash
git clone https://github.com/your-username/from_news_to_video_uploaded.git
cd from_news_to_video_uploaded
```

### Step 3: Set Up a Virtual Environment

1. Create and activate a virtual environment:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Rename `config.py.example` to `config.py`:
   ```bash
   mv config.py.example config.py
   ```

2. Edit `config.py` with your API keys:
   ```python
   # NewsAPI
   NEWSAPI_API_KEY = 'your_newsapi_api_key'
   
   # YouTube
   YOUTUBE_API_KEY = 'your_youtube_api_key'
   ```

## Obtaining API Keys

### NewsAPI

1. Register at [NewsAPI](https://newsapi.org/).
2. Generate your API key from the dashboard.

### YouTube

1. Visit [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project and enable the YouTube Data API v3.
3. Generate an API key from the credentials section.

## Usage

1. Run the main script:
   ```bash
   python main.py
   ```

   This script:
   - Fetches the latest news articles using `NewsAPI`.
   - Generates descriptive text using an AI model.
   - Creates a voiceover in Spanish using `gTTS`.
   - Assembles the video with subtitles and voiceover.
   - Uploads the video to YouTube Shorts.

## Project Structure

- `main.py`: The main script that orchestrates the entire process.
- `config.py`: Configuration file for API keys.
- `src/`: Contains modules for various functionalities:
  - `news_api_client.py`: Handles fetching news from NewsAPI.
  - `text_generator.py`: Generates descriptive text.
  - `audio_generator.py`: Creates audio using gTTS.
  - `video_assembler.py`: Assembles the video.
  - `youtube_uploader.py`: Uploads the video to YouTube Shorts.

## Notes

- The TikTok integration is under development and will be available in a future update.
- Ensure that `ffmpeg` and `ImageMagick` are installed on your system for video processing. 

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

For more information, visit the [GitHub repository](https://github.com/your-username/from_news_to_video_uploaded).
