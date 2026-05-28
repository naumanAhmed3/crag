# Compliance notes — mapping `crag` behaviour to common enterprise asks

This page does **not** claim a SOC 2 / ISO 27001 / FedRAMP / equivalent
certification. It does describe, control-by-control, what `crag` does
out of the box and what an operator would need to add to make the
system audit-ready under those frameworks.

The framing is deliberately practical: an auditor's first question is
not "is this certified?" — it is "show me the control, show me the
evidence, show me how it fails." That's what is below.

## 1. Source attribution

| Control | "Every output must cite an internal source." |
|---|---|
| What `crag` does | The grounding prompt requires `[N]` citations after every factual claim. The CLI prints each cited passage's `file_path` and `locator` alongside the answer. |
| Evidence | Sample inspection of any `crag ask` output; structured logs at `$CRAG_DATA_DIR/audit/answers.jsonl` (operator-added). |
| Failure mode | Model emits a claim with no `[N]`. Detected by `eval.judge` faithfulness scoring; surfaces in the daily audit run. |

## 2. Refusal on out-of-corpus questions

| Control | "Never answer from outside the approved corpus." |
|---|---|
| What `crag` does | System prompt instructs refusal with a verbatim string. The string is documented in `corpus/handbook.docx` §2 and is machine-grep-able. |
| Evidence | `grep "I don't have enough information" $CRAG_DATA_DIR/audit/answers.jsonl` returns a clean count. |
| Failure mode | Model refuses with a phrased variant. Detected by the same grep returning *low* counts when the off-corpus query rate is high. |

## 3. Deletion on demand

| Control | "On request, remove content X within Y hours." |
|---|---|
| What `crag` does | `corpus/code/eviction.py` removes both the manifest entries and the vector-store points for a file, then writes a structured audit-log entry. |
| Evidence | The `$CRAG_DATA_DIR/audit/evictions.jsonl` file contains one line per eviction with timestamp, file path, chunk count, reason, operator. |
| Failure mode | A file is evicted from disk but its chunks remain in the store. Detected by `corpus/code/health_check.py` (it asserts manifest chunk count equals store point count). |

## 4. Retention

| Control | "Documents must not persist past N days of being removed from the source." |
|---|---|
| What `crag` does | Incremental ingest detects file deletions and evicts on the next run. With the recommended 10-minute polling, the lag between source-of-truth deletion and index removal is ≤ 10 minutes. |
| Evidence | Manifest `ingested_at` timestamp on remaining files; eviction-log timestamps on removed files. |
| Failure mode | Ingest cron stops running. Detected by `health_check.py` returning OK with a stale `ingested_at`. Operational layer (cron monitoring) is responsible. |

## 5. Audit-log integrity

| Control | "Audit log must be tamper-evident." |
|---|---|
| What `crag` does | Audit files are append-only JSONL. The repo's eviction script and judge runner both write here. |
| Evidence | The files exist and grow monotonically. |
| Failure mode | A privileged user edits or deletes a line. **The library does not prevent this.** Operationally, the recommended pattern is to roll the audit file daily, hash it (SHA-256), and append the hash to a write-only register hosted on a separate machine. |

## 6. Approved-model register

| Control | "Only review-board-approved models may load." |
|---|---|
| What `crag` does | `Settings.embedding_model`, `reranker_model`, and `llm_model` are the canonical declarations of what loads. They are set via environment variable or config file. |
| Evidence | `crag stats` prints the active model strings. |
| Failure mode | An operator sets `CRAG_EMBEDDING_MODEL` to an unapproved model. **The library does not enforce a whitelist.** Operationally, the recommended pattern is a startup-time check against a register file (`/etc/crag/approved-models`) baked into the host image. |

## 7. Air-gap behaviour

| Control | "The runtime must not initiate outbound network connections." |
|---|---|
| What `crag` does | Every package used has been chosen for offline operation. The library itself makes no network calls; sentence-transformers and Ollama are configurable for offline (see `corpus/notes/airgap-deployment.md`). |
| Evidence | `tcpdump` on the host shows no outbound traffic during query path; full pre-staging of HF cache documented. |
| Failure mode | A sentence-transformers version check tries to reach the HF Hub. Detected by setting `TRANSFORMERS_OFFLINE=1` and `HF_HUB_OFFLINE=1`, which turns these into loud errors instead of silent waits. |

## 8. Reproducibility

| Control | "The same input produces the same output." |
|---|---|
| What `crag` does | The retrieval pipeline is deterministic (BM25 ranking, RRF, cross-encoder scores). The generation step is at `temperature = 0.2` by default — *not* fully deterministic, by design (a slightly varied answer is more readable than a robotic one). |
| Evidence | `crag eval --gold gold.yaml` produces the same retrieval metrics on repeated runs to within tolerance. |
| Failure mode | Generation varies enough to flip a citation. Detected by sampling identical questions on a schedule; flagged if the cited passages change between identical runs. |
