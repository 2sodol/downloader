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
YOUTUBE_PLAYER_CLIENTS: tuple[Optional[str], ...] = ("android_vr", None)


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


def _with_youtube_player_client(options: dict[str, Any], client: Optional[str]) -> dict[str, Any]:
    configured = dict(options)
    if client is None:
        return configured

    extractor_args = dict(configured.get("extractor_args") or {})
    youtube_args = dict(extractor_args.get("youtube") or {})
    youtube_args["player_client"] = [client]
    extractor_args["youtube"] = youtube_args
    configured["extractor_args"] = extractor_args
    return configured


def _extract_info(
    url: str,
    *,
    options: dict[str, Any],
    download: bool,
) -> tuple[Any, dict[str, Any]]:
    YoutubeDL = _load_ytdlp()
    last_error: Optional[Exception] = None

    # Prefer android_vr since it currently avoids the YouTube 403s we see with
    # the default web client, but keep the default path as a fallback.
    for client in YOUTUBE_PLAYER_CLIENTS:
        configured = _with_youtube_player_client(options, client)
        with YoutubeDL(configured) as ydl:
            try:
                info = ydl.extract_info(url, download=download)
            except Exception as exc:
                last_error = exc
                continue
            return info, ydl.sanitize_info(info)

    if last_error is None:
        raise DownloaderUnavailableError("yt-dlp에서 다운로드 정보를 불러오지 못했습니다.")
    raise last_error


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
    options = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "logger": _QuietLogger(),
        "skip_download": True,
        "noplaylist": not is_playlist_url(url),
    }
    _, sanitized = _extract_info(url, options=options, download=False)

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

    info, sanitized = _extract_info(url, options=options, download=True)
    output_path = _find_output_path(info)

    return {
        "title": sanitized.get("title"),
        "output_path": output_path,
        "id": sanitized.get("id"),
        "url": sanitized.get("webpage_url") or url,
    }
