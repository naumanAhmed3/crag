# Risk register

Failure modes a real deployment will hit, ranked by likelihood ×
impact. The matrix is the procurement-team version of "what
could go wrong" — every row is a thing this repo, on its own,
mitigates *up to a point* and where the next ring of defence has to
come from operational practice.

Severities (impact): **S1** loss of trust / wrong answer, **S2**
service outage, **S3** degraded quality, **S4** audit-trail gap.

| ID | Risk | Likelihood | Impact | Owner | Mitigation in this repo | Residual handling |
|---|---|---|---|---|---|---|
| R-01 | Hallucinated answer the user trusts | low | **S1** | retrieval | Refusal-by-default grounding prompt; LLM-judge faithfulness scoring; verbatim refusal string for auditability | Sample 0.5 % of answers daily into the judge; alert ops if faithfulness < 0.95 over a 24 h window |
| R-02 | Stale index after a corpus update | medium | **S3** | ops | Manifest mtime + size detection; 10-min poll OR watch mode | Cron monitor compares `crag stats` files to the file-share count hourly; alert on drift > 1 % |
| R-03 | Right document retrieved, wrong chunk | medium | **S3** | retrieval | Cross-encoder rerank; substring-recall metric in the gold set | Failing queries land in the gold set; chunker tuned per `studies/03` if needed |
| R-04 | Vector store corruption (crash mid-upsert) | low | **S2** | ingestion | Qdrant local mode is crash-safe (WAL); manifest is WAL SQLite | Daily `tar` snapshot to NAS; restore is `tar -xf` + `crag stats` |
| R-05 | LLM OOM at long-context query | medium | **S2** | gen runtime | Configured `num_ctx` ≤ 8192; smaller `phi3:3.8b-q4` documented as fallback | Watchdog restarts Ollama on OOM; alert if rate > 1 / hr |
| R-06 | Embedding model drift between ingest and query | low | **S3** | ops | Settings.embedding_model is the canonical source; collection name versioned on change | Pre-deploy hook compares the new bundle's `embedding_model` to the manifest's; blocks if mismatched |
| R-07 | Right-to-be-forgotten request not honoured | low | **S1** | ops | `corpus/code/eviction.py` deletes + audit-logs | Quarterly drill: evict a known canary file, verify it disappears from `crag ask` and the audit log captures it |
| R-08 | Audit log tampered with | low | **S4** | security | Append-only JSONL; daily SHA of rotated logs to a controlled register | Logs forwarded to read-only NAS hourly; external hash check |
| R-09 | New chunker shipped without re-embed | low | **S3** | deploy | Manifest stamped with chunker config; CI refuses incremental ingest on mismatch | Operator runs `--rebuild` flag explicitly to acknowledge the cost |
| R-10 | Two operators run `crag ingest` simultaneously | low | **S2** | ops | Qdrant local rejects with explicit lock-conflict error | Ingest wrapped in a flock; cron schedule single-instance |
| R-11 | OS page cache cold, p95 latency triples | high | **S3** | ops | Document the cold-start expectation; `OLLAMA_KEEP_ALIVE=24h` | Warm-up query at host boot in the systemd unit |
| R-12 | Adversarial document injects instructions | low | **S1** | security | Grounding prompt isolates passages from instructions; passage delimiter clear | Pre-ingest hook scans for known prompt-injection patterns; quarantines hits |

## Threats not in scope for this artifact

- **Network attack on the host** — air-gap is assumed; perimeter
  defence is delegated to the operator's network team.
- **Insider compromise** — anyone with shell on the box can read the
  corpus directly. RAG is a search interface, not a permission
  boundary.
- **GPU driver / firmware vulnerabilities** — vendor patching cycle.
