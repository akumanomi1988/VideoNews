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
        self.config = config
        self._setup_defaults()

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
        from ..services.news_service import NewsService
        from ..services.media_service import CompositeMediaService
        from ..services.tts_service import EdgeTTSService
        from ..services.video_assembler import VideoAssembler as VideoAssemblerImpl
        from ..services.storage_service import LocalStorageManager
        
        # Bind default implementations
        self.bind(NewsProcessor, NewsService)
        self.bind(VideoAssembler, VideoAssemblerImpl)
        self.bind(StorageManager, LocalStorageManager)
        
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
                cache_dir=str(Path(self.config['temp_dir']) / 'cache' / 'flux')
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

    def create_pipeline(self, pipeline_type: str = 'default'):
        """Create a pipeline instance of the specified type"""
        from ..pipeline import VideoProcessingPipeline, ShortFormPipeline, LongFormPipeline
        
        # Resolve dependencies
        news_processor = self.resolve(NewsProcessor)
        media_generator = self.resolve(MediaGenerator)
        tts_service = self.resolve(TextToSpeech)
        video_assembler = self.resolve(VideoAssembler)
        video_uploader = self.resolve(VideoUploader)
        storage = self.resolve(StorageManager)
        
        # Create appropriate pipeline type
        if pipeline_type == 'short':
            return ShortFormPipeline(
                news_processor=news_processor,
                media_generator=media_generator,
                tts_service=tts_service,
                video_assembler=video_assembler,
                video_uploader=video_uploader,
                storage=storage,
                config=self.config
            )
        elif pipeline_type == 'long':
            return LongFormPipeline(
                news_processor=news_processor,
                media_generator=media_generator,
                tts_service=tts_service,
                video_assembler=video_assembler,
                video_uploader=video_uploader,
                storage=storage,
                config=self.config
            )
        else:
            return VideoProcessingPipeline(
                news_processor=news_processor,
                media_generator=media_generator,
                tts_service=tts_service,
                video_assembler=video_assembler,
                video_uploader=video_uploader,
                storage=storage,
                config=self.config
            )