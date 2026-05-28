"""End-to-end question answering."""

from __future__ import annotations

import time
from dataclasses import dataclass

from crag.llm.backends import LLMBackend
from crag.llm.prompts import GROUNDED_SYSTEM_PROMPT, build_user_prompt
from crag.retrieval.search import HybridRetriever, RetrievedChunk


@dataclass(frozen=True)
class Answer:
    text: str
    chunks: list[RetrievedChunk]
    retrieval_ms: float
    generation_ms: float

    @property
    def total_ms(self) -> float:
        return self.retrieval_ms + self.generation_ms


def answer_question(
    question: str,
    retriever: HybridRetriever,
    backend: LLMBackend,
    *,
    max_tokens: int = 600,
    temperature: float = 0.2,
) -> Answer:
    t0 = time.perf_counter()
    chunks = retriever.search(question)
    retrieval_ms = (time.perf_counter() - t0) * 1000

    t1 = time.perf_counter()
    reply = backend.chat(
        messages=[
            {"role": "system", "content": GROUNDED_SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(question, chunks)},
        ],
        max_tokens=max_tokens,
        temperature=temperature,
    )
    generation_ms = (time.perf_counter() - t1) * 1000

    return Answer(
        text=reply.strip(),
        chunks=chunks,
        retrieval_ms=retrieval_ms,
        generation_ms=generation_ms,
    )
