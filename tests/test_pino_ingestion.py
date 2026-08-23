import json
import unittest
from app.telemetry.pino_parser import PinoParser


class TestPinoIngestion(unittest.TestCase):
    def test_parse_standard_pino_log(self):
        raw = {
            "level": 30,
            "time": 1714000000000,
            "pid": 4120,
            "hostname": "algofight-node-1",
            "name": "worker",
            "msg": "Job started",
            "submissionId": "sub-1234",
            "userId": "user-88",
        }
        entry = PinoParser.parse_log(raw)
        self.assertEqual(entry.level, 30)
        self.assertEqual(entry.level_name, "info")
        self.assertEqual(entry.submission_id, "sub-1234")
        self.assertEqual(entry.user_id, "user-88")
        self.assertEqual(entry.msg, "Job started")

    def test_extract_execution_telemetry_from_pino(self):
        raw = {
            "level": 30,
            "msg": "submission.completed: execution succeeded",
            "submissionId": "sub-9999",
            "userId": "user-42",
            "problemId": "binary-search",
            "executionTimeMs": 34.5,
            "cpuTimeMs": 32.1,
            "compileTimeMs": 120.0,
            "peakMemoryKb": 15200,
            "verdict": "ACCEPTED",
            "passCount": 8,
            "totalTestcases": 8,
        }
        entry = PinoParser.parse_log(raw)
        telemetry = PinoParser.extract_execution_telemetry(entry)
        self.assertIsNotNone(telemetry)
        self.assertEqual(telemetry.submission_id, "sub-9999")
        self.assertEqual(telemetry.execution_time_ms, 34.5)
        self.assertEqual(telemetry.compile_time_ms, 120.0)
        self.assertEqual(telemetry.verdict, "ACCEPTED")
        self.assertEqual(telemetry.pass_count, 8)

    def test_extract_battle_telemetry_from_pino(self):
        raw = {
            "level": 30,
            "msg": "battle.finished: match completed",
            "battleId": "battle-555",
            "roomId": "room-12",
            "durationSeconds": 18.2,
            "player1": {
                "userId": "alice",
                "executionTimeMs": 25.0,
                "peakMemoryKb": 12000,
                "score": 100,
            },
            "player2": {
                "userId": "bob",
                "executionTimeMs": 40.0,
                "peakMemoryKb": 18000,
                "score": 100,
            },
            "winnerId": "alice",
        }
        entry = PinoParser.parse_log(raw)
        battle = PinoParser.extract_battle_telemetry(entry)
        self.assertIsNotNone(battle)
        self.assertEqual(battle.battle_id, "battle-555")
        self.assertEqual(battle.winner_id, "alice")
        self.assertEqual(battle.speed_delta_ms, 15.0)


if __name__ == "__main__":
    unittest.main()
