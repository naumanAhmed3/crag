# Round 04 — Embedding model bake-off

## Question
On this corpus, with our chunking and gold set, which open-weight
embedding model balances retrieval quality, throughput, and footprint?

The MTEB leaderboard is the obvious starting point but not the
finishing line — leaderboard rankings frequently invert on
domain-specific corpora. We measure on *our* data.

## Setup

Three open models, each ingested into its own isolated index because
the vector dimension is locked at collection-creation time.

| Model | Dim | Notes |
|---|---|---|
| `BAAI/bge-small-en-v1.5` | 384 | The default; CPU-fast, 33 MB |
| `BAAI/bge-base-en-v1.5` | 768 | ~440 MB; ~3× store size vs small |
| `intfloat/e5-small-v2` | 384 | Alternative 384-dim baseline |

Any model whose download fails (offline / firewall) is skipped and
reported with `model_loaded: false`. The remaining results stand on
their own.

## How to run
```
uv run python studies/04-embedding-bakeoff/experiment.py
```

First run downloads any uncached models. Wall-clock varies with
network speed; the embedding + retrieval pass itself is ~10 s per
model on the sample corpus.

## What we measure
Per model:

- Ingest stats (chunks added, embed seconds, wall time).
- Vector dimension.
- Dense-only retrieval metrics.
- Hybrid retrieval metrics (dense + BM25 + RRF).
- Per-query latency (p50, p95, mean).

## Lock-in rule
The production embedding model is the highest-Recall@5 model whose
ingest throughput is within 2× of the fastest measured. We pay for
better retrieval up to 2× ingest cost; beyond that, the operational
weight outweighs the marginal accuracy.

## Findings
See `findings.md`.
