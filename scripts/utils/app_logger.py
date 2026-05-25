import os
import sqlite3
import logging
import threading
import json
import time
import functools
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Callable, TypeVar, ParamSpec

P = ParamSpec('P')
R = TypeVar('R')
F = TypeVar('F', bound=Callable[..., Any])

LOG_DIR = Path(__file__).resolve().parent.parent.parent / 'logs'
_local = threading.local()

class SQLiteHandler(logging.Handler):
    _db_lock = threading.Lock()
    _connections: Dict[str, sqlite3.Connection] = {}

    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db_for_today()

    def _db_path(self) -> Path:
        return LOG_DIR / f"log_{datetime.now().strftime('%Y-%m-%d')}.db"

    def _init_db_for_today(self):
        db_path = self._db_path()
        with self._db_lock:
            if str(db_path) not in self._connections:
                conn = sqlite3.connect(str(db_path), check_same_thread=False)
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS app_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        logger_name TEXT NOT NULL,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        module TEXT,
                        func_name TEXT,
                        line_no INTEGER,
                        thread_name TEXT,
                        trace_id TEXT,
                        duration_ms REAL,
                        extra TEXT
                    )
                ''')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_level ON app_logs(level)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON app_logs(timestamp)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_logger ON app_logs(logger_name)')
                conn.execute('CREATE INDEX IF NOT EXISTS idx_trace_id ON app_logs(trace_id)')
                conn.commit()
                self._connections[str(db_path)] = conn

    def emit(self, record: logging.LogRecord):
        try:
            db_path = self._db_path()
            with self._db_lock:
                if str(db_path) not in self._connections:
                    self._init_db_for_today()
                conn = self._connections[str(db_path)]

            extra_data = {}
            if hasattr(record, 'trace_id'):
                extra_data['trace_id'] = record.trace_id
            if hasattr(record, 'duration_ms'):
                extra_data['duration_ms'] = record.duration_ms

            conn.execute(
                '''INSERT INTO app_logs
                   (timestamp, logger_name, level, message, module, func_name, line_no, thread_name, trace_id, duration_ms, extra)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    datetime.fromtimestamp(record.created).isoformat(),
                    record.name,
                    record.levelname,
                    record.getMessage(),
                    record.module if record.module else '',
                    record.funcName if record.funcName else '',
                    record.lineno if record.lineno else 0,
                    record.threadName if record.threadName else '',
                    extra_data.get('trace_id', ''),
                    extra_data.get('duration_ms', None),
                    json.dumps(extra_data) if extra_data else '{}'
                )
            )
            conn.commit()
        except Exception:
            self.handleError(record)

    def close(self):
        with self._db_lock:
            for conn in self._connections.values():
                try:
                    conn.close()
                except Exception:
                    pass
            self._connections.clear()
        super().close()


def _get_next_trace_id() -> str:
    tid = getattr(_local, 'trace_counter', 0) + 1
    _local.trace_counter = tid
    return f"{datetime.now().strftime('%H%M%S')}_{tid:04d}"


def _trace_enter(func: Callable[..., Any], args, kwargs, level: int) -> str:
    logger = logging.getLogger(func.__module__)
    tid = _get_next_trace_id()
    _local.current_trace_id = tid

    args_repr = []
    if args:
        args_repr.extend(repr(a) for a in args)
    if kwargs:
        args_repr.extend(f"{k}={v!r}" for k, v in kwargs.items())
    call_str = f"{func.__qualname__}({', '.join(args_repr)})" if args_repr else func.__qualname__

    extra = {'trace_id': tid}
    logger.log(level, f">> {call_str}", extra=extra)
    return tid


def _trace_exit(logger: logging.Logger, tid: str, result: Any, duration: float, level: int, exc: Optional[BaseException] = None):
    if exc:
        logger.log(level, f"!!! {type(exc).__name__}: {exc} [{duration*1000:.1f}ms]",
                   extra={'trace_id': tid, 'duration_ms': duration*1000})
    else:
        result_repr = repr(result) if result is not None else ''
        msg = f"=> {result_repr} [{duration*1000:.1f}ms]" if result_repr else f"=> OK [{duration*1000:.1f}ms]"
        logger.log(level, msg, extra={'trace_id': tid, 'duration_ms': duration*1000})


def trace(level=logging.DEBUG):
    def decorator(func: F) -> F:
        is_coro = asyncio.iscoroutinefunction(func)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            tid = _trace_enter(func, args, kwargs, level)
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                duration = time.perf_counter() - start
                logger = logging.getLogger(func.__module__)
                _trace_exit(logger, tid, result, duration, level)
                return result
            except BaseException as e:
                duration = time.perf_counter() - start
                logger = logging.getLogger(func.__module__)
                _trace_exit(logger, tid, None, duration, level, exc=e)
                raise

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            tid = _trace_enter(func, args, kwargs, level)
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start
                logger = logging.getLogger(func.__module__)
                _trace_exit(logger, tid, result, duration, level)
                return result
            except BaseException as e:
                duration = time.perf_counter() - start
                logger = logging.getLogger(func.__module__)
                _trace_exit(logger, tid, None, duration, level, exc=e)
                raise

        return async_wrapper if is_coro else sync_wrapper  # type: ignore
    return decorator


def trace_module(module, level=logging.DEBUG, skip_if_has_trace=False):
    for name in dir(module):
        obj = getattr(module, name)
        if not callable(obj):
            continue
        if name.startswith('_'):
            continue
        if skip_if_has_trace and hasattr(obj, '__wrapped__'):
            continue
        try:
            setattr(module, name, trace(level=level)(obj))
        except (TypeError, AttributeError):
            pass


def setup_logging(level=logging.INFO, sqlite_level=logging.DEBUG, console_level=logging.INFO):
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    for h in root.handlers[:]:
        root.removeHandler(h)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(formatter)
    root.addHandler(console)

    sqlite = SQLiteHandler()
    sqlite.setLevel(sqlite_level)
    sqlite.setFormatter(formatter)
    root.addHandler(sqlite)

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("moviepy").setLevel(logging.WARNING)

    return root
