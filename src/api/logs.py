from __future__ import annotations

import logging
from collections import deque
from datetime import datetime
from threading import Lock
from typing import Deque, Dict, List

from fastapi import APIRouter, Query


class InMemoryLogHandler(logging.Handler):
    def __init__(self, capacity: int = 500) -> None:
        super().__init__()
        self._capacity = capacity
        self._lock = Lock()
        self._records: Deque[Dict[str, str]] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        with self._lock:
            self._records.append(entry)

    def get_logs(self, limit: int) -> List[Dict[str, str]]:
        with self._lock:
            if limit <= 0 or limit >= len(self._records):
                return list(self._records)
            return list(self._records)[-limit:]

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


LOG_HANDLER = InMemoryLogHandler()
LOG_SOURCES = [
    "flows.quest.login",
    "flows.quest.logout",
    "flows.quest.results",
    "scripts.quest",
    "scripts.tricore",
    "scripts.zio",
    "scripts.xr",
]


def attach_loggers() -> None:
    for logger_name in LOG_SOURCES:
        logger = logging.getLogger(logger_name)
        if LOG_HANDLER not in logger.handlers:
            logger.addHandler(LOG_HANDLER)


log_router = APIRouter()


@log_router.get("/logs")
def read_logs(limit: int = Query(200, ge=1, le=1000)) -> Dict[str, List[Dict[str, str]]]:
    return {"logs": LOG_HANDLER.get_logs(limit)}
