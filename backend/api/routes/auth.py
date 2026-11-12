"""Registration, login, logout, profile and account deletion (Module 1)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.config import settings
from api.db import User, get_db
from api.deps import required_user
from api.schemas import LoginIn, ProfileIn, RegisterIn, UserOut
from api.security import COOKIE_NAME, create_token, hash_password, login_limiter, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, display_name=u.display_name, age_years=u.age_years,
                   sex=u.sex, language=u.language, is_admin=u.is_admin)


def _set_session(response: Response, user: User) -> None:
    response.set_cookie(COOKIE_NAME, create_token(user.id), httponly=True, samesite="lax",
                        secure=settings.cookie_secure, max_age=settings.token_hours * 3600, path="/")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(email=body.email, password_hash=hash_password(body.password),
                display_name=body.display_name, language=body.language)
    db.add(user)
    db.commit()
    _set_session(response, user)
    return _user_out(user)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, response: Response, db: Session = Depends(get_db)) -> UserOut:
    key = body.email.strip().lower()
    if login_limiter.blocked(key):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Try again in 15 minutes.")
    user = db.scalar(select(User).where(User.email == key))
    if not verify_password(body.password, user.password_hash if user else None):
        login_limiter.fail(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    login_limiter.reset(key)
    _set_session(response, user)
    return _user_out(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> Response:
    response.delete_cookie(COOKIE_NAME, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(required_user)) -> UserOut:
    return _user_out(user)


@router.put("/me", response_model=UserOut)
def update_profile(body: ProfileIn, user: User = Depends(required_user), db: Session = Depends(get_db)) -> UserOut:
    # Only these fields can change; is_admin and email are never taken from the request.
    user.display_name = body.display_name
    user.age_years = body.age_years
    user.sex = body.sex
    if body.language:
        user.language = body.language
    db.add(user)
    db.commit()
    return _user_out(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(response: Response, user: User = Depends(required_user), db: Session = Depends(get_db)) -> Response:
    """Deletes the account and ALL saved assessments (cascade). Anonymous statistics contain
    no user id and therefore cannot be linked back to the account."""
    db.delete(user)
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
