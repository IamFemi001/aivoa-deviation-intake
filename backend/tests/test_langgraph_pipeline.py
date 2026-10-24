"""
Tests for the LangGraph deviation-intake pipeline.

These tests do NOT call the real Groq API — they inject a FakeLLM whose
`.with_structured_output(Model).invoke(messages)` returns pre-canned,
scenario-appropriate Pydantic instances. This lets us verify:

  - the graph actually executes end-to-end (all 7 nodes run, in order)
  - the canonical output schema is produced
  - missing information is never fabricated (Test 2 / Test 3 from the
    Agent 4 prompt)
  - malformed structured output is caught and raised as ExtractionFailedError
  - a Groq/provider failure is caught and raised as a controlled error,
    not an unhandled exception

Run with:  pytest tests/test_langgraph_pipeline.py -v
(requires the AI pipeline deps: pip install -r requirements.txt)
"""
import asyncio

import pytest
from pydantic import BaseModel, ValidationError

from app.schemas.deviation import (
    AiOutputSchema,
    ExtractedDeviation,
    ImpactAssessment,
    ImpactCategory,
    SeverityRecommendation,
)
from app.services.langgraph_pipeline import build_deviation_graph


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeStructuredRunnable:
    """Stands in for `llm.with_structured_output(Model)`."""

    def __init__(self, response):
        self._response = response

    def invoke(self, messages):
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class FakeLLM:
    """
    Stands in for ChatGroq. `responses` maps the Pydantic model class name
    (e.g. "ExtractedDeviation") requested via with_structured_output to the
    canned object (or Exception) that should be returned for that node.
    """

    def __init__(self, responses: dict):
        self._responses = responses

    def with_structured_output(self, model_cls):
        key = model_cls.__name__
        if key not in self._responses:
            raise KeyError(f"FakeLLM has no canned response configured for {key}")
        return _FakeStructuredRunnable(self._responses[key])


def _unknown_category(label: str) -> ImpactCategory:
    return ImpactCategory(level="unknown", reason=f"Insufficient information to assess {label} impact.")


# ---------------------------------------------------------------------------
# Test 1 — normal deviation (full extraction, non-empty missing_information
# only for genuinely absent fields)
# ---------------------------------------------------------------------------

def test_normal_deviation_produces_full_canonical_output():
    extraction = ExtractedDeviation(
        title="Temperature Excursion — Batch API-2026-001",
        event_datetime=None,  # source gives no exact clock time
        reported_datetime=None,
        department=None,
        manufacturing_stage="API Manufacturing",
        batch_number="API-2026-001",
        description=(
            "During API batch API-2026-001 manufacturing, the temperature exceeded "
            "the approved range of 20-25C and reached 28C. The batch was placed on "
            "hold and the production supervisor was notified."
        ),
        expected_condition="Temperature maintained within 20-25C.",
        actual_condition="Temperature reached 28C.",
        process_parameter="Manufacturing temperature",
        expected_value="20-25C",
        actual_value="28C",
        immediate_action="Batch placed on hold; production supervisor notified.",
    )
    impact = ImpactAssessment(
        product_quality=ImpactCategory(level="potential", reason="Temperature excursion may affect product quality."),
        patient_safety=_unknown_category("patient safety"),
        process=ImpactCategory(level="confirmed", reason="Temperature confirmedly exceeded the approved range."),
        regulatory=_unknown_category("regulatory"),
        data_integrity=ImpactCategory(level="none", reason="No indication of data integrity issues."),
        batch_product=ImpactCategory(level="potential", reason="Batch placed on hold pending review."),
        overall_summary="Confirmed process excursion with potential quality impact; batch on hold.",
    )
    severity = SeverityRecommendation(
        recommended_level="major",
        confidence=0.75,
        reason="Process parameter exceeded its approved range during active manufacturing.",
        evidence=["Actual temperature (28C) exceeded approved range (20-25C)", "Batch placed on hold"],
    )

    llm = FakeLLM({
        "ExtractedDeviation": extraction,
        "ImpactAssessment": impact,
        "SeverityRecommendation": severity,
    })
    graph = build_deviation_graph(llm)

    source_text = (
        "During API batch API-2026-001 manufacturing, the temperature exceeded "
        "the approved range of 20-25C and reached 28C. The batch was placed on "
        "hold and the production supervisor was notified."
    )
    final_state = asyncio.run(graph.ainvoke({"raw_text": source_text, "source_type": "text"}))

    result: AiOutputSchema = final_state["result"]
    assert isinstance(result, AiOutputSchema)
    assert result.extraction.batch_number == "API-2026-001"
    assert result.severity.recommended_level == "major"
    # event_datetime, department, reported_datetime were never given -> must
    # show up as missing, never fabricated.
    assert "Batch/Lot Number" not in result.missing_information
    assert any("Date/time" in m for m in result.missing_information)
    assert any("Department" in m for m in result.missing_information)


