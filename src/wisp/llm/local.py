"""Local backend — Mana's llama-server, native OpenAI-compatible endpoint.

No auth: this hits llama.cpp's own server directly (127.0.0.1 only),
not Mana's authenticated /v1/chat/completions proxy.
"""

from __future__ import annotations

import httpx


class LocalBackend:
    def __init__(self, base_url: str, model: str):
        self.base_url = base_url
        self.model = model

    async def chat(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return data["choices"][0]["message"]["content"]
