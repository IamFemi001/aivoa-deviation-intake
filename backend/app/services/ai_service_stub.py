"""
Deterministic stand-in for the real LangGraph + Groq pipeline.

This lets the API, database, and frontend integration all be built,
tested, and demoed end-to-end before the AI workflow itself exists.
It mirrors the same "rich vs. sparse" heuristic the frontend's own mock
(frontend/src/services/mockAiResponses.js) uses, so behavior is
consistent whichever side of the stack you're pointed at during
development.

Replace with app/services/ai_service_langgraph.py + AI_SERVICE_ENABLED=true
when the real pipeline is ready — see ai_service.get_ai_service().
"""
import logging
from datetime import datetime, timezone

from app.schemas.deviation import (
    AiOutputSchema,
    ExtractedDeviation,
    ImpactAssessment,
    ImpactCategory,
    SeverityRecommendation,
)
from app.services.ai_service import AiService

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rich_response(raw_text: str) -> AiOutputSchema:
    description = (
        "Operator noted that the crystallizer temperature exceeded the approved "
        "upper limit during the hold step, as described in the submitted source text."
        if raw_text
        else "Crystallizer temperature exceeded the approved upper limit during the hold step."
    )
    return AiOutputSchema(
        extraction=ExtractedDeviation(
            title="Process Parameter Excursion — Batch API-2026-014",
            event_datetime="2026-09-24T03:15:00Z",
            reported_datetime=_now_iso(),
            department="API Manufacturing",
            manufacturing_stage="Crystallization",
            batch_number="API-2026-014",
            description=description,
            expected_condition="Crystallizer temperature held at 18-22°C during the hold step.",
            actual_condition="Crystallizer temperature reached 27°C for approximately 40 minutes.",
            process_parameter="Crystallizer hold temperature",
            expected_value="18-22°C",
            actual_value="27°C",
            immediate_action="Batch quarantined; QA notified; crystallizer cooling circuit inspected.",
        ),
        impact_assessment=ImpactAssessment(
            product_quality=ImpactCategory(
                level="potential",
                reason="Elevated hold temperature may affect crystal size distribution and purity.",
            ),
            patient_safety=ImpactCategory(
                level="none",
                reason="No evidence of a patient-facing safety concern at this stage of manufacturing.",
            ),
            process=ImpactCategory(
                level="confirmed",
                reason="The hold temperature confirmedly exceeded the approved process range.",
            ),
            regulatory=ImpactCategory(
                level="potential",
                reason="An out-of-range process parameter may require regulatory notification depending on batch disposition.",
            ),
            data_integrity=ImpactCategory(
                level="none",
                reason="No indication of missing, altered, or inconsistent records.",
            ),
            batch_product=ImpactCategory(
                level="potential",
                reason="Batch API-2026-014 may require additional quality review before release.",
            ),
            overall_summary=(
                "A confirmed process excursion during crystallization with potential downstream "
                "effects on product quality and batch disposition; no patient safety or data "
                "integrity signal identified."
            ),
        ),
        severity=SeverityRecommendation(
            recommended_level="major",
            confidence=0.78,
            reason=(
                "The process parameter exceeded its approved range during manufacturing and "
                "may affect the quality of the affected batch."
            ),
            evidence=[
                "Actual hold temperature (27°C) exceeded the approved range (18-22°C)",
                "Deviation occurred during an active manufacturing stage (crystallization)",
                "Batch was quarantined pending quality review",
            ],
        ),
        missing_information=['Exact duration of the temperature excursion beyond "approximately 40 minutes"'],
    )


def _sparse_response() -> AiOutputSchema:
    unknown_category = lambda label: ImpactCategory(  # noqa: E731
        level="unknown", reason=f"Insufficient information to assess {label} impact."
    )
    return AiOutputSchema(
        extraction=ExtractedDeviation(
            title="Deviation Reported — Details Pending Review",
            reported_datetime=_now_iso(),
            description=(
                "An unspecified deviation was reported; the source text did not include "
                "enough detail for full extraction."
            ),
        ),
        impact_assessment=ImpactAssessment(
            product_quality=unknown_category("product quality"),
            patient_safety=unknown_category("patient safety"),
            process=unknown_category("process"),
            regulatory=unknown_category("regulatory"),
            data_integrity=unknown_category("data integrity"),
            batch_product=unknown_category("batch/product"),
            overall_summary="The supplied source did not contain enough detail for a confident impact assessment.",
        ),
        severity=SeverityRecommendation(
            recommended_level="unknown",
            confidence=None,
            reason="Insufficient evidence in the supplied source to recommend a severity level with confidence.",
            evidence=[],
        ),
        missing_information=[
            "Batch/Lot Number",
            "Exact event time",
            "Department/Area",
            "Process parameter and expected/actual values",
        ],
    )


def _pick_response(source_text: str) -> AiOutputSchema:
    length = len((source_text or "").strip())
    return _rich_response(source_text) if length > 40 else _sparse_response()


class StubAiService(AiService):
    async def analyze_text(self, text: str, source_type: str = "text") -> AiOutputSchema:
        logger.info("StubAiService.analyze_text called (source_type=%s, len=%d)", source_type, len(text or ""))
        return _pick_response(text)

    async def analyze_document(self, raw_text: str, filename: str, source_type: str) -> AiOutputSchema:
        logger.info(
            "StubAiService.analyze_document called (filename=%s, source_type=%s, len=%d)",
            filename,
            source_type,
            len(raw_text or ""),
        )
        return _pick_response(raw_text)
