from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Application
    APP_NAME: str = "AI Web Research & Intelligence Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    VERSION: str = "1.0.0"

    # Qwen LLM
    QWEN_BACKEND: Literal["ollama", "openai_compatible", "mock"] = "mock"
    QWEN_BASE_URL: str = "http://localhost:11434/v1"
    QWEN_API_KEY: str = "ollama"
    QWEN_MODEL: str = "qwen2.5:latest"
    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_TOKENS: int = 4096

    # Playwright Browser (Zero Search API)
    PLAYWRIGHT_HEADLESS: bool = True
    BROWSER_TIMEOUT_MS: int = 6000
    MAX_CONCURRENT_PAGES: int = 5
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    )

    # Safe Browsing & Anti-Abuse
    ENABLE_AD_BLOCKING: bool = True
    ENABLE_SSRF_PROTECTION: bool = True
    PAGE_MAX_BODY_CHARS: int = 25000
    MAX_RESEARCH_DEPTH: int = 2
    MAX_SOURCES_PER_QUERY: int = 4
    SEARCH_ENGINE: str = "duckduckgo"


settings = Settings()
