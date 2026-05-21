from abc import ABC, abstractmethod
from typing import Protocol, List, Dict, Any
from dataclasses import dataclass

@dataclass
class VideoMetadata:
    title: str
    description: str
    tags: List[str]
    thumbnail_path: str

class MediaGenerator(ABC):
    @abstractmethod
    def generate_media(self, prompt: str, **kwargs) -> str:
        """Generate or fetch media content based on prompt"""
        pass

class TextToSpeech(ABC):
    @abstractmethod
    def generate_audio(self, text: str, **kwargs) -> str:
        """Generate audio from text"""
        pass

class VideoAssembler(Protocol):
    def assemble(self, 
                media_paths: List[str], 
                audio_path: str, 
                subtitles_path: str, 
                metadata: VideoMetadata) -> str:
        """Assemble video from components"""
        pass

class NewsProcessor(Protocol):
    def process_article(self, url: str) -> Dict[str, Any]:
        """Process news article and return content"""
        pass

class VideoUploader(Protocol):
    def upload(self, video_path: str, metadata: VideoMetadata) -> str:
        """Upload video and return URL/ID"""
        pass

class ProcessingPipeline(ABC):
    @abstractmethod
    def execute(self, input_data: Dict[str, Any]) -> str:
        """Execute the complete video processing pipeline"""
        pass

class StorageManager(Protocol):
    def save_temp_file(self, content: bytes, extension: str) -> str:
        """Save temporary file and return path"""
        pass
    
    def cleanup(self) -> None:
        """Clean up temporary files"""
        pass