from typing import Dict, Any, List
import logging
from pathlib import Path
from scripts.AI.natural_language_generation import Chatbot
from scripts.DataFetcher.news_extractor import NewsExtractor
from ..interfaces import NewsProcessor
from ..utils.app_logger import trace

class ArticleProcessor(NewsProcessor):
    """Handles news article processing and content generation"""
    
    @trace()
    def __init__(
        self,
        language: str = "en",
        model: str = "nemotron-3-super:cloud",
        providers: list = None,
        logger: logging.Logger = None
    ):
        self.logger = logger or logging.getLogger(__name__)
        self.chatbot = Chatbot(language=language, model=model, providers=providers)
        self.extractor = NewsExtractor()

    @trace()
    def process_article(self, url: str) -> Dict[str, Any]:
        """Process news article and generate required content"""
        try:
            # Extract article content
            article_data = self.extractor.extract_article(url)
            if not article_data or not getattr(article_data, 'text', None):
                raise ValueError("Failed to extract article content")

            title = getattr(article_data, 'title', '') or url
            raw_text = article_data.text[:3000]  # Limit for processing

            # Try LLM content generation; fall back to using extracted text directly
            try:
                article, phrases, title, description, tags, cover_text, cover_image = (
                    self.chatbot.generate_article_and_phrases_long(url)
                )
            except Exception as llm_err:
                self.logger.warning(f"LLM generation failed, using extracted text: {llm_err}")
                article = raw_text[:2000]
                phrases = []
                description = raw_text[:200]
                tags = ["news", "article"]
                cover_text = title
                cover_image = ""

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
            # Return a safe fallback using article sentences
            sentences = [s.strip() for s in article.replace('.', '\n').split('\n') if len(s.strip()) > 20]
            return sentences[:max_prompts] if sentences else [article[:100]]

class ShortFormProcessor(ArticleProcessor):
    """Specialized processor for short-form content"""
    
    def process_article(self, url: str) -> Dict[str, Any]:
        try:
            # Override with short-form specific processing
            article_data = self.extractor.extract_article(url)
            if not article_data or not getattr(article_data, 'text', None):
                raise ValueError("Failed to extract article content")

            title = getattr(article_data, 'title', '') or url
            raw_text = article_data.text[:2000]

            # Try LLM content generation; fall back to using extracted text directly
            try:
                article, phrases, title, description, tags, cover_text, cover_image = (
                    self.chatbot.generate_article_and_phrases_short(url)
                )
            except Exception as llm_err:
                self.logger.warning(f"LLM generation failed, using extracted text: {llm_err}")
                article = raw_text[:1000]
                phrases = []
                description = raw_text[:150]
                tags = ["news", "article"]
                cover_text = title
                cover_image = ""

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