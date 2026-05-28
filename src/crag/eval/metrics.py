"""Retrieval metrics computed against a gold set.

Three metrics, all you actually need for retrieval-only studies:

- **Recall@K** — fraction of gold items where at least one expected
  source appears in the top-K retrieved chunks.
- **Precision@K** — share of top-K retrievals that match an expected
  source.
- **MRR** — mean reciprocal rank of the first matching chunk; rewards
  ranking the right answer higher rather than just including it.

"Match" is a substring test on `file_path` (case-insensitive) so the
gold can be authored against bare filenames, not absolute paths.

The optional **substring evidence check** independently asks: was the
expected verbatim phrase actually present in any retrieved chunk's text?
This catches the case where the right file is retrieved but the chunk
containing the answer wasn't.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from crag.retrieval.search import RetrievedChunk


@dataclass(frozen=True)
class GoldItem:
    id: str
    question: str
    expected_files: list[str]
    expected_substrings: list[str] = field(default_factory=list)


def load_gold(path: Path) -> list[GoldItem]:
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or []
    return [
        GoldItem(
            id=str(item["id"]),
            question=str(item["question"]),
            expected_files=[str(p) for p in item.get("expected_files", [])],
            expected_substrings=[str(s) for s in item.get("expected_substrings", [])],
        )
        for item in raw
    ]


def _file_match(file_path: str, expected: Iterable[str]) -> bool:
    fp = file_path.lower()
    return any(e.lower() in fp for e in expected)


@dataclass
class RetrievalMetrics:
    n_questions: int
    recall_at_k: float
    precision_at_k: float
    mrr: float
    substring_recall: float | None  # None if no substrings in the gold set
    per_question: list[dict[str, Any]] = field(default_factory=list)

    def asdict(self) -> dict:
        return {
            "n_questions": self.n_questions,
            "recall_at_k": round(self.recall_at_k, 4),
            "precision_at_k": round(self.precision_at_k, 4),
            "mrr": round(self.mrr, 4),
            "substring_recall": (
                round(self.substring_recall, 4) if self.substring_recall is not None else None
            ),
            "per_question": self.per_question,
        }


def evaluate_retrieval(
    gold: list[GoldItem],
    retriever_fn,  # callable: question -> list[RetrievedChunk]
    *,
    top_k: int,
) -> RetrievalMetrics:
    """Run the retriever over every gold item and aggregate."""
    n = len(gold)
    if n == 0:
        return RetrievalMetrics(0, 0.0, 0.0, 0.0, None, [])

    recalls: list[int] = []
    precisions: list[float] = []
    rrs: list[float] = []
    substring_hits: list[int] = []
    has_substrings = False
    per_question: list[dict[str, Any]] = []

    for item in gold:
        hits: list[RetrievedChunk] = retriever_fn(item.question)[:top_k]
        # binary recall — any expected file in the topK?
        relevances = [_file_match(h.file_path, item.expected_files) for h in hits]
        recall = int(any(relevances))
        recalls.append(recall)
        precisions.append(sum(relevances) / max(top_k, 1))

        rr = 0.0
        for rank, hit_rel in enumerate(relevances, start=1):
            if hit_rel:
                rr = 1.0 / rank
                break
        rrs.append(rr)

        substring_hit: int | None = None
        if item.expected_substrings:
            has_substrings = True
            combined = "\n".join(h.text for h in hits).lower()
            substring_hit = int(all(s.lower() in combined for s in item.expected_substrings))
            substring_hits.append(substring_hit)

        per_question.append(
            {
                "id": item.id,
                "recall": recall,
                "precision_at_k": round(precisions[-1], 4),
                "rr": round(rr, 4),
                "substring_hit": substring_hit,
                "top_files": [h.file_path for h in hits],
            }
        )

    return RetrievalMetrics(
        n_questions=n,
        recall_at_k=sum(recalls) / n,
        precision_at_k=sum(precisions) / n,
        mrr=sum(rrs) / n,
        substring_recall=(sum(substring_hits) / len(substring_hits)) if has_substrings else None,
        per_question=per_question,
    )
