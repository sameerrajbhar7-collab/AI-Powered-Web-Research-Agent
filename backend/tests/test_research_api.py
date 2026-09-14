import pytest
from unittest.mock import patch, AsyncMock
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.browser.search_engine import SearchResult


@pytest.mark.asyncio
async def test_research_endpoint_validation_error():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/research", json={"query": ""})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_research_endpoint_mocked():
    fake_search_results = [
        SearchResult(
            title="Next-Gen AI Research",
            url="https://example.com/ai-doc",
            snippet="Autonomous agents navigating web pages directly.",
            engine="duckduckgo"
        )
    ]

    with patch("app.browser.search_engine.browser_search.search", new_callable=AsyncMock) as mock_search, \
         patch("app.browser.playwright_manager.playwright_manager.fetch_page_content", new_callable=AsyncMock) as mock_fetch:

        mock_search.return_value = fake_search_results
        mock_fetch.return_value = ("<html><body><h1>AI Doc</h1><p>Autonomous agents are transforming intelligence gathering.</p></body></html>", "AI Doc", 200)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            response = await ac.post(
                "/research",
                json={
                    "query": "Future of Autonomous Agents",
                    "max_depth": 1,
                    "max_sources": 1
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "Future of Autonomous Agents"
        assert len(data["sources"]) >= 1
        assert "Autonomous agents" in data["report"] or "Intelligence Report" in data["report"]
        assert data["execution_time_sec"] >= 0


@pytest.mark.asyncio
async def test_research_stream_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/research/stream",
            params={
                "query": "Stream Test Query",
                "max_depth": 1,
                "max_sources": 1
            }
        )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers.get("content-type", "")
