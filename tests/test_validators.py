from __future__ import annotations

import unittest

from app.validators import URLValidationError, is_playlist_url, validate_youtube_url


class ValidateYouTubeURLTest(unittest.TestCase):
    def test_accepts_watch_short_and_playlist_urls(self):
        watch = validate_youtube_url("https://www.youtube.com/watch?v=BaW_jenozKc")
        short = validate_youtube_url("https://www.youtube.com/shorts/abc123")
        playlist = validate_youtube_url("https://www.youtube.com/playlist?list=PL123")

        self.assertIn("watch?v=BaW_jenozKc", watch)
        self.assertIn("/shorts/abc123", short)
        self.assertTrue(is_playlist_url(playlist))

    def test_adds_scheme_for_common_youtube_hosts(self):
        url = validate_youtube_url("youtu.be/BaW_jenozKc")
        self.assertEqual(url, "https://youtu.be/BaW_jenozKc")

    def test_rejects_non_youtube_urls(self):
        with self.assertRaises(URLValidationError):
            validate_youtube_url("https://example.com/watch?v=BaW_jenozKc")

    def test_rejects_credential_urls(self):
        with self.assertRaises(URLValidationError):
            validate_youtube_url("https://user:pass@www.youtube.com/watch?v=BaW_jenozKc")


if __name__ == "__main__":
    unittest.main()

