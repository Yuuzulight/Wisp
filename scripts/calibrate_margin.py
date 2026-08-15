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
    "how do vaccines work",
    "best programming language to learn in 2026",
    "causes of world war one",
    "how to make sourdough bread",
    "electric vehicle battery degradation",
    "what is quantum computing",
    "signs of a heart attack",
    "how to invest in index funds",
    "renewable energy vs fossil fuels",
    "history of the roman empire",
    "how does a nuclear reactor work",
    "best hiking trails in the pacific northwest",
    "what is machine learning",
    "side effects of intermittent fasting",
    "how to write a resume",
    "causes of inflation",
    "what is the metaverse",
    "benefits of meditation",
    "how do black holes form",
    "tips for public speaking",
    "what is cryptocurrency mining",
    "causes of the french revolution",
    "how to start a small business",
    "difference between weather and climate",
    "symptoms of the flu vs covid",
    "how do airplanes fly",
    "best practices for password security",
    "what is the gig economy",
    "how to reduce screen time",
    "origins of jazz music",
    # Science & nature
    "how do tectonic plates move",
    "what causes the northern lights",
    "how does the human eye see color",
    "what is dark matter",
    "how do bees communicate",
    "what causes earthquakes",
    "how does the water cycle work",
    "what is the theory of evolution",
    "how do volcanoes erupt",
    "what causes ocean tides",
    # Space & astronomy
    "what is a neutron star",
    "how far is the nearest star to earth",
    "what is the james webb space telescope",
    "how do rockets escape earth's gravity",
    "what is the search for extraterrestrial intelligence",
    "how was the moon formed",
    "what is a supernova",
    "how many planets are in the solar system",
    "what is the big bang theory",
    "how do satellites stay in orbit",
    # Health & medicine
    "what is type 2 diabetes",
    "how does chemotherapy work",
    "what are the benefits of regular exercise",
    "how does anesthesia work",
    "what causes migraines",
    "how do antibiotics work",
    "what is the immune system",
    "signs of anxiety disorder",
    "how does the digestive system work",
    "what is a stroke",
    # Nutrition & fitness
    "benefits of a mediterranean diet",
    "how much protein do you need per day",
    "what is high intensity interval training",
    "benefits of strength training",
    "how to build a sustainable workout routine",
    "what is the glycemic index",
    "benefits of drinking enough water",
    "how to improve sleep quality",
    # Technology
    "what is edge computing",
    "how does blockchain technology work",
    "what is a large language model",
    "how does wifi work",
    "what is cloud computing",
    "how do search engines rank pages",
    "what is the internet of things",
    "how does end to end encryption work",
    "what is a neural network",
    "how do self driving cars work",
    "what is quantum encryption",
    "how does 5g technology work",
    # Programming & software
    "difference between sql and nosql databases",
    "what is object oriented programming",
    "how does garbage collection work",
    "what is a rest api",
    "difference between frontend and backend development",
    "what is continuous integration",
    "how does version control work",
    "what is a microservices architecture",
    "difference between compiled and interpreted languages",
    "what is test driven development",
    # Cybersecurity
    "what is a ddos attack",
    "how does two factor authentication work",
    "what is phishing",
    "how do vpns protect privacy",
    "what is ransomware",
    "how does a firewall work",
    "what is zero trust security",
    "how do hackers exploit software vulnerabilities",
    # History -- ancient & medieval
    "history of ancient egypt",
    "what caused the fall of constantinople",
    "history of the silk road",
    "who were the vikings",
    "history of the byzantine empire",
    "what was the black death",
    "history of ancient greece",
    "who built the great wall of china",
    "history of the crusades",
    "what was the renaissance",
    # History -- modern
    "causes of world war two",
    "what was the industrial revolution",
    "history of the cold war",
    "what caused the great depression",
    "history of the civil rights movement",
    "what was the berlin wall",
    "causes of the russian revolution",
    "history of the space race",
    "what was the marshall plan",
    "history of decolonization in africa",
    # Finance & economics
    "what is compound interest",
    "how does the federal reserve control interest rates",
    "what is a recession",
    "difference between a roth ira and traditional ira",
    "what is diversification in investing",
    "how do mutual funds work",
    "what is gdp",
    "how does inflation affect purchasing power",
    "what is a bear market",
    "how do credit scores work",
    "what is dollar cost averaging",
    "how does the bond market work",
    # Business & entrepreneurship
    "how to write a business plan",
    "what is product market fit",
    "how to raise venture capital",
    "what is a minimum viable product",
    "how to price a product",
    "what makes a good company culture",
    "how to build a marketing strategy",
    "what is customer lifetime value",
    # Environment & climate
    "what is ocean acidification",
    "how do carbon offsets work",
    "what is deforestation's impact on climate",
    "how does recycling plastic work",
    "what is a circular economy",
    "how do wind turbines generate electricity",
    "what is biodiversity loss",
    "how does air pollution affect health",
    "what is sustainable agriculture",
    "how do electric grids balance renewable energy",
    # Geography & travel
    "what is the largest desert in the world",
    "how were the himalayas formed",
    "best time to visit japan",
    "what causes monsoon seasons",
    "geography of the amazon rainforest",
    "how deep is the mariana trench",
    "what countries border the sahara desert",
    "best practices for solo travel safety",
    # Culture, art & entertainment
    "history of impressionist painting",
    "origins of hip hop music",
    "what makes a film a cult classic",
    "history of the olympic games",
    "how does streaming change the music industry",
    "what is magical realism in literature",
    "history of classical ballet",
    "origins of anime",
    "what makes a novel a bestseller",
    "history of photography as an art form",
    # Sports
    "rules of american football",
    "history of the fifa world cup",
    "how does the offside rule work in soccer",
    "what is var in football",
    "history of the olympics marathon",
    "how do tennis rankings work",
    "rules of cricket for beginners",
    "how does doping testing work in sports",
    # Psychology & behavior
    "what is cognitive behavioral therapy",
    "how does habit formation work",
    "what is imposter syndrome",
    "how does memory consolidation work during sleep",
    "what is emotional intelligence",
    "how does procrastination affect productivity",
    "what is the placebo effect",
    "how does social media affect mental health",
    # Education & learning
    "what is spaced repetition",
    "benefits of bilingual education",
    "how does the montessori method work",
    "what is project based learning",
    "benefits of standardized testing",
    "how does online learning compare to in person",
    "what is growth mindset",
    "benefits of lifelong learning",
    # Law & civics
    "how does the electoral college work",
    "what is the separation of powers",
    "how does a bill become a law in the us",
    "what is intellectual property law",
    "how does jury selection work",
    "what is the difference between civil and criminal law",
    "how does the supreme court decide cases",
    "what is habeas corpus",
    # Parenting & relationships
    "how to encourage healthy screen time habits in kids",
    "what is attachment theory in child development",
    "benefits of reading to children early",
    "how to navigate conflict in a relationship",
    "what are the stages of child development",
    "how to build financial literacy in teenagers",
    # Automotive & transportation
    "how do hybrid engines work",
    "what is regenerative braking",
    "history of the interstate highway system",
    "how do electric vehicle charging networks work",
    "what is autonomous vehicle level classification",
    "benefits of public transit for cities",
    # Food & cooking
    "science behind bread fermentation",
    "how to properly season cast iron",
    "what makes umami flavor",
    "difference between baking soda and baking powder",
    "how does fermentation preserve food",
    "what is the maillard reaction",
    "benefits of fermented foods",
    "how to reduce food waste at home",
    # Real estate & housing
    "how does a mortgage amortization schedule work",
    "what is a homeowners association",
    "how do property taxes get calculated",
    "what is the difference between renting and buying a home",
    "how does home appraisal work",
    "what is a fixed vs adjustable rate mortgage",
    # Language & linguistics
    "how do languages evolve over time",
    "what makes a language endangered",
    "how does sign language grammar work",
    "benefits of learning a second language as an adult",
    "what is the difference between a dialect and a language",
    "how do translation apps work",
    # Religion & philosophy (history/concepts, kept factual)
    "history of the protestant reformation",
    "what is stoicism",
    "history of buddhism's spread across asia",
    "what is utilitarianism",
    "history of the islamic golden age",
    "what is existentialism",
    "history of hinduism's major texts",
    "what is the socratic method",
    # Gaming & digital culture
    "history of the video game industry",
    "what makes a game go viral",
    "how does esports scale as a career",
    "what is procedural generation in games",
    "history of virtual reality technology",
    "how do loot boxes work in games",
    # Agriculture & food systems
    "how does vertical farming work",
    "what is regenerative agriculture",
    "how do gmo crops get developed",
    "what causes food price inflation",
    "how does crop rotation improve soil health",
    "what is precision agriculture",
    # Weather & natural disasters
    "how do hurricanes form",
    "what causes tornadoes",
    "how do meteorologists predict weather",
    "what is el nino",
    "how does wildfire behavior change with climate",
    "what causes flash floods",
    "how do drought conditions develop",
    "what is a polar vortex",
    # Insurance & personal finance
    "how does life insurance underwriting work",
    "what is an emergency fund",
    "how do health insurance deductibles work",
    "what is the difference between term and whole life insurance",
    "how does budgeting with the 50/30/20 rule work",
    "what is identity theft protection",
    # Wellbeing & everyday science
    "what is seasonal affective disorder",
    "how does caffeine affect the body",
    "what is the uncanny valley effect",
    "how do noise pollution regulations work",
    "what is biophilic design",
    "how does the urban heat island effect work",
    "what is the tragedy of the commons",
    "how does spaced learning improve retention",
    # Architecture & engineering
    "how do suspension bridges support weight",
    "what makes a building earthquake resistant",
    "history of skyscraper construction",
    "how does hvac system design work",
    "what is sustainable architecture",
    "how do dams generate hydroelectric power",
    "what is structural load bearing",
    "history of gothic cathedral architecture",
    # Practical & everyday
    "how do noise cancelling headphones work",
    "what is the sharing economy",
    "how does airline pricing work",
    "what causes traffic congestion",
    "how do vending machines work",
    "what is minimalism as a lifestyle",
    "benefits of decluttering your home",
    "how does insurance underwriting work",
    "what is a supply chain bottleneck",
    "how do loyalty reward programs work",
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
    for i, q in enumerate(QUERIES):
        try:
            r = await run_one(q)
        except Exception as exc:
            r = {"query": q, "error": str(exc)}
        out.append(r)
        print(f"[{i + 1}/{len(QUERIES)}] {json.dumps(r)}")

        # Paced, not fired as fast as possible -- a 1.5s gap still tripped
        # Brave/Google CSE's abuse detection (SearxEngineTooManyRequests,
        # ~1hr suspension) and Startpage's CAPTCHA wall (~24hr suspension)
        # during a 300-query run. 6s is far more conservative.
        if i < len(QUERIES) - 1:
            await asyncio.sleep(6.0)

        if (i + 1) % 20 == 0:
            with open("scripts/calibration_results.json", "w") as f:
                json.dump(out, f, indent=2)

    with open("scripts/calibration_results.json", "w") as f:
        json.dump(out, f, indent=2)


if __name__ == "__main__":
    asyncio.run(main())
