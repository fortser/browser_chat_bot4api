"""Stealth mode for hiding browser automation."""

from playwright.async_api import BrowserContext, Page
import logging

logger = logging.getLogger(__name__)


async def apply_stealth(context: BrowserContext) -> None:
    """
    Apply stealth settings to hide automation.
    
    This helps avoid detection by anti-bot systems.
    
    Args:
        context: Browser context to apply stealth to
    """
    # JavaScript to inject for hiding automation
    stealth_js = """
    () => {
        // Override navigator.webdriver
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        
        // Override navigator.plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
        });
        
        // Override navigator.languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        
        // Override chrome runtime
        window.chrome = {
            runtime: {},
        };
        
        // Override permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        
        // Prevent detection via iframe
        Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
            get: function() {
                return window;
            }
        });
        
        // Remove automation-related properties
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
    }
    """
    
    # Add script to run on each new page
    await context.add_init_script(stealth_js)
    
    logger.info("Stealth mode applied")


async def apply_stealth_to_page(page: Page) -> None:
    """
    Apply stealth settings to a specific page.
    
    Use this for pages created after context initialization.
    
    Args:
        page: Page to apply stealth to
    """
    await page.add_init_script("""
    () => {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
    }
    """)
