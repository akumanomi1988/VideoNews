from flask import Flask, render_template, jsonify
import logging
from pathlib import Path
from typing import Dict, Any, List
import json
import time
from datetime import datetime

app = Flask(__name__)
logger = logging.getLogger(__name__)

class DashboardMetrics:
    def __init__(self, metrics_dir: str = 'metrics'):
        self.metrics_dir = Path(metrics_dir)
        
    def get_active_pipelines(self) -> List[Dict[str, Any]]:
        """Get metrics for all active pipelines"""
        active_pipelines = []
        try:
            for file in self.metrics_dir.glob('*.json'):
                try:
                    with open(file, 'r') as f:
                        metrics = json.load(f)
                        if not metrics.get('is_completed') and not metrics.get('is_failed'):
                            active_pipelines.append(metrics)
                except Exception as e:
                    logger.error(f"Failed to read metrics file {file}: {e}")
        except Exception as e:
            logger.error(f"Failed to list metrics files: {e}")
        
        return active_pipelines

    def get_recent_pipelines(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics for recently completed pipelines"""
        recent_pipelines = []
        current_time = time.time()
        max_age = hours * 3600
        
        try:
            for file in self.metrics_dir.glob('*.json'):
                if (current_time - file.stat().st_mtime) <= max_age:
                    try:
                        with open(file, 'r') as f:
                            metrics = json.load(f)
                            recent_pipelines.append(metrics)
                    except Exception as e:
                        logger.error(f"Failed to read metrics file {file}: {e}")
        except Exception as e:
            logger.error(f"Failed to list metrics files: {e}")
        
        return sorted(
            recent_pipelines,
            key=lambda x: x.get('start_time', 0),
            reverse=True
        )

    def get_pipeline_metrics(self, pipeline_id: str) -> Dict[str, Any]:
        """Get metrics for a specific pipeline"""
        try:
            file_path = self.metrics_dir / f"{pipeline_id}.json"
            if not file_path.exists():
                return {}
            
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read metrics for pipeline {pipeline_id}: {e}")
            return {}

    def get_summary_metrics(self) -> Dict[str, Any]:
        """Get summary metrics for all pipelines"""
        try:
            pipelines = self.get_recent_pipelines(24)
            total_count = len(pipelines)
            completed_count = sum(1 for p in pipelines if p.get('is_completed', False))
            failed_count = sum(1 for p in pipelines if p.get('is_failed', False))
            active_count = sum(1 for p in pipelines if not p.get('is_completed') and not p.get('is_failed'))
            
            durations = [p.get('duration', 0) for p in pipelines if p.get('is_completed')]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            return {
                'total_pipelines': total_count,
                'completed_pipelines': completed_count,
                'failed_pipelines': failed_count,
                'active_pipelines': active_count,
                'average_duration': avg_duration
            }
        except Exception as e:
            logger.error(f"Failed to generate summary metrics: {e}")
            return {}

dashboard_metrics = DashboardMetrics()

@app.route('/')
def index():
    """Render dashboard homepage"""
    return render_template(
        'dashboard.html',
        summary=dashboard_metrics.get_summary_metrics(),
        active_pipelines=dashboard_metrics.get_active_pipelines(),
        recent_pipelines=dashboard_metrics.get_recent_pipelines()
    )

@app.route('/api/metrics/summary')
def get_summary():
    """API endpoint for summary metrics"""
    return jsonify(dashboard_metrics.get_summary_metrics())

@app.route('/api/metrics/active')
def get_active():
    """API endpoint for active pipeline metrics"""
    return jsonify(dashboard_metrics.get_active_pipelines())

@app.route('/api/metrics/recent')
def get_recent():
    """API endpoint for recent pipeline metrics"""
    return jsonify(dashboard_metrics.get_recent_pipelines())

@app.route('/api/metrics/pipeline/<pipeline_id>')
def get_pipeline(pipeline_id: str):
    """API endpoint for specific pipeline metrics"""
    return jsonify(dashboard_metrics.get_pipeline_metrics(pipeline_id))

def create_app(metrics_dir: str = 'metrics') -> Flask:
    """Create and configure Flask application"""
    global dashboard_metrics
    dashboard_metrics = DashboardMetrics(metrics_dir)
    return app

if __name__ == '__main__':
    app.run(debug=True)