"""Cross-encoder reranker — runs CPU-only by default.

The cross-encoder scores each (query, passage) pair end-to-end through
a small transformer; it costs more than a bi-encoder but pays back in
precision, especially on the top-K. We restrict the model to the top
~8 candidates from RRF, which keeps total reranking latency well below
the dense+sparse retrieval step on the reference rig.

Disable via `Settings.reranker_enabled = False` for retrieval-only
studies.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property


@dataclass(frozen=True)
class RerankedHit:
    chunk_id: str
    score: float
    payload: dict


class CrossEncoderReranker:
    def __init__(self, model_name: str, *, device: str | None = None) -> None:
        self.model_name = model_name
        self._device = device

    @cached_property
    def _model(self):
        from sentence_transformers import CrossEncoder

        return CrossEncoder(self.model_name, device=self._device)

    def rerank(
        self,
        query: str,
        candidates: list[tuple[str, dict]],
        top_k: int,
    ) -> list[RerankedHit]:
        """`candidates` is a list of (chunk_id, payload). Returns top-K by score."""
        if not candidates:
            return []
        pairs = [[query, p.get("text", "")] for _, p in candidates]
        scores = self._model.predict(pairs, show_progress_bar=False)
        ranked = sorted(
            (
                RerankedHit(chunk_id=cid, score=float(score), payload=payload)
                for (cid, payload), score in zip(candidates, scores, strict=True)
            ),
            key=lambda h: h.score,
            reverse=True,
        )
        return ranked[:top_k]
