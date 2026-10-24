"""
Persistence logic for saved deviations. Routes call into this module
rather than touching the ORM/session directly, so the DB access pattern
can change (e.g. add pagination, filters, soft deletes) without touching
app/api/.
"""
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import DatabaseError, DeviationNotFoundError
from app.models.deviation import Deviation
from app.schemas.deviation import SaveDeviationRequest

logger = logging.getLogger(__name__)


def create_deviation(db: Session, payload: SaveDeviationRequest) -> Deviation:
    record = Deviation(
        title=payload.title,
        event_datetime=payload.event_datetime,
        reported_datetime=payload.reported_datetime,
        department=payload.department,
        manufacturing_stage=payload.manufacturing_stage,
        batch_number=payload.batch_number,
        description=payload.description,
        expected_condition=payload.expected_condition,
        actual_condition=payload.actual_condition,
        process_parameter=payload.process_parameter,
        expected_value=payload.expected_value,
        actual_value=payload.actual_value,
        immediate_action=payload.immediate_action,
        impact_assessment=payload.impact_assessment.model_dump() if payload.impact_assessment else None,
        final_severity=payload.final_severity.value if payload.final_severity else None,
        source_type=payload.source_type.value if payload.source_type else None,
        source_filename=payload.source_filename,
    )
    try:
        db.add(record)
        db.commit()
        db.refresh(record)
        return record
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("Failed to save deviation")
        raise DatabaseError("The deviation could not be saved. Please try again.") from exc


def get_deviation(db: Session, deviation_id: str) -> Deviation:
    record = db.get(Deviation, deviation_id)
    if record is None:
        raise DeviationNotFoundError(f"No deviation found with id '{deviation_id}'.")
    return record


def list_deviations(db: Session, limit: int = 50, offset: int = 0) -> tuple[list[Deviation], int]:
    items = (
        db.execute(select(Deviation).order_by(Deviation.created_at.desc()).offset(offset).limit(limit))
        .scalars()
        .all()
    )
    total_count = db.execute(select(func.count()).select_from(Deviation)).scalar_one()
    return list(items), total_count
