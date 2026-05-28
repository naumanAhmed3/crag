# Round 00 — Baseline (dense-only)

## Question
What does "do nothing fancy" get us? A single-leg dense retriever with
the default embedding model, no reranker, no BM25. The numbers from
this round are the ones every later round must improve on.

## Setup
- Embedding: `BAAI/bge-small-en-v1.5` (384-dim, CPU)
- Chunking: 512-token sentence-snap, 64-token overlap
- Retrieval: dense top-K (cosine in Qdrant)
- Reranker: off
- BM25: off
- Gold set: `src/crag/eval/gold.yaml` (15 questions)
- top-K: 5

## How to run
```
make ingest-sample   # if not already ingested
uv run python studies/00-baseline/experiment.py
```

## What we measure
Recall@5, Precision@5, MRR, substring-recall (where the gold item
includes verbatim phrases), and per-query p50 / p95 / mean latency in
milliseconds.

## Findings
See `findings.md` (written from `results.json` after the run).

## Reproducibility
The active git SHA, hardware fingerprint, and Python / PyTorch
versions are embedded in `results.json` under `hardware`. To re-run
on a different rig, repeat the steps above; absolute latencies vary
by hardware but the relative ranking of configurations should hold.
