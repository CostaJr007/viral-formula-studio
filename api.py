"""FastAPI backend — exposes the studio engine to the React frontend.

Run: uv run python api.py  ->  http://localhost:8000 (docs at /docs)

Long operations (ingest + analyze) run as in-memory jobs polled by the client.
Everything else (profile, hooks, copy, dossier) is a direct request/response.
"""

import asyncio
import logging
import os
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from studio import store
from studio.create import copy_payload, generate_copy, generate_hooks
from studio.dossier import generate_dossier
from studio.ingest import ingest_urls
from studio.limits import limiter
from studio.pipeline import analyze_creator

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
).split(",")

app = FastAPI(title="Viral Formula Studio API", version="0.6.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

JOBS: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class IngestRequest(BaseModel):
    creator: str = Field(min_length=1)
    urls: list[str] = Field(min_length=1, max_length=5)


class HooksRequest(BaseModel):
    creator: str = Field(min_length=1)
    topic: str = Field(min_length=3)
    profile: dict | None = None  # optional: frontend passes cached profile to survive restarts


class CopyRequest(BaseModel):
    creator: str = Field(min_length=1)
    topic: str = Field(min_length=3)
    hook: str = Field(min_length=5)
    profile: dict | None = None


class DossierRequest(BaseModel):
    creator: str = Field(min_length=1)
    topic: str = Field(min_length=3)
    profile: dict | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _health_payload() -> dict:
    from studio.config import get_settings

    settings = get_settings()
    return {"status": "ok", "provider": settings.model_provider}


@app.get("/api/health")
def health() -> dict:
    return _health_payload()


@app.get("/api/usage")
def usage(request: Request) -> dict:
    ip = request.client.host if request.client else "unknown"
    return {
        "remaining_creators": limiter.remaining_creators(ip),
        "max_creators": 8,
        "max_dossiers_per_creator": 8,
        "window_minutes": 60,
    }


@app.get("/health")
def health_alias() -> dict:
    """Alias for load balancers / keep-warm pings that probe /health."""
    return _health_payload()


@app.get("/api/creators")
def list_creators() -> dict:
    creators = []
    for name in store.list_creators():
        profile = store.load_profile(name)
        creators.append(
            {
                "name": name,
                "has_profile": profile is not None,
                "videos_analyzed": profile.videos_analyzed if profile else 0,
                "has_metrics": bool(profile and profile.metrics),
            }
        )
    return {"creators": creators}


async def _run_ingest_job(job_id: str, creator: str, urls: list[str]) -> None:
    job = JOBS[job_id]
    try:
        job["status"] = "ingesting"
        report = await asyncio.to_thread(ingest_urls, creator, urls)
        job["ingest_report"] = report
        if not report["ok"]:
            job["status"] = "failed"
            # Surface concrete per-URL reasons so users/judges aren't stuck on a generic message.
            details = []
            for item in (report.get("failed") or [])[:4]:
                if isinstance(item, dict):
                    url = str(item.get("url") or "")[:48]
                    reason = str(item.get("reason") or "unknown error")[:160]
                    details.append(f"{url} → {reason}" if url else reason)
                else:
                    details.append(str(item)[:160])
            detail_txt = " | ".join(details) if details else "unknown reason"
            skipped = len(report.get("skipped") or [])
            job["error"] = (
                "No video could be ingested. "
                f"{detail_txt}"
                + (f" ({skipped} skipped)." if skipped else ".")
                + " Tip: use public YouTube Shorts, or try seed creators bryan / jeffnippard / kallaway (no upload)."
            )
            return

        job["status"] = "analyzing"
        profile = await asyncio.to_thread(analyze_creator, creator)
        job["status"] = "done"
        job["result"] = {
            "creator": profile.creator,
            "videos_analyzed": profile.videos_analyzed,
            "metrics": profile.metrics,
        }
    except Exception as e:  # noqa: BLE001 — surface any engine failure to the client
        logger.exception("Job %s failed", job_id)
        job["status"] = "failed"
        job["error"] = str(e)


@app.post("/api/ingest", status_code=202)
async def start_ingest(req: IngestRequest, request: Request) -> dict:
    ip = request.client.host if request.client else "unknown"

    if not limiter.check_ingest(ip, req.creator):
        remaining = limiter.remaining_creators(ip)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: max 3 distinct creators per IP. {remaining} slots remaining.",
        )

    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {"status": "queued", "creator": req.creator}
    asyncio.create_task(_run_ingest_job(job_id, req.creator, req.urls))
    return {"job_id": job_id, "remaining_creators": limiter.remaining_creators(ip)}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _check_rate(request: Request) -> None:
    """Shared rate-limit helper. Not currently used — hooks/copy are unconstrained."""
    pass


@app.get("/api/profile/{creator}")
def get_profile(creator: str) -> dict:
    profile = store.load_profile(creator)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No profile for '{creator}' — run the analysis first.")
    return profile.model_dump()


@app.post("/api/hooks")
async def hooks(req: HooksRequest) -> dict:
    try:
        hook_list = await asyncio.to_thread(generate_hooks, req.creator, req.topic, profile=req.profile)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"hooks": [h.model_dump() for h in hook_list.hooks]}


@app.post("/api/copy")
async def copy(req: CopyRequest) -> dict:
    try:
        result = await asyncio.to_thread(generate_copy, req.creator, req.topic, req.hook, profile=req.profile)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    # Structured blocks + spoken_copy so the frontend never depends on brittle pipe parsing alone
    return copy_payload(result)


@app.post("/api/dossier")
async def dossier(req: DossierRequest, request: Request) -> dict:
    ip = request.client.host if request.client else "unknown"
    if not limiter.check_dossier(ip, req.creator):
        remaining = limiter.remaining_dossiers(ip, req.creator)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit: max 3 dossier/PDF exports per creator. {remaining} remaining for '{req.creator}'.",
        )
    try:
        markdown = await asyncio.to_thread(generate_dossier, req.creator, req.topic, profile_data=req.profile)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"markdown": markdown}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
