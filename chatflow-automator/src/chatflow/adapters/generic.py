"""Generic chat adapter with configurable selectors and thread-safe operations."""

from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING
import asyncio
import logging

from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import ChatAdapter

if TYPE_CHECKING:
    from ..browser.threadsafe_browser import ThreadsafeBrowser

logger = logging.getLogger(__name__)


@dataclass
class GenericSelectors:
    """Configurable CSS selectors for generic adapter."""
    
    input_field: str = "textarea"
    send_button: str = "button[type='submit']"
    response_container: str = "[data-message-author-role='assistant']"
    stop_button: str = "button[aria-label='Stop']"
    loading_indicator: str = ".loading, .generating"
    auth_indicator: str = "textarea"
    input_field_alt: str = "input[type='text']"
    send_button_alt: str = "button:has-text('Send')"
    
    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary."""
        return {
            "input_field": self.input_field,
            "send_button": self.send_button,
            "response_container": self.response_container,
            "stop_button": self.stop_button,
            "loading_indicator": self.loading_indicator,
            "auth_indicator": self.auth_indicator,
            "input_field_alt": self.input_field_alt,
            "send_button_alt": self.send_button_alt,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GenericSelectors":
        """Create from dictionary."""
        return cls(
            input_field=data.get("input_field", "textarea"),
            send_button=data.get("send_button", "button[type='submit']"),
            response_container=data.get("response_container", "[data-message-author-role='assistant']"),
            stop_button=data.get("stop_button", "button[aria-label='Stop']"),
            loading_indicator=data.get("loading_indicator", ".loading, .generating"),
            auth_indicator=data.get("auth_indicator", "textarea"),
            input_field_alt=data.get("input_field_alt", "input[type='text']"),
            send_button_alt=data.get("send_button_alt", "button:has-text('Send')"),
        )


class GenericAdapter(ChatAdapter):
    """Universal adapter with configurable selectors."""
    
    name = "generic"
    description = "Universal adapter with configurable selectors"
    
    def __init__(
        self,
        page: Page,
        settings: Optional[dict[str, Any]] = None,
        threadsafe_browser: Optional["ThreadsafeBrowser"] = None
    ):
        super().__init__(page, settings, threadsafe_browser)
        
        # Initialize selectors from settings
        selectors_data = {}
        if settings:
            selectors_data = settings.get("selectors", {})
        self.selectors = GenericSelectors.from_dict(selectors_data)
        
        # Response tracking
        self._initial_response_count = 0
    
    async def is_ready(self) -> bool:
        """Check if interface is ready."""
        if not self.page:
            return False
            
        try:
            await self.page.wait_for_selector(
                self.selectors.input_field,
                timeout=5000,
                state="visible"
            )
            return True
        except PlaywrightTimeout:
            pass
        except Exception as e:
            logger.debug(f"is_ready error: {e}")
        
        try:
            await self.page.wait_for_selector(
                self.selectors.input_field_alt,
                timeout=2000,
                state="visible"
            )
            return True
        except:
            return False
    
    async def send_message(self, message: str) -> bool:
        """Send a message to the chat."""
        if not self.page:
            raise RuntimeError("Page not initialized")
            
        logger.debug(f"Sending message: {message[:50]}...")
        
        # Store initial response count
        self._initial_response_count = await self.get_response_count()
        
        # Find and fill input field
        input_field = await self._find_input_field()
        if not input_field:
            raise RuntimeError("Input field not found")
        
        # Clear and fill
        await input_field.fill("")
        await input_field.fill(message)
        
        # Small delay
        await asyncio.sleep(0.2)
        
        # Try to click send button
        sent = await self._click_send_button()
        
        if not sent:
            # Fallback: press Enter
            await input_field.press("Enter")
        
        logger.debug("Message sent")
        return True
    
    async def _find_input_field(self):
        """Find the input field element."""
        if not self.page:
            return None
            
        try:
            element = self.page.locator(self.selectors.input_field).first
            if await element.is_visible():
                return element
        except Exception as e:
            logger.debug(f"Primary input not found: {e}")
        
        try:
            element = self.page.locator(self.selectors.input_field_alt).first
            if await element.is_visible():
                return element
        except Exception as e:
            logger.debug(f"Alt input not found: {e}")
        
        return None
    
    async def _click_send_button(self) -> bool:
        """Try to click the send button."""
        if not self.page:
            return False
            
        try:
            button = self.page.locator(self.selectors.send_button).first
            if await button.is_visible():
                await button.click()
                return True
        except Exception as e:
            logger.debug(f"Primary send button not found: {e}")
        
        try:
            button = self.page.locator(self.selectors.send_button_alt).first
            if await button.is_visible():
                await button.click()
                return True
        except Exception as e:
            logger.debug(f"Alt send button not found: {e}")
        
        return False
    
    async def wait_for_response(self, timeout: int = 120) -> bool:
        """Wait for response to complete."""
        if not self.page:
            return False
            
        logger.debug(f"Waiting for response (timeout: {timeout}s)")
        
        timeout_ms = timeout * 1000
        poll_interval = 500
        elapsed = 0
        
        # Wait for response to start
        start_wait = 10000
        response_started = False
        
        while elapsed < start_wait and not response_started:
            current_count = await self.get_response_count()
            if current_count > self._initial_response_count:
                response_started = True
                break
            
            if await self.is_generating():
                response_started = True
                break
            
            await asyncio.sleep(poll_interval / 1000)
            elapsed += poll_interval
        
        if not response_started:
            logger.warning("Response did not start")
        
        # Wait for response to complete
        elapsed = 0
        while elapsed < timeout_ms:
            if not await self.is_generating():
                await asyncio.sleep(0.5)
                if not await self.is_generating():
                    logger.debug("Response completed")
                    return True
            
            await asyncio.sleep(poll_interval / 1000)
            elapsed += poll_interval
        
        logger.warning("Response timeout")
        return False
    
    async def is_generating(self) -> bool:
        """Check if response is being generated."""
        if not self.page:
            return False
            
        try:
            stop_visible = await self.page.locator(
                self.selectors.stop_button
            ).first.is_visible()
            
            if stop_visible:
                return True
            
            loading_visible = await self.page.locator(
                self.selectors.loading_indicator
            ).first.is_visible()
            
            return loading_visible
        except Exception:
            return False
    
    async def get_last_response(self) -> str:
        """Get the last response text."""
        if not self.page:
            return ""
            
        try:
            responses = self.page.locator(self.selectors.response_container)
            count = await responses.count()
            
            if count > 0:
                last_response = responses.nth(count - 1)
                text = await last_response.inner_text()
                return text.strip()
            
            return ""
        except Exception as e:
            logger.error(f"Failed to get response: {e}")
            return ""
    
    async def get_response_count(self) -> int:
        """Get number of responses."""
        if not self.page:
            return 0
            
        try:
            responses = self.page.locator(self.selectors.response_container)
            return await responses.count()
        except Exception:
            return 0
    
    async def clear_input(self) -> None:
        """Clear the input field."""
        input_field = await self._find_input_field()
        if input_field:
            await input_field.fill("")
