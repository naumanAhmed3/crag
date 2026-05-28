# Round 01 — Hybrid retrieval (dense + BM25 → RRF)

## Question
Does adding a BM25 (sparse, lexical) leg next to the dense retriever
measurably improve Recall@5 and MRR on technical-document text, or is
dense-only already enough?

## Setup
Same index as round 00. We vary only the retrieval composition:

| Configuration | Dense | BM25 | RRF | Reranker |
|---|---|---|---|---|
| `dense_only` | ✓ | — | — | — |
| `bm25_only` | — | ✓ | — | — |
| `hybrid_rrf_k60` | ✓ | ✓ | k=60 | — |

## How to run
```
make ingest-sample          # if not already ingested
uv run python studies/01-hybrid-fusion/experiment.py
```

## What we measure
For each configuration: Recall@5, Precision@5, MRR, substring-recall,
and p50 / p95 / mean latency in milliseconds.

## Lock-in rule
The hybrid configuration is promoted to the production stack if
Δ Recall@5 (hybrid − dense) ≥ +5 percentage points *and* p95 latency
stays below 600 ms. Anything less and we revert to dense-only — the
sparse leg's index build, memory footprint, and operational complexity
need to be earning their place.

## Findings
See `findings.md` (written after the run from `results.json`).
