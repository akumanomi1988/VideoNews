import shutil
import re
import os
import glob
import configparser
from pathlib import Path
from colorama import Fore, Style, init
from scripts.article_generator import ArticleGenerator
from scripts.pexels_media_fetcher import PexelsMediaFetcher
from scripts.subtitle_and_voice import SubtitleAndVoiceGenerator
from scripts.video_assembler import VideoAssembler
from scripts.youtube_uploader import YoutubeUploader
from scripts.news_api_client import NewsAPIClient
from scripts.tts_elevenlabs import TextToSpeech  
from scripts.tiktok_uploader import TikTokUploader
import tkinter as tk
from presentation.config_editor import ConfigEditorApp
# from presentation.config_editor import ConfigEditorApp

# Initialize Colorama
init(autoreset=True)

def main():
    # Step 1: Show Configuration Editor
    # print(Fore.CYAN + "Opening Configuration Editor...")
    # root = tk.Tk()
    # app = ConfigEditorApp(root)
    # root.mainloop()
    
    # Step 2: Load Configuration
    config_file = 'settings.config'
    if not os.path.exists(config_file):
        print(Fore.YELLOW + "Configuration file not found. Please create one using the configuration editor.")
        return
    
    config = load_configuration(config_file)
    print(Fore.GREEN + "Configuration loaded successfully.")

    # Step 3: Initialize Components
    print(Fore.CYAN + "Initializing components...")
    news_client = NewsAPIClient(api_key=config['NewsAPI']['api_key'])
    article_generator = ArticleGenerator(
        language=config['ArticleSettings']['LANGUAGE'],
        model=config['ArticleSettings']['MODEL'],
        image_model=config['ArticleSettings']['IMAGE_MODEL']
    )
    media_fetcher = PexelsMediaFetcher(api_key=config['Pexels']['API_KEY'], temp_dir=config['settings']['temp_dir'])
    video_files = []
    temp_dir = config['settings']['temp_dir']
    
    stt = SubtitleAndVoiceGenerator()
    tts = TextToSpeech(
        api_key=config['ElevenLabs']['API_KEY'],
        model_id=config['ElevenLabs']['MODEL'],
        voice_id=config['ElevenLabs']['VOICE']
    )
    tiktok_uploader = TikTokUploader(session_id=config['tiktok']['session_id'])
    youtube_uploader = YoutubeUploader(client_secrets_file=config['Youtube']['youtube_credentials_file'],
                                channel_description="")

    # Step 4: Process Information
    print(Fore.CYAN + "Processing latest news...")
    #article_generator.generate_cover_image(aspect_ratio='16:9',output_path='.temp\\archivo.jpeg',prompt='Casa en ruinas')
    process_latest_news(news_client, config, article_generator, media_fetcher, video_files, temp_dir, tts, stt,youtube_uploader,tiktok_uploader)

    
def load_configuration(config_file):
    """
    Loads the configuration from the specified config file.

    Parameters:
        config_file (str): Path to the configuration file.

    Returns:
        configparser.ConfigParser: The loaded configuration object.
    """
    config = configparser.ConfigParser()
    config.read(config_file)
    return config

