import threading
import time
import unittest

from backend.core import AnalysisRequest, JobManager, SlidingWindowLimiter, sanitize_public_payload


class AnalysisRequestTests(unittest.TestCase):
    def test_normalizes_supported_oce_id(self):
        request = AnalysisRequest(" Geolonwe#OC ", "OC1", 10).normalized()
        self.assertEqual(request.riot_id, "Geolonwe#OC")
        self.assertEqual(request.platform, "oc1")

    def test_rejects_unsupported_platform_and_excessive_history(self):
        with self.assertRaises(ValueError):
            AnalysisRequest("Player#NA1", "na1", 10).normalized()
        with self.assertRaises(ValueError):
            AnalysisRequest("Player#OC", "oc1", 21).normalized()

    def test_public_payload_strips_stable_riot_identifiers(self):
        payload = sanitize_public_payload({
            "puuid": "private",
            "nested": [{"matchId": "OC1_123", "champion": "Ashe"}],
        })
        self.assertEqual(payload, {"nested": [{"champion": "Ashe"}]})


class LimiterTests(unittest.TestCase):
    def test_sliding_window(self):
        limiter = SlidingWindowLimiter(2, 60)
        self.assertTrue(limiter.allow("client", now=100))
        self.assertTrue(limiter.allow("client", now=101))
        self.assertFalse(limiter.allow("client", now=102))
        self.assertTrue(limiter.allow("client", now=161))


class JobManagerTests(unittest.TestCase):
    def test_deduplicates_active_job_and_caches_completed_result(self):
        release = threading.Event()
        calls = []

        def analyzer(request):
            calls.append(request.riot_id)
            release.wait(2)
            return {"playerCase": {"meta": {"riotId": request.riot_id}}, "replays": {}}

        manager = JobManager(analyzer, cache_ttl_seconds=60)
        request = AnalysisRequest("Player#OC", "oc1", 10)
        first, cached = manager.submit(request)
        second, second_cached = manager.submit(request)
        self.assertFalse(cached)
        self.assertFalse(second_cached)
        self.assertEqual(first.job_id, second.job_id)
        release.set()
        deadline = time.time() + 2
        while time.time() < deadline and manager.get(first.job_id).status != "completed":
            time.sleep(0.01)
        self.assertEqual(manager.get(first.job_id).status, "completed")
        third, third_cached = manager.submit(request)
        self.assertTrue(third_cached)
        self.assertEqual(third.status, "completed")
        self.assertEqual(calls, ["Player#OC"])

    def test_public_failure_does_not_expose_exception_details(self):
        def analyzer(_request):
            raise RuntimeError("secret upstream detail")

        manager = JobManager(analyzer)
        record, _ = manager.submit(AnalysisRequest("Player#OC"))
        deadline = time.time() + 2
        while time.time() < deadline and manager.get(record.job_id).status not in {"failed", "completed"}:
            time.sleep(0.01)
        public = manager.get(record.job_id).public()
        self.assertEqual(public["status"], "failed")
        self.assertNotIn("secret upstream detail", public["error"])


if __name__ == "__main__":
    unittest.main()
