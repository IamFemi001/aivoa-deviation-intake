"""
Database integration tests for the persistence layer added around the
existing FastAPI backend.

These tests do NOT require a running PostgreSQL server. They cover:

  1. DATABASE_URL / settings parsing (including a Postgres-shaped URL).
  2. Engine/dialect selection for sqlite vs. postgres URLs.
  3. A full functional round-trip (create -> get -> list) run against a
     throwaway SQLite database, exercising the exact same SQLAlchemy
     model/service code that would run against Postgres.
  4. Rollback + controlled error handling when the underlying commit
     fails.

A real PostgreSQL connection is exercised separately — see the
"Remaining manual test" note in the project handoff/report, not in this
file — since no live Postgres instance is available in this environment.
"""
import os
import tempfile
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


# ---------------------------------------------------------------------------
# 1. Settings / DATABASE_URL parsing
# ---------------------------------------------------------------------------

def test_settings_reads_postgres_url_from_env(monkeypatch):
    """A Postgres-shaped DATABASE_URL is picked up as-is, with no rewriting."""
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://aivoa:secret@db.example.com:5432/aivoa_deviations",
    )
    # Import locally so the env var above is in place before Settings() reads it.
    from app.core.config import Settings

    settings = Settings(_env_file=None)  # ignore any local .env for this test
    assert settings.DATABASE_URL == (
        "postgresql+psycopg2://aivoa:secret@db.example.com:5432/aivoa_deviations"
    )


def test_settings_accepts_explicit_sqlite_url_for_isolated_tests():
    """SQLite remains usable when explicitly supplied to isolated tests."""
    from app.core.config import Settings

    settings = Settings(_env_file=None, DATABASE_URL="sqlite:///./deviations.db")
    assert settings.DATABASE_URL.startswith("sqlite")


# ---------------------------------------------------------------------------
# 2. Engine/dialect selection (no actual network connection required —
#    create_engine() with psycopg2 does not connect until first use)
# ---------------------------------------------------------------------------

def test_engine_uses_postgres_dialect_for_postgres_url():
    engine = create_engine(
        "postgresql+psycopg2://aivoa:secret@localhost:5432/aivoa_deviations"
    )
    assert engine.dialect.name == "postgresql"
    assert engine.dialect.driver == "psycopg2"


def test_engine_uses_sqlite_dialect_for_sqlite_url():
    engine = create_engine("sqlite:///./should_not_be_created.db", connect_args={"check_same_thread": False})
    try:
        assert engine.dialect.name == "sqlite"
    finally:
        engine.dispose()
        Path("./should_not_be_created.db").unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# 3. Functional persistence round-trip
#
#    Runs against a fresh temp-file SQLite DB rather than the real Postgres
#    server (none is available in this sandbox), but goes through the exact
#    same ORM model (app/models/deviation.py) and service functions
#    (app/services/deviation_service.py) that will run unchanged against
#    Postgres — only the engine's DATABASE_URL differs.
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    from app.database.session import Base

    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test_deviations.db")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})

    # Import models so they register on Base before create_all.
    from app.models import deviation  # noqa: F401

    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _sample_save_request():
    from app.schemas.deviation import (
        ImpactAssessment,
        ImpactCategory,
        SaveDeviationRequest,
        SeverityLevel,
        SourceType,
    )

    return SaveDeviationRequest(
        title="Process Parameter Excursion — Batch API-2026-014",
        event_datetime="2026-09-24T03:15:00Z",
        reported_datetime="2026-09-26T07:00:00+00:00",
        department="API Manufacturing",
        manufacturing_stage="Crystallization",
        batch_number="API-2026-014",
        description="Crystallizer temperature exceeded the hold limit.",
        expected_condition="18-22C during hold",
        actual_condition="27C for ~40 minutes",
        process_parameter="Crystallizer hold temperature",
        expected_value="18-22C",
        actual_value="27C",
        immediate_action="Batch quarantined; QA notified.",
        impact_assessment=ImpactAssessment(
            product_quality=ImpactCategory(level="potential", reason="Thermal excursion may affect crystal form."),
            patient_safety=ImpactCategory(level="none", reason="No safety-critical parameter affected."),
            process=ImpactCategory(level="confirmed", reason="Hold temperature limit was exceeded."),
            regulatory=ImpactCategory(level="potential", reason="May require regulatory notification."),
            data_integrity=ImpactCategory(level="none", reason="Logging system unaffected."),
            batch_product=ImpactCategory(level="potential", reason="Batch quarantined pending investigation."),
            overall_summary="Process excursion with potential product quality impact.",
        ),
        final_severity=SeverityLevel.major,
        source_type=SourceType.text,
        source_filename=None,
    )


def test_create_and_get_deviation_round_trip(db_session):
    from app.services.deviation_service import create_deviation, get_deviation

    payload = _sample_save_request()
    created = create_deviation(db_session, payload)

    assert created.id.startswith("DEV-")
    assert created.created_at is not None

    fetched = get_deviation(db_session, created.id)
    assert fetched.title == payload.title
    assert fetched.batch_number == "API-2026-014"
    assert fetched.final_severity == "major"
    assert fetched.source_type == "text"

    # JSON impact assessment persists and round-trips as a plain dict.
    assert fetched.impact_assessment["overall_summary"] == (
        "Process excursion with potential product quality impact."
    )
    assert fetched.impact_assessment["process"]["level"] == "confirmed"


def test_list_deviations_returns_saved_record(db_session):
    from app.services.deviation_service import create_deviation, list_deviations

    create_deviation(db_session, _sample_save_request())
    items, total = list_deviations(db_session)

    assert total == 1
    assert len(items) == 1
    assert items[0].title == _sample_save_request().title


def test_get_deviation_not_found_raises(db_session):
    from app.core.errors import DeviationNotFoundError
    from app.services.deviation_service import get_deviation

    with pytest.raises(DeviationNotFoundError):
        get_deviation(db_session, "DEV-DOES-NOT-EXIST")


# ---------------------------------------------------------------------------
# 4. Rollback / controlled error handling
# ---------------------------------------------------------------------------

def test_create_deviation_rolls_back_and_raises_database_error(db_session, monkeypatch):
    from app.core.errors import DatabaseError
    from app.services import deviation_service

    def _boom():
        raise RuntimeError("simulated DB failure (e.g. connection dropped)")

    monkeypatch.setattr(db_session, "commit", _boom)
    rollback_calls = []
    monkeypatch.setattr(db_session, "rollback", lambda: rollback_calls.append(True))

    with pytest.raises(DatabaseError) as exc_info:
        deviation_service.create_deviation(db_session, _sample_save_request())

    # Rolled back exactly once, and the raw RuntimeError never reaches the caller.
    assert rollback_calls == [True]
    assert "could not be saved" in str(exc_info.value)
