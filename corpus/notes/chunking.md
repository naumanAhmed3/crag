# Chunking — the most under-investigated lever in RAG

Chunking is the step where you decide what unit of text the retriever
will index, score, and return. It looks trivial — split the document
into pieces — and is, in practice, the single largest source of
recall and precision swings outside of the embedding model itself.
A poorly chunked corpus can hide good retrieval, and a well-chunked one
can paper over a mediocre retriever.

## Three strategies, ordered by sophistication

1. **Fixed token windows.** Cut every `N` tokens, with a small overlap
   (`o`) so a query straddling a boundary can still match. Predictable,
   deterministic, fastest. The downside is mid-sentence splits — the
   last token of a chunk might be the verb of an unfinished clause.
2. **Sentence-snap.** Same target size as fixed, but the actual cut is
   shifted to the nearest sentence boundary within a ±15 % window of
   the target. Costs a small amount of size variance for clean reads.
3. **Semantic chunking.** Embed candidate boundaries and cut where the
   embedding distance between adjacent sentences is largest — i.e. at
   topic shifts. Slower at ingest (extra embedding pass), but yields
   chunks that are coherent paragraphs. Worth it for prose; usually not
   for tabular or list-heavy content.

## What size to pick

Two countervailing pressures:

- **Smaller chunks** improve *precision*: the returned passage is
  tightly on-topic, the LLM has less noise to ignore, and the citation
  is exact. They hurt *recall*: a concept spanning two sentences may
  be split such that neither chunk alone contains the full claim.
- **Larger chunks** improve recall (more context per chunk, more chance
  the answer is in there) but hurt precision (more off-topic text
  in the context window, more tokens spent at generation time).

Empirically, 256-token chunks with ~32-token overlap maximise MRR for
short-answer factoid questions over technical documentation;
512-token chunks with ~64-token overlap are the sweet spot for
explanatory questions where the answer is a paragraph.

## Overlap matters more than people think

A common mistake is setting `chunk_overlap = 0` to save on storage.
That's the wrong trade: a query whose answer happens to sit at the
chunk boundary will retrieve neither side. The conventional 10–15 %
overlap of the chunk size is cheap insurance.

## Where chunking is structural, not parametric

PDFs with strong section structure (RFCs, contracts), code (where the
"chunk" should be a function or class, not a fixed token window) and
spreadsheets (where the "chunk" is a row or a logical block of cells)
all reward a structure-aware chunker over the same generic
token-window strategy used for prose. Build the parser to expose
structural hints, and let the chunker honour them.
