import httpx
import pytest
import respx

from wisp.retrieve import retrieve


@pytest.mark.asyncio
@respx.mock
async def test_retrieve_omits_engines_param_by_default():
    route = respx.get("http://searxng.test/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    await retrieve("query", "http://searxng.test")

    assert "engines" not in route.calls.last.request.url.params


@pytest.mark.asyncio
@respx.mock
async def test_retrieve_passes_engines_param_when_given():
    route = respx.get("http://searxng.test/search").mock(
        return_value=httpx.Response(200, json={"results": []})
    )

    await retrieve("query", "http://searxng.test", engines="google,stackoverflow")

    assert route.calls.last.request.url.params["engines"] == "google,stackoverflow"
