from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class StressConfig(BaseModel):
    total_jobs: int = Field(default=4000, ge=1, le=100_000)
    users: int = Field(default=250, ge=1, le=10_000)
    heavy_ratio: float = Field(default=0.15, ge=0.0, le=1.0)
    light_iterations: int = Field(default=350_000, ge=1_000)
    heavy_iterations: int = Field(default=1_400_000, ge=1_000)
    failure_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    max_retries: int = Field(default=2, ge=0, le=10)
    scenario: str = Field(default="concurrent")  # concurrent, sustained, peak_burst


class StressStatus(BaseModel):
    state: str = "idle"  # idle, starting, running, stopping, completed, stopped, failed
    progress_percent: float = 0.0
    total_jobs: int = 0
    completed_jobs: int = 0
    successful_jobs: int = 0
    failed_jobs: int = 0
    retry_events: int = 0
    recovered_jobs: int = 0
    active_workers: int = 0
    light_queue_depth: int = 0
    heavy_queue_depth: int = 0
    processing_jobs: int = 0
    throughput_rps: float = 0.0
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    elapsed_seconds: float = 0.0
    queue_wait_seconds: Dict[str, float] = Field(default_factory=dict)
    end_to_end_latency_seconds: Dict[str, float] = Field(default_factory=dict)
    job_distribution: Dict[str, int] = Field(default_factory=dict)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    last_error: Optional[str] = None


class StressReport(BaseModel):
    report_id: str
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
    job_distribution: Dict[str, int]
    queue_wait_seconds: Dict[str, float]
    execution_duration_seconds: Dict[str, float]
    end_to_end_latency_seconds: Dict[str, float]
    light_end_to_end_latency_seconds: Dict[str, float]
    heavy_end_to_end_latency_seconds: Dict[str, float]
    fairness: Dict[str, Any]
    config: Dict[str, Any]
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    last_error: Optional[str] = None
