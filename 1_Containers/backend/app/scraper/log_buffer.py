"""In-memory ring buffer that captures scraper log records for the live log API."""

import logging
import threading
import time
from collections import deque

_lock = threading.Lock()
_buffer: deque = deque(maxlen=1000)
_counter = 0


class BufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        global _counter
        entry_time = time.strftime("%H:%M:%S", time.localtime(record.created))
        with _lock:
            _counter += 1
            _buffer.append(
                {
                    "id": _counter,
                    "time": entry_time,
                    "level": record.levelname,
                    "message": record.getMessage(),
                }
            )


def get_logs(after: int = 0) -> list[dict]:
    with _lock:
        return [entry for entry in _buffer if entry["id"] > after]


def setup() -> None:
    """Attach the buffer handler to all scraper loggers (idempotent)."""
    logger = logging.getLogger("app.scraper")
    if not any(isinstance(h, BufferHandler) for h in logger.handlers):
        logger.addHandler(BufferHandler())
