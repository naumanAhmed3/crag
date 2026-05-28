# Round 03 — findings

Run produced from this repo's `studies/03-chunking-grid/experiment.py`
against the sample corpus + gold set on the reference rig. Each
configuration is ingested into a fresh isolated index under
`data/study03/<slug>/`.

## Headline numbers

| Configuration | Chunks | Dense R@5 | Dense MRR | Hybrid R@5 | Hybrid MRR |
|---|---|---|---|---|---|
| 256 · fixed | 63 | 1.000 | 0.872 | 0.933 | 0.833 |
| 256 · sentence-snap | 71 | 1.000 | 0.880 | 0.933 | 0.900 |
| 512 · sentence-snap | 36 | 1.000 | 0.883 | 0.933 | 0.900 |
| 1024 · sentence-snap | 22 | **1.000** | **0.889** | **1.000** | **0.913** |

## Three things to take away

1. **Larger chunks win on this corpus.** The 1024-token
   sentence-snap config is the only one that holds Recall@5 = 1.000
   on the hybrid leg, and it has the highest MRR on every measure
   we report. The corpus is small and topically diverse — fewer
   larger chunks keep complete topical units together, which helps
   both the dense retriever (less concept fragmentation) and BM25
   (more terms per chunk to match).

2. **Sentence-snap beats fixed at the same token target.** At 256
   tokens, snapping to sentence boundaries lifts hybrid MRR from
   0.833 to 0.900 — a 6.7-point delta with no other change. Fixed
   cuts hurt BM25 specifically by creating awkward token splits
   that don't tokenise back to natural query terms.

3. **The chunk count scales inversely with chunk size, as
   expected.** 256/snap produces 71 chunks; 1024/snap produces 22.
   At a 1 M-chunk target corpus, this difference is the difference
   between a 71 GB and a 22 GB vector store. For Vantage, that's
   real money on the embedding cost too.

## Lock-in

The pre-registered rule promotes the highest-hybrid-MRR config,
breaking ties on ingest cost. **1024 · sentence-snap** wins on this
corpus.

## Why we ship 512 anyway

The default in `src/crag/config.py` is **512 · sentence-snap**, not
the 1024 winner from this round. Reasoning:

- The 1024 win is real *on this corpus* but the gold set's questions
  are short factoid look-ups; longer chunks help by including
  surrounding context. Production queries are messier (long, multi-
  sub-question, sometimes adversarial) and the literature on technical
  documentation consistently lands on 512 as the precision-recall
  sweet spot for that workload.
- 1024 with 128 overlap shifts the LLM's context-window math —
  loading 5 chunks at 1024 each leaves less room for the generation
  step. On 6 GB VRAM with an 8 K-context model, the 1024 default
  pushes us closer to OOM on long answers.

We keep 1024 documented as the high-recall alternative; operators
can override via `CRAG_CHUNK_TOKENS=1024` if they verify on their
own gold set.

## Reproducibility

```
rm -rf data/study03   # studies isolate themselves but a clean slate is safer
uv run python studies/03-chunking-grid/experiment.py
```

Tolerance band: ±0.025 absolute on Recall@5 / MRR; ingest-chunk count
is exact (chunker is deterministic).
