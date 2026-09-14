import re
from typing import Optional
from bs4 import BeautifulSoup
from app.core.config import settings


class ContentExtractor:
    """
    Cleans raw HTML and extracts the main informational content as structured Markdown.
    Filters out noise like navigations, ads, footers, and scripts.
    """

    UNWANTED_TAGS = [
        "script", "style", "noscript", "svg", "header", "footer", "nav",
        "aside", "form", "iframe", "button", "input", "select", "textarea"
    ]

    UNWANTED_CLASSES_OR_IDS = [
        "cookie", "banner", "sidebar", "menu", "advert", "advertisement",
        "social-share", "newsletter", "popup", "modal", "disclaimer", "promo"
    ]

    @classmethod
    def clean_html_to_markdown(cls, raw_html: str, max_chars: Optional[int] = None) -> str:
        """
        Parses raw HTML and returns a clean, token-efficient text/markdown summary.
        """
        if not raw_html:
            return ""

        soup = BeautifulSoup(raw_html, "html.parser")

        # 1. Remove unwanted tags
        for tag in list(soup.find_all(cls.UNWANTED_TAGS)):
            if tag:
                try:
                    tag.decompose()
                except Exception:
                    pass

        # 2. Remove unwanted class/id elements matching ad/cookie patterns
        for tag in list(soup.find_all(True)):
            if not tag or not hasattr(tag, "attrs") or tag.attrs is None:
                continue
            id_val = str(tag.get("id") or "")
            class_val = " ".join(tag.get("class") or []) if isinstance(tag.get("class"), list) else str(tag.get("class") or "")
            attrs_str = f"{id_val} {class_val}".lower()
            if any(pattern in attrs_str for pattern in cls.UNWANTED_CLASSES_OR_IDS):
                try:
                    tag.decompose()
                except Exception:
                    pass

        # 3. Locate main content area if present
        main_content = (
            soup.find("article")
            or soup.find("main")
            or soup.find(attrs={"role": "main"})
            or soup.find(id=re.compile(r"content|main|article|body", re.I))
            or soup.body
            or soup
        )

        # 4. Extract meaningful text blocks
        blocks = []
        for elem in main_content.find_all(["h1", "h2", "h3", "h4", "p", "li", "table"]):
            tag_name = elem.name.lower()
            text = elem.get_text(separator=" ", strip=True)
            if not text or len(text) < 15 and tag_name not in ("h1", "h2", "h3", "h4"):
                continue

            if tag_name == "h1":
                blocks.append(f"\n# {text}\n")
            elif tag_name == "h2":
                blocks.append(f"\n## {text}\n")
            elif tag_name == "h3":
                blocks.append(f"\n### {text}\n")
            elif tag_name == "h4":
                blocks.append(f"\n#### {text}\n")
            elif tag_name == "li":
                blocks.append(f"- {text}")
            elif tag_name == "p":
                blocks.append(f"{text}\n")
            elif tag_name == "table":
                # Basic table text representation
                table_text = elem.get_text(separator=" | ", strip=True)
                if table_text:
                    blocks.append(f"[Table: {table_text[:300]}]\n")

        # Fallback if specific tags missed the text
        if not blocks:
            raw_text = main_content.get_text(separator="\n", strip=True)
            cleaned_text = re.sub(r"\n{3,}", "\n\n", raw_text)
            blocks.append(cleaned_text)

        result = "\n".join(blocks).strip()
        # Clean excessive whitespace
        result = re.sub(r"[ \t]+", " ", result)
        result = re.sub(r"\n{3,}", "\n\n", result)

        limit = max_chars or settings.PAGE_MAX_BODY_CHARS
        if len(result) > limit:
            result = result[:limit] + "\n\n...[Content truncated for analysis]..."

        return result


content_extractor = ContentExtractor()
