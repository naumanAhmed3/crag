"""Embedding model wrapper.

A thin adapter over `sentence_transformers.SentenceTransformer`. Lazy
loads the model on first use so unrelated CLI commands (`crag stats`,
`crag --help`) stay fast.

The default model (`BAAI/bge-small-en-v1.5`) emits L2-normalised vectors,
so cosine similarity collapses to a dot product. Qdrant cosine distance
yields the same ranking — we configure the store with COSINE for clarity.
"""

from __future__ import annotations

from functools import cached_property

import numpy as np


class Embedder:
    """Sentence-transformer adapter; suitable for ingest + query embedding."""

    def __init__(self, model_name: str, *, device: str | None = None) -> None:
        self.model_name = model_name
        self._device = device

    @cached_property
    def _model(self):  # delayed import for fast CLI startup
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(self.model_name, device=self._device)

    @property
    def dim(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    def encode(
        self,
        texts: list[str],
        *,
        batch_size: int = 32,
        normalize: bool = True,
    ) -> np.ndarray:
        """Return an `(N, dim)` float32 ndarray."""
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        vecs = self._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
        )
        return vecs.astype(np.float32)

    def encode_one(self, text: str, *, normalize: bool = True) -> np.ndarray:
        return self.encode([text], normalize=normalize)[0]
