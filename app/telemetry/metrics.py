"""
Prometheus Metrics Registry with Graceful Fallback
"""

try:
    from prometheus_client import (
        REGISTRY,
        Counter as PromCounter,
        Gauge as PromGauge,
        Histogram as PromHistogram,
        generate_latest,
    )
    PROMETHEUS_AVAILABLE = True
except ModuleNotFoundError:
    PROMETHEUS_AVAILABLE = False
    REGISTRY = None

    # Dummy metric classes for environments where prometheus_client is not yet installed
    class DummyMetric:
        def __init__(self, *args, **kwargs): pass
        def set(self, val): pass
        def inc(self, amount=1): pass
        def observe(self, val): pass
        def labels(self, *args, **kwargs): return self

    PromGauge = DummyMetric
    PromCounter = DummyMetric
    PromHistogram = DummyMetric

    def generate_latest(registry=None):
        return b"# prometheus_client not installed in current environment\n"

# Core Telemetry Gauges
cpu_gauge = PromGauge("algofight_cpu_percent", "Host Linux CPU utilization percentage")
ram_gauge = PromGauge("algofight_ram_percent", "Host Linux RAM utilization percentage")
active_workers_gauge = PromGauge("algofight_active_workers", "Number of active workers in pool")
throughput_gauge = PromGauge("algofight_throughput_rps", "Current throughput in requests/jobs per second")
light_queue_gauge = PromGauge("algofight_light_queue_depth", "Depth of light execution queue")
heavy_queue_gauge = PromGauge("algofight_heavy_queue_gauge", "Depth of heavy execution queue")
active_battles_gauge = PromGauge("algofight_active_battles", "Number of currently active 1v1 battles")

# Event Counters
logs_ingested_counter = PromCounter("algofight_pino_logs_total", "Total Pino structured logs ingested", ["level"])
verdicts_counter = PromCounter("algofight_execution_verdicts_total", "Total execution verdicts", ["verdict", "language"])
battles_counter = PromCounter("algofight_battles_total", "Total battles completed")

# Latency Histograms
execution_duration_histogram = PromHistogram(
    "algofight_execution_duration_seconds",
    "Per-submission execution duration",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
compile_duration_histogram = PromHistogram(
    "algofight_compile_duration_seconds",
    "Code compilation duration",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)
queue_wait_histogram = PromHistogram(
    "algofight_queue_wait_seconds",
    "Time spent waiting in queue before processing",
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


def get_prometheus_metrics_bytes() -> bytes:
    """Generate Prometheus metric scrape payload."""
    return generate_latest(REGISTRY)
