"""Local-LLM backends. Two implementations behind one Protocol so studies
can swap generation without touching the rest of the pipeline.
"""

from crag.llm.backends import LLMBackend, make_backend
from crag.llm.prompts import GROUNDED_SYSTEM_PROMPT, JUDGE_SYSTEM_PROMPT, format_context

__all__ = [
    "GROUNDED_SYSTEM_PROMPT",
    "JUDGE_SYSTEM_PROMPT",
    "LLMBackend",
    "format_context",
    "make_backend",
]
