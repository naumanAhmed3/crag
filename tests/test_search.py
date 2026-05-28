from __future__ import annotations

from crag.retrieval.search import _rrf
from crag.retrieval.store import Hit


def _hit(cid: str, score: float = 1.0) -> Hit:
    return Hit(chunk_id=cid, score=score, payload={"chunk_id": cid})


def test_rrf_one_list_matches_inverse_rank() -> None:
    dense = [_hit("a"), _hit("b"), _hit("c")]
    out = _rrf(dense, [], k=60)
    assert out["a"][0] == 1 / 61
    assert out["b"][0] == 1 / 62
    assert out["c"][0] == 1 / 63


def test_rrf_sums_across_lists() -> None:
    dense = [_hit("a"), _hit("b")]
    sparse_ids = ["b", "a"]
    out = _rrf(dense, sparse_ids, k=60)
    # `a` is rank 1 dense + rank 2 sparse → 1/61 + 1/62
    assert out["a"][0] == 1 / 61 + 1 / 62
    # `b` is rank 2 dense + rank 1 sparse → 1/62 + 1/61
    assert out["b"][0] == 1 / 62 + 1 / 61
    # Ranks are recorded.
    assert out["a"][1] == 1 and out["a"][2] == 2
    assert out["b"][1] == 2 and out["b"][2] == 1


def test_rrf_unique_to_one_list() -> None:
    dense = [_hit("a")]
    sparse_ids = ["x"]
    out = _rrf(dense, sparse_ids, k=60)
    assert out["a"][2] is None  # not in sparse
    assert out["x"][1] is None  # not in dense
