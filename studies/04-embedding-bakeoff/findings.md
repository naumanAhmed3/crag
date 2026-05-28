# Round 04 — findings

Run produced from this repo's `studies/04-embedding-bakeoff/experiment.py`
against the sample corpus + gold set on the reference rig. Each model
is ingested into its own isolated index because the collection's
vector dimension is locked at creation time.

## Headline numbers

| Model | Dim | Embed (s) | Dense R@5 | Dense MRR | Hybrid R@5 | Hybrid MRR |
|---|---|---|---|---|---|---|
| `BAAI/bge-small-en-v1.5` | 384 | 1.28 | 1.000 | 0.883 | 0.933 | 0.900 |
| `BAAI/bge-base-en-v1.5` | 768 | 2.49 | 1.000 | 0.889 | 0.933 | 0.867 |
| `intfloat/e5-small-v2` | 384 | 1.13 | 1.000 | **0.913** | 0.933 | 0.900 |

## Three things to take away

1. **e5-small-v2 wins MRR on this corpus** (0.913 vs 0.883 for
   bge-small and 0.889 for bge-base). It is also the fastest ingest
   in this group. On its raw numbers it would be the right choice.

2. **bge-base doesn't earn its size.** 2× the embed cost and 2× the
   per-vector storage (768 vs 384 dim) for no improvement on hybrid
   MRR (in fact a small regression). On this corpus there's no case
   to upgrade.

3. **Recall@5 is saturated for every model.** All three find the
   expected source in the top-5 for every gold question. The
   discriminating metric is MRR — *where* in the top-5 — which is
   why the bake-off matters even though raw recall is identical.

## What we ship and why it isn't the local winner

The default in `src/crag/config.py` remains **`bge-small-en-v1.5`**,
not the e5-small winner from this round. Three reasons:

- **Generalisation evidence.** On MTEB (a much larger, more diverse
  benchmark than our 15-question gold), bge-small consistently
  outperforms e5-small-v2 on retrieval. The local win here is real
  but on a small corpus.
- **Document type stability.** bge-small was specifically trained on
  the query → relevant-passage objective; e5-small's training mix
  leans more toward STS-style similarity. For RAG queries (questions
  with informational intent) the former is the safer bet across
  unseen corpora.
- **Operational familiarity.** bge-small is what the largest fleet
  of open-source RAG deployments runs. Shipping it as the default
  lowers the support burden when the system enters production.

The follow-up in `docs/open-questions.md` Q-04 documents the planned
re-measurement at production-scale corpus where these differences
should widen or invert.

## Reproducibility

```
rm -rf data/study04
uv run python studies/04-embedding-bakeoff/experiment.py
```

First run downloads any uncached model. Wall-clock varies with
network speed; the embedding + retrieval pass itself is ~1–3 s per
model on the sample corpus.

Tolerance band: ±0.030 absolute on MRR (the gold set is small enough
that one or two ranking flips moves the absolute value visibly);
embed-time tolerance ±15 % (CPU-thermal-sensitive).
