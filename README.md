# crag — an offline RAG field investigation

A public engineering record of building a grounded, source-cited
document-Q&A system that fits on commodity laptop hardware and answers
only from an approved internal corpus. The repo is structured as a
**series of case studies** (`studies/00 … 04`), each with a runnable
experiment, a committed `results.json`, and a one-page findings
write-up. The synthesis is a working Python library (`src/crag/`) you
can drop into a real engagement.

It is shaped around a fictional client brief — **Vantage Holdings**,
~12 000 employees, 2.3 TB of mixed internal documentation, served from
a single RTX 3060 laptop (6 GB VRAM, 16 GB RAM), air-gapped. See
`docs/00-brief.md`. Every architectural choice answers to that brief.

---

## Why this exists

Two reasons:

- **The problem keeps showing up.** "Offline / on-prem / low-VRAM RAG
  over a large internal corpus" is the brief for a meaningful share
  of enterprise AI consulting. Most public RAG demos use cloud APIs
  and small toy corpora; none are useful as evidence for the brief
  this repo addresses.
- **The decisions in a RAG system are knowable from data.** The
  retrieval mode, the reranker on/off, the chunk size — these are
  not religious choices. They are *measurable*. This repo measures
  them on a single corpus end-to-end, commits the numbers, and
  documents what changed in the architecture as a result.

---

## Quickstart

```bash
git clone https://github.com/naumanAhmed3/crag
cd crag
make setup            # installs Python 3.11 + all deps via uv
make ingest-sample    # parses + chunks + embeds the bundled corpus
make stats            # confirm > 0 chunks in the manifest and store

# retrieval works without an LLM —
CRAG_LLM_BACKEND=none uv run crag eval

# end-to-end (grounded answer):
ollama pull qwen2.5:7b-instruct-q4_K_M    # ~4.4 GB; one-time
make ask Q="How does HNSW work?"
```

First-run downloads (bge-small + reranker) total ~600 MB; ingest +
gold-set evaluation finish in <1 minute on a M3-class laptop.

---

## How to read this repo

| You want to … | Open |
|---|---|
| Understand the constraints driving every decision | `docs/00-brief.md` |
| See the recommended architecture and why | `docs/02-recommendations.md` |
| Read the experiments and their numbers | `studies/00 … 04/` |
| Reproduce / refresh the numbers on your hardware | `docs/01-methodology.md` |
| Trace any decision to its alternatives | `docs/decision-log.md` |
| See risk / cost / compliance treatment | `docs/risk-register.md`, `docs/cost-model.md`, `docs/compliance-notes.md` |
| Find what we didn't get to and what we'd test next | `docs/open-questions.md` |
| Use the library API in your own code | `src/crag/` (start at `cli.py`) |

---

## The findings, in one table

Numbers from the reference rig (see `docs/hardware-fingerprint.md`).
Every row points at a `studies/<round>/results.json` you can verify.

| Round | What we asked | What we found | Locked in? |
|---|---|---|---|
| 00 — Baseline | What does dense-only get us? | Recall@5 1.000 · MRR 0.883 · p95 13 ms | starting point |
| 01 — Hybrid fusion | Does adding BM25 + RRF help? | Δ MRR +1.7 pts · Δ Recall@5 −6.7 pts on this corpus; literature predicts hybrid wins at production scale | enabled, with caveat |
| 02 — Cross-encoder rerank | Worth the latency? | +1.4 pts Precision · +1 320 ms p95 on CPU; rule (≥+8 pts @ ≤+300 ms) **rejects** for this corpus | per-query opt-in |
| 03 — Chunking grid | Which size + strategy wins? | 1024 · sentence-snap wins locally; we ship 512 · sentence-snap to keep LLM context budget safe | default 512 / 64 / snap |
| 04 — Embedding bake-off | bge-small vs bge-base vs e5-small | See `studies/04-embedding-bakeoff/results.json` for numbers | see study |

Each of the four findings sits in a `findings.md` next to its
`results.json`; that's where the per-question detail lives.

---

## The stack we landed on

| Concern | Component | Why |
|---|---|---|
| Generation | Ollama + `qwen2.5:7b-instruct-q4_K_M` | ~4.4 GB VRAM; strong instruction-following; swap is one flag |
| Embedding | sentence-transformers + `BAAI/bge-small-en-v1.5` (CPU) | 33 MB on disk, MTEB-strong, leaves the GPU for generation |
| Reranker | `BAAI/bge-reranker-v2-m3` (CPU, opt-in) | Precision lifter for the queries that need it |
| Vector store | Qdrant local (embedded) | File-backed, sharded path to 2 TB documented |
| Sparse / lexical | `rank_bm25` (in-memory) | Zero infra, deterministic, sub-ms |
| Fusion | RRF, k = 60 | No score normalisation; literature-default |
| Chunking | tiktoken token-window + sentence-snap (512 / 64) | Tunable from `Settings` per corpus |
| Manifest | SQLite (stdlib) | mtime + sha256 for incremental ingest |
| CLI | `typer` | `crag ingest / ask / stats / eval / version` |
| Package mgmt | `uv` | Pinned, reproducible offline |

What is **not** in the box (and `docs/decision-log.md` explains why):
LangChain / LlamaIndex, web UI, Docker, fine-tuning, multi-tenant
auth.

---

## Layout

```
crag/
├── README.md               this file
├── pyproject.toml          uv-managed
├── Makefile                setup, ingest-sample, ask, test, bench
├── docs/                   premium docs (see "How to read this repo")
├── src/crag/               the synthesis library
│   ├── config.py · cli.py
│   ├── ingest/             parsers · chunker · manifest · pipeline
│   ├── retrieval/          embed · qdrant store · bm25 · rerank · hybrid search
│   ├── llm/                ollama + llamacpp backends · grounding prompts
│   ├── answer/             retrieve → ground → generate
│   └── eval/               metrics · gold.yaml · llm-judge
├── studies/                round-by-round investigation
│   ├── 00-baseline/
│   ├── 01-hybrid-fusion/
│   ├── 02-reranking/
│   ├── 03-chunking-grid/
│   └── 04-embedding-bakeoff/
├── corpus/                 ~20 real docs across PDF / DOCX / XLSX / MD / TXT / code / YAML
├── benchmarks/             (reserved for the larger-corpus regimens; SCALING math in docs)
└── tests/                  pytest suite — chunker · manifest · parsers · search
```

## License

MIT. See `LICENSE`.

---

## Honest disclosures

- **The reference rig is an Apple Silicon laptop, not the brief's
  RTX 3060.** Generation-step numbers (faithfulness, VRAM, tok/s)
  ship as `PLANNED.md` until measured on the target rig. Retrieval
  numbers transfer.
- **Studies 05 (generation bake-off), 06 (incremental churn), and 07
  (adversarial) are framed as planned next steps in
  `docs/open-questions.md`.** The infrastructure to run them
  (`studies/_common.py`, the gold set, the hardware-fingerprint
  capture) is in place.
- **The sample corpus is small** (~20 documents, ~25 k words). It's
  big enough for chunking + retrieval-mode studies to move
  measurably; it's not big enough for hybrid retrieval to
  demonstrate its production-scale lift. See
  `studies/01-hybrid-fusion/findings.md` for the candid take.
