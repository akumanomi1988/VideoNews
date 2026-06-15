import json
import hashlib
import time
import os
import threading
from pathlib import Path
from typing import Any, Optional


class FileCache:
    def __init__(self, cache_dir: str = ".temp/cache", ttl: int = 86400):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = ttl
        self._lock = threading.Lock()

    def _key_to_path(self, key: str) -> Path:
        h = hashlib.sha256(key.encode()).hexdigest()[:32]
        return self.cache_dir / f"{h}.json"

    def get(self, key: str) -> Optional[Any]:
        path = self._key_to_path(key)
        if not path.exists():
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                entry = json.load(f)
            if time.time() - entry['ts'] > self.ttl:
                path.unlink(missing_ok=True)
                return None
            return entry['data']
        except (json.JSONDecodeError, OSError):
            path.unlink(missing_ok=True)
            return None

    def set(self, key: str, data: Any) -> None:
        path = self._key_to_path(key)
        entry = {'ts': time.time(), 'data': data}
        tmp = path.with_suffix('.tmp')
        try:
            with self._lock:
                with open(tmp, 'w', encoding='utf-8') as f:
                    json.dump(entry, f, ensure_ascii=False)
                tmp.replace(path)
        except OSError:
            tmp.unlink(missing_ok=True)

    def clear(self) -> None:
        with self._lock:
            for f in self.cache_dir.glob("*.json"):
                f.unlink(missing_ok=True)
