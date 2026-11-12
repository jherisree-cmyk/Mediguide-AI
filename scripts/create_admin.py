"""Give an existing account administrator rights (run on the server, never via the API).

Usage: python scripts/create_admin.py someone@example.com
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from sqlalchemy import select  # noqa: E402

from api.db import SessionLocal, User, init_db  # noqa: E402

if len(sys.argv) != 2:
    sys.exit(__doc__)
init_db()
with SessionLocal() as db:
    user = db.scalar(select(User).where(User.email == sys.argv[1].strip().lower()))
    if user is None:
        sys.exit("No account with that email. Register in the app first.")
    user.is_admin = True
    db.commit()
    print(f"{user.email} is now an administrator.")
