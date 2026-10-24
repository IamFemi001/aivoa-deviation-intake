"""SQLAlchemy engine/session wiring. One place owns the DB connection."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

settings = get_settings()

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# check_same_thread is only needed by SQLite tests/local fallback scenarios;
# it doesn't apply to Postgres/MySQL, so it is scoped to the sqlite branch.
connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    # Recycles connections that the DB server (or a proxy/load balancer in
    # front of it) may have silently dropped while idle. A no-op for SQLite,
    # but important for Postgres/MySQL so long-lived worker processes don't
    # hand out dead connections. Harmless to leave on for both dialects.
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency: yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create tables if they don't exist yet. Called once on startup."""
    # Import models here so they're registered on Base before create_all.
    from app.models import deviation  # noqa: F401

    Base.metadata.create_all(bind=engine)
