![Banner](https://img.shields.io/badge/Project%20Status-Active-green) ![Python Version](https://img.shields.io/badge/Python-3.10-blue) ![License](https://img.shields.io/badge/License-MIT-lightgrey)

</br>
<a href="https://www.buymeacoffee.com/akumanomi1k"><img src="https://img.buymeacoffee.com/button-api/?text=Fuel my creativity! 💸&emoji=🍺&slug=akumanomi1k&button_colour=FF3737&font_colour=000000&font_family=Inter&outline_colour=000000&coffee_colour=FF3737" /></a>


# 📺 **VideoNews** 📰

![banner](https://th.bing.com/th/id/OIG4.QJJxpMDBlrWO4t0OTO.j?w=1024&h=1024&rs=1&pid=ImgDetMain)

## 📄 Overview

**fVideo News** is a full-featured automation tool designed to streamline the creation of engaging, high-quality videos from news articles. The tool is particularly useful for content creators, media agencies, and social media marketers who want to transform written news into visually captivating and easily shareable videos for platforms like YouTube, TikTok, and Instagram.

This repository combines cutting-edge AI technologies for text generation, image creation, voice synthesis, and video assembly, allowing users to generate videos with minimal manual intervention. By leveraging APIs and powerful libraries, it offers a modular approach to customize various aspects of video production. Here’s a breakdown of what this project can do:
Let's craft a visually appealing README that stands out, adds precise installation guidance, and integrates best practices for clarity. Here's an updated version:

---



**VideoNews** automates news content creation by fetching, summarizing, and assembling articles into videos. With integrated AI, it generates voiceovers and uploads to YouTube & TikTok!

🚀 **[Get Started Today!](#quickstart)**

---

## ✨ **Features**

- 🔍 **Fetch** news via APIs (NewsAPI, Currents)
- 🗣️ **Text-to-Speech** (TTS) with ElevenLabs
- 🎥 **Video Generation**: Combine media and subtitles
- 📤 **Auto-upload** to YouTube & TikTok

---

## 🎯 **Technologies Used**

- **Python 3.10**
- **APIs**: NewsAPI, Currents, Pexels, ElevenLabs
- **YouTube API**: OAuth 2.0 integration
- **Google Cloud Console**: API setup
- **SFML**: For rendering videos

---

## ⚙️ **Installation**

### 1. **Clone the Repository**

```bash
git clone https://github.com/akumanomi1988/VideoNews.git
cd VideoNews
```

### 2. **Set Up Virtual Environment**

```bash
python -m venv venv
source venv/bin/activate  # MacOS/Linux
venv\Scripts\activate      # Windows
```

### 3. **Install Dependencies**

```bash
pip install -r requirements.txt
```

### 4. **Install SFML** (for multimedia processing)

- On **Windows**: Use the precompiled binaries from [SFML Downloads](https://www.sfml-dev.org/download.php)
- On **Linux**: Install via package manager
  ```bash
  sudo apt-get install libsfml-dev
  ```
- On **Mac**: Install via Homebrew
  ```bash
  brew install sfml
  ```

### 5. **Google Cloud Console Setup**

You'll need to configure the **YouTube Data API** for video uploads:

1. Go to [Google Console](https://console.cloud.google.com/).
2. Create a **New Project**.
3. Enable **YouTube Data API v3**.
4. Create **OAuth Credentials** and download the `client_secret.json` file.
5. Place the file inside the `.secrets/` folder.

---

## 🗂 **Project Structure**

```plaintext
VideoNews/
│
├── .secrets/                    # Stores sensitive API credentials
├── scripts/                     # Temporary files, subtitles, and processing scripts
├── DataFetcher/                 # Fetching news and media
├── dbControllers/               # User management (optional)
├── IA/                          # AI models: NLP, TTS, Text-to-Image
├── Uploaders/                   # Uploaders for TikTok, YouTube
├── main.py                      # Main program
├── settings.json                # API keys configuration
└── telegram_bot.py              # Integration with Telegram for notifications
```

---

## 📋 **Configuration**

Before running the app, configure your API keys in `settings.json`:

```json
{
  "news_api_key": "YOUR_NEWS_API_KEY",
  "pexels_api_key": "YOUR_PEXELS_API_KEY",
  "elevenlabs_api_key": "YOUR_ELEVENLABS_API_KEY",
  "google_credentials": "path_to_your_google_credentials.json"
}
```

---

## 🚀 **Run the Application**

Once everything is set up, run the following command to generate a video from news:

```bash
python main.py
```

The tool will fetch news, generate voiceovers, assemble a video, and upload it to YouTube or TikTok.

---

## 🛠 **API Setup**

1. **NewsAPI**: [Sign up for API key](https://newsapi.org/).
2. **Pexels API**: [Register for key](https://pexels.com/api/).
3. **ElevenLabs API**: [Sign up](https://elevenlabs.io/).

---

## 💡 **Best Practices**

- Customize your content by editing text summarization models.
- Ensure you monitor API rate limits to avoid overuse.
- Stay updated with the latest API changes on their official websites.

---

## 🤝 **Contributing**

Feel free to contribute by submitting issues or pull requests. Let's make **VideoNews** better together!

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

That's it! Your **VideoNews** README is now designed to be informative, visually appealing, and clear for potential users and contributors. The sections cover everything from setup to project structure, with icons and precise guidance on the technologies used, ensuring a smooth user experience.

If you find this project useful, give it a ⭐ **star** and help spread the word by sharing it with others in the community! Fork the repository and make it your own—let’s collaborate to make this tool even better.

## Star History ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=Akumanomi1988/from_news_to_uploaded&type=Date)](https://star-history.com/#Akumanomi1988/from_news_to_uploaded&Date)
---

For more information, visit the [GitHub repository](https://github.com/Akumanomi1988/VideoNews).
