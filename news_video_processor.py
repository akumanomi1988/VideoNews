import os
import re
import json
import time
import shutil
import random
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Union

from colorama import Fore, init
from telegram import CallbackQuery, Message
from scripts.AI.natural_language_generation import Chatbot
from scripts.AI.speech_to_text import stt_whisper
from scripts.AI.text_to_speech import TTSFactory, TTSProvider
from scripts.AI.text_to_image import FluxImageGenerator, AspectRatio, StylePreset
from scripts.DataFetcher.pexels_media_fetcher import PexelsMediaFetcher
from scripts.DataFetcher.news_api_client import NewsAPIClient
from scripts.MediaManagers.SRT_Processor import SRTProcessor
from scripts.video_assembler import VideoAssembler
from scripts.helpers.media_helper import ImageHelper, Position, Style
from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader
from scripts.utils.app_logger import trace

# Initialize Colorama
init(autoreset=True)

# Constants for configuration keys
CONFIG_ARTICLE_SETTINGS = 'article_settings'
CONFIG_NEWSAPI = 'newsapi'
CONFIG_PEXELS = 'pexels'
CONFIG_HUGGINGFACE = 'huggingface'
CONFIG_YOUTUBE = 'youtube'
CONFIG_TTS_EDGE = 'tts_edge'
CONFIG_VIDEO_RESULT = 'video_result'
CONFIG_SETTINGS = 'settings'

DEFAULT_CONFIG_FILE = 'settings.json'
DEFAULT_MAX_FILENAME_LENGTH = 30

class _RateLimiter:
    """Simple thread-safe token bucket rate limiter."""

    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self.tokens = max_calls
        self.last_refill = time.time()
        self._lock = __import__('threading').Lock()

    def acquire(self):
        with self._lock:
            now = time.time()
            elapsed = now - self.last_refill
            self.tokens = min(self.max_calls, self.tokens + elapsed * (self.max_calls / self.period))
            self.last_refill = now
            if self.tokens >= 1:
                self.tokens -= 1
                return
        sleep_time = self.period / self.max_calls
        time.sleep(sleep_time)
        self.acquire()


