"""
Tests for app/services/ai_service_langgraph.py — the AiService wrapper
around the LangGraph pipeline. These focus on error handling (section 17
of the Agent 4 prompt): missing API key, provider failure, timeout, and
malformed output must all become controlled AppError subclasses, never
raw exceptions or a crash.
"""
import asyncio

import pytest

from app.core.errors import AiServiceUnavailableError, ExtractionFailedError


def test_missing_api_key_raises_ai_service_unavailable(monkeypatch):
    from app.core.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("GROQ_API_KEY", "")
    monkeypatch.setenv("AI_SERVICE_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test_ai_service.db")
    get_settings.cache_clear()

    from app.services.ai_service_langgraph import LangGraphAiService

    with pytest.raises(AiServiceUnavailableError):
        LangGraphAiService()

    get_settings.cache_clear()


def test_empty_source_text_raises_extraction_failed(monkeypatch):
    """analyze_text/_run_graph must reject blank input before touching Groq."""
    from app.services.ai_service_langgraph import LangGraphAiService

    # Bypass __init__ (which requires a real API key + langchain_groq
    # installed) and exercise _run_graph directly.
    service = LangGraphAiService.__new__(LangGraphAiService)
    service.timeout = 30

    with pytest.raises(ExtractionFailedError):
        asyncio.run(service._run_graph("   ", "text"))


def test_provider_failure_is_wrapped_as_extraction_failed(monkeypatch):
    from app.services.ai_service_langgraph import LangGraphAiService

    class ExplodingGraph:
        async def ainvoke(self, state):
            raise RuntimeError("simulated Groq outage")

    service = LangGraphAiService.__new__(LangGraphAiService)
    service.timeout = 30
    service.graph = ExplodingGraph()

    with pytest.raises(ExtractionFailedError):
        asyncio.run(service._run_graph("some deviation text", "text"))


def test_timeout_is_wrapped_as_ai_service_unavailable(monkeypatch):
    from app.services.ai_service_langgraph import LangGraphAiService

    class HangingGraph:
        async def ainvoke(self, state):
            await asyncio.sleep(10)

    service = LangGraphAiService.__new__(LangGraphAiService)
    service.timeout = 0.05
    service.graph = HangingGraph()

    with pytest.raises(AiServiceUnavailableError):
        asyncio.run(service._run_graph("some deviation text", "text"))
