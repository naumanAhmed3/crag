"""Shared infrastructure for case-study experiments.

The studies share three concerns:
  1. Build a stack with controlled overrides (model, chunking, retrieval mode).
  2. Run the gold set, measure retrieval metrics + per-query latency.
  3. Write a `results.json` next to the calling script with the metrics
     and a hardware fingerprint so anyone re-running the study can
     verify the numbers reproduce on their rig.
"""

from __future__ import annotations

import json
import os
import platform
import statistics
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from crag.config import Settings
from crag.eval.metrics import evaluate_retrieval, load_gold
from crag.retrieval.bm25 import BM25Index
from crag.retrieval.embed import Embedder
from crag.retrieval.rerank import CrossEncoderReranker
from crag.retrieval.search import HybridRetriever, RetrievedChunk
from crag.retrieval.store import VectorStore

REPO_ROOT = Path(__file__).resolve().parent.parent
GOLD_PATH = REPO_ROOT / "src" / "crag" / "eval" / "gold.yaml"


# ── stack assembly ─────────────────────────────────────────────────────


@dataclass
class Stack:
    settings: Settings
    embedder: Embedder
    store: VectorStore
    bm25: BM25Index
    reranker: CrossEncoderReranker | None


def bootstrap(**overrides) -> Stack:
    s = Settings(**overrides)
    s.data_dir.mkdir(parents=True, exist_ok=True)
    embedder = Embedder(s.embedding_model)
    store = VectorStore(s.data_dir, collection="default", dim=embedder.dim)
    bm25 = BM25Index(store.all_payloads())
    reranker = CrossEncoderReranker(s.reranker_model) if s.reranker_enabled else None
    return Stack(s, embedder, store, bm25, reranker)


# ── retrieval modes for the studies ────────────────────────────────────


def dense_only(stack: Stack, query: str) -> list[RetrievedChunk]:
    vec = stack.embedder.encode_one(query)
    hits = stack.store.search(vec, top_k=stack.settings.final_top_k)
    return [
        RetrievedChunk(
            chunk_id=h.chunk_id,
            text=h.payload.get("text", ""),
            file_path=h.payload.get("file_path", ""),
            locator=h.payload.get("locator", ""),
            score=h.score,
            dense_rank=rank,
            sparse_rank=None,
        )
        for rank, h in enumerate(hits, start=1)
    ]


def bm25_only(stack: Stack, query: str) -> list[RetrievedChunk]:
    hits = stack.bm25.search(query, top_k=stack.settings.final_top_k)
    out: list[RetrievedChunk] = []
    for rank, h in enumerate(hits, start=1):
        pl = stack.bm25.payload(h.chunk_id) or {}
        out.append(
            RetrievedChunk(
                chunk_id=h.chunk_id,
                text=pl.get("text", ""),
                file_path=pl.get("file_path", ""),
                locator=pl.get("locator", ""),
                score=h.score,
                dense_rank=None,
                sparse_rank=rank,
            )
        )
    return out


def hybrid(stack: Stack, query: str) -> list[RetrievedChunk]:
    """Hybrid without the reranker."""
    s = stack.settings
    retriever = HybridRetriever(s, stack.embedder, stack.store, stack.bm25, reranker=None)
    # Force-skip the reranker by overriding the flag locally.
    s_copy = s.model_copy(update={"reranker_enabled": False})
    retriever.settings = s_copy
    return retriever.search(query)


def hybrid_rerank(stack: Stack, query: str) -> list[RetrievedChunk]:
    """Full hybrid + cross-encoder rerank."""
    s = stack.settings
    assert stack.reranker is not None, "rerank requested but reranker is disabled"
    retriever = HybridRetriever(s, stack.embedder, stack.store, stack.bm25, stack.reranker)
    return retriever.search(query)


# ── measurement ────────────────────────────────────────────────────────


def time_retriever(
    retriever_fn: Callable[[str], list[RetrievedChunk]],
    questions: list[str],
) -> dict:
    """Return p50 / p95 / mean latency in ms across the question set."""
    latencies: list[float] = []
    for q in questions:
        t0 = time.perf_counter()
        retriever_fn(q)
        latencies.append((time.perf_counter() - t0) * 1000)
    latencies.sort()
    if not latencies:
        return {"p50_ms": 0.0, "p95_ms": 0.0, "mean_ms": 0.0, "n": 0}
    p50_idx = max(0, len(latencies) // 2 - 1)
    p95_idx = max(0, int(0.95 * len(latencies)) - 1)
    return {
        "p50_ms": round(latencies[p50_idx], 1),
        "p95_ms": round(latencies[p95_idx], 1),
        "mean_ms": round(statistics.fmean(latencies), 1),
        "n": len(latencies),
    }


# ── hardware fingerprint ───────────────────────────────────────────────


def hardware_fingerprint() -> dict:
    import psutil

    try:
        ram_gb = round(psutil.virtual_memory().total / (1024**3), 1)
    except Exception:
        ram_gb = None

    fp = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or platform.machine(),
        "python": sys.version.split()[0],
        "ram_gb": ram_gb,
        "cpu_count": os.cpu_count(),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "git_sha": _git_sha(),
        "torch": _torch_version(),
        "numpy": np.__version__,
    }
    return fp


def _git_sha() -> str | None:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT, stderr=subprocess.DEVNULL
            )
            .decode()
            .strip()
        )
    except Exception:
        return None


def _torch_version() -> str | None:
    try:
        import torch

        return torch.__version__
    except Exception:
        return None


# ── one-line study runner ──────────────────────────────────────────────


def run_and_save(
    study_id: str,
    study_dir: Path,
    runs: list[dict],
    *,
    notes: str = "",
) -> Path:
    """Write `study_dir/results.json` with `runs` (a list of named result dicts)."""
    output = {
        "study_id": study_id,
        "notes": notes,
        "hardware": hardware_fingerprint(),
        "runs": runs,
    }
    out_path = study_dir / "results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    return out_path


def run_metrics_for(
    label: str,
    retriever_fn: Callable[[str], list[RetrievedChunk]],
    *,
    top_k: int = 5,
) -> dict:
    """Helper: run gold + capture metrics + timing under one label."""
    gold = load_gold(GOLD_PATH)
    metrics = evaluate_retrieval(gold, retriever_fn, top_k=top_k)
    timing = time_retriever(retriever_fn, [g.question for g in gold])
    return {"label": label, "metrics": metrics.asdict(), "timing": timing}
