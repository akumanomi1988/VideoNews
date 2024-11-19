import shutil
import re
import os
import glob
import json
import time
from colorama import Fore,  init
from telegram import CallbackQuery
from scripts.AI.natural_language_generation import Chatbot
from scripts.AI.speech_to_text import stt_whisper
from scripts.AI.text_to_speech import TTSEdge
from scripts.AI.text_to_image import FluxImageGenerator, AspectRatio, StylePreset
from scripts.DataFetcher.pexels_media_fetcher import PexelsMediaFetcher
from scripts.DataFetcher.news_api_client import NewsAPIClient
from scripts.MediaManagers.media_manager import MediaManager
from scripts.video_assembler import VideoAssembler
from scripts.helpers.media_helper import ImageHelper, Position, Style
from scripts.Uploaders.youtube_uploader import YoutubeMediaUploader
from scripts.Uploaders.tiktok_uploader import TiktokMediaUploader
# from scripts.video_manager import MediaManager  # Asegúrate de que esta importación sea correcta.

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
        self.tts = TTSEdge(output_dir=self.temp_dir)
        self.image_generator = FluxImageGenerator(token=self.config['huggingface']['api_key'], output_dir=self.temp_dir)
        self.youtube_uploader = YoutubeMediaUploader(client_secrets_file=self.config['youtube']['credentials_file'], channel_description="")
        #self.tiktok_uploader = TikTokMediaUploader(app_id=self.config['tiktok']['app_id'],access_token=self.config['tiktok'][''],app_secret="")
        self.video_files = []

    def send_progress(self, message):
        """Send progress messages via a callback if provided."""
        if self.callback_query:
            self.callback_query.message.reply_text(message)

    def load_configuration(self):
        """Load the configuration from the specified JSON file."""
        if not os.path.exists(self.config_file):
            print(Fore.YELLOW + "Configuration file not found. Please create one using the configuration editor.")
            return None
        with open(self.config_file, 'r') as file:
            config = json.load(file)
        print(Fore.GREEN + "Configuration loaded successfully.")
        return config

    def process_latest_news_in_short_format(self, forze_topic: str):
        """Process the latest news, generating articles, media, subtitles, and uploading the videos."""
        self.cleanup_temp_folder()
        os.makedirs(self.temp_dir, exist_ok=True)

        latest_news = []
        latest_news.append(forze_topic)

        cover = None
        self.send_progress("🔄 Starting to process the latest news...")

        for topic in latest_news:
            if topic['title'] == '[Removed]':
                continue
            self.send_progress(f"📰 Processing: {topic['title']}")

            article, phrases, title, description, tags, cover_text,cover_image = self.article_generator.generate_article_and_phrases_short(topic['title'])
            if article == "":
                self.send_progress(f"⚠️ Skipped article generation for: {topic['title']}")
                continue

            self.send_progress("🎨 Generating cover image...")
            self.image_generator.model = "black-forest-labs/FLUX.1-dev"
            cover = self.fetch_related_media(phrases=cover_image, style=StylePreset.REALISM, max_items=1)[0]
            ImageHelper.enhance_thumbnail(cover, cover_text, Position.BOTTOM_CENTER, Style.THUMBNAIL_BOLD, 2000, 95)

            article += " Suscríbete y dale like para mantenerte informado!."
            self.send_progress("🎤 Generating voiceover...")
            audio_path = self.tts.text_to_speech_file(article)

            self.send_progress("📝 Generating subtitles...")
            subtitle_path = self.stt.generate_word_level_subtitles(audio_path)

            self.send_progress("📹 Fetching related media...")
            self.image_generator.model = "black-forest-labs/FLUX.1-schnell"
            media_images = self.fetch_related_media(phrases, StylePreset.NONE, len(phrases))

            output_file = os.path.join(self.temp_dir, self.clean_filename(title))

            video_assembler = VideoAssembler(
                subtitle_file=subtitle_path,
                voiceover_file=audio_path,
                output_file=output_file,
                media_images=media_images,
                background_music=self.config['video_result']['background_music'],
                aspect_ratio='9:16')
            # Using MediaManager to assemble the video
            video_assembler.assemble_video(Style.BOLD,position=Position.MIDDLE_CENTER)

            # # media_manager = MediaManager(
            # #     subtitle_file=subtitle_path,
            # #     voiceover_file=audio_path,
            # #     output_file=f"_{output_file}",
            # #     media_images=media_images,
            # #     aspect_ratio='9:16'  # Usando la relación de aspecto para videos cortos,
            # # #     background_music=self.config['video_result']['background_music']
            # # )

            # # self.send_progress("🎬 Assembling video...")
            # # media_manager.assemble_video()  # Ensure this method correctly handles file closure
            # # self.video_files.append(output_file)

            self.send_progress("📤 Uploading to YouTube...")
            if 'url' in topic and topic['url']:
                description += '\n' + topic['url']

            youtube_response = self.youtube_uploader.upload(                
                output_file,
                title=title,
                thumbnail_path=cover,
                description=description,
                tags=tags
            )
            self.send_progress(f"✅ YouTube upload completed: {youtube_response}")
            self.send_progress("📤 Uploading to TikTok...")
            # self.tiktok_uploader.upload_video(output_file, description, tags)
            self.send_progress(f"✅ TikTok upload completed.")
            return youtube_response

    def process_latest_news_in_long_format(self, forze_topic: str):
        """Process the latest news, generating articles, media, subtitles, and uploading the videos."""
        self.cleanup_temp_folder()
        os.makedirs(self.temp_dir, exist_ok=True)

        latest_news = []
        latest_news.append(forze_topic)

        cover = None
        self.send_progress("🔄 Starting to process the latest news...")

        for topic in latest_news:
            if topic['title'] == '[Removed]':
                continue
            self.send_progress(f"📰 Processing: {topic['title']}")

            article, phrases, title, description, tags, cover_text,cover_image = self.article_generator.generate_article_and_phrases_long(topic['title'])
            if article == "":
                self.send_progress(f"⚠️ Skipped article generation for: {topic['title']}")
                continue

            self.send_progress("🎨 Generating cover image...")
            self.image_generator.model = "black-forest-labs/FLUX.1-dev"
            cover = self.fetch_related_media(phrases=cover_image, style=StylePreset.NONE, max_items=1,orientation=AspectRatio.LANDSCAPE)[0]
            ImageHelper.enhance_thumbnail(cover, cover_text, Position.BOTTOM_CENTER, Style.THUMBNAIL_BOLD, 2000, 95)

            article += " Suscríbete y dale like para mantenerte informado!."
            self.send_progress("🎤 Generating voiceover...")
            audio_path = self.tts.text_to_speech_file(article)

            self.send_progress("📝 Generating subtitles...")
            subtitle_path = self.stt.generate_sentences_subtitles(audio_path)

            self.send_progress("📹 Fetching related media...")
            self.image_generator.model = "black-forest-labs/FLUX.1-schnell"
            media_images = self.fetch_related_media(phrases, StylePreset.NONE, len(phrases),orientation=AspectRatio.LANDSCAPE)

            output_file = os.path.join(self.temp_dir, self.clean_filename(title))
            
            video_assembler = VideoAssembler(
                subtitle_file=subtitle_path,
                voiceover_file=audio_path,
                output_file=output_file,
                media_images=media_images,
                aspect_ratio='16:9')
            # Using MediaManager to assemble the video
            video_assembler.assemble_video(Style.SUBTLE,position=Position.BOTTOM_CENTER)

            # # media_manager = MediaManager(
            # #     subtitle_file=subtitle_path,
            # #     voiceover_file=audio_path,
            # #     output_file=f"_{output_file}",
            # #     media_images=media_images,
            # #     aspect_ratio='9:16'  # Usando la relación de aspecto para videos cortos,
            # # #     background_music=self.config['video_result']['background_music']
            # # )

            # # self.send_progress("🎬 Assembling video...")
            # # media_manager.assemble_video()  # Ensure this method correctly handles file closure
            # # self.video_files.append(output_file)

            self.send_progress("📤 Uploading to YouTube...")
            if 'url' in topic and topic['url']:
                description += '\n' + topic['url']

            youtube_response = self.youtube_uploader.upload(                
                output_file,
                title=title,
                thumbnail_path=cover,
                description=description,
                tags=tags
            )
            self.send_progress(f"✅ YouTube upload completed: {youtube_response}")
            self.send_progress("📤 Uploading to TikTok...")
            # self.tiktok_uploader.upload_video(output_file, description, tags)
            self.send_progress(f"✅ TikTok upload completed.")
            return youtube_response

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

    def cleanup_temp_folder(self):
        """Cleanup the temporary folder by deleting it and its contents."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print(Fore.RED + f"Deleted {self.temp_dir} directory.")
        else:
            print(Fore.YELLOW + f"{self.temp_dir} directory does not exist.")

        for pattern in ['*TEMP_MPY_wvf_snd.mp3.log']:
            for file in glob.glob(pattern):
                try:
                    os.remove(file)
                    print(Fore.RED + f"Deleted file {file}.")
                except Exception as e:
                    print(Fore.RED + f"Error deleting file {file}: {e}")

    def clean_filename(self, topic_title, max_length=30):
        """Clean and return a valid filename based on the topic title."""
        clean_title = topic_title.replace(' ', '_')
        clean_title = re.sub(r'[^a-zA-Z0-9_]', '', clean_title)
        clean_title = clean_title[:max_length]
        return f"{clean_title}.mp4"
