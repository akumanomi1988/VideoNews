import os
import re
import json
import time
import uuid
import shutil
import random
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple, Union

from colorama import Fore, init
from telegram import Bot, CallbackQuery, Message
from scripts.AI.natural_language_generation import Chatbot
from scripts.AI.speech_to_text import stt_whisper
from scripts.AI.text_to_speech import TTSFactory, TTSProvider
from scripts.AI.text_to_image import FluxImageGenerator, AspectRatio, StylePreset
from scripts.DataFetcher.pexels_media_fetcher import PexelsMediaFetcher
from scripts.DataFetcher.serpapi_client import SerpAPIProvider
from scripts.MediaManagers.SRT_Processor import SRTProcessor
from scripts.video_assembler import VideoAssembler
from scripts.helpers.media_helper import ImageHelper, Position, Style
from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader
from scripts.utils.app_logger import trace
from scripts.utils.rate_limiter import RateLimiter

# Initialize Colorama
init(autoreset=True)

# Constants for configuration keys
CONFIG_ARTICLE_SETTINGS = 'article_settings'
CONFIG_SERPAPI = 'serpapi'
CONFIG_PEXELS = 'pexels'
CONFIG_HUGGINGFACE = 'huggingface'
CONFIG_YOUTUBE = 'youtube'
CONFIG_TTS_EDGE = 'tts_edge'
CONFIG_VIDEO_RESULT = 'video_result'
CONFIG_SETTINGS = 'settings'

DEFAULT_CONFIG_FILE = 'settings.json'
DEFAULT_MAX_FILENAME_LENGTH = 30


