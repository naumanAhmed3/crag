# Ollama — what it does, what it doesn't

Ollama is a wrapper around llama.cpp that handles three annoying
things on your behalf: downloading and caching GGUF model files,
parsing chat templates so you can send raw `messages: [...]`, and
exposing a small HTTP API on `localhost:11434`. That's roughly the
entire product surface. It does not do fine-tuning, multi-GPU
sharding, or distributed serving.

## What "pulling a model" actually does

`ollama pull qwen2.5:7b-instruct-q4_K_M` does three things:

1. Resolves the tag against the Ollama registry to a manifest.
2. Downloads the GGUF blob (~4.4 GB for this tag) into
   `~/.ollama/models/blobs/`.
3. Writes a small JSON manifest associating the tag with the blob and
   the model's chat-template + system-prompt defaults.

Tags are content-addressed: the same model with different defaults
gets a different tag. You can publish your own tags from a `Modelfile`
that specifies a base model, a system prompt, parameters, and an
optional adapter (`FROM qwen2.5:7b ... PARAMETER temperature 0.1`).

## Memory and concurrency

Ollama keeps each loaded model resident until a few minutes of
inactivity, then evicts it. With 6 GB of VRAM you can keep one 7 B q4
model live; trying to keep two at once will swap and tank latency.
Concurrency is single-stream per loaded model — the server queues
requests. For parallel serving, run multiple Ollama instances on
different ports backed by separate model copies (memory permitting).

## Where Ollama is the wrong choice

- **Air-gapped boxes without a working DNS / HTTPS path to the Ollama
  registry**: you would need to side-load GGUFs anyway, at which point
  using `llama-cpp-python` directly cuts a layer.
- **Servers that need OpenAI-compatible structured outputs (JSON mode,
  function-calling).** Ollama supports `format: "json"` but lacks the
  tool-call schema fidelity of dedicated inference servers (vLLM, TGI,
  Llama.cpp's `/v1/chat/completions` endpoint).
- **Hot-path latency below ~100 ms p50**: Ollama's HTTP overhead is
  noticeable for tiny single-token requests. For RAG, where each call
  generates hundreds of tokens, the overhead is irrelevant.

## Practical configuration

Two environment variables worth knowing:

- `OLLAMA_NUM_PARALLEL` controls request concurrency on a single
  loaded model (default 1; raise to 2–4 if VRAM allows).
- `OLLAMA_KEEP_ALIVE` controls how long a model stays loaded after the
  last request (default 5 m). Set to `-1` or `24h` if your daemon
  serves a long-lived RAG process and you want zero cold-start.
