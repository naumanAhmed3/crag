"""Utility: force-evict a set of files from both manifest and vector store.

Use when a document needs to disappear urgently (compliance request,
accidental ingest of a private file, retraction). Normal incremental
ingest only evicts files that are no longer on disk; this script
evicts files that are still on disk but should not be searchable.

Usage:
    python eviction.py --reason "GDPR right-to-be-forgotten" path1 path2 ...

The script writes an audit-log entry per evicted file to
$CRAG_DATA_DIR/audit/evictions.jsonl with the SHA-256, chunk count,
and reason. Auditors grep this file for "reason: <category>" to
generate compliance reports.
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from crag.config import settings
from crag.ingest.manifest import Manifest
from crag.retrieval.embed import Embedder
from crag.retrieval.store import VectorStore


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("--reason", required=True, help="Audit-log reason string.")
    args = ap.parse_args()

    s = settings()
    embedder = Embedder(s.embedding_model)
    store = VectorStore(s.data_dir, collection="default", dim=embedder.dim)
    audit_path = s.data_dir / "audit" / "evictions.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)

    with Manifest(s.data_dir / "manifest.sqlite") as manifest, audit_path.open("a") as audit:
        for p in args.paths:
            p = p.resolve()
            fr = manifest.get(p)
            if fr is None:
                print(f"skip: {p} (not in manifest)")
                continue
            evicted = manifest.remove(p)
            store.delete(evicted)
            entry = {
                "ts": time.time(),
                "path": str(p),
                "sha256": fr.sha256,
                "chunks_removed": len(evicted),
                "reason": args.reason,
                "operator": os.environ.get("USER", "unknown"),
            }
            audit.write(json.dumps(entry) + "\n")
            print(f"evicted: {p} ({len(evicted)} chunks)")


if __name__ == "__main__":
    main()
