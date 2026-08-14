"""Runtime configuration, loaded from environment / .env.

All values here are the tunables called out in the design doc's decision
records — defaults are starting points for empirical calibration, not
final numbers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    searxng_url: str
    llama_server_url: str
    anthropic_api_key: str | None
    embedding_model: str
    extract_top_n: int
    prune_margin: float
    local_model: str
    claude_model: str


def load_settings() -> Settings:
    return Settings(
        searxng_url=os.getenv("SEARXNG_URL", "http://127.0.0.1:8890"),
        llama_server_url=os.getenv("LLAMA_SERVER_URL", "http://127.0.0.1:8090"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        embedding_model=os.getenv("WISP_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        extract_top_n=int(os.getenv("WISP_EXTRACT_TOP_N", "6")),
        # Calibrated against 10 real queries (see scripts/calibrate_margin.py):
        # genuinely on-topic sources land within 0.03-0.40 of the top score,
        # while extraction failures (near-zero/negative similarity) land at
        # 0.59+, with a clean gap between the two -- 0.45 sits in that gap.
        prune_margin=float(os.getenv("WISP_PRUNE_MARGIN", "0.45")),
        local_model=os.getenv("WISP_LOCAL_MODEL", "local"),
        claude_model=os.getenv("WISP_CLAUDE_MODEL", "claude-sonnet-5"),
    )


settings = load_settings()
