# Round 02 — Cross-encoder reranking

## Question
Is the cross-encoder reranker worth the latency it adds? Reranking is
a precision tool — its job is to lift the right passage to the top of
the K. The trade is straightforward: precision gain vs latency cost.

## Setup
Same index as round 00 and 01. Two variants:

| Configuration | Hybrid | Reranker |
|---|---|---|
| `hybrid` | dense + BM25 → RRF | — |
| `hybrid + rerank` | same | `BAAI/bge-reranker-v2-m3` (CPU) |

Both return the same final top-5; the reranker scores the top-8 from
RRF and re-orders them.

## How to run
```
make ingest-sample          # if not already ingested
uv run python studies/02-reranking/experiment.py
```

First run downloads the reranker (~568 MB).

## What we measure
Recall@5, Precision@5, MRR, substring-recall, and the latency profile
under each configuration. The latency delta is the cost; the precision
delta is the benefit.

## Lock-in rule
The reranker stays on in the production stack if:

- Δ Precision@5 ≥ +8 percentage points **and**
- Δ p95 latency ≤ +300 ms on the reference rig.

If the precision lift is real but the latency cost exceeds the
threshold, we promote a smaller reranker (e.g. `bge-reranker-base`)
in a follow-up round.

## Findings
See `findings.md`.
