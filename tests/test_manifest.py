from __future__ import annotations

from pathlib import Path

from crag.ingest.manifest import Manifest, chunk_id, file_sha256


def test_chunk_id_is_deterministic() -> None:
    a = chunk_id("/x.md", 0, "hello world")
    b = chunk_id("/x.md", 0, "hello world")
    assert a == b
    assert len(a) == 64


def test_chunk_id_changes_with_text() -> None:
    a = chunk_id("/x.md", 0, "hello")
    b = chunk_id("/x.md", 0, "hello!")
    assert a != b


def test_chunk_id_changes_with_ordinal() -> None:
    a = chunk_id("/x.md", 0, "same")
    b = chunk_id("/x.md", 1, "same")
    assert a != b


def test_file_sha256_streams(tmp_path: Path) -> None:
    p = tmp_path / "a.txt"
    p.write_text("hello world")
    assert file_sha256(p) == file_sha256(p)


def test_manifest_upsert_and_unchanged(tmp_path: Path) -> None:
    p = tmp_path / "a.md"
    p.write_text("hello")
    m = Manifest(tmp_path / "manifest.sqlite")
    try:
        assert not m.unchanged(p)  # not yet ingested
        sha = file_sha256(p)
        evicted = m.upsert_file(p, sha, [("c1", 0, 5), ("c2", 1, 7)])
        assert evicted == []  # nothing prior
        assert m.unchanged(p)  # mtime + size match
        assert m.stats()["files"] == 1
        assert m.stats()["chunks"] == 2

        # Re-upsert with a partly overlapping chunk set; expect the
        # disappearing chunk to be returned for eviction.
        evicted = m.upsert_file(p, sha, [("c1", 0, 5), ("c3", 1, 9)])
        assert evicted == ["c2"]
        assert m.stats()["chunks"] == 2

        # Remove returns the surviving chunk ids for the caller to delete.
        evicted2 = m.remove(p)
        assert sorted(evicted2) == ["c1", "c3"]
        assert m.stats()["files"] == 0
        assert m.stats()["chunks"] == 0
    finally:
        m.close()
