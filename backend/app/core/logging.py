from __future__ import annotations

import json
import logging
import sys
import time
from contextvars import ContextVar
from typing import Any, Optional

REQUEST_ID_CTX: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
TENANT_ID_CTX: ContextVar[Optional[str]] = ContextVar("tenant_id", default=None)


def get_request_id() -> Optional[str]:
    return REQUEST_ID_CTX.get()


def get_tenant_id() -> Optional[str]:
    return TENANT_ID_CTX.get()


class StructuredJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + ".{:03.0f}Z".format(record.msecs),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        request_id = get_request_id()
        if request_id:
            log_entry["request_id"] = request_id

        tenant_id = get_tenant_id()
        if tenant_id:
            log_entry["tenant_id"] = tenant_id

        if record.exc_info and record.exc_info[0] is not None:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        if hasattr(record, "extra_data"):
            log_entry["data"] = record.extra_data

        return json.dumps(log_entry, default=str)


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or ""
        record.tenant_id = get_tenant_id() or ""
        return True


def configure_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    if json_format:
        formatter: logging.Formatter = StructuredJSONFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    handler.setFormatter(formatter)
    handler.addFilter(CorrelationFilter())

    root.addHandler(handler)
    root.setLevel(handler.level)

    for noisy in ("httpcore", "httpx", "openai", "anthropic", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
