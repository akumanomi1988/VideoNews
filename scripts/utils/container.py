from typing import Dict, Any, Type, TypeVar, Optional, Callable
import logging
from pathlib import Path

T = TypeVar('T')

class Container:
    """Dependency injection container"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._bindings: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._factories: Dict[str, Callable[..., Any]] = {}

    def bind(self, interface: Type[T], implementation: Type[T]):
        """Bind an interface to its implementation"""
        key = self._get_key(interface)
        self._bindings[key] = implementation

    def bind_instance(self, interface: Type[T], instance: T):
        """Bind an interface to a singleton instance"""
        key = self._get_key(interface)
        self._singletons[key] = instance

    def bind_factory(self, interface: Type[T], factory: Callable[..., T]):
        """Bind an interface to a factory function"""
        key = self._get_key(interface)
        self._factories[key] = factory

    def resolve(self, interface: Type[T], **kwargs) -> T:
        """Resolve an interface to its implementation or instance"""
        key = self._get_key(interface)
        
        # Check singletons first
        if key in self._singletons:
            return self._singletons[key]
            
        # Check factories
        if key in self._factories:
            return self._factories[key](**kwargs)
            
        # Create new instance from binding
        if key in self._bindings:
            implementation = self._bindings[key]
            try:
                return implementation(**kwargs)
            except Exception as e:
                self.logger.error(f"Failed to instantiate {implementation}: {e}")
                raise
                
        raise KeyError(f"No binding found for {interface}")

    def _get_key(self, interface: Type[T]) -> str:
        """Get string key for an interface"""
        return f"{interface.__module__}.{interface.__name__}"

class PipelineContainer(Container):
    """Specialized container for pipeline components"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__()
        self.config = self._normalize_config(config)
        self._setup_defaults()

    @staticmethod
    def _normalize_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize settings.json structure to flat keys expected by container"""
        normalized: Dict[str, Any] = {}

        settings = config.get("settings", {})
        normalized["temp_dir"] = config.get("temp_dir") or settings.get("temp_dir", ".temp")
        normalized["media_source"] = settings.get("media_source", "huggingface")

        pexels = config.get("pexels", {})
        normalized["pexels_api_key"] = pexels.get("api_key", "")

        huggingface = config.get("huggingface", {})
        normalized["flux_api_key"] = huggingface.get("api_key", "")

        serpapi = config.get("serpapi", {})
        normalized["serpapi_api_key"] = serpapi.get("api_key", "")
        normalized["serpapi_use_cache"] = serpapi.get("use_cache", True)
        normalized["serpapi_cache_ttl_hours"] = serpapi.get("cache_ttl_hours", 24)
        normalized["serpapi_cache_dir"] = serpapi.get("cache_dir", ".temp/cache/serpapi")

        newsapi = config.get("newsapi", {})
        normalized["newsapi_api_key"] = newsapi.get("api_key", "")

        tts_edge = config.get("tts_edge", {})
        normalized["tts_voice"] = tts_edge.get("voice", "en-US-AriaNeural")
        normalized["tts_language"] = tts_edge.get("language", "en-US")

        article_settings = config.get("article_settings", {})
        normalized["article_language"] = article_settings.get("language", "en")
        normalized["article_model"] = article_settings.get("model", "gpt-4o-mini")

        llm_config = config.get("llm", {})
        normalized["llm_providers"] = llm_config.get("providers", [])

        azure_images = config.get("azure_images", {})
        normalized["azure_image_endpoint"] = azure_images.get("endpoint", "")
        normalized["azure_image_api_key"] = azure_images.get("api_key", "")
        normalized["azure_image_model"] = azure_images.get("model", "MAI-Image-2e")

        youtube = config.get("youtube", {})
        normalized["youtube_client_secrets"] = youtube.get("credentials_file", "secrets/client_secret.json")
        normalized["youtube_credentials"] = normalized["youtube_client_secrets"]

        tiktok = config.get("tiktok", {})
        normalized["tiktok_session"] = tiktok.get("session_file", "")

        normalized["upload_type"] = config.get("upload_type", "youtube")
        normalized["background_music"] = config.get("video_result", {}).get("background_music", "")

        # Pass through any unrecognized keys for compat
        for k, v in config.items():
            if k not in normalized:
                normalized[k] = v

        return normalized

    def _setup_defaults(self):
        """Set up default pipeline component bindings"""
        from ..interfaces import (
            NewsProcessor,
            MediaGenerator,
            TextToSpeech,
            VideoAssembler,
            VideoUploader,
            StorageManager
        )
        from ..services.news_service import ArticleProcessor as NewsService
        from ..services.media_service import CompositeMediaService
        from ..services.tts_service import EdgeTTSService
        from ..services.video_assembler import VideoAssembler as VideoAssemblerImpl
        from ..services.storage_service import LocalStorageManager
        
        # Bind default implementations
        self.bind(NewsProcessor, NewsService)
        self.bind(VideoAssembler, VideoAssemblerImpl)
        def storage_factory(**kwargs):
            return LocalStorageManager(base_dir=self.config['temp_dir'])
        self.bind_factory(StorageManager, storage_factory)
        
        # Bind text-to-speech with configuration
        def tts_factory(**kwargs):
            return EdgeTTSService(
                output_dir=self.config['temp_dir'],
                voice=self.config.get('tts_voice', 'en-US-AriaNeural'),
                language=self.config.get('tts_language', 'en-US')
            )
        self.bind_factory(TextToSpeech, tts_factory)
        
        # Set up media generation pipeline
        def media_factory(**kwargs):
            from ..services.media_service import FluxMediaService, PexelsMediaService
            
            # Create services
            flux = FluxMediaService(
                api_key=self.config['flux_api_key'],
                output_dir=self.config['temp_dir'],
                cache_dir=str(Path(self.config['temp_dir']) / 'cache' / 'flux'),
                azure_endpoint=self.config.get('azure_image_endpoint', ''),
                azure_api_key=self.config.get('azure_image_api_key', ''),
                azure_model=self.config.get('azure_image_model', 'MAI-Image-2e'),
            )
            
            pexels = PexelsMediaService(
                api_key=self.config['pexels_api_key'],
                output_dir=self.config['temp_dir'],
                cache_dir=str(Path(self.config['temp_dir']) / 'cache' / 'pexels')
            )
            
            # Create composite service with both providers
            return CompositeMediaService(
                services=[flux, pexels],
                cache_dir=str(Path(self.config['temp_dir']) / 'cache' / 'composite')
            )
        self.bind_factory(MediaGenerator, media_factory)
        
        # Set up video uploader based on configuration
        def uploader_factory(**kwargs):
            upload_type = self.config.get('upload_type', 'youtube')
            
            if upload_type == 'youtube':
                from ..services.youtube_uploader import YoutubeUploader
                return YoutubeUploader(
                    credentials_path=self.config['youtube_credentials'],
                    client_secrets_path=self.config['youtube_client_secrets']
                )
            elif upload_type == 'tiktok':
                from ..services.tiktok_uploader import TiktokUploader
                return TiktokUploader(
                    session_file=self.config['tiktok_session']
                )
            else:
                raise ValueError(f"Unsupported upload type: {upload_type}")
                
        self.bind_factory(VideoUploader, uploader_factory)

    def create_pipeline(self, pipeline_type: str = 'default',
                        progress_callback: Optional[Callable[[Dict], None]] = None):
        """Create a pipeline instance of the specified type"""
        from ..interfaces import (
            NewsProcessor, MediaGenerator, TextToSpeech,
            VideoAssembler, VideoUploader, StorageManager
        )
        from ..pipeline import VideoProcessingPipeline, ShortFormPipeline, LongFormPipeline
        
        # Resolve dependencies
        news_processor = self.resolve(
            NewsProcessor,
            language=self.config.get("article_language", "en"),
            model=self.config.get("article_model", "nemotron-3-super:cloud"),
            providers=self.config.get("llm_providers", []),
        )
        media_generator = self.resolve(MediaGenerator)
        tts_service = self.resolve(TextToSpeech)
        video_assembler = self.resolve(VideoAssembler)
        video_uploader = self.resolve(VideoUploader)
        storage = self.resolve(StorageManager)
        
        common_kwargs = dict(
            news_processor=news_processor,
            media_generator=media_generator,
            tts_service=tts_service,
            video_assembler=video_assembler,
            video_uploader=video_uploader,
            storage=storage,
            config=self.config,
        )
        if progress_callback is not None:
            common_kwargs['progress_callback'] = progress_callback

        # Create appropriate pipeline type
        if pipeline_type == 'short':
            return ShortFormPipeline(**common_kwargs)
        elif pipeline_type == 'long':
            return LongFormPipeline(**common_kwargs)
        else:
            return VideoProcessingPipeline(**common_kwargs)
