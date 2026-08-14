"""Rerank + prune, shared by Stage 2 (snippets) and Stage 3.5 (real content).

Failure handling (decided in the grilling session): if the embedding model
fails to load, or every candidate text is empty, reranking is skipped and
the original SearXNG order is passed through untouched. Reranking is a
quality enhancement over raw SearXNG, not a correctness requirement, so a
query must never hard-fail just because this stage couldn't run.
"""

from __future__ import annotations

from functools import lru_cache

from wisp.models import Source


@lru_cache(maxsize=1)
def _get_embedder(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def rerank(query: str, sources: list[Source], model_name: str, text_of=lambda s: s.snippet) -> list[Source]:
    texts = [text_of(s) for s in sources]
    if not any(t.strip() for t in texts):
        return sources

    try:
        embedder = _get_embedder(model_name)
        query_vec = embedder.encode(query, normalize_embeddings=True)
        text_vecs = embedder.encode(texts, normalize_embeddings=True)
        scores = text_vecs @ query_vec
    except Exception:
        return sources

    for source, score in zip(sources, scores):
        source.score = float(score)

    return sorted(sources, key=lambda s: s.score, reverse=True)


def prune(sources: list[Source], margin: float) -> list[Source]:
    if not sources:
        return sources
    top_score = sources[0].score
    return [s for s in sources if s.score >= top_score - margin]
