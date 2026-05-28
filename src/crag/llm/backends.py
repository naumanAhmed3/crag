"""Local-LLM backend abstraction.

Two implementations are shipped:

- **OllamaBackend** — preferred when Ollama is installed (`ollama serve`
  running locally). Best ergonomics: model swap is `--llm-model` and
  Ollama handles the model download + quantisation file management.
- **LlamaCppBackend** — direct GGUF path via `llama-cpp-python`. Useful
  on air-gapped systems where Ollama isn't installed or allowed. The
  caller passes the path to a `.gguf` file as `Settings.llm_model`.

Selecting `Settings.llm_backend = "none"` returns a sentinel that lets
retrieval-only flows (gold-set Recall@K, MRR studies) run end-to-end
without a generation model installed.
"""

from __future__ import annotations

from typing import Protocol


class LLMBackend(Protocol):
    name: str

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 600,
        temperature: float = 0.2,
    ) -> str: ...


class _NullBackend:
    """No-op backend; raises if called. Used when llm_backend = 'none'."""

    name = "none"

    def chat(
        self, messages: list[dict[str, str]], *, max_tokens: int = 600, temperature: float = 0.2
    ) -> str:
        raise RuntimeError(
            "No LLM backend configured. Set CRAG_LLM_BACKEND to 'ollama' or 'llamacpp'."
        )


class OllamaBackend:
    name = "ollama"

    def __init__(self, model: str, context_window: int = 8192, host: str | None = None) -> None:
        self.model = model
        self.context_window = context_window
        self._host = host
        self._client = None

    def _client_lazy(self):
        if self._client is None:
            import ollama

            self._client = ollama.Client(host=self._host) if self._host else ollama.Client()
        return self._client

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 600,
        temperature: float = 0.2,
    ) -> str:
        resp = self._client_lazy().chat(
            model=self.model,
            messages=messages,
            options={
                "num_ctx": self.context_window,
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        )
        return resp["message"]["content"]


class LlamaCppBackend:
    name = "llamacpp"

    def __init__(self, gguf_path: str, context_window: int = 8192) -> None:
        self.gguf_path = gguf_path
        self.context_window = context_window
        self._llm = None

    def _llm_lazy(self):
        if self._llm is None:
            from llama_cpp import Llama

            self._llm = Llama(
                model_path=self.gguf_path,
                n_ctx=self.context_window,
                n_threads=None,  # let llama-cpp pick
                verbose=False,
            )
        return self._llm

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 600,
        temperature: float = 0.2,
    ) -> str:
        out = self._llm_lazy().create_chat_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return out["choices"][0]["message"]["content"]


def make_backend(backend: str, model: str, context_window: int = 8192) -> LLMBackend:
    """Pick a backend by name. Raises ImportError if the chosen backend's
    extras aren't installed; raises ValueError for an unknown backend.
    """
    if backend == "none":
        return _NullBackend()
    if backend == "ollama":
        try:
            import ollama  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "Ollama backend selected but the `ollama` package is missing. "
                "Install with `pip install crag[ollama]` and ensure `ollama serve` is running."
            ) from e
        return OllamaBackend(model=model, context_window=context_window)
    if backend == "llamacpp":
        try:
            import llama_cpp  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "llamacpp backend selected but the `llama-cpp-python` package is missing. "
                "Install with `pip install crag[llamacpp]`."
            ) from e
        return LlamaCppBackend(gguf_path=model, context_window=context_window)
    raise ValueError(f"Unknown LLM backend: {backend!r}")
