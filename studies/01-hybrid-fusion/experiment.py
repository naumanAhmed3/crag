"""Round 01 — Hybrid retrieval: dense + BM25 → RRF (k=60).

Question for this round: on technical-document text, does adding a
sparse lexical leg measurably improve Recall@5 and MRR over the
dense-only baseline?

Run:
    uv run python studies/01-hybrid-fusion/experiment.py
Output:
    studies/01-hybrid-fusion/results.json
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from _common import (
    bm25_only,
    bootstrap,
    dense_only,
    hybrid,
    run_and_save,
    run_metrics_for,
)

STUDY_DIR = Path(__file__).resolve().parent


def main() -> None:
    stack = bootstrap()
    runs = [
        run_metrics_for("dense_only", lambda q: dense_only(stack, q), top_k=5),
        run_metrics_for("bm25_only", lambda q: bm25_only(stack, q), top_k=5),
        run_metrics_for("hybrid_rrf_k60", lambda q: hybrid(stack, q), top_k=5),
    ]
    out = run_and_save(
        study_id="01-hybrid-fusion",
        study_dir=STUDY_DIR,
        runs=runs,
        notes=(
            "Three-way comparison on the same index: dense-only, BM25-only, "
            "and the fusion of the two via Reciprocal Rank Fusion (k=60). "
            "Same chunking, same embedding model, same gold set — only the "
            "retrieval composition varies."
        ),
    )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
