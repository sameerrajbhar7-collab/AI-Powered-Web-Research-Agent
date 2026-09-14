import time
import asyncio
from typing import List, Dict, Any, AsyncGenerator
from urllib.parse import urlparse
from app.browser.playwright_manager import playwright_manager
from app.browser.search_engine import browser_search, SearchResult
from app.browser.content_extractor import content_extractor
from app.agent.qwen_client import qwen_client
from app.core.logging_config import logger
from app.core.security import is_safe_url


class SimpleWebSearchAgent:
    """
    Simplified AI Web Search Agent.
    Flow: User Question -> Playwright Web Search -> Open Webpages -> Extract Text -> Qwen Answer + Sources.
    """

    async def _fetch_page(self, res: SearchResult) -> Dict[str, Any]:
        """Opens a webpage via Playwright and extracts clean text."""
        domain = urlparse(res.url).netloc
        safe, reason = is_safe_url(res.url)
        if not safe:
            return {
                "url": res.url,
                "title": res.title,
                "domain": domain,
                "snippet": res.snippet,
                "content": res.snippet,
                "status": "blocked"
            }

        try:
            html, page_title, status = await playwright_manager.fetch_page_content(res.url)
            if html and status == 200:
                text = content_extractor.clean_html_to_markdown(html)
                return {
                    "url": res.url,
                    "title": page_title or res.title,
                    "domain": domain,
                    "snippet": res.snippet,
                    "content": text if len(text) > 60 else res.snippet,
                    "status": "verified"
                }
        except Exception as e:
            logger.warning(f"[Agent] Failed to read {res.url}: {e}")

        return {
            "url": res.url,
            "title": res.title,
            "domain": domain,
            "snippet": res.snippet,
            "content": res.snippet,
            "status": "snippet_only"
        }

    async def search_and_answer(self, question: str) -> Dict[str, Any]:
        """
        Executes the simplified pipeline:
        User Question -> Playwright Search -> Fetch Webpages -> Qwen Answer.
        """
        start_time = time.time()
        logger.info(f"[Agent] Processing question: '{question}'")

        # 1. Playwright search (find top 3 relevant organic web links)
        search_results = await browser_search.search(question, max_results=3)

        # 2. Open pages & extract text in parallel
        tasks = [self._fetch_page(r) for r in search_results]
        sources = []
        if tasks:
            fetched = await asyncio.gather(*tasks, return_exceptions=True)
            for item in fetched:
                if isinstance(item, dict):
                    sources.append(item)

        # 3. Send extracted web content to Qwen to generate concise answer
        answer = await qwen_client.answer_question(question, sources)

        duration = round(time.time() - start_time, 2)
        logger.info(f"[Agent] Answered in {duration}s")

        return {
            "query": question,
            "question": question,
            "answer": answer,
            "report": answer,
            "sources": sources,
            "execution_time_sec": duration,
            "sub_queries": [question],
            "total_sources_scanned": len(sources)
        }

    async def execute_research(self, query: str, **kwargs) -> Dict[str, Any]:
        """Backward-compatible wrapper for search_and_answer."""
        return await self.search_and_answer(query)

    async def stream_research(self, query: str, **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Streams real-time progress events for the web UI."""
        start_time = time.time()

        yield {
            "step": "SEARCHING",
            "message": "Searching the web with Playwright...",
            "details": {"question": query}
        }

        # 1. Search
        search_results = await browser_search.search(query, max_results=3)

        # 2. Extract
        yield {
            "step": "CRAWLING",
            "message": f"Opening {len(search_results)} relevant webpages...",
            "details": {"count": len(search_results)}
        }

        tasks = [self._fetch_page(r) for r in search_results]
        sources = []
        if tasks:
            fetched = await asyncio.gather(*tasks, return_exceptions=True)
            for item in fetched:
                if isinstance(item, dict):
                    sources.append(item)

        # 3. Qwen Answer
        yield {
            "step": "SYNTHESIZING",
            "message": "Qwen is reading pages and generating answer...",
            "details": {"sources_count": len(sources)}
        }

        answer = await qwen_client.answer_question(query, sources)
        duration = round(time.time() - start_time, 2)

        yield {
            "step": "COMPLETE",
            "message": f"Answer generated in {duration}s.",
            "details": {
                "query": query,
                "question": query,
                "answer": answer,
                "report": answer,
                "sources": sources,
                "execution_time_sec": duration,
            }
        }


research_agent = SimpleWebSearchAgent()
