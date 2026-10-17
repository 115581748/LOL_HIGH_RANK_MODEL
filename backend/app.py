from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from backend.core import AnalysisEngine, AnalysisRequest, JobManager, SlidingWindowLimiter


ROOT = Path(__file__).resolve().parents[1]
RIOT_API_KEY = os.environ.get("RIOT_API_KEY", "").strip()
ALLOWED_ORIGIN = os.environ.get(
    "RIFTSCALE_ALLOWED_ORIGIN", "https://115581748.github.io"
).rstrip("/")
CACHE_DIR = Path(os.environ.get("RIFTSCALE_CACHE_DIR", "/tmp/riftscale-cache"))

engine = AnalysisEngine(ROOT, RIOT_API_KEY, CACHE_DIR)
manager = JobManager(
    engine,
    cache_ttl_seconds=int(os.environ.get("RIFTSCALE_CACHE_TTL_SECONDS", "300")),
)
ip_limiter = SlidingWindowLimiter(
    limit=int(os.environ.get("RIFTSCALE_IP_LIMIT", "3")), window_seconds=60
)
player_limiter = SlidingWindowLimiter(limit=2, window_seconds=300)

app = FastAPI(
    title="RiftScale private analysis API",
    version="1.0.0",
    docs_url=None if os.environ.get("RIFTSCALE_ENV") == "production" else "/docs",
    redoc_url=None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN, "http://127.0.0.1:8765", "http://localhost:8765"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=3600,
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        host.strip()
        for host in os.environ.get(
            "RIFTSCALE_ALLOWED_HOSTS", "*.run.app,localhost,127.0.0.1"
        ).split(",")
        if host.strip()
    ],
)


class AnalysisBody(BaseModel):
    riotId: str = Field(min_length=3, max_length=81)
    platform: str = Field(default="oc1", max_length=8)
    matchCount: int = Field(default=10, ge=1, le=20)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 4096:
                return JSONResponse(status_code=413, content={"detail": "Request body is too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.get("/health")
def health() -> dict:
    return {
        "ok": bool(RIOT_API_KEY),
        "service": "riftscale-analysis-api",
        "keyConfigured": bool(RIOT_API_KEY),
        "region": "oce",
    }


@app.post("/v1/analyses", status_code=status.HTTP_202_ACCEPTED)
def create_analysis(body: AnalysisBody, request: Request) -> dict:
    if not RIOT_API_KEY:
        raise HTTPException(status_code=503, detail="Riot API service is not configured")
    client_ip = request.client.host if request.client else "unknown"
    if not ip_limiter.allow(client_ip):
        raise HTTPException(status_code=429, detail="Too many analysis requests; retry in one minute")
    try:
        normalized = AnalysisRequest(body.riotId, body.platform, body.matchCount).normalized()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not player_limiter.allow(normalized.cache_key):
        raise HTTPException(status_code=429, detail="This player was refreshed recently; retry later")
    record, cached = manager.submit(normalized)
    return {**record.public(), "cached": cached, "pollAfterMs": 1500}


@app.get("/v1/analyses/{job_id}")
def read_analysis(job_id: str) -> dict:
    record = manager.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis job not found or expired")
    return record.public()
