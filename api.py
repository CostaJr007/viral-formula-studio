"""FastAPI backend — exposes the studio engine to the React frontend.

Run: uv run python api.py  ->  http://localhost:8000 (docs at /docs)

Long operations (ingest + analyze) run as in-memory jobs polled by the client.
Everything else (profile, hooks, copy, dossier) is a direct request/response.
"""

import asyncio
import logging
import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from studio import store
from studio.create import generate_copy, generate_hooks
from studio.dossier import generate_dossier
from studio.ingest import ingest_urls
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


class CopyRequest(BaseModel):
    creator: str = Field(min_length=1)
    topic: str = Field(min_length=3)
    hook: str = Field(min_length=5)


class DossierRequest(BaseModel):
    creator: str = Field(min_length=1)
    topic: str = Field(min_length=3)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict:
    from studio.config import get_settings

    settings = get_settings()
    return {"status": "ok", "provider": settings.model_provider}


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
            job["error"] = "No video could be ingested. Check the links (YouTube Shorts/TikTok work best)."
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
async def start_ingest(req: IngestRequest) -> dict:
    job_id = uuid.uuid4().hex[:12]
    JOBS[job_id] = {"status": "queued", "creator": req.creator}
    asyncio.create_task(_run_ingest_job(job_id, req.creator, req.urls))
    return {"job_id": job_id}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/profile/{creator}")
def get_profile(creator: str) -> dict:
    profile = store.load_profile(creator)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"No profile for '{creator}' — run the analysis first.")
    return profile.model_dump()


@app.post("/api/hooks")
async def hooks(req: HooksRequest) -> dict:
    try:
        hook_list = await asyncio.to_thread(generate_hooks, req.creator, req.topic)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"hooks": [h.model_dump() for h in hook_list.hooks]}


@app.post("/api/copy")
async def copy(req: CopyRequest) -> dict:
    try:
        result = await asyncio.to_thread(generate_copy, req.creator, req.topic, req.hook)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return result.model_dump() | {"word_count": len(result.script.split())}


@app.post("/api/dossier")
async def dossier(req: DossierRequest) -> dict:
    try:
        markdown = await asyncio.to_thread(generate_dossier, req.creator, req.topic)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"markdown": markdown}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
