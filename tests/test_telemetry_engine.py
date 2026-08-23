import unittest
from app.cache.cache_service import CacheService
from app.telemetry.engine import TelemetryEngine
from app.telemetry.models import ExecutionIngestPayload


class TestTelemetryEngine(unittest.TestCase):
    def setUp(self):
        self.cache = CacheService()
        self.engine = TelemetryEngine(cache_service=self.cache)

    def test_ingest_execution_payload(self):
        payload = ExecutionIngestPayload(
            submission_id="sub-test-1",
            user_id="user-1",
            language="python",
            execution_time_ms=45.0,
            cpu_time_ms=42.0,
            peak_memory_kb=18000.0,
            verdict="ACCEPTED",
            pass_count=5,
            total_testcases=5,
        )
        result = self.engine.ingest_execution(payload)
        self.assertEqual(result.submission_id, "sub-test-1")
        self.assertEqual(result.verdict, "ACCEPTED")

        cached = self.cache.execution_store.get("sub-test-1")
        self.assertIsNotNone(cached)
        self.assertEqual(cached.execution_time_ms, 45.0)

    def test_get_system_vitals(self):
        vitals = self.engine.get_system_vitals()
        self.assertIsInstance(vitals.cpu_percent, float)
        self.assertIsInstance(vitals.ram_percent, float)


if __name__ == "__main__":
    unittest.main()
