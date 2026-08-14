"""Shared data shapes passed between pipeline stages."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Source:
    title: str
    url: str
    snippet: str
    score: float = 0.0
    content: str | None = None
    publish_date: str | None = None
    extraction_failed: bool = False


@dataclass
class QueryResult:
    query: str
    answer: str | None
    sources: list[Source]
    synthesis_unavailable: bool = False
    reason: str | None = None
