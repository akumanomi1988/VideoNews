# Video Processing Pipeline

## Architecture Overview

### Pipeline Types
1. **ShortFormPipeline**
   - Optimized for vertical video (9:16)
   - Target duration: 60 seconds
   - Platforms: TikTok, Instagram Reels

2. **LongFormPipeline**
   - Optimized for horizontal video (16:9)
   - Target duration: 10 minutes
   - Platform: YouTube

## Pipeline Stages

### 1. Article Processing
```mermaid
graph LR
    A[URL Input] --> B[Duplicate Check]
    B --> C[Content Extraction]
    C --> D[Text Analysis]
    D --> E[Prompt Generation]
```

### 2. Media Generation
```mermaid
graph LR
    A[Image Prompts] --> B[Style Selection]
    B --> C[Image Generation]
    C --> D[Aspect Ratio Adjustment]
    D --> E[Media Validation]
```

### 3. Audio Generation
```mermaid
graph LR
    A[Text Content] --> B[Voice Selection]
    B --> C[TTS Processing]
    C --> D[Subtitle Generation]
    D --> E[Audio Optimization]
```

### 4. Video Assembly
```mermaid
graph LR
    A[Media Assets] --> B[Timeline Creation]
    B --> C[Audio Sync]
    C --> D[Subtitle Overlay]
    D --> E[Final Render]
```

## Component Details

### Progress Tracking
```python
class ProgressTracker:
    """
    Tracks pipeline stage progress with the following stages:
    - article_processing
    - media_generation
    - audio_generation
    - subtitle_generation
    - video_assembly
    - upload
    """
```

### Resource Management
```python
class ResourceManager:
    """
    Handles:
    - Temporary file cleanup
    - Media asset registration
    - Memory optimization
    - Resource deallocation
    """
```

## Pipeline Factory

### Configuration
```json
{
    "pipeline_type": "short|long",
    "video_settings": {
        "aspect_ratio": "9:16|16:9",
        "duration_target": 60|600,
        "quality": "high|medium|low"
    },
    "processing": {
        "parallel_media_generation": true,
        "memory_optimization": true,
        "cache_enabled": true
    }
}
```

### Factory Methods
```python
class PipelineFactory:
    """Creates and configures video processing pipelines"""
    def create_pipeline(self, config_path: str, pipeline_type: str = 'default')
    def create_pipeline_from_config(self, config: Dict[str, Any], pipeline_type: str = 'default')
```

## Video Assembly

### Media Processing
- Parallel chunk processing
- Memory-efficient operations
- Format standardization
- Quality optimization

### Resource Optimization
- Lazy loading of large assets
- Temporary file management
- Memory usage monitoring
- Cache management

## Error Handling

### Pipeline Errors
```python
class VideoProcessingError(Exception):
    """Custom exception for video processing errors"""
    pass
```

### Recovery Strategies
1. **Transient Failures**
   - Automatic retry with backoff
   - Resource cleanup
   - State restoration

2. **Fatal Errors**
   - Resource cleanup
   - Error reporting
   - Pipeline shutdown

## Monitoring

### Statistics Collection
```python
class ProcessingStats:
    """
    Tracks:
    - Processing duration
    - Resource usage
    - Success/failure rates
    - Error patterns
    """
```

### Performance Metrics
- Stage completion times
- Resource utilization
- Queue lengths
- Error frequencies

## Directory Structure
```
scripts/
├── pipeline.py          # Pipeline implementations
├── factory.py          # Pipeline factory
├── video_assembler.py  # Video processing
├── monitoring.py       # Statistics and monitoring
└── utils/
    ├── progress_tracker.py
    ├── resource_manager.py
    └── container.py
```

## Usage Examples

### Short-Form Video Generation
```python
from news_video_processor import NewsVideoProcessor

processor = NewsVideoProcessor('settings.json')
result = processor.process_latest_news_in_short_format({
    'url': 'https://example.com/article',
    'format': 'short',
    'aspect_ratio': '9:16'
})
```

### Long-Form Video Generation
```python
result = processor.process_latest_news_in_long_format({
    'url': 'https://example.com/article',
    'format': 'long',
    'aspect_ratio': '16:9'
})
```

## Performance Optimization

### Memory Management
- Chunk-based processing
- Resource pooling
- Cache strategies
- Garbage collection

### Processing Optimization
- Parallel execution
- Asset preloading
- Format optimization
- Queue management

## Best Practices

### Pipeline Development
1. Use dependency injection
2. Implement proper error handling
3. Add comprehensive logging
4. Include progress tracking
5. Optimize resource usage

### Resource Management
1. Clean up temporary files
2. Monitor memory usage
3. Implement timeouts
4. Handle interruptions

## Troubleshooting

### Common Issues
1. **Memory Exhaustion**
   - Enable memory optimization
   - Reduce parallel processing
   - Implement chunking

2. **Processing Failures**
   - Check resource availability
   - Verify API quotas
   - Monitor error patterns

3. **Performance Issues**
   - Optimize asset loading
   - Enable caching
   - Adjust chunk sizes