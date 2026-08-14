"""Dev tool: run retrieve + rerank + extract + rerank(3.5) for a spread of
real queries and print the resulting score distributions, so WISP_PRUNE_MARGIN
can be re-calibrated from real data as usage patterns change. Not part of the
installed package -- run manually with `uv run python scripts/calibrate_margin.py`.
"""

from __future__ import annotations

import asyncio
import json

from wisp.config import settings
from wisp.extract import extract
from wisp.rerank import rerank
from wisp.retrieve import retrieve

QUERIES = [
    "what is retrieval augmented generation",
    "best budget graphics card 2026",
    "how does photosynthesis work",
    "latest news on the artemis moon program",
    "python asyncio vs threading",
    "symptoms of vitamin d deficiency",
    "who won the last world cup",
    "how to negotiate a salary raise",
    "difference between tcp and udp",
    "climate change effects on coral reefs",
]


async def run_one(query: str) -> dict:
    results = await retrieve(query, settings.searxng_url)
    results = rerank(query, results, settings.embedding_model, text_of=lambda s: s.snippet)
    candidates = results[: settings.extract_top_n]

    extracted = await extract(candidates)
    extracted = rerank(query, extracted, settings.embedding_model, text_of=lambda s: s.content or s.snippet)

    scores = [round(s.score, 4) for s in extracted]
    top = scores[0] if scores else None
    deltas = [round(top - s, 4) for s in scores] if top is not None else []
    return {"query": query, "scores": scores, "deltas_from_top": deltas}


async def main() -> None:
    out = []
    for q in QUERIES:
        try:
            r = await run_one(q)
        except Exception as exc:
            r = {"query": q, "error": str(exc)}
        out.append(r)
        print(json.dumps(r))

    with open("scripts/calibration_results.json", "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
