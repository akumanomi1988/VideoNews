import os
import shutil
import logging
from typing import List, Optional
from pathlib import Path
import tempfile
from datetime import datetime, timedelta

from ..interfaces import StorageManager
from ..utils.app_logger import trace

class LocalStorageManager(StorageManager):
    """Manages local file storage and cleanup"""
    
    @trace()
    def __init__(self, base_dir: str, max_age_days: int = 7):
        self.logger = logging.getLogger(__name__)
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.max_age = timedelta(days=max_age_days)
        self._temp_dirs: List[str] = []
        self._managed_files: List[str] = []

    @trace()
    def create_temp_dir(self) -> str:
        """Create a temporary directory for processing"""
        try:
            temp_dir = tempfile.mkdtemp(dir=str(self.base_dir))
            self._temp_dirs.append(temp_dir)
            return temp_dir
        except Exception as e:
            self.logger.error(f"Failed to create temp directory: {e}")
            raise

    def save_file(self, source_path: str, target_dir: Optional[str] = None) -> str:
        """Save a file to managed storage"""
        try:
            source = Path(source_path)
            if not source.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")

            # Determine target directory
            target_base = Path(target_dir) if target_dir else self.base_dir
            target_base.mkdir(parents=True, exist_ok=True)

            # Create target path preserving extension
            target = target_base / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{source.name}"
            
            # Copy file
            shutil.copy2(source_path, str(target))
            self._managed_files.append(str(target))
            
            return str(target)
        except Exception as e:
            self.logger.error(f"Failed to save file {source_path}: {e}")
            raise

    def delete_file(self, file_path: str) -> bool:
        """Delete a managed file"""
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
                if str(path) in self._managed_files:
                    self._managed_files.remove(str(path))
                return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to delete file {file_path}: {e}")
            return False

    def cleanup(self, force: bool = False):
        """Clean up temporary and old files"""
        try:
            # Clean up temporary directories
            for temp_dir in self._temp_dirs:
                try:
                    if Path(temp_dir).exists():
                        shutil.rmtree(temp_dir)
                except Exception as e:
                    self.logger.warning(f"Failed to remove temp dir {temp_dir}: {e}")
            self._temp_dirs.clear()

            # Clean up old files if not force cleanup
            if not force:
                current_time = datetime.now()
                for file_path in self._managed_files[:]:
                    try:
                        path = Path(file_path)
                        if not path.exists():
                            self._managed_files.remove(file_path)
                            continue

                        mtime = datetime.fromtimestamp(path.stat().st_mtime)
                        if current_time - mtime > self.max_age:
                            path.unlink()
                            self._managed_files.remove(file_path)
                    except Exception as e:
                        self.logger.warning(f"Failed to cleanup file {file_path}: {e}")
            # Force cleanup - remove all managed files
            else:
                for file_path in self._managed_files[:]:
                    try:
                        path = Path(file_path)
                        if path.exists():
                            path.unlink()
                        self._managed_files.remove(file_path)
                    except Exception as e:
                        self.logger.warning(f"Failed to force cleanup file {file_path}: {e}")

            # Clean up empty directories
            self._cleanup_empty_dirs(self.base_dir)

        except Exception as e:
            self.logger.error(f"Cleanup operation failed: {e}")
            raise

    def _cleanup_empty_dirs(self, directory: Path):
        """Recursively remove empty directories"""
        if not directory.exists():
            return

        for item in directory.iterdir():
            if item.is_dir():
                self._cleanup_empty_dirs(item)

        try:
            directory.rmdir()  # Will only succeed if directory is empty
        except OSError:
            pass  # Directory not empty or other error, ignore

    def get_storage_stats(self) -> dict:
        """Get storage statistics"""
        try:
            total_size = 0
            file_count = 0
            oldest_file = None
            newest_file = None

            for file_path in self._managed_files:
                try:
                    path = Path(file_path)
                    if not path.exists():
                        continue

                    stat = path.stat()
                    total_size += stat.st_size
                    file_count += 1

                    mtime = datetime.fromtimestamp(stat.st_mtime)
                    if not oldest_file or mtime < oldest_file:
                        oldest_file = mtime
                    if not newest_file or mtime > newest_file:
                        newest_file = mtime

                except Exception as e:
                    self.logger.warning(f"Failed to get stats for {file_path}: {e}")

            return {
                'total_files': file_count,
                'total_size_mb': total_size / (1024 * 1024),
                'oldest_file': oldest_file.isoformat() if oldest_file else None,
                'newest_file': newest_file.isoformat() if newest_file else None,
                'temp_dirs': len(self._temp_dirs)
            }

        except Exception as e:
            self.logger.error(f"Failed to get storage stats: {e}")
            return {}