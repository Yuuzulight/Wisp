"""Stage 1 — Retrieve. Thin client for the existing, unmodified SearXNG instance."""

from __future__ import annotations

import httpx

from wisp.models import Source


async def retrieve(query: str, searxng_url: str) -> list[Source]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{searxng_url}/search",
            params={"q": query, "format": "json"},
        )
        resp.raise_for_status()
        data = resp.json()

    return [
        Source(
            title=r.get("title", ""),
            url=r.get("url", ""),
            snippet=r.get("content", ""),
            publish_date=r.get("publishedDate"),
        )
        for r in data.get("results", [])
    ]
