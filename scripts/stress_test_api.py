"""Dev tool: fire a batch of real queries at Wisp's live HTTP API
sequentially (llama-server is single-model/CPU, so concurrent requests
would just queue behind each other) and report latency, citation, and
failure-rate stats. Requires the API already running (`uv run wisp`).

Not part of the installed package -- run manually with
`uv run python scripts/stress_test_api.py`.
"""

from __future__ import annotations

import json
import re
import statistics
import time

import httpx

API_URL = "http://127.0.0.1:8899/query"

QUERIES = [
    "what caused the 2008 financial crisis",
    "how does the immune system fight infection",
    "explain the theory of relativity in simple terms",
    "what are the risks of artificial intelligence",
    "how did the printing press change society",
    "what is the difference between stocks and bonds",
    "how does the human brain form memories",
    "what caused the fall of the roman empire",
    "how do solar panels generate electricity",
    "what is the greenhouse effect",
    "how does the stock market crash of 1929 compare to 2008",
    "what are the main theories of dinosaur extinction",
    "how does dna replication work",
    "what is the current state of fusion energy research",
    "how did the cold war end",
    # Science & how things work
    "how does gravity bend light",
    "how do mrna vaccines differ from traditional vaccines",
    "how does cellular respiration produce energy",
    "how do coral reefs support marine biodiversity",
    "how does the ozone layer protect earth",
    "how do glaciers shape landscapes",
    "how does bioluminescence work in deep sea creatures",
    "how do plants communicate with each other",
    "how does the placebo effect influence clinical trials",
    "how do antibiotics become resistant over time",
    "how does the human microbiome affect digestion",
    "how does sleep affect long term memory",
    # History & consequences
    "how did the transatlantic slave trade shape modern economies",
    "how did the manhattan project change warfare",
    "how did the fall of the soviet union reshape eastern europe",
    "how did colonialism affect indigenous populations",
    "how did the great fire of london change city planning",
    "how did the treaty of versailles contribute to world war two",
    "how did the apollo program advance modern technology",
    "how did the bubonic plague change european society",
    "how did the transcontinental railroad transform the american west",
    "how did the suez canal change global trade routes",
    "how did the printing press contribute to the reformation",
    "how did the opium wars affect china's history",
    # Technology & AI
    "how do recommendation algorithms decide what to show you",
    "how does generative ai differ from traditional machine learning",
    "how do data centers manage cooling at scale",
    "how does biometric authentication work",
    "how do autonomous drones navigate without gps",
    "how does federated learning protect user privacy",
    "how do chatbots handle multiple languages",
    "how does open source software development typically work",
    "how do content delivery networks speed up websites",
    "how does digital rights management protect media",
    "how do smart home devices communicate with each other",
    "how does augmented reality overlay digital content",
    # Health & medicine
    "how do doctors diagnose autoimmune diseases",
    "how does gene therapy treat genetic disorders",
    "how does the body regulate blood sugar levels",
    "how do organ transplants avoid rejection",
    "how does exercise affect mental health",
    "how do vaccines achieve herd immunity",
    "how does chronic stress affect the body long term",
    "how do doctors treat antibiotic resistant infections",
    "how does the gut brain connection work",
    "how do pain medications work in the body",
    "how does aging affect the cardiovascular system",
    "how do allergies develop in the immune system",
    # Finance & economics
    "how do central banks fight inflation without causing a recession",
    "how does quantitative easing affect the economy",
    "how do stock buybacks affect shareholder value",
    "how does the housing market affect the broader economy",
    "how do tariffs affect consumer prices",
    "how does venture capital funding actually work",
    "how do hedge funds generate returns",
    "how does currency exchange rate fluctuation affect trade",
    "how do credit default swaps work",
    "how does student loan debt affect the economy",
    # Environment & climate
    "how does melting arctic ice affect global weather patterns",
    "how do carbon capture technologies work",
    "how does ocean acidification threaten marine life",
    "how do rising sea levels threaten coastal cities",
    "how does deforestation contribute to climate change",
    "how do renewable energy subsidies affect adoption rates",
    "how does plastic pollution affect ocean ecosystems",
    "how do climate models predict future warming",
    "how does urban sprawl affect local ecosystems",
    "how do international climate agreements get enforced",
    # Business & work
    "how do companies decide on remote work policies",
    "how does automation affect job markets",
    "how do startups typically scale their operations",
    "how does the gig economy affect worker benefits",
    "how do mergers and acquisitions typically work",
    "how does supply chain disruption affect global trade",
    "how do companies measure employee productivity",
    "how does workplace burnout affect performance",
    # Psychology & society
    "how does social media algorithm design affect polarization",
    "how does peer pressure influence teenage decision making",
    "how does confirmation bias affect political beliefs",
    "how does groupthink affect organizational decisions",
    "how does trauma affect long term mental health",
    "how does cognitive dissonance influence behavior",
    "how does loneliness affect physical health",
    "how does parenting style affect child development",
    "how does culture shape moral values",
    "how does propaganda influence public opinion",
    # Space & physics
    "how do black holes affect spacetime",
    "how does the international space station stay in orbit",
    "how do astronomers detect exoplanets",
    "how does time dilation work near the speed of light",
    "how do space telescopes capture images of distant galaxies",
    "how does zero gravity affect the human body",
    "how do scientists study dark energy",
    "how does the sun generate energy through fusion",
    # Law & policy
    "how does antitrust law regulate big tech companies",
    "how do international courts handle war crimes cases",
    "how does copyright law apply to ai generated content",
    "how do privacy laws differ between the us and eu",
    "how does immigration policy affect labor markets",
    "how do patent laws protect inventors",
    "how does campaign finance law regulate elections",
    "how do trade agreements affect domestic industries",
    # Culture & entertainment
    "how did streaming services change how people watch tv",
    "how does the music industry make money in the streaming era",
    "how do video game developers balance monetization and player experience",
    "how does social media influence fashion trends",
    "how do film studios decide which movies to greenlight",
    "how does fan culture shape modern entertainment franchises",
    "how did podcasts become a mainstream media format",
    "how does algorithmic curation shape what music people discover",
    # Everyday practical
    "how do airlines decide flight ticket prices dynamically",
    "how does dynamic pricing work for ride sharing apps",
    "how do grocery stores decide product placement",
    "how does search engine optimization affect website rankings",
    "how do subscription services encourage customer retention",
    "how does personal credit card interest actually accumulate",
    "how do loyalty programs affect consumer spending habits",
    # Food & agriculture
    "how does industrial farming affect soil health",
    "how do food deserts affect community nutrition",
    "how does the global coffee supply chain work",
    "how do fisheries manage sustainable seafood populations",
    "how does food labeling regulation protect consumers",
    "how do plant based meat alternatives get developed",
    "how does climate change affect crop yields",
    "how do restaurants manage food waste",
    "how does the wine industry classify quality",
    # Education & learning
    "how do standardized tests affect college admissions",
    "how does student debt affect career choices after graduation",
    "how do online learning platforms personalize education",
    "how does early childhood education affect long term outcomes",
    "how do universities decide tuition pricing",
    "how does vocational training compare to traditional college",
    "how do learning disabilities get diagnosed and supported",
    "how does homeschooling regulation vary by state",
    "how do libraries adapt to the digital age",
]

