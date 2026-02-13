"""Browser actions - common browser interactions."""

from typing import Optional
import logging

from playwright.async_api import Page, Locator

logger = logging.getLogger(__name__)


class BrowserActions:
    """
    Common browser actions and interactions.
    
    Provides high-level methods for interacting with page elements.
    """
    
    def __init__(self, page: Page):
        self.page = page
    
    async def click(
        self,
        selector: str,
        timeout: int = 5000,
        force: bool = False
    ) -> bool:
        """
        Click an element.
        
        Args:
            selector: CSS selector
            timeout: Wait timeout in ms
            force: Force click even if not visible
            
        Returns:
            True if click successful
        """
        try:
            element = self.page.locator(selector).first
            await element.click(timeout=timeout, force=force)
            return True
        except Exception as e:
            logger.debug(f"Click failed for {selector}: {e}")
            return False
    
    async def fill(
        self,
        selector: str,
        text: str,
        timeout: int = 5000,
        clear_first: bool = True
    ) -> bool:
        """
        Fill a text input.
        
        Args:
            selector: CSS selector
            text: Text to fill
            timeout: Wait timeout in ms
            clear_first: Clear existing content first
            
        Returns:
            True if fill successful
        """
        try:
            element = self.page.locator(selector).first
            if clear_first:
                await element.fill("", timeout=timeout)
            await element.fill(text, timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"Fill failed for {selector}: {e}")
            return False
    
    async def type_text(
        self,
        selector: str,
        text: str,
        delay: int = 50,
        timeout: int = 5000
    ) -> bool:
        """
        Type text character by character (human-like).
        
        Args:
            selector: CSS selector
            text: Text to type
            delay: Delay between keystrokes in ms
            timeout: Wait timeout in ms
            
        Returns:
            True if typing successful
        """
        try:
            element = self.page.locator(selector).first
            await element.type(text, delay=delay, timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"Type failed for {selector}: {e}")
            return False
    
    async def press_key(
        self,
        selector: str,
        key: str,
        timeout: int = 5000
    ) -> bool:
        """
        Press a key on an element.
        
        Args:
            selector: CSS selector
            key: Key to press (e.g., "Enter", "Tab")
            timeout: Wait timeout in ms
            
        Returns:
            True if press successful
        """
        try:
            element = self.page.locator(selector).first
            await element.press(key, timeout=timeout)
            return True
        except Exception as e:
            logger.debug(f"Press key failed for {selector}: {e}")
            return False
    
    async def get_text(
        self,
        selector: str,
        timeout: int = 5000
    ) -> Optional[str]:
        """
        Get text content of an element.
        
        Args:
            selector: CSS selector
            timeout: Wait timeout in ms
            
        Returns:
            Text content or None
        """
        try:
            element = self.page.locator(selector).first
            return await element.inner_text(timeout=timeout)
        except Exception as e:
            logger.debug(f"Get text failed for {selector}: {e}")
            return None
    
    async def get_all_texts(
        self,
        selector: str,
        timeout: int = 5000
    ) -> list[str]:
        """
        Get text content of all matching elements.
        
        Args:
            selector: CSS selector
            timeout: Wait timeout in ms
            
        Returns:
            List of text contents
        """
        try:
            elements = self.page.locator(selector)
            count = await elements.count()
            texts = []
            for i in range(count):
                text = await elements.nth(i).inner_text(timeout=timeout)
                texts.append(text)
            return texts
        except Exception as e:
            logger.debug(f"Get all texts failed for {selector}: {e}")
            return []
    
    async def is_visible(
        self,
        selector: str,
        timeout: int = 1000
    ) -> bool:
        """
        Check if element is visible.
        
        Args:
            selector: CSS selector
            timeout: Wait timeout in ms
            
        Returns:
            True if visible
        """
        try:
            element = self.page.locator(selector).first
            return await element.is_visible(timeout=timeout)
        except Exception:
            return False
    
    async def wait_for_visible(
        self,
        selector: str,
        timeout: int = 30000
    ) -> bool:
        """
        Wait for element to become visible.
        
        Args:
            selector: CSS selector
            timeout: Wait timeout in ms
            
        Returns:
            True if element became visible
        """
        try:
            await self.page.wait_for_selector(
                selector,
                state="visible",
                timeout=timeout
            )
            return True
        except Exception:
            return False
    
    async def wait_for_hidden(
        self,
        selector: str,
        timeout: int = 30000
    ) -> bool:
        """
        Wait for element to become hidden.
        
        Args:
            selector: CSS selector
            timeout: Wait timeout in ms
            
        Returns:
            True if element became hidden
        """
        try:
            await self.page.wait_for_selector(
                selector,
                state="hidden",
                timeout=timeout
            )
            return True
        except Exception:
            return False
    
    async def scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the page."""
        await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    
    async def scroll_into_view(self, selector: str) -> bool:
        """
        Scroll element into view.
        
        Args:
            selector: CSS selector
            
        Returns:
            True if successful
        """
        try:
            element = self.page.locator(selector).first
            await element.scroll_into_view_if_needed()
            return True
        except Exception:
            return False
    
    async def count_elements(self, selector: str) -> int:
        """
        Count matching elements.
        
        Args:
            selector: CSS selector
            
        Returns:
            Number of matching elements
        """
        try:
            return await self.page.locator(selector).count()
        except Exception:
            return 0
