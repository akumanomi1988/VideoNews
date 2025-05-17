import shutil
import re
import os
import json
import time
import psutil
from colorama import Fore, init
from telegram import CallbackQuery
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

# Initialize Colorama
init(autoreset=True)

class NewsVideoProcessor:
    def __init__(self, config_file='settings.json', callback_query: CallbackQuery = None):
        self.callback_query = callback_query
        self.send_progress("🔄 Loading configuration...")
        self.config_file = config_file
        self.config = self.load_configuration()
        self.temp_dir = self.config['settings']['temp_dir']
        self.news_client = NewsAPIClient(api_key=self.config['newsapi']['api_key'])
        self.article_generator = Chatbot(
            language=self.config['article_settings']['language'],
            model=self.config['article_settings']['model']
        )
        self.media_fetcher = PexelsMediaFetcher(api_key=self.config['pexels']['api_key'], temp_dir=self.temp_dir)
        self.stt = stt_whisper()
        # self.tts = TTSBark(output_dir=self.temp_dir,optimize_for_low_vram=True)
        #self.tts = TTSElevenlabs(credentials_path=self.config['elevenlabs']['credentials_path'], quota_min=100)
        # self.tts = TTSEdge(output_dir=self.temp_dir)
        self.tts = TTSFactory(TTSProvider.EDGE, output_dir=self.temp_dir)
        self.image_generator = FluxImageGenerator(token=self.config['huggingface']['api_key'], output_dir=self.temp_dir)
        self.youtube_uploader = YoutubeMediaUploader(client_secrets_file=self.config['youtube']['credentials_file'], channel_description="")
        # self.tiktok_uploader = TikTokMediaUploader(app_id=self.config['tiktok']['app_id'], access_token=self.config['tiktok'][''], app_secret="")
        self.video_files = []

    def send_progress(self, message):
        """Send progress messages via a callback if provided."""
        if self.callback_query:
            try:
                self.callback_query.message.reply_text(
                    message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                print(Fore.YELLOW + f"Error sending progress message: {str(e)}")
                # Fallback to plain text if Markdown parsing fails
                try:
                    self.callback_query.message.reply_text(message.replace('*', '').replace('_', ''))
                except Exception:
                    print(Fore.RED + "Failed to send message even without Markdown")

    def load_configuration(self):
        """Load the configuration from the specified JSON file."""
        if not os.path.exists(self.config_file):
            error_msg = "⚠️ *Configuration Error*\n\n" \
                        "Configuration file not found.\n" \
                        "_Please use the configuration editor._"
            self.send_progress(error_msg)
            return None
            
        try:
            with open(self.config_file, 'r') as file:
                config = json.load(file)
                success_msg = "✅ *System Ready*\n\n" \
                              "Configuration loaded successfully\n" \
                              "_Starting process..._"
                self.send_progress(success_msg)
                return config
        except json.JSONDecodeError:
            error_msg = "❌ *Invalid Configuration*\n\n" \
                        "The configuration file is corrupted.\n" \
                        "_Please check the JSON format._"
            self.send_progress(error_msg)
            return None
        except Exception as e:
            error_msg = "❌ *Configuration Error*\n\n" \
                        f"Error: `{str(e)}`\n" \
                        "_Check file permissions._"
            self.send_progress(error_msg)
            return None

    def cleanup_temp_folder(self):
        """Cleanup the temporary folder by deleting it and its contents."""
        try:
            if os.path.exists(self.temp_dir):
                try:
                    shutil.rmtree(self.temp_dir)
                    success_msg = "🧹 *Cleanup Complete*\n\n" \
                                  "Temporary files removed\n" \
                                  "_Workspace is clean._"
                    self.send_progress(success_msg)
                except Exception as e:
                    warning_msg = "⚠️ *Cleanup Warning*\n\n" \
                                  "Some files are still in use\n" \
                                  "_Attempting to release locks..._"
                    self.send_progress(warning_msg)
                    self.release_locked_files(self.temp_dir)
            else:
                info_msg = "ℹ️ *Cleanup Info*\n\n" \
                           "No temporary files found\n" \
                           "_Workspace is already clean._"
                self.send_progress(info_msg)
        except Exception as e:
            error_msg = "⚠️ *Cleanup Error*\n\n" \
                        f"Error: `{str(e)}`\n" \
                        "_Some files may remain._"
            self.send_progress(error_msg)
            
    def release_locked_files(self, directory):
        """Release locked files in the specified directory."""
        for proc in psutil.process_iter(['pid', 'open_files']):
            try:
                for open_file in proc.info['open_files']:
                    if open_file.path.startswith(directory):
                        print(Fore.YELLOW + f"Killing process {proc.info['pid']} holding file {open_file.path}")
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        try:
            shutil.rmtree(directory)
            print(Fore.RED + f"Deleted {directory} after releasing locks.")
        except Exception as e:
            print(Fore.YELLOW + f"Could not delete {directory} even after releasing locks: {e}.")

    def clean_filename(self, topic_title, max_length=30):
        """Clean and return a valid filename based on the topic title."""
        clean_title = topic_title.replace(' ', '_')
        clean_title = re.sub(r'[^a-zA-Z0-9_]', '', clean_title)
        clean_title = clean_title[:max_length]
        return f"{clean_title}.mp4"

    def generate_related_media(self, phrases, style: StylePreset, max_items=1, orientation: AspectRatio = AspectRatio.PORTRAIT):
        """Generate images based on the provided phrases."""
        images = []
        if isinstance(phrases, str):
            phrases = [phrases]
        for phrase in phrases:
            while len(images) < max_items:
                try:
                    media_file = self.image_generator.generate_image(custom_prompt=phrase, aspect_ratio=orientation, style_preset=style)
                    if media_file:
                        images.append(media_file)
                        break
                except Exception as e:
                    print(f"Error generating image for phrase '{phrase}': {e}. Retrying...")
                    time.sleep(60)
        return images

    def fetch_related_media(self, phrases, style=StylePreset.NONE, max_items=10, orientation: AspectRatio = AspectRatio.PORTRAIT):
        """Fetch related media based on phrases from the specified source."""
        media_files = []
        image_generator_method = self.config['settings']['media_source']
        if isinstance(phrases, str):
            phrases = [phrases]
        for phrase in phrases:
            if image_generator_method == 'huggingface':
                media_files.extend(self.generate_related_media(phrase, style, max_items, orientation))
            elif image_generator_method == 'pexels':
                media_file = self.media_fetcher.fetch_and_save_media(phrase)
                if media_file:
                    media_files.append(media_file)
            if len(media_files) >= max_items:
                break
        return media_files

    def process_latest_news_in_short_format(self, forze_topic: dict):
        """Process the latest news, generating articles, media, subtitles, and uploading the videos."""
        try:
            self.cleanup_temp_folder()
            os.makedirs(self.temp_dir, exist_ok=True)
            latest_news = [forze_topic]
            cover = None
            
            self.send_progress(
                "🎬 *Starting Video Creation*\n\n"
                "Format: Short-form vertical video\n"
                "_Initializing processing pipeline..._"
            )
            
            for topic in latest_news:
                if topic['title'] == '[Removed]':
                    continue
                    
                self.send_progress(
                    "📝 *Content Generation*\n\n"
                    f"Processing Article: `{topic['title'][:50]}...`\n"
                    "_Generating engaging content..._"
                )
                
                article, phrases, title, description, tags, cover_text, cover_image = self.article_generator.generate_article_and_phrases_short(topic['title'])
                
                if article == "":
                    self.send_progress(
                        "⚠️ *Generation Failed*\n\n"
                        f"Could not generate content for:\n"
                        f"`{topic['title']}`\n"
                        "_Skipping to next article..._"
                    )
                    continue
                    
                self.send_progress(
                    "🎨 *Creating Thumbnail*\n\n"
                    "Style: `Realistic Design`\n"
                    "_Generating eye-catching cover..._"
                )
                
                self.image_generator.model = "black-forest-labs/FLUX.1-dev"
                cover = self.fetch_related_media(phrases=cover_image, style=StylePreset.REALISM, max_items=1)[0]
                ImageHelper.enhance_thumbnail(cover, cover_text, Position.BOTTOM_CENTER, Style.THUMBNAIL_BOLD, 2000, 95)
                
                self.send_progress(
                    "🎤 *Audio Generation*\n\n"
                    "Creating professional voiceover\n"
                    "_This may take a few moments..._"
                )
                
                audio_path = self.tts.text_to_speech_file(
                    article,
                    voice=self.config['tts_edge']['voice'],
                    language=self.config['tts_edge']['language'],
                    srt_path=self.temp_dir + '/subtitles.srt'
                )
                
                self.send_progress(
                    "📝 *Subtitle Generation*\n\n"
                    "Creating synchronized captions\n"
                    "_Formatting for maximum engagement..._"
                )
                
                subtitle_path = self.temp_dir + '/subtitles.srt'
                
                self.send_progress(
                    "🖼️ *Media Generation*\n\n"
                    f"Creating `{len(phrases)}` visual elements\n"
                    "_Generating engaging visuals..._"
                )
                
                self.image_generator.model = "black-forest-labs/FLUX.1-schnell"
                media_images = self.fetch_related_media(phrases, StylePreset.NONE, len(phrases))
                
                self.send_progress(
                    "🎥 *Video Assembly*\n\n"
                    "Combining all elements\n"
                    "_Creating final composition..._"
                )
                
                output_file = os.path.join(self.temp_dir, self.clean_filename(title))
                video_assembler = VideoAssembler(
                    subtitle_file=subtitle_path,
                    voiceover_file=audio_path,
                    output_file=output_file,
                    media_images=media_images,
                    background_music=self.config['video_result']['background_music'],
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
                    thumbnail_path=cover,
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

    def process_latest_news_in_long_format(self, forze_topic: dict):
        """Process the latest news, generating articles, media, subtitles, and uploading the videos."""
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
                if topic['title'] == '[Removed]':
                    continue
                    
                self.send_progress(
                    "📊 *Content Analysis*\n\n"
                    f"Topic: `{topic['title'][:50]}...`\n"
                    "_Analyzing and structuring content..._"
                )
                
                article, phrases, title, description, tags, cover_text, cover_image = self.article_generator.generate_article_and_phrases_long(topic['title'])
                
                if article == "":
                    self.send_progress(
                        "⚠️ *Analysis Failed*\n\n"
                        f"Unable to process article:\n"
                        f"`{topic['title']}`\n"
                        "_Moving to next topic..._"
                    )
                    continue
                    
                self.send_progress(
                    "🎨 *Thumbnail Design*\n\n"
                    "Creating professional thumbnail\n"
                    "_Applying custom branding..._"
                )
                
                self.image_generator.model = "black-forest-labs/FLUX.1-dev"
                cover = self.fetch_related_media(phrases=cover_image, style=StylePreset.NONE, max_items=1, orientation=AspectRatio.LANDSCAPE)[0]
                ImageHelper.enhance_thumbnail(cover, 'NEWSPHERE', Position.TOP_LEFT, Style.THUMBNAIL_CARTOON, 2000, 95)
                ImageHelper.enhance_thumbnail(cover, cover_text, Position.BOTTOM_CENTER, Style.THUMBNAIL_INTENSA, 2000, 95)
                
                self.send_progress(
                    "🎤 *Audio Production*\n\n"
                    "Creating professional narration\n"
                    "_Generating clear voiceover..._"
                )
                
                audio_path = self.tts.text_to_speech_file(
                    article,
                    voice=self.config['tts_edge']['voice'],
                    language=self.config['tts_edge']['language'],
                    srt_path=self.temp_dir + '/subtitles.srt'
                )
                
                self.send_progress(
                    "📝 *Caption Generation*\n\n"
                    "Creating timed subtitles\n"
                    "_Optimizing for readability..._"
                )
                
                subtitle_path = self.temp_dir + '/subtitles.srt'
                processor = SRTProcessor(subtitle_path, max_duration=2.0, max_words=5, pause_threshold=0.3)
                processor.process()
                
                self.send_progress(
                    "🖼️ *Visual Content*\n\n"
                    f"Generating `{len(phrases)}` visual segments\n"
                    "_Creating professional imagery..._"
                )
                
                self.image_generator.model = "black-forest-labs/FLUX.1-schnell"
                media_images = self.fetch_related_media(phrases, StylePreset.NONE, len(phrases), orientation=AspectRatio.LANDSCAPE)
                
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
                    background_music=self.config['video_result']['background_music'],
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
                    thumbnail_path=cover,
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