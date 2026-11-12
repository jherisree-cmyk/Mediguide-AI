"""Configuration from environment variables (or a local .env file in the project root).

    MEDIGUIDE_SECRET_KEY   signs login tokens (JWT, HS256)
    MEDIGUIDE_FERNET_KEY   encrypts stored symptom text and results
    MEDIGUIDE_DB_URL       database URL (default: SQLite file in data/app/)
    MEDIGUIDE_COOKIE_SECURE  "true" when served over HTTPS (required in production)
    MEDIGUIDE_CORS_ORIGINS comma-separated list of allowed frontend origins
    MEDIGUIDE_ENV          "development" (default) or "production"

In development, missing keys are generated once and written to .env (which is git-ignored).
In production, missing keys are an error: keys must never be generated silently there.
"""
from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet

ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = ROOT / ".env"


def _read_env_file() -> dict[str, str]:
    if not ENV_FILE.exists():
        return {}
    out = {}
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


@dataclass(frozen=True)
class Settings:
    env: str
    secret_key: str
    fernet_key: str
    db_url: str
    cookie_secure: bool
    cors_origins: list[str]
    token_hours: int = 8
    followup_minutes: int = 60
    max_text_chars: int = 2000


def load_settings() -> Settings:
    file_vals = _read_env_file()

    def get(name: str, default: str | None = None) -> str | None:
        return os.environ.get(name) or file_vals.get(name) or default

    env = get("MEDIGUIDE_ENV", "development")
    secret, fkey = get("MEDIGUIDE_SECRET_KEY"), get("MEDIGUIDE_FERNET_KEY")
    if not secret or not fkey:
        if env == "production":
            raise RuntimeError("MEDIGUIDE_SECRET_KEY and MEDIGUIDE_FERNET_KEY must be set in production")
        secret = secret or secrets.token_urlsafe(48)
        fkey = fkey or Fernet.generate_key().decode()
        if "PYTEST_CURRENT_TEST" not in os.environ and "MEDIGUIDE_NO_ENV_WRITE" not in os.environ:
            lines = [f"MEDIGUIDE_SECRET_KEY={secret}", f"MEDIGUIDE_FERNET_KEY={fkey}"]
            with open(ENV_FILE, "a", encoding="utf-8") as fh:
                fh.write("# generated for local development - never commit this file\n" + "\n".join(lines) + "\n")
    db_dir = ROOT / "data" / "app"
    db_dir.mkdir(parents=True, exist_ok=True)
    return Settings(
        env=env, secret_key=secret, fernet_key=fkey,
        db_url=get("MEDIGUIDE_DB_URL", f"sqlite:///{(db_dir / 'mediguide.db').as_posix()}"),
        cookie_secure=(get("MEDIGUIDE_COOKIE_SECURE", "false").lower() == "true"),
        cors_origins=[o.strip() for o in get("MEDIGUIDE_CORS_ORIGINS",
                                             "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()],
    )


settings = load_settings()
