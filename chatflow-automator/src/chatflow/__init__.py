"""ChatFlow Automator - Browser automation for chat interfaces."""

__version__ = "0.1.0"
__author__ = "ChatFlow Team"

from .core.types import (
    TaskStatus,
    BrowserStatus,
    ProxyConfig,
    BrowserConfig,
    ConnectionConfig,
    TaskCard,
    TaskSequence,
    TaskResult,
    SessionResult,
)

__all__ = [
    "__version__",
    "TaskStatus",
    "BrowserStatus",
    "ProxyConfig",
    "BrowserConfig",
    "ConnectionConfig",
    "TaskCard",
    "TaskSequence",
    "TaskResult",
    "SessionResult",
]
