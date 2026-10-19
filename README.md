# Wisp — A Local Answer-Engine Layer on Top of SearXNG

**Status:** Core pipeline scaffolded in Python and verified working end-to-end against a live SearXNG instance and a local LLM — retrieve, rerank, extract, rerank+prune, synthesize all run and return a cited answer. Not yet hardened (no real query-load testing). The pruning margin was calibrated on 2026-08-15 against 10 real queries and set to 0.45 (see the Decision Record below). Standalone side project — separate from Mana, though Mana could become a consumer of it later.

**Name notes:** Wisp — chosen to reflect the core architecture decision: nothing is cached or persisted between queries. Every answer is gathered fresh and dissipates once served, like a wisp — no index, no standing crawl, no memory between requests.

**One-line pitch:** SearXNG already does multi-engine metasearch with zero index/crawler overhead. This project adds the layer Perplexity/ChatGPT Search/Claude web search have on top of retrieval — reranking, full-page extraction, and cited synthesis — without ever building or storing a web index.

## Why this project exists

Perplexity-class "answer engines" are built on a RAG (Retrieval-Augmented Generation) pattern: retrieve → rerank → extract → synthesize with citations. What makes them expensive to build is the retrieval half — they run their own crawler (PerplexityBot, OAI-SearchBot) and maintain a standing index of a meaningful slice of the web. That's genuinely a different category of project (server fleets, storage, crawl-rate/robots.txt/legal considerations at scale) — not something worth attempting solo.

The insight this project is built on: the other half of the RAG pattern — rerank, extract, synthesize, cite — doesn't need an index at all. SearXNG already solves retrieval (it aggregates existing search engines' live results, no crawler needed). This project is specifically the missing layer between "SearXNG gives you 10 links" and "here's a synthesized, cited answer."

## Explicit non-goals

- Not building a crawler. No PerplexityBot-equivalent, ever. Retrieval stays 100% delegated to SearXNG (which itself delegates to Google/Bing/DuckDuckGo/etc.).
- Not building an index. No caching of web content between queries. Every query is fully live: fetch, extract, rerank, synthesize, discard.
- Not trying to beat Perplexity on speed. Live-only retrieval will always be slower than a system with a warm cache/index. Accepting that tradeoff explicitly in exchange for zero infrastructure cost.
- Not a general search engine. This is a personal/small-scale tool, not a product aimed at competing with any of the big players.

## Architecture — 4 stages, all stateless/live, no persistence layer

```
User query
    ↓
[1] RETRIEVE — SearXNG (existing, unmodified)
    - Fan out to multiple engines in parallel via SearXNG's existing aggregation
    - Returns: list of (title, url, snippet) results
    ↓
[2] RERANK — new component, the first real addition
    - Small local embedding model scores query-vs-snippet semantic similarity
    - Re-orders SearXNG's raw results by actual relevance, not just source-interleaving
    - Optional: weight recency explicitly for time-sensitive queries (prefer pages
      with recent publish/modified dates)
    - Output: top N (e.g. 5-8) reranked candidate URLs
    ↓
[3] EXTRACT — new component
    - Fetch full page content for the top N candidates (parallel fetches)
    - Strip nav/ads/boilerplate, keep substantive article text
    - Comparable to what Jina AI Reader / Firecrawl do as a hosted service —
      this is the local, self-hosted equivalent of that single step
    - Output: clean text per source, with source URL retained for citation
    ↓
[3.5] RERANK + PRUNE (real content) — new component, see Decision Record below
    - Re-score the extracted sources using their actual full text, not the
      original thin snippet
    - Reorder by this new score
    - Prune: keep only sources within a margin of the top score (relative
      cutoff, not fixed threshold/count — margin 0.45, calibrated
      empirically on 2026-08-15; see the Decision Record)
    - Output: a pruned, reordered subset of sources — the ones that
      survive both the snippet pass AND the real-content pass
    ↓
[4] SYNTHESIZE — new component
    - Feed extracted, reranked content to an LLM
    - Prompt explicitly for inline numbered citations tied to which source
      backs which claim (Perplexity-style [1][2] inline markers)
    - Output: synthesized answer + citation list mapping numbers to URLs
```

Nothing is cached or stored between stages or between queries. Every request pays the full pipeline cost — this is the accepted tradeoff for having zero index/storage.

## Stage-by-stage build notes

### Stage 1 — Retrieve (SearXNG, no changes needed)

- Self-hosted SearXNG instance (already proven — this is literally what Mana already uses for `/web/search`)
- No modification needed at this stage; it's the existing, working foundation

