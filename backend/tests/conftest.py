"""Test configuration: API tests use a throw-away SQLite database and throw-away keys.
These environment variables must be set BEFORE `api.config` is imported."""
import os
import tempfile

from cryptography.fernet import Fernet

_tmp = tempfile.mkdtemp(prefix="mediguide-test-")
os.environ.setdefault("MEDIGUIDE_DB_URL", f"sqlite:///{_tmp}/test.db".replace("\\", "/"))
os.environ.setdefault("MEDIGUIDE_SECRET_KEY", "test-secret-key-not-for-production-use-0123456789")
os.environ.setdefault("MEDIGUIDE_FERNET_KEY", Fernet.generate_key().decode())
os.environ.setdefault("MEDIGUIDE_NO_ENV_WRITE", "1")
