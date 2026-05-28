"""LLM-as-judge for answer faithfulness.

Uses the same local model that generated the answer (or a different
local model passed via `backend`). Parses a single-line JSON object
of the shape {"faithful": bool, "unsupported_claims": [...], "reason": "..."}.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from crag.llm.backends import LLMBackend
from crag.llm.prompts import JUDGE_SYSTEM_PROMPT, build_judge_prompt
from crag.retrieval.search import RetrievedChunk


@dataclass(frozen=True)
class FaithfulnessResult:
    faithful: bool
    unsupported_claims: list[str]
    reason: str
    raw: str


_JSON_OBJECT = re.compile(r"\{.*\}", re.DOTALL)


def judge_faithfulness(
    question: str,
    answer: str,
    chunks: list[RetrievedChunk],
    *,
    backend: LLMBackend,
) -> FaithfulnessResult:
    raw = backend.chat(
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {"role": "user", "content": build_judge_prompt(question, answer, chunks)},
        ],
        max_tokens=400,
        temperature=0.0,
    )
    parsed = _parse(raw)
    return FaithfulnessResult(
        faithful=bool(parsed.get("faithful", False)),
        unsupported_claims=[str(s) for s in parsed.get("unsupported_claims", [])],
        reason=str(parsed.get("reason", "")),
        raw=raw,
    )


def _parse(text: str) -> dict:
    m = _JSON_OBJECT.search(text)
    if not m:
        return {"faithful": False, "unsupported_claims": [], "reason": "judge returned no JSON"}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {
            "faithful": False,
            "unsupported_claims": [],
            "reason": "judge returned malformed JSON",
        }