### Stage 2 — Rerank

- What's needed: a small local embedding model (e.g. something in the all-MiniLM class — small, fast, CPU-friendly, same class of model mentioned for Soul of Waifu's episodic memory search in Mana's research)
- Score = semantic similarity between the query embedding and each snippet's embedding
- Sort SearXNG's results by this score instead of trusting default ordering
- Optional recency boost: parse/estimate publish date where available, weight into final score for queries that look time-sensitive
- This is the cheapest stage to build first — small, self-contained, testable independently of the rest

### Stage 3 — Extract

- Fetch top N reranked URLs (parallel HTTP requests)
- Content extraction: strip boilerplate (nav, ads, footers, cookie banners), keep the actual article/answer text
- Existing open-source tools worth evaluating rather than building from scratch: readability-style extraction libraries (the same class of tool behind "reader mode" in browsers) — no need to reinvent boilerplate-stripping
- Handle failures gracefully: some fetches will fail/timeout/block — degrade to using SearXNG's snippet for that source rather than failing the whole query
- This is the stage genuinely comparable to Jina AI Reader / Firecrawl — if a self-hosted version proves too fiddly, evaluate whether a self-hostable open-source equivalent already exists before building fully custom

### Stage 3.5 — Rerank + Prune (real content)

- Reuses the same embedding approach as Stage 2, just applied to extracted full text instead of snippets
- Score each surviving source's full text against the query, same as Stage 2's method
- Sort by this new score, then prune: keep everything within a relative margin of the top score (see Decision Record below — the margin is a tunable parameter, calibrated to 0.45 on 2026-08-15)
- This stage is what actually fixes the "reranking on thin signal" problem — it's the reason a genuinely weak source that slipped through Stage 2's snippet-based judgment gets caught before reaching synthesis

### Stage 4 — Synthesize

- LLM call (local model, or whichever model this project's host system has available — this is provider-agnostic, doesn't need to be tied to any specific model choice)
- System prompt requirement: inline numbered citations, explicit mapping between claims and sources — this is the single feature that makes output feel like an "answer engine" instead of a chatbot with search bolted on
- Output format: synthesized prose + a citation list (number → title + URL)

## What "better and more current" actually means here, concretely

- Better than raw SearXNG: reranked results (not just aggregated), full extracted page content (not just snippets), synthesized cited answer (not just a link list)
- Current by construction: since nothing is cached, every answer is exactly as fresh as whatever the underlying search engines' live indexes currently show — no staleness from an outdated local index, because there is no local index

## What it will never be

