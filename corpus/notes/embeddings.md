# Dense embeddings — what they encode, what they miss

A dense sentence embedding model is a function from text to a
fixed-length vector — typically 384, 768, or 1024 dimensions —
where semantically similar pieces of text land near each other in the
vector space. Most modern open-weight models (BGE, GTE, nomic-embed,
E5) are fine-tuned BERT-derivatives trained with contrastive losses
on hundreds of millions of query–passage pairs.

## What "similar" means to an embedding model

The model has been *trained* on a specific notion of relevance, and it
reflects the labels it saw. Models trained on web-style query–passage
pairs (BGE, E5) are good at "did this passage answer the question."
Models trained on STS-style pairs (older Sentence-BERT) are good at
"are these two sentences saying the same thing." For RAG you want the
former; using the latter leads to retrievers that surface paraphrases
of the question instead of answers to it.

## The MTEB benchmark and its limits

Massive Text Embedding Benchmark (MTEB) is the leaderboard most teams
consult when picking a model. It is useful as a directional signal but
not a substitute for evaluating on *your* corpus. Three reasons:

1. MTEB tasks are predominantly English, mostly web-scale general
   knowledge. Your corpus may be domain-specific (legal, medical,
   engineering) where the rankings shuffle.
2. MTEB measures retrieval against curated short queries; production
   queries are messier, longer, sometimes adversarial.
3. The leaderboard rewards over-fitting; models near the top sometimes
   degrade on out-of-distribution data.

The right move: pick three top-quartile models, run them on your own
gold set, take the one with the highest Recall@5.

## Footprint vs accuracy

| Model | Dim | Disk | Indicative MTEB | Notes |
|---|---|---|---|---|
| BAAI/bge-small-en-v1.5 | 384 | 33 MB | ~62.2 | CPU-fast, ~85 % of large's quality |
| BAAI/bge-base-en-v1.5 | 768 | 110 MB | ~63.5 | Balanced default; needs ~600 MB RAM |
| BAAI/bge-large-en-v1.5 | 1024 | 335 MB | ~64.2 | Best quality; ideally GPU-served |
| nomic-embed-text-v1.5 | 768 | 137 MB | ~62.7 | 8k context — useful for long-document corpora |

The accuracy gap between small and large is real but smaller than the
marketing copy suggests. On a 6 GB VRAM rig where the GPU is also
serving generation, BGE-small on CPU is the rational default.

## Always normalise

Every model listed above produces vectors meant to be L2-normalised
before storage and search. With normalised vectors, cosine similarity
equals the dot product, which is what every vector database
implements efficiently. Forgetting normalisation costs ~5 points of
Recall@5 silently.
