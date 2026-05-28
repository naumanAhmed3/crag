"""End-to-end ingestion: walk a path → diff against manifest → parse → chunk → embed → upsert.

The pipeline is deliberately idempotent and small. A second run with no
changes is fast (mtime checks only); a run with a few changed files
embeds only those files; a deleted file is detected and its chunks
removed from both manifest and vector store.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from crag.config import Settings
from crag.ingest.chunker import Chunk, chunk_text
from crag.ingest.manifest import Manifest, chunk_id, file_sha256
from crag.ingest.parsers import SUPPORTED_EXTENSIONS, parse
from crag.retrieval.embed import Embedder
from crag.retrieval.store import VectorStore


@dataclass
class IngestStats:
    files_seen: int = 0
    files_skipped_unchanged: int = 0
    files_skipped_unsupported: int = 0
    files_added: int = 0
    files_updated: int = 0
    files_removed: int = 0
    chunks_added: int = 0
    chunks_removed: int = 0
    embed_seconds: float = 0.0
    total_seconds: float = 0.0
    errors: list[tuple[str, str]] = field(default_factory=list)

    def asdict(self) -> dict:
        return {
            "files_seen": self.files_seen,
            "files_skipped_unchanged": self.files_skipped_unchanged,
            "files_skipped_unsupported": self.files_skipped_unsupported,
            "files_added": self.files_added,
            "files_updated": self.files_updated,
            "files_removed": self.files_removed,
            "chunks_added": self.chunks_added,
            "chunks_removed": self.chunks_removed,
            "embed_seconds": round(self.embed_seconds, 3),
            "total_seconds": round(self.total_seconds, 3),
            "errors": self.errors,
        }


def _walk(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    return [p for p in root.rglob("*") if p.is_file()]


def ingest(
    paths: list[Path],
    *,
    settings: Settings,
    embedder: Embedder,
    store: VectorStore,
    manifest: Manifest,
    collection_root: Path | None = None,
) -> IngestStats:
    """Ingest `paths` (files or dirs) into the configured store + manifest.

    `collection_root` is the conceptual root used for deletion-detection:
    if a file under it is in the manifest but no longer on disk, its chunks
    are removed. Defaults to the parent of the first argument when only
    one root is passed.
    """
    t0 = time.perf_counter()
    stats = IngestStats()

    discovered: list[Path] = []
    for p in paths:
        discovered.extend(_walk(p))
    # Track absolute paths so the manifest is stable across cwd changes.
    discovered = [p.resolve() for p in discovered]

    # ── ingest / update ──────────────────────────────────────────────
    on_disk: set[str] = set()
    for path in discovered:
        stats.files_seen += 1
        on_disk.add(str(path))

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            stats.files_skipped_unsupported += 1
            continue

        existed = manifest.get(path) is not None
        if existed and manifest.unchanged(path):
            stats.files_skipped_unchanged += 1
            continue

        try:
            blocks = parse(path)
        except Exception as e:
            stats.errors.append((str(path), f"parse: {e!s}"))
            continue
        if not blocks:
            continue

        # Chunk each block, keeping a continuous ordinal across the file.
        chunks: list[Chunk] = []
        ord_ = 0
        for block in blocks:
            for c in chunk_text(
                block.text,
                target_tokens=settings.chunk_tokens,
                overlap_tokens=settings.chunk_overlap,
                strategy=settings.chunk_strategy,
                locator=block.locator,
            ):
                chunks.append(Chunk(ordinal=ord_, text=c.text, tokens=c.tokens, locator=c.locator))
                ord_ += 1

        if not chunks:
            continue

        # Embed.
        t_e = time.perf_counter()
        vectors = embedder.encode(
            [c.text for c in chunks], batch_size=settings.embedding_batch_size
        )
        stats.embed_seconds += time.perf_counter() - t_e

        # Identifiers + payloads.
        chunk_ids = [chunk_id(str(path), c.ordinal, c.text) for c in chunks]
        payloads = [
            {
                "file_path": str(path),
                "ordinal": c.ordinal,
                "locator": c.locator,
                "tokens": c.tokens,
                "text": c.text,
            }
            for c in chunks
        ]

        # Upsert into the manifest first (computes which old chunks to evict),
        # then mirror that into the vector store.
        sha = file_sha256(path)
        old_chunk_ids = manifest.upsert_file(
            path,
            sha,
            [(cid, c.ordinal, c.tokens) for cid, c in zip(chunk_ids, chunks, strict=True)],
        )
        if old_chunk_ids:
            store.delete(old_chunk_ids)
            stats.chunks_removed += len(old_chunk_ids)
        store.upsert(chunk_ids, np.asarray(vectors), payloads)

        if existed:
            stats.files_updated += 1
        else:
            stats.files_added += 1
        stats.chunks_added += len(chunks)

    # ── deletion detection ───────────────────────────────────────────
    # If a root was provided (or inferred), scope the deletion check to it
    # so we never accidentally evict chunks belonging to a different corpus.
    scopes: list[str] = (
        [str(collection_root.resolve())] if collection_root else [str(p.resolve()) for p in paths]
    )
    for fr in manifest.all_files():
        if fr.path in on_disk:
            continue
        if not any(fr.path.startswith(scope) for scope in scopes):
            continue
        evicted = manifest.remove(Path(fr.path))
        if evicted:
            store.delete(evicted)
            stats.chunks_removed += len(evicted)
        stats.files_removed += 1

    stats.total_seconds = time.perf_counter() - t0
    return stats
