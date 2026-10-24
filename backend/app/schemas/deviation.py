"""
Pydantic models for the Deviation Intake API.

These mirror, field for field, the "Exact AI Output Schema" and "Save API"
contracts already implemented on the frontend
(frontend/src/types/deviation.js and frontend/src/utils/buildSaveRecord.js).
Do not rename fields here without updating the frontend — this is the
stable JSON contract both sides were built against.
"""
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SourceType(str, Enum):
    text = "text"
    email = "email"
    pdf = "pdf"
    txt = "txt"


class ImpactLevel(str, Enum):
    none = "none"
    potential = "potential"
    confirmed = "confirmed"
    unknown = "unknown"


class SeverityLevel(str, Enum):
    minor = "minor"
    major = "major"
    critical = "critical"
    unknown = "unknown"


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Body for POST /api/deviations/analyze (pasted text or email)."""

    source_type: SourceType = SourceType.text
    text: str = Field(..., min_length=1, description="Pasted deviation text or email content")

    @field_validator("text")
    @classmethod
    def text_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("text must not be blank")
        return v


# ---------------------------------------------------------------------------
# Shared AI-output building blocks
# ---------------------------------------------------------------------------

class ExtractedDeviation(BaseModel):
    """The 'extraction' block — fields the AI Copilot populates on the form."""

    title: Optional[str] = None
    event_datetime: Optional[str] = None
    reported_datetime: Optional[str] = None
    department: Optional[str] = None
    manufacturing_stage: Optional[str] = None
    batch_number: Optional[str] = None
    description: Optional[str] = None
    expected_condition: Optional[str] = None
    actual_condition: Optional[str] = None
    process_parameter: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    immediate_action: Optional[str] = None


class ImpactCategory(BaseModel):
    level: ImpactLevel = ImpactLevel.unknown
    reason: str = ""


class ImpactAssessment(BaseModel):
    product_quality: ImpactCategory
    patient_safety: ImpactCategory
    process: ImpactCategory
    regulatory: ImpactCategory
    data_integrity: ImpactCategory
    batch_product: ImpactCategory
    overall_summary: str = ""


class SeverityRecommendation(BaseModel):
    recommended_level: SeverityLevel = SeverityLevel.unknown
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reason: str = ""
    evidence: List[str] = Field(default_factory=list)


class AiOutputSchema(BaseModel):
    """
    The full payload returned by both analyze endpoints, exactly matching
    frontend AiOutputSchema. Returned to the client wrapped as
    { "data": AiOutputSchema } by AnalyzeResponse below.
    """

    extraction: ExtractedDeviation
    impact_assessment: ImpactAssessment
    severity: SeverityRecommendation
    missing_information: List[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    """Top-level response envelope for both /analyze endpoints."""

    success: bool = True
    data: AiOutputSchema


# ---------------------------------------------------------------------------
# Save (create) models
# ---------------------------------------------------------------------------

class SaveDeviationRequest(BaseModel):
    """
    Body for POST /api/deviations — the exact shape produced by
    frontend/src/utils/buildSaveRecord.js after user review.
    """

    title: str = Field(..., min_length=1)
    event_datetime: Optional[str] = None
    reported_datetime: Optional[str] = None
    department: Optional[str] = None
    manufacturing_stage: Optional[str] = None
    batch_number: Optional[str] = None
    description: Optional[str] = None
    expected_condition: Optional[str] = None
    actual_condition: Optional[str] = None
    process_parameter: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    immediate_action: Optional[str] = None

    impact_assessment: Optional[ImpactAssessment] = None
    final_severity: Optional[SeverityLevel] = None

    source_type: Optional[SourceType] = None
    source_filename: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("title must not be blank")
        return v


class SaveDeviationResponse(BaseModel):
    """Response for POST /api/deviations, matching the documented save contract."""

    success: bool = True
    deviation_id: str
    message: str = "Deviation saved successfully"


# ---------------------------------------------------------------------------
# Read models
# ---------------------------------------------------------------------------

class DeviationResponse(BaseModel):
    """Response for GET /api/deviations/{id} and the list endpoint."""

    id: str
    title: str
    event_datetime: Optional[str] = None
    reported_datetime: Optional[str] = None
    department: Optional[str] = None
    manufacturing_stage: Optional[str] = None
    batch_number: Optional[str] = None
    description: Optional[str] = None
    expected_condition: Optional[str] = None
    actual_condition: Optional[str] = None
    process_parameter: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    immediate_action: Optional[str] = None

    impact_assessment: Optional[ImpactAssessment] = None
    final_severity: Optional[SeverityLevel] = None

    source_type: Optional[SourceType] = None
    source_filename: Optional[str] = None

    created_at: datetime

    model_config = {"from_attributes": True}


class DeviationListResponse(BaseModel):
    items: List[DeviationResponse]
    total: int
