from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.cache.models import BattleParticipantMetrics, TestCaseTrace


class ExecutionIngestPayload(BaseModel):
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
    timestamp: Optional[float] = None


class BattleIngestPayload(BaseModel):
    battle_id: str
    room_id: Optional[str] = None
    battle_type: str = "1v1"  # 1v1, MULTIPLAYER, SOLO_AI, TOURNAMENT, PRACTICE
    problem_id: Optional[str] = None
    problem_title: str = "Algorithm Challenge"
    status: str = "FINISHED"
    duration_seconds: float = 0.0
    participants: List[BattleParticipantMetrics] = Field(default_factory=list)
    player1: Optional[BattleParticipantMetrics] = None
    player2: Optional[BattleParticipantMetrics] = None
    winner_id: Optional[str] = None
    speed_delta_ms: Optional[float] = None
    memory_delta_kb: Optional[float] = None
    rankings: List[Dict[str, Any]] = Field(default_factory=list)
    timestamp: Optional[float] = None


class PinoLogBatchPayload(BaseModel):
    logs: List[Dict[str, Any]] = Field(default_factory=list)


class SystemVitals(BaseModel):
    timestamp: float = Field(default_factory=lambda: datetime.now(timezone.utc).timestamp())
    iso_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    cpu_percent: float
    per_cpu_percent: List[float] = Field(default_factory=list)
    ram_percent: float
    ram_used_mb: float
    ram_total_mb: float
    ram_free_mb: float
    swap_percent: float = 0.0
    load_avg: List[float] = Field(default_factory=list)
    active_workers: int = 0
    light_queue_depth: int = 0
    heavy_queue_depth: int = 0
    throughput_rps: float = 0.0
    active_battles: int = 0
    uptime_seconds: float = 0.0