class NewsVideoProcessor:
    """
    Main processor for generating news videos from articles.
    Handles configuration, media generation, video assembly, and uploading.
    """

    @trace()
    def __init__(
        self,
        config_file: str = DEFAULT_CONFIG_FILE,
        callback_query: Optional[Union[CallbackQuery, Message]] = None
    ):
        """
        Initialize the NewsVideoProcessor.

        Args:
            config_file (str): Path to the configuration file.
            callback_query: Telegram CallbackQuery or Message object for progress updates.
        """
        self.callback_query = callback_query
        self.config_file = config_file
        self.config = self._load_configuration()
        self.temp_dir = self.config[CONFIG_SETTINGS]['temp_dir']
        self.parallel_workers = self.config[CONFIG_SETTINGS].get('parallel_workers', 6)
        images_per_minute = self.config[CONFIG_SETTINGS].get('images_per_minute', 20)
        self._img_rate_limiter = _RateLimiter(images_per_minute, 60.0) if images_per_minute else None
        self.news_client = NewsAPIClient(api_key=self.config[CONFIG_NEWSAPI]['api_key'])
        llm_providers = self.config.get("llm", {}).get("providers", [])
        self.article_generator = Chatbot(
            language=self.config[CONFIG_ARTICLE_SETTINGS]['language'],
            model=self.config[CONFIG_ARTICLE_SETTINGS]['model'],
            providers=llm_providers,
        )
        self.media_fetcher = PexelsMediaFetcher(
            api_key=self.config[CONFIG_PEXELS]['api_key'],
            temp_dir=self.temp_dir
        )
        self.stt = stt_whisper()
        self.tts = TTSFactory(TTSProvider.EDGE, output_dir=self.temp_dir)
        azure_img = self.config.get("azure_images", {})
        self.image_generator = FluxImageGenerator(
            token=self.config[CONFIG_HUGGINGFACE]['api_key'],
            output_dir=self.temp_dir,
            azure_endpoint=azure_img.get("endpoint"),
            azure_api_key=azure_img.get("api_key"),
            azure_model=azure_img.get("model", "MAI-Image-2e"),
        )
        self.youtube_uploader = YoutubeMediaUploader(
            client_secrets_file=self.config[CONFIG_YOUTUBE]['credentials_file'],
            channel_description=""
        )
        self.logger = logging.getLogger(__name__)
        self.video_files: List[str] = []

    @trace()
    def send_progress(self, message_text: str) -> None:
        """
        Send progress messages via a callback if provided.
        Safe to call from sync code running in a thread pool.
        """
        if not self.callback_query:
            return
        try:
            msg_obj = getattr(self.callback_query, 'message', self.callback_query)
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                msg_obj.reply_text(message_text, parse_mode='Markdown')
        except Exception as e:
            print(Fore.YELLOW + f"Error sending progress message: {str(e)}")
            try:
                msg_obj = getattr(self.callback_query, 'message', self.callback_query)
                import warnings
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    msg_obj.reply_text(message_text.replace('*', '').replace('_', ''))
            except Exception as ex:
                print(Fore.RED + f"Failed to send message even without Markdown: {str(ex)}")

    @trace()
    def _load_configuration(self) -> Dict[str, Any]:
        """
        Load the configuration from the specified JSON file.

        Returns:
            dict: Loaded configuration.
        """
        if not os.path.exists(self.config_file):
            self.send_progress(
                "⚠️ *Configuration Error*\n\n"
                "Configuration file not found.\n"
                "_Please use the configuration editor._"
            )
            raise FileNotFoundError("Configuration file not found.")

        try:
            with open(self.config_file, 'r', encoding='utf-8') as file:
                config = json.load(file)
            self.send_progress(
                "✅ *System Ready*\n\n"
                "Configuration loaded successfully\n"
                "_Starting process..._"
            )
            return config
        except json.JSONDecodeError:
            self.send_progress(
                "❌ *Invalid Configuration*\n\n"
                "The configuration file is corrupted.\n"
                "_Please check the JSON format._"
            )
            raise
        except Exception as e:
            self.send_progress(
                "❌ *Configuration Error*\n\n"
                f"Error: `{str(e)}`\n"
                "_Check file permissions._"
            )
            raise

    @trace()
    def cleanup_temp_folder(self) -> None:
        """
        Cleanup the temporary folder by deleting it and its contents.
        """
        if not os.path.exists(self.temp_dir):
            self.send_progress(
                "ℹ️ *Cleanup Info*\n\n"
                "No temporary files found\n"
                "_Workspace is already clean._"
            )
            return

        try:
            shutil.rmtree(self.temp_dir)
            self.send_progress(
                "🧹 *Cleanup Complete*\n\n"
                "Temporary files removed\n"
                "_Workspace is clean._"
            )
        except Exception as e:
            self.logger.warning(f"Failed to clean up temp directory: {e}")
            self.send_progress(
                "⚠️ *Cleanup Warning*\n\n"
                f"Could not remove all files: {e}\n"
                "_Manual cleanup may be required._"
            )

    @staticmethod
    @trace()
    def clean_filename(topic_title: str, max_length: int = DEFAULT_MAX_FILENAME_LENGTH) -> str:
        """
        Clean and return a valid filename based on the topic title.

        Args:
            topic_title (str): The title to clean.
            max_length (int): Maximum length of the filename.

        Returns:
            str: Cleaned filename.
        """
        clean_title = re.sub(r'[^a-zA-Z0-9_]', '', topic_title.replace(' ', '_'))
        clean_title = clean_title[:max_length]
        return f"{clean_title}.mp4"

    @trace()
    def generate_related_media(
        self,
        phrases: Union[str, List[str]],
        style: StylePreset,
        max_items: int = 1,
        orientation: AspectRatio = AspectRatio.PORTRAIT
    ) -> List[str]:
        """
        Generate images based on the provided phrases (parallelized).

        Args:
            phrases (str or list): Phrases to generate images for.
            style (StylePreset): Style preset for image generation.
            max_items (int): Maximum number of images to generate.
            orientation (AspectRatio): Image orientation.

        Returns:
            list: List of generated image file paths.
        """
        images = []
        phrase_list = [phrases] if isinstance(phrases, str) else phrases
        with ThreadPoolExecutor(max_workers=min(self.parallel_workers, len(phrase_list))) as executor:
            future_map = {}
            for phrase in phrase_list:
                if len(images) >= max_items:
                    break
                future = executor.submit(
                    self._generate_single_image, phrase, style, orientation
                )
                future_map[future] = phrase
            for future in as_completed(future_map):
                try:
                    result = future.result()
                    if result:
                        images.append(result)
                except Exception as e:
                    print(Fore.YELLOW + f"Error generating image: {e}")
        return images[:max_items]

    def _generate_single_image(
        self, phrase: str, style: StylePreset, orientation: AspectRatio
    ) -> Optional[str]:
        """Generate a single image with retry logic and rate limiting."""
        if self._img_rate_limiter:
            self._img_rate_limiter.acquire()
        for attempt in range(3):
            try:
                return self.image_generator.generate_image(
                    custom_prompt=phrase,
                    aspect_ratio=orientation,
                    style_preset=style
                )
            except Exception as e:
                print(f"Error generating image for phrase '{phrase}' (attempt {attempt+1}): {e}")
                if attempt < 2:
                    time.sleep(5)
        return None

    @trace()
    def fetch_related_media(
        self,
        phrases: Union[str, List[str]],
        style: StylePreset = StylePreset.NONE,
        max_items: int = 10,
        orientation: AspectRatio = AspectRatio.PORTRAIT
    ) -> List[str]:
        """
        Fetch related media based on phrases from the specified source.

        Args:
            phrases (str or list): Phrases to fetch media for.
            style (StylePreset): Style preset for image generation.
            max_items (int): Maximum number of media files to fetch.
            orientation (AspectRatio): Image orientation.

        Returns:
            list: List of media file paths.
        """
        media_files = []
        image_source = self.config[CONFIG_SETTINGS]['media_source']
        phrase_list = [phrases] if isinstance(phrases, str) else phrases
        for phrase in phrase_list:
            if image_source == 'huggingface':
                media_files.extend(
                    self.generate_related_media(phrase, style, max_items, orientation)
                )
            elif image_source == 'pexels':
                media_file = self.media_fetcher.fetch_and_save_media(phrase)
                if media_file:
                    media_files.append(media_file)
            if len(media_files) >= max_items:
                break
        return media_files

    @staticmethod
    @trace()
    def get_random_style() -> StylePreset:
        """
        Return a random StylePreset (excluding YOUTUBE_THUMBNAIL and NONE).

        Returns:
            StylePreset: Random style preset.
        """
        presets = [s for s in StylePreset if s not in (StylePreset.YOUTUBE_THUMBNAIL, StylePreset.NONE)]
        return random.choice(presets)

    @trace()
    def process_latest_news_in_short_format(self, forze_topic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process the latest news, generating articles, media, subtitles, and uploading the videos (short format).

        Args:
            forze_topic (dict): News topic to process.

        Returns:
            dict or None: YouTube upload response or None if failed.
        """
        try:
            self.cleanup_temp_folder()
            os.makedirs(self.temp_dir, exist_ok=True)
            latest_news = [forze_topic]

            self.send_progress(
                "🎬 *Starting Video Creation*\n\n"
                "Format: Short-form vertical video\n"
                "_Initializing processing pipeline..._"
            )

            for topic in latest_news:
                if topic.get('title') == '[Removed]':
                    continue

                self.send_progress(
                    "📝 *Content Generation*\n\n"
                    f"Processing Article: `{topic['title'][:50]}...`\n"
                    "_Generating engaging content..._"
                )

                article, phrases, title, description, tags, cover_text, cover_image = \
                    self.article_generator.generate_article_and_phrases_short(topic['title'])

                if not article:
                    self.send_progress(
                        "⚠️ *Generation Failed*\n\n"
                        f"Could not generate content for:\n"
                        f"`{topic['title']}`\n"
                        "_Skipping to next article..._"
                    )
                    continue

                self._generate_and_enhance_thumbnail(cover_image, cover_text, StylePreset.REALISM, Position.BOTTOM_CENTER, Style.THUMBNAIL_BOLD)

                self.send_progress(
                    "🎤 *Audio Generation*\n\n"
                    "Creating professional voiceover\n"
                    "_This may take a few moments..._"
                )

                audio_path = self.tts.text_to_speech_file(
                    article,
                    voice=self.config[CONFIG_TTS_EDGE]['voice'],
                    language=self.config[CONFIG_TTS_EDGE].get('language', 'es')
                )

                
                subtitle_path = os.path.join(self.temp_dir, 'subtitles.srt')

                self.send_progress(
                    "🖼️ *Media Generation*\n\n"
                    f"Creating `{len(phrases)}` visual elements\n"
                    "_Generating engaging visuals..._"
                )

                self.image_generator.model = "black-forest-labs/FLUX.1-schnell"
                random_style = self.get_random_style()
                media_images = self.fetch_related_media(phrases, random_style, len(phrases))

                self.send_progress(
                    "🎥 *Video Assembly*\n\n"
                    "Combining all elements\n"
                    "_Creating final composition..._"
                )

                output_file = os.path.join(self.temp_dir, self.clean_filename(title))
                video_assembler = VideoAssembler(
                    subtitle_file=None,
                    voiceover_file=audio_path,
                    output_file=output_file,
                    media_images=media_images,
                    background_music=self.config[CONFIG_VIDEO_RESULT]['background_music'],
                    aspect_ratio='9:16'
                )
                video_assembler.assemble_video(Style.DEFAULT, position=Position.BOTTOM_CENTER)

                self.send_progress(
                    "📤 *YouTube Upload*\n\n"
                    f"Title: `{title[:50]}...`\n"
                    "_Uploading to your channel..._"
                )

                description += '\n' + topic['title']
                youtube_response = self.youtube_uploader.upload(
                    output_file,
                    title=title[:80],
                    thumbnail_path=self.cover_path,
                    description=description,
                    tags=tags
                )

                self.send_progress(
                    "✨ *Process Complete*\n\n"
                    "Video successfully created and uploaded!\n"
                    "_Check your YouTube channel._"
                )

                return youtube_response
        finally:
            self.cleanup_temp_folder()

    @trace()
    def process_latest_news_in_long_format(self, forze_topic: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process the latest news, generating articles, media, subtitles, and uploading the videos (long format).

        Args:
            forze_topic (dict): News topic to process.

        Returns:
            dict or None: YouTube upload response or None if failed.
        """
        try:
            self.cleanup_temp_folder()
            os.makedirs(self.temp_dir, exist_ok=True)
            latest_news = [forze_topic]
            cover = None

            self.send_progress(
                "🎥 *Starting Long-Form Video*\n\n"
                "Format: Landscape detailed video\n"
                "_Preparing comprehensive content..._"
            )

            for topic in latest_news:
                if topic.get('title') == '[Removed]':
                    continue

                self.send_progress(
                    "📊 *Content Analysis*\n\n"
                    f"Topic: `{topic['title'][:50]}...`\n"
                    "_Analyzing and structuring content..._"
                )

                article, phrases, title, description, tags, cover_text, cover_image = \
                    self.article_generator.generate_article_and_phrases_long(topic['title'])

                if not article:
                    self.send_progress(
                        "⚠️ *Analysis Failed*\n\n"
                        f"Unable to process article:\n"
                        f"`{topic['title']}`\n"
                        "_Moving to next topic..._"
                    )
                    continue

                self._generate_and_enhance_thumbnail(
                    cover_image, 'NEWSPHERE', StylePreset.NONE, Position.TOP_LEFT, Style.THUMBNAIL_CARTOON, orientation=AspectRatio.LANDSCAPE
                )
                self._generate_and_enhance_thumbnail(
                    cover_image, cover_text, StylePreset.NONE, Position.BOTTOM_CENTER, Style.THUMBNAIL_INTENSA, orientation=AspectRatio.LANDSCAPE
                )

                self.send_progress(
                    "🎤 *Audio Production*\n\n"
                    "Creating professional narration\n"
                    "_Generating clear voiceover..._"
                )

                audio_path = self.tts.text_to_speech_file(
                    article,
                    voice=self.config[CONFIG_TTS_EDGE]['voice'],
                    language=self.config[CONFIG_TTS_EDGE].get('language', 'es'),
                    srt_path=os.path.join(self.temp_dir, 'subtitles.srt'),
                )

                subtitle_path = os.path.join(self.temp_dir, 'subtitles.srt')
                processor = SRTProcessor(subtitle_path, max_duration=2.0, max_words=5, pause_threshold=0.3)
                processor.process()

                self.send_progress(
                    "🖼️ *Visual Content*\n\n"
                    f"Generating `{len(phrases)}` visual segments\n"
                    "_Creating professional imagery..._"
                )

                self.image_generator.model = "black-forest-labs/FLUX.1-schnell"
                random_style = self.get_random_style()
                media_images = self.fetch_related_media(phrases, random_style, len(phrases), orientation=AspectRatio.LANDSCAPE)

                self.send_progress(
                    "🎬 *Video Production*\n\n"
                    "Assembling final video\n"
                    "_Combining all elements..._"
                )

                output_file = os.path.join(self.temp_dir, self.clean_filename(title))
                video_assembler = VideoAssembler(
                    subtitle_file=subtitle_path,
                    voiceover_file=audio_path,
                    output_file=output_file,
                    media_images=media_images,
                    background_music=self.config[CONFIG_VIDEO_RESULT]['background_music'],
                    aspect_ratio='16:9'
                )
                video_assembler.assemble_video(Style.FORMAL, position=Position.BOTTOM_CENTER)

                self.send_progress(
                    "📤 *Publishing Content*\n\n"
                    f"Title: `{title[:50]}...`\n"
                    "_Uploading to YouTube..._"
                )

                description += '\n' + topic['title']
                youtube_response = self.youtube_uploader.upload(
                    output_file,
                    title=title[:80],
                    thumbnail_path=self.cover_path,
                    description=description,
                    tags=tags
                )

                self.send_progress(
                    "🌟 *Upload Complete*\n\n"
                    "Long-form video published successfully!\n"
                    "_Your content is now live._"
                )

                return youtube_response
        finally:
            self.cleanup_temp_folder()

    @trace()
    def _generate_and_enhance_thumbnail(
        self,
        cover_image: Union[str, List[str]],
        cover_text: str,
        style: StylePreset,
        position: Position,
        enhancement_style: Style,
        font_size: int = 2000,
        quality: int = 95,
        orientation: AspectRatio = AspectRatio.PORTRAIT
    ) -> None:
        """
        Generate and enhance a thumbnail image.

        Args:
            cover_image (str or list): Cover image prompt(s).
            cover_text (str): Text to overlay on the thumbnail.
            style (StylePreset): Style preset for image generation.
            position (Position): Position for the overlay text.
            enhancement_style (Style): Enhancement style for the thumbnail.
            font_size (int): Font size for the overlay text.
            quality (int): Quality for the output image.
            orientation (AspectRatio): Image orientation.
        """
        self.image_generator.model = "black-forest-labs/FLUX.1-dev"
        images = self.fetch_related_media(
            phrases=cover_image,
            style=style,
            max_items=1,
            orientation=orientation
        )
        if images:
            self.cover_path = images[0]
            ImageHelper.enhance_thumbnail(
                self.cover_path,
                cover_text,
                position,
                enhancement_style,
                font_size,
                quality
            )
