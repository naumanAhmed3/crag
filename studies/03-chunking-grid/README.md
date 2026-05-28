# Round 03 — Chunking grid

## Question
What chunk size and boundary strategy win on a technical-document
corpus? Chunking is the most under-investigated lever in RAG; we sweep
it explicitly to lock down the default.

## Setup

Four configurations on the same corpus, same embedding model, same
retrieval mode:

| Config | Tokens | Overlap | Strategy |
|---|---|---|---|
| `256 · fixed` | 256 | 32 | fixed token cut |
| `256 · sentence-snap` | 256 | 32 | sentence-boundary snap (±15 %) |
| `512 · sentence-snap` | 512 | 64 | sentence-boundary snap |
| `1024 · sentence-snap` | 1024 | 128 | sentence-boundary snap |

Each config is ingested into a fresh, isolated data directory.

For each config we evaluate **both** dense-only and hybrid retrieval,
because chunking effects often interact with retrieval mode — fewer,
larger chunks can hurt dense recall (concept lost in a longer block)
while helping BM25 (more terms per chunk to match).

## How to run
```
uv run python studies/03-chunking-grid/experiment.py
```

Wall-clock: ~30 s on the bundled sample corpus; scales linearly with
corpus size.

## What we measure
Per config:
- Ingest stats: chunks added, embed seconds.
- Dense-only retrieval metrics + latency.
- Hybrid (dense + BM25 + RRF) metrics + latency.

## Lock-in rule
The configuration with the highest hybrid MRR wins, breaking ties on
embed-time + ingest-time cost. Anything within 1.5 points of the winner
is treated as a tie; we pick the cheaper one. The chosen config
becomes the production default in `src/crag/config.py`.

## Findings
See `findings.md`.
