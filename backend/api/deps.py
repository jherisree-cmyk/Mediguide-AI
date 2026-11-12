"""Shared FastAPI dependencies: who is the current user (if anyone)?"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from api.db import User, get_db
from api.security import COOKIE_NAME, read_token


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = request.cookies.get(COOKIE_NAME)
    user_id = read_token(token) if token else None
    return db.get(User, user_id) if user_id else None


def required_user(user: User | None = Depends(optional_user)) -> User:
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in")
    return user


def admin_user(user: User = Depends(required_user)) -> User:
    if not user.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator access required")
    return user
