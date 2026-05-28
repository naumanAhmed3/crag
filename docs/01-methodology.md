# Methodology

This is a research repo. Every claim in the README and the
`studies/` documents comes back to an experiment under `studies/` that
produced a `results.json`. This doc says how those experiments are
run, what is controlled, and how the numbers should be read.

## The unit of measurement

Each experiment runs the **gold set** (`src/crag/eval/gold.yaml`)
through one or more retrieval configurations and reports five
metrics:

| Metric | What it answers |
|---|---|
| Recall@K | Did at least one expected source land in the top-K? |
| Precision@K | What share of the top-K are relevant? |
| MRR | How high did we rank the first relevant result? |
| Substring recall | Did the verbatim phrase the gold expected appear in any retrieved chunk's text? |
| Latency (p50/p95/mean) | Wall-clock time per query, in milliseconds |

"Relevant" is a substring match between the chunk's `file_path` and
the gold item's `expected_files` list. That's deliberately permissive
— our concern is whether the right *source* surfaces; whether the
*right chunk within that source* surfaces is captured by the
substring-recall metric.

## What is controlled

For every experiment:

- **The corpus**: `corpus/` is checked into the repo. Nothing else
  is added during ingest.
- **The gold set**: `src/crag/eval/gold.yaml`. Untouched once an
  experiment starts; new gold items go to the next experiment, not
  back into the running one.
- **The hardware fingerprint**: captured in `results.json` under
  `hardware`. CPU, RAM, OS, Python version, PyTorch version, git SHA
  at run time.

What varies is named in the experiment's `config` field — chunking
size, embedding model, retrieval composition, etc.

## What is *not* a controlled variable (and how we handle it)

- **The OS page cache.** Re-running a study back-to-back is faster
  than running it cold; we re-run on a freshly-rebooted host when
  the latency delta matters. The committed numbers come from cold
  runs unless explicitly noted.
- **HF Hub download speed.** Model-download time is reported in the
  ingest wall-clock but never claimed as a measurement of the
  system — it's an environmental fact.
- **LLM-judge variance.** The local LLM judge is set to
  `temperature = 0.0` but is not perfectly deterministic across
  runs because GGUF kernels are not bit-exact on CPU. We accept a
  ±1 absolute-point band on faithfulness scores.

## How to re-run

Every study's `experiment.py` is self-contained:

```
uv run python studies/<N-name>/experiment.py
```

This produces (or overwrites) `studies/<N-name>/results.json`. The
top-level `make reproduce` runs all of them in sequence and compares
the new numbers to the committed ones, printing a pass/fail per
round.

## Reading the results

Two principles:

1. **Trends, not absolutes.** The committed numbers come from one
   reference rig. Latency on your hardware will differ; the
   *ranking* of configurations (which beat which) is what should
   transfer.
2. **Effect size, not p-values.** The gold set is small enough (≈ 15
   questions) that significance testing is not meaningful. A change
   that shifts a metric by 5 points is real; a change that shifts
   it by 1 point is within the gold's noise floor.

## Gold-set hygiene

When a query the system answers poorly is worth fixing, the
checked-in process is:

1. Add the failing question to `gold.yaml` with a new `id`
   (`q01` → `q02` → …; never recycled).
2. Re-run the affected studies; commit the updated `results.json`.
3. If the change moves a metric materially, write a one-line note in
   the affected study's `findings.md`.

Old gold items are kept in `gold.yaml` forever unless the corpus is
restructured. This makes the gold set a regression suite, not a
moving target.
