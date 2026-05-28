"""Sparse retrieval — BM25 over chunk text.

A pure-Python BM25 (via `rank_bm25`) built from the vector store payloads.
At our target scales (tens of thousands to a few hundred thousand chunks)
the in-memory representation is small (~50 MB per 100k chunks of mid-length
text) and rebuild is fast (~5 s on the reference rig).

Larger corpora (millions of chunks, the 2 TB regime) would graduate to
Tantivy or a Qdrant sparse index — `docs/SCALING.md` documents the path.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokenise(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text)]


@dataclass(frozen=True)
class SparseHit:
    chunk_id: str
    score: float


class BM25Index:
    """In-memory BM25 keyed by chunk id."""

    def __init__(self, payloads: Iterable[dict]) -> None:
        items = list(payloads)
        self._chunk_ids: list[str] = [str(p["chunk_id"]) for p in items]
        self._payloads: dict[str, dict] = {p["chunk_id"]: p for p in items}
        corpus = [_tokenise(p.get("text", "")) for p in items]
        self._bm25 = BM25Okapi(corpus) if corpus else None
        self._size = len(items)

    def __len__(self) -> int:
        return self._size

    def payload(self, chunk_id: str) -> dict | None:
        return self._payloads.get(chunk_id)

    def search(self, query: str, top_k: int) -> list[SparseHit]:
        if self._bm25 is None:
            return []
        scores = self._bm25.get_scores(_tokenise(query))
        if len(scores) == 0:
            return []
        # argpartition + sort top-K — faster than full sort at scale.
        top_k = min(top_k, len(scores))
        idx = scores.argpartition(-top_k)[-top_k:]
        idx = idx[scores[idx].argsort()[::-1]]
        return [SparseHit(chunk_id=self._chunk_ids[i], score=float(scores[i])) for i in idx]
