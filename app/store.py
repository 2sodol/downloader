from __future__ import annotations

import threading
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Optional

from app.models import DownloadJob, JobStatus


UPDATE_FIELDS = {
    "title",
    "status",
    "progress",
    "downloaded_bytes",
    "total_bytes",
    "speed",
    "eta",
    "output_path",
    "error_message",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class JobStore:
    """Volatile in-memory job store for one-off local downloads."""

    def __init__(self) -> None:
        self._jobs: dict[str, DownloadJob] = {}
        self._lock = threading.Lock()

    def create(self, source_url: str, quality: str = "compatible", status: str = JobStatus.QUEUED) -> DownloadJob:
        now = utc_now()
        job = DownloadJob(
            id=str(uuid.uuid4()),
            source_url=source_url,
            quality=quality,
            status=status,
            progress=0,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._jobs = {job.id: job}
        return job

    def get(self, job_id: str) -> Optional[DownloadJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_recent(self, limit: int = 25) -> list[DownloadJob]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)
        return jobs[:limit]

    def find_active_by_url(self, source_url: str) -> Optional[DownloadJob]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)
        for job in jobs:
            if job.source_url == source_url and job.status in JobStatus.ACTIVE:
                return job
        return None

    def find_active(self) -> Optional[DownloadJob]:
        with self._lock:
            jobs = sorted(self._jobs.values(), key=lambda job: job.created_at, reverse=True)
        for job in jobs:
            if job.status in JobStatus.ACTIVE:
                return job
        return None

    def update(self, job_id: str, **changes: Any) -> Optional[DownloadJob]:
        fields = {key: value for key, value in changes.items() if key in UPDATE_FIELDS}
        if not fields:
            return self.get(job_id)

        fields["updated_at"] = utc_now()
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            updated = replace(job, **fields)
            self._jobs[job_id] = updated
            return updated
