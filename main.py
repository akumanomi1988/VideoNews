import shutil
import re
import os
import glob
import json
from colorama import Fore, Style, init
from scripts.IA.natural_language_generation import ArticleGenerator
from scripts.IA.speech_to_text import stt_whisper
from scripts.IA.text_to_speech import TTSEdge
from scripts.IA.text_to_image import FluxImageGenerator, AspectRatio, StylePreset
from scripts.DataFetcher.pexels_media_fetcher import PexelsMediaFetcher
from scripts.DataFetcher.news_api_client import NewsAPIClient
from scripts.Uploaders.youtube_uploader import YoutubeUploader
from scripts.Uploaders.tiktok_uploader import TikTokVideoUploader
from scripts.video_assembler import VideoAssembler

# Initialize Colorama
init(autoreset=True)

def main():
    config_file = 'settings.json'
    if not os.path.exists(config_file):
        print(Fore.YELLOW + "Configuration file not found. Please create one using the configuration editor.")
        return
    
    config = load_configuration(config_file)
    print(Fore.GREEN + "Configuration loaded successfully.")

    print(Fore.CYAN + "Initializing components...")
    temp_dir = config['settings']['temp_dir']
    news_client = NewsAPIClient(api_key=config['newsapi']['api_key'])
    article_generator = ArticleGenerator(
        language=config['article_settings']['language'],
        model=config['article_settings']['model'],
        image_model=config['article_settings']['image_model']
    )
    media_fetcher = PexelsMediaFetcher(api_key=config['pexels']['api_key'], temp_dir=temp_dir)
    video_files = []
    stt = stt_whisper()
    
    tts = TTSEdge(output_dir=temp_dir)
    
    tiktok_uploader = TikTokVideoUploader(session_id=config['tiktok']['session_id'])
    image_generator = FluxImageGenerator(token=config['huggingface']['api_key'], output_dir=temp_dir)
    youtube_uploader = YoutubeUploader(client_secrets_file=config['youtube']['credentials_file'],
                                channel_description="")
    
    print(Fore.CYAN + "Processing latest news...")
    process_latest_news(news_client, config, article_generator, media_fetcher, video_files, temp_dir, tts, stt, youtube_uploader, tiktok_uploader, image_generator)

def load_configuration(config_file):
    """
    Loads the configuration from the specified JSON config file.

    Parameters:
        config_file (str): Path to the configuration file.

    Returns:
        dict: The loaded configuration object.
    """
    with open(config_file, 'r') as file:
        config = json.load(file)
    return config

