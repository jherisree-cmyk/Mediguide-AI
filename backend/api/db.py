"""Database (SQLite through SQLAlchemy 2.0).

Tables
  users             account + optional profile (age, sex, language). No health data.
  assessments       one row per assessment that must be kept: pending follow-ups (expire after
                    60 min) and assessments a logged-in user chose to SAVE. Symptom text,
                    answers and results are ENCRYPTED (Fernet).
  assessment_stats  anonymous aggregate record of every completed assessment: day, language,
                    level, symptom ids. NO user id, NO free text. The admin dashboard reads only this.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, create_engine,
                        event)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

from api.config import settings


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(50))
    age_years: Mapped[float | None] = mapped_column(Float)
    sex: Mapped[str | None] = mapped_column(String(1))              # "F" | "M" | None
    language: Mapped[str] = mapped_column(String(2), default="en")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    assessments: Mapped[list["AssessmentRecord"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AssessmentRecord(Base):
    __tablename__ = "assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)          # uuid4
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    status: Mapped[str] = mapped_column(String(20))                         # needs_followup | complete
    saved: Mapped[bool] = mapped_column(Boolean, default=False)
    input_language: Mapped[str] = mapped_column(String(2))
    display_language: Mapped[str] = mapped_column(String(2))
    level: Mapped[str | None] = mapped_column(String(10))
    followup_token_hash: Mapped[str | None] = mapped_column(String(64))
    text_enc: Mapped[bytes] = mapped_column(LargeBinary)
    answers_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    result_enc: Mapped[bytes | None] = mapped_column(LargeBinary)
    age_years: Mapped[float | None] = mapped_column(Float)                 # age given with the request
    user: Mapped[User | None] = relationship(back_populates="assessments")


class AssessmentStat(Base):
    __tablename__ = "assessment_stats"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    day: Mapped[str] = mapped_column(String(10), index=True)               # YYYY-MM-DD only
    input_language: Mapped[str] = mapped_column(String(2))
    level: Mapped[str] = mapped_column(String(10))
    rule_level: Mapped[str | None] = mapped_column(String(10))
    ml_level: Mapped[str | None] = mapped_column(String(10))
    asked_followup: Mapped[bool] = mapped_column(Boolean, default=False)
    symptom_ids: Mapped[str] = mapped_column(Text, default="")             # comma-separated concept ids


engine = create_engine(settings.db_url, connect_args={"check_same_thread": False}
                       if settings.db_url.startswith("sqlite") else {})


@event.listens_for(engine, "connect")
def _sqlite_fk(dbapi_conn, _):
    if settings.db_url.startswith("sqlite"):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
