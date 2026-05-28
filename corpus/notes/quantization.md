# Quantisation — how a 14 GB model fits in 4 GB of VRAM

Quantisation is the process of representing a model's weights with
fewer bits per parameter. Full-precision (FP32) weights take four
bytes each; a 7-billion-parameter model is therefore 28 GB on disk
and in memory. Standard half-precision (FP16) halves that to 14 GB.
Four-bit quantisation (the `q4_*` family in GGUF) brings it down to
roughly 4 GB — small enough to fit on a 6 GB consumer GPU with room
left for the KV cache.

## What the suffixes mean (GGUF naming)

GGUF — the format used by `llama.cpp` and Ollama — uses a naming
scheme like `q4_K_M`. Reading right-to-left:

- The last letter (`S`, `M`, `L`) is a *size* qualifier within the
  same nominal bit-width. `M` is the safe default for most users.
- The middle letter is the *type*. `K` (k-quants) is the modern
  successor to legacy `0`/`1` schemes and gives noticeably better
  quality at the same bit budget.
- The number is the *nominal bit-width*. `q4_K_M` is ≈ 4.85 bits per
  weight in practice — slightly above the literal 4 because some
  weights (the most numerically sensitive layers) are kept at higher
  precision.

For most workloads the right choice is `q4_K_M`. `q5_K_M` is the
quality-comfortable upgrade if you have the VRAM. `q3_K_S` exists for
the truly memory-constrained but begins to degrade reasoning quality
noticeably.

## What you lose

Two effects matter in practice:

1. **Perplexity drift.** Measured on standard benchmarks, q4_K_M
   typically costs 0.5–1.5 % perplexity vs FP16 for 7B-class models.
   For RAG, which constrains the model to a small context, this is
   nearly invisible.
2. **Instruction-following degradation.** Smaller and more aggressive
   quants sometimes lose the ability to follow complex multi-step
   instructions. The fix is usually a higher-quality model at the
   same VRAM budget rather than a less-aggressive quant of the same
   model: `qwen2.5:7b-q4_K_M` beats `llama-3.1:8b-q3_K_S` on most
   instruction tasks while using similar VRAM.

## VRAM accounting

A 7 B parameter model at q4_K_M is approximately 4.4 GB. To that, add:

- **KV cache**: ~0.4 GB per 1 K context tokens at FP16. An 8 K context
  window allocates ~3.2 GB at full load — usually the surprising
  number that makes deployments OOM after the first long query.
- **Activation overhead**: ~200 MB.

On 6 GB VRAM, run a 7 B q4_K_M with an 8 K context only if the OS
isn't fighting you for the rest. In practice it works on a fresh
nvidia-smi readout under 200 MB; allocate 4 K or 6 K otherwise.
