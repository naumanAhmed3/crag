# Decision log

One row per architectural decision, in ADR shape. Format:

> **Decision** — what we chose · **Alternatives** — what we rejected · **Why** — reasoning · **Backing evidence** — the study or doc that supports it.

---

### 001 · Ship Qdrant in embedded local mode, not a server.

- **Decision** — `QdrantClient(path=…)` in-process, file-backed.
- **Alternatives** — Qdrant server in Docker; Chroma; sqlite-vss; FAISS-on-disk.
- **Why** — The brief mandates air-gapped; the host already runs the ingester, retriever, and LLM. A separate server process is one more thing to monitor without a single capability the embedded client doesn't have at this scale. Graduation path to server mode is one URL change, documented in `docs/SCALING.md`.
- **Backing** — `corpus/notes/qdrant.md`; `studies/04-embedding-bakeoff/results.json` for footprint numbers.

### 002 · Reciprocal Rank Fusion at k = 60, not score-blending.

- **Decision** — RRF over dense + BM25 ranks, fixed k = 60.
- **Alternatives** — min-max normalisation of cosine + log(BM25); learned fusion via a small MLP.
- **Why** — Dense and BM25 scores live on incomparable scales. Normalisation is fragile (one outlier in either leg destroys the ordering). Learned fusion would re-introduce per-corpus training. RRF needs neither and is what the literature converged on.
- **Backing** — `corpus/notes/rrf.md`; `studies/01-hybrid-fusion/results.json`.

### 003 · Token chunking with sentence-boundary snap, 512 / 64.

- **Decision** — Default chunker is tiktoken `cl100k_base` token windows of 512 with 64-token overlap, snapped to the nearest sentence boundary within ±15 %.
- **Alternatives** — Fixed 256 with 32 overlap; structural chunking (paragraph as chunk); semantic chunking via embedding-distance peaks.
- **Why** — The sentence-snap variant on 512/64 maximised hybrid MRR in `studies/03-chunking-grid/`. Smaller chunks gain a small precision lift but cost recall on multi-sentence answers. Semantic chunking costs an extra embedding pass at ingest for a marginal quality lift on prose only.
- **Backing** — `studies/03-chunking-grid/results.json`.

### 004 · BGE-small-en-v1.5 as the default embedding model.

- **Decision** — `BAAI/bge-small-en-v1.5`, 384-dim, CPU.
- **Alternatives** — `bge-base-en-v1.5` (768d); `nomic-embed-text-v1.5`; `e5-small-v2`.
- **Why** — `bge-small` is within 1.5 points of `bge-base` on our gold set at ⅓ of the ingest cost and ½ of the vector-store footprint. The RTX 3060 is busy running the generation model; serving embeddings on CPU is the rational allocation.
- **Backing** — `studies/04-embedding-bakeoff/results.json`; `corpus/notes/embeddings.md`.

### 005 · Cross-encoder rerank enabled by default.

- **Decision** — Top-8 candidates from RRF are reranked by `BAAI/bge-reranker-v2-m3` (CPU) before returning the final top-5.
- **Alternatives** — Skip rerank (rely on RRF alone); LLM-as-reranker via Ollama.
- **Why** — The reranker is the cheapest way to lift the right passage to rank 1; LLM-as-reranker is slower and shares VRAM with the generation model, which means swapping models mid-query.
- **Backing** — `corpus/notes/reranking.md`; `studies/02-reranking/results.json`.

### 006 · qwen2.5:7b-instruct-q4_K_M as the default generation model.

- **Decision** — Ollama, `qwen2.5:7b-instruct-q4_K_M`.
- **Alternatives** — Llama-3.1-8B q4; Phi-3-mini q4; Gemma-2-9B q4.
- **Why** — Qwen-2.5-7B at q4_K_M is ~4.4 GB VRAM (fits with 8 K context on the RTX 3060), is the strongest instruction-follower in the 7B class on technical content, and Ollama makes model swap one CLI flag. `phi3-mini` is the documented fallback when VRAM is < 4 GB.
- **Backing** — `corpus/notes/quantization.md`; `corpus/notes/ollama.md`; `studies/05-generation-bakeoff/` (planned).

### 007 · SQLite manifest for incremental ingestion.

- **Decision** — Single-file SQLite database co-located with the vector store.
- **Alternatives** — JSON / JSONL manifest; rely on Qdrant payload only.
- **Why** — SQLite is in the standard library, supports WAL for concurrent reads, FK cascades correctly handle file deletes, and is trivially backed up. JSON requires re-parsing the whole file on every ingest; Qdrant-only loses the ability to express "this file changed" without scanning every chunk.
- **Backing** — `corpus/notes/incremental-ingestion.md`; `src/crag/ingest/manifest.py`.

### 008 · Refusal is the verbatim string `I don't have enough information in the indexed corpus to answer this.`

- **Decision** — Refusal string is fixed and machine-detectable.
- **Alternatives** — Refusal phrased per-question; structured `{"answer": null, "reason": "…"}` JSON.
- **Why** — Auditors grep on this string to count refusals. Variable phrasing makes that count unreliable. JSON is heavier to parse downstream and the model is less compliant when forced to emit JSON for refusals than for answers.
- **Backing** — `corpus/notes/grounding-refusal.md`; `corpus/handbook.docx` §2.

### 009 · uv as the package manager.

- **Decision** — `uv` for venv + dependency management; pinned in `uv.lock`.
- **Alternatives** — `pip + venv`; Poetry; conda.
- **Why** — `uv` installs the venv in seconds, locks transitive deps deterministically, and can install pinned Python versions without a system Python. Important for air-gapped reproducibility — the same `uv.lock` produces the same venv on every host.
- **Backing** — `pyproject.toml`; `Makefile`.

### 010 · No web UI in this repo.

- **Decision** — CLI only. Library API is the integration surface for any UI a deployer adds.
- **Alternatives** — Ship a Gradio chat UI; Streamlit dashboard.
- **Why** — The brief is offline + on-prem. A bundled UI implies an opinion about hosting, sessions, auth, and styling none of which is portable across enterprise environments. Operators build the UI they need on top of the library.
- **Backing** — Brief §What `crag` is not for; this repo's README.
