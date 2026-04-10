from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    project_root: Path
    download_dir: Path
    static_dir: Path
    max_concurrent_downloads: int

    @classmethod
    def defaults(cls) -> "Settings":
        return cls(
            project_root=PROJECT_ROOT,
            download_dir=PROJECT_ROOT / "downloads",
            static_dir=PROJECT_ROOT / "app" / "static",
            max_concurrent_downloads=1,
        )

    def ensure_runtime_dirs(self) -> None:
        self.download_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.defaults()
