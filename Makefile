.DEFAULT_GOAL := help

PY    := uv run python
CRAG  := uv run crag

.PHONY: help
help:  ## list targets
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z0-9_.-]+:.*?## / {printf "  \033[1m%-22s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: setup
setup:  ## create venv + install all deps
	uv sync --all-extras

.PHONY: ingest-sample
ingest-sample:  ## ingest the bundled sample corpus
	$(CRAG) ingest ./corpus

.PHONY: ask
ask:  ## ask the system a question, e.g. make ask Q="how does HNSW work"
	$(CRAG) ask "$(Q)"

.PHONY: stats
stats:  ## print corpus + index stats
	$(CRAG) stats

.PHONY: eval
eval:  ## run the gold-set evaluation
	$(CRAG) eval

.PHONY: test
test:  ## run pytest
	uv run pytest

.PHONY: lint
lint:  ## ruff check + format check
	uv run ruff check .
	uv run ruff format --check .

.PHONY: fmt
fmt:  ## auto-format
	uv run ruff check --fix .
	uv run ruff format .

.PHONY: bench
bench:  ## run all benchmarks; commit results to benchmarks/results/
	$(PY) benchmarks/run_all.py

.PHONY: reproduce
reproduce:  ## re-run every committed study; pass/fail per round
	$(PY) -m crag.eval.reproduce

.PHONY: clean
clean:  ## wipe local state (qdrant data + manifest)
	rm -rf data/

.PHONY: clean-all
clean-all: clean  ## also wipe venv
	rm -rf .venv .ruff_cache .pytest_cache
