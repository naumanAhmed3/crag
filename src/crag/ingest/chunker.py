"""Token-based chunking with optional sentence-boundary snapping.

The chunker is the most-tuned component in any RAG system; we expose it
deterministically so studies in `studies/03-chunking-grid/` can sweep it.

Two strategies:

- **fixed** — hard cut at `chunk_tokens`, with `chunk_overlap` carry-over.
  Predictable, fastest, occasionally splits a sentence mid-word in the
  worst case.
- **sentence-snap** — same target size, but the cut point is shifted to
  the nearest sentence boundary inside a ±15 % window. Avoids splitting
  sentences across chunks at the cost of slightly variable chunk sizes.

Tokenisation is `tiktoken` (`cl100k_base`). The choice is convenient
(stable, fast, no model download) and the chunk sizes line up with the
context budgets of every major instruction-tuned model.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal


@dataclass(frozen=True)
class Chunk:
    """One unit of retrieval. Ordinal is per-file, 0-indexed."""

    ordinal: int
    text: str
    tokens: int
    locator: str  # carried from the source RawText so citations stay precise


# A pragmatic sentence splitter — handles the common cases without a heavy
# NLP dependency. Edge cases (URLs, abbreviations) cost a few percent of
# precision but never break retrieval.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[\"'`])")


@lru_cache(maxsize=1)
def _encoder():
    import tiktoken

    return tiktoken.get_encoding("cl100k_base")


def _split_sentences(text: str) -> list[str]:
    parts = _SENTENCE_END.split(text)
    return [p.strip() for p in parts if p.strip()]


def chunk_text(
    text: str,
    *,
    target_tokens: int = 512,
    overlap_tokens: int = 64,
    strategy: Literal["fixed", "sentence-snap"] = "sentence-snap",
    locator: str = "document",
) -> list[Chunk]:
    """Split `text` into chunks. Empty / whitespace input returns [].

    `overlap_tokens` is the number of tokens from the tail of one chunk
    repeated at the head of the next — small, but enough for retrieval
    queries that straddle the boundary.
    """
    text = text.strip()
    if not text:
        return []

    enc = _encoder()
    tokens = enc.encode(text)

    if strategy == "fixed":
        chunks = list(_chunk_fixed(text, tokens, enc, target_tokens, overlap_tokens))
    else:
        chunks = list(_chunk_snap(text, tokens, enc, target_tokens, overlap_tokens))

    return [Chunk(ordinal=i, text=t, tokens=n, locator=locator) for i, (t, n) in enumerate(chunks)]


def _chunk_fixed(
    _text: str,
    tokens: list[int],
    enc,
    target: int,
    overlap: int,
) -> Iterator[tuple[str, int]]:
    n = len(tokens)
    step = max(1, target - overlap)
    i = 0
    while i < n:
        window = tokens[i : i + target]
        yield enc.decode(window), len(window)
        i += step


def _chunk_snap(
    text: str,
    tokens: list[int],
    enc,
    target: int,
    overlap: int,
) -> Iterator[tuple[str, int]]:
    """Same overall slicing as fixed, but each cut is nudged to a
    sentence boundary within ±15 % of the target if one exists.
    """
    sentences = _split_sentences(text)
    if len(sentences) <= 1:
        yield from _chunk_fixed(text, tokens, enc, target, overlap)
        return

    # Pre-tokenise sentences so we can do all arithmetic in token space.
    sent_tokens: list[list[int]] = [enc.encode(s) for s in sentences]
    sent_len: list[int] = [len(t) for t in sent_tokens]

    n_sent = len(sentences)
    window = round(target * 0.15)  # boundary search radius in tokens
    i = 0
    while i < n_sent:
        running = 0
        j = i
        while j < n_sent and running + sent_len[j] <= target + window:
            running += sent_len[j]
            j += 1
            if running >= target - window:
                break
        j = max(j, i + 1)  # always advance at least one sentence
        text_chunk = " ".join(sentences[i:j])
        token_count = sum(sent_len[i:j])
        yield text_chunk, token_count

        # Step forward with a sentence-level approximation of overlap.
        if overlap <= 0 or j >= n_sent:
            i = j
            continue
        carry = 0
        back = j
        while back > i and carry < overlap:
            back -= 1
            carry += sent_len[back]
        i = max(back, i + 1)
