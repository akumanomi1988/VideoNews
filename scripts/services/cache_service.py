import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any
from pathlib import Path
import time
import shutil
from datetime import datetime, timedelta
from ..utils.app_logger import trace

class CacheManager:
    """Manages caching of generated media assets"""
    
    @trace()
    def __init__(self, cache_dir: str, max_age_days: int = 7):
        self.logger = logging.getLogger(__name__)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = timedelta(days=max_age_days)
        self.metadata_file = self.cache_dir / "cache_metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load cache metadata from disk"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"Failed to load cache metadata: {e}")
            return {}

    def _save_metadata(self):
        """Save cache metadata to disk"""
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save cache metadata: {e}")

    def _compute_hash(self, content: str, **params) -> str:
        """Compute hash for cache key"""
        # Include params in hash calculation
        hash_content = content + json.dumps(params, sort_keys=True)
        return hashlib.sha256(hash_content.encode()).hexdigest()

    def get(self, key: str, params: Dict[str, Any] = None) -> Optional[str]:
        """Get cached file path if it exists and is valid"""
        try:
            cache_key = self._compute_hash(key, **(params or {}))
            
            if cache_key not in self.metadata:
                return None
                
            entry = self.metadata[cache_key]
            cache_path = Path(entry['path'])
            
            # Check if file exists and is not too old
            if not cache_path.exists():
                del self.metadata[cache_key]
                self._save_metadata()
                return None
                
            created = datetime.fromtimestamp(entry['created'])
            if datetime.now() - created > self.max_age:
                self._remove_cached_file(cache_key)
                return None
                
            return str(cache_path)
            
        except Exception as e:
            self.logger.error(f"Failed to get from cache: {e}")
            return None

    def put(self, key: str, file_path: str, params: Dict[str, Any] = None) -> str:
        """Store file in cache"""
        try:
            cache_key = self._compute_hash(key, **(params or {}))
            cached_path = self.cache_dir / f"{cache_key}{Path(file_path).suffix}"
            
            # Copy file to cache directory
            shutil.copy2(file_path, cached_path)
            
            # Update metadata
            self.metadata[cache_key] = {
                'path': str(cached_path),
                'created': datetime.now().timestamp(),
                'original_key': key,
                'params': params
            }
            
            self._save_metadata()
            return str(cached_path)
            
        except Exception as e:
            self.logger.error(f"Failed to store in cache: {e}")
            return file_path  # Return original path on failure

    def _remove_cached_file(self, cache_key: str):
        """Remove a cached file and its metadata"""
        try:
            if cache_key in self.metadata:
                cache_path = Path(self.metadata[cache_key]['path'])
                if cache_path.exists():
                    cache_path.unlink()
                del self.metadata[cache_key]
                self._save_metadata()
        except Exception as e:
            self.logger.error(f"Failed to remove cached file: {e}")

    def cleanup(self):
        """Clean up expired cache entries"""
        try:
            current_time = datetime.now()
            expired_keys = []
            
            for key, entry in self.metadata.items():
                created = datetime.fromtimestamp(entry['created'])
                if current_time - created > self.max_age:
                    expired_keys.append(key)
            
            for key in expired_keys:
                self._remove_cached_file(key)
                
            # Remove any orphaned files
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file() and file_path.name != "cache_metadata.json":
                    file_hash = file_path.stem
                    if file_hash not in self.metadata:
                        try:
                            file_path.unlink()
                        except Exception as e:
                            self.logger.warning(f"Failed to remove orphaned file {file_path}: {e}")
                            
        except Exception as e:
            self.logger.error(f"Failed to cleanup cache: {e}")

    def clear(self):
        """Clear all cached files"""
        try:
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True)
            self.metadata.clear()
            self._save_metadata()
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            total_size = 0
            file_count = 0
            
            for entry in self.metadata.values():
                path = Path(entry['path'])
                if path.exists():
                    total_size += path.stat().st_size
                    file_count += 1
            
            return {
                'total_files': file_count,
                'total_size_mb': total_size / (1024 * 1024),
                'cache_dir': str(self.cache_dir)
            }
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {e}")
            return {}