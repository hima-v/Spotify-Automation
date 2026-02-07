"""Structured logging with redaction of tokens and secrets (CWE-532, CWE-359)."""
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any


REDACT_PATTERNS = [
    (re.compile(r"\b(access_token|refresh_token|token|secret|password|api_key)=['\"]?[\w\-\.]+", re.I), r"\1=***"),
    (re.compile(r"Bearer\s+[\w\-\.]+", re.I), "Bearer ***"),
    (re.compile(r"\b[A-Za-z0-9\-_]{20,}\.([A-Za-z0-9\-_]{20,}\.){2}[A-Za-z0-9\-_]{20,}\b"), "***"),
]


def redact_message(msg: str) -> str:
    if not isinstance(msg, str):
        return str(msg)
    out = msg
    for pattern, repl in REDACT_PATTERNS:
        out = pattern.sub(repl, out)
    return out


class RedactingFormatter(logging.Formatter):
    """Formats log records with message redaction; does not mutate the record."""

    def format(self, record: logging.LogRecord) -> str:
        msg = redact_message(record.getMessage())
        s = f"{self.formatTime(record)} {record.levelname} [{record.name}] {msg}"
        if record.exc_info:
            s += "\n" + self.formatException(record.exc_info)
        return s


class JsonFormatter(logging.Formatter):
    """JSON log lines with redacted message."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_message(record.getMessage()),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """Set up root logger with redaction. Call once at app startup."""
    root = logging.getLogger()
    root.setLevel(level.upper())
    for h in root.handlers[:]:
        root.removeHandler(h)
    handler = logging.StreamHandler()
    handler.setLevel(level.upper())
    handler.setFormatter(JsonFormatter() if json_logs else RedactingFormatter())
    root.addHandler(handler)
