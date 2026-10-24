"""
LangGraph pipeline for the AI Deviation Intake workflow.

Graph shape (see Agent 4 prompt, section 7):

    START
      -> receive_source
      -> extract_deviation
      -> validate_extraction
      -> assess_impact
      -> recommend_severity
      -> identify_missing_information
      -> format_response
      -> END

Each LLM-backed node calls Groq (via langchain_groq's ChatGroq) with
`.with_structured_output(...)` against the exact Pydantic models already
defined in app/schemas/deviation.py, so a malformed model response fails
fast as a validation error rather than reaching the frontend as bad JSON.

This module has no FastAPI/HTTP concerns — it is imported and driven by
app/services/ai_service_langgraph.py, which is the only place that
translates graph failures into the app's AppError hierarchy.
"""
from __future__ import annotations

import logging
from typing import Any, Optional, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

from app.schemas.deviation import (
    AiOutputSchema,
    ExtractedDeviation,
    ImpactAssessment,
    ImpactCategory,
    SeverityRecommendation,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------

class DeviationGraphState(TypedDict, total=False):
    raw_text: str
    source_type: str
    extraction: ExtractedDeviation
    impact_assessment: ImpactAssessment
    severity: SeverityRecommendation
    missing_information: list[str]
    result: AiOutputSchema


# ---------------------------------------------------------------------------
# Shared instructions — repeated in every extraction/assessment prompt so
# each node independently resists fabrication (section 9 / 10 / 11).
# ---------------------------------------------------------------------------

_NO_FABRICATION_RULE = (
    "Only use information that is explicitly present in, or directly and "
    "unambiguously inferable from, the SOURCE TEXT below. Never invent, "
    "assume, or guess a date, batch number, department, value, or fact "
    "that is not supported by the source text. If a piece of information "
    "is not present, you MUST represent it as null (for scalar fields) or "
    "as \"unknown\" (for impact levels / severity), never as a plausible "
    "guess."
)


def _source_block(raw_text: str) -> str:
    return f"SOURCE TEXT:\n\"\"\"\n{raw_text.strip()}\n\"\"\""


# ---------------------------------------------------------------------------
# Node 1 — receive_source
# ---------------------------------------------------------------------------

def receive_source_node(state: DeviationGraphState) -> dict:
    """
    Normalizes the incoming text. The AI layer never reads raw file bytes —
    by the time text reaches this graph it has already been converted to
    plain text by app/services/document_extraction.py (uploads) or comes
    directly from the pasted-text/email request body.
    """
    raw_text = (state.get("raw_text") or "").strip()
    source_type = state.get("source_type") or "text"
    logger.info("receive_source: source_type=%s, chars=%d", source_type, len(raw_text))
    return {"raw_text": raw_text, "source_type": source_type}


# ---------------------------------------------------------------------------
# Node 2 — extract_deviation
# ---------------------------------------------------------------------------

_EXTRACTION_SYSTEM_PROMPT = (
    "You are a pharmaceutical quality-systems assistant extracting structured "
    "deviation-report data for an API (active pharmaceutical ingredient) "
    "manufacturer. " + _NO_FABRICATION_RULE + "\n\n"
    "Return the response as valid JSON matching the requested schema. "
    "Extract exactly these fields: title, event_datetime (ISO-8601 if a date/"
    "time is given, else null), reported_datetime (ISO-8601 if given, else "
    "null), department, manufacturing_stage, batch_number, description, "
    "expected_condition, actual_condition, process_parameter, expected_value, "
    "actual_value, immediate_action. Write description, expected_condition, "
    "actual_condition and immediate_action as concise, factual, professional "
    "sentences drawn only from the source text."
)


def make_extract_node(llm):
    structured_llm = llm.with_structured_output(ExtractedDeviation, method="json_mode")

    def extract_deviation_node(state: DeviationGraphState) -> dict:
        raw_text = state.get("raw_text", "")
        messages = [
            SystemMessage(content=_EXTRACTION_SYSTEM_PROMPT),
            HumanMessage(content=_source_block(raw_text)),
        ]
        extraction = structured_llm.invoke(messages)
        if not isinstance(extraction, ExtractedDeviation):
            extraction = ExtractedDeviation.model_validate(extraction)
        logger.info("extract_deviation: extraction produced")
        return {"extraction": extraction}

    return extract_deviation_node


# ---------------------------------------------------------------------------
# Node 3 — validate_extraction
# ---------------------------------------------------------------------------

def validate_extraction_node(state: DeviationGraphState) -> dict:
    """
    Structural safety net: re-validates the extraction against the Pydantic
    model (catching anything a future node-swap might let through) and
    strips obvious fabrication artifacts such as placeholder strings some
    models emit instead of null (e.g. "N/A", "unknown", "not specified").
    """
    extraction = state.get("extraction")
    if extraction is None:
        raise ValueError("validate_extraction: no extraction produced by extract_deviation node.")

    extraction = ExtractedDeviation.model_validate(extraction)

    placeholder_values = {"n/a", "na", "unknown", "not specified", "none", "not provided", ""}
    cleaned = extraction.model_dump()
    for field, value in cleaned.items():
        if isinstance(value, str) and value.strip().lower() in placeholder_values:
            cleaned[field] = None
    validated = ExtractedDeviation.model_validate(cleaned)

    logger.info("validate_extraction: ok")
    return {"extraction": validated}


# ---------------------------------------------------------------------------
# Node 4 — assess_impact
# ---------------------------------------------------------------------------

_IMPACT_SYSTEM_PROMPT = (
    "Return the response as valid JSON matching the requested schema. "
    "You are a pharmaceutical quality-systems assistant performing an initial "
    "impact assessment of a manufacturing deviation for an API manufacturer. "
    + _NO_FABRICATION_RULE + "\n\n"
    "Assess these six categories: product_quality, patient_safety, process, "
    "regulatory, data_integrity, batch_product. For each, choose a level of "
    "exactly one of: none, potential, confirmed, unknown — and give a short, "
    "specific reason grounded in the source text. Use \"unknown\" whenever "
    "the source text does not give you enough evidence to judge that "
    "category with confidence; do not default to \"none\" just because "
    "nothing was mentioned. Then write a concise overall_summary (2-3 "
    "sentences) synthesizing the six judgments. Do not make definitive "
    "pharmaceutical, clinical, or regulatory determinations — this is a "
    "preliminary assessment for human quality-team review."
)


def make_impact_node(llm):
    structured_llm = llm.with_structured_output(ImpactAssessment, method="json_mode")

    def assess_impact_node(state: DeviationGraphState) -> dict:
        raw_text = state.get("raw_text", "")
        extraction: ExtractedDeviation = state["extraction"]
        prompt = (
            f"{_source_block(raw_text)}\n\n"
            f"EXTRACTED DEVIATION DATA (for context; already reviewed):\n"
            f"{extraction.model_dump_json(indent=2)}"
        )
        messages = [
            SystemMessage(content=_IMPACT_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        impact = structured_llm.invoke(messages)
        if not isinstance(impact, ImpactAssessment):
            impact = ImpactAssessment.model_validate(impact)
        logger.info("assess_impact: impact assessment produced")
        return {"impact_assessment": impact}

    return assess_impact_node


# ---------------------------------------------------------------------------
# Node 5 — recommend_severity
# ---------------------------------------------------------------------------

_SEVERITY_SYSTEM_PROMPT = (
    "Return the response as valid JSON matching the requested schema. "
    "You are a pharmaceutical quality-systems assistant proposing an INITIAL "
    "severity classification for a manufacturing deviation, for a human "
    "quality reviewer to confirm, edit, or override. " + _NO_FABRICATION_RULE + "\n\n"
    "Choose recommended_level as exactly one of: minor, major, critical, "
    "unknown. Provide confidence as a number between 0 and 1 reflecting how "
    "well-supported the source text is (or null if you cannot meaningfully "
    "estimate it), a short reason, and a list of concrete evidence strings "
    "drawn directly from the source text and the extraction/impact data. "
    "Use \"unknown\" rather than guessing when the evidence is insufficient. "
    "This is a recommendation only — never phrase it as a final, official, "
    "or regulatory determination."
)


def make_severity_node(llm):
    structured_llm = llm.with_structured_output(SeverityRecommendation, method="json_mode")

    def recommend_severity_node(state: DeviationGraphState) -> dict:
        raw_text = state.get("raw_text", "")
        extraction: ExtractedDeviation = state["extraction"]
        impact: ImpactAssessment = state["impact_assessment"]
        prompt = (
            f"{_source_block(raw_text)}\n\n"
            f"EXTRACTED DEVIATION DATA:\n{extraction.model_dump_json(indent=2)}\n\n"
            f"IMPACT ASSESSMENT:\n{impact.model_dump_json(indent=2)}"
        )
        messages = [
            SystemMessage(content=_SEVERITY_SYSTEM_PROMPT),
            HumanMessage(content=prompt),
        ]
        severity = structured_llm.invoke(messages)
        if not isinstance(severity, SeverityRecommendation):
            severity = SeverityRecommendation.model_validate(severity)
        logger.info("recommend_severity: severity=%s", severity.recommended_level)
        return {"severity": severity}

    return recommend_severity_node


# ---------------------------------------------------------------------------
# Node 6 — identify_missing_information (pure Python, no LLM call needed)
# ---------------------------------------------------------------------------

_REQUIRED_FIELD_LABELS: list[tuple[str, str]] = [
    ("event_datetime", "Date/time the deviation occurred"),
    ("department", "Department / area"),
    ("manufacturing_stage", "Manufacturing stage"),
    ("batch_number", "Batch/Lot Number"),
    ("description", "Detailed description of what happened"),
    ("process_parameter", "Process parameter involved"),
    ("expected_value", "Expected value/range for the process parameter"),
    ("actual_value", "Actual observed value"),
    ("immediate_action", "Immediate action taken"),
]


def identify_missing_information_node(state: DeviationGraphState) -> dict:
    extraction: ExtractedDeviation = state["extraction"]
    data = extraction.model_dump()
    missing = [label for field, label in _REQUIRED_FIELD_LABELS if not data.get(field)]
    logger.info("identify_missing_information: %d field(s) missing", len(missing))
    return {"missing_information": missing}


# ---------------------------------------------------------------------------
# Node 7 — format_response
# ---------------------------------------------------------------------------

def format_response_node(state: DeviationGraphState) -> dict:
    result = AiOutputSchema(
        extraction=state["extraction"],
        impact_assessment=state["impact_assessment"],
        severity=state["severity"],
        missing_information=state.get("missing_information", []),
    )
    return {"result": result}


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_deviation_graph(llm) -> Any:
    """Builds and compiles the LangGraph StateGraph described above."""
    graph = StateGraph(DeviationGraphState)

    graph.add_node("receive_source", receive_source_node)
    graph.add_node("extract_deviation", make_extract_node(llm))
    graph.add_node("validate_extraction", validate_extraction_node)
    graph.add_node("assess_impact", make_impact_node(llm))
    graph.add_node("recommend_severity", make_severity_node(llm))
    graph.add_node("identify_missing_information", identify_missing_information_node)
    graph.add_node("format_response", format_response_node)

    graph.set_entry_point("receive_source")
    graph.add_edge("receive_source", "extract_deviation")
    graph.add_edge("extract_deviation", "validate_extraction")
    graph.add_edge("validate_extraction", "assess_impact")
    graph.add_edge("assess_impact", "recommend_severity")
    graph.add_edge("recommend_severity", "identify_missing_information")
    graph.add_edge("identify_missing_information", "format_response")
    graph.add_edge("format_response", END)

    return graph.compile()
