import pytest

from wisp.models import Source
from wisp.synthesize import synthesize


class _FailingBackend:
    async def chat(self, system: str, user: str) -> str:
        raise RuntimeError("boom")


class _OkBackend:
    async def chat(self, system: str, user: str) -> str:
        return "answer text [1]"


@pytest.mark.asyncio
async def test_synthesize_returns_unavailable_when_no_usable_sources():
    result = await synthesize("q", [Source(title="t", url="u", snippet="")], _OkBackend())

    assert result.synthesis_unavailable is True
    assert result.answer is None


@pytest.mark.asyncio
async def test_synthesize_returns_unavailable_when_backend_raises():
    sources = [Source(title="t", url="u", snippet="some content")]

    result = await synthesize("q", sources, _FailingBackend())

    assert result.synthesis_unavailable is True
    assert "boom" in result.reason


@pytest.mark.asyncio
async def test_synthesize_returns_answer_on_success():
    sources = [Source(title="t", url="u", snippet="some content")]

    result = await synthesize("q", sources, _OkBackend())

    assert result.synthesis_unavailable is False
    assert result.answer == "answer text [1]"
