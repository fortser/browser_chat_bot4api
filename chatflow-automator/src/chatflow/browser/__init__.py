"""Browser module - browser management and automation."""

from .manager import BrowserManager
from .threadsafe_browser import ThreadsafeBrowser
from .actions import BrowserActions
from .cookies import CookieManager

__all__ = [
    "BrowserManager",
    "ThreadsafeBrowser",
    "BrowserActions",
    "CookieManager",
]
