import re
import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.core.logging_config import logger
from app.agent.prompts import (
    QA_SYSTEM_PROMPT,
    QA_USER_PROMPT,
    FALLBACK_ANSWER_TEMPLATE,
)


class QwenLLMClient:
    """
    Simplified Qwen LLM Client.
    Directly answers user questions from extracted Playwright web content.
    """

    def __init__(self):
        self.backend = settings.QWEN_BACKEND
        self.base_url = settings.QWEN_BASE_URL.rstrip("/")
        self.api_key = settings.QWEN_API_KEY
        self.model = settings.QWEN_MODEL

    async def check_health(self) -> tuple[bool, str]:
        """Verifies connectivity to the configured LLM backend."""
        if self.backend == "mock":
            return True, "Qwen Heuristic (Autonomous Mock)"

        try:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            async with httpx.AsyncClient(timeout=3.0) as client:
                test_url = f"{self.base_url}/models"
                resp = await client.get(test_url, headers=headers)
                if resp.status_code in (200, 401, 403):
                    return True, f"{self.backend.upper()} reachable ({resp.status_code})"
                return False, f"Unexpected status {resp.status_code} from {test_url}"
        except Exception as e:
            return False, f"LLM backend unreachable: {e}"

    async def _call_api(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """Calls OpenAI-compatible /chat/completions endpoint."""
        url = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": settings.LLM_TEMPERATURE,
            "max_tokens": 1024,
        }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "").strip()
                logger.warning(f"LLM API returned status {resp.status_code}: {resp.text[:200]}")
                return None
        except Exception as e:
            logger.warning(f"Error communicating with LLM API: {e}")
            return None

    async def expand_queries(self, topic: str) -> List[str]:
        """Returns direct search query without complex multi-query expansion."""
        return [topic.strip()]

    async def answer_question(self, question: str, sources: List[Dict[str, Any]]) -> str:
        """
        Sends extracted web page content to Qwen to generate a concise answer with source URLs.
        """
        if not sources:
            return "No web pages could be retrieved to answer this question."

        # Prepare context blocks from extracted web content
        context_parts = []
        sources_list = []
        for idx, src in enumerate(sources, start=1):
            title = src.get("title", f"Source {idx}")
            url = src.get("url", "")
            snippet = src.get("snippet", "")
            content = src.get("content", "")
            body = content if content and len(content) > 50 else snippet

            context_parts.append(f"[Source {idx}] {title} ({url}):\n{body[:1800]}\n")
            sources_list.append(f"- [{title}]({url})")

        web_content = "\n---\n".join(context_parts)
        user_prompt = QA_USER_PROMPT.format(question=question, web_content=web_content)

        # Call live Qwen if configured
        if self.backend != "mock":
            messages = [
                {"role": "system", "content": QA_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
            answer = await self._call_api(messages)
            if answer and len(answer) > 20:
                return answer

        # Fast heuristic fallback: extracts core informative sentences from web pages (2 to 3 lines per source)
        sources_used_lines = []

        for idx, src in enumerate(sources, start=1):
            title = src.get("title", f"Source {idx}")
            url = src.get("url", "")
            text = src.get("content") or src.get("snippet") or ""

            # Extract clean meaningful sentences from this source
            sentences = [
                s.strip()
                for s in re.split(r"[.\n]+", text)
                if len(s.strip()) > 30
                and not s.strip().startswith("#")
                and not any(w in s.lower() for w in ["cookie", "privacy policy", "javascript", "log in", "sign up"])
            ]
            chosen = sentences[:3]
            if chosen:
                fact = ". ".join(s.rstrip(". ") for s in chosen) + "."
            else:
                fact = src.get("snippet", "").strip() or "Information retrieved from source."

            sources_used_lines.append(f"- **[{title}]({url})**: {fact}")

        return FALLBACK_ANSWER_TEMPLATE.format(
            sources_used="\n".join(sources_used_lines)
        )

    async def synthesize_report(self, topic: str, sources: List[Dict[str, Any]]) -> str:
        """Backward-compatible alias for answer_question."""
        return await self.answer_question(topic, sources)


qwen_client = QwenLLMClient()
