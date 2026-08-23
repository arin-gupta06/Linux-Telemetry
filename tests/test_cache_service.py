import unittest
from app.cache.cache_service import CacheService
from app.cache.models import (
    BattleMetricsEntry,
    BattleParticipantMetrics,
    ExecutionTelemetryEntry,
    PinoLogEntry,
    RawTelemetryPoint,
)


class TestCacheService(unittest.TestCase):
    def setUp(self):
        self.cache = CacheService()

    def test_raw_store_ring_buffer(self):
        for i in range(25):
            pt = RawTelemetryPoint(
                cpu_percent=float(i),
                ram_percent=50.0,
                active_workers=2,
                throughput_rps=float(i * 10),
            )
            self.cache.raw_store.add_point(pt)

        summary = self.cache.raw_store.get_summary()
        self.assertEqual(summary["count"], 25)
        self.assertEqual(summary["current_cpu"], 24.0)

    def test_log_store_search(self):
        entry = PinoLogEntry(
            id="log-1",
            level=50,
            level_name="error",
            time=1714000000000,
            iso_time="2026-08-22T00:00:00Z",
            msg="Database connection timeout",
            submission_id="sub-100",
        )
        self.cache.log_store.add_log(entry)

        results = self.cache.log_store.get_recent(query="timeout")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].submission_id, "sub-100")

    def test_battle_store(self):
        p1 = BattleParticipantMetrics(user_id="p1", execution_time_ms=10.0)
        p2 = BattleParticipantMetrics(user_id="p2", execution_time_ms=20.0)
        battle = BattleMetricsEntry(
            battle_id="b-99",
            player1=p1,
            player2=p2,
            winner_id="p1",
            speed_delta_ms=10.0,
        )
        self.cache.battle_store.add_or_update(battle)
        retrieved = self.cache.battle_store.get("b-99")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.winner_id, "p1")


if __name__ == "__main__":
    unittest.main()
