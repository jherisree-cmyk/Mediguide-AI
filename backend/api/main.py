"""MediGuide AI - FastAPI application.

Run (from the backend folder):  uvicorn api.main:app --reload
Interactive API docs:           http://localhost:8000/docs
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import settings
from api.db import init_db
from api.routes import admin, assess, auth, history
from mediguide.followup.questions import load_templates
from mediguide.knowledge import load_knowledge
from mediguide.ml.predictor import get_predictor
from mediguide.nlp.extractor import get_extractor

log = logging.getLogger("mediguide")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    for lang in ("en", "te", "hi"):   # warm up so the first user does not wait
        get_extractor(lang)
    get_predictor()
    yield


app = FastAPI(title="MediGuide AI", version="0.1.0", lifespan=lifespan,
              description="Educational prototype: multilingual symptom urgency guidance. "
                          "NOT a diagnostic tool and NOT clinically validated.")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "DELETE"], allow_headers=["Content-Type"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"          # health data must not be cached
    if settings.cookie_secure:
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    # Never echo internals or user text back; log only the type and the path.
    log.error("unhandled %s on %s", type(exc).__name__, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal error"})


for r in (auth.router, assess.router, history.router, admin.router):
    app.include_router(r)


@app.get("/api/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/meta", tags=["meta"])
def meta() -> dict:
    tpl = load_templates()
    return {"languages": ["en", "te", "hi"], "disclaimer": tpl["disclaimer"],
            "prototype_notice": tpl["prototype_notice"], "levels": tpl["levels"],
            "emergency_contacts": load_knowledge().emergency_contacts,
            "model_version": get_predictor().meta["version"]}
