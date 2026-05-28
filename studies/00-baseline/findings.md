# Round 00 — findings

Run produced from this repo's `studies/00-baseline/experiment.py`
against the sample corpus + checked-in gold set on the reference rig
(see `docs/hardware-fingerprint.md`).

## Headline numbers

| Metric | Value |
|---|---|
| Recall@5 | **1.000** |
| Precision@5 | 0.373 |
| MRR | 0.883 |
| Substring recall | 0.933 |
| p50 latency | 10 ms |
| p95 latency | 13 ms |

## Three things to take away

1. **Dense-only saturates Recall@5** on the bundled corpus + gold set.
   Every gold question has at least one expected source in the
   top-5. That's good news for the engine and bad news for measuring
   improvement on this small corpus — later rounds have nowhere to lift
   recall.
2. **Precision@5 is ~0.37**, which means roughly two of the five
   returned chunks are off-target on the average query. That's the
   number the cross-encoder rerank in round 02 will try to move.
3. **MRR is ~0.88**, so the right source is usually at rank 1 already.
   The remaining ~0.12 worth of MRR is the precision-shaped headroom.

The honest interpretation is that the *corpus* is the binding
constraint on what later rounds can show, not the retriever. See
`docs/open-questions.md` Q-03 for the planned follow-up at corpus
sizes where dense saturates *less*.

## Reproducibility

```
make ingest-sample
uv run python studies/00-baseline/experiment.py
```

Tolerance band: ±0.020 absolute on Recall@5 / MRR / Precision@5; ±10 %
on absolute p95 latency.
