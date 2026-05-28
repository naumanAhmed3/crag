# Incremental ingestion — never re-embed what hasn't changed

Bulk re-ingestion is the path of least resistance: wipe the index,
walk the corpus, embed everything. It is also the wrong default for any
non-trivial corpus, because embedding cost dominates ingest time and
re-embedding 99 % of documents that haven't changed wastes 99 % of
the budget. Incremental ingestion exists to bring that wasted work to
zero.

## The manifest pattern

The simplest correct design is a small SQLite manifest sitting
alongside the vector store:

```
files (path PK, mtime, size, sha256, chunk_count, ingested_at)
chunks (id PK, file_path FK ON DELETE CASCADE, ordinal, tokens)
```

On every ingest run:

1. Walk the corpus directory; collect the current `(path, mtime, size)`
   tuple per file.
2. For each file:
   - If the manifest has no record → **add** (parse, chunk, embed,
     insert).
   - If `mtime` and `size` both match the manifest → **skip** (the
     file is provably unchanged).
   - If either differs → **update** (re-parse, re-chunk, re-embed,
     replace the file's chunks atomically).
3. After processing, any manifest file not seen on disk → **remove**
   (drop its chunks from the vector store via the cascade).

`mtime` + `size` is sufficient for the local-disk case. For network
mounts (NFS, SMB) where mtime can lie, fall back to the file's
SHA-256, computed only when mtime+size match but you want a paranoid
check.

## Chunk identifiers must be stable

The deterministic chunk ID is the second half of the trick:

```
chunk_id = sha256(file_path || ordinal || chunk_text)
```

A file with two changed sentences ends up with two new chunk IDs and
the rest are bit-for-bit identical to the old ones. If the vector
store and manifest both key by this ID, an update is the symmetric
difference: delete the chunk IDs that disappeared, upsert the chunks
that are new, leave the unchanged 95 % alone.

## Watch mode for low-latency freshness

For corpora where the user expects near-real-time freshness (a wiki, a
shared docs folder), wrap the same pipeline in a filesystem watcher
(`watchdog` on POSIX). The watcher debounces events, drops temp files
(`.tmp`, `.swp`, OS metadata), and feeds each settled file change into
the same incremental ingest path. The manifest semantics are
unchanged.

## What you give up

Strict incrementality assumes the chunking and embedding model haven't
changed. If either does, you must re-embed the corpus. Two ways to
make this explicit:

- Stamp the manifest with the active chunker config + embedding model
  ID. On mismatch at startup, refuse to start an incremental ingest;
  require an explicit `--rebuild` flag.
- Version the vector store collection name (`docs_bge_small_v1`,
  `docs_bge_base_v1`); reindexing builds the new collection alongside
  the old, with a switch-over once it's complete.
