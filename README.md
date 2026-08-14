# Wisp — A Local Answer-Engine Layer on Top of SearXNG

**Status:** Design doc, not started. Standalone side project — separate from Mana, though Mana could become a consumer of it later.

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
      cutoff, not fixed threshold/count — margin itself TBD, calibrate
      empirically once real query data exists)
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
- Sort by this new score, then prune: keep everything within a relative margin of the top score (see Decision Record below — the exact margin is a tunable parameter, not fixed at design time)
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
3. Rerank+Prune (Stage 3.5) third — reuse Stage 1's embedding approach on the now-extracted full text; this is also where the pruning margin gets calibrated empirically, using real query data from steps 1-2
4. Synthesize last — the LLM/citation layer, since it depends on 1-3 already working well
5. Iterate on recency weighting and failure handling once the core pipeline works end-to-end

## Known open questions

Not yet resolved (the reranking design question was resolved separately — see Decision Record below):

- Failure handling is uneven across stages. Stage 3 has an explicit fallback (use the SearXNG snippet if a fetch fails). Stages 2 and 4 don't yet — worth defining before build: what happens if the embedding model fails or all snippets come back empty (Stage 2), and what happens if the LLM call fails or every extracted source is empty/unusable (Stage 4)? Reasonable default: degrade gracefully back toward raw SearXNG results rather than failing the whole query outright.
- How Stage 2's reranker actually gets served isn't decided. Left open intentionally at design stage — options include a small local process alongside the rest of the pipeline, or folding it into whatever app framework ends up hosting Stages 2-4. Needs a dependency decision (e.g. a sentence-embedding library) once implementation starts.

## Decision Record: Two-Pass Reranking (resolved 2026-08-15)

**Decision:** Reranking happens twice, not once — a cheap first pass on SearXNG snippets (Stage 2, unchanged), then a second pass after extraction (new: Stage 3.5) that re-scores using real page content, reorders, and prunes weak sources before they reach synthesis. Pruning uses a relative cutoff — sources within some margin of the top-scoring result survive — rather than a fixed score threshold or fixed count. The margin itself is deliberately left as a tunable parameter, to be calibrated empirically once Stage 2 is built and real query data shows how similarity scores actually distribute.

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
