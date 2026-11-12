"""Passwords, login tokens, encryption and login rate limiting.

  * Passwords: Argon2id (argon2-cffi), the winner of the Password Hashing Competition.
  * Sessions: short-lived JWT (HS256) in an httpOnly, SameSite=Lax cookie. JavaScript cannot
    read it (protects against token theft via XSS); SameSite=Lax blocks cross-site POSTs (CSRF).
  * Health data at rest: Fernet (AES-128-CBC + HMAC-SHA256) for symptom text and results.
  * Brute force: at most 5 failed logins per email per 15 minutes (in-memory; single process).
"""
from __future__ import annotations

import json
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from api.config import settings

COOKIE_NAME = "mg_session"
_hasher = PasswordHasher()
_fernet = Fernet(settings.fernet_key.encode())
_DUMMY_HASH = _hasher.hash("timing-equaliser-not-a-real-password")


# ---- passwords ------------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, stored_hash: str | None) -> bool:
    """Always runs one Argon2 verification, so 'unknown email' and 'wrong password' take
    the same time (prevents discovering which emails are registered)."""
    try:
        return _hasher.verify(stored_hash or _DUMMY_HASH, password) and stored_hash is not None
    except (VerifyMismatchError, InvalidHashError):
        return False


# ---- tokens -----------------------------------------------------------------------------------
def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=settings.token_hours)},
                      settings.secret_key, algorithm="HS256")


def read_token(token: str) -> int | None:
    try:
        return int(jwt.decode(token, settings.secret_key, algorithms=["HS256"])["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None


# ---- encryption -------------------------------------------------------------------------------
def encrypt_text(text: str) -> bytes:
    return _fernet.encrypt(text.encode("utf-8"))


def decrypt_text(blob: bytes | None) -> str | None:
    if blob is None:
        return None
    try:
        return _fernet.decrypt(blob).decode("utf-8")
    except InvalidToken:
        return None


def encrypt_json(obj) -> bytes:
    return encrypt_text(json.dumps(obj, ensure_ascii=False, default=str))


def decrypt_json(blob: bytes | None):
    text = decrypt_text(blob)
    return json.loads(text) if text else None


# ---- login rate limiting ------------------------------------------------------------------------
class LoginLimiter:
    def __init__(self, max_failures: int = 5, window_s: int = 900):
        self.max, self.window = max_failures, window_s
        self.failures: dict[str, deque] = defaultdict(deque)

    def _prune(self, key: str) -> None:
        q, cutoff = self.failures[key], time.monotonic() - self.window
        while q and q[0] < cutoff:
            q.popleft()

    def blocked(self, key: str) -> bool:
        self._prune(key)
        return len(self.failures[key]) >= self.max

    def fail(self, key: str) -> None:
        self.failures[key].append(time.monotonic())

    def reset(self, key: str) -> None:
        self.failures.pop(key, None)


login_limiter = LoginLimiter()
