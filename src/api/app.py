from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.jobs import JobManager, JobRecord
from src.orchestrator import STATIC_CREDENTIAL_MAP, handler as run_handler

app = FastAPI(title="Automation Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

LOGGER = logging.getLogger("api.jobs")

_executor = ThreadPoolExecutor(
    max_workers=int(os.getenv("RUNNER_MAX_WORKERS", "2"))
)
_jobs = JobManager()


def _prepare_payload(
    payload: Dict[str, Any],
    header_username: str | None,
    header_password: str | None,
) -> Dict[str, Any]:
    """Inject credentials from headers or static defaults before invoking the handler."""
    prepared = dict(payload)

    # Respect explicit payload credentials if already provided
    payload_credentials = prepared.get("credentials") or {}
    if payload_credentials.get("username") and payload_credentials.get("password"):
        return prepared

    if header_username and header_password:
        prepared["credentials"] = {
            "username": header_username,
            "password": header_password,
        }
        return prepared

    site = (
        prepared.get("site")
        or prepared.get("site_name")
        or ""
    )
    site_key = str(site).strip().lower()
    static_creds = STATIC_CREDENTIAL_MAP.get(site_key)
    if static_creds:
        prepared["credentials"] = {
            "username": static_creds["username"],
            "password": static_creds["password"],
        }
    return prepared


def _job_runner(job_id: str, payload: Dict[str, Any]) -> None:
    _jobs.mark_running(job_id)
    try:
        result = run_handler(payload)
        _jobs.mark_completed(job_id, result)
    except ValueError as exc:
        LOGGER.warning("Job %s failed with validation error: %s", job_id, exc)
        _jobs.mark_failed(job_id, str(exc))
    except Exception as exc:
        LOGGER.exception("Job %s failed unexpectedly", job_id)
        _jobs.mark_failed(job_id, str(exc))


def _serialize_job(record: JobRecord) -> Dict[str, Any]:
    return {
        "job_id": record.job_id,
        "status": record.status,
        "created_at": record.created_at.isoformat() + "Z",
        "updated_at": record.updated_at.isoformat() + "Z",
        "result": record.result,
        "error": record.error,
    }


def _submit_job(
    payload: Dict[str, Any],
    x_user_name: str | None,
    x_password: str | None,
) -> Dict[str, Any]:
    prepared = _prepare_payload(payload, x_user_name, x_password)
    job = _jobs.create_job(prepared)
    _executor.submit(_job_runner, job.job_id, prepared)
    return {
        "job_id": job.job_id,
        "status": job.status,
        "created_at": job.created_at.isoformat() + "Z",
    }


api_router = APIRouter()


@api_router.post("/run")
async def run_automation(
    payload: Dict[str, Any],
    x_user_name: str | None = Header(default=None, convert_underscores=False),
    x_password: str | None = Header(default=None, convert_underscores=False),
) -> Dict[str, Any]:
    """Submit an automation job and return a job identifier."""
    return _submit_job(payload, x_user_name, x_password)


@api_router.get("/jobs/{job_id}")
async def get_job(job_id: str) -> Dict[str, Any]:
    record = _jobs.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(record)


@app.post("/run")
async def run_automation_root(
    payload: Dict[str, Any],
    x_user_name: str | None = Header(default=None, convert_underscores=False),
    x_password: str | None = Header(default=None, convert_underscores=False),
) -> Dict[str, Any]:
    """Submit an automation job when the frontend is hosted separately."""
    return _submit_job(payload, x_user_name, x_password)


@app.get("/jobs/{job_id}")
async def get_job_root(job_id: str) -> Dict[str, Any]:
    record = _jobs.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(record)


app.include_router(api_router, prefix="/api")


def _detect_frontend_dir() -> Path | None:
    env_path = os.getenv("FRONTEND_DIST")
    if env_path:
        candidate = Path(env_path)
        if candidate.exists():
            return candidate

    repo_root = Path(__file__).resolve().parents[2]
    fallback = repo_root / "ui" / "dist"
    if fallback.exists():
        return fallback

    return None


_FRONTEND_DIR = _detect_frontend_dir()

if _FRONTEND_DIR:
    app.mount("/", StaticFiles(directory=_FRONTEND_DIR, html=True), name="frontend")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        index_path = _FRONTEND_DIR / "index.html"
        return FileResponse(index_path)
