from typing import Dict, Any, List
import logging
from pathlib import Path
from scripts.AI.natural_language_generation import Chatbot
from scripts.DataFetcher.news_extractor import NewsExtractor
from ..interfaces import NewsProcessor

class ArticleProcessor(NewsProcessor):
    """Handles news article processing and content generation"""
    
    def __init__(
        self,
        language: str = "en",
        model: str = "gpt-3.5-turbo",
        logger: logging.Logger = None
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.chatbot = Chatbot(language=language, model=model)
        self.extractor = NewsExtractor()

    def process_article(self, url: str) -> Dict[str, Any]:
        """Process news article and generate required content"""
        try:
            # Extract article content
            article_text = self.extractor.extract_article(url)
            if not article_text:
                raise ValueError("Failed to extract article content")

            # Generate article content and metadata
            article, phrases, title, description, tags, cover_text, cover_image = (
                self.chatbot.generate_article_and_phrases_long(url)
            )

            # Generate media prompts from article content
            media_prompts = self._generate_media_prompts(article)

            return {
                'title': title,
                'description': description,
                'content': article,
                'tags': tags,
                'media_prompts': media_prompts,
                'cover_text': cover_text,
                'cover_image': cover_image
            }

        except Exception as e:
            self.logger.error(f"Failed to process article: {e}")
            raise

    def _generate_media_prompts(self, article: str, max_prompts: int = 10) -> List[str]:
        """Generate media prompts from article content"""
        try:
            # Use the chatbot to generate scene descriptions
            scene_descriptions = self.chatbot.generate_scene_descriptions(article)
            
            # Filter and limit the number of prompts
            valid_prompts = [
                desc for desc in scene_descriptions 
                if desc and len(desc.split()) >= 3  # Ensure meaningful prompts
            ][:max_prompts]

            if not valid_prompts:
                # Fallback to basic article-based prompt
                return [self.chatbot.generate_cover_image(article)]

            return valid_prompts

        except Exception as e:
            self.logger.error(f"Failed to generate media prompts: {e}")
            # Return a safe fallback
            return [article[:100]]  # Use first 100 chars as emergency fallback

class ShortFormProcessor(ArticleProcessor):
    """Specialized processor for short-form content"""
    
    def process_article(self, url: str) -> Dict[str, Any]:
        try:
            # Override with short-form specific processing
            article_text = self.extractor.extract_article(url)
            if not article_text:
                raise ValueError("Failed to extract article content")

            # Generate shorter content for short-form videos
            article, phrases, title, description, tags, cover_text, cover_image = (
                self.chatbot.generate_article_and_phrases_short(url)
            )

            media_prompts = self._generate_media_prompts(article, max_prompts=5)

            return {
                'title': title,
                'description': description,
                'content': article,
                'tags': tags,
                'media_prompts': media_prompts,
                'cover_text': cover_text,
                'cover_image': cover_image
            }

        except Exception as e:
            self.logger.error(f"Failed to process short-form article: {e}")
            raise