class NewsVideoProcessor:
    """
    Main processor for generating news videos from articles.
    Handles configuration, media generation, video assembly, and uploading.
    """

    @trace()
    def __init__(
        self,
        config_file: str = DEFAULT_CONFIG_FILE,
        callback_query: Optional[Union[CallbackQuery, Message]] = None,
        event_loop: Optional[asyncio.AbstractEventLoop] = None,
        bot: Optional[Bot] = None,
    ):
        self.callback_query = callback_query
        self._event_loop = event_loop
        self._bot = bot
        if not self._bot and callback_query is not None:
            try:
                self._bot = callback_query.get_bot() if hasattr(callback_query, 'get_bot') else None
            except Exception:
                self._bot = None
        self.config_file = config_file
        self.config = self._load_configuration()
        self.temp_dir = self.config[CONFIG_SETTINGS]['temp_dir']
        self.parallel_workers = self.config[CONFIG_SETTINGS].get('parallel_workers', 6)
        images_per_minute = self.config[CONFIG_SETTINGS].get('images_per_minute', 20)
        self._img_rate_limiter = RateLimiter(images_per_minute, 60.0) if images_per_minute and images_per_minute > 0 else None
        serpapi_cfg = self.config[CONFIG_SERPAPI]
        self.news_client = SerpAPIProvider(
            api_key=serpapi_cfg['api_key'],
            use_cache=serpapi_cfg.get('use_cache', True),
            cache_ttl_hours=serpapi_cfg.get('cache_ttl_hours', 24),
            cache_dir=serpapi_cfg.get('cache_dir', '.temp/cache/serpapi'),
        )
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
        self.cover_path: Optional[str] = None

    @trace()
    def send_progress(self, message_text: str) -> None:
        if not self._bot or not self._event_loop:
            return
        msg_obj = getattr(self.callback_query, "message", self.callback_query)
        chat_id = None
        if msg_obj:
            chat_id = getattr(msg_obj, "chat_id", None) or getattr(getattr(msg_obj, "chat", None), "id", None)
        if not chat_id:
            return
        loop = self._event_loop
        if loop.is_closed():
            return
        text = message_text
        try:
            asyncio.run_coroutine_threadsafe(
                self._bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown"),
                loop,
            )
        except Exception as e:
            self.logger.warning("Error sending progress message: %s", e)
            try:
                asyncio.run_coroutine_threadsafe(
                    self._bot.send_message(chat_id=chat_id, text=text.replace("*", "").replace("_", "")),
                    loop,
                )
            except Exception as ex:
                self.logger.warning("Failed to send message even without Markdown: %s", ex)

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
        except json.JSONDecodeError:
            self.send_progress(
                "❌ *Invalid Configuration*\n\n"
                "The configuration file is corrupted.\n"
                "_Please check the JSON format._"
            )
            raise

        missing = []
        checks = {
            CONFIG_SETTINGS: ['temp_dir'],
            CONFIG_SERPAPI: ['api_key'],
            CONFIG_PEXELS: ['api_key'],
            CONFIG_HUGGINGFACE: ['api_key'],
            CONFIG_YOUTUBE: ['credentials_file'],
            CONFIG_ARTICLE_SETTINGS: ['language', 'model'],
        }
        for section, keys in checks.items():
            s = config.get(section, {})
            for k in keys:
                if not s.get(k):
                    missing.append(f"{section}.{k}")
        if missing:
            raise ValueError(
                f"Missing required configuration keys: {', '.join(missing)}. "
                f"Check settings.json."
            )

        self.send_progress(
            "✅ *System Ready*\n\n"
            "Configuration loaded successfully\n"
            "_Starting process..._"
        )
        return config

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

    def _write_state(self, step: str, **extra) -> None:
        state = {"step": step, "timestamp": time.time(), **extra}
        try:
            path = os.path.join(self.temp_dir, "process_state.json")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.warning(f"Failed to write process state: {e}")

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
        if not clean_title:
            clean_title = f"news_{uuid.uuid4().hex[:8]}"
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
        with ThreadPoolExecutor(max_workers=min(self.parallel_workers, max(len(phrase_list), 1))) as executor:
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
                    result = future.result(timeout=120)
                    if result:
                        images.append(result)
                except Exception as e:
                    phrase_snippet = future_map.get(future, '')[:50]
                    self.logger.warning("Error generating image for phrase '%s': %s", phrase_snippet, e)
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
                self.logger.warning("Error generating image for phrase '%s' (attempt %d): %s", phrase, attempt + 1, e)
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
        media_files = []
        image_source = self.config[CONFIG_SETTINGS].get('media_source', 'huggingface')
        phrase_list = [phrases] if isinstance(phrases, str) else phrases
        for phrase in phrase_list:
            generated = False
            if image_source == 'huggingface':
                result = self.generate_related_media(phrase, style, max_items, orientation)
                if result:
                    media_files.extend(result)
                    generated = True
                    self.logger.debug("Generated %d images from HuggingFace for phrase '%s'", len(result), phrase[:50])
                else:
                    self.logger.warning("HuggingFace returned no images for phrase '%s', trying Pexels fallback", phrase[:50])
            if not generated:
                pexels_file = None
                try:
                    pexels_file = self.media_fetcher.fetch_and_save_media(phrase, media_type="photo")
                except Exception as e:
                    self.logger.warning("Pexels fallback failed for phrase '%s': %s", phrase[:50], e)
                if pexels_file:
                    media_files.append(pexels_file)
                    self.logger.debug("Fetched media from Pexels for phrase '%s'", phrase[:50])
                else:
                    placeholder = self._generate_placeholder_image(self.temp_dir, phrase, orientation)
                    if placeholder:
                        media_files.append(placeholder)
                        self.logger.warning("Using placeholder image for phrase '%s'", phrase[:50])
            if len(media_files) >= max_items:
                break
        return media_files[:max_items]

    @trace()
    @staticmethod
    def _generate_placeholder_image(output_dir: str, text: str = "News", orientation: AspectRatio = AspectRatio.PORTRAIT) -> Optional[str]:
        try:
            from PIL import Image, ImageDraw, ImageFont
            import uuid
            w, h = (1080, 1920) if orientation == AspectRatio.PORTRAIT else (1920, 1080)
            img = Image.new("RGB", (w, h), (30, 30, 50))
            draw = ImageDraw.Draw(img)
            _text = text[:50] if text else "News"
            font = None
            for fp in [
                r"C:\Windows\Fonts\Arial.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            ]:
                if os.path.exists(fp):
                    font = ImageFont.truetype(fp, 48)
                    break
            bbox = draw.textbbox((0, 0), _text, font=font) if font else (0, 0, 200, 30)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.text(((w - tw) / 2, (h - th) / 2), _text, fill=(200, 200, 255), font=font)
            out = os.path.join(output_dir, f"placeholder_{uuid.uuid4().hex[:8]}.png")
            os.makedirs(output_dir, exist_ok=True)
            img.save(out)
            return out
        except Exception as e:
            logging.getLogger(__name__).warning("Failed to generate placeholder image: %s", e)
            return None

    @staticmethod
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
                    self.article_generator.generate_article_and_phrases_short(topic)

                if not article:
                    self.send_progress(
                        "⚠️ *Generation Failed*\n\n"
                        f"Could not generate content for:\n"
                        f"`{topic['title']}`\n"
                        "_Skipping to next article..._"
                    )
                    continue

                self._write_state("article_ready", title=title, phrases=len(phrases))
                self._generate_and_enhance_thumbnail(
                    cover_image, cover_text,
                    StylePreset.REALISM,
                    Position.BOTTOM_CENTER,
                    Style.THUMBNAIL_BOLD,
                    orientation=AspectRatio.SHORTS,
                    target_size=(1080, 1920),
                )

                self.send_progress(
                    "🎤 *Audio Generation*\n\n"
                    "Creating professional voiceover\n"
                    "_This may take a few moments..._"
                )

                subtitle_path = os.path.join(self.temp_dir, 'subtitles.srt')
                audio_path = self.tts.text_to_speech_file(
                    article,
                    voice=self.config[CONFIG_TTS_EDGE]['voice'],
                    language=self.config[CONFIG_TTS_EDGE].get('language', 'es'),
                    srt_path=subtitle_path,
                    rate=self.config[CONFIG_TTS_EDGE].get('speech_rate_adjustment', 0),
                    pitch=self.config[CONFIG_TTS_EDGE].get('pitch_adjustment', 0),
                )

                self._write_state("audio_ready", subtitle_path=subtitle_path, audio_path=audio_path)

                self.send_progress(
                    "🖼️ *Media Generation*\n\n"
                    f"Creating `{len(phrases)}` visual elements\n"
                    "_Generating engaging visuals..._"
                )

                self.image_generator.model = "black-forest-labs/FLUX.1-schnell"
                style_name = topic.get('style')
                if style_name:
                    random_style = StylePreset[style_name]
                else:
                    random_style = self.get_random_style()
                media_images = self.fetch_related_media(phrases, random_style, len(phrases))

                self._write_state("media_ready", image_count=len(media_images))

                self.send_progress(
                    "🎥 *Video Assembly*\n\n"
                    "Combining all elements\n"
                    "_Creating final composition..._"
                )

                output_file = os.path.join(self.temp_dir, self.clean_filename(title))
                video_assembler = VideoAssembler(
                    subtitle_file=subtitle_path if os.path.exists(subtitle_path) else None,
                    voiceover_file=audio_path,
                    output_file=output_file,
                    media_images=media_images,
                    background_music=self.config.get(CONFIG_VIDEO_RESULT, {}).get('background_music', ''),
                    aspect_ratio='9:16'
                )
                video_assembler.assemble_video(Style.DEFAULT, position=Position.BOTTOM_CENTER)

                self._write_state("video_ready", output_file=output_file)

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

                self._write_state("complete")
                self.cleanup_temp_folder()
                return youtube_response
        except Exception as e:
            self.logger.error(f"Short format processing failed: {e}")
            self.send_progress(f"❌ *Process Failed*\n\nError: `{str(e)}`")
            self.logger.warning(f"Temp files preserved in {self.temp_dir!r} for analysis")
            return None

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

                self._write_state("article_ready", title=title, phrases=len(phrases))

                # Generate ONE cover image and overlay both texts
                self.image_generator.model = "black-forest-labs/FLUX.1-dev"
                _thumbs = self.fetch_related_media(phrases=cover_image, style=StylePreset.NONE, max_items=1, orientation=AspectRatio.LANDSCAPE)
                if not _thumbs:
                    _placeholder = self._generate_placeholder_image(self.temp_dir, title, AspectRatio.LANDSCAPE)
                    if _placeholder:
                        _thumbs = [_placeholder]
                if _thumbs:
                    self.cover_path = _thumbs[0]
                    ImageHelper.enhance_thumbnail(self.cover_path, 'NEWSPHERE', Position.TOP_LEFT, Style.THUMBNAIL_CARTOON)
                    ImageHelper.enhance_thumbnail(self.cover_path, cover_text or title, Position.BOTTOM_CENTER, Style.THUMBNAIL_INTENSA)
                else:
                    self.cover_path = None

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
                    rate=self.config[CONFIG_TTS_EDGE].get('speech_rate_adjustment', 0),
                    pitch=self.config[CONFIG_TTS_EDGE].get('pitch_adjustment', 0),
                    boundary_type="WordBoundary",
                )

                subtitle_path = os.path.join(self.temp_dir, 'subtitles.srt')
                processor = SRTProcessor(subtitle_path, max_duration=4.0, max_words=8, pause_threshold=0.3)
                processor.process()

                self._write_state("audio_ready", subtitle_path=subtitle_path, audio_path=audio_path)

                self.send_progress(
                    "🖼️ *Visual Content*\n\n"
                    f"Generating `{len(phrases)}` visual segments\n"
                    "_Creating professional imagery..._"
                )

                self.image_generator.model = "black-forest-labs/FLUX.1-schnell"
                style_name = topic.get('style')
                if style_name:
                    random_style = StylePreset[style_name]
                else:
                    random_style = self.get_random_style()
                media_images = self.fetch_related_media(phrases, random_style, len(phrases), orientation=AspectRatio.LANDSCAPE)

                self._write_state("media_ready", image_count=len(media_images))

                self.send_progress(
                    "🎬 *Video Production*\n\n"
                    "Assembling final video\n"
                    "_Combining all elements..._"
                )

                output_file = os.path.join(self.temp_dir, self.clean_filename(title))
                video_assembler = VideoAssembler(
                    subtitle_file=subtitle_path if os.path.exists(subtitle_path) else None,
                    voiceover_file=audio_path,
                    output_file=output_file,
                    media_images=media_images,
                    background_music=self.config.get(CONFIG_VIDEO_RESULT, {}).get('background_music', ''),
                    aspect_ratio='16:9'
                )
                video_assembler.assemble_video(Style.FORMAL, position=Position.BOTTOM_CENTER)

                self._write_state("video_ready", output_file=output_file)

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

                self._write_state("complete")
                self.cleanup_temp_folder()
                return youtube_response
        except Exception as e:
            self.logger.error(f"Long format processing failed: {e}")
            self.send_progress(f"❌ *Process Failed*\n\nError: `{str(e)}`")
            self.logger.warning(f"Temp files preserved in {self.temp_dir!r} for analysis")
            return None

    @trace()
    def _generate_and_enhance_thumbnail(
        self,
        cover_image: Union[str, List[str]],
        cover_text: str,
        style: StylePreset,
        position: Position,
        enhancement_style: Style,
        font_size: int = 0,
        quality: int = 95,
        orientation: AspectRatio = AspectRatio.PORTRAIT,
        target_size: Optional[Tuple[int, int]] = None
    ) -> None:
        self.cover_path = None
        prev_model = self.image_generator.model
        self.image_generator.model = "black-forest-labs/FLUX.1-dev"
        try:
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
                    text_size=font_size,
                    target_size=target_size,
                )
        finally:
            self.image_generator.model = prev_model