def process_latest_news(news_client: NewsAPIClient,
                        config: configparser.ConfigParser,
                        article_generator: ArticleGenerator,
                        media_fetcher: PexelsMediaFetcher,
                        video_files=[],
                        temp_dir=".temp",
                        tts: TextToSpeech = None,
                        stt: SubtitleAndVoiceGenerator=None,
                        yt_uploader: YoutubeUploader=None,
                        tk_uploader: TikTokUploader=None):
    """
    Processes the latest news, generating articles, media, subtitles, and uploading the videos.

    Parameters:
        news_client (NewsAPIClient): The news API client.
        config (configparser.ConfigParser): The configuration object.
        article_generator (ArticleGenerator): The article generator object.
        media_fetcher (PexelsMediaFetcher): The media fetcher object.
        video_files (list): List to store paths of generated video files.
        temp_dir (str): The directory for temporary files.
        tts (TextToSpeech): The TextToSpeech object for generating audio.
    """
    # media_files = ['.temp\\adjusted_7f66735e-0b60-435c-bf30-99bea6372cdd.mp4','.temp\\adjusted_7f66735e-0b60-435c-bf30-99bea6372cdd.mp4','.temp\\adjusted_7f66735e-0b60-435c-bf30-99bea6372cdd.mp4','.temp\\adjusted_7f66735e-0b60-435c-bf30-99bea6372cdd.mp4']
    # # subtitle_path='.temp\\subtitles.srt'
    # audio_path ='.temp\\43f92bde-e8bc-4618-8557-fd3c1873e80d.mp3'
    # output_file = '.temp\\output.mp4'
    # subtitle_path = stt.generate_word_level_subtitles(audio_path)
    # video_assembler = VideoAssembler(media_files, subtitle_path, audio_path, output_file)
    # video_assembler.assemble_video()

    cleanup_temp_folder()
    #Get latest news headlines
    latest_news = news_client.get_latest_headlines(
        country=config['NewsAPI']['country'],
        page_size=config.getint('NewsAPI', 'page_size'),
        category=config['NewsAPI']['category']
    )
    cover = None
    os.makedirs(temp_dir,exist_ok=True)
    for topic in latest_news:
        print(Fore.MAGENTA + f"Title: {topic['title']}")
        # print(Fore.YELLOW + f"Description: {topic['description']}")
        # print(Fore.BLUE + f"URL: {topic['url']}")
        print(Style.DIM + "-" * 80)
    
        # Generate article and phrases
        
        article, phrases, title, description, tags = article_generator.generate_article_and_phrases_short(topic['title'])
        if article == None:
            continue
        #cover = article_generator.generate_cover_image(title,temp_dir,aspect_ratio=config['VideoResult']['aspect_ratio'])

        # Generate subtitles and voice using TextToSpeech
        audio_path = tts.text_to_speech_file(article, temp_dir)
        subtitle_path = stt.generate_word_level_subtitles(audio_path)

        # Fetch related media
        media_files = fetch_related_media(media_fetcher, phrases)
        if not media_files:
            print(Fore.RED + f"No media found for topic: {topic}")
            continue

        # Assemble video
        output_file = os.path.join(temp_dir, clean_filename(title))
        video_assembler = VideoAssembler(media_files, subtitle_path, audio_path, output_file)
        video_assembler.assemble_video()
        video_files.append(output_file)

        # Upload video to YouTube
        youtube_response = yt_uploader.upload_short(
            output_file,
            title=title,
            thumbnail_path=cover,
            description=description,
            tags=tags
        )
        # tk_uploader.upload_video(
        #     video_path=output_file,
        #     description=description,
        #     tags=tags
        # )
        print(Fore.GREEN + f"YouTube upload response: {youtube_response}")
        return



def fetch_related_media(media_fetcher, phrases, max_items=10):
    """
    Fetches related media for the given phrases using the media fetcher.

    Parameters:
        media_fetcher (PexelsMediaFetcher): The media fetcher object.
        phrases (list): List of phrases to search for media.

    Returns:
        list: List of paths to the fetched media files.
    """
    media_files = []
    for phrase in phrases:
        media_file = media_fetcher.fetch_and_save_media(phrase)
        if media_file:
            media_files.append(media_file)
        if len(media_files) >= max_items:
            break
    return media_files

def cleanup_temp_folder():
    """
    Cleans up the temporary folder and specific files in the root directory.
    """
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
    """
    Cleans the topic title for use as a filename.

    Parameters:
        topic_title (str): The original topic title.
        max_length (int): The maximum length of the filename.

    Returns:
        str: The cleaned filename.
    """
    clean_title = topic_title.replace(' ', '_')
    clean_title = re.sub(r'[^a-zA-Z0-9_]', '', clean_title)
    clean_title = clean_title[:max_length]
    return f"{clean_title}.mp4"

if __name__ == "__main__":
    main()
