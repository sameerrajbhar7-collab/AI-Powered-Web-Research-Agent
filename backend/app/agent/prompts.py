"""
Prompt templates for Qwen LLM Web QA.
Generates:
Sources Used (with specific answer/facts retrieved from each source)
"""

QA_SYSTEM_PROMPT = """You are an elite AI Web Assistant.
Your goal is to extract and attribute answers to the user's question directly to the source web pages.
Under Sources Used, explicitly state each source title, direct URL, and the specific answer or facts retrieved from that source."""

QA_USER_PROMPT = """Question: {question}

--- EXTRACTED WEB CONTENT ---
{web_content}
-----------------------------

Instructions:
Under "### Sources Used", list each source and provide a comprehensive 2 to 3 line explanation of the specific facts and answers retrieved from that webpage.

Output Format:
### Sources Used
- **[Source Title](URL)**: <Detailed 2-3 line answer and factual explanation retrieved from this source>

"""

FALLBACK_ANSWER_TEMPLATE = """### Sources Used
{sources_used}
"""
