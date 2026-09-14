from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "healthy"
    app_name: str
    version: str
    environment: str
    playwright_ready: bool
    llm_backend: str
    llm_ready: bool
    llm_message: str
    search_engine: str


class ResearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500, description="The research topic or question")
    max_depth: int = Field(default=2, ge=1, le=4, description="Search depth (number of sub-queries)")
    max_sources: int = Field(default=4, ge=1, le=10, description="Maximum web sources to scrape and analyze")
    language: Optional[str] = Field(default="en", description="Target response language")


class SourceItem(BaseModel):
    url: str
    title: str
    domain: str
    snippet: str
    status: str


class ResearchResponse(BaseModel):
    query: str
    question: Optional[str] = None
    answer: Optional[str] = None
    report: str
    sources: List[SourceItem]
    execution_time_sec: float
    sub_queries: List[str] = []
    total_sources_scanned: int = 0


class StreamEvent(BaseModel):
    step: str
    message: str
    details: Optional[Dict[str, Any]] = None
