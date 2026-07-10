"""
Logging configuration for Atomic Search.

Provides structured, privacy-preserving logging.
"""

import json
import logging
import sys
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class LogLevel(Enum):
    """Log levels."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


@dataclass
class LogEntry:
    """Single log entry."""
    timestamp: str
    level: str
    message: str
    logger: str
    context: Dict[str, Any] = field(default_factory=dict)


class PrivacyPreservingFormatter(logging.Formatter):
    """Formatter that removes sensitive data."""

    SENSITIVE_KEYS = {
        'password', 'secret', 'token', 'api_key', 'apikey',
        'auth', 'credential', 'key', 'authorization'
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format log record."""
        # Remove sensitive data
        if hasattr(record, 'extra'):
            record.extra = self._sanitize_dict(record.extra)

        if hasattr(record, 'args') and record.args:
            record.args = tuple(
                self._sanitize_value(arg) for arg in record.args
            )

        return super().format(record)

    def _sanitize_dict(self, data: Dict) -> Dict:
        """Sanitize dictionary values."""
        if not isinstance(data, dict):
            return data

        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                sanitized[key] = '[REDACTED]'
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            else:
                sanitized[key] = value

        return sanitized

    def _sanitize_value(self, value: Any) -> Any:
        """Sanitize a value."""
        if isinstance(value, str):
            for key in self.SENSITIVE_KEYS:
                if key in value.lower():
                    return '[REDACTED]'
        return value


class MemoryHandler(logging.Handler):
    """Handler that stores logs in memory."""

    def __init__(self, max_entries: int = 1000):
        super().__init__()
        self.entries: deque = deque(maxlen=max_entries)
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord):
        """Emit a log entry."""
        entry = LogEntry(
            timestamp=datetime.utcnow().isoformat(),
            level=record.levelname,
            message=self.format(record),
            logger=record.name,
            context=getattr(record, 'extra', {})
        )

        with self._lock:
            self.entries.append(entry)

    def get_entries(
        self,
        level: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> List[LogEntry]:
        """Get log entries with filters."""
        with self._lock:
            entries = list(self.entries)

        if level:
            entries = [e for e in entries if e.level == level]

        if since:
            since_iso = since.isoformat()
            entries = [e for e in entries if e.timestamp >= since_iso]

        return entries

    def clear(self):
        """Clear all entries."""
        with self._lock:
            self.entries.clear()

    def to_dict(self) -> List[Dict]:
        """Convert entries to dictionary."""
        return [asdict(e) for e in self.entries]


class AtomicLogger:
    """Atomic Search logger with privacy features."""

    def __init__(self, name: str = 'atomic_search'):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self._memory_handler = MemoryHandler()
        self._setup_handlers()

    def _setup_handlers(self):
        """Setup logging handlers."""
        # Console handler
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)

        formatter = PrivacyPreservingFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console.setFormatter(formatter)

        # Memory handler
        self._memory_handler.setFormatter(formatter)

        # Add handlers
        self.logger.addHandler(console)
        self.logger.addHandler(self._memory_handler)

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """Log info message."""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error message."""
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self.logger.critical(message, extra=kwargs)

    def search(self, query: str, results_count: int, duration_ms: float, **kwargs):
        """Log search event."""
        self.info(
            f"Search: '{query}' -> {results_count} results in {duration_ms:.2f}ms",
            query_hash=hashlib.md5(query.encode()).hexdigest()[:8],
            results_count=results_count,
            duration_ms=duration_ms,
            **kwargs
        )

    def api_request(self, endpoint: str, method: str, status: int, duration_ms: float):
        """Log API request."""
        self.info(
            f"API: {method} {endpoint} -> {status} ({duration_ms:.2f}ms)",
            endpoint=endpoint,
            method=method,
            status=status,
            duration_ms=duration_ms
        )

    def security_event(self, event_type: str, details: str, severity: str = 'medium'):
        """Log security event."""
        self.warning(
            f"Security [{severity}]: {event_type} - {details}",
            event_type=event_type,
            severity=severity
        )

    def get_logs(self, level: Optional[str] = None, since: Optional[datetime] = None) -> List[Dict]:
        """Get logs from memory."""
        return self._memory_handler.to_dict()

    def clear_logs(self):
        """Clear logs from memory."""
        self._memory_handler.clear()

    def disable_console(self):
        """Disable console logging."""
        for handler in self.logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                self.logger.removeHandler(handler)

    def enable_console(self):
        """Enable console logging."""
        if not any(isinstance(h, logging.StreamHandler) and h.stream == sys.stdout for h in self.logger.handlers):
            console = logging.StreamHandler(sys.stdout)
            console.setFormatter(PrivacyPreservingFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(console)


# Import hashlib for search logging
import hashlib

# Global logger
logger = AtomicLogger()
