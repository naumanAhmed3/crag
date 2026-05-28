"""Liveness + readiness probe for the crag service.

Bind a `/healthz` endpoint to this script's exit code, or run it from
the orchestrator's `livenessProbe`. Exit codes:

    0  OK
    1  index empty (manifest reports 0 files)
    2  vector store size != manifest chunk count (drift)
    3  ollama not reachable / model not loaded

The probe is deliberately strict: drift between the manifest and the
store is silent-bad and worth restarting for. If you only want
liveness (process is up), use `crag version` instead.
"""

from __future__ import annotations

import sys

from crag.config import settings
from crag.ingest.manifest import Manifest
from crag.retrieval.embed import Embedder
from crag.retrieval.store import VectorStore


def main() -> int:
    s = settings()
    embedder = Embedder(s.embedding_model)
    store = VectorStore(s.data_dir, collection="default", dim=embedder.dim)
    with Manifest(s.data_dir / "manifest.sqlite") as manifest:
        mstats = manifest.stats()

    if mstats["files"] == 0:
        print("FAIL: manifest is empty (no files ingested)")
        return 1

    store_points = store.count()
    if store_points != mstats["chunks"]:
        print(f"FAIL: drift — store has {store_points} points, manifest expects {mstats['chunks']}")
        return 2

    if s.llm_backend == "ollama":
        try:
            import ollama

            ollama.Client().list()
        except Exception as e:
            print(f"FAIL: ollama unreachable ({e!s})")
            return 3

    print(
        f"OK  files={mstats['files']:,}  chunks={mstats['chunks']:,}  "
        f"tokens={mstats['tokens']:,}  store={store_points:,}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
