from typing import Optional, Dict, Any, List, Callable
import time
from enum import Enum, auto
import logging
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path

class StageStatus(Enum):
    """Pipeline stage status"""
    PENDING = auto()
    IN_PROGRESS = auto()
    COMPLETED = auto()
    FAILED = auto()
    SKIPPED = auto()

@dataclass
class StageProgress:
    """Tracks progress of a single pipeline stage"""
    name: str
    status: StageStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    progress: float = 0.0  # 0-100
    message: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    @property
    def duration(self) -> Optional[float]:
        """Get stage duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

class ProgressTracker:
    """Tracks progress of the video processing pipeline"""
    
    def __init__(self, callback: Optional[Callable[[Dict], None]] = None):
        self.logger = logging.getLogger(__name__)
        self.stages: Dict[str, StageProgress] = {}
        self.current_stage: Optional[str] = None
        self.callback = callback
        self.start_time = datetime.now()
        self._setup_stages()

    def _setup_stages(self):
        """Initialize pipeline stages"""
        stages = [
            "article_processing",
            "media_generation",
            "audio_generation",
            "subtitle_generation",
            "video_assembly",
            "upload"
        ]
        
        for stage in stages:
            self.stages[stage] = StageProgress(
                name=stage,
                status=StageStatus.PENDING,
                metadata={}
            )

    def start_stage(self, stage_name: str, message: str = ""):
        """Start tracking a pipeline stage"""
        if stage_name not in self.stages:
            raise ValueError(f"Unknown stage: {stage_name}")
            
        stage = self.stages[stage_name]
        stage.status = StageStatus.IN_PROGRESS
        stage.start_time = datetime.now()
        stage.message = message
        self.current_stage = stage_name
        
        self._notify_progress()

    def update_progress(self, progress: float, message: str = ""):
        """Update progress of current stage"""
        if not self.current_stage:
            return
            
        stage = self.stages[self.current_stage]
        stage.progress = min(max(progress, 0), 100)
        if message:
            stage.message = message
            
        self._notify_progress()

    def complete_stage(self, metadata: Optional[Dict[str, Any]] = None):
        """Mark current stage as completed"""
        if not self.current_stage:
            return
            
        stage = self.stages[self.current_stage]
        stage.status = StageStatus.COMPLETED
        stage.end_time = datetime.now()
        stage.progress = 100
        if metadata:
            stage.metadata = metadata
            
        self._notify_progress()

    def fail_stage(self, error: str, metadata: Optional[Dict[str, Any]] = None):
        """Mark current stage as failed"""
        if not self.current_stage:
            return
            
        stage = self.stages[self.current_stage]
        stage.status = StageStatus.FAILED
        stage.end_time = datetime.now()
        stage.error = error
        if metadata:
            stage.metadata = metadata
            
        self._notify_progress()

    def skip_stage(self, reason: str):
        """Mark current stage as skipped"""
        if not self.current_stage:
            return
            
        stage = self.stages[self.current_stage]
        stage.status = StageStatus.SKIPPED
        stage.end_time = datetime.now()
        stage.message = reason
        
        self._notify_progress()

    def _notify_progress(self):
        """Notify progress through callback"""
        if not self.callback:
            return
            
        try:
            self.callback(self.get_progress_report())
        except Exception as e:
            self.logger.error(f"Failed to notify progress: {e}")

    def get_progress_report(self) -> Dict[str, Any]:
        """Get detailed progress report"""
        total_progress = self._calculate_total_progress()
        current_stage = self.stages[self.current_stage] if self.current_stage else None
        
        return {
            "total_progress": total_progress,
            "start_time": self.start_time.isoformat(),
            "elapsed_time": (datetime.now() - self.start_time).total_seconds(),
            "current_stage": {
                "name": current_stage.name if current_stage else None,
                "status": current_stage.status.name if current_stage else None,
                "progress": current_stage.progress if current_stage else 0,
                "message": current_stage.message if current_stage else "",
                "error": current_stage.error if current_stage else None
            },
            "stages": {
                name: {
                    "status": stage.status.name,
                    "progress": stage.progress,
                    "duration": stage.duration,
                    "message": stage.message,
                    "error": stage.error,
                    "metadata": stage.metadata
                }
                for name, stage in self.stages.items()
            }
        }

    def _calculate_total_progress(self) -> float:
        """Calculate overall pipeline progress"""
        stage_weights = {
            "article_processing": 0.1,
            "media_generation": 0.3,
            "audio_generation": 0.2,
            "subtitle_generation": 0.1,
            "video_assembly": 0.2,
            "upload": 0.1
        }
        
        total_progress = 0.0
        for stage_name, stage in self.stages.items():
            weight = stage_weights.get(stage_name, 0)
            if stage.status == StageStatus.COMPLETED:
                total_progress += weight * 100
            elif stage.status == StageStatus.IN_PROGRESS:
                total_progress += weight * stage.progress
            elif stage.status == StageStatus.SKIPPED:
                total_progress += weight * 100
                
        return min(total_progress, 100)

    def save_report(self, output_path: str):
        """Save progress report to file"""
        try:
            report = self.get_progress_report()
            
            # Convert datetime to string
            report['start_time'] = str(self.start_time)
            
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
                
            self.logger.info(f"Progress report saved to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save progress report: {e}")

    def reset(self):
        """Reset progress tracker"""
        self.stages.clear()
        self.current_stage = None
        self.start_time = datetime.now()
        self._setup_stages()