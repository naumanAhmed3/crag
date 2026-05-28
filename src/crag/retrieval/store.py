"""Vector store — Qdrant in local (embedded) mode.

Stored payload per chunk:
    {
        "file_path": str,
        "ordinal":   int,
        "locator":   str,        # e.g. "p. 4", "sheet: Q3 Forecast"
        "tokens":    int,
        "text":      str,        # the chunk body — kept here so retrieval
                                 # doesn't need a second round-trip
    }

Point IDs are the deterministic chunk SHA-256 from `ingest.manifest.chunk_id`.

We use `Distance.COSINE` because the default embedding model emits unit
vectors; the result ranking is identical to dot-product but the metric
name is what every operator expects.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    SearchParams,
    VectorParams,
)


def _point_uuid(chunk_id_hex: str) -> str:
    """Qdrant requires either int or UUID point IDs; map our hex sha256 to UUID5."""
    return str(uuid.UUID(chunk_id_hex[:32]))


@dataclass(frozen=True)
class Hit:
    chunk_id: str
    score: float
    payload: dict[str, Any]


class VectorStore:
    """Thin wrapper over QdrantClient in local persistent mode."""

    def __init__(self, data_dir: Path, collection: str, dim: int) -> None:
        data_dir.mkdir(parents=True, exist_ok=True)
        self.collection = collection
        self.dim = dim
        self.client = QdrantClient(path=str(data_dir / "qdrant"))
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        if not self.client.collection_exists(self.collection):
            self.client.create_collection(
                collection_name=self.collection,
                vectors_config=VectorParams(size=self.dim, distance=Distance.COSINE),
            )

    # ── mutation ─────────────────────────────────────────────────────

    def upsert(
        self,
        chunk_ids: list[str],
        vectors: np.ndarray,
        payloads: list[dict[str, Any]],
    ) -> None:
        if len(chunk_ids) == 0:
            return
        points = [
            PointStruct(
                id=_point_uuid(cid),
                vector=vec.tolist(),
                payload={**pl, "chunk_id": cid},
            )
            for cid, vec, pl in zip(chunk_ids, vectors, payloads, strict=True)
        ]
        self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def delete(self, chunk_ids: Iterable[str]) -> None:
        ids = [_point_uuid(c) for c in chunk_ids]
        if not ids:
            return
        self.client.delete(collection_name=self.collection, points_selector=ids, wait=True)

    def delete_by_file(self, file_path: str) -> int:
        """Delete all chunks belonging to a file; returns count removed."""
        flt = Filter(must=[FieldCondition(key="file_path", match=MatchValue(value=file_path))])
        # Count first for the return value (Qdrant local doesn't return delete counts).
        n = self.client.count(self.collection, count_filter=flt, exact=True).count
        if n:
            self.client.delete(self.collection, points_selector=flt, wait=True)
        return n

    # ── search ───────────────────────────────────────────────────────

    def search(self, query_vec: np.ndarray, top_k: int) -> list[Hit]:
        res = self.client.query_points(
            collection_name=self.collection,
            query=query_vec.tolist(),
            limit=top_k,
            search_params=SearchParams(hnsw_ef=128, exact=False),
            with_payload=True,
        )
        return [
            Hit(chunk_id=str(r.payload["chunk_id"]), score=float(r.score), payload=r.payload)
            for r in res.points
        ]

    # ── inspection ───────────────────────────────────────────────────

    def all_payloads(self) -> list[dict[str, Any]]:
        """Stream every payload — used by BM25 to build its in-memory index."""
        out: list[dict[str, Any]] = []
        offset: Any = None
        while True:
            points, offset = self.client.scroll(
                collection_name=self.collection,
                limit=512,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )
            for p in points:
                out.append(p.payload)
            if offset is None:
                break
        return out

    def count(self) -> int:
        return self.client.count(self.collection, exact=True).count

    # ── lifecycle ────────────────────────────────────────────────────

    def close(self) -> None:
        """Release the embedded Qdrant lock. Safe to call once per store."""
        try:
            self.client.close()
        except Exception:
            pass