- Not faster than Perplexity/ChatGPT Search (no warm cache to serve from)
- Not able to answer about content the underlying search engines themselves don't surface well
- Not building proprietary ranking signals from historical crawl data (Perplexity's reranker benefits from their own crawl history; this project's reranker only ever sees what's live right now)

## Suggested build order

1. Rerank stage first, standalone — wire it directly onto existing SearXNG output, measure whether reordering actually improves result quality before building anything else
2. Extract stage second — add full-page fetch/extraction on top of the reranked top-N, still no synthesis yet; verify extraction quality across a variety of real sites
3. Rerank+Prune (Stage 3.5) third — reuse Stage 1's embedding approach on the now-extracted full text; this is also where the pruning margin was calibrated empirically, using real query data from steps 1-2 (done 2026-08-15)
4. Synthesize last — the LLM/citation layer, since it depends on 1-3 already working well
5. Iterate on recency weighting and failure handling once the core pipeline works end-to-end

## Known open questions

All resolved as of the first implementation pass (2026-08-15):

- Failure handling is now consistent across every stage that can fail. Stage 2 (embedding model fails, or every snippet is empty) skips reranking and passes SearXNG's original order through. Stage 3 falls back to the SearXNG snippet on a failed fetch, per source. Stage 4 (LLM call fails, or nothing usable survived pruning) returns the ranked source list with no synthesized prose rather than erroring the request. None of these degrade to a hard failure.
- Stage 2's reranker is served in-process, as a plain Python module imported by the FastAPI app that hosts the whole pipeline — not a separate service. See Implementation below.

## Decision Record: Two-Pass Reranking (resolved 2026-08-15)

**Decision:** Reranking happens twice, not once — a cheap first pass on SearXNG snippets (Stage 2, unchanged), then a second pass after extraction (new: Stage 3.5) that re-scores using real page content, reorders, and prunes weak sources before they reach synthesis. Pruning uses a relative cutoff — sources within some margin of the top-scoring result survive — rather than a fixed score threshold or fixed count.

**Margin calibration (2026-08-15):** Run against 10 real queries spanning factual, technical, current-events, and how-to phrasing (`scripts/calibrate_margin.py`), Stage 3.5 scores split into two clean clusters with no overlap: genuinely on-topic sources always land within 0.03-0.40 of the top score, while sources where extraction actually failed (near-zero or negative cosine similarity — garbage/boilerplate text, not a relevance judgment) land at 0.59+. The default margin is set to `0.45`, in the middle of that gap — tight enough to reliably drop extraction failures, loose enough to keep every source that's actually on-topic even when it's phrased very differently from the top result. Re-run the calibration script if real usage data ever shows this distribution shifting.

**Why:** Snippet-only reranking (the original single-pass design) has a real weakness — SearXNG snippets are often thin (a meta description, not real content), so a genuinely strong source could be misjudged and filtered out before its full content is ever seen in Stage 3's extraction. A second rerank pass on real extracted text corrects for this.

**Alternatives considered and rejected:**

- Single-pass, snippet-only reranking — simplest, but keeps the known weakness of judging sources on thin signal
- Extract everything before any ranking — would fully solve the thin-signal problem, but pays full-page-fetch cost for every raw SearXNG result instead of just the promising ones; rejected as unnecessarily expensive
- Reorder without pruning — keeps all original candidates, just resorts them; rejected because a weak source demoted to a lower position still reaches the LLM as context, and LLMs don't reliably discount low-quality context just because it's ranked lower
- Fixed score threshold for pruning — rejected as fragile, since embedding-similarity scores aren't well-calibrated in absolute terms across different queries; a cutoff tuned for one query could wrongly reject everything for another
- Fixed count for pruning (always keep top K) — rejected as arbitrary; some queries genuinely have only 1 strong source, others have 5, and a fixed K doesn't adapt to that
- Backfill after pruning (go back to SearXNG for a replacement if pruning drops below a minimum) — rejected for now as added complexity for what's likely a rare case; revisit only if empirical testing shows the pool frequently prunes down too far

**Revised architecture (Stage 3.5 inserted):**

```
[2] RERANK (snippets)  →  [3] EXTRACT (top N)  →  [3.5] RERANK+PRUNE (real content)  →  [4] SYNTHESIZE
```

## Relationship to Mana

Not a dependency in either direction right now. Mana already uses SearXNG directly via `/web/search` and `/web/read`. If/when this project is built out, Mana could become a consumer — pointing its web-access endpoints at this pipeline instead of (or in addition to) raw SearXNG — but that's a future integration decision, not a requirement of building this.

## Implementation

- **Stack:** Python, [uv](https://github.com/astral-sh/uv) for dependency management, FastAPI for the HTTP surface.
- **Rerank (Stages 2 & 3.5):** `sentence-transformers/all-MiniLM-L6-v2`. Pruning keeps sources within an absolute cosine-similarity delta of the top score (default `0.45`, calibrated against real queries — see the Decision Record below), not a percentage — score ranges shift too much between queries for a percentage cutoff to behave consistently.
- **Extract (Stage 3):** [`trafilatura`](https://github.com/adbar/trafilatura). Falls back to the SearXNG snippet whenever a fetch fails or returns nothing usable.
- **Synthesize (Stage 4):** pluggable backend, picked per request — a local `llama-server` instance by default (no ongoing cost), or the Claude API as an opt-in alternative. Falls back to returning the ranked, un-synthesized source list if the LLM call fails or nothing survived pruning, rather than erroring the whole request.
- **API:** a single `POST /query` endpoint (`{query, backend, engines}`), bound to `127.0.0.1` only — this is a single-user local tool, not a public service. `engines` is an optional escape hatch (comma-separated SearXNG engine names, e.g. `"google"`) that overrides Stage 1's default engine set for that one request — for when the defaults are degraded/rate-limited, or a specific engine fits the query better (e.g. `stackoverflow` for a programming question). Leave it unset for normal operation; SearXNG's own default aggregation is the intended path, not this override.

### Running it

```
uv sync
cp .env.example .env   # fill in SEARXNG_URL / LLAMA_SERVER_URL / ANTHROPIC_API_KEY as needed
uv run wisp             # starts the API on http://127.0.0.1:8899
```

Needs a reachable SearXNG instance (JSON output format enabled) and, for the default `local` backend, an OpenAI-compatible `llama-server` running locally.
