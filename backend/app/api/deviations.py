"""
Deviation Intake routes.

    POST /api/deviations/analyze        pasted text/email -> AI output
    POST /api/deviations/analyze-file   uploaded PDF/TXT   -> AI output
    POST /api/deviations                save reviewed deviation
    GET  /api/deviations                list saved deviations (testing/demo)
    GET  /api/deviations/{id}           fetch one saved deviation

Routes stay thin: request validation (via Pydantic), call a service, shape
the response. All extraction/AI/DB logic lives in app/services/.
"""
import logging

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import EmptySourceError, FileTooLargeError, InvalidFileError, UnsupportedFileTypeError
from app.database.session import get_db
from app.schemas.deviation import (
    AnalyzeRequest,
    AnalyzeResponse,
    DeviationListResponse,
    DeviationResponse,
    SaveDeviationRequest,
    SaveDeviationResponse,
)
from app.services.ai_service import AiService, get_ai_service
from app.services.deviation_service import create_deviation, get_deviation, list_deviations
from app.services.document_extraction import extract_text_from_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deviations", tags=["deviations"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(
    payload: AnalyzeRequest,
    ai_service: AiService = Depends(get_ai_service),
) -> AnalyzeResponse:
    """Analyze pasted deviation text or email content."""
    if not payload.text or not payload.text.strip():
        raise EmptySourceError("Paste some deviation text or an email before analyzing.")

    result = await ai_service.analyze_text(payload.text, source_type=payload.source_type.value)
    return AnalyzeResponse(data=result)


@router.post("/analyze-file", response_model=AnalyzeResponse)
async def analyze_file(
    file: UploadFile = File(...),
    ai_service: AiService = Depends(get_ai_service),
    settings: Settings = Depends(get_settings),
) -> AnalyzeResponse:
    """Analyze an uploaded deviation document (PDF or TXT for the MVP)."""
    if not file or not file.filename:
        raise InvalidFileError("No file was provided.")

    filename = file.filename
    lower_name = filename.lower()
    allowed = settings.allowed_upload_extensions_list
    if not any(lower_name.endswith(ext) for ext in allowed):
        raise UnsupportedFileTypeError(f"Only {', '.join(allowed)} files are supported.")

    content = await file.read()
    if len(content) == 0:
        raise InvalidFileError("The uploaded file is empty.")
    if len(content) > settings.max_upload_size_bytes:
        raise FileTooLargeError(f"File exceeds the {settings.MAX_UPLOAD_SIZE_MB}MB size limit.")

    raw_text = extract_text_from_upload(filename, content, file.content_type)
    if not raw_text.strip():
        raise EmptySourceError("No readable text was found in the uploaded document.")

    source_type = "pdf" if lower_name.endswith(".pdf") else "txt"
    result = await ai_service.analyze_document(raw_text, filename=filename, source_type=source_type)
    return AnalyzeResponse(data=result)


@router.post("", response_model=SaveDeviationResponse, status_code=201)
async def save_deviation(
    payload: SaveDeviationRequest,
    db: Session = Depends(get_db),
) -> SaveDeviationResponse:
    """Persist the user-reviewed deviation record."""
    record = create_deviation(db, payload)
    logger.info("Saved deviation %s", record.id)
    return SaveDeviationResponse(deviation_id=record.id, message="Deviation saved successfully")


@router.get("", response_model=DeviationListResponse)
async def get_deviations(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> DeviationListResponse:
    """List saved deviations, most recent first. Primarily for testing/demo."""
    items, total = list_deviations(db, limit=limit, offset=offset)
    return DeviationListResponse(items=[DeviationResponse.model_validate(i) for i in items], total=total)


@router.get("/{deviation_id}", response_model=DeviationResponse)
async def get_deviation_by_id(
    deviation_id: str,
    db: Session = Depends(get_db),
) -> DeviationResponse:
    """Fetch a single saved deviation by id."""
    record = get_deviation(db, deviation_id)
    return DeviationResponse.model_validate(record)
