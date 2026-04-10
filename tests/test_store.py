from __future__ import annotations

import unittest

from app.models import JobStatus
from app.store import JobStore


class JobStoreTest(unittest.TestCase):
    def test_create_update_and_find_active_job(self):
        store = JobStore()

        job = store.create("https://www.youtube.com/watch?v=BaW_jenozKc", quality="best")
        self.assertEqual(job.status, JobStatus.QUEUED)
        self.assertEqual(job.quality, "best")

        active = store.find_active_by_url(job.source_url)
        self.assertIsNotNone(active)
        self.assertEqual(active.id, job.id)

        updated = store.update(
            job.id,
            status=JobStatus.RUNNING,
            progress=42.5,
            downloaded_bytes=100,
            total_bytes=200,
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, JobStatus.RUNNING)
        self.assertEqual(updated.progress, 42.5)
        self.assertEqual(store.find_active().id, job.id)

        store.update(job.id, status=JobStatus.COMPLETED, progress=100)
        self.assertIsNone(store.find_active_by_url(job.source_url))
        self.assertIsNone(store.find_active())

    def test_create_replaces_completed_jobs(self):
        store = JobStore()
        first = store.create("https://www.youtube.com/watch?v=BaW_jenozKc")
        store.update(first.id, status=JobStatus.COMPLETED, progress=100)

        second = store.create("https://www.youtube.com/watch?v=jNQXAC9IVRw")

        self.assertIsNone(store.get(first.id))
        self.assertEqual(store.get(second.id), second)
        self.assertEqual(store.list_recent(), [second])


if __name__ == "__main__":
    unittest.main()
