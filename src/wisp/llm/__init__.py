"""LLM backends for Stage 4, behind one shared interface so the pipeline
doesn't care whether synthesis runs against the local llama-server or the
Claude API."""

from __future__ import annotations

from typing import Protocol


class LLMBackend(Protocol):
    async def chat(self, system: str, user: str) -> str: ...


def get_backend(name: str, settings) -> LLMBackend:
    if name == "claude":
        from wisp.llm.claude import ClaudeBackend

        return ClaudeBackend(api_key=settings.anthropic_api_key, model=settings.claude_model)

    from wisp.llm.local import LocalBackend

    return LocalBackend(base_url=settings.llama_server_url, model=settings.local_model)
