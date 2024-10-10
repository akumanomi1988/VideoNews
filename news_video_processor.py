import shutil
import re
import os
import glob
import json
from colorama import Fore, Style, init
from scripts.AI.natural_language_generation import ArticleGenerator
from scripts.AI.speech_to_text import stt_whisper
from scripts.AI.text_to_speech import TTSEdge
from scripts.AI.text_to_image import FluxImageGenerator, AspectRatio, StylePreset
from scripts.DataFetcher.pexels_media_fetcher import PexelsMediaFetcher
from scripts.DataFetcher.news_api_client import NewsAPIClient
from scripts.MediaManagers.image_manager import ImageManager
from scripts.MediaManagers.video_manager import VideoManager
from scripts.Uploaders.youtube_uploader import YoutubeUploader
from scripts.Uploaders.tiktok_uploader import TikTokVideoUploader
from scripts.video_assembler import VideoAssembler

# Initialize Colorama
init(autoreset=True)

class NewsVideoProcessor:
    def __init__(self, config_file='settings.json', progress_callback=None):
        self.config_file = config_file
        self.config = self.load_configuration()
        self.temp_dir = self.config['settings']['temp_dir']
        self.news_client = NewsAPIClient(api_key=self.config['newsapi']['api_key'])
        self.article_generator = ArticleGenerator(
            language=self.config['article_settings']['language'],
            model=self.config['article_settings']['model'],
            image_model=self.config['article_settings']['image_model']
        )
        self.media_fetcher = PexelsMediaFetcher(api_key=self.config['pexels']['api_key'], temp_dir=self.temp_dir)
        self.stt = stt_whisper()
        self.tts = TTSEdge(output_dir=self.temp_dir)
        self.tiktok_uploader = TikTokVideoUploader(session_id=self.config['tiktok']['session_id'])
        self.image_generator = FluxImageGenerator(token=self.config['huggingface']['api_key'], output_dir=self.temp_dir)
        self.youtube_uploader = YoutubeUploader(client_secrets_file=self.config['youtube']['credentials_file'], channel_description="")
        self.video_files = []
        self.progress_callback = progress_callback

    def send_progress(self, message):
        """Send progress messages via a callback if provided."""
        if self.progress_callback:
            self.progress_callback(message)

    def load_configuration(self):
        """Load the configuration from the specified JSON file."""
        if not os.path.exists(self.config_file):
            print(Fore.YELLOW + "Configuration file not found. Please create one using the configuration editor.")
            return None
        with open(self.config_file, 'r') as file:
            config = json.load(file)
        print(Fore.GREEN + "Configuration loaded successfully.")
        return config

    def process_latest_news_in_short_format(self, forze_topic: str = ""):
        """Process the latest news, generating articles, media, subtitles, and uploading the videos."""
        self.cleanup_temp_folder()
        os.makedirs(self.temp_dir, exist_ok=True)

        latest_news = []  # Inicializar el array

        if forze_topic:
            # Si forze_topic tiene un valor, añadirlo a la lista de noticias
            latest_news.append(forze_topic)  # Cambiado a append para añadir el tópico
        else:
            # Obtener los últimos titulares de noticias
            latest_news = self.news_client.get_latest_headlines(
                country=self.config['newsapi']['country'],
                page_size=self.config['newsapi']['page_size'],
                category=self.config['newsapi']['category']
            )


        cover = None
        self.send_progress("🔄 Starting to process the latest news...")

        for topic in latest_news:
            if topic['title'] == '[Removed]':
                continue
            self.send_progress(f"📰 Processing: {topic['title']}")

            article, phrases, title, description, tags = self.article_generator.generate_article_and_phrases_short(topic['title'])
            if article == "":
                self.send_progress(f"⚠️ Skipped article generation for: {topic['title']}")
                continue

            self.send_progress("🎨 Generating cover image...")

            cover = self.fetch_related_media(phrases=title, style=StylePreset.NONE, max_items=1)[0]

            article += " Suscríbete y dale like para mantenerte informado!."
            self.send_progress("🎤 Generating voiceover...")
            audio_path = self.tts.text_to_speech_file(article)

            self.send_progress("📝 Generating subtitles...")
            subtitle_path = self.stt.generate_word_level_subtitles(audio_path)

            self.send_progress("📹 Fetching related media...")
            media_images = self.fetch_related_media(phrases,StylePreset.NONE,len(phrases))

            output_file = os.path.join(self.temp_dir, self.clean_filename(title))
            background_music = self.config['video_result'].get('background_music')  # Get background music

            video_assembler = VideoAssembler(
                media_videos=[],
                subtitle_file=subtitle_path,
                voiceover_file=audio_path,
                output_file=output_file,
                media_images=media_images
            )

            self.send_progress("🎬 Assembling video...")
            video_assembler.assemble_video()  # Ensure this method correctly handles file closure
            self.video_files.append(output_file)

            self.send_progress("📤 Uploading to YouTube...")
            ImageManager().reduce_image_size(image_path=cover,max_size_kb = 2000,reduction_percentage = 5)
            youtube_response = self.youtube_uploader.upload_short(
                output_file,
                title=title,
                thumbnail_path=cover,
                description=description + '\n' + topic['url'],
                tags=tags
            )

            self.send_progress(f"✅ YouTube upload completed: {youtube_response}")
            return youtube_response
    def process_latest_news_in_long_format(self,forze_topic:str = ""):
        """Process the latest news, generating articles, media, subtitles, and uploading the videos."""
        self.cleanup_temp_folder()
        os.makedirs(self.temp_dir, exist_ok=True)
        if forze_topic != "":
            latest_news.add(topic)
        else:
            # Get the latest news headlines
            latest_news = self.news_client.get_latest_headlines(
                country=self.config['newsapi']['country'],
                page_size=self.config['newsapi']['page_size'],
                category=self.config['newsapi']['category']
            )

        cover = None
        self.send_progress("🔄 Starting to process the latest news...")

        for topic in latest_news:
            if topic['title'] == '[Removed]':
                continue
            self.send_progress(f"📰 Processing: {topic['title']}")

            article, phrases, title, description, tags = self.article_generator.generate_article_and_phrases_short(topic['title'])
            if article == "":
                self.send_progress(f"⚠️ Skipped article generation for: {topic['title']}")
                continue

            self.send_progress("🎨 Generating cover image...")

            cover = self.fetch_related_media(phrases=title, style=StylePreset.NONE, max_items=1)[0]

            article += " Suscríbete y dale like para mantenerte informado!."
            self.send_progress("🎤 Generating voiceover...")
            audio_path = self.tts.text_to_speech_file(article)

            self.send_progress("📝 Generating subtitles...")
            subtitle_path = self.stt.generate_word_level_subtitles(audio_path)

            self.send_progress("📹 Fetching related media...")
            media_images = self.fetch_related_media(phrases,StylePreset.NONE,len(phrases))

            output_file = os.path.join(self.temp_dir, self.clean_filename(title))
            background_music = self.config['video_result'].get('background_music')  # Get background music

            video_assembler = VideoAssembler(
                media_videos=[],
                subtitle_file=subtitle_path,
                voiceover_file=audio_path,
                output_file=output_file,
                media_images=media_images
            )

            self.send_progress("🎬 Assembling video...")
            video_assembler.assemble_video()  # Ensure this method correctly handles file closure
            self.video_files.append(output_file)

            self.send_progress("📤 Uploading to YouTube...")
            youtube_response = self.youtube_uploader.upload_short(
                output_file,
                title=title,
                thumbnail_path=cover,
                description=description + '\n' + topic['url'],
                tags=tags
            )

            self.send_progress(f"✅ YouTube upload completed: {youtube_response}")
            return youtube_response

    def generate_related_media(self, phrases, style: StylePreset, max_items=1):
        """Generate images based on the provided phrases."""
        images = []

        # Asegurarse de que 'phrases' sea una lista, incluso si es un solo string
        if isinstance(phrases, str):
            phrases = [phrases]

        # Generar imágenes para cada frase hasta alcanzar el límite max_items
        for phrase in phrases:
            while len(images) < max_items:
                try:
                    media_file = self.image_generator.generate_image(custom_prompt=phrase, aspect_ratio=AspectRatio.PORTRAIT, style_preset=style)
                    if media_file:
                        images.append(media_file)
                        break  # Salir del while para procesar la siguiente frase
                except Exception as e:
                    print(f"Error generating image for phrase '{phrase}': {e}. Retrying...")

        return images


    def fetch_related_media(self, phrases, style=StylePreset.NONE, max_items=10):
        """Fetch related media based on phrases from the specified source."""
        media_files = []
        image_generator_method = self.config['settings']['media_source']

        # Asegurarse de que 'phrases' sea una lista, incluso si es un solo string
        if isinstance(phrases, str):
            phrases = [phrases]

        for phrase in phrases:
            if image_generator_method == 'huggingface':
                # Llama a 'generate_related_media' correctamente
                media_files.extend(self.generate_related_media(phrase, style, max_items))
            elif image_generator_method == 'pexels':
                # Obtener media de Pexels
                media_file = self.media_fetcher.fetch_and_save_media(phrase)
                if media_file:
                    media_files.append(media_file)

            # Detenerse si ya se ha alcanzado el número máximo de elementos
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

if __name__ == "__main__":
    ImageManager().reduce_image_size(image_path="C:/Users/mozot/source/repos/akumanomi1988/from_news_to_video_uploaded/.temp/NONE_9ce8e642-c477-4b54-b4e9-33c46ef8de1a.png",max_size_kb = 2000,reduction_percentage = 5)
    # processor = NewsVideoProcessor()
    # processor.process_latest_news_in_short_format()
