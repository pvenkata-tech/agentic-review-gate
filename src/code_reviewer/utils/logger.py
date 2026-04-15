"""
Structured JSON Logging: Production-grade logging for the review system.

This module configures structlog for JSON-formatted logs with:
- Request tracing via correlation IDs
- Agent execution context
- Performance metrics
- Error tracking
"""

import logging
import json
import sys
from typing import Any, Dict
from datetime import datetime
from uuid import uuid4

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False


class JSONFormatter(logging.Formatter):
    """Custom formatter for JSON-structured logs."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        
        # Add custom fields from extra
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in ("name", "msg", "args", "created", "filename", 
                              "funcName", "levelname", "levelno", "lineno", 
                              "module", "msecs", "message", "pathname", "process",
                              "processName", "relativeCreated", "thread", "threadName"):
                    log_obj[key] = value
        
        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_obj)


class ReviewLogger:
    """High-level logger for the review system."""
    
    _instance = None
    _context: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the logger."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._logger = logging.getLogger("code-reviewer")
            self._setup_handlers()
            self._request_id = str(uuid4())
    
    def _setup_handlers(self) -> None:
        """Configure logging handlers."""
        # Console handler with JSON formatter
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(JSONFormatter())
        
        # Log level
        log_level = logging.INFO  # In production, read from config
        self._logger.setLevel(log_level)
        console_handler.setLevel(log_level)
        
        # Remove existing handlers to avoid duplicates
        self._logger.handlers.clear()
        self._logger.addHandler(console_handler)
    
    def set_context(self, **kwargs) -> None:
        """Set context variables for the current request."""
        self._context.update(kwargs)
    
    def get_context(self) -> Dict[str, Any]:
        """Get current context."""
        return {
            "request_id": self._request_id,
            **self._context,
        }
    
    def info(self, message: str, **kwargs) -> None:
        """Log info level message."""
        self._logger.info(message, extra={**self.get_context(), **kwargs})
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning level message."""
        self._logger.warning(message, extra={**self.get_context(), **kwargs})
    
    def error(self, message: str, **kwargs) -> None:
        """Log error level message."""
        self._logger.error(message, extra={**self.get_context(), **kwargs})
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug level message."""
        self._logger.debug(message, extra={**self.get_context(), **kwargs})
    
    def log_agent_execution(
        self,
        agent_id: str,
        status: str,
        execution_time_ms: float,
        findings_count: int,
        **kwargs
    ) -> None:
        """Log agent execution details."""
        self.info(
            f"Agent execution: {agent_id}",
            agent_id=agent_id,
            status=status,
            execution_time_ms=execution_time_ms,
            findings_count=findings_count,
            **kwargs,
        )
    
    def log_pr_review_start(self, pr_number: int, author: str) -> None:
        """Log start of PR review."""
        self.info(
            f"Starting PR review #{pr_number}",
            pr_number=pr_number,
            author=author,
        )
    
    def log_pr_review_complete(
        self,
        pr_number: int,
        total_findings: int,
        is_blocked: bool,
        execution_time_ms: float,
    ) -> None:
        """Log completion of PR review."""
        self.info(
            f"Completed PR review #{pr_number}",
            pr_number=pr_number,
            total_findings=total_findings,
            is_blocked=is_blocked,
            execution_time_ms=execution_time_ms,
        )
    
    def log_finding(
        self,
        agent_id: str,
        file_path: str,
        finding_type: str,
        severity: str,
        line_number: int = None,
    ) -> None:
        """Log a finding."""
        self.debug(
            f"Finding: {finding_type}",
            agent_id=agent_id,
            file_path=file_path,
            finding_type=finding_type,
            severity=severity,
            line_number=line_number,
        )


def get_logger() -> ReviewLogger:
    """Get the singleton ReviewLogger instance."""
    return ReviewLogger()


# Configure structlog if available
if STRUCTLOG_AVAILABLE:
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
