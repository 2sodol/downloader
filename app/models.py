from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Optional


class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    ACTIVE = {QUEUED, RUNNING}
    TERMINAL = {COMPLETED, FAILED, CANCELLED}
    ALL = ACTIVE | TERMINAL


@dataclass(frozen=True)
class DownloadJob:
    id: str
    source_url: str
    status: str
    progress: float
    created_at: str
    updated_at: str
    quality: str = "compatible"
    title: Optional[str] = None
    downloaded_bytes: Optional[int] = None
    total_bytes: Optional[int] = None
    speed: Optional[float] = None
    eta: Optional[int] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None

    @classmethod
    def from_row(cls, row: Any) -> "DownloadJob":
        return cls(
            id=row["id"],
            source_url=row["source_url"],
            title=row["title"],
            quality=row["quality"],
            status=row["status"],
            progress=float(row["progress"] or 0),
            downloaded_bytes=row["downloaded_bytes"],
            total_bytes=row["total_bytes"],
            speed=row["speed"],
            eta=row["eta"],
            output_path=row["output_path"],
            error_message=row["error_message"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
