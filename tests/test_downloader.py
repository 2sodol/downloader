from __future__ import annotations

import unittest
from unittest.mock import patch

from app.downloader import extract_metadata


class _FakeYoutubeDL:
    instances = []

    def __init__(self, options):
        self.options = options
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_info(self, url, download=False):
        player_client = (
            self.options.get("extractor_args", {})
            .get("youtube", {})
            .get("player_client")
        )
        if player_client == ["android_vr"]:
            raise RuntimeError("HTTP Error 403: Forbidden")
        return {
            "id": "video-id",
            "title": "Example title",
            "webpage_url": url,
            "formats": [],
        }

    def sanitize_info(self, info):
        return info


class DownloaderTest(unittest.TestCase):
    def test_extract_metadata_falls_back_to_default_client(self):
        _FakeYoutubeDL.instances = []

        with patch("app.downloader._load_ytdlp", return_value=_FakeYoutubeDL):
            data = extract_metadata("https://www.youtube.com/watch?v=BaW_jenozKc")

        self.assertEqual(data["title"], "Example title")
        self.assertEqual(len(_FakeYoutubeDL.instances), 2)
        first = _FakeYoutubeDL.instances[0].options
        second = _FakeYoutubeDL.instances[1].options
        self.assertEqual(
            first["extractor_args"]["youtube"]["player_client"],
            ["android_vr"],
        )
        self.assertNotIn("extractor_args", second)


if __name__ == "__main__":
    unittest.main()
