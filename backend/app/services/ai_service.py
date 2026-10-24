"""
Interface the rest of the backend codes against for AI extraction.

The real implementation (LangGraph + Groq) lives in ai_service_langgraph.py
and is a drop-in replacement — see get_ai_service() at the bottom, which is
the single switch point. Nothing in app/api/ should ever import a concrete
AI implementation directly.
"""
from abc import ABC, abstractmethod

from app.core.config import get_settings
from app.schemas.deviation import AiOutputSchema


class AiService(ABC):
    """Contract every deviation-extraction AI backend must satisfy."""

    @abstractmethod
    async def analyze_text(self, text: str, source_type: str = "text") -> AiOutputSchema:
        """
        Given raw deviation text/email content, return the full
        extraction + impact assessment + severity recommendation.
        Implementations should raise app.core.errors.ExtractionFailedError
        or AiServiceUnavailableError on failure rather than letting
        provider-specific exceptions escape.
        """
        raise NotImplementedError

    @abstractmethod
    async def analyze_document(self, raw_text: str, filename: str, source_type: str) -> AiOutputSchema:
        """
        Given text already extracted from an uploaded document (see
        app/services/document_extraction.py) plus the original filename,
        return the same AiOutputSchema shape as analyze_text.
        """
        raise NotImplementedError


def get_ai_service() -> AiService:
    """
    Dependency-injection entry point. The real LangGraph/Groq service is
    the default; set AI_SERVICE_ENABLED=false only for offline/local testing.
    """
    settings = get_settings()
    if settings.AI_SERVICE_ENABLED:
        # Deferred import: keeps the stub usable even if the LangGraph
        # dependency isn't installed yet.
        from app.services.ai_service_langgraph import LangGraphAiService

        return LangGraphAiService()

    from app.services.ai_service_stub import StubAiService

    return StubAiService()
