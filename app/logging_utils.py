import json
import logging
import os
import socket
import sys
import time
from typing import Any, Dict

# Pino standard level values
PINO_LEVELS = {
    "trace": 10,
    "debug": 20,
    "info": 30,
    "warn": 40,
    "error": 50,
    "fatal": 60,
}

PINO_LEVEL_NAMES = {v: k for k, v in PINO_LEVELS.items()}
HOSTNAME = socket.gethostname()
PID = os.getpid()


class PinoJSONFormatter(logging.Formatter):
    """Formats standard python logging records into Pino-compatible JSON."""

    def __init__(self, service_name: str = "algofight-linux-service"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        level_num = PINO_LEVELS.get(record.levelname.lower(), 30)
        timestamp_ms = int(record.created * 1000)

        log_dict: Dict[str, Any] = {
            "level": level_num,
            "time": timestamp_ms,
            "pid": os.getpid(),
            "hostname": HOSTNAME,
            "name": record.name or self.service_name,
            "msg": record.getMessage(),
        }

        if record.exc_info:
            log_dict["err"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else "Exception",
                "message": str(record.exc_info[1]) if record.exc_info[1] else "",
                "stack": self.formatException(record.exc_info),
            }

        # Include custom extra fields if passed
        for key, value in record.__dict__.items():
            if key not in (
                "args",
                "asctime",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            ):
                log_dict[key] = value

        return json.dumps(log_dict)


def setup_pino_logging(service_name: str = "algofight-linux-service", level: int = logging.INFO):
    """Configure root logger with Pino JSON format."""
    root = logging.getLogger()
    root.setLevel(level)

    # Remove existing handlers
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(PinoJSONFormatter(service_name))
    root.addHandler(handler)


def get_logger(name: str = "algofight") -> logging.Logger:
    """Get a logger instance with Pino-compatible logger adapter."""
    return logging.getLogger(name)


def pino_format_dict(level: str, msg: str, **kwargs) -> Dict[str, Any]:
    """Helper to construct a raw Pino-compatible dictionary."""
    return {
        "level": PINO_LEVELS.get(level.lower(), 30),
        "time": int(time.time() * 1000),
        "pid": PID,
        "hostname": HOSTNAME,
        "name": kwargs.pop("name", "algofight"),
        "msg": msg,
        **kwargs,
    }
