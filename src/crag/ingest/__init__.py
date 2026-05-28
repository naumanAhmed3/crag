"""Ingestion pipeline: parse → chunk → embed → upsert with manifest tracking."""

from crag.ingest.chunker import Chunk, chunk_text
from crag.ingest.manifest import Manifest
from crag.ingest.parsers import RawText, parse

__all__ = ["Chunk", "Manifest", "RawText", "chunk_text", "parse"]
