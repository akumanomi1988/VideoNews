from typing import Dict, Any, Optional, Callable
import logging
import json
from pathlib import Path

from .config_validator import ConfigValidator
from .utils.container import PipelineContainer
from .interfaces import ProcessingPipeline
from .utils.app_logger import trace

class PipelineFactory:
    """Factory for creating and configuring video processing pipelines"""
    
    @trace()
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.validator = ConfigValidator()
        self._container: Optional[PipelineContainer] = None

    @trace()
    def create_pipeline(
        self,
        config_path: str,
        pipeline_type: str = 'default',
        progress_callback: Optional[Callable[[Dict], None]] = None
    ) -> ProcessingPipeline:
        """Create a pipeline instance from configuration file"""
        # Validate configuration
        errors = self.validator.validate_file(config_path)
        if errors:
            error_msg = self.validator.format_errors(errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)

        # Load configuration
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise

        return self.create_pipeline_from_config(config, pipeline_type, progress_callback=progress_callback)

    def create_pipeline_from_config(
        self,
        config: Dict[str, Any],
        pipeline_type: str = 'default',
        skip_validation: bool = False,
        progress_callback: Optional[Callable[[Dict], None]] = None
    ) -> ProcessingPipeline:
        """Create a pipeline instance from configuration dictionary"""
        # Validate configuration
        if not skip_validation:
            errors = self.validator.validate(config)
            if errors:
                error_msg = self.validator.format_errors(errors)
                self.logger.error(error_msg)
                raise ValueError(error_msg)

        # Ensure required directories exist
        self._setup_directories(config)

        # Create dependency container
        self._container = PipelineContainer(config)

        # Create pipeline instance
        try:
            pipeline = self._container.create_pipeline(pipeline_type, progress_callback=progress_callback)
            self.logger.info(f"Created {pipeline_type} pipeline successfully")
            return pipeline
        except Exception as e:
            self.logger.error(f"Failed to create pipeline: {e}")
            raise

    def _setup_directories(self, config: Dict[str, Any]):
        """Ensure required directories exist"""
        try:
            # Setup temp directory (handle both flat and settings.json nested formats)
            temp_dir = Path(
                config.get('temp_dir')
                or config.get('settings', {}).get('temp_dir', '.temp')
            )
            temp_dir.mkdir(parents=True, exist_ok=True)

            # Setup cache directories
            cache_dir = temp_dir / 'cache'
            (cache_dir / 'flux').mkdir(parents=True, exist_ok=True)
            (cache_dir / 'pexels').mkdir(parents=True, exist_ok=True)
            (cache_dir / 'composite').mkdir(parents=True, exist_ok=True)

            # Setup output directories based on uploader type
            if config.get('upload_type', 'youtube') == 'youtube':
                (temp_dir / 'youtube').mkdir(parents=True, exist_ok=True)
            elif config['upload_type'] == 'tiktok':
                (temp_dir / 'tiktok').mkdir(parents=True, exist_ok=True)

        except Exception as e:
            self.logger.error(f"Failed to setup directories: {e}")
            raise

    @staticmethod
    def get_available_pipeline_types() -> Dict[str, str]:
        """Get available pipeline types with descriptions"""
        return {
            'default': 'Standard video processing pipeline',
            'short': 'Pipeline optimized for short-form vertical videos (TikTok, Reels)',
            'long': 'Pipeline optimized for long-form horizontal videos (YouTube)'
        }

    def cleanup(self):
        """Cleanup resources when factory is no longer needed"""
        if self._container:
            try:
                # Get storage manager and cleanup
                storage = self._container.resolve('StorageManager')
                if storage:
                    storage.cleanup(force=True)
            except Exception as e:
                self.logger.error(f"Failed to cleanup resources: {e}")
            finally:
                self._container = None