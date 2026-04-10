from __future__ import annotations

import shutil
from typing import Optional


def ffmpeg_path() -> Optional[str]:
    return shutil.which("ffmpeg")


def ffmpeg_available() -> bool:
    return ffmpeg_path() is not None
