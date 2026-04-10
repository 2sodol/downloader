from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Literal

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.downloader import (
    QUALITY_BEST,
    QUALITY_COMPATIBLE,
    DownloaderUnavailableError,
    download_url,
    extract_metadata,
)
from app.models import DownloadJob, JobStatus
from app.store import JobStore
from app.system import ffmpeg_available, ffmpeg_path
from app.validators import URLValidationError, validate_youtube_url


settings = get_settings()
settings.ensure_runtime_dirs()
job_store = JobStore()
download_slots = threading.Semaphore(settings.max_concurrent_downloads)

app = FastAPI(title="Local YouTube Downloader")
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")


class URLRequest(BaseModel):
    url: str = Field(min_length=1)


class DownloadRequest(URLRequest):
    quality: Literal["compatible", "best"] = QUALITY_COMPATIBLE


def serialize_job(job: DownloadJob) -> dict[str, Any]:
    data = job.to_dict()
    data["file_ready"] = bool(job.output_path and Path(job.output_path).exists())
    return data


def _http_validation_error(error: Exception) -> HTTPException:
    return HTTPException(status_code=422, detail=str(error))


def _safe_completed_file(job: DownloadJob) -> Path:
    if job.status != JobStatus.COMPLETED or not job.output_path:
        raise HTTPException(status_code=404, detail="완료된 파일이 없습니다.")

    candidate = Path(job.output_path)
    if not candidate.is_absolute():
        candidate = settings.download_dir / candidate

    resolved = candidate.resolve()
    download_root = settings.download_dir.resolve()
    try:
        resolved.relative_to(download_root)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="다운로드 디렉터리 밖의 파일은 제공할 수 없습니다.") from exc

    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return resolved


def run_download_job(job_id: str, url: str, quality: str) -> None:
    download_slots.acquire()
    try:
        job_store.update(
            job_id,
            status=JobStatus.RUNNING,
            progress=0,
            error_message=None,
        )

        if not ffmpeg_available():
            raise RuntimeError("ffmpeg가 설치되어 있지 않습니다. ffmpeg 설치 후 다시 시도해 주세요.")

        def on_progress(payload: dict[str, Any]) -> None:
            changes: dict[str, Any] = {
                "status": JobStatus.RUNNING,
                "downloaded_bytes": payload.get("downloaded_bytes"),
                "total_bytes": payload.get("total_bytes"),
                "speed": payload.get("speed"),
                "eta": payload.get("eta"),
            }
            if payload.get("progress") is not None:
                changes["progress"] = payload["progress"]
            if payload.get("filename"):
                changes["output_path"] = payload["filename"]
            job_store.update(job_id, **changes)

        result = download_url(url, settings=settings, quality=quality, progress_callback=on_progress)
        job_store.update(
            job_id,
            status=JobStatus.COMPLETED,
            progress=100,
            title=result.get("title"),
            output_path=result.get("output_path"),
            error_message=None,
        )
    except Exception as exc:
        job_store.update(
            job_id,
            status=JobStatus.FAILED,
            error_message=str(exc),
        )
    finally:
        download_slots.release()


@app.get("/")
def index():
    return FileResponse(settings.static_dir / "index.html")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ffmpeg_available": ffmpeg_available(),
        "ffmpeg_path": ffmpeg_path(),
        "download_dir": str(settings.download_dir),
        "storage": "memory",
    }


@app.post("/metadata")
def metadata(payload: URLRequest):
    try:
        url = validate_youtube_url(payload.url)
        return extract_metadata(url)
    except URLValidationError as exc:
        raise _http_validation_error(exc) from exc
    except DownloaderUnavailableError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/downloads")
def create_download(payload: DownloadRequest, background_tasks: BackgroundTasks):
    try:
        url = validate_youtube_url(payload.url)
    except URLValidationError as exc:
        raise _http_validation_error(exc) from exc

    active_job = job_store.find_active_by_url(url)
    if active_job is not None:
        return {"duplicate": True, "job": serialize_job(active_job)}

    running_job = job_store.find_active()
    if running_job is not None:
        raise HTTPException(status_code=409, detail="다른 다운로드가 실행 중입니다. 완료 후 다시 시도해 주세요.")

    quality = QUALITY_BEST if payload.quality == QUALITY_BEST else QUALITY_COMPATIBLE
    job = job_store.create(url, quality=quality)
    background_tasks.add_task(run_download_job, job.id, url, quality)
    return {"duplicate": False, "job": serialize_job(job)}


@app.get("/downloads")
def list_downloads(limit: int = 25):
    limit = min(max(limit, 1), 100)
    return {"jobs": [serialize_job(job) for job in job_store.list_recent(limit=limit)]}


@app.get("/downloads/{job_id}")
def get_download(job_id: str):
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    return serialize_job(job)


@app.get("/downloads/{job_id}/file")
def get_download_file(job_id: str):
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="작업을 찾을 수 없습니다.")
    file_path = _safe_completed_file(job)
    return FileResponse(file_path, filename=file_path.name)
