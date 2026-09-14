import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")

    assert response.status_code == 200
    data = response.json()

    assert "status" in data
    assert "app_name" in data
    assert "version" in data
    assert "playwright_ready" in data
    assert "llm_backend" in data
    assert "search_engine" in data
    assert data["app_name"] == "AI Web Research & Intelligence Agent"
