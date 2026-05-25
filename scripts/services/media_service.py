from typing import Optional, List
from pathlib import Path
import logging
import requests
from scripts.AI.text_to_image import FluxImageGenerator, AspectRatio, StylePreset
from scripts.DataFetcher.pexels_media_fetcher import PexelsMediaFetcher
from ..interfaces import MediaGenerator
from ..utils.retry import retry_with_backoff, is_transient_error, RetryError
from .cache_service import CacheManager
from ..utils.app_logger import trace

class MediaGenerationError(Exception):
    """Custom exception for media generation failures"""
    pass

class FluxMediaService(MediaGenerator):
    """Handles image generation using Flux API with caching and retry mechanism"""
    
    @trace()
    def __init__(self, api_key: str, output_dir: str, cache_dir: str = None, model: str = "black-forest-labs/FLUX.1-dev",
                 azure_endpoint: str = "", azure_api_key: str = "", azure_model: str = "MAI-Image-2e"):
        self.logger = logging.getLogger(__name__)
        self.generator = FluxImageGenerator(
            token=api_key,
            output_dir=output_dir,
            azure_endpoint=azure_endpoint or None,
            azure_api_key=azure_api_key or None,
            azure_model=azure_model,
        )
        self.generator.model = model
        self.cache = CacheManager(
            cache_dir or str(Path(output_dir) / "cache" / "flux")
        )

    @trace()
    @retry_with_backoff(
        retries=5,
        backoff_in_seconds=2,
        max_backoff_in_seconds=60,
        exceptions=(Exception,),
        should_retry=is_transient_error
    )
    def generate_media(self, prompt: str, **kwargs) -> str:
        try:
            # Check cache first
            cache_params = {
                'style': kwargs.get('style', StylePreset.NONE),
                'orientation': kwargs.get('orientation', AspectRatio.PORTRAIT),
                'model': self.generator.model
            }
            
            if cached_path := self.cache.get(prompt, cache_params):
                self.logger.info(f"Using cached image for prompt: {prompt[:100]}...")
                return cached_path
            
            # Generate new image if not in cache
            self.logger.info(f"Generating new image for prompt: {prompt[:100]}...")
            result = self.generator.generate_image(
                custom_prompt=prompt,
                aspect_ratio=cache_params['orientation'],
                style_preset=cache_params['style']
            )
            
            if not result:
                raise MediaGenerationError("Failed to generate image: no result returned")
            
            # Cache the result
            return self.cache.put(prompt, result, cache_params)
            
        except Exception as e:
            self.logger.error(f"Failed to generate image: {e}")
            raise

class PexelsMediaService(MediaGenerator):
    """Handles media fetching from Pexels with caching"""
    
    @trace()
    def __init__(self, api_key: str, output_dir: str, cache_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.fetcher = PexelsMediaFetcher(api_key=api_key, temp_dir=output_dir)
        self.cache = CacheManager(
            cache_dir or str(Path(output_dir) / "cache" / "pexels")
        )

    @trace()
    @retry_with_backoff(
        retries=3,
        backoff_in_seconds=1,
        max_backoff_in_seconds=30,
        exceptions=(requests.RequestException, Exception),
        should_retry=is_transient_error
    )
    def generate_media(self, prompt: str, **kwargs) -> str:
        try:
            # Check cache first
            cache_params = {
                'type': kwargs.get('media_type', 'photo'),
                'orientation': kwargs.get('orientation', 'portrait')
            }
            
            if cached_path := self.cache.get(prompt, cache_params):
                self.logger.info(f"Using cached media for prompt: {prompt[:100]}...")
                return cached_path
            
            # Fetch new media if not in cache
            self.logger.info(f"Fetching new media from Pexels: {prompt[:100]}...")
            result = self.fetcher.fetch_and_save_media(prompt)
            
            if not result:
                raise MediaGenerationError("Failed to fetch media: no result returned")
            
            # Cache the result
            return self.cache.put(prompt, result, cache_params)
            
        except Exception as e:
            self.logger.error(f"Failed to fetch media from Pexels: {e}")
            raise

class CompositeMediaService(MediaGenerator):
    """Combines multiple media services with smart failover and caching"""
    
    @trace()
    def __init__(self, services: List[MediaGenerator], cache_dir: str = None):
        self.logger = logging.getLogger(__name__)
        self.services = services
        self.fallback_index = 0
        self.cache = CacheManager(
            cache_dir or str(Path("temp") / "cache" / "composite")
        )

    @trace()
    def generate_media(self, prompt: str, **kwargs) -> str:
        """Generate media using multiple services with caching and failover"""
        # Check composite cache first
        cache_params = {
            'style': kwargs.get('style', 'default'),
            'orientation': kwargs.get('orientation', 'portrait')
        }
        
        if cached_path := self.cache.get(prompt, cache_params):
            self.logger.info(f"Using cached media from composite service: {prompt[:100]}...")
            return cached_path

        # Try each service if not in cache
        last_error = None
        errors = []

        for _ in range(len(self.services)):
            service = self.services[self.fallback_index]
            try:
                result = service.generate_media(prompt, **kwargs)
                
                # Cache successful result
                cached_path = self.cache.put(prompt, result, cache_params)
                
                # On success, move this service to the front for next time
                if self.fallback_index > 0:
                    self.services.insert(0, self.services.pop(self.fallback_index))
                    self.fallback_index = 0
                    
                return cached_path
                
            except RetryError as e:
                # Retry error means we exhausted retries, try next service
                errors.append(f"{service.__class__.__name__}: {str(e)}")
                last_error = e
                
            except Exception as e:
                # Unexpected error, log and try next service
                self.logger.warning(f"Unexpected error from {service.__class__.__name__}: {e}")
                errors.append(f"{service.__class__.__name__}: {str(e)}")
                last_error = e
            
            # Move to next service
            self.fallback_index = (self.fallback_index + 1) % len(self.services)

        error_msg = "\n".join(errors)
        raise MediaGenerationError(
            f"All media services failed to generate content. Errors:\n{error_msg}"
        ) from last_error