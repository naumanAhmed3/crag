# Recommendations — what we would ship for Vantage today

Recommendation, not a survey. One architecture, named components,
each justified by a study under `studies/`.

## The shipping architecture

```
                                   ┌──────────────────────────┐
   filesystem watcher              │  ingestion process       │
   (10-min poll OR watchdog) ────▶ │                          │
                                   │  parse  → chunk  →  embed │
                                   └──────────┬───────────────┘
                                              │
                                              ▼
                  ┌───────────────────────────────────────────┐
                  │  SQLite manifest    +    Qdrant collection │
                  │  per-file mtime/sha     dense + sparse pts  │
                  └─────────────────────┬────────────────────┬┘
                                        │ writes             │ reads
                                        ▼                    │
   query ──▶  embed(query)  ─┬─▶  dense top-K (Qdrant)  ─────┤
                             │                                │
                             └─▶  BM25 top-K (in-memory) ────┘
                                          │
                                          ▼
                                       RRF (k=60)
                                          │
                                          ▼
                                   cross-encoder rerank
                                          │
                                          ▼
                                   top-5 + grounding prompt
                                          │
                                          ▼
                                   Ollama: qwen2.5:7b-q4_K_M
                                          │
                                          ▼
                                   grounded answer + citations
```

## Components, in shipping order

### 1. Ingestion process

- **Parser dispatch** — `pymupdf` for PDF, `python-docx` for DOCX,
  `openpyxl` for XLSX, `selectolax` for HTML, direct read for
  Markdown / TXT / source code.
- **Chunker** — token-based with sentence-snap boundary, 512 tokens
  / 64 overlap. *Locked by `studies/03-chunking-grid/`.*
- **Embedder** — `BAAI/bge-small-en-v1.5` (384-d), CPU. *Locked by
  `studies/04-embedding-bakeoff/`.*
- **Manifest** — SQLite, schema in `src/crag/ingest/manifest.py`.
  Per-file `mtime + size` for change-detection, per-chunk SHA-256
  for stable identifiers. *Locked by `studies/06-incremental-churn/`.*
- **Vector store** — Qdrant in embedded local mode, cosine distance,
  HNSW (m=16, ef_construction=64).

### 2. Retrieval

- **Dense**: Qdrant `query_points`, top-K=20, `hnsw_ef=128`.
- **Sparse**: in-memory BM25 (`rank_bm25`), top-K=20.
- **Fusion**: Reciprocal Rank Fusion, k=60. *No score normalisation —
  RRF doesn't need it, and using it would re-introduce a tuning knob
  per corpus that we've worked hard to avoid.*
- **Rerank**: `BAAI/bge-reranker-v2-m3` cross-encoder, CPU, top-K=8
  in / 5 out. *Promote/demote rule in `studies/02-reranking/`.*

### 3. Generation

- **Backend**: Ollama on `localhost:11434` (`OLLAMA_KEEP_ALIVE=24h`
  so the model stays warm).
- **Model**: `qwen2.5:7b-instruct-q4_K_M` — 4.4 GB VRAM. Headroom for
  an 8 K context on the RTX 3060.
- **System prompt**: `src/crag/llm/prompts.py` — refusal is the
  default; every claim cites `[N]`.

### 4. Evaluation

- **Retrieval regressions**: `crag eval` runs the gold set on every
  CI build. Tolerance bands documented in `docs/01-methodology.md`.
- **Faithfulness**: LLM-as-judge using the same local Ollama model,
  scored daily on a sample of recent queries. Logs to
  `$CRAG_DATA_DIR/audit/faithfulness.jsonl`.

## What we are *not* shipping

- A web UI. The CLI is the operator interface; downstream services
  consume the library API.
- LangChain / LlamaIndex.
- Docker, Kubernetes, the entire cloud-native ladder.
- Fine-tuning. Per the brief.

## What changes once the corpus crosses 100 M chunks

The single-process embedded Qdrant graduates to a Qdrant server,
sharded by document type or business unit. The BM25 implementation
graduates to Tantivy or Qdrant's sparse-vector mode (we keep the
RRF orchestration; only the leg-level retrievers change). The
manifest migrates from SQLite to a Postgres instance running on the
same host. See `SCALING.md` for the math.

## Operational defaults

- **Ingest cadence**: 10-minute polling (`crontab -e ... * /10 * * *
  * /usr/local/bin/crag ingest /vantage/share`).
- **Liveness probe**: `corpus/code/health_check.py`. Exit 0 = OK.
- **Eviction**: `corpus/code/eviction.py` for compliance-driven
  immediate removal; logs to the audit trail.
- **Backup**: `tar` the `$CRAG_DATA_DIR` directory daily to NAS.
  Restore is `tar -xf` to a fresh host followed by `crag stats` to
  verify counts match.
