![Banner](https://img.shields.io/badge/Project%20Status-Active-green) ![Python Version](https://img.shields.io/badge/Python-3.12-blue) ![License](https://img.shields.io/badge/License-MIT-lightgrey)
</br>
<a href="https://www.buymeacoffee.com/akumanomi1k"><img src="https://img.buymeacoffee.com/button-api/?text=Fuel my creativity! 💸&emoji=🍺&slug=akumanomi1k&button_colour=FF3737&font_colour=000000&font_family=Inter&outline_colour=000000&coffee_colour=FF3737" /></a>

# Video News

![banner](https://th.bing.com/th/id/OIG4.QJJxpMDBlrWO4t0OTO.j?w=1024&h=1024&rs=1&pid=ImgDetMain)

## 📄 Overview

**from_news_to_video_uploaded** is a full-featured automation tool designed to streamline the creation of engaging, high-quality videos from news articles. The tool is particularly useful for content creators, media agencies, and social media marketers who want to transform written news into visually captivating and easily shareable videos for platforms like YouTube, TikTok, and Instagram.

This repository combines cutting-edge AI technologies for text generation, image creation, voice synthesis, and video assembly, allowing users to generate videos with minimal manual intervention. By leveraging APIs and powerful libraries, it offers a modular approach to customize various aspects of video production. Here’s a breakdown of what this project can do:

1. **Automated News Summarization**: 
   The core of the application is its ability to automatically summarize news headlines into engaging and readable articles. This feature is powered by AI models capable of understanding complex news contexts and condensing them into bite-sized information pieces ready for video narration. The summarization can be fine-tuned to suit different tones and audiences, from formal news reporting to more casual, social media-friendly formats.

2. **Customizable AI-Generated Thumbnails and Images**: 
   With the integration of **Hugging Face's Flux model**, this tool offers an option to generate custom images or thumbnails that align with the news content. These images can be used as visuals within the video or as eye-catching thumbnails to improve engagement on social media platforms. It uses cutting-edge text-to-image generation techniques to create visually appealing images that are unique for every news story.

3. **Seamless Media Integration**: 
   To enrich video content, this project integrates with the **Pexels API** to fetch high-quality images and videos related to the article topics. This enables a diverse selection of media that adds depth and visual appeal to each video. By automating the media fetching process, the project ensures that each video is filled with relevant and appealing content without the need for manual searching and downloading.

4. **Text-to-Speech with Multiple Voices and Accounts**: 
   Utilizing **ElevenLabs’ Text-to-Speech (TTS)** technology, the tool can narrate articles with natural-sounding voices. With recent improvements, it now supports **multiple accounts and voices** using a JSON configuration file, allowing for different segments of the video to have varying narrations. This makes it possible to create dynamic videos with diverse voiceovers tailored to specific audiences or regions.

5. **Subtitle Generation and Synchronization**: 
   The tool automatically generates subtitles based on the summarized text and synchronizes them with the voiceover. The updated module provides two synchronization modes: **segment-based** and **word-based**, giving users the flexibility to choose how accurate and detailed they want the subtitle timing to be. This ensures accessibility and caters to audiences who prefer or require text to follow along.

6. **Video Assembly**: 
   The application’s video assembly feature combines all elements (text, voice, images, and subtitles) into a cohesive video. Users can choose to create videos from static images, with the duration of each image dynamically calculated based on the number of segments in the news story. This allows for visually balanced, well-paced videos that are engaging to viewers.

7. **TikTok Upload Automation**: 
   (In development) – A forthcoming feature will allow users to automatically upload the generated videos to **TikTok**. This will further enhance the tool’s functionality by enabling seamless content distribution to one of the world’s most popular social media platforms.

8. **Flexible Configurations**: 
   The project is highly configurable, allowing users to set API keys, modify article prompts, and choose voice preferences. It is also designed to be modular, meaning users can swap out or modify individual components such as the text generator, image generator, or video assembly workflow to fit specific use cases.

This tool is designed to save creators time and effort while producing professional-quality videos. By automating the most time-consuming parts of content creation—writing, editing, designing, and assembling media—it allows creators to focus on strategy and growth.

## Table of Contents
- 📦 [Features](#features-)
- 🛠 [Installation](#installation-)
- 🔧 [Modules](#modules-)
  - 📝 [article_generator](#article_generator-)
  - 🖼 [flux_image_generator](#flux_image_generator-)
  - 📰 [news_api_client](#news_api_client-)
  - 🎞 [pexels_media_fetcher](#pexels_media_fetcher-)
  - 🗣 [subtitle_and_voice](#subtitle_and_voice-)
  - 🚀 [tiktok_uploader](#tiktok_uploader-)
  - 🎤 [tts_elevenlabs](#tts_elevenlabs-)
  - 🎬 [video_assembler](#video_assembler-)
  - ⚙️ [main](#main-)
- 📋 [Requirements](#requirements-)
- 📥 [External Dependencies](#external-dependencies-)

---

## Features 📦

This project automates the process of creating engaging videos from news articles. Below are the core features:

1. **Article Generation**: Automatically generates short, engaging articles from news headlines using AI-based text generation.
2. **Image and Thumbnail Generation**: Creates AI-generated images and thumbnails based on news content via Hugging Face's Flux model.
3. **News Fetching**: Retrieves the latest articles from major news sources using the NewsAPI.
4. **Media Fetching**: Downloads related images and videos from the Pexels API to enrich the visual experience.
5. **Subtitles and Voice Synchronization**: Generates subtitles synchronized with AI-based voiceovers, supporting word-by-word or segment-based synchronization.
6. **TikTok Upload Automation**: (Under development) Automates uploading generated videos to TikTok.
7. **Text-to-Speech**: Uses ElevenLabs' TTS service, now supporting multiple accounts and voices through a JSON configuration.
8. **Video Assembly**: Assembles videos from individual images, calculating precise timing based on content segments.
9. **Customizable Workflows**: Modular design allows easy customization for different video formats and lengths.

---

## Installation 🛠

Follow these steps to set up the project:

1. **Download and install Python 3.10+**:  
   Get the latest version of Python from the [official website](https://www.python.org/downloads/).
   
2. **Clone the repository**:  
   Clone this repository using Git:
   ```bash
   git clone https://github.com/akumanomi1988/from_news_to_video_uploaded.git
   ```
   
3. **Move to the project directory**:
   ```bash
   cd from_news_to_video_uploaded
   ```

4. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

5. **Activate the virtual environment**:  
   - On **Windows**:
     ```bash
     venv\Scripts\activate
     ```
   - On **Linux/MacOS**:
     ```bash
     source venv/bin/activate
     ```

6. **Install the dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

7. **Download and install ffmpeg**:  
   You will need `ffmpeg` for video and audio manipulation. You can download it from [here](https://ffmpeg.org/download.html). After downloading, make sure to add it to your system PATH.

8. **Configure API keys and settings**:  
   - Set up the **NewsAPI** key for fetching news.
   - Set up your **Pexels API** key for media fetching.
   - Add your **ElevenLabs API** keys for TTS. Use a JSON configuration if you're handling multiple accounts.

   Configuration files:
   - `settings.config` for API keys and general settings.
   - `elevenlabsaccounts.json` for ElevenLabs TTS accounts.

9. **Run the main script**:
   ```bash
   python main.py
   ```
   This will trigger the workflow, fetching news, generating videos, and processing the content.

---

## Modules 🔧

### article_generator 📝
- **Description**: Generates a summary based on the news headline. The prompt used for text generation has been **improved** for more precise and engaging summaries.

### flux_image_generator 🖼
- **Description**: This module generates images and thumbnails using Flux via Hugging Face.

### news_api_client 📰
- **Description**: Fetches the latest news articles via News API. No recent changes here.

### pexels_media_fetcher 🎞
- **Description**: Fetches related images and videos from Pexels API based on keywords.

### subtitle_and_voice 🗣
- **Description**: Handles subtitle generation and synchronization with voiceovers. Improved synchronization accuracy and quality, with options for text segment or word-based syncing.

### tiktok_uploader 🚀
- **Description**: Currently under development. Will handle video uploads to TikTok once completed.

### tts_elevenlabs 🎤
- **Description**: Text-to-speech functionality using ElevenLabs, with support for multiple accounts via a JSON structure.

### video_assembler 🎬
- **Description**: Assembles videos from individual images and calculates the duration of each image based on the content.

### main ⚙️
- **Description**: Orchestrates the full workflow from fetching news to assembling videos and preparing them for upload.

---

## Requirements 📋

- Python 3.10+
- Install all necessary dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### External Dependencies 📥
- **ffmpeg**: Needed for video and audio manipulation. Download from [here](https://ffmpeg.org/download.html) and add it to your system PATH.
  
This project also requires the following third-party services:
- **NewsAPI** for fetching news.
- **Pexels API** for media assets.
- **ElevenLabs** for TTS.
- **Hugging Face Hub** for image generation.

---
## Notes

- The TikTok integration is under development and will be available in a future update.
- Ensure that `ffmpeg` and `ImageMagick` are installed on your system for video processing. 

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing 🤝

We warmly welcome contributions from the open-source community! If you have ideas for new features, bug fixes, or improvements, feel free to submit a pull request. Whether it's improving documentation, refining code, or adding a brand-new module, every bit helps!

Here’s how you can contribute:

1. **Fork the Repository**: Start by forking the repository to your GitHub account.
2. **Create a Branch**: Work on your changes in a new branch, making sure your updates are isolated to avoid conflicts.
3. **Submit a Pull Request**: Once you're happy with your contribution, open a pull request, and we’ll review it as soon as possible.

If you find this project useful, give it a ⭐ **star** and help spread the word by sharing it with others in the community! Fork the repository and make it your own—let’s collaborate to make this tool even better.

## Star History ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=Akumanomi1988/from_news_to_uploaded&type=Date)](https://star-history.com/#Akumanomi1988/from_news_to_uploaded&Date)
---

For more information, visit the [GitHub repository](https://github.com/Akumanomi1988/VideoNews).
