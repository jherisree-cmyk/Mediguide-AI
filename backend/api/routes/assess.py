"""Symptom assessment endpoints (Modules 2-8 through the recommendation engine)."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from api.config import settings
from api.db import AssessmentRecord, AssessmentStat, User, get_db, utcnow
from api.deps import optional_user
from api.schemas import AnswersIn, AssessIn, PreviewIn
from api.security import decrypt_text, encrypt_json, encrypt_text
from mediguide.recommend.engine import Assessment, assess, preview

router = APIRouter(prefix="/api/assess", tags=["assessment"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _purge_expired(db: Session) -> None:
    cutoff = utcnow() - timedelta(minutes=settings.followup_minutes)
    db.execute(delete(AssessmentRecord).where(AssessmentRecord.status == "needs_followup",
                                              AssessmentRecord.created_at < cutoff))
    db.commit()  # commit now: a later 404 must not roll the purge back (found by a test)


def _record_stat(db: Session, a: Assessment, asked_followup: bool) -> None:
    """Anonymous aggregate only: no user id, no text."""
    db.add(AssessmentStat(day=datetime.now(timezone.utc).strftime("%Y-%m-%d"), input_language=a.input_language,
                          level=a.level, rule_level=a.trace.get("rule_level"), ml_level=a.trace.get("ml_level"),
                          asked_followup=asked_followup,
                          symptom_ids=",".join(s["id"] for s in a.symptoms if s["kind"] in ("symptom", "sign"))))


def _response(a: Assessment, record_id: str | None, token: str | None, saved: bool) -> dict:
    return {"id": record_id, "followup_token": token, "saved": saved, **a.to_dict()}


@router.post("/preview")
def live_preview(body: PreviewIn) -> dict:
    """Live symptom detection while typing. Stateless: no database, no statistics, no logging of text."""
    return preview(body.text, lang=body.lang, display_lang=body.display_lang, age_years=body.age_years)


@router.post("")
def start_assessment(body: AssessIn, user: User | None = Depends(optional_user), db: Session = Depends(get_db)) -> dict:
    _purge_expired(db)
    age = body.age_years if body.age_years is not None else (user.age_years if user else None)
    display = body.display_lang or (user.language if user and not body.lang else None)
    a = assess(body.text, lang=body.lang, display_lang=display, age_years=age, sex=user.sex if user else None)
    save = bool(user and body.save)

    if a.status == "needs_followup":
        token = secrets.token_urlsafe(24)
        rec = AssessmentRecord(id=str(uuid.uuid4()), user_id=user.id if user else None, status=a.status,
                               saved=save, input_language=a.input_language, display_language=a.display_language,
                               followup_token_hash=_hash_token(token), text_enc=encrypt_text(body.text),
                               age_years=age)
        db.add(rec)
        db.commit()
        return _response(a, rec.id, token, save)

    _record_stat(db, a, asked_followup=False)
    record_id = None
    if save:
        rec = AssessmentRecord(id=str(uuid.uuid4()), user_id=user.id, status="complete", saved=True,
                               input_language=a.input_language, display_language=a.display_language, level=a.level,
                               text_enc=encrypt_text(body.text), result_enc=encrypt_json(a.to_dict()), age_years=age)
        db.add(rec)
        record_id = rec.id
    db.commit()
    return _response(a, record_id, None, save)


@router.post("/{assessment_id}/answers")
def answer_followup(assessment_id: str, body: AnswersIn, user: User | None = Depends(optional_user),
                    db: Session = Depends(get_db)) -> dict:
    _purge_expired(db)
    rec = db.get(AssessmentRecord, assessment_id)
    not_found = HTTPException(status.HTTP_404_NOT_FOUND, "Assessment not found or expired")
    if rec is None or rec.status != "needs_followup":
        raise not_found
    # Owner check: the logged-in owner, or (anonymous) whoever holds the one-time token.
    owner_ok = rec.user_id is not None and user is not None and rec.user_id == user.id
    token_ok = body.followup_token is not None and rec.followup_token_hash is not None and \
        hmac.compare_digest(rec.followup_token_hash, _hash_token(body.followup_token))
    if not (owner_ok or token_ok):
        raise not_found  # same answer as "missing": do not reveal that the id exists

    text = decrypt_text(rec.text_enc)
    if text is None:
        raise not_found
    a = assess(text, lang=rec.input_language, display_lang=rec.display_language, answers=body.answers,
               age_years=rec.age_years, sex=user.sex if user else None)
    _record_stat(db, a, asked_followup=True)
    if rec.saved:
        rec.status, rec.level, rec.followup_token_hash = "complete", a.level, None
        rec.answers_enc, rec.result_enc = encrypt_json(body.answers), encrypt_json(a.to_dict())
        record_id = rec.id
    else:
        db.delete(rec)  # not saved: keep nothing identifiable once the assessment is finished
        record_id = None
    db.commit()
    return _response(a, record_id, None, rec.saved)
