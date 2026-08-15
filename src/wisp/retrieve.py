"""Stage 1 — Retrieve. Thin client for the existing, unmodified SearXNG instance."""

from __future__ import annotations

import httpx

from wisp.models import Source


async def retrieve(query: str, searxng_url: str, engines: str | None = None) -> list[Source]:
    params = {"q": query, "format": "json"}
    if engines:
        # Comma-separated SearXNG engine names (e.g. "google,stackoverflow"),
        # explicitly overriding the default general-category engine set for
        # this one request. Not for routine use -- SearXNG's default set is
        # the normal path; this is an escape hatch for when it's degraded
        # (rate-limited/suspended) or a specific engine is known to fit the
        # query better (e.g. stackoverflow for a programming question).
        params["engines"] = engines

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{searxng_url}/search", params=params)
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
