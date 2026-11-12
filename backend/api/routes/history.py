"""Assessment history (Module 9): only the owner can see or delete their saved assessments."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from api.db import AssessmentRecord, User, get_db
from api.deps import required_user
from api.schemas import HistoryItem
from api.security import decrypt_json, decrypt_text

router = APIRouter(prefix="/api/history", tags=["history"])


def _own(db: Session, user: User, assessment_id: str) -> AssessmentRecord:
    rec = db.get(AssessmentRecord, assessment_id)
    if rec is None or rec.user_id != user.id or not rec.saved or rec.status != "complete":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assessment not found")  # same for "not yours"
    return rec


@router.get("", response_model=list[HistoryItem])
def list_history(user: User = Depends(required_user), db: Session = Depends(get_db)) -> list[HistoryItem]:
    rows = db.scalars(select(AssessmentRecord).where(AssessmentRecord.user_id == user.id,
                                                     AssessmentRecord.saved.is_(True),
                                                     AssessmentRecord.status == "complete")
                      .order_by(AssessmentRecord.created_at.desc())).all()
    items = []
    for r in rows:
        result = decrypt_json(r.result_enc) or {}
        items.append(HistoryItem(id=r.id, created_at=r.created_at.isoformat(), level=r.level,
                                 input_language=r.input_language, text=decrypt_text(r.text_enc),
                                 symptoms=[s["label"] for s in result.get("symptoms", [])]))
    return items


@router.get("/{assessment_id}")
def get_history_item(assessment_id: str, user: User = Depends(required_user), db: Session = Depends(get_db)) -> dict:
    rec = _own(db, user, assessment_id)
    return {"id": rec.id, "created_at": rec.created_at.isoformat(), "text": decrypt_text(rec.text_enc),
            "answers": decrypt_json(rec.answers_enc), "result": decrypt_json(rec.result_enc)}


@router.delete("/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history_item(assessment_id: str, user: User = Depends(required_user), db: Session = Depends(get_db)) -> None:
    db.delete(_own(db, user, assessment_id))
    db.commit()


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_history(user: User = Depends(required_user), db: Session = Depends(get_db)) -> None:
    db.execute(delete(AssessmentRecord).where(AssessmentRecord.user_id == user.id))
    db.commit()
