"""Round 03 — Chunking grid: target size × boundary strategy.

For each chunking config:
  1. Wipe the index for that config.
  2. Re-ingest the bundled corpus with that config.
  3. Run the gold set; capture metrics + latency.
  4. Record ingest stats (chunks added, embed seconds).

Each config gets its own sub-directory under data/study03/<slug>/ so
the configs are isolated and the original data/ directory is never
touched.

Run:
    uv run python studies/03-chunking-grid/experiment.py
Output:
    studies/03-chunking-grid/results.json
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from _common import (
    REPO_ROOT,
    bootstrap,
    dense_only,
    hybrid,
    run_and_save,
    run_metrics_for,
)

from crag.ingest.manifest import Manifest
from crag.ingest.pipeline import ingest as run_ingest

STUDY_DIR = Path(__file__).resolve().parent
CORPUS_DIR = REPO_ROOT / "corpus"


CONFIGS = [
    {"chunk_tokens": 256, "chunk_overlap": 32, "chunk_strategy": "fixed", "label": "256 · fixed"},
    {
        "chunk_tokens": 256,
        "chunk_overlap": 32,
        "chunk_strategy": "sentence-snap",
        "label": "256 · sentence-snap",
    },
    {
        "chunk_tokens": 512,
        "chunk_overlap": 64,
        "chunk_strategy": "sentence-snap",
        "label": "512 · sentence-snap",
    },
    {
        "chunk_tokens": 1024,
        "chunk_overlap": 128,
        "chunk_strategy": "sentence-snap",
        "label": "1024 · sentence-snap",
    },
]


def _slug(cfg: dict) -> str:
    return f"chunk{cfg['chunk_tokens']}_{cfg['chunk_strategy']}"


def main() -> None:
    runs = []
    for cfg in CONFIGS:
        label = cfg.pop("label")
        slug = _slug(cfg)
        data_dir = REPO_ROOT / "data" / "study03" / slug
        if data_dir.exists():
            shutil.rmtree(data_dir)

        # Fresh stack per config.
        stack = bootstrap(data_dir=data_dir, **cfg)
        with Manifest(data_dir / "manifest.sqlite") as manifest:
            stats = run_ingest(
                paths=[CORPUS_DIR],
                settings=stack.settings,
                embedder=stack.embedder,
                store=stack.store,
                manifest=manifest,
                collection_root=CORPUS_DIR,
            )
        # Refresh BM25 against the just-ingested store; we cannot open a
        # second qdrant client to the same path (single-process lock).
        from crag.retrieval.bm25 import BM25Index

        stack.bm25 = BM25Index(stack.store.all_payloads())

        # Both retrieval modes on the new index — chunking has different
        # effects on dense vs hybrid.
        dense = run_metrics_for(f"{label} · dense", lambda q, s=stack: dense_only(s, q), top_k=5)
        hyb = run_metrics_for(f"{label} · hybrid", lambda q, s=stack: hybrid(s, q), top_k=5)

        runs.append(
            {
                "config": {**cfg, "label": label},
                "ingest": stats.asdict(),
                "dense": dense,
                "hybrid": hyb,
            }
        )

        # Release the qdrant lock so the next config can open its own dir.
        stack.store.close()

    out = run_and_save(
        study_id="03-chunking-grid",
        study_dir=STUDY_DIR,
        runs=runs,
        notes=(
            "Sweeps chunk size (256 / 512 / 1024 tokens) and boundary "
            "strategy (fixed vs sentence-snap). Each config gets a fresh "
            "index. Reports both dense-only and hybrid metrics so we can "
            "see whether chunking effects are independent of retrieval "
            "mode (often: yes)."
        ),
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
