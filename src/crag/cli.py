"""crag CLI.

Five commands cover the entire surface:

    crag ingest <path...>    parse/chunk/embed/store; incremental by default
    crag ask "<question>"    retrieve + generate a grounded answer
    crag stats               manifest + vector-store stats
    crag eval [--gold path]  run the gold set; print retrieval metrics
    crag version             show package version
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
from rich import box
from rich.console import Console
from rich.table import Table

from crag import __version__
from crag.config import settings as load_settings
from crag.ingest.manifest import Manifest
from crag.ingest.pipeline import ingest as run_ingest
from crag.retrieval.bm25 import BM25Index
from crag.retrieval.embed import Embedder
from crag.retrieval.rerank import CrossEncoderReranker
from crag.retrieval.search import HybridRetriever
from crag.retrieval.store import VectorStore

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="crag — offline RAG over a local corpus.",
)
console = Console()


# ── shared helpers ──────────────────────────────────────────────────────


def _open_stack(*, need_reranker: bool = False, need_bm25: bool = False):
    """Build the runtime stack from current Settings. Returns a tuple
    (settings, embedder, store, manifest, bm25_or_None, reranker_or_None).
    """
    s = load_settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    embedder = Embedder(s.embedding_model)
    store = VectorStore(s.data_dir, collection="default", dim=embedder.dim)
    manifest = Manifest(s.data_dir / "manifest.sqlite")
    bm25 = BM25Index(store.all_payloads()) if need_bm25 else None
    reranker = (
        CrossEncoderReranker(s.reranker_model) if (need_reranker and s.reranker_enabled) else None
    )
    return s, embedder, store, manifest, bm25, reranker


# ── commands ────────────────────────────────────────────────────────────


@app.command()
def ingest(
    paths: list[Path] = typer.Argument(..., exists=True, help="Files or directories to ingest."),
    json_out: bool = typer.Option(False, "--json", help="Emit raw stats as JSON."),
) -> None:
    """Ingest one or more paths incrementally."""
    s, embedder, store, manifest, _bm25, _rerank = _open_stack()
    with manifest:
        stats = run_ingest(
            paths=paths,
            settings=s,
            embedder=embedder,
            store=store,
            manifest=manifest,
        )

    if json_out:
        print(json.dumps(stats.asdict(), indent=2))
        return

    t = Table(title="Ingest stats", box=box.SIMPLE, show_header=False)
    t.add_column(style="dim")
    t.add_column(justify="right")
    d = stats.asdict()
    for k in (
        "files_seen",
        "files_added",
        "files_updated",
        "files_skipped_unchanged",
        "files_skipped_unsupported",
        "files_removed",
        "chunks_added",
        "chunks_removed",
        "embed_seconds",
        "total_seconds",
    ):
        t.add_row(k.replace("_", " "), f"{d[k]:,}" if isinstance(d[k], int) else str(d[k]))
    console.print(t)
    if d["errors"]:
        console.print(f"[red]{len(d['errors'])} error(s)[/red]")
        for p, msg in d["errors"][:10]:
            console.print(f"  • {p}: {msg}")


@app.command()
def ask(
    question: str = typer.Argument(..., help="The question to ask."),
    top_k: int | None = typer.Option(None, "--top-k", help="Override final_top_k."),
    show_passages: bool = typer.Option(True, "--passages/--no-passages"),
) -> None:
    """Retrieve and generate a grounded answer."""
    from crag.answer.pipeline import answer_question
    from crag.llm.backends import make_backend

    s, embedder, store, _manifest, bm25, rerank = _open_stack(need_reranker=True, need_bm25=True)
    if top_k is not None:
        s.final_top_k = top_k
        s.rerank_top_k = max(s.rerank_top_k, top_k)

    if store.count() == 0:
        console.print("[yellow]The index is empty. Run `crag ingest <path>` first.[/yellow]")
        sys.exit(1)

    retriever = HybridRetriever(s, embedder, store, bm25, rerank)
    backend = make_backend(s.llm_backend, s.llm_model, context_window=s.llm_context_window)
    answer = answer_question(
        question, retriever, backend, max_tokens=s.llm_max_tokens, temperature=s.llm_temperature
    )

    console.rule("Answer")
    console.print(answer.text)
    console.print()
    console.print(
        f"[dim]retrieval {answer.retrieval_ms:.0f} ms · generation {answer.generation_ms:.0f} ms "
        f"· total {answer.total_ms:.0f} ms · model {s.llm_model}[/dim]"
    )

    if show_passages:
        console.rule("Passages")
        for i, c in enumerate(answer.chunks, start=1):
            loc = f" — {c.locator}" if c.locator and c.locator != "document" else ""
            console.print(f"[bold cyan][{i}][/bold cyan] {c.file_path}{loc}")
            preview = c.text.strip().replace("\n", " ")
            console.print(f"  {preview[:240]}{'…' if len(preview) > 240 else ''}")


@app.command()
def stats() -> None:
    """Print manifest + vector-store stats."""
    s, _embedder, store, manifest, _bm25, _rerank = _open_stack()
    with manifest:
        m = manifest.stats()
    t = Table(title="crag", box=box.SIMPLE, show_header=False)
    t.add_column(style="dim")
    t.add_column(justify="right")
    t.add_row("data dir", str(s.data_dir.resolve()))
    t.add_row("collection points", f"{store.count():,}")
    t.add_row("manifest files", f"{m['files']:,}")
    t.add_row("manifest chunks", f"{m['chunks']:,}")
    t.add_row("total tokens", f"{m['tokens']:,}")
    t.add_row("embedding model", s.embedding_model)
    t.add_row("reranker", s.reranker_model if s.reranker_enabled else "(disabled)")
    t.add_row("llm backend", s.llm_backend)
    t.add_row("llm model", s.llm_model)
    console.print(t)


@app.command(name="eval")
def evaluate(
    gold: Path = typer.Option(
        Path("src/crag/eval/gold.yaml"), "--gold", exists=True, help="Gold-set YAML."
    ),
    top_k: int = typer.Option(5, "--top-k"),
    json_out: bool = typer.Option(False, "--json"),
) -> None:
    """Evaluate retrieval on a gold set."""
    from crag.eval.metrics import evaluate_retrieval, load_gold

    s, embedder, store, _manifest, bm25, rerank = _open_stack(need_reranker=True, need_bm25=True)
    if store.count() == 0:
        console.print("[yellow]The index is empty. Run `crag ingest <path>` first.[/yellow]")
        sys.exit(1)
    items = load_gold(gold)
    retriever = HybridRetriever(s, embedder, store, bm25, rerank)
    metrics = evaluate_retrieval(items, retriever.search, top_k=top_k)

    if json_out:
        print(json.dumps(metrics.asdict(), indent=2))
        return

    t = Table(title=f"Retrieval @ top-{top_k} · n={metrics.n_questions}", box=box.SIMPLE)
    t.add_column("metric", style="dim")
    t.add_column("value", justify="right")
    t.add_row("Recall@K", f"{metrics.recall_at_k:.3f}")
    t.add_row("Precision@K", f"{metrics.precision_at_k:.3f}")
    t.add_row("MRR", f"{metrics.mrr:.3f}")
    if metrics.substring_recall is not None:
        t.add_row("Substring recall", f"{metrics.substring_recall:.3f}")
    console.print(t)


@app.command()
def version() -> None:
    """Print the version."""
    console.print(__version__)


if __name__ == "__main__":  # pragma: no cover
    app()
