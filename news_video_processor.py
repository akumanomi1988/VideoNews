import logging
from typing import Dict, Optional
from telegram import CallbackQuery
from colorama import init

from scripts.factory import PipelineFactory
from scripts.pipeline import VideoProcessingError

# Initialize Colorama
init(autoreset=True)

class NewsVideoProcessor:
    """Main entry point for video processing with Telegram integration"""
    
    def __init__(self, config_file='pipeline_config.json', callback_query: Optional[CallbackQuery] = None):
        self.logger = logging.getLogger(__name__)
        self.callback_query = callback_query
        self.config_file = config_file
        
        # Initialize pipeline factory
        try:
            self.factory = PipelineFactory()
            self.factory.create_pipeline(config_path=config_file)
        except Exception as e:
            self.logger.error(f"Failed to initialize pipeline factory: {e}")
            raise

    def send_progress(self, message: str) -> None:
        """Send progress updates through callback or logging"""
        self.logger.info(message)
        if self.callback_query:
            try:
                self.callback_query.message.reply_text(message)
            except Exception as e:
                self.logger.error(f"Failed to send progress message: {e}")

    def process_latest_news_in_short_format(self, topic: Dict) -> str:
        """Process news in short-form vertical video format"""
        try:
            self.send_progress("🔄 Starting short-form video processing...")
            
            pipeline = self.factory.create_pipeline(pipeline_type='short')
            result = pipeline.execute({
                'url': topic['title'],
                'format': 'short',
                'aspect_ratio': '9:16'
            })
            
            self.send_progress("✅ Short-form video processing completed!")
            return result
            
        except VideoProcessingError as e:
            self.send_progress(f"❌ Video processing failed: {e}")
            raise
        except Exception as e:
            self.send_progress(f"❌ Unexpected error: {e}")
            self.logger.exception("Unexpected error in short format processing")
            raise

    def process_latest_news_in_long_format(self, topic: Dict) -> str:
        """Process news in long-form horizontal video format"""
        try:
            self.send_progress("🔄 Starting long-form video processing...")
            
            pipeline = self.factory.create_pipeline(pipeline_type='long')
            result = pipeline.execute({
                'url': topic['title'],
                'format': 'long',
                'aspect_ratio': '16:9'
            })
            
            self.send_progress("✅ Long-form video processing completed!")
            return result
            
        except VideoProcessingError as e:
            self.send_progress(f"❌ Video processing failed: {e}")
            raise
        except Exception as e:
            self.send_progress(f"❌ Unexpected error: {e}")
            self.logger.exception("Unexpected error in long format processing")
            raise