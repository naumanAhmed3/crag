# Qdrant — local mode, server mode, and when to graduate

Qdrant is an open-source vector database written in Rust. The reason
it shows up so often in offline RAG stacks is the same reason it shows
up in production: it runs in three modes (in-process embedded,
single-node server, multi-node cluster) with the same client API. You
start with embedded for the laptop demo and graduate to server when
the corpus or the concurrency demands it, with zero data-model
change.

## Local (embedded) mode

`QdrantClient(path="./data/qdrant")` opens a file-backed instance in
the calling process. No network, no separate binary, no Docker, no
ports. Persistence is a directory; you can `tar` it. This is what
fits the offline brief perfectly — the entire vector store moves with
the laptop.

Trade-offs:

- Single-process only (no concurrent writers).
- Memory-mapped HNSW; the page cache does the heavy lifting.
- Snapshots and shard rebalancing are not available.

## Server mode

`docker run -p 6333:6333 qdrant/qdrant` or the equivalent native
binary. Same client code; you change the URL to `http://localhost:6333`.
Adds gRPC, REST, dashboard, multi-tenant collections, snapshots,
backups.

Graduate to server mode when any of these is true:

- Multiple processes need to write to the same store.
- The corpus exceeds 10 M points and you want async upserts.
- You need on-line snapshots without stopping the writer.
- You want telemetry (Prometheus metrics, dashboard).

## Sharded collections — the path to 2 TB

A single Qdrant collection can practically hold tens of millions of
vectors; beyond that, sharding becomes the right tool. The pattern:

- Shard by a stable key (file path prefix, tenant ID, document type).
- Search by issuing parallel queries to each shard and merging top-K.
- Reindex one shard at a time so the others stay online.

For 2 TB of mixed corpus, a reasonable starting shape is 12–20 shards
of ~200 K points each, each with its own HNSW index. The merge step is
cheap (small top-K from each shard) and the per-shard memory footprint
stays comfortable on commodity hardware.

## The metric question — cosine vs dot vs L2

Cosine is the safe default and what we use here, because every modern
embedding model emits L2-normalised vectors and cosine on normalised
vectors equals the dot product. Pick **dot** explicitly if you know
your vectors are normalised and want to skip the cosine numerator.
**L2** is right for some image embeddings (CLIP-style) but is almost
always wrong for sentence embeddings.
