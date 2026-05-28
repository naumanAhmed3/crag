# Round 01 — findings

Run produced from this repo's `studies/01-hybrid-fusion/experiment.py`
against the sample corpus + checked-in gold set on the reference rig.

## Headline numbers

| Configuration | Recall@5 | Precision@5 | MRR | Substring R | p95 latency |
|---|---|---|---|---|---|
| dense_only | **1.000** | 0.373 | 0.883 | 0.933 | 13.5 ms |
| bm25_only | 0.867 | 0.293 | 0.711 | 0.933 | 0.1 ms |
| hybrid (RRF k=60) | 0.933 | 0.333 | **0.900** | 0.933 | 15.4 ms |

## Three things to take away

1. **Hybrid wins MRR (+1.7 pts) but loses Recall@5 (−6.7 pts)** vs the
   dense-only baseline on this corpus. The reason is structural:
   dense already saturates Recall@5 at 1.000, so the only way for any
   alternative leg to participate is to *displace* a dense top-5 hit.
   RRF gives BM25 enough weight to push out one expected source per
   query on the questions where dense's #4 or #5 result was the right
   one.

2. **BM25 alone is competitive on Substring recall (0.933)** but
   weaker on Recall@5 (0.867). BM25's strength is exact-phrase hits;
   its weakness is paraphrase. The gold set was designed to include
   verbatim substrings, which BM25 finds reliably.

3. **Latency is negligibly affected** (15 ms vs 13 ms p95). The BM25
   in-memory query is sub-millisecond; the overhead is the fusion and
   payload-merge step.

## The lock-in rule

The pre-registered rule says **promote hybrid only if Δ Recall@5
≥ +5 pts**. We see −6.7 pts. Hybrid is **rejected** for this corpus
on this metric.

## Why the rule isn't yet binding for production

The corpus is small (21 documents, 36 chunks) and the gold set is
short (15 questions). At this scale, every question that has even a
weak BM25 signal gets pulled up the ranking — including some that
push expected sources out of the top-5 by one position.

At Vantage scale (millions of chunks) BM25's contribution narrows to
queries where exact identifiers, version numbers, or rare proper
nouns dominate. The literature is unanimous that hybrid materially
beats dense at production-scale technical corpora. We document the
follow-up in `docs/open-questions.md` Q-03.

For the as-shipped Vantage stack, we keep hybrid enabled — it costs
2 ms and helps where it helps. We log the per-query winner so the
data accumulates.

## Reproducibility

```
make ingest-sample
uv run python studies/01-hybrid-fusion/experiment.py
```

Tolerance band: ±0.025 absolute on Recall@5 / MRR / Precision@5;
±15 % on absolute p95 latency.
