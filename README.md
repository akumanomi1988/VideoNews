# 📺 VideoNews 📰 - Telegram Bot Edition

![Banner](https://img.shields.io/badge/Project%20Status-Active-green) ![Python Version](https://img.shields.io/badge/Python-3.10+-blue) ![License](https://img.shields.io/badge/License-MIT-lightgrey)

</br>
<a href="https://www.buymeacoffee.com/akumanomi1k"><img src="https://img.buymeacoffee.com/button-api/?text=Fuel my creativity! 💸&emoji=🍺&slug=akumanomi1k&button_colour=FF3737&font_colour=000000&font_family=Inter&outline_colour=000000&coffee_colour=FF3737" /></a>

[🔗 Join the VideoNews Community on Telegram](https://t.me/VideoNewsCommunity)

## 🎯 Overview

VideoNews is an advanced automation framework that transforms news articles into engaging video content using a sophisticated multi-stage pipeline architecture. This version focuses on the Telegram bot interface for interacting with the VideoNews system. The bot allows users to fetch news, process it into videos, and manage configurations.

Key improvements in this version include a structured logging system, enhanced error handling with unique error IDs, a service-oriented architecture for better maintainability, and utility commands for improved user experience.

## 📚 Documentation

Detailed documentation for the core VideoNews pipeline is available in the following sections:

- [AI Components](docs/AI.md) - Natural language, speech, and image generation capabilities
- [Database Architecture](docs/DATABASE.md) - Data models and storage systems
- [API Integration](docs/API.md) - External service integrations
- [Pipeline System](docs/PIPELINE.md) - Video processing pipeline architecture

## ⚙️ Core Features (Bot Interface)

- 🤖 **News Interaction**:
  - Fetch news by category.
  - Process news articles into short or long-form videos based on selected topics or user-provided headlines.
- ⚙️ **Configuration Management (Legacy)**:
  - Interface to view and modify settings stored in `settings.json` (Note: This is an older system; primary configuration is via `.env` file).
- 🛠️ **Utility Commands**:
  - `/help`: Displays available commands and their usage.
  - Unknown command handling: Guides users when a command is not recognized.
- 📝 **Enhanced Backend**:
  - Structured logging for better traceability.
  - Robust error handling with unique error IDs for support.
  - Service-oriented architecture for improved code organization.
  - Retry mechanisms for resilient communication with the Telegram API.

## 🏗️ Project Structure (Bot)

The main bot logic resides within the `bot/` directory:

```
VideoNews/
├── bot/
│   ├── __init__.py
│   ├── main.py             # Main application runner for the bot
│   ├── config.py           # Handles loading of environment variables
│   ├── dispatcher.py       # Centralized registration of command/message handlers
│   ├── handlers/           # Request handlers for different bot commands
│   │   ├── __init__.py
│   │   ├── news_handler.py
│   │   ├── settings_handler.py
│   │   └── utility_handler.py
│   ├── services/           # Business logic (news fetching, video processing)
│   │   ├── __init__.py
│   │   ├── news_service.py
│   │   ├── settings_service.py
│   │   └── video_service.py
│   ├── utils/              # Utility modules (e.g., message sending, retries)
│   │   ├── __init__.py
│   │   ├── message_sender.py
│   │   └── retry_utils.py
│   └── models/             # Data models (currently placeholder)
│       └── __init__.py
├── tests/                  # Pytest tests for the bot
│   ├── __init__.py
│   ├── conftest.py
│   ├── handlers/
│   ├── services/
│   └── utils/
├── .env.example            # Example environment variables file
├── requirements.txt        # Python dependencies
├── telegram_bot.py         # Main entry point for the bot application
├── pipeline_config.json    # Configuration for the video processing pipeline
├── settings.json           # Legacy settings file (managed by /settings command)
└── ... (other project files and directories for the core pipeline)
```

## 🛠️ Technical Requirements

- Python 3.10+
- FFmpeg (for core video processing pipeline)
- Other dependencies as listed in `requirements.txt`

## ⚙️ Configuration

1.  **Environment Variables**:
    Create a `.env` file in the root directory by copying from `.env.example`:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file to include your actual API keys and tokens:
    *   `TELEGRAM_BOT_TOKEN`: Your Telegram Bot token from BotFather.
    *   `NEWS_API_KEY`: Your API key from NewsAPI.org (or your chosen news provider).
    *   `NEWS_API_COUNTRY` (optional, default: `us`): Default country for news.
    *   `NEWS_API_PAGE_SIZE` (optional, default: `10`): Default number of news articles to fetch.
    *   `TTS_LANGUAGE` (optional, default: `en-US`): Default language for Text-to-Speech services.
    *   Other API keys as required by the core VideoNews pipeline (e.g., ElevenLabs, Pexels) should also be managed here if they are integrated via environment variables in the services.

2.  **Pipeline Configuration (`pipeline_config.json`)**:
    This file configures the stages and parameters of the video processing pipeline. Refer to the core VideoNews documentation for details.

3.  **Legacy Settings (`settings.json`)**:
    Some bot commands (`/settings`, `/show_settings`) interact with a `settings.json` file. This is an older configuration method. For primary bot operations like API keys, the `.env` file takes precedence. If `settings.json` does not exist, it might be created by `SettingsService` or need to be copied from `settings.example.json` if that exists for the core pipeline.

## 📦 Installation

1.  **Clone the Repository**:
    ```bash
    git clone https://github.com/akumanomi1988/VideoNews.git
    cd VideoNews
    ```

2.  **Create and Activate Virtual Environment**:
    It is highly recommended to use a virtual environment.
    ```bash
    python3 -m venv venv  # Ensure you use python3.10 or higher
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    Ensure your `pip` is updated, then install the required packages:
    ```bash
    pip install --upgrade pip
    pip install -r requirements.txt
    ```
    If you encounter issues, especially with `spacy` models, you might need to download them as per messages during installation (e.g., `python -m spacy download en_core_web_sm`).

4.  **Set up Environment Variables**:
    Copy `.env.example` to `.env` and fill in your API keys and tokens as described in the **Configuration** section.

## 🚀 Running Locally

To run the Telegram bot:

```bash
python telegram_bot.py
```
This script initializes and starts the bot using the main logic defined in `bot/main.py`.

### Running with Docker (Optional)

You can also run the bot using Docker and Docker Compose.

1.  Ensure you have Docker and Docker Compose installed.
2.  Make sure you have a `.env` file created from `.env.example` in the project root, containing your API keys and bot token.
3.  If your `NewsProcessor` (used by the `/headless` command) relies on `config.json` (which is `settings.example.json` copied in the Docker image), ensure `settings.example.json` is a valid configuration for it.
4.  If you use `elevenlabsaccounts.payload.json`, ensure it's present in the root for `docker-compose.yml` to mount it.
5.  Build and run the container:
    ```bash
    docker-compose up --build -d
    ```
    (The `-d` flag runs it in detached mode)
6.  To view logs:
    ```bash
    docker-compose logs -f
    ```
7.  To stop the bot:
    ```bash
    docker-compose down
    ```

## 🤝 Contributing

Contributions are welcome! Please check our [Contributing Guidelines](CONTRIBUTING.md).

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Thanks to the amazing AI and ML communities.
- All our contributors and supporters.
- Special thanks to our Telegram community members.

---

Built with ❤️ by the VideoNews Team
