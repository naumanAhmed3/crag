"""Round 02 — Cross-encoder reranking on top of hybrid.

Question: is the cross-encoder reranker worth its latency? We measure
the precision gain it delivers against the latency cost it adds.

Run:
    uv run python studies/02-reranking/experiment.py
Output:
    studies/02-reranking/results.json
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from _common import (
    bootstrap,
    hybrid,
    hybrid_rerank,
    run_and_save,
    run_metrics_for,
)

STUDY_DIR = Path(__file__).resolve().parent


def main() -> None:
    # Bootstrap with the reranker enabled so the cross-encoder loads once.
    stack = bootstrap(reranker_enabled=True)

    runs = [
        run_metrics_for(
            "hybrid (no rerank)",
            lambda q: hybrid(stack, q),
            top_k=5,
        ),
        run_metrics_for(
            "hybrid + bge-reranker-v2-m3",
            lambda q: hybrid_rerank(stack, q),
            top_k=5,
        ),
    ]
    out = run_and_save(
        study_id="02-reranking",
        study_dir=STUDY_DIR,
        runs=runs,
        notes=(
            "Compares the fused retrieval pipeline with and without a "
            "cross-encoder reranker (bge-reranker-v2-m3). Same index, "
            "same gold set, same RRF settings. The interesting trade is "
            "Δ Precision@5 vs Δ p95 latency."
        ),
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
