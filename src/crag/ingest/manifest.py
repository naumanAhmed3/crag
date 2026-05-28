"""SQLite-backed manifest — the source of truth for "what is already indexed."

The manifest tracks every file we have ingested and every chunk that file
owns. Incremental ingestion uses it to decide which files to skip (mtime
+ size unchanged), reprocess (changed) or remove (deleted from disk).

Schema is intentionally tiny:

  files(path PK, mtime, size, sha256, chunk_count, ingested_at)
  chunks(id PK, file_path FK, ordinal, tokens)

`chunks.id` is the SHA-256 of `f"{file_path}::{ordinal}::{chunk_text}"` —
deterministic, stable across runs, used as the Qdrant point id.
"""

from __future__ import annotations

import hashlib
import sqlite3
import time
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path


def chunk_id(file_path: str, ordinal: int, text: str) -> str:
    """Deterministic chunk identifier — stable across ingest runs."""
    h = hashlib.sha256()
    h.update(file_path.encode())
    h.update(b"::")
    h.update(str(ordinal).encode())
    h.update(b"::")
    h.update(text.encode())
    return h.hexdigest()


def file_sha256(path: Path, _bufsize: int = 1 << 16) -> str:
    """SHA-256 of a file's bytes. Streamed; safe for large files."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(_bufsize):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class FileRecord:
    path: str
    mtime: float
    size: int
    sha256: str
    chunk_count: int
    ingested_at: float


class Manifest:
    """Per-collection ingestion manifest. Thread-safe per connection."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS files (
        path         TEXT PRIMARY KEY,
        mtime        REAL    NOT NULL,
        size         INTEGER NOT NULL,
        sha256       TEXT    NOT NULL,
        chunk_count  INTEGER NOT NULL,
        ingested_at  REAL    NOT NULL
    );
    CREATE TABLE IF NOT EXISTS chunks (
        id         TEXT PRIMARY KEY,
        file_path  TEXT    NOT NULL,
        ordinal    INTEGER NOT NULL,
        tokens     INTEGER NOT NULL,
        FOREIGN KEY (file_path) REFERENCES files(path) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_chunks_file ON chunks(file_path);
    """

    def __init__(self, db_path: Path) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._conn = sqlite3.connect(str(db_path), isolation_level=None)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.executescript(self.SCHEMA)

    # ── inspection ───────────────────────────────────────────────────

    def unchanged(self, path: Path) -> bool:
        """Has this file already been ingested with the same mtime + size?"""
        row = self._conn.execute(
            "SELECT mtime, size FROM files WHERE path = ?",
            (str(path),),
        ).fetchone()
        if row is None:
            return False
        st = path.stat()
        return row[0] == st.st_mtime and row[1] == st.st_size

    def get(self, path: Path) -> FileRecord | None:
        row = self._conn.execute(
            "SELECT path, mtime, size, sha256, chunk_count, ingested_at FROM files WHERE path = ?",
            (str(path),),
        ).fetchone()
        return FileRecord(*row) if row else None

    def all_files(self) -> list[FileRecord]:
        rows = self._conn.execute(
            "SELECT path, mtime, size, sha256, chunk_count, ingested_at FROM files ORDER BY path"
        ).fetchall()
        return [FileRecord(*r) for r in rows]

    def all_chunk_ids(self) -> list[str]:
        return [r[0] for r in self._conn.execute("SELECT id FROM chunks").fetchall()]

    def stats(self) -> dict[str, int]:
        files = self._conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        chunks = self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        tokens = self._conn.execute("SELECT COALESCE(SUM(tokens), 0) FROM chunks").fetchone()[0]
        return {"files": files, "chunks": chunks, "tokens": tokens}

    # ── mutation ─────────────────────────────────────────────────────

    @contextmanager
    def transaction(self):
        self._conn.execute("BEGIN")
        try:
            yield
        except BaseException:
            self._conn.execute("ROLLBACK")
            raise
        else:
            self._conn.execute("COMMIT")

    def upsert_file(
        self,
        path: Path,
        sha256: str,
        chunks: Iterable[tuple[str, int, int]],
    ) -> list[str]:
        """Replace any existing record for `path` with the new chunk set.

        `chunks` is an iterable of `(chunk_id, ordinal, tokens)`.

        Returns the chunk ids that existed under this path *before* the
        upsert and are no longer needed — the caller should delete them
        from the vector store.
        """
        st = path.stat()
        prior = [
            r[0]
            for r in self._conn.execute(
                "SELECT id FROM chunks WHERE file_path = ?", (str(path),)
            ).fetchall()
        ]
        chunk_list = list(chunks)
        with self.transaction():
            self._conn.execute("DELETE FROM files WHERE path = ?", (str(path),))
            self._conn.execute(
                "INSERT INTO files(path, mtime, size, sha256, chunk_count, ingested_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(path),
                    st.st_mtime,
                    st.st_size,
                    sha256,
                    len(chunk_list),
                    time.time(),
                ),
            )
            self._conn.executemany(
                "INSERT INTO chunks(id, file_path, ordinal, tokens) VALUES (?, ?, ?, ?)",
                [(cid, str(path), ord_, tokens) for cid, ord_, tokens in chunk_list],
            )
        new_ids = {cid for cid, _, _ in chunk_list}
        return [p for p in prior if p not in new_ids]

    def remove(self, path: Path) -> list[str]:
        """Drop a file's record. Returns the chunk ids to evict from the store."""
        prior = [
            r[0]
            for r in self._conn.execute(
                "SELECT id FROM chunks WHERE file_path = ?", (str(path),)
            ).fetchall()
        ]
        with self.transaction():
            self._conn.execute("DELETE FROM files WHERE path = ?", (str(path),))
            # chunks deleted by FK cascade
        return prior

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> Manifest:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
