import re
import base64
import urllib.parse
from dataclasses import dataclass
from typing import List, Optional
import httpx
from bs4 import BeautifulSoup
from app.browser.playwright_manager import playwright_manager
from app.core.config import settings
from app.core.logging_config import logger
from app.core.security import is_safe_url


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    engine: str


class DirectBrowserSearch:
    """
    Executes web searches directly without commercial Search APIs.
    Uses direct HTML search parsing with Bing/DuckDuckGo fallback.
    """

    @staticmethod
    def _unwrap_ddg_url(raw_href: str) -> str:
        """Extracts the actual destination URL from DuckDuckGo redirect link."""
        if not raw_href:
            return ""
        if "uddg=" in raw_href:
            parsed = urllib.parse.urlparse(raw_href)
            query_params = urllib.parse.parse_qs(parsed.query)
            if "uddg" in query_params:
                return query_params["uddg"][0]
        if raw_href.startswith("//"):
            return "https:" + raw_href
        return raw_href

    @staticmethod
    def _unwrap_bing_url(raw_href: str) -> str:
        """Extracts the direct target URL from Bing tracking redirect links."""
        if not raw_href:
            return ""
        if "bing.com/ck/a?" in raw_href and "&u=a1" in raw_href:
            try:
                u_part = raw_href.split("&u=a1")[1].split("&")[0]
                u_part += "=" * (-len(u_part) % 4)
                decoded = base64.b64decode(u_part).decode("utf-8", errors="ignore")
                if decoded.startswith("http"):
                    return decoded
            except Exception:
                pass
        return raw_href

    @classmethod
    def parse_duckduckgo_html(cls, html: str) -> List[SearchResult]:
        """Parses organic search results from DuckDuckGo HTML output."""
        soup = BeautifulSoup(html, "html.parser")
        results: List[SearchResult] = []

        items = soup.select(".result") or soup.select(".web-result") or soup.select(".results_links")
        for item in items:
            if "result--ad" in item.get("class", []):
                continue

            title_elem = item.select_one(".result__a") or item.select_one("a.result__title") or item.select_one("h2 a")
            snippet_elem = item.select_one(".result__snippet") or item.select_one(".snippet")

            if not title_elem:
                continue

            raw_href = title_elem.get("href", "").strip()
            target_url = cls._unwrap_ddg_url(raw_href)
            title = title_elem.get_text(strip=True)
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            if not target_url.startswith("http"):
                continue

            safe, _ = is_safe_url(target_url)
            if not safe:
                continue

            results.append(
                SearchResult(
                    title=title,
                    url=target_url,
                    snippet=snippet,
                    engine="duckduckgo"
                )
            )

        return results

    @classmethod
    def parse_bing_html(cls, html: str) -> List[SearchResult]:
        """Parses organic search results from Bing web search output."""
        soup = BeautifulSoup(html, "html.parser")
        results: List[SearchResult] = []

        algo_items = soup.select("li.b_algo")
        for item in algo_items:
            title_elem = item.select_one("h2 a")
            snippet_elem = item.select_one(".b_caption p") or item.select_one("p")

            if not title_elem:
                continue

            raw_href = title_elem.get("href", "").strip()
            target_url = cls._unwrap_bing_url(raw_href)
            title = title_elem.get_text(strip=True)
            snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

            if not target_url.startswith("http"):
                continue

            safe, _ = is_safe_url(target_url)
            if not safe:
                continue

            results.append(
                SearchResult(
                    title=title,
                    url=target_url,
                    snippet=snippet,
                    engine="bing"
                )
            )

        return results

    async def search(self, query: str, max_results: Optional[int] = None) -> List[SearchResult]:
        """
        Executes an instant browser-driven web search without any search API.
        Uses DuckDuckGo direct POST first for ultra-fast (sub-second) results,
        with Playwright Bing fallback.
        """
        limit = max_results or settings.MAX_SOURCES_PER_QUERY
        results: List[SearchResult] = []

        # 1. Ultra-fast direct DuckDuckGo HTML query
        try:
            logger.info(f"[DirectSearch] Fast web query for: '{query}'")
            headers = {
                "User-Agent": settings.USER_AGENT,
                "Referer": "https://html.duckduckgo.com/",
                "Accept-Language": "en-US,en;q=0.9",
            }
            async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
                resp = await client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query.strip()},
                    headers=headers
                )
                if resp.status_code == 200:
                    results = self.parse_duckduckgo_html(resp.text)
                    logger.info(f"[DirectSearch] Found {len(results)} results from DuckDuckGo.")
        except Exception as e:
            logger.warning(f"[DirectSearch] DuckDuckGo quick query skipped: {e}")

        # 2. Fallback to Bing via Playwright if DDG had insufficient results
        if len(results) < 2:
            logger.info("[DirectSearch] Using Bing browser search...")
            encoded_query = urllib.parse.quote_plus(query.strip())
            bing_url = f"https://www.bing.com/search?q={encoded_query}"
            bing_html, _, bing_status = await playwright_manager.fetch_page_content(bing_url)
            if bing_html and bing_status == 200:
                bing_results = self.parse_bing_html(bing_html)
                logger.info(f"[DirectSearch] Found {len(bing_results)} results from Bing.")
                existing_urls = {r.url for r in results}
                for br in bing_results:
                    if br.url not in existing_urls:
                        results.append(br)

        return results[:limit]


browser_search = DirectBrowserSearch()
