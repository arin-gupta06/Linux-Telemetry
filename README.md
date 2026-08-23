# AlgoFight - Standalone Linux Telemetry, Evaluation & Stress Server

A dedicated, high-performance Linux evaluation service for **AlgoFight**. Code execution is performed on the Main Application, while this standalone Linux server serves as the unified engine for **Telemetry Collection**, **Pino Structured Log Ingestion**, **Load & Stress Benchmarking**, **Multi-Tier Caching**, and **Real-Time Statistics UI**.

---

## Architecture Diagram

```
                         ALGOFIGHT
                    Main Application
                         │
                         │ HTTP (Pino logs, telemetry & test events)
                         ▼
              ┌──────────────────────────┐
              │ Linux Evaluation Service │
              │                          │
              │ ┌──────────────────────┐ │
              │ │ Ingestion & Pino Log │ │  <-- Ingests Pino JSON logs & execution events
              │ │ Stream Processor    │ │
              │ └──────────┬───────────┘ │
              │            │              │
              │ ┌──────────▼───────────┐  │
              │ │ Telemetry Engine     │  │  <-- Processes & aggregates metrics
              │ │                      │  │
              │ │ • CPU Utilization    │  │
              │ │ • Memory (Peak RSS)  │  │
              │ │ • Compile Time       │  │
              │ │ • Execution Time     │  │
              │ │ • Individual Runs    │  │
              │ └──────────┬───────────┘  │
              │            │              │
              │ ┌──────────▼───────────┐  │
              │ │ Load & Stress Engine │  │  <-- Standalone load generation & stress analysis
              │ │                      │  │
              │ │ • Concurrent Execs   │  │
              │ │ • Sustained Load     │  │
              │ │ • Peak Load / Spikes │  │
              │ │ • Response Time (P99)│  │
              │ │ • Throughput (RPS)   │  │
              │ │ • Failure Rate       │  │
              │ └──────────┬───────────┘  │
              └────────────┼──────────────┘
                           │
                           │ telemetry stream
                           ▼
                    ┌───────────────┐
                    │     CACHE     │
                    │               │
                    │ Raw telemetry │
                    │ Battle metrics│
                    │ Execution data│
                    │ Pino log store│
                    │ Load metrics  │
                    │ Stress metrics│
                    │ Temporary data│
                    └───────┬───────┘
                            │
                            │ query
                            ▼
                     AlgoFight API
                            │
                            ▼
                      Statistics UI (with Live Pino Log Viewer)
```

---

## Core Capabilities

1. **Pino Structured Log Stream & Metric Extraction**:
   - Ingests single or batch JSON logs formatted with Pino (`POST /api/v1/telemetry/logs`).
   - Automatically detects and extracts execution telemetry (CPU time, memory RSS, compile duration, verdict, duration) from Pino logs.
   - Provides an in-memory searchable ring-buffer of structured logs with search indexing by `submissionId`, `battleId`, and level.
2. **Telemetry Engine**:
   - Gathers host Linux vitals (CPU per-core load, RAM, swap, load averages, active workers, queue depth).
   - Records per-submission execution and compilation times into Prometheus histograms and cache stores.
3. **Load & Stress Engine**:
   - Multi-worker concurrent load testing simulator with adaptive auto-scaling (scaling up/down based on CPU and queue backpressure).
   - Computes exact response time distribution ($p50, p90, p95, p99$, max) and fairness among users.
4. **1v1 Battle Telemetry**:
   - Ingests and stores head-to-head battle metrics comparing Player 1 vs Player 2 execution times, memory footprints, and verdicts.
5. **Real-Time Statistics Dashboard**:
   - Served at `/dashboard` with 60fps canvas rolling graphs, live Server-Sent Events (SSE) stream, expandable Pino log terminal, battle comparison cards, and stress test controllers.
6. **Prometheus Metrics**:
   - Scrape endpoint at `/metrics`.

---

## Getting Started

### Installation
```bash
pip install -r requirements.txt
```

### Running the Server
```bash
# Launch on port 8000
python run_server.py --port 8000

# Or run via uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Accessing the Services
- **Statistics Dashboard**: `http://localhost:8000/dashboard`
- **Swagger / OpenAPI Docs**: `http://localhost:8000/docs`
- **Prometheus Metrics**: `http://localhost:8000/metrics`
- **Live SSE Telemetry Stream**: `http://localhost:8000/api/v1/stream`

---

## API Reference

### Telemetry & Ingestion
- `POST /api/v1/telemetry/logs`: Ingest single or batch Pino JSON logs.
- `GET /api/v1/telemetry/logs`: Search & filter structured logs (`?q=...&min_level=30&submission_id=...`).
- `POST /api/v1/telemetry/ingest`: Ingest submission execution telemetry.
- `GET /api/v1/telemetry/execution/{submission_id}`: Retrieve submission execution trace.
- `POST /api/v1/telemetry/battle`: Ingest 1v1 battle telemetry.
- `GET /api/v1/telemetry/battle/{battle_id}`: Retrieve 1v1 battle stats.
- `GET /api/v1/telemetry/raw`: Retrieve raw time-series metrics.
- `GET /api/v1/telemetry/summary`: High-level summary of cached metrics.

### Load & Stress Engine
- `POST /api/v1/stress/start`: Start stress benchmark (`total_jobs`, `users`, `heavy_ratio`, `failure_rate`).
- `GET /api/v1/stress/status`: Stream current status of stress test.
- `POST /api/v1/stress/stop`: Terminate running benchmark.
- `GET /api/v1/stress/results`: Get latest stress benchmark report with percentiles ($p50/p95/p99$).

### System & Metrics
- `GET /api/v1/stats/system`: Instantaneous Linux host vitals.
- `GET /metrics`: Standard Prometheus metrics.
- `GET /api/v1/stream`: Server-Sent Events (SSE) live data stream.

# Linux-Telemetry

