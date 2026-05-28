# Reciprocal Rank Fusion — the cheap, correct way to fuse rankings

Reciprocal Rank Fusion (RRF) is the answer to the question "how do I
combine my dense retriever's top-K with my BM25 retriever's top-K when
the two scores live on completely different scales." Cosine similarity
runs from −1 to 1; BM25 is unbounded and corpus-dependent. Min-max
normalising both onto [0,1] is fragile (a single high-scoring outlier
in one leg destroys the other). RRF dodges the scale problem entirely:
it only looks at rank position.

## The formula

For each candidate document `d` appearing in any of the ranked lists,

```
RRF(d) = Σ_lists 1 / (k + rank_in_list(d))
```

where `k` is a damping constant — the literature settled on **k = 60**
after the original 2009 paper by Cormack, Clarke, and Büttcher. A
document ranked first in two lists scores `2 / 61 ≈ 0.0328`; a
document ranked tenth in one list scores `1 / 70 ≈ 0.0143`. The
gradient is smooth, deeper ranks contribute less, and a document
appearing in any one of the lists is never excluded.

## Why k = 60

The constant has one purpose: damp the gradient so the top result
doesn't dominate by an order of magnitude. With `k = 60`, the score
difference between rank 1 and rank 2 is small (0.0164 vs 0.0161),
which lets the second retriever's input meaningfully change the
ordering. Tiny values (k = 1) recover a winner-takes-all behaviour
that defeats the point.

## Where RRF is the wrong tool

If you only have one retriever, RRF degenerates to "sort by 1/(k+rank)"
which is just "sort by rank" — pointless. If your scoring functions
*are* on the same scale (two dense retrievers fine-tuned on the same
data), a weighted sum is cleaner. RRF earns its place only when the
input scores are incomparable.

## Beyond two-way fusion

RRF extends trivially to any number of input lists — three retrievers,
five, ten. Some search systems fuse a dense retriever, a sparse
retriever, a learned sparse retriever (SPLADE), and a graph-based
retriever in one RRF step. The risk at high `N` is that adding a weak
retriever can dilute a strong one. Audit each leg's standalone
performance before adding it to the fusion.
