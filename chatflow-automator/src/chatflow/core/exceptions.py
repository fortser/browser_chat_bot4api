"""Custom exceptions for ChatFlow Automator."""


class ChatFlowError(Exception):
    """Base exception for all ChatFlow errors."""
    
    def __init__(self, message: str = "", details: str = ""):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class BrowserError(ChatFlowError):
    """Error related to browser operations."""
    pass


class ConnectionError(ChatFlowError):
    """Error related to connection operations."""
    pass


class TaskError(ChatFlowError):
    """Error related to task operations."""
    pass


class AdapterError(ChatFlowError):
    """Error related to adapter operations."""
    pass


class ConfigError(ChatFlowError):
    """Error related to configuration."""
    pass


class StorageError(ChatFlowError):
    """Error related to storage operations."""
    pass


class ValidationError(ChatFlowError):
    """Error related to data validation."""
    pass


class TimeoutError(ChatFlowError):
    """Error when operation times out."""
    pass
