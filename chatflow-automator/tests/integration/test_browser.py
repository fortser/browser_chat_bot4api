"""Integration tests for browser module.

These tests require Playwright to be installed.
Run with: pytest tests/integration -v
"""

import pytest
import asyncio

# Skip all tests if playwright is not available
pytest.importorskip("playwright")


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


class TestBrowserManager:
    """Integration tests for BrowserManager."""
    
    @pytest.mark.asyncio
    async def test_launch_and_close(self, event_emitter):
        """Test launching and closing browser."""
        from chatflow.browser.manager import BrowserManager
        from chatflow.core.types import BrowserConfig
        
        config = BrowserConfig(headless=True)
        manager = BrowserManager(config, event_emitter)
        
        await manager.launch()
        assert manager._browser is not None
        
        await manager.close()
        assert manager._browser is None
    
    @pytest.mark.asyncio
    async def test_navigate(self, event_emitter):
        """Test navigation."""
        from chatflow.browser.manager import BrowserManager
        from chatflow.core.types import BrowserConfig
        
        config = BrowserConfig(headless=True)
        manager = BrowserManager(config, event_emitter)
        
        try:
            await manager.launch()
            await manager.navigate("https://example.com")
            
            page = await manager.get_page()
            assert "example" in page.url.lower()
        finally:
            await manager.close()
