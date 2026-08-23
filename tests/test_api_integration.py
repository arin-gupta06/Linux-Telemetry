import unittest
from fastapi.testclient import TestClient
from app.main import app


class TestAPIIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_healthz(self):
        res = self.client.get("/healthz")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["status"], "ok")

    def test_dashboard_html(self):
        res = self.client.get("/dashboard")
        self.assertEqual(res.status_code, 200)
        self.assertIn("ALGOFIGHT", res.text)
        self.assertIn("Pino Structured Logs", res.text)

    def test_metrics_prometheus(self):
        res = self.client.get("/metrics")
        self.assertEqual(res.status_code, 200)
        self.assertIn("algofight_cpu_percent", res.text)

    def test_pino_logs_ingest_and_query(self):
        log_payload = {
            "level": 30,
            "msg": "Worker process initialized",
            "name": "worker",
            "submissionId": "sub-api-test",
            "userId": "user-tester",
        }
        res = self.client.post("/api/v1/telemetry/logs", json=log_payload)
        self.assertEqual(res.status_code, 200)

        # Query logs
        res_query = self.client.get("/api/v1/telemetry/logs?submission_id=sub-api-test")
        self.assertEqual(res_query.status_code, 200)
        logs = res_query.json()
        self.assertGreaterEqual(len(logs), 1)
        self.assertEqual(logs[0]["submission_id"], "sub-api-test")

    def test_execution_telemetry_ingest_and_query(self):
        exec_payload = {
            "submission_id": "sub-api-exec-1",
            "user_id": "user-101",
            "language": "cpp",
            "compile_time_ms": 75.0,
            "execution_time_ms": 22.5,
            "cpu_time_ms": 20.0,
            "peak_memory_kb": 14000.0,
            "verdict": "ACCEPTED",
            "pass_count": 10,
            "total_testcases": 10,
        }
        res = self.client.post("/api/v1/telemetry/ingest", json=exec_payload)
        self.assertEqual(res.status_code, 200)

        # Query execution
        res_get = self.client.get("/api/v1/telemetry/execution/sub-api-exec-1")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["verdict"], "ACCEPTED")

    def test_battle_telemetry_ingest_and_query(self):
        battle_payload = {
            "battle_id": "battle-api-1",
            "room_id": "room-101",
            "problem_id": "two-sum",
            "player1": {
                "user_id": "player1",
                "execution_time_ms": 15.0,
                "score": 100,
            },
            "player2": {
                "user_id": "player2",
                "execution_time_ms": 30.0,
                "score": 100,
            },
            "winner_id": "player1",
        }
        res = self.client.post("/api/v1/telemetry/battle", json=battle_payload)
        self.assertEqual(res.status_code, 200)

        # Query battle
        res_get = self.client.get("/api/v1/telemetry/battle/battle-api-1")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["winner_id"], "player1")

    def test_system_stats(self):
        res = self.client.get("/api/v1/stats/system")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("cpu_percent", data)
        self.assertIn("ram_percent", data)


if __name__ == "__main__":
    unittest.main()
