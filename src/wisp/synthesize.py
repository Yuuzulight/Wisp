"""Stage 4 — Synthesize. Prompts the selected LLM backend for a cited answer.

Failure handling (decided in the grilling session): if the LLM call fails,
or there are no usable sources to synthesize from, return the ranked
sources with no prose and `synthesis_unavailable=True` rather than
failing the whole request.
"""

from __future__ import annotations

from wisp.llm import LLMBackend
from wisp.models import QueryResult, Source

SYSTEM_PROMPT = (
    "You are an answer-engine synthesizer. Using only the numbered sources "
    "provided, write a concise, accurate answer to the user's query. Cite "
    "every claim inline with the matching source number in square brackets, "
    "e.g. [1], [2]. Do not cite a source you did not use. If the sources do "
    "not contain enough information to answer, say so plainly."
)


def _build_prompt(query: str, sources: list[Source]) -> str:
    numbered = "\n\n".join(
        f"[{i}] {s.title}\n{s.url}\n{(s.content or s.snippet).strip()[:2000]}"
        for i, s in enumerate(sources, start=1)
    )
    return f"Query: {query}\n\nSources:\n\n{numbered}\n\nAnswer, with inline [n] citations:"


async def synthesize(query: str, sources: list[Source], backend: LLMBackend) -> QueryResult:
    usable = [s for s in sources if (s.content or s.snippet).strip()]
    if not usable:
        return QueryResult(
            query=query,
            answer=None,
            sources=sources,
            synthesis_unavailable=True,
            reason="No usable source content survived extraction/pruning.",
        )

    try:
        answer = await backend.chat(SYSTEM_PROMPT, _build_prompt(query, usable))
    except Exception as exc:
        return QueryResult(
            query=query,
            answer=None,
            sources=sources,
            synthesis_unavailable=True,
            reason=f"LLM call failed: {exc}",
        )

    return QueryResult(query=query, answer=answer, sources=sources)
