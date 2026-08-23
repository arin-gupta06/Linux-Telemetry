import time
import unittest
from app.cache.cache_service import CacheService
from app.stress.engine import StressEngine
from app.stress.models import StressConfig
from app.stress.stats import latency_stats, percentile


class TestStressEngine(unittest.TestCase):
    def test_percentile_calculations(self):
        data = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
        self.assertEqual(percentile(data, 50), 55.0)
        self.assertEqual(percentile(data, 90), 91.0)

        stats = latency_stats(data)
        self.assertEqual(stats["avg"], 55.0)
        self.assertEqual(stats["min"], 10.0)
        self.assertEqual(stats["max"], 100.0)

    def test_mini_stress_run(self):
        cache = CacheService()
        engine = StressEngine(cache_service=cache)
        config = StressConfig(
            total_jobs=30,
            users=5,
            heavy_ratio=0.1,
            light_iterations=5000,
            heavy_iterations=10000,
            failure_rate=0.0,
        )

        res = engine.start(config)
        self.assertEqual(res["status"], "started")

        # Wait for completion (small run takes ~1-2 sec)
        for _ in range(30):
            time.sleep(0.2)
            status = engine.get_status()
            if status.state in {"completed", "stopped"}:
                break

        final_status = engine.get_status()
        self.assertIn(final_status.state, {"running", "completed"})
        engine.stop()


if __name__ == "__main__":
    unittest.main()
