import json
import asyncio
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from app.core.config import settings
from app.core.logging_config import logger
from app.browser.playwright_manager import playwright_manager
from app.agent.qwen_client import qwen_client
from app.agent.research_agent import research_agent
from app.models.schemas import (
    HealthResponse,
    ResearchRequest,
    ResearchResponse,
    SourceItem
)

router = APIRouter()


@router.get("/health", response_model=HealthResponse, summary="System Health and Readiness")
async def get_health():
    """
    Returns system status, Playwright browser readiness, and Qwen LLM connectivity.
    """
    playwright_ready = await playwright_manager.is_ready()
    llm_ready, llm_msg = await qwen_client.check_health()

    status = "healthy" if (playwright_ready and llm_ready) else "degraded"

    return HealthResponse(
        status=status,
        app_name=settings.APP_NAME,
        version=settings.VERSION,
        environment=settings.APP_ENV,
        playwright_ready=playwright_ready,
        llm_backend=settings.QWEN_BACKEND,
        llm_ready=llm_ready,
        llm_message=llm_msg,
        search_engine=settings.SEARCH_ENGINE
    )


@router.post("/research", response_model=ResearchResponse, summary="Execute Complete Research Run")
async def execute_research(request: ResearchRequest):
    """
    Runs the multi-step browser-driven research pipeline synchronously without search APIs.
    """
    try:
        data = await research_agent.execute_research(
            query=request.query,
            max_depth=request.max_depth,
            max_sources=request.max_sources
        )

        sources = [
            SourceItem(
                url=s["url"],
                title=s.get("title", ""),
                domain=s.get("domain", ""),
                snippet=s.get("snippet", ""),
                status=s.get("status", "verified")
            )
            for s in data["sources"]
        ]

        return ResearchResponse(
            query=data["query"],
            question=data.get("question", data["query"]),
            answer=data.get("answer", data["report"]),
            report=data["report"],
            sources=sources,
            execution_time_sec=data["execution_time_sec"],
            sub_queries=data.get("sub_queries", [data["query"]]),
            total_sources_scanned=data.get("total_sources_scanned", len(sources))
        )
    except Exception as e:
        logger.exception(f"Error during research execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/research/stream", summary="Stream Research Execution Events via SSE")
async def stream_research_post(request: ResearchRequest):
    """
    Streams step-by-step progress, browser actions, visited URLs, and the final dossier via SSE.
    """
    async def event_generator():
        try:
            async for event in research_agent.stream_research(
                query=request.query,
                max_depth=request.max_depth,
                max_sources=request.max_sources
            ):
                payload = json.dumps(event)
                yield f"data: {payload}\n\n"
        except Exception as e:
            logger.exception(f"Stream error: {e}")
            err_payload = json.dumps({"step": "ERROR", "message": str(e), "details": {}})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/research/stream", summary="Stream Research via GET Query Params")
async def stream_research_get(
    query: str = Query(..., min_length=2, max_length=500),
    max_depth: int = Query(default=2, ge=1, le=4),
    max_sources: int = Query(default=4, ge=1, le=10),
):
    """
    GET convenience endpoint for SSE streaming directly from browser EventSource.
    """
    req = ResearchRequest(query=query, max_depth=max_depth, max_sources=max_sources)
    return await stream_research_post(req)
