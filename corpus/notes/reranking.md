# Reranking — when the cross-encoder pass earns its latency

A retriever produces a candidate set; a reranker reorders that set so
the most relevant items are at the top. The distinction matters because
the two stages have different cost profiles: retrievers scale to
millions of documents because they encode each document once at index
time, while rerankers re-score each (query, document) pair from
scratch at query time.

## Bi-encoder vs cross-encoder

- **Bi-encoder** (what the dense retriever is): query and document are
  encoded *independently* into vectors. Similarity is a cheap dot
  product. Index once, query forever. Good recall, mediocre precision
  on subtle cases.
- **Cross-encoder** (what the reranker is): query and document are
  concatenated and passed through the model *together*. The output is
  a single score. Slow — every (query, document) pair runs the full
  model — but the joint attention captures word-level interactions a
  bi-encoder cannot.

The complementary fit is: bi-encoder retrieves the candidate top-K
fast; cross-encoder reranks that K precisely. Typical K for reranking
sits between 8 and 50.

## What "+8 points of precision" really buys

On a 5-question gold set with single-relevant-document answers, going
from Recall@5 = 0.6 to 0.6 (unchanged) but Precision@5 = 0.20 to 0.28
means: the right answer was always in the top-5 either way, but the
reranker promoted it from rank 4 to rank 1 in 40 % of cases.

For RAG this matters disproportionately. The LLM weighs early
passages more heavily; a relevant passage at rank 4 is half-ignored
in favour of three irrelevant ones at ranks 1–3, and the answer
quality suffers. A rerank pass that lifts the right passage to rank
1 changes the final answer.

## Cost on CPU

A typical cross-encoder (`bge-reranker-v2-m3`, 568 MB) scores a
single (query, 512-token-passage) pair in 80–150 ms on a modern
laptop CPU. Reranking 10 candidates is 800 ms – 1.5 s, dominated by
the model latency. On a GPU it drops by an order of magnitude.

## When to skip the rerank

Three scenarios where the latency isn't worth it:

1. The bi-encoder already wins. If Recall@1 of the dense retriever is
   already > 0.85 on your gold set, reranking buys little.
2. Hard real-time SLAs (< 500 ms p95). Drop the rerank and lean on
   better chunking or a better embedding model.
3. Reranker model failure modes: cross-encoders trained on web data
   sometimes downscore domain-specific text (legal, medical).
   Always re-evaluate the reranker on your own data — never blindly
   trust the leaderboard ordering.
