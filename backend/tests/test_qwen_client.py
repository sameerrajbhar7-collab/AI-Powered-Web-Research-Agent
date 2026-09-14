import pytest
from app.agent.qwen_client import QwenLLMClient


@pytest.mark.asyncio
async def test_qwen_expand_queries():
    client = QwenLLMClient()
    topic = "Autonomous Web Crawlers"
    queries = await client.expand_queries(topic)

    assert isinstance(queries, list)
    assert len(queries) >= 1
    assert any("Autonomous Web Crawlers" in q for q in queries)


@pytest.mark.asyncio
async def test_qwen_synthesize_report_fallback():
    client = QwenLLMClient()
    topic = "Quantum Supercomputing"
    mock_sources = [
        {
            "url": "https://example.com/quantum",
            "title": "Quantum Breakthroughs",
            "snippet": "New logical qubits demonstrated unprecedented error mitigation rates.",
            "content": "Researchers achieved 99.9% gate fidelity using superconducting transmon qubits.",
        }
    ]

    answer = await client.answer_question(topic, mock_sources)

    assert "Sources Used" in answer
    assert "https://example.com/quantum" in answer
    assert "Quantum Breakthroughs" in answer

