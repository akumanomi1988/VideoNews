import os
import configparser
# from scripts.twitter_trending import get_trending_topics
from scripts.article_generator import ArticleGenerator
from scripts.pexels_media_fetcher import PexelsMediaFetcher
from scripts.subtitle_and_voice import SubtitleAndVoiceGenerator
from scripts.video_assembler import VideoAssembler
# from scripts.video_uploader import VideoUploader
# from scripts.long_video_compiler import LongVideoCompiler
from scripts.news_api_client import NewsAPIClient

def main():
    # Cargar configuración
    config = configparser.ConfigParser()
    config.read('settings.config')

    # youtube_api_key = config['YouTubeAPI']['API_KEY']
    # tiktok_api_key = config['TikTokAPI']['API_KEY']
    
    video_files = []  # Lista para almacenar los archivos de video generados
     # Obtener la clave de API, país y número de noticias desde el archivo de configuración
    news_api_key = config.get('NewsAPI', 'api_key')
    country = config.get('NewsAPI', 'country')
    page_size = config.getint('NewsAPI', 'page_size')  # Obtener como entero

    # Inicializar el cliente de NewsAPI
    news_client = NewsAPIClient(api_key=news_api_key)
    
    # Obtener los titulares de las últimas noticias basados en la configuración
    latest_news = news_client.get_latest_headlines(country=country, page_size=page_size)

    # Procesar las noticias
    for topic in latest_news:
        print(f"Title: {topic['title']}")
        print(f"Description: {topic['description']}")
        print(f"URL: {topic['url']}")
        print("-" * 40)
    
        generator = ArticleGenerator()
        article, phrases = generator.generate_article_and_phrases(topic['title'])

    #     # Obtener medios relacionados
        media_fetcher = PexelsMediaFetcher()
        media_files = []
        for phrase in phrases:
            media_file = media_fetcher.fetch_and_save_media(phrase)
            if media_file:
                media_files.append(media_file)
        
        if not media_files:
            print(f"No media found for topic: {topic}")
            continue

        # Generar subtítulos y voz
        subtitle_and_voice = SubtitleAndVoiceGenerator(article)
        voiceover_file = subtitle_and_voice.generate_voiceover()
        subtitle_file = subtitle_and_voice.generate_subtitles()

    #     # Ensamblar video
        output_file = os.path.join(".temp", f"{topic.replace(' ', '_')}.mp4")
        video_assembler = VideoAssembler(media_files, subtitle_file, voiceover_file, output_file)
        video_assembler.assemble_video()
        
    #     # Agregar el video a la lista de videos
    #     video_files.append(output_file)

    #     # Subir video a YouTube Shorts y TikTok
    #     uploader = VideoUploader(youtube_api_key, tiktok_api_key)
    #     print(f"Uploading video for topic: {topic}")
    #     youtube_response = uploader.upload_to_youtube(output_file, 
    #         title=f"Trending Topic: {topic}",
    #         description=f"Check out the trending topic: {topic}",
    #         tags=[topic]
    #     )
    #     print(f"YouTube upload response: {youtube_response}")

    #     tiktok_response = uploader.upload_to_tiktok(output_file, 
    #         description=f"Trending Topic: {topic} #Trending"
    #     )
    #     print(f"TikTok upload response: {tiktok_response}")

    # # Finalmente, compilar todos los videos en un solo video largo
    # if video_files:
    #     long_video_file = os.path.join(".temp", "Trending_Topics_Compilation.mp4")
    #     long_video_compiler = LongVideoCompiler(video_files, long_video_file)
    #     long_video_compiler.compile_video()

    #     # Subir el video largo a YouTube
    #     print("Uploading long video to YouTube...")
    #     long_video_response = long_video_compiler.upload_to_youtube(
    #         title="Trending Topics Compilation",
    #         description="Compilation of today's trending topics.",
    #         tags=["Trending", "Compilation"]
    #     )
    #     print(f"YouTube long video upload response: {long_video_response}")

if __name__ == "__main__":
    main()