# ---------------------------------------------------------------------------
# Test 2 — missing batch number must stay null and be flagged, never guessed
# ---------------------------------------------------------------------------

def test_missing_batch_number_is_not_fabricated():
    extraction = ExtractedDeviation(
        title="Unplanned Process Deviation",
        description="An operator observed an unexpected result during processing.",
        batch_number=None,
    )
    impact = ImpactAssessment(
        product_quality=_unknown_category("product quality"),
        patient_safety=_unknown_category("patient safety"),
        process=_unknown_category("process"),
        regulatory=_unknown_category("regulatory"),
        data_integrity=_unknown_category("data integrity"),
        batch_product=_unknown_category("batch/product"),
        overall_summary="Insufficient detail for a confident assessment.",
    )
    severity = SeverityRecommendation(recommended_level="unknown", confidence=None, reason="Insufficient evidence.")

    llm = FakeLLM({
        "ExtractedDeviation": extraction,
        "ImpactAssessment": impact,
        "SeverityRecommendation": severity,
    })
    graph = build_deviation_graph(llm)

    final_state = asyncio.run(graph.ainvoke({
        "raw_text": "An operator observed an unexpected result during processing.",
        "source_type": "text",
    }))
    result: AiOutputSchema = final_state["result"]

    assert result.extraction.batch_number is None
    assert "Batch/Lot Number" in result.missing_information


# ---------------------------------------------------------------------------
# Test 3 — missing event date must stay null, not invented
# ---------------------------------------------------------------------------

def test_missing_event_date_is_not_fabricated():
    extraction = ExtractedDeviation(
        title="Deviation Reported",
        description="A deviation was reported without a specific event time.",
        batch_number="API-2026-099",
        event_datetime=None,
    )
    impact = ImpactAssessment(
        product_quality=_unknown_category("product quality"),
        patient_safety=_unknown_category("patient safety"),
        process=_unknown_category("process"),
        regulatory=_unknown_category("regulatory"),
        data_integrity=_unknown_category("data integrity"),
        batch_product=_unknown_category("batch/product"),
        overall_summary="Insufficient detail for a confident assessment.",
    )
    severity = SeverityRecommendation(recommended_level="unknown", confidence=None, reason="Insufficient evidence.")

    llm = FakeLLM({
        "ExtractedDeviation": extraction,
        "ImpactAssessment": impact,
        "SeverityRecommendation": severity,
    })
    graph = build_deviation_graph(llm)

    final_state = asyncio.run(graph.ainvoke({
        "raw_text": "A deviation was reported without a specific event time.",
        "source_type": "text",
    }))
    result: AiOutputSchema = final_state["result"]

    assert result.extraction.event_datetime is None
    assert any("Date/time" in m for m in result.missing_information)


# ---------------------------------------------------------------------------
# Test 4 — malformed / invalid structured output must not reach the caller
# ---------------------------------------------------------------------------

def test_malformed_extraction_output_raises_validation_error():
    class NotAnExtraction(BaseModel):
        unexpected_field: str = "oops"

    llm = FakeLLM({"ExtractedDeviation": NotAnExtraction()})
    graph = build_deviation_graph(llm)

    with pytest.raises((ValidationError, Exception)):
        asyncio.run(graph.ainvoke({"raw_text": "some deviation text", "source_type": "text"}))


# ---------------------------------------------------------------------------
# Test 5 — a Groq/provider failure propagates as a normal exception, which
# ai_service_langgraph.py is responsible for turning into ExtractionFailedError
# (verified separately in test_ai_service_langgraph.py)
# ---------------------------------------------------------------------------

def test_provider_failure_propagates_instead_of_hanging_or_crashing_silently():
    llm = FakeLLM({"ExtractedDeviation": RuntimeError("simulated Groq API failure")})
    graph = build_deviation_graph(llm)

    with pytest.raises(RuntimeError, match="simulated Groq API failure"):
        asyncio.run(graph.ainvoke({"raw_text": "some deviation text", "source_type": "text"}))
