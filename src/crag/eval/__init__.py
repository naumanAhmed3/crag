"""Evaluation harness: gold-set retrieval metrics + LLM-as-judge faithfulness."""

from crag.eval.judge import FaithfulnessResult, judge_faithfulness
from crag.eval.metrics import RetrievalMetrics, evaluate_retrieval

__all__ = [
    "FaithfulnessResult",
    "RetrievalMetrics",
    "evaluate_retrieval",
    "judge_faithfulness",
]
