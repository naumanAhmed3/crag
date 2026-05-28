# Grounding and refusal — making "I don't know" a first-class answer

The defining behaviour an enterprise RAG must guarantee is: it never
fabricates. If the retrieved passages don't support an answer, the
system says so, plainly, and stops. Every other property — accuracy,
trust, auditability — is downstream of this one.

## Why refusal is hard

The base language model wants to be helpful. Its training is full of
examples where a question is followed by an answer; it has very few
examples where a question is followed by "I don't have enough
information." Without active intervention, even an honestly retrieved
context will be supplemented from parametric memory, and the citations
will look right but the claims will be partly invented.

## The intervention is the system prompt

The two non-negotiable rules in the prompt:

1. "Use only information from the PASSAGES." Stated absolutely, not as
   a preference.
2. "If the PASSAGES do not contain enough information to answer, reply
   exactly: 'I don't have enough information in the indexed corpus
   to answer this.'" The verbatim refusal string makes the refusal
   *machine-detectable* — auditors can grep, dashboards can count.

Adding "do not draw on outside knowledge, even if you know the
answer" is redundant on paper but reduces hallucination on weaker
models by another 10–20 % in measured tests.

## The citation contract

Every factual claim must cite the passage(s) supporting it as `[N]`.
Two reasons:

- It is verifiable: a user (or a compliance reviewer) can click into
  the citation and read the source.
- It is a forcing function for the model: writing `[N]` is harder when
  there is no N to write, so the model is more likely to refuse rather
  than half-cite.

## Measuring it — faithfulness

The metric you track is *faithfulness*: the fraction of generated
answers where every claim is supported by the cited passages. The
cheapest measurement is LLM-as-judge — a second pass with a small
local model that returns `{faithful: true|false, unsupported_claims:
[...]}`. Faithfulness should be the *first* number on the dashboard,
ahead of latency, throughput, and cost.

A faithful answer can still be wrong (the corpus may be outdated or
incomplete). But an unfaithful answer is *guaranteed* to be wrong in
the eyes of an auditor, regardless of whether it happens to be
factually accurate. RAG buys you "always citable"; faithfulness is
how you keep that promise.
