from typing import Optional, List, Dict
import logging
from pathlib import Path
import os
import json
from concurrent.futures import ThreadPoolExecutor
from scripts.AI.text_to_speech import TTSFactory, TTSProvider
from ..interfaces import TextToSpeech
from ..utils.retry import retry_with_backoff, is_transient_error
from .subtitle_service import SubtitleProcessor
from ..utils.app_logger import trace

class TTSError(Exception):
    """Custom exception for TTS failures"""
    pass

class ChunkProcessor:
    """Handles text chunking for parallel TTS processing"""
    
    @staticmethod
    def split_text(text: str, max_chunk_size: int = 1000) -> List[str]:
        """Split text into chunks at sentence boundaries"""
        sentences = text.replace('\n', ' ').split('. ')
        chunks = []
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Add period back if it was removed during split
            if not sentence.endswith('.'):
                sentence += '.'
                
            sentence_size = len(sentence)
            
            if current_size + sentence_size > max_chunk_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_size = sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
            
        return chunks

class EdgeTTSService(TextToSpeech):
    """Microsoft Edge TTS implementation with parallel processing"""
    
    @trace()
    def __init__(self, output_dir: str, voice: str, language: str):
        self.logger = logging.getLogger(__name__)
        self.tts = TTSFactory(TTSProvider.EDGE, output_dir=output_dir)
        self.voice = voice
        self.language = language
        self.output_dir = Path(output_dir)
        self.chunk_processor = ChunkProcessor()

    @trace()
    @retry_with_backoff(
        retries=3,
        backoff_in_seconds=1,
        exceptions=(Exception,),
        should_retry=is_transient_error
    )
    def generate_audio(self, text: str, **kwargs) -> str:
        """Generate audio with parallel processing and improved subtitles"""
        try:
            # Create output directory if it doesn't exist
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            # Split text into chunks for parallel processing
            chunks = self.chunk_processor.split_text(text)
            chunk_files = []
            
            # Process chunks in parallel
            with ThreadPoolExecutor(max_workers=min(4, len(chunks))) as executor:
                future_to_chunk = {
                    executor.submit(
                        self._process_chunk,
                        chunk,
                        i
                    ): (i, chunk) for i, chunk in enumerate(chunks)
                }
                
                for future in future_to_chunk:
                    try:
                        chunk_file = future.result()
                        if chunk_file:
                            chunk_files.append((future_to_chunk[future][0], chunk_file))
                    except Exception as e:
                        self.logger.error(f"Chunk processing failed: {e}")
                        raise

            if not chunk_files:
                raise TTSError("No audio chunks were generated")

            # Combine audio chunks
            final_path = self._combine_audio_chunks(
                sorted(chunk_files, key=lambda x: x[0])
            )
            
            # Generate subtitles if path provided
            if srt_path := kwargs.get('srt_path'):
                self._generate_synchronized_subtitles(text, final_path, srt_path)

            return final_path

        except Exception as e:
            self.logger.error(f"Audio generation failed: {e}")
            raise TTSError(f"Failed to generate audio: {e}")

    def _generate_synchronized_subtitles(self, text: str, audio_path: str, srt_path: str) -> None:
        """Generate synchronized subtitles using the SubtitleProcessor"""
        try:
            processor = SubtitleProcessor(
                audio_file=audio_path,
                output_dir=str(self.output_dir)
            )
            
            result_path = processor.process_subtitles(
                text=text,
                max_chars_per_line=42,
                min_duration=1.0,
                max_duration=4.0
            )
            
            # Copy the generated subtitles to the requested path if different
            if str(result_path) != srt_path:
                import shutil
                shutil.copy2(result_path, srt_path)
                
        except Exception as e:
            self.logger.error(f"Failed to generate synchronized subtitles: {e}")
            raise

    def _process_chunk(self, text: str, chunk_index: int, srt_path: Optional[str] = None) -> str:
        """Process a single text chunk"""
        try:
            chunk_path = self.output_dir / f"chunk_{chunk_index}.mp3"
            
            return self.tts.text_to_speech_file(
                text,
                voice=self.voice,
                language=self.language,
                output_path=str(chunk_path)
            )
        except Exception as e:
            self.logger.error(f"Failed to process chunk {chunk_index}: {e}")
            raise

    def _combine_audio_chunks(self, chunk_files: List[tuple]) -> str:
        """Combine audio chunks into final audio file"""
        try:
            from pydub import AudioSegment
            
            combined = AudioSegment.empty()
            for _, chunk_path in chunk_files:
                chunk_audio = AudioSegment.from_mp3(chunk_path)
                combined += chunk_audio
                
            final_path = self.output_dir / "final_audio.mp3"
            combined.export(str(final_path), format="mp3")
            
            # Cleanup chunk files
            for _, chunk_path in chunk_files:
                try:
                    Path(chunk_path).unlink()
                except Exception as e:
                    self.logger.warning(f"Failed to delete chunk file {chunk_path}: {e}")
            
            return str(final_path)
            
        except Exception as e:
            self.logger.error(f"Failed to combine audio chunks: {e}")
            raise

class ElevenLabsTTSService(TextToSpeech):
    """ElevenLabs TTS implementation with retry mechanism"""
    
    def __init__(self, credentials_path: str, output_dir: str, quota_min: int = 100):
        self.logger = logging.getLogger(__name__)
        self.tts = TTSFactory(
            TTSProvider.ELEVENLABS,
            credentials_path=credentials_path,
            output_dir=output_dir,
            quota_min=quota_min
        )

    @retry_with_backoff(
        retries=3,
        backoff_in_seconds=2,
        max_backoff_in_seconds=30,
        exceptions=(Exception,),
        should_retry=is_transient_error
    )
    def generate_audio(self, text: str, **kwargs) -> str:
        try:
            srt_path = kwargs.get('srt_path')
            return self.tts.text_to_speech_file(text, srt_path=srt_path)
        except Exception as e:
            self.logger.error(f"Failed to generate audio with ElevenLabs: {e}")
            raise

class FallbackTTSService(TextToSpeech):
    """Implements a fallback strategy between multiple TTS services"""
    
    def __init__(self, primary: TextToSpeech, fallback: TextToSpeech):
        self.logger = logging.getLogger(__name__)
        self.primary = primary
        self.fallback = fallback

    def generate_audio(self, text: str, **kwargs) -> str:
        try:
            return self.primary.generate_audio(text, **kwargs)
        except Exception as e:
            self.logger.warning(f"Primary TTS failed: {e}, trying fallback")
            try:
                return self.fallback.generate_audio(text, **kwargs)
            except Exception as e:
                self.logger.error(f"Fallback TTS also failed: {e}")
                raise