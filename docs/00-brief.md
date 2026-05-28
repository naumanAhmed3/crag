# The anchoring brief — Vantage Holdings

Every choice in this repo answers to a single fictional client. Naming
the client up front keeps the design honest: when a tradeoff comes up,
the answer is whichever option serves Vantage. The brief below is
plausible and unambiguously fictional; replace it with your own when
applying the artifact to a real engagement.

## The company

**Vantage Holdings** is a 12 200-employee industrial conglomerate
operating in metals refining, energy infrastructure, and on-chain
commodity-tracking services. Headquartered in Singapore, with field
operations across Australia, Indonesia, and Kazakhstan. The internal
documentation set is the institutional memory of forty years of
operations:

- Engineering specifications (PDFs, AutoCAD-exported text, CAD review notes)
- Regulatory filings (multi-jurisdictional, dense citation patterns)
- Vendor master agreements + amendments (DOCX, ~30 000 documents)
- Internal wiki pages (Confluence export, Markdown)
- Operations runbooks and incident postmortems (plain text + Markdown)
- Source code for the on-chain attestation service (Python + Go + Rust)
- Blockchain operations data (transaction logs, contract source, audit
  reports, ~140 000 records)

Combined, ~**2.3 TB** on the file shares; ~38 M unique chunks at the
chunking config we settle on in `studies/03/`.

## The constraint

Legal compliance and a recent third-party security review require the
production system to be **air-gapped**. No outbound network from the
host that serves answers, no embeddings or queries leaving the
perimeter, no third-party APIs at inference time. This rules out every
cloud LLM API, the entire OpenAI / Anthropic / Cohere catalogue, and
most vector-DB SaaS offerings.

## The hardware

Each office hub runs a single workstation rated for both indexing and
serving:

- 8-core Xeon W-class CPU, 16 GB system RAM.
- One discrete NVIDIA RTX 3060 (laptop class), **6 GB VRAM**.
- 4 TB local NVMe; periodic snapshots to an internal NAS.

There is no second machine. The same host ingests, embeds, indexes,
serves retrieval, and runs the local LLM.

## What "answer" means

Every answer the system returns must:

1. Cite the source passage(s) it draws on, by file path + locator
   (page number, sheet, section).
2. Refuse — using the verbatim string `I don't have enough information
   in the indexed corpus to answer this.` — when the retrieved
   passages do not support an answer.
3. Land within an SLA the auditors agreed to:
   **p95 ≤ 3 000 ms retrieval, ≤ 30 000 ms grounded answer**.

## What the users do

~40 % of headcount (≈ 4 800 people) will use the system at least
weekly. Peak concurrency is bounded by office working hours (small —
< 20 simultaneous users per hub). The hardest queries are technical:
operators asking "what's the torque spec for valve VLV-44A on platform
NL-12 as of the 2023 maintenance revision?" — answers that demand both
exact lexical hits (valve identifier) and a sense of context (the most
recent revision).

## What we are explicitly not designing for

- **Multi-modality.** The corpus is text. CAD diagrams, photos, and
  scanned-but-not-OCR'd documents are out of scope.
- **Fine-tuning the generation model.** Legal has flagged the cost,
  the QA burden, and the model-drift risk of doing this in-house.
- **Realtime ingest under 5 minutes.** A 10-minute polling cadence is
  acceptable; the watcher exists for opportunistic use, not as a hard
  freshness SLA.

## How this brief shapes downstream decisions

Every tradeoff in `studies/` and `docs/decision-log.md` resolves to
the Vantage frame:

- Default to lighter models (BGE-small on CPU, qwen2.5:7b-q4 on the
  RTX 3060) because that's the box we have.
- Default to deterministic, file-backed components (SQLite manifest,
  embedded Qdrant) because air-gapped operators don't want a server
  process they have to babysit.
- Default to LLM-as-judge running on the same model that generated
  the answer, because importing a separate eval model would mean
  another download, another VRAM tenant, another approval cycle.

For any real customer, the analogous step is one paragraph of context
of this shape — concrete numbers, real constraints, named users. The
rest of the repo is downstream of it.
