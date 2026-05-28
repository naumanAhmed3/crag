"""Typed, env-driven configuration for crag.

All knobs the system exposes live here. The defaults below are the values
that the case studies in `studies/` converged on — overriding any of them
is one environment variable away (or one `Settings(...)` call from code).

The hardware-relevant defaults assume the brief's target box: a ~6 GB-VRAM
laptop GPU. Where the value is constrained by that hardware, the docstring
calls it out so anyone running on a larger rig knows what to relax.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Environment-prefix: `CRAG_`."""

    model_config = SettingsConfigDict(
        env_prefix="CRAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── paths ───────────────────────────────────────────────────────────
    data_dir: Path = Field(
        default=Path("./data"),
        description="Root for the local Qdrant store + SQLite manifest.",
    )

    # ── embedding ──────────────────────────────────────────────────────
    embedding_model: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="sentence-transformers model id. Default is CPU-fast and "
        "MTEB-strong at 33 MB / 384-dim. Swap for `bge-base-en-v1.5` if you "
        "have CPU headroom; `bge-large-en-v1.5` only on a discrete GPU.",
    )
    embedding_dim: int = Field(default=384)
    embedding_batch_size: int = Field(default=32)

    # ── chunking ───────────────────────────────────────────────────────
    chunk_tokens: int = Field(
        default=512,
        description="Target chunk size in tokens (tiktoken cl100k_base).",
    )
    chunk_overlap: int = Field(
        default=64,
        description="Overlap between consecutive chunks, in tokens.",
    )
    chunk_strategy: Literal["fixed", "sentence-snap"] = Field(
        default="sentence-snap",
        description="`sentence-snap` ends chunks at the nearest sentence "
        "boundary within ±15% of `chunk_tokens`; `fixed` is hard token-cut.",
    )

    # ── retrieval ──────────────────────────────────────────────────────
    dense_top_k: int = Field(default=20, description="Dense candidates per query.")
    sparse_top_k: int = Field(default=20, description="BM25 candidates per query.")
    rrf_k: int = Field(default=60, description="Reciprocal Rank Fusion constant.")
    rerank_top_k: int = Field(default=8, description="Top-K passed to reranker.")
    final_top_k: int = Field(default=5, description="Top-K returned to caller.")

    # ── reranker ───────────────────────────────────────────────────────
    reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3")
    reranker_enabled: bool = Field(default=True)

    # ── llm ────────────────────────────────────────────────────────────
    llm_backend: Literal["ollama", "llamacpp", "none"] = Field(
        default="ollama",
        description="`none` runs retrieval-only — useful for retrieval studies "
        "(MRR / Recall@K) without standing up a generation model.",
    )
    llm_model: str = Field(
        default="qwen2.5:7b-instruct-q4_K_M",
        description="Ollama model tag, or path to GGUF file for llamacpp.",
    )
    llm_max_tokens: int = Field(default=600)
    llm_temperature: float = Field(default=0.2)
    llm_context_window: int = Field(default=8192)

    # ── grounding ──────────────────────────────────────────────────────
    refuse_off_corpus: bool = Field(
        default=True,
        description="When True, the answer prompt instructs the model to "
        "refuse if the retrieved passages don't support an answer.",
    )

    # ── observability ──────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")


def settings() -> Settings:
    """Build a fresh Settings instance. Cheap; no I/O."""
    return Settings()
