"""Stage 3 — Extract. Full-page fetch + boilerplate stripping via trafilatura.

Per-source failures (fetch timeout/block, empty extraction) degrade to the
SearXNG snippet for that source rather than failing the whole query.
"""

from __future__ import annotations

import asyncio

import trafilatura

from wisp.models import Source


def _extract_one(source: Source) -> Source:
    try:
        downloaded = trafilatura.fetch_url(source.url)
        result = trafilatura.bare_extraction(downloaded) if downloaded else None
        if result and result.text:
            source.content = result.text
            source.publish_date = result.date or source.publish_date
            return source
    except Exception:
        pass

    source.content = source.snippet
    source.extraction_failed = True
    return source


async def extract(sources: list[Source]) -> list[Source]:
    return await asyncio.gather(*(asyncio.to_thread(_extract_one, s) for s in sources))
