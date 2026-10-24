"""
Real AI extraction service — LangGraph + Groq.

Implements the AiService contract (see ai_service.py) by compiling and
running the LangGraph pipeline defined in app/services/langgraph_pipeline.py:

    receive_source -> extract_deviation -> validate_extraction
    -> assess_impact -> recommend_severity -> identify_missing_information
    -> format_response

This is the only module that talks to Groq. Everything upstream (routes,
schemas, DI) is unaware of LangGraph/Groq and would work unchanged against
any other AiService implementation (see ai_service_stub.py).
"""
import asyncio
import logging

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.errors import AiServiceUnavailableError, ExtractionFailedError
from app.schemas.deviation import AiOutputSchema
from app.services.ai_service import AiService
logger = logging.getLogger(__name__)


class LangGraphAiService(AiService):
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.GROQ_API_KEY:
            raise AiServiceUnavailableError(
                "AI service is enabled but GROQ_API_KEY is not configured.",
            )

        # Deferred import: langchain_groq/groq are only required once the
        # real pipeline is switched on (AI_SERVICE_ENABLED=true), so the
        # stub service and the rest of the app stay usable without them
        # installed.
        try:
            from langchain_groq import ChatGroq
            from app.services.langgraph_pipeline import build_deviation_graph
        except ImportError as exc:  # pragma: no cover - environment/dependency guard
            logger.exception("AI pipeline dependencies are unavailable")
            raise AiServiceUnavailableError(
                "The AI service dependencies are not installed. Please install the backend requirements and try again."
            ) from exc

        self.model = settings.GROQ_MODEL
        self.timeout = settings.AI_REQUEST_TIMEOUT_SECONDS

        llm = ChatGroq(
            model=self.model,
            api_key=settings.GROQ_API_KEY,
            temperature=0,
            timeout=self.timeout,
            max_retries=2,
        )
        self.graph = build_deviation_graph(llm)

    async def _run_graph(self, raw_text: str, source_type: str) -> AiOutputSchema:
        if not raw_text or not raw_text.strip():
            raise ExtractionFailedError("No source text was provided to the AI pipeline.")

        try:
            final_state = await asyncio.wait_for(
                self.graph.ainvoke({"raw_text": raw_text, "source_type": source_type}),
                timeout=self.timeout,
            )
        except asyncio.TimeoutError as exc:
            logger.exception("LangGraph pipeline timed out")
            raise AiServiceUnavailableError(
                "The AI service took too long to respond. Please try again."
            ) from exc
        except (AiServiceUnavailableError, ExtractionFailedError):
            raise
        except Exception as exc:  # noqa: BLE001 - provider/network/pipeline failures
            logger.exception("LangGraph pipeline failed")
            raise ExtractionFailedError(
                "AI analysis failed while processing the deviation. Please try again."
            ) from exc

        result = final_state.get("result") if isinstance(final_state, dict) else None
        if result is None:
            logger.error("LangGraph pipeline completed without producing a result: %s", final_state)
            raise ExtractionFailedError("The AI pipeline did not produce a result.")

        try:
            return AiOutputSchema.model_validate(
                result if isinstance(result, dict) else result.model_dump()
            )
        except ValidationError as exc:
            logger.exception("LangGraph pipeline produced output that failed schema validation")
            raise ExtractionFailedError(
                "The AI produced an invalid response. Please try again."
            ) from exc

    async def analyze_text(self, text: str, source_type: str = "text") -> AiOutputSchema:
        return await self._run_graph(text, source_type)

    async def analyze_document(self, raw_text: str, filename: str, source_type: str) -> AiOutputSchema:
        # Document text is pre-extracted by app/services/document_extraction.py,
        # so this simply runs the same pipeline as pasted text/email.
        logger.info("analyze_document: filename=%s, source_type=%s", filename, source_type)
        return await self._run_graph(raw_text, source_type)
