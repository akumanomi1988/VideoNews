"""Persistent, atomic deduplication of article production attempts.

The registry is intentionally conservative about uncertain publication: retrying
an upload after a connection drop can produce a duplicate public video.
Only failures *before* uploading are automatically retriable.
"""
from __future__ import annotations

import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path


class DuplicateJobError(RuntimeError):
    """An article is already processing, completed or requires reconciliation."""


def _database_path() -> Path:
    return Path(os.getenv("VIDEO_JOBS_DB", "videonews_jobs.sqlite3"))


@contextmanager
def _connection():
    path = _database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=30, isolation_level=None)
    connection.execute("PRAGMA busy_timeout = 30000")
    # WAL persists on disk; another process may set it concurrently.
    # BEGIN IMMEDIATE still serializes claims for correctness.
    try:
        connection.execute("PRAGMA journal_mode = WAL")
    except sqlite3.OperationalError as exc:
        if "locked" not in str(exc).lower():
            connection.close()
            raise
    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS article_jobs (
                source_url TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                format TEXT NOT NULL,
                state TEXT NOT NULL,
                output TEXT,
                last_error TEXT,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        yield connection
    finally:
        connection.close()


def claim(source_url: str, format: str) -> str:
    """Reserve a URL transactionally across processes; retry only safe failures."""
    if not source_url or format not in ("short", "long"):
        raise ValueError("A valid source URL and format are required")
    job_id = uuid.uuid4().hex
    now = time.time()
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            row = db.execute(
                "SELECT state FROM article_jobs WHERE source_url = ?", (source_url,)
            ).fetchone()
            if row and row[0] != "FAILED":
                raise DuplicateJobError(
                    f"This URL is already registered (state={row[0]}). "
                    "Use the job registry to reconcile before creating another video."
                )
            if row:
                db.execute(
                    """UPDATE article_jobs SET job_id=?, format=?, state='RESERVED',
                       output=NULL, last_error=NULL, updated_at=? WHERE source_url=?""",
                    (job_id, format, now, source_url),
                )
            else:
                db.execute(
                    """INSERT INTO article_jobs
                       (source_url, job_id, format, state, created_at, updated_at)
                       VALUES (?, ?, ?, 'RESERVED', ?, ?)""",
                    (source_url, job_id, format, now, now),
                )
            db.execute("COMMIT")
            return job_id
        except BaseException:
            db.execute("ROLLBACK")
            raise


def advance(job_id: str, state: str) -> None:
    """Save durable milestone prior to high-risk publication attempts."""
    if state not in ("PREPARING", "UPLOADING"):
        raise ValueError("Unsupported job milestone")
    with _connection() as db:
        cursor = db.execute(
            """UPDATE article_jobs SET state=?, updated_at=?
               WHERE job_id=? AND state IN ('RESERVED', 'PREPARING')""",
            (state, time.time(), job_id),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("Unexpected job state change; refusing to publish")


def complete(job_id: str, output: str) -> None:
    if not output:
        raise ValueError("Output reference is required")
    with _connection() as db:
        cursor = db.execute(
            """UPDATE article_jobs SET state='COMPLETED', output=?, updated_at=?
               WHERE job_id=? AND state IN ('RESERVED', 'PREPARING', 'UPLOADING')""",
            (output, time.time(), job_id),
        )
        if cursor.rowcount != 1:
            raise RuntimeError("Could not commit completed job state")


def fail(job_id: str, error: str) -> None:
    """A failed upload remains blocked for manual reconciliation."""
    with _connection() as db:
        db.execute(
            """UPDATE article_jobs
               SET state=CASE WHEN state='UPLOADING' THEN 'NEEDS_REVIEW' ELSE 'FAILED' END,
                   last_error=?, updated_at=?
               WHERE job_id=? AND state NOT IN ('COMPLETED', 'NEEDS_REVIEW')""",
            (error[:1500], time.time(), job_id),
        )


def get(source_url: str):
    with _connection() as db:
        row = db.execute(
            """SELECT job_id, format, state, output, last_error, created_at, updated_at
               FROM article_jobs WHERE source_url = ?""",
            (source_url,),
        ).fetchone()
        if not row:
            return None
        keys = ("job_id", "format", "state", "output", "last_error", "created_at", "updated_at")
        return dict(zip(keys, row))


def review_required():
    """Surface crashed or publication-uncertain jobs for operator reconciliation."""
    with _connection() as db:
        rows = db.execute(
            """SELECT source_url, job_id, state, updated_at FROM article_jobs
               WHERE state NOT IN ('COMPLETED', 'FAILED') ORDER BY updated_at DESC"""
        ).fetchall()
        return [
            {"source_url": url, "job_id": job, "state": state, "updated_at": stamp}
            for url, job, state, stamp in rows
        ]


def reconcile(source_url: str, *, published: bool, reference: str = "") -> None:
    """Explicit operator resolution after verifying the remote platform.

    published=True: a real external publication ID/URL has been confirmed.
    published=False: operator explicitly verified that nothing was published.
    This operation is deliberately unavailable through model-callable interfaces.
    """
    if published and not reference:
        raise ValueError("Verified published outcome requires a remote reference")
    with _connection() as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            row = db.execute(
                "SELECT state FROM article_jobs WHERE source_url=?", (source_url,)
            ).fetchone()
            if not row or row[0] not in ("RESERVED", "PREPARING", "UPLOADING", "NEEDS_REVIEW"):
                raise ValueError("No unresolved job exists for this URL")
            if published:
                db.execute(
                    """UPDATE article_jobs SET state='COMPLETED', output=?, last_error=NULL,
                       updated_at=? WHERE source_url=?""",
                    (reference, time.time(), source_url),
                )
            else:
                db.execute(
                    """UPDATE article_jobs SET state='FAILED', last_error='Operator confirmed no upload',
                       updated_at=? WHERE source_url=?""",
                    (time.time(), source_url),
                )
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise
