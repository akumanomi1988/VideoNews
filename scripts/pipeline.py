from typing import Dict, Any, Optional, Callable
import logging
from pathlib import Path
import traceback
import os

from .interfaces import (
    ProcessingPipeline,
    MediaGenerator,
    TextToSpeech,
    VideoAssembler,
    NewsProcessor,
    VideoUploader,
    VideoMetadata,
    StorageManager
)
from .monitoring import PipelineMonitor, ProcessingStats
from .utils.progress_tracker import ProgressTracker

class VideoProcessingError(Exception):
    """Custom exception for video processing errors"""
    pass

class VideoProcessingPipeline(ProcessingPipeline):
    """Orchestrates the complete video generation process with monitoring"""
    
    def __init__(
        self,
        news_processor: NewsProcessor,
        media_generator: MediaGenerator,
        tts_service: TextToSpeech,
        video_assembler: VideoAssembler,
        video_uploader: VideoUploader,
        storage: StorageManager,
        config: Dict[str, Any],
        progress_callback: Optional[Callable[[Dict], None]] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.news_processor = news_processor
        self.media_generator = media_generator
        self.tts_service = tts_service
        self.video_assembler = video_assembler
        self.video_uploader = video_uploader
        self.storage = storage
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.monitor = PipelineMonitor()
        self.progress = ProgressTracker(callback=progress_callback)

    def execute(self, input_data: Dict[str, Any]) -> str:
        """Execute the complete video processing pipeline with monitoring"""
        stats = self.monitor.start_monitoring(self.__class__.__name__)
        media_info = {
            'media_generated': 0,
            'total_attempts': 0,
            'audio_duration': 0.0,
            'video_size_mb': 0.0
        }

        try:
            # Process article content
            self.progress.start_stage("article_processing", "Processing article content...")
            article_data = self.news_processor.process_article(input_data['url'])
            self.progress.complete_stage({
                'title': article_data['title'],
                'content_length': len(article_data['content'])
            })
            self.logger.info(f"Article processed: {article_data['title']}")

            # Generate media assets
            self.progress.start_stage("media_generation", "Generating media assets...")
            media_paths = []
            total_prompts = len(article_data['media_prompts'])
            
            for i, prompt in enumerate(article_data['media_prompts'], 1):
                media_info['total_attempts'] += 1
                try:
                    path = self.media_generator.generate_media(
                        prompt,
                        style=input_data.get('style', 'default'),
                        aspect_ratio=input_data.get('aspect_ratio', '16:9')
                    )
                    if path:
                        media_paths.append(path)
                        media_info['media_generated'] += 1
                        progress = (i / total_prompts) * 100
                        self.progress.update_progress(
                            progress,
                            f"Generated {len(media_paths)} of {total_prompts} media files"
                        )
                except Exception as e:
                    self.logger.warning(f"Failed to generate media for prompt '{prompt}': {e}")
                    continue
            
            if not media_paths:
                self.progress.fail_stage("Failed to generate any media assets")
                raise VideoProcessingError("Failed to generate any media assets")
            
            self.progress.complete_stage({
                'media_generated': len(media_paths),
                'total_attempts': media_info['total_attempts']
            })

            # Generate audio and subtitles
            self.progress.start_stage("audio_generation", "Generating audio...")
            audio_path = self.tts_service.generate_audio(
                article_data['content'],
                srt_path=str(Path(self.config['temp_dir']) / 'subtitles.srt')
            )
            
            # Track audio duration
            import moviepy.editor as mp
            audio_clip = mp.AudioFileClip(audio_path)
            media_info['audio_duration'] = audio_clip.duration
            audio_clip.close()
            
            self.progress.complete_stage({
                'audio_duration': media_info['audio_duration']
            })

            # Prepare metadata
            metadata = VideoMetadata(
                title=article_data['title'][:100],
                description=article_data['description'],
                tags=article_data['tags'],
                thumbnail_path=media_paths[0]
            )

            # Assemble video
            self.progress.start_stage("video_assembly", "Assembling video...")
            video_path = self.video_assembler.assemble(
                media_paths=media_paths,
                audio_path=audio_path,
                subtitles_path=str(Path(self.config['temp_dir']) / 'subtitles.srt'),
                metadata=metadata
            )
            
            # Track video size
            media_info['video_size_mb'] = os.path.getsize(video_path) / (1024 * 1024)
            self.progress.complete_stage({
                'video_size_mb': media_info['video_size_mb'],
                'output_path': video_path
            })

            # Upload video
            self.progress.start_stage("upload", "Uploading video...")
            upload_result = self.video_uploader.upload(video_path, metadata)
            self.progress.complete_stage({
                'upload_url': upload_result
            })

            # Record success
            self.monitor.record_success(stats, media_info)
            return upload_result

        except Exception as e:
            error_msg = f"Pipeline execution failed: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            if self.progress.current_stage:
                self.progress.fail_stage(error_msg)
            self.monitor.record_failure(stats, e)
            raise VideoProcessingError(error_msg)
        finally:
            try:
                self.storage.cleanup()
            except Exception as cleanup_error:
                self.logger.error(f"Cleanup failed: {cleanup_error}")

class ShortFormPipeline(VideoProcessingPipeline):
    """Pipeline optimized for short-form vertical videos"""
    
    def execute(self, input_data: Dict[str, Any]) -> str:
        """Execute pipeline for short-form content"""
        input_data.update({
            'format': 'short',
            'aspect_ratio': '9:16',
            'duration_target': 60  # Target 60 seconds for short form
        })
        return super().execute(input_data)

class LongFormPipeline(VideoProcessingPipeline):
    """Pipeline optimized for long-form horizontal videos"""
    
    def execute(self, input_data: Dict[str, Any]) -> str:
        """Execute pipeline for long-form content"""
        input_data.update({
            'format': 'long',
            'aspect_ratio': '16:9',
            'duration_target': 600  # Target 10 minutes for long form
        })
        return super().execute(input_data)