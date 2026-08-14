from wisp.models import Source
from wisp.rerank import prune, rerank


def _source(url: str, snippet: str) -> Source:
    return Source(title=url, url=url, snippet=snippet)


def test_rerank_passes_through_when_all_texts_empty():
    sources = [_source("a", ""), _source("b", "")]
    result = rerank("query", sources, "sentence-transformers/all-MiniLM-L6-v2")
    assert result == sources


def test_prune_keeps_only_sources_within_margin_of_top_score():
    sources = [_source("a", "x"), _source("b", "y"), _source("c", "z")]
    sources[0].score = 0.90
    sources[1].score = 0.87
    sources[2].score = 0.50

    result = prune(sources, margin=0.05)

    assert [s.url for s in result] == ["a", "b"]


def test_prune_empty_list_returns_empty_list():
    assert prune([], margin=0.05) == []
