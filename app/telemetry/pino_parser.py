import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.cache.models import (
    BattleMetricsEntry,
    BattleParticipantMetrics,
    ExecutionTelemetryEntry,
    PinoLogEntry,
)
from app.logging_utils import PINO_LEVEL_NAMES, PINO_LEVELS


class PinoParser:
    """Parser and Telemetry Extractor for Pino-formatted structured logs."""

    @staticmethod
    def parse_log(raw_input: str | Dict[str, Any]) -> PinoLogEntry:
        if isinstance(raw_input, str):
            try:
                data = json.loads(raw_input)
            except Exception:
                data = {
                    "msg": raw_input,
                    "level": 30,
                    "time": int(time.time() * 1000),
                }
        else:
            data = dict(raw_input)

        raw_level = data.get("level", 30)
        if isinstance(raw_level, str):
            level_num = PINO_LEVELS.get(raw_level.lower(), 30)
            level_name = raw_level.lower()
        else:
            level_num = int(raw_level)
            level_name = PINO_LEVEL_NAMES.get(level_num, "info")

        raw_time = data.get("time", int(time.time() * 1000))
        if isinstance(raw_time, (int, float)):
            time_ms = int(raw_time)
            if time_ms < 1_000_000_000_000:
                time_ms *= 1000
            iso_time = datetime.fromtimestamp(time_ms / 1000, tz=timezone.utc).isoformat()
        else:
            time_ms = int(time.time() * 1000)
            iso_time = datetime.now(timezone.utc).isoformat()

        req_id = data.get("reqId") or data.get("req_id") or data.get("requestId")
        sub_id = data.get("submissionId") or data.get("submission_id")
        battle_id = data.get("battleId") or data.get("battle_id") or data.get("roomId") or data.get("room_id")
        user_id = data.get("userId") or data.get("user_id")
        msg = str(data.get("msg") or data.get("message") or "")

        err = data.get("err") or data.get("error")
        if err and not isinstance(err, dict):
            err = {"message": str(err)}

        entry_id = str(uuid.uuid4())[:8]

        return PinoLogEntry(
            id=entry_id,
            level=level_num,
            level_name=level_name,
            time=time_ms,
            iso_time=iso_time,
            pid=data.get("pid", 0),
            hostname=str(data.get("hostname", "")),
            name=str(data.get("name", "algofight")),
            msg=msg,
            req_id=str(req_id) if req_id else None,
            submission_id=str(sub_id) if sub_id else None,
            battle_id=str(battle_id) if battle_id else None,
            user_id=str(user_id) if user_id else None,
            err=err,
            data=data,
            raw=data,
        )

    @classmethod
    def extract_execution_telemetry(cls, entry: PinoLogEntry) -> Optional[ExecutionTelemetryEntry]:
        data = entry.data
        msg = entry.msg.lower()

        is_exec_event = any(
            k in msg
            for k in ("submission", "execution", "execute", "verdict", "judge", "compile")
        ) or any(
            k in data
            for k in ("executionTimeMs", "cpuTimeMs", "compileTimeMs", "verdict", "testcases")
        )

        if not is_exec_event:
            return None

        sub_id = entry.submission_id or str(data.get("id", f"sub-{entry.id}"))
        user_id = entry.user_id or str(data.get("user", data.get("author", "user-unknown")))

        exec_time = float(data.get("executionTimeMs", data.get("execution_time_ms", data.get("durationMs", data.get("duration", 0.0)))))
        cpu_time = float(data.get("cpuTimeMs", data.get("cpu_time_ms", exec_time * 0.95)))
        compile_time = float(data.get("compileTimeMs", data.get("compile_time_ms", 0.0)))
        memory_kb = float(data.get("peakMemoryKb", data.get("memoryKb", data.get("memory_kb", data.get("memory", 0.0)))))
        verdict = str(data.get("verdict", data.get("status", "ACCEPTED"))).upper()

        if verdict in ("COMPLETED", "OK", "PASS", "SUCCESS"):
            verdict = "ACCEPTED"

        pass_count = int(data.get("passCount", data.get("pass_count", data.get("passed", 0))))
        total_tests = int(data.get("totalTestcases", data.get("total_testcases", data.get("tests", pass_count))))

        return ExecutionTelemetryEntry(
            submission_id=sub_id,
            user_id=user_id,
            problem_id=str(data.get("problemId", data.get("problem_id", ""))) or None,
            battle_id=entry.battle_id,
            language=str(data.get("language", data.get("lang", "cpp"))),
            compile_time_ms=compile_time,
            execution_time_ms=exec_time,
            cpu_time_ms=cpu_time,
            peak_memory_kb=memory_kb,
            verdict=verdict,
            exit_code=int(data.get("exitCode", data.get("exit_code", 0))),
            pass_count=pass_count,
            total_testcases=total_tests,
            timestamp=entry.time / 1000.0,
            iso_time=entry.iso_time,
        )

    @classmethod
    def extract_battle_telemetry(cls, entry: PinoLogEntry) -> Optional[BattleMetricsEntry]:
        data = entry.data
        msg = entry.msg.lower()

        is_battle_event = "battle" in msg or "room" in msg or "match" in msg or "participants" in data or "player1" in data

        if not is_battle_event or not entry.battle_id:
            return None

        participants: List[BattleParticipantMetrics] = []

        if "participants" in data and isinstance(data["participants"], list):
            for idx, p in enumerate(data["participants"]):
                participants.append(
                    BattleParticipantMetrics(
                        user_id=str(p.get("userId", p.get("user_id", f"player-{idx+1}"))),
                        username=str(p.get("username", f"Player {idx+1}")),
                        language=str(p.get("language", "cpp")),
                        execution_time_ms=float(p.get("executionTimeMs", p.get("execution_time_ms", 0.0))),
                        cpu_time_ms=float(p.get("cpuTimeMs", p.get("cpu_time_ms", 0.0))),
                        peak_memory_kb=float(p.get("peakMemoryKb", p.get("memoryKb", 0.0))),
                        score=int(p.get("score", 0)),
                        rank=int(p.get("rank", idx + 1)),
                        verdict=str(p.get("verdict", "ACCEPTED")),
                        tests_passed=int(p.get("testsPassed", p.get("tests_passed", 0))),
                        tests_total=int(p.get("testsTotal", p.get("tests_total", 0))),
                    )
                )
        elif "player1" in data or "player2" in data:
            p1_data = data.get("player1", {})
            p2_data = data.get("player2", {})
            p1 = BattleParticipantMetrics(
                user_id=str(p1_data.get("userId", p1_data.get("user_id", "player1"))),
                username=str(p1_data.get("username", "Player 1")),
                language=str(p1_data.get("language", "cpp")),
                execution_time_ms=float(p1_data.get("executionTimeMs", 0.0)),
                cpu_time_ms=float(p1_data.get("cpuTimeMs", 0.0)),
                peak_memory_kb=float(p1_data.get("peakMemoryKb", 0.0)),
                score=int(p1_data.get("score", 0)),
                verdict=str(p1_data.get("verdict", "ACCEPTED")),
                tests_passed=int(p1_data.get("testsPassed", 0)),
                tests_total=int(p1_data.get("testsTotal", 0)),
            )
            p2 = BattleParticipantMetrics(
                user_id=str(p2_data.get("userId", p2_data.get("user_id", "player2"))),
                username=str(p2_data.get("username", "Player 2")),
                language=str(p2_data.get("language", "cpp")),
                execution_time_ms=float(p2_data.get("executionTimeMs", 0.0)),
                cpu_time_ms=float(p2_data.get("cpuTimeMs", 0.0)),
                peak_memory_kb=float(p2_data.get("peakMemoryKb", 0.0)),
                score=int(p2_data.get("score", 0)),
                verdict=str(p2_data.get("verdict", "ACCEPTED")),
                tests_passed=int(p2_data.get("testsPassed", 0)),
                tests_total=int(p2_data.get("testsTotal", 0)),
            )
            participants = [p1, p2]

        battle_type = str(data.get("battleType", data.get("battle_type", "1v1" if len(participants) <= 2 else "MULTIPLAYER")))

        speed_delta = 0.0
        memory_delta = 0.0
        if len(participants) >= 2:
            speed_delta = abs(participants[0].execution_time_ms - participants[1].execution_time_ms)
            memory_delta = abs(participants[0].peak_memory_kb - participants[1].peak_memory_kb)

        p1 = participants[0] if len(participants) > 0 else None
        p2 = participants[1] if len(participants) > 1 else None

        return BattleMetricsEntry(
            battle_id=entry.battle_id,
            room_id=str(data.get("roomId", entry.battle_id)),
            battle_type=battle_type,
            problem_id=str(data.get("problemId", "prob-1")),
            problem_title=str(data.get("problemTitle", "Algorithm Battle")),
            status=str(data.get("status", "FINISHED")),
            duration_seconds=float(data.get("durationSeconds", data.get("duration", 0.0))),
            participants=participants,
            player1=p1,
            player2=p2,
            winner_id=str(data.get("winnerId", data.get("winner", ""))) or None,
            speed_delta_ms=speed_delta,
            memory_delta_kb=memory_delta,
            rankings=data.get("rankings", []),
            timestamp=entry.time / 1000.0,
            iso_time=entry.iso_time,
        )