CITATION_RE = re.compile(r"\[\d+\]")


def run_one(client: httpx.Client, query: str) -> dict:
    start = time.monotonic()
    try:
        # Above the local backend's own 300s timeout (see llm/local.py) so
        # this doesn't cut a request off before the backend would itself.
        resp = client.post(API_URL, json={"query": query}, timeout=320.0)
        elapsed = time.monotonic() - start
        resp.raise_for_status()
        data = resp.json()
        return {
            "query": query,
            "status": resp.status_code,
            "elapsed_s": round(elapsed, 1),
            "synthesis_unavailable": data.get("synthesis_unavailable"),
            "reason": data.get("reason"),
            "answer_len": len(data.get("answer") or ""),
            "num_sources": len(data.get("sources") or []),
            "num_citations": len(CITATION_RE.findall(data.get("answer") or "")),
        }
    except Exception as exc:
        return {
            "query": query,
            "elapsed_s": round(time.monotonic() - start, 1),
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> None:
    results = []
    with httpx.Client() as client:
        for i, q in enumerate(QUERIES, start=1):
            print(f"[{i}/{len(QUERIES)}] {q}")
            r = run_one(client, q)
            results.append(r)
            print(f"  -> {json.dumps(r)}")

            # Paced -- each query also fires a SearXNG retrieve underneath,
            # and a 2s gap still tripped Brave/Google CSE's ~1hr suspension
            # and Startpage's ~24hr CAPTCHA suspension during the 300-query
            # calibration run. 8s is far more conservative; synthesis itself
            # already dominates wall time here anyway.
            if i < len(QUERIES):
                time.sleep(8.0)

            if i % 10 == 0:
                with open("scripts/stress_test_results.json", "w") as f:
                    json.dump(results, f, indent=2)

    with open("scripts/stress_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

    ok = [r for r in results if "error" not in r]
    errors = [r for r in results if "error" in r]
    unavailable = [r for r in ok if r["synthesis_unavailable"]]
    times = [r["elapsed_s"] for r in ok]

    print("\n--- summary ---")
    print(f"total: {len(results)}, ok: {len(ok)}, errors: {len(errors)}, synthesis_unavailable: {len(unavailable)}")
    if times:
        print(f"latency (s): min={min(times)} max={max(times)} mean={round(statistics.mean(times), 1)} median={statistics.median(times)}")
    if ok:
        sources = [r["num_sources"] for r in ok]
        citations = [r["num_citations"] for r in ok]
        print(f"sources per query: min={min(sources)} max={max(sources)} mean={round(statistics.mean(sources), 1)}")
        print(f"citations per answer: min={min(citations)} max={max(citations)} mean={round(statistics.mean(citations), 1)}")
    if errors:
        print("errors:")
        for r in errors:
            print(f"  {r['query']}: {r['error']}")


if __name__ == "__main__":
    main()
