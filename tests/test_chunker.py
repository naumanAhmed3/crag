from __future__ import annotations

from crag.ingest.chunker import chunk_text

SAMPLE = (
    "Vector search is a method for finding the nearest neighbours of a query "
    "vector in a high-dimensional space. Modern systems use approximate "
    "algorithms because exact nearest-neighbour search scales poorly. The "
    "most common algorithm is HNSW, which builds a multi-layer proximity "
    "graph over the vectors. " * 8
)


def test_empty_returns_empty() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n  \t  ") == []


def test_short_text_one_chunk() -> None:
    chunks = chunk_text("This is one short sentence.", target_tokens=512)
    assert len(chunks) == 1
    assert chunks[0].ordinal == 0
    assert chunks[0].tokens > 0


def test_fixed_strategy_sizes() -> None:
    chunks = chunk_text(SAMPLE, target_tokens=64, overlap_tokens=8, strategy="fixed")
    assert len(chunks) >= 2
    # Fixed-strategy chunks should be very close to the target.
    for c in chunks[:-1]:
        assert c.tokens == 64
    assert chunks[-1].tokens <= 64


def test_sentence_snap_strategy_within_window() -> None:
    chunks = chunk_text(SAMPLE, target_tokens=80, overlap_tokens=10, strategy="sentence-snap")
    assert len(chunks) >= 2
    window = round(80 * 0.15)
    # Snap should keep chunks within ±15% of target except for the final tail.
    for c in chunks[:-1]:
        assert 80 - window - 10 <= c.tokens <= 80 + window + 10


def test_ordinals_are_dense_and_zero_based() -> None:
    chunks = chunk_text(SAMPLE, target_tokens=80, overlap_tokens=10)
    assert [c.ordinal for c in chunks] == list(range(len(chunks)))


def test_locator_is_carried_through() -> None:
    chunks = chunk_text("Hello world.", locator="p. 7")
    assert chunks[0].locator == "p. 7"
