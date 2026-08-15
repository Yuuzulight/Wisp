"""Wires the four stages together: retrieve -> rerank -> extract -> rerank+prune -> synthesize."""

from __future__ import annotations

from wisp.config import Settings
from wisp.extract import extract
from wisp.llm import get_backend
from wisp.models import QueryResult
from wisp.rerank import prune, rerank
from wisp.retrieve import retrieve
from wisp.synthesize import synthesize


async def run_query(query: str, backend_name: str, settings: Settings, engines: str | None = None) -> QueryResult:
    results = await retrieve(query, settings.searxng_url, engines=engines)

    results = rerank(query, results, settings.embedding_model, text_of=lambda s: s.snippet)
    candidates = results[: settings.extract_top_n]

    extracted = await extract(candidates)

    extracted = rerank(query, extracted, settings.embedding_model, text_of=lambda s: s.content or s.snippet)
    pruned = prune(extracted, settings.prune_margin)

    backend = get_backend(backend_name, settings)
    return await synthesize(query, pruned, backend)
