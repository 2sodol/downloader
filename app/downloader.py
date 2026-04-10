from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

from app.config import Settings
from app.validators import is_playlist_url


ProgressCallback = Callable[[dict[str, Any]], None]

QUALITY_COMPATIBLE = "compatible"
QUALITY_BEST = "best"
QUALITY_CHOICES = {QUALITY_COMPATIBLE, QUALITY_BEST}

COMPATIBLE_MP4_FORMAT = (
    "bv*[ext=mp4][vcodec^=avc1]+ba[ext=m4a][acodec^=mp4a]/"
    "b[ext=mp4][vcodec^=avc1][acodec^=mp4a]/"
    "bv*[ext=mp4][vcodec^=avc1]+ba[ext=m4a]/"
    "b[ext=mp4]/"
    "bv*+ba/b"
)
BEST_FORMAT = "bv*+ba/b"


class DownloaderUnavailableError(RuntimeError):
    pass


class _QuietLogger:
    def debug(self, message: str) -> None:
        pass

    def info(self, message: str) -> None:
        pass

    def warning(self, message: str) -> None:
        pass

    def error(self, message: str) -> None:
        pass


def _load_ytdlp():
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise DownloaderUnavailableError("yt-dlp가 설치되어 있지 않습니다.") from exc
    return YoutubeDL


def _format_summary(info: dict[str, Any]) -> list[dict[str, Any]]:
    formats = []
    for item in info.get("formats") or []:
        formats.append(
            {
                "format_id": item.get("format_id"),
                "ext": item.get("ext"),
                "resolution": item.get("resolution") or item.get("format_note"),
                "filesize": item.get("filesize") or item.get("filesize_approx"),
                "vcodec": item.get("vcodec"),
                "acodec": item.get("acodec"),
            }
        )
    return formats[:25]


def extract_metadata(url: str) -> dict[str, Any]:
    YoutubeDL = _load_ytdlp()
    options = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "logger": _QuietLogger(),
        "skip_download": True,
        "noplaylist": not is_playlist_url(url),
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
        sanitized = ydl.sanitize_info(info)

    entries = sanitized.get("entries") or []
    return {
        "id": sanitized.get("id"),
        "url": sanitized.get("webpage_url") or url,
        "title": sanitized.get("title"),
        "duration": sanitized.get("duration"),
        "uploader": sanitized.get("uploader"),
        "thumbnail": sanitized.get("thumbnail"),
        "is_playlist": bool(entries),
        "entry_count": len(entries) if entries else None,
        "formats": _format_summary(sanitized),
    }


def _progress_from_event(event: dict[str, Any]) -> dict[str, Any]:
    downloaded = event.get("downloaded_bytes")
    total = event.get("total_bytes") or event.get("total_bytes_estimate")
    progress = None
    if downloaded is not None and total:
        progress = round((downloaded / total) * 100, 2)

    return {
        "status": event.get("status"),
        "progress": progress,
        "downloaded_bytes": downloaded,
        "total_bytes": total,
        "speed": event.get("speed"),
        "eta": event.get("eta"),
        "filename": event.get("filename"),
    }


def _find_output_path(info: Any) -> Optional[str]:
    if not isinstance(info, dict):
        return None

    for key in ("filepath", "_filename", "filename"):
        value = info.get(key)
        if value:
            return str(value)

    for item in info.get("requested_downloads") or []:
        value = item.get("filepath") or item.get("_filename") or item.get("filename")
        if value:
            return str(value)

    paths = []
    for entry in info.get("entries") or []:
        path = _find_output_path(entry)
        if path:
            paths.append(path)
    if paths:
        return paths[-1]
    return None


def download_url(
    url: str,
    settings: Settings,
    quality: str = QUALITY_COMPATIBLE,
    progress_callback: Optional[ProgressCallback] = None,
) -> dict[str, Any]:
    YoutubeDL = _load_ytdlp()
    settings.ensure_runtime_dirs()
    if quality not in QUALITY_CHOICES:
        quality = QUALITY_COMPATIBLE

    def hook(event: dict[str, Any]) -> None:
        if progress_callback is not None:
            progress_callback(_progress_from_event(event))

    options = {
        "format": COMPATIBLE_MP4_FORMAT if quality == QUALITY_COMPATIBLE else BEST_FORMAT,
        "outtmpl": str(settings.download_dir / "%(title).180B [%(id)s].%(ext)s"),
        "windowsfilenames": True,
        "overwrites": True,
        "noplaylist": not is_playlist_url(url),
        "retries": 3,
        "fragment_retries": 3,
        "progress_hooks": [hook],
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "logger": _QuietLogger(),
    }
    if quality == QUALITY_COMPATIBLE:
        options["merge_output_format"] = "mp4"

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        output_path = _find_output_path(info)
        sanitized = ydl.sanitize_info(info)

    return {
        "title": sanitized.get("title"),
        "output_path": output_path,
        "id": sanitized.get("id"),
        "url": sanitized.get("webpage_url") or url,
    }
