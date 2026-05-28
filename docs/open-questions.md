# Open questions — what we'd test next and what we didn't get to

Intellectually honest list. Anything below is either a study that
would change a decision in this repo, or a known gap we punted on.
Each is open against a real next step, not abstract aspirations.

## Studies queued behind the floor commitment

### 05 — Generation-model bake-off

Compare `qwen2.5:7b-instruct-q4_K_M` against `llama-3.1-8b-instruct-q4_K_M`,
`phi-3-mini-4k-instruct-q4_K_M`, and `gemma-2-9b-it-q4_K_M`. Metrics:
LLM-judge faithfulness, token throughput, peak VRAM, refusal rate on
an off-corpus question set.

Gates: requires a host with Ollama installed *and* a CUDA-capable
GPU. The reference rig (Apple Silicon) can stand in for token
throughput and faithfulness measurement; VRAM numbers must come from
the target rig.

### 06 — Incremental ingestion at 50 k-doc scale

Simulate a churn cycle (10 % of files modified, 1 % added, 0.5 %
deleted per day) on a 50 k-document synthetic corpus generated from
the 30-doc sample. Measure files-touched-per-cycle, index drift, end-
to-end ingest latency, RAM headroom.

Gates: corpus generation script + disk space. Not a model gate.

### 07 — Adversarial behaviour

Three sub-experiments:

- *Off-corpus question robustness*: 100 questions whose answers are
  not in the corpus. Refusal rate should be ≥ 0.95.
- *Prompt-injection-in-documents*: ingest 50 documents containing
  embedded "ignore previous instructions" payloads. Re-score
  faithfulness; expect drop on injected queries; document mitigations.
- *Jailbreak attempts*: 50 social-engineering queries. Expect refusal
  rate ≥ 0.95.

Gates: gold-set authoring. Not a model gate.

## Decisions we'd revisit if data appeared

### Q-01 · Is rrf k=60 still correct on a 2 TB corpus?

The literature converged on k=60 on web-scale retrieval. At 2 TB
across heterogeneous formats (engineering specs, vendor contracts,
blockchain records) the optimal k may shift. The lock-in rule says
re-measure after the live corpus crosses 1 M chunks. We have not.

### Q-02 · Does semantic chunking earn its cost on operational text?

`studies/03-chunking-grid/` measured fixed and sentence-snap. We did
not test embedding-distance-peak semantic chunking because the extra
ingest pass roughly doubles embed cost. If a customer specifically
ingests long-prose technical manuals (operator handbooks, regulatory
guidance), the trade may flip.

### Q-03 · Hybrid lost on the bundled corpus — is that a corpus shape or a real result?

In `studies/01-hybrid-fusion/`, hybrid did not beat dense-only on
Recall@5 on the 15-question gold over the sample corpus. That's
because dense retrieval saturated recall at 1.0 — there was no
room to improve. The conclusion to take seriously is *this corpus
is too small and too dense-friendly for hybrid to demonstrate its
value*. On the brief's full corpus (technical jargon, vendor
identifiers, version numbers), hybrid is expected to win
materially; the published literature is unanimous on that. Worth
re-running on a 5 k-document slice as a sanity check.

### Q-04 · Cross-encoder rerank on contract-heavy corpora

`bge-reranker-v2-m3` is trained on a broad domain mix. Its behaviour
on legal-contract text (where the same noun-phrase appears under
many synonyms — "Vendor", "Supplier", "the Party of the second
part") has not been measured in our studies. A small contract gold
set would close this.

## Gaps we know we have

### G-01 · Multi-modal documents

CAD diagrams, photos, scanned-but-not-OCR'd documents are out of
scope for this artifact. The right next move is a separate ingest
pipeline that OCRs at parse time and routes the extracted text
through the same chunker / embedder. Adding this without measuring
its faithfulness impact would be irresponsible.

### G-02 · Multilingual corpora

The embedding model and reranker we ship are English-only.
`bge-m3` (multilingual) and `nomic-embed-text` would be reasonable
swaps; the change is one config value and a re-embed. We have not
re-run the gold set against either.

### G-03 · Concurrent writers

Qdrant local mode rejects concurrent writers explicitly (and the
runbook at `corpus/runbooks/incident-stale-answers.txt` describes
recovery). At Vantage's per-hub workstation scale this is correct.
The graduation path to Qdrant server mode unblocks concurrent
writers; it is documented in `docs/02-recommendations.md` but not
yet exercised in any study.

### G-04 · Live faithfulness dashboard

The library produces faithfulness scores; the *display* of those
scores over time is left to the operator. A small Grafana / Plotly
dashboard would close the loop. We did not build one because the
choice is environment-specific.
