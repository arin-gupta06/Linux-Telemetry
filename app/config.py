import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    # Server settings
    host: str = Field(default=os.getenv("ALGOFIGHT_HOST", "0.0.0.0"))
    port: int = Field(default=int(os.getenv("ALGOFIGHT_PORT", "8000")))
    prometheus_port: int = Field(default=int(os.getenv("PROMETHEUS_PORT", "8001")))
    enable_standalone_prom_server: bool = Field(
        default=os.getenv("ENABLE_STANDALONE_PROM", "false").lower() == "true"
    )

    # Telemetry and Ingestion
    service_name: str = Field(default="algofight-linux-service")
    environment: str = Field(default=os.getenv("NODE_ENV", "development"))

    # Cache Limits
    cache_max_raw_entries: int = Field(default=50_000)
    cache_max_log_entries: int = Field(default=10_000)
    cache_max_battles: int = Field(default=5_000)
    cache_max_executions: int = Field(default=10_000)
    cache_max_stress_reports: int = Field(default=500)
    cache_ttl_seconds: int = Field(default=86_400)
    redis_url: str | None = Field(default=os.getenv("REDIS_URL", None))

    # Stress and Load Engine
    default_stress_jobs: int = Field(default=4000)
    default_stress_users: int = Field(default=250)
    default_heavy_ratio: float = Field(default=0.15)
    default_light_iterations: int = Field(default=350_000)
    default_heavy_iterations: int = Field(default=1_400_000)
    default_failure_rate: float = Field(default=0.0)
    default_max_retries: int = Field(default=2)

    min_workers: int = Field(default=2)
    max_workers: int = Field(default=max(2, int((os.cpu_count() or 2) * 0.9)))
    scale_up_cpu_threshold: float = Field(default=60.0)
    scale_down_cpu_threshold: float = Field(default=25.0)
    scale_cooldown_seconds: float = Field(default=2.0)
    join_timeout_seconds: float = Field(default=5.0)

    # Monitoring & Alerts
    alert_cpu_threshold: float = Field(default=90.0)
    alert_ram_threshold: float = Field(default=85.0)
    alert_queue_wait_p95_seconds: float = Field(default=2.0)
    heartbeat_interval_seconds: float = Field(default=0.5)
    stale_heartbeat_seconds: float = Field(default=3.0)


settings = Settings()