def process_latest_news(news_client: NewsAPIClient,
                        config: dict,
                        article_generator: ArticleGenerator,
                        media_fetcher: PexelsMediaFetcher,
                        video_files=[],
                        temp_dir=".temp",
                        tts: TTSEdge = None,
                        stt: stt_whisper = None,
                        yt_uploader: YoutubeUploader = None,
                        tk_uploader: TikTokVideoUploader = None,
                        image_generator: FluxImageGenerator = None):
    """
    Processes the latest news, generating articles, media, subtitles, and uploading the videos.

    Parameters:
        news_client (NewsAPIClient): The news API client.
        config (dict): The configuration object.
        article_generator (ArticleGenerator): The article generator object.
        media_fetcher (PexelsMediaFetcher): The media fetcher object.
        video_files (list): List to store paths of generated video files.
        temp_dir (str): The directory for temporary files.
        tts (TextToSpeech): The TextToSpeech object for generating audio.
    """

    cleanup_temp_folder()

    # Get latest news headlines
    latest_news = news_client.get_latest_headlines(
        country=config['newsapi']['country'],
        page_size=config['newsapi']['page_size'],
        category=config['newsapi']['category']
    )
    
    cover = None
    os.makedirs(temp_dir, exist_ok=True)
    
    for topic in latest_news:
        print(Fore.MAGENTA + f"Title: {topic['title']}")
        print(Fore.BLUE + f"URL: {topic['url']}")
        print(Style.DIM + "-" * 80)

        # Generate article and phrases
        article, phrases, title, description, tags = article_generator.generate_article_and_phrases_short(topic['title'])

        if article == "":
            continue
        cover = generate_related_media(image_generator, phrases=title, style=StylePreset.YOUTUBE_THUMBNAIL, max_items=1)[0]

        # Generate subtitles and voice using TextToSpeech
        article = article + " Suscríbete y dale like para mantenerte informado!."
        audio_path = tts.text_to_speech_file(article)
        subtitle_path = stt.generate_word_level_subtitles(audio_path)

        # Fetch related media
        media_files = None
        media_images = None
        image_generator_method = config['settings']['media_source']
        if image_generator_method == 'huggingface':
            media_images = generate_related_media(image_generator, phrases=phrases, style=StylePreset.PHOTOREALISTIC, max_items=len(phrases))
            if not media_images:
                print(Fore.RED + f"No media generated for topic: {topic}")
                continue
        elif image_generator_method == 'pexels':
            media_files = fetch_related_media(media_fetcher, phrases)
            if not media_files:
                print(Fore.RED + f"No media found for topic: {topic}")
                continue

        # Assemble video
        output_file = os.path.join(temp_dir, clean_filename(title))
        video_assembler = VideoAssembler(media_videos=media_files, subtitle_file=subtitle_path, voiceover_file=audio_path, output_file=output_file, media_images=media_images)
        video_assembler.assemble_video()
        video_files.append(output_file)

        # Upload video to YouTube
        youtube_response = yt_uploader.upload_short(
            output_file,
            title=title,
            thumbnail_path=cover,
            description=description + '\n' + topic['url'],
            tags=tags
        )

        print(Fore.GREEN + f"YouTube upload response: {youtube_response}")
        return

def generate_related_media(image_generator: FluxImageGenerator, phrases, style: StylePreset, max_items=10):
    images = []
    for phrase in phrases:
        while len(images) < max_items:
            try:
                media_file = image_generator.generate_image(custom_prompt=phrase, aspect_ratio=AspectRatio.PORTRAIT, style_preset=style)
                if media_file:
                    images.append(media_file)
                    break
            except Exception as e:
                print(f"Error generating image for phrase '{phrase}': {e}. Retrying...")
    return images

def fetch_related_media(media_fetcher, phrases, max_items=10):
    media_files = []
    for phrase in phrases:
        media_file = media_fetcher.fetch_and_save_media(phrase)
        if media_file:
            media_files.append(media_file)
        if len(media_files) >= max_items:
            break
    return media_files

def cleanup_temp_folder():
    temp_folder = ".temp"
    if os.path.exists(temp_folder):
        shutil.rmtree(temp_folder)
        print(Fore.RED + f"Deleted {temp_folder} directory.")
    else:
        print(Fore.YELLOW + f"{temp_folder} directory does not exist.")

    pattern = '*TEMP_MPY_wvf_snd.mp3'
    files_to_delete = glob.glob(pattern)
    for file in files_to_delete:
        try:
            os.remove(file)
            print(Fore.RED + f"Deleted file {file}.")
        except Exception as e:
            print(Fore.RED + f"Error deleting file {file}: {e}")
    
    pattern = '*TEMP_MPY_wvf_snd.log'
    files_to_delete = glob.glob(pattern)
    for file in files_to_delete:
        try:
            os.remove(file)
            print(Fore.RED + f"Deleted file {file}.")
        except Exception as e:
            print(Fore.RED + f"Error deleting file {file}: {e}")

def clean_filename(topic_title, max_length=30):
    clean_title = topic_title.replace(' ', '_')
    clean_title = re.sub(r'[^a-zA-Z0-9_]', '', clean_title)
    clean_title = clean_title[:max_length]
    return f"{clean_title}.mp4"

if __name__ == "__main__":
    main()
