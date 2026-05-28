"""Round 00 — Baseline: dense-only retrieval, no rerank, no BM25.

The starting point. Every later round must beat these numbers; if a
round doesn't, that's worth knowing as much as if it does.

Run:
    uv run python studies/00-baseline/experiment.py
Output:
    studies/00-baseline/results.json
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from _common import bootstrap, dense_only, run_and_save, run_metrics_for

STUDY_DIR = Path(__file__).resolve().parent


def main() -> None:
    stack = bootstrap()
    runs = [
        run_metrics_for(
            "dense_only / bge-small / final_top_k=5",
            lambda q: dense_only(stack, q),
            top_k=5,
        )
    ]
    out = run_and_save(
        study_id="00-baseline",
        study_dir=STUDY_DIR,
        runs=runs,
        notes=(
            "Dense-only retrieval with the default embedding model. "
            "Sole leg; no BM25, no reranker. Establishes the starting "
            "point for Recall@5, Precision@5, MRR, and per-query latency."
        ),
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
