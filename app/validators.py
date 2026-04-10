from __future__ import annotations

from urllib.parse import parse_qs, urlparse


class URLValidationError(ValueError):
    pass


YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}


def _host(parsed_url) -> str:
    return (parsed_url.hostname or "").lower()


def _has_path_id(path: str, prefix: str) -> bool:
    value = path[len(prefix) :].strip("/")
    return bool(value)


def validate_youtube_url(raw_url: str) -> str:
    if not isinstance(raw_url, str) or not raw_url.strip():
        raise URLValidationError("URL을 입력해 주세요.")

    candidate = raw_url.strip()
    if "://" not in candidate and (
        candidate.startswith("youtube.com")
        or candidate.startswith("www.youtube.com")
        or candidate.startswith("m.youtube.com")
        or candidate.startswith("music.youtube.com")
        or candidate.startswith("youtu.be")
    ):
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise URLValidationError("http 또는 https URL만 지원합니다.")
    if parsed.username or parsed.password:
        raise URLValidationError("계정 정보가 포함된 URL은 지원하지 않습니다.")

    host = _host(parsed)
    query = parse_qs(parsed.query)

    if host == "youtu.be":
        if parsed.path.strip("/"):
            return parsed.geturl()
        raise URLValidationError("youtu.be URL에 영상 ID가 없습니다.")

    if host not in YOUTUBE_HOSTS:
        raise URLValidationError("YouTube URL만 지원합니다.")

    if parsed.path == "/watch" and query.get("v"):
        return parsed.geturl()
    if parsed.path == "/playlist" and query.get("list"):
        return parsed.geturl()
    if parsed.path.startswith("/shorts/") and _has_path_id(parsed.path, "/shorts/"):
        return parsed.geturl()

    raise URLValidationError("지원하는 형식은 watch, shorts, playlist URL입니다.")


def is_playlist_url(url: str) -> bool:
    parsed = urlparse(url)
    return _host(parsed) in YOUTUBE_HOSTS and parsed.path == "/playlist"

