"""Logging configuration and utilities."""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
import os


# Custom log format
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Log levels
LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for console output."""
    
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    
    def format(self, record: logging.LogRecord) -> str:
        # Add color if terminal supports it
        if hasattr(sys.stdout, "isatty") and sys.stdout.isatty():
            color = self.COLORS.get(record.levelname, "")
            record.levelname = f"{color}{record.levelname}{self.RESET}"
        
        return super().format(record)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    console: bool = True,
) -> None:
    """
    Setup logging configuration.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file
        console: Whether to log to console
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVELS.get(level.upper(), logging.INFO))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter(LOG_FORMAT, LOG_DATE_FORMAT))
        root_logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        root_logger.addHandler(file_handler)
    
    # Set level for third-party libraries
    logging.getLogger("playwright").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def get_log_file_path() -> Path:
    """Get default log file path."""
    from .paths import get_data_dir
    
    log_dir = get_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create log file with date
    date_str = datetime.now().strftime("%Y%m%d")
    return log_dir / f"chatflow_{date_str}.log"


class LogCapture:
    """Context manager for capturing log output."""
    
    def __init__(self, logger_name: str = ""):
        self.logger_name = logger_name
        self.logs: list[str] = []
        self._handler: Optional[logging.Handler] = None
    
    def __enter__(self) -> "LogCapture":
        logger = logging.getLogger(self.logger_name)
        
        class ListHandler(logging.Handler):
            def __init__(self, log_list: list):
                super().__init__()
                self.log_list = log_list
            
            def emit(self, record: logging.LogRecord) -> None:
                self.log_list.append(self.format(record))
        
        self._handler = ListHandler(self.logs)
        self._handler.setFormatter(logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT))
        logger.addHandler(self._handler)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._handler:
            logger = logging.getLogger(self.logger_name)
            logger.removeHandler(self._handler)
    
    def get_logs(self) -> list[str]:
        """Get captured logs."""
        return self.logs.copy()
