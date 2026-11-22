"""Runtime configuration, read from environment variables.

Defaults target Groq's free tier. Any OpenAI-compatible endpoint works: change LLM_BASE_URL,
LLM_API_KEY and CONSEARCH_MODEL (see README for Gemini, OpenRouter and Ollama presets).
"""

import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import find_dotenv, load_dotenv

# Ensure .env is loaded reliably from the project root and overrides any stale shell environment variables
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE, override=True)
else:
    load_dotenv(find_dotenv(usecwd=True), override=True)

def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


@dataclass(frozen=True)
class Settings:
    # LLM (OpenAI-compatible chat completions with tool calling)
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1").strip()
    llm_api_key: str | None = os.getenv("LLM_API_KEY", "").strip() or None
    model: str = os.getenv("CONSEARCH_MODEL", "openai/gpt-oss-20b").strip()

    # Web search: "duckduckgo" (default, no key), "wikipedia" (no key), or "searxng" (self-hosted)
    search_provider: str = os.getenv("SEARCH_PROVIDER", "duckduckgo")
    searxng_url: str | None = os.getenv("SEARXNG_URL")

    # Agent behaviour
    max_agent_steps: int = _env_int("CONSEARCH_MAX_STEPS", 6)
    history_turns: int = _env_int("CONSEARCH_HISTORY_TURNS", 6)

    # RAG
    embedder: str = os.getenv("CONSEARCH_EMBEDDER", "tfidf")  # "tfidf" | "sentence-transformers"
    top_k: int = _env_int("CONSEARCH_TOP_K", 5)
    chunk_words: int = _env_int("CONSEARCH_CHUNK_WORDS", 180)
    chunk_overlap: int = _env_int("CONSEARCH_CHUNK_OVERLAP", 30)
    fetch_chars: int = _env_int("CONSEARCH_FETCH_CHARS", 4000)
