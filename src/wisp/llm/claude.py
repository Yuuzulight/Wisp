"""Hosted backend — Claude API. Opt-in alternative to the local backend,
selected per-request; costs real money per query."""

from __future__ import annotations

from anthropic import AsyncAnthropic


class ClaudeBackend:
    def __init__(self, api_key: str | None, model: str):
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set; cannot use the claude backend.")
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def chat(self, system: str, user: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(block.text for block in response.content if block.type == "text")
