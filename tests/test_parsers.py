from __future__ import annotations

from pathlib import Path

import pytest

from crag.ingest.parsers import parse


def test_parse_markdown(tmp_path: Path) -> None:
    p = tmp_path / "x.md"
    p.write_text("# Title\n\nA short paragraph about HNSW.")
    blocks = parse(p)
    assert len(blocks) == 1
    assert "HNSW" in blocks[0].text


def test_parse_unsupported_raises(tmp_path: Path) -> None:
    p = tmp_path / "x.unknown"
    p.write_text("opaque bytes")
    with pytest.raises(KeyError):
        parse(p)


def test_parse_empty_file_returns_empty(tmp_path: Path) -> None:
    p = tmp_path / "blank.md"
    p.write_text("   \n\t\n")
    assert parse(p) == []
