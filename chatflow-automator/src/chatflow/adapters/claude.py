"""Claude adapter example."""

from typing import Any, Optional
from playwright.async_api import Page
from .generic import GenericAdapter, GenericSelectors


class ClaudeSelectors(GenericSelectors):
    """Selectors optimized for Claude interface."""
    
    def __init__(self):
        super().__init__()
        self.input_field = "[contenteditable='true']"
        self.send_button = "button[aria-label='Send Message']"
        self.response_container = "[data-is-streaming]"
        self.stop_button = "button:has-text('Stop')"
        self.loading_indicator = "[data-is-streaming='true']"
        self.auth_indicator = "[contenteditable='true']"


class ClaudeAdapter(GenericAdapter):
    """
    Adapter for Claude web interface.
    
    Note: This is an example. Actual selectors may change
    as the Claude interface is updated.
    """
    
    name = "claude"
    description = "Adapter for Claude (claude.ai)"
    
    def __init__(self, page: Page, settings: Optional[dict[str, Any]] = None):
        super().__init__(page, settings)
        # Override with Claude-specific selectors
        self.selectors = ClaudeSelectors()


# Register adapter
from . import register_adapter
register_adapter("claude", ClaudeAdapter)
