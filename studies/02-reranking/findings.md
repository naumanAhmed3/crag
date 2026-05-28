# Round 02 — findings

Run produced from this repo's `studies/02-reranking/experiment.py`
against the sample corpus + gold set on the reference rig.

## Headline numbers

| Configuration | Recall@5 | Precision@5 | MRR | Substring R | p95 latency |
|---|---|---|---|---|---|
| hybrid (no rerank) | 0.933 | 0.333 | 0.900 | 0.933 | 13.0 ms |
| hybrid + bge-reranker-v2-m3 | 0.933 | **0.347** | 0.900 | 0.933 | **1 333 ms** |

## Three things to take away

1. **The rerank costs ~100× the latency for a 1.3-point precision
   gain.** Recall and MRR are unchanged. On this corpus the reranker
   has effectively nothing to lift — most queries already have the
   right answer at rank 1.

2. **The pre-registered lock-in rule does not fire.** The rule says
   keep rerank if Δ Precision ≥ +8 pts at Δ p95 latency ≤ +300 ms.
   We see +1.4 pts at +1 320 ms. Both gates fail. **Reject for this
   corpus.**

3. **The reranker still pays off in two scenarios the gold set
   doesn't simulate.** First, queries where the answer is at rank 3
   or 4 in the fused result — exactly the situation that breaks
   downstream LLM grounding, because the model weights early
   passages more heavily. Second, larger corpora where dense recall
   no longer saturates. Neither situation appears in our 15-question
   gold; the published literature consistently shows both holding at
   production scale.

## Operational note

The CPU latency (~1.3 s p95 at top-K=8) is the bottleneck. On a
discrete GPU the same reranker drops to ~80–120 ms, well within
the 300 ms lock-in budget. The Vantage box has a GPU but it is
occupied by the generation model; running both concurrently means
ping-ponging weights through VRAM, which is worse than just paying
the CPU cost. For Vantage we ship with rerank **disabled by default**
and re-enable per-query when an operator-controlled flag is set
(e.g. `crag ask --rerank` for expensive but precise answers).

## Reproducibility

```
make ingest-sample
uv run python studies/02-reranking/experiment.py
```

First run downloads `BAAI/bge-reranker-v2-m3` (~568 MB).

Tolerance band: ±0.025 absolute on Precision@5; ±25 % on absolute
p95 latency (cross-encoder latency is sensitive to CPU thermal
state).
