# Sample corpus — Vantage Holdings analog

This corpus is the public, redistributable stand-in for the fictional
client's (`docs/00-brief.md`) ~2.3 TB private knowledge base. It is
intentionally small (~20 documents, ~25k words) so the repo stays cheap
to clone and every experiment in `studies/` can finish on a laptop in
minutes — while still being substantive enough that retrieval metrics
move meaningfully between rounds.

**Why this domain.** The documents are about retrieval, vector search,
quantised LLMs, and offline deployment. That choice is deliberate: it
makes the demo *self-referential* (a reader can immediately ask "How
does HNSW work?" and see a real grounded answer), which is the most
honest way to demonstrate a RAG system without parading a private
corpus.

**Provenance.** Every document is originally authored for this repo by
the project owner. No third-party text is included; nothing needs
license attribution. Replace this directory wholesale with your own
documents for a real deployment.

## Layout

```
corpus/
├── README.md              this file
├── notes/                 markdown technical notes (~10 files)
├── runbooks/              plain-text operational runbooks (~3 files)
├── configs/               yaml configuration snippets (~2 files)
├── code/                  short python utilities (~2 files)
├── handbook.docx          DOCX policy excerpt (generated)
└── benchmarks.xlsx        XLSX metrics sheet (generated)
```

To regenerate the binary `.docx` and `.xlsx` from source, run
`python scripts/build_corpus.py` from the repo root.
