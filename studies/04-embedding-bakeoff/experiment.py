"""Round 04 — Embedding model bake-off.

For each candidate embedding model:
  1. Wipe a per-model index.
  2. Re-ingest the corpus through the model.
  3. Run the gold set; record retrieval metrics + latency.
  4. Record embed throughput (chunks/sec) and ingest time.

Each model gets its own data subdirectory because the vector dimension
must match the collection's configured dim.

Models with no local cache will be downloaded on first run; if a
download fails (offline / firewall), that model is skipped and the run
continues with the rest. The set of successfully-measured models is
recorded in `results.json` under `runs[*].config.model_loaded = true`.

Run:
    uv run python studies/04-embedding-bakeoff/experiment.py
Output:
    studies/04-embedding-bakeoff/results.json
"""

from __future__ import annotations

import shutil
import sys
import time
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


MODELS = [
    {"id": "BAAI/bge-small-en-v1.5", "label": "bge-small-en-v1.5 (384d)"},
    {"id": "BAAI/bge-base-en-v1.5", "label": "bge-base-en-v1.5 (768d)"},
    {"id": "intfloat/e5-small-v2", "label": "e5-small-v2 (384d)"},
]


def main() -> None:
    runs = []
    for model in MODELS:
        slug = model["id"].replace("/", "_").replace(".", "_")
        data_dir = REPO_ROOT / "data" / "study04" / slug
        if data_dir.exists():
            shutil.rmtree(data_dir)

        config = {"embedding_model": model["id"]}
        try:
            stack = bootstrap(data_dir=data_dir, **config)
            t0 = time.perf_counter()
            with Manifest(data_dir / "manifest.sqlite") as manifest:
                stats = run_ingest(
                    paths=[CORPUS_DIR],
                    settings=stack.settings,
                    embedder=stack.embedder,
                    store=stack.store,
                    manifest=manifest,
                    collection_root=CORPUS_DIR,
                )
            wall = round(time.perf_counter() - t0, 2)
            from crag.retrieval.bm25 import BM25Index

            stack.bm25 = BM25Index(stack.store.all_payloads())
            dense = run_metrics_for(
                f"{model['label']} · dense", lambda q, s=stack: dense_only(s, q), top_k=5
            )
            hyb = run_metrics_for(
                f"{model['label']} · hybrid", lambda q, s=stack: hybrid(s, q), top_k=5
            )
            runs.append(
                {
                    "config": {**model, "model_loaded": True},
                    "ingest": stats.asdict(),
                    "wall_seconds": wall,
                    "embedding_dim": stack.embedder.dim,
                    "dense": dense,
                    "hybrid": hyb,
                }
            )
            stack.store.close()
        except Exception as e:
            runs.append(
                {
                    "config": {**model, "model_loaded": False},
                    "error": f"{type(e).__name__}: {e!s}"[:240],
                }
            )
            continue

    out = run_and_save(
        study_id="04-embedding-bakeoff",
        study_dir=STUDY_DIR,
        runs=runs,
        notes=(
            "Compares three open-weight embedding models on the same "
            "corpus and gold set. The trade-space: vector dimension (RAM "
            "footprint, store size, query latency) vs Recall@5. Each "
            "model gets a fresh isolated index because the collection's "
            "vector dim is set at creation time."
        ),
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
