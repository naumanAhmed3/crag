# HNSW — Hierarchical Navigable Small World graphs

HNSW is the index that almost every modern vector database reaches for
when you need approximate nearest-neighbour search at scale. The data
structure is a multi-layer proximity graph: each node represents a
vector, and edges connect a node to its closest neighbours in the
embedding space. Higher layers are sparse — most nodes only live in the
bottom layer — and a search walks the graph top-down, greedily moving
toward the query before descending one layer at a time.

## Why graphs beat trees in high dimensions

Tree-based ANN structures (KD-trees, ball trees) work well up to about
20 dimensions and fall apart above that — the curse of dimensionality
means most pairs of points end up roughly equidistant, so the tree's
partitioning loses its discriminative power. Embedding spaces are
typically 384 to 1536 dimensions, well past where trees collapse. The
small-world property of HNSW — that every node can reach any other in
O(log n) hops — gives an empirical query cost that scales like log of
the corpus size, even at 1024 dimensions.

## The two knobs that matter

- **`m`** (or `M`): the maximum number of outbound edges per node at the
  bottom layer. Higher `m` means a denser graph, faster query, more
  memory, slower build. Typical production values are 16 to 48.
- **`ef_construction`**: the size of the dynamic candidate list during
  insertion. Larger values produce a higher-quality graph at the cost
  of build time. Typical values: 100 to 400.

At query time, **`ef`** (or `hnsw_ef`) controls how aggressively the
search expands the candidate set. It is the single knob you tune in
production: `ef = 32` is fast but lossy; `ef = 256` is slow but
near-exhaustive. Most workloads sit at 64 to 128.

## When HNSW is the wrong choice

Two scenarios:

1. **Tiny corpora.** Below ~10k vectors, brute-force search is
   competitive on a CPU and saves you the build cost + RAM overhead.
2. **Very high churn.** HNSW supports inserts and deletes, but heavy
   deletion fragments the graph; periodic rebuilds become necessary.
   For workloads where >30 % of vectors turn over daily, IVF-Flat or
   even partitioned brute-force is often more honest.

## Memory footprint

Rule of thumb: ~`(dim * 4 + m * 2 * 8)` bytes per vector, plus the
vector itself. A 384-dim BGE-small corpus of one million chunks with
`m=16` runs about 1.8 GB before payload — comfortably fits in 16 GB of
RAM with room for the model and the OS.
