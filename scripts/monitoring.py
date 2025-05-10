import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class PipelineMonitor:
    def __init__(self, metrics_dir: str = 'metrics'):
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
    def start_pipeline(self, pipeline_id: str, metadata: Dict[str, Any]) -> None:
        """Record the start of a pipeline execution"""
        metrics = {
            'pipeline_id': pipeline_id,
            'start_time': time.time(),
            'metadata': metadata,
            'steps_completed': [],
            'current_step': None,
            'is_completed': False,
            'is_failed': False,
            'error': None
        }
        self._save_metrics(pipeline_id, metrics)

    def complete_step(self, pipeline_id: str, step_name: str, duration: float) -> None:
        """Record completion of a pipeline step"""
        metrics = self._load_metrics(pipeline_id)
        if not metrics:
            return
            
        metrics['steps_completed'].append({
            'name': step_name,
            'completion_time': time.time(),
            'duration': duration
        })
        self._save_metrics(pipeline_id, metrics)

    def set_current_step(self, pipeline_id: str, step_name: str) -> None:
        """Update the current step being executed"""
        metrics = self._load_metrics(pipeline_id)
        if not metrics:
            return
            
        metrics['current_step'] = {
            'name': step_name,
            'start_time': time.time()
        }
        self._save_metrics(pipeline_id, metrics)

    def complete_pipeline(self, pipeline_id: str) -> None:
        """Record successful completion of a pipeline"""
        metrics = self._load_metrics(pipeline_id)
        if not metrics:
            return
            
        metrics['is_completed'] = True
        metrics['completion_time'] = time.time()
        metrics['duration'] = metrics['completion_time'] - metrics['start_time']
        self._save_metrics(pipeline_id, metrics)

    def fail_pipeline(self, pipeline_id: str, error: str) -> None:
        """Record pipeline failure"""
        metrics = self._load_metrics(pipeline_id)
        if not metrics:
            return
            
        metrics['is_failed'] = True
        metrics['error'] = error
        metrics['failure_time'] = time.time()
        metrics['duration'] = metrics['failure_time'] - metrics['start_time']
        self._save_metrics(pipeline_id, metrics)

    def get_pipeline_status(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a pipeline"""
        return self._load_metrics(pipeline_id)

    def _save_metrics(self, pipeline_id: str, metrics: Dict[str, Any]) -> None:
        """Save pipeline metrics to file"""
        try:
            metrics_file = self.metrics_dir / f"{pipeline_id}.json"
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metrics for pipeline {pipeline_id}: {e}")

    def _load_metrics(self, pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Load pipeline metrics from file"""
        try:
            metrics_file = self.metrics_dir / f"{pipeline_id}.json"
            if not metrics_file.exists():
                logger.warning(f"No metrics file found for pipeline {pipeline_id}")
                return None
                
            with open(metrics_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load metrics for pipeline {pipeline_id}: {e}")
            return None

    def cleanup_old_metrics(self, max_age_days: int = 7) -> None:
        """Remove metrics files older than specified days"""
        try:
            current_time = time.time()
            max_age = max_age_days * 24 * 3600
            
            for file in self.metrics_dir.glob('*.json'):
                if (current_time - file.stat().st_mtime) > max_age:
                    file.unlink()
        except Exception as e:
            logger.error(f"Failed to cleanup old metrics: {e}")

    def start_monitoring(self, pipeline_name: str) -> 'ProcessingStats':
        """Start monitoring a new pipeline execution"""
        stats = ProcessingStats()
        stats.metadata['pipeline_name'] = pipeline_name
        return stats

    def record_success(self, stats: 'ProcessingStats', media_info: Dict[str, Any]) -> None:
        """Record successful completion of pipeline execution"""
        stats.complete(media_info)
        self._save_metrics(stats.metadata['pipeline_name'], stats.to_dict())

    def record_failure(self, stats: 'ProcessingStats', error: Exception) -> None:
        """Record failed pipeline execution"""
        stats.fail(error)
        self._save_metrics(stats.metadata['pipeline_name'], stats.to_dict())

class StepTimer:
    def __init__(self, monitor: PipelineMonitor, pipeline_id: str, step_name: str):
        self.monitor = monitor
        self.pipeline_id = pipeline_id
        self.step_name = step_name
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        self.monitor.set_current_step(self.pipeline_id, self.step_name)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            duration = time.time() - self.start_time
            self.monitor.complete_step(self.pipeline_id, self.step_name, duration)

class ProcessingStats:
    """Class to track processing statistics during pipeline execution"""
    def __init__(self):
        self.start_time = time.time()
        self.end_time = None
        self.duration = None
        self.success = False
        self.error = None
        self.media_info = {}
        self.metadata = {}
        
    def complete(self, media_info: Dict[str, Any] = None):
        """Mark processing as complete with success"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = True
        if media_info:
            self.media_info = media_info
            
    def fail(self, error: Exception):
        """Mark processing as failed"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        self.success = False
        self.error = str(error)
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert stats to dictionary format"""
        return {
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'success': self.success,
            'error': self.error,
            'media_info': self.media_info,
            'metadata': self.metadata
        }