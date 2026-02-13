"""Base chat adapter interface with thread-safe operations."""

from abc import ABC, abstractmethod
from typing import Any, Optional, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from playwright.async_api import Page
    from ..browser.threadsafe_browser import ThreadsafeBrowser

logger = logging.getLogger(__name__)


class ChatAdapter(ABC):
    """
    Base class for chat interface adapters.
    
    Adapters encapsulate the logic for interacting with specific
    chat interfaces (finding elements, sending messages, etc.)
    
    All methods are designed to work with ThreadsafeBrowser.
    """
    
    name: str = "base"
    description: str = "Base adapter"
    
    def __init__(
        self, 
        page: "Page",
        settings: Optional[dict[str, Any]] = None,
        threadsafe_browser: Optional["ThreadsafeBrowser"] = None
    ):
        """
        Initialize adapter.
        
        Args:
            page: Playwright page instance
            settings: Adapter-specific settings
            threadsafe_browser: ThreadsafeBrowser instance for thread-safe operations
        """
        self.page = page
        self.settings = settings or {}
        self._browser = threadsafe_browser
    
    def set_threadsafe_browser(self, browser: "ThreadsafeBrowser") -> None:
        """Set the ThreadsafeBrowser instance."""
        self._browser = browser
    
    def _run_async(self, coro):
        """
        Run async coroutine through ThreadsafeBrowser.
        
        Falls back to direct await if no ThreadsafeBrowser is set.
        """
        if self._browser is not None:
            return self._browser.run_coroutine(coro)
        else:
            # Fallback - это не должно использоваться в production
            import asyncio
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(coro)
    
    @abstractmethod
    async def is_ready(self) -> bool:
        """
        Check if the chat interface is ready for interaction.
        
        Returns:
            True if interface is ready (input field visible, etc.)
        """
        pass
    
    @abstractmethod
    async def send_message(self, message: str) -> bool:
        """
        Send a message to the chat.
        
        Args:
            message: Text message to send
            
        Returns:
            True if message was sent successfully
        """
        pass
    
    @abstractmethod
    async def wait_for_response(self, timeout: int = 120) -> bool:
        """
        Wait for the response to complete.
        
        Args:
            timeout: Maximum wait time in seconds
            
        Returns:
            True if response received successfully
        """
        pass
    
    @abstractmethod
    async def get_last_response(self) -> str:
        """
        Get the last response from the chat.
        
        Returns:
            Text content of the last response
        """
        pass
    
    async def is_authenticated(self) -> bool:
        """
        Check if user is authenticated.
        
        Default implementation checks if interface is ready.
        Override for specific authentication checks.
        
        Returns:
            True if authenticated
        """
        return await self.is_ready()
    
    async def clear_input(self) -> None:
        """
        Clear the input field.
        
        Override if specific clearing logic is needed.
        """
        pass
    
    async def get_response_count(self) -> int:
        """
        Get the number of responses in the conversation.
        
        Returns:
            Number of response messages
        """
        return 0
    
    async def is_generating(self) -> bool:
        """
        Check if a response is currently being generated.
        
        Returns:
            True if response generation is in progress
        """
        return False
    
    async def stop_generation(self) -> bool:
        """
        Stop the current response generation.
        
        Returns:
            True if stop was successful
        """
        return False
    
    # Thread-safe wrapper methods
    def is_ready_sync(self) -> bool:
        """Thread-safe version of is_ready."""
        return self._run_async(self.is_ready())
    
    def send_message_sync(self, message: str) -> bool:
        """Thread-safe version of send_message."""
        return self._run_async(self.send_message(message))
    
    def wait_for_response_sync(self, timeout: int = 120) -> bool:
        """Thread-safe version of wait_for_response."""
        return self._run_async(self.wait_for_response(timeout))
    
    def get_last_response_sync(self) -> str:
        """Thread-safe version of get_last_response."""
        return self._run_async(self.get_last_response())
    
    def get_response_count_sync(self) -> int:
        """Thread-safe version of get_response_count."""
        return self._run_async(self.get_response_count())
    
    def is_generating_sync(self) -> bool:
        """Thread-safe version of is_generating."""
        return self._run_async(self.is_generating())
