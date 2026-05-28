"""Hybrid retrieval orchestrator.

Pipeline (defaults from `Settings`):

    query
      ├─ dense    top-K (Qdrant cosine)
      └─ sparse   top-K (BM25)
              └─ RRF fusion (k = 60)
                      └─ cross-encoder rerank (optional)
                              └─ final top-K

Reciprocal Rank Fusion (RRF) is the right choice here because the dense
and sparse scores live on different scales — RRF only cares about rank
position, so there's nothing to normalise. The constant `k` damps the
contribution of low-ranked items; the literature settles on ~60.
"""

from __future__ import annotations

from dataclasses import dataclass

from crag.config import Settings
from crag.retrieval.bm25 import BM25Index
from crag.retrieval.embed import Embedder
from crag.retrieval.rerank import CrossEncoderReranker
from crag.retrieval.store import Hit, VectorStore


@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    text: str
    file_path: str
    locator: str
    score: float  # final fused / reranked score
    dense_rank: int | None  # 1-indexed rank from the dense leg; None if absent
    sparse_rank: int | None
    rerank_score: float | None = None


def _rrf(
    dense: list[Hit],
    sparse_ids: list[str],
    k: int,
) -> dict[str, tuple[float, int | None, int | None]]:
    """Return {chunk_id: (rrf_score, dense_rank, sparse_rank)}."""
    rrf: dict[str, float] = {}
    dense_rank: dict[str, int] = {}
    sparse_rank: dict[str, int] = {}
    for rank, hit in enumerate(dense, start=1):
        rrf[hit.chunk_id] = rrf.get(hit.chunk_id, 0.0) + 1.0 / (k + rank)
        dense_rank[hit.chunk_id] = rank
    for rank, cid in enumerate(sparse_ids, start=1):
        rrf[cid] = rrf.get(cid, 0.0) + 1.0 / (k + rank)
        sparse_rank[cid] = rank
    return {cid: (score, dense_rank.get(cid), sparse_rank.get(cid)) for cid, score in rrf.items()}


class HybridRetriever:
    """Composes dense + sparse + (optional) reranker per the active Settings."""

    def __init__(
        self,
        settings: Settings,
        embedder: Embedder,
        store: VectorStore,
        bm25: BM25Index,
        reranker: CrossEncoderReranker | None = None,
    ) -> None:
        self.settings = settings
        self.embedder = embedder
        self.store = store
        self.bm25 = bm25
        self.reranker = reranker

    def search(self, query: str) -> list[RetrievedChunk]:
        s = self.settings

        # ── stage 1: parallel retrieval (logically; both are fast on CPU) ──
        qvec = self.embedder.encode_one(query)
        dense_hits = self.store.search(qvec, top_k=s.dense_top_k)
        sparse_hits = self.bm25.search(query, top_k=s.sparse_top_k)

        # ── stage 2: fuse ──
        fused = _rrf(dense_hits, [h.chunk_id for h in sparse_hits], s.rrf_k)
        # Order fused candidates by RRF score and take rerank_top_k for the
        # cross-encoder pass (or final_top_k if the reranker is disabled).
        ordered_ids = sorted(fused, key=lambda c: fused[c][0], reverse=True)

        # Resolve payloads — prefer the dense hit payload, fall back to BM25.
        payload_by_id: dict[str, dict] = {h.chunk_id: h.payload for h in dense_hits}
        for sh in sparse_hits:
            payload_by_id.setdefault(sh.chunk_id, self.bm25.payload(sh.chunk_id) or {})

        candidates = [(cid, payload_by_id[cid]) for cid in ordered_ids if cid in payload_by_id]

        # ── stage 3: rerank (optional) ──
        if self.reranker and s.reranker_enabled:
            top = candidates[: s.rerank_top_k]
            reranked = self.reranker.rerank(query, top, top_k=s.final_top_k)
            final = [
                RetrievedChunk(
                    chunk_id=r.chunk_id,
                    text=r.payload.get("text", ""),
                    file_path=r.payload.get("file_path", ""),
                    locator=r.payload.get("locator", ""),
                    score=r.score,
                    dense_rank=fused[r.chunk_id][1],
                    sparse_rank=fused[r.chunk_id][2],
                    rerank_score=r.score,
                )
                for r in reranked
            ]
            return final

        # Reranker off — return fused top-K directly.
        out: list[RetrievedChunk] = []
        for cid in ordered_ids[: s.final_top_k]:
            pl = payload_by_id[cid]
            score, drank, srank = fused[cid]
            out.append(
                RetrievedChunk(
                    chunk_id=cid,
                    text=pl.get("text", ""),
                    file_path=pl.get("file_path", ""),
                    locator=pl.get("locator", ""),
                    score=score,
                    dense_rank=drank,
                    sparse_rank=srank,
                )
            )
        return out
