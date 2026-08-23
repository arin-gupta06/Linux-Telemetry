from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RawTelemetryPoint(BaseModel):
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    iso_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cpu_percent: float
    ram_percent: float
    active_workers: int
    light_queue_depth: int = 0
    heavy_queue_depth: int = 0
    throughput_rps: float = 0.0
    active_battles: int = 0
    load_avg: List[float] = Field(default_factory=list)


class PinoLogEntry(BaseModel):
    id: str
    level: int
    level_name: str
    time: int
    iso_time: str
    pid: int = 0
    hostname: str = ""
    name: str = "algofight"
    msg: str
    req_id: Optional[str] = None
    submission_id: Optional[str] = None
    battle_id: Optional[str] = None
    user_id: Optional[str] = None
    err: Optional[Dict[str, Any]] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    raw: Dict[str, Any] = Field(default_factory=dict)


class BattleParticipantMetrics(BaseModel):
    user_id: str
    username: str = ""
    language: str = "cpp"
    execution_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    peak_memory_kb: float = 0.0
    compile_time_ms: float = 0.0
    score: int = 0
    rank: int = 1
    verdict: str = "ACCEPTED"
    tests_passed: int = 0
    tests_total: int = 0
    solved_at: Optional[str] = None
    code_length: int = 0


class BattleMetricsEntry(BaseModel):
    battle_id: str
    room_id: Optional[str] = None
    battle_type: str = "1v1"  # 1v1, MULTIPLAYER, SOLO_AI, TOURNAMENT, PRACTICE
    problem_id: Optional[str] = None
    problem_title: str = "Algorithm Challenge"
    status: str = "FINISHED"  # WAITING, READY, RUNNING, FINISHED, CANCELLED
    duration_seconds: float = 0.0
    participants: List[BattleParticipantMetrics] = Field(default_factory=list)
    player1: Optional[BattleParticipantMetrics] = None
    player2: Optional[BattleParticipantMetrics] = None
    winner_id: Optional[str] = None
    speed_delta_ms: float = 0.0
    memory_delta_kb: float = 0.0
    rankings: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    iso_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class TestCaseTrace(BaseModel):
    test_id: int
    input_sample: str = ""
    expected_output: str = ""
    actual_output: str = ""
    execution_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    memory_kb: float = 0.0
    verdict: str = "ACCEPTED"
    exit_code: int = 0
    error_message: Optional[str] = None


class ExecutionTelemetryEntry(BaseModel):
    submission_id: str
    user_id: str
    problem_id: Optional[str] = None
    battle_id: Optional[str] = None
    language: str = "cpp"
    compile_time_ms: float = 0.0
    execution_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    peak_memory_kb: float = 0.0
    verdict: str = "ACCEPTED"
    exit_code: int = 0
    pass_count: int = 0
    total_testcases: int = 0
    testcases: List[TestCaseTrace] = Field(default_factory=list)
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    iso_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class StressMetricsEntry(BaseModel):
    report_id: str
    run_id: str
    scenario: str
    status: str
    total_jobs: int
    completed_jobs: int
    successful_jobs: int
    failed_jobs: int
    retry_events: int
    recovered_jobs: int
    duration_seconds: float
    throughput_rps: float
    queue_wait_stats: Dict[str, float]
    execution_duration_stats: Dict[str, float]
    end_to_end_latency_stats: Dict[str, float]
    light_end_to_end_stats: Dict[str, float]
    heavy_end_to_end_stats: Dict[str, float]
    fairness: Dict[str, Any]
    config: Dict[str, Any]
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    iso_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
