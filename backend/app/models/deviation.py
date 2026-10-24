"""ORM model for a saved (reviewed) deviation record."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def _new_deviation_id() -> str:
    # Human-friendly, still unique enough for the MVP: DEV-<year>-<short uuid>
    year = datetime.now(timezone.utc).year
    return f"DEV-{year}-{uuid.uuid4().hex[:6].upper()}"


class Deviation(Base):
    __tablename__ = "deviations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_new_deviation_id)

    title: Mapped[str] = mapped_column(String(500), nullable=False)
    event_datetime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reported_datetime: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manufacturing_stage: Mapped[str | None] = mapped_column(String(255), nullable=True)
    batch_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    process_parameter: Mapped[str | None] = mapped_column(String(255), nullable=True)
    expected_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actual_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    immediate_action: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Stored as JSON blobs — structure is validated at the API boundary by
    # ImpactAssessment / SeverityLevel, so we don't need relational columns
    # for each impact category in the MVP.
    impact_assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    final_severity: Mapped[str | None] = mapped_column(String(32), nullable=True)

    source_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_filename: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
