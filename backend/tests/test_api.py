"""Phase 8 / Experiment 6 (backend): API behaviour, security and privacy."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select, text

from api.db import AssessmentRecord, AssessmentStat, SessionLocal, User, engine
from api.main import app
from api.security import login_limiter


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def new_client():
    return TestClient(app)


def register(c, email=None, password="correct-horse-1"):
    email = email or f"user-{uuid.uuid4().hex[:8]}@example.com"
    r = c.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return email


# ---- meta / headers ----------------------------------------------------------------------------
def test_health_and_meta(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    meta = client.get("/api/meta").json()
    assert set(meta["languages"]) == {"en", "te", "hi"} and "diagnose" in meta["disclaimer"]["en"]


def test_security_headers(client):
    h = client.get("/api/health").headers
    assert h["x-content-type-options"] == "nosniff" and h["x-frame-options"] == "DENY"
    assert h["cache-control"] == "no-store"


# ---- anonymous assessment --------------------------------------------------------------------
def test_anonymous_emergency_is_immediate_and_not_stored(client):
    with SessionLocal() as db:
        before = db.query(AssessmentRecord).count()
    r = client.post("/api/assess", json={"text": "I can't breathe and my lips are blue"}).json()
    assert r["level"] == "EMERGENCY" and r["questions"] == [] and r["id"] is None
    with SessionLocal() as db:
        assert db.query(AssessmentRecord).count() == before


def test_anonymous_followup_flow_with_token(client):
    r = client.post("/api/assess", json={"text": "I have chest pain"}).json()
    assert r["status"] == "needs_followup" and r["id"] and r["followup_token"]
    url = f"/api/assess/{r['id']}/answers"
    ans = {"checklist": ["radiating_pain"], "age": 50}
    assert client.post(url, json={"answers": ans}).status_code == 404                    # no token
    assert client.post(url, json={"answers": ans, "followup_token": "wrong"}).status_code == 404
    done = client.post(url, json={"answers": ans, "followup_token": r["followup_token"]}).json()
    assert done["level"] == "EMERGENCY"
    # not saved -> pending record deleted; token cannot be reused
    assert client.post(url, json={"answers": ans, "followup_token": r["followup_token"]}).status_code == 404


def test_telugu_assessment(client):
    r = client.post("/api/assess", json={"text": "ఊపిరి అందడం లేదు"}).json()
    assert r["input_language"] == "te" and r["level"] == "EMERGENCY"


@pytest.mark.parametrize("body", [{"text": "x" * 2001}, {"text": ""}, {"text": "fever", "lang": "fr"},
                                  {"text": "fever", "age_years": 300}])
def test_input_validation(client, body):
    assert client.post("/api/assess", json=body).status_code == 422


@pytest.mark.parametrize("answers", [{"pain": 11}, {"evil": 1}, {"checklist": ["DROP TABLE users"]},
                                     {"onset:chest_pain": "yesterday"}, {"age": -1}])
def test_answer_validation(client, answers):
    r = client.post("/api/assess", json={"text": "I have chest pain"}).json()
    resp = client.post(f"/api/assess/{r['id']}/answers",
                       json={"answers": answers, "followup_token": r["followup_token"]})
    assert resp.status_code == 422


# ---- accounts --------------------------------------------------------------------------------
def test_register_login_logout(client):
    c = new_client()
    email = register(c)
    assert c.get("/api/auth/me").json()["email"] == email
    c.post("/api/auth/logout")
    assert c.get("/api/auth/me").status_code == 401
    assert c.post("/api/auth/login", json={"email": email, "password": "correct-horse-1"}).status_code == 200
    assert c.get("/api/auth/me").status_code == 200


def test_session_cookie_is_httponly(client):
    c = new_client()
    r = c.post("/api/auth/register", json={"email": f"h-{uuid.uuid4().hex[:6]}@example.com", "password": "abcdefgh1"})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_duplicate_email_and_wrong_password(client):
    c = new_client()
    email = register(c)
    assert new_client().post("/api/auth/register", json={"email": email, "password": "another-pass"}).status_code == 409
    assert new_client().post("/api/auth/login", json={"email": email, "password": "wrong-pass"}).status_code == 401


def test_password_is_hashed_not_stored(client):
    c = new_client()
    email = register(c, password="my-secret-pw-42")
    with SessionLocal() as db:
        h = db.scalar(select(User).where(User.email == email)).password_hash
    assert "my-secret-pw-42" not in h and h.startswith("$argon2")


def test_login_rate_limit(client):
    c = new_client()
    email = register(c)
    login_limiter.reset(email)
    for _ in range(5):
        assert c.post("/api/auth/login", json={"email": email, "password": "nope-nope"}).status_code == 401
    assert c.post("/api/auth/login", json={"email": email, "password": "correct-horse-1"}).status_code == 429
    login_limiter.reset(email)


def test_profile_cannot_make_user_admin(client):
    c = new_client()
    register(c)
    r = c.put("/api/auth/me", json={"age_years": 40, "sex": "F", "language": "hi", "is_admin": True}).json()
    assert r["is_admin"] is False and r["age_years"] == 40 and r["language"] == "hi"


# ---- history, encryption and access control ---------------------------------------------------
def test_saved_assessment_is_encrypted_and_listed(client):
    c = new_client()
    register(c)
    secret = "unique phrase 7391 with chest pain spreading to my left arm"
    r = c.post("/api/assess", json={"text": secret, "save": True}).json()
    assert r["level"] == "EMERGENCY" and r["saved"] and r["id"]
    with engine.connect() as conn:
        raw = conn.execute(text("SELECT text_enc, result_enc FROM assessments WHERE id=:i"), {"i": r["id"]}).one()
    assert b"7391" not in raw[0] and b"chest" not in raw[1]                          # encrypted at rest
    items = c.get("/api/history").json()
    assert items[0]["text"] == secret and items[0]["level"] == "EMERGENCY"


def test_saved_followup_uses_session_instead_of_token(client):
    c = new_client()
    register(c)
    r = c.post("/api/assess", json={"text": "I have a headache", "save": True}).json()
    done = c.post(f"/api/assess/{r['id']}/answers",
                  json={"answers": {"checklist": ["none"], "age": 30, "onset:headache": "gradual", "pain": 3}}).json()
    assert done["status"] == "complete" and done["id"] == r["id"]
    detail = c.get(f"/api/history/{r['id']}").json()
    assert detail["answers"]["pain"] == 3 and detail["result"]["level"] == done["level"]


def test_users_cannot_see_or_delete_each_other(client):
    a, b = new_client(), new_client()
    register(a)
    register(b)
    rid = a.post("/api/assess", json={"text": "I can't breathe", "save": True}).json()["id"]
    assert b.get(f"/api/history/{rid}").status_code == 404
    assert b.delete(f"/api/history/{rid}").status_code == 404
    assert rid not in [i["id"] for i in b.get("/api/history").json()]
    pending = a.post("/api/assess", json={"text": "I have chest pain", "save": True}).json()
    assert b.post(f"/api/assess/{pending['id']}/answers", json={"answers": {"age": 40}}).status_code == 404
    assert a.get(f"/api/history/{rid}").status_code == 200


def test_history_requires_login(client):
    assert new_client().get("/api/history").status_code == 401


def test_anonymous_save_flag_is_ignored(client):
    r = new_client().post("/api/assess", json={"text": "I can't breathe", "save": True}).json()
    assert r["saved"] is False and r["id"] is None


def test_delete_item_all_and_account(client):
    c = new_client()
    email = register(c)
    ids = [c.post("/api/assess", json={"text": "I can't breathe", "save": True}).json()["id"] for _ in range(3)]
    assert c.delete(f"/api/history/{ids[0]}").status_code == 204
    assert len(c.get("/api/history").json()) == 2
    assert c.delete("/api/history").status_code == 204
    assert c.get("/api/history").json() == []
    c.post("/api/assess", json={"text": "I can't breathe", "save": True})
    assert c.delete("/api/auth/me").status_code == 204
    with SessionLocal() as db:
        assert db.scalar(select(User).where(User.email == email)) is None
        assert db.scalar(select(AssessmentRecord).where(AssessmentRecord.id.in_(ids))) is None


# ---- admin -------------------------------------------------------------------------------------
def test_stats_table_has_no_personal_columns():
    cols = {c["name"] for c in inspect(engine).get_columns("assessment_stats")}
    assert not cols & {"user_id", "text", "text_enc", "email", "result_enc"}


def test_admin_stats_access_control_and_content(client):
    c = new_client()
    email = register(c)
    assert c.get("/api/admin/stats").status_code == 403
    assert new_client().get("/api/admin/stats").status_code == 401
    with SessionLocal() as db:
        db.scalar(select(User).where(User.email == email)).is_admin = True
        db.commit()
    s = c.get("/api/admin/stats").json()
    assert s["total_assessments"] >= 1 and "EMERGENCY" in s["levels"]
    assert s["model"]["version"] == "v1"
    body = str(s)
    assert "@" not in body and "lips are blue" not in body       # no emails, no free text
    with SessionLocal() as db:
        assert db.query(AssessmentStat).count() == s["total_assessments"]


def test_pending_followup_expires(client):
    from datetime import timedelta

    from api.db import utcnow
    r = client.post("/api/assess", json={"text": "I have chest pain"}).json()
    with SessionLocal() as db:
        db.get(AssessmentRecord, r["id"]).created_at = utcnow() - timedelta(minutes=61)
        db.commit()
    resp = client.post(f"/api/assess/{r['id']}/answers",
                       json={"answers": {"age": 40}, "followup_token": r["followup_token"]})
    assert resp.status_code == 404
    with SessionLocal() as db:
        assert db.get(AssessmentRecord, r["id"]) is None      # purged, text gone


# ---- live preview (Phase 12) -------------------------------------------------------------------
def test_preview_lists_symptoms_and_denials_without_storing_anything(client):
    with SessionLocal() as db:
        before = (db.query(AssessmentRecord).count(), db.query(AssessmentStat).count())
    r = client.post("/api/assess/preview", json={"text": "headache and cough, no fever", "display_lang": "hi"})
    assert r.status_code == 200
    body = r.json()
    assert {s["id"] for s in body["symptoms"]} >= {"headache", "cough"}
    assert [d["id"] for d in body["denied"]] == ["fever"]
    assert body["emergency_sign"] is False
    assert any(s["label"] == "सिरदर्द" for s in body["symptoms"])   # labels in the display language
    with SessionLocal() as db:
        assert (db.query(AssessmentRecord).count(), db.query(AssessmentStat).count()) == before


@pytest.mark.parametrize("text,lang", [("I can't breathe and my lips are blue", "en"),
                                       ("నాకు ఊపిరి ఆడటం లేదు", "te")])
def test_preview_flags_emergency_signs(client, text, lang):
    body = client.post("/api/assess/preview", json={"text": text, "lang": lang}).json()
    assert body["emergency_sign"] is True and body["input_language"] == lang


def test_preview_validation(client):
    assert client.post("/api/assess/preview", json={"text": ""}).status_code == 422
    assert client.post("/api/assess/preview", json={"text": "x" * 5000}).status_code == 422
    assert client.post("/api/assess/preview", json={"text": "cough", "lang": "fr"}).status_code == 422
