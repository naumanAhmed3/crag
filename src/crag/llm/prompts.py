"""Grounding prompts.

The system prompt is intentionally short and absolute. Two principles:

1. *Refusal is a valid answer.* If the passages don't support an answer,
   the model says so explicitly — this is what the brief means by
   "answer only from approved internal data."
2. *Every claim cites a passage.* Citations are bracketed numbers
   `[N]` that index into the ordered passage list, so they round-trip
   into a UI without parsing.
"""

from __future__ import annotations

from crag.retrieval.search import RetrievedChunk

GROUNDED_SYSTEM_PROMPT = """\
You are a careful assistant answering questions strictly from the
PASSAGES provided. Follow these rules without exception:

1. Use only information from the PASSAGES. Do not draw on outside
   knowledge, even if you know the answer.
2. After each factual claim, cite the passage(s) that support it as
   `[N]` where N is the passage number from the list below.
3. If the PASSAGES do not contain enough information to answer, reply
   exactly: "I don't have enough information in the indexed corpus to
   answer this." Then briefly say what would be needed.
4. Prefer the language of the passages. Quote short phrases verbatim
   when the exact wording matters (e.g. policy clauses, numbers).
5. Be concise. No preamble, no apologies.
"""

JUDGE_SYSTEM_PROMPT = """\
You are evaluating whether an ANSWER is faithful to a set of PASSAGES.

Reply with a single JSON object on one line:

  {"faithful": true|false, "unsupported_claims": ["..."], "reason": "..."}

Rules:
- An answer is faithful only if every factual claim is directly
  supported by at least one passage.
- "I don't have enough information..." is faithful by definition,
  regardless of the passages.
- Cite specific unsupported claims in `unsupported_claims` (verbatim
  spans from the answer).
- `reason` is one sentence.
"""


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Render a passage list ready to drop into the user prompt."""
    if not chunks:
        return "(no passages retrieved)"
    parts: list[str] = []
    for i, c in enumerate(chunks, start=1):
        head = f"[{i}] {c.file_path}"
        if c.locator and c.locator != "document":
            head += f" — {c.locator}"
        parts.append(f"{head}\n{c.text.strip()}")
    return "\n\n".join(parts)


def build_user_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    return (
        "PASSAGES:\n"
        f"{format_context(chunks)}\n\n"
        "QUESTION:\n"
        f"{question}\n\n"
        "ANSWER (cite passages as [N]):"
    )


def build_judge_prompt(question: str, answer: str, chunks: list[RetrievedChunk]) -> str:
    return (
        "PASSAGES:\n"
        f"{format_context(chunks)}\n\n"
        f"QUESTION:\n{question}\n\n"
        f"ANSWER:\n{answer}\n\n"
        "Evaluate faithfulness."
    )
