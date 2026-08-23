#!/usr/bin/env python3
"""
AlgoFight Linux Standalone Telemetry & Evaluation Server Runner
"""

import argparse
import os
import sys
import uvicorn
from app.config import settings
from app.logging_utils import get_logger

logger = get_logger("runner")


def main():
    parser = argparse.ArgumentParser(description="AlgoFight Linux Standalone Server")
    parser.add_argument("--host", type=str, default=settings.host, help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=settings.port, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    print("=" * 60)
    print("  ALGOFIGHT LINUX STANDALONE TELEMETRY & STRESS SERVER")
    print(f"  Listening on: http://{args.host}:{args.port}")
    print(f"  Dashboard UI: http://{args.host}:{args.port}/dashboard")
    print(f"  Prometheus:   http://{args.host}:{args.port}/metrics")
    print(f"  SSE Stream:   http://{args.host}:{args.port}/api/v1/stream")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
        access_log=False,
    )


if __name__ == "__main__":
    main()
