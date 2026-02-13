"""Cookie management for browser sessions."""

import json
from pathlib import Path
from typing import Any
import logging

from playwright.async_api import BrowserContext

logger = logging.getLogger(__name__)


class CookieManager:
    """
    Manages browser cookies.
    
    Handles loading and saving cookies for session persistence.
    """
    
    def __init__(self, context: BrowserContext):
        self.context = context
    
    async def load(self, file_path: Path) -> None:
        """
        Load cookies from a JSON file.
        
        Args:
            file_path: Path to cookies JSON file
        """
        if not file_path.exists():
            logger.warning(f"Cookies file not found: {file_path}")
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                cookies = json.load(f)
            
            # Validate and convert cookies
            valid_cookies = self._validate_cookies(cookies)
            
            if valid_cookies:
                await self.context.add_cookies(valid_cookies)
                logger.info(f"Loaded {len(valid_cookies)} cookies")
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid cookies JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            raise
    
    async def save(self, file_path: Path) -> None:
        """
        Save cookies to a JSON file.
        
        Args:
            file_path: Path to save cookies
        """
        try:
            cookies = await self.context.cookies()
            
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(cookies)} cookies to {file_path}")
            
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            raise
    
    async def clear(self) -> None:
        """Clear all cookies."""
        await self.context.clear_cookies()
        logger.info("Cookies cleared")
    
    async def get_all(self) -> list[dict[str, Any]]:
        """Get all cookies."""
        return await self.context.cookies()
    
    async def get_by_name(self, name: str) -> list[dict[str, Any]]:
        """Get cookies by name."""
        all_cookies = await self.context.cookies()
        return [c for c in all_cookies if c.get("name") == name]
    
    def _validate_cookies(self, cookies: list[dict]) -> list[dict]:
        """
        Validate and clean cookie data.
        
        Args:
            cookies: List of cookie dictionaries
            
        Returns:
            List of valid cookies
        """
        valid = []
        required_fields = {"name", "value", "domain"}
        
        for cookie in cookies:
            if not isinstance(cookie, dict):
                continue
            
            # Check required fields
            if not required_fields.issubset(cookie.keys()):
                logger.warning(f"Cookie missing required fields: {cookie.get('name', 'unknown')}")
                continue
            
            # Build valid cookie
            valid_cookie = {
                "name": str(cookie["name"]),
                "value": str(cookie["value"]),
                "domain": str(cookie["domain"]),
                "path": cookie.get("path", "/"),
            }
            
            # Add optional fields
            if "secure" in cookie:
                valid_cookie["secure"] = bool(cookie["secure"])
            if "httpOnly" in cookie:
                valid_cookie["httpOnly"] = bool(cookie["httpOnly"])
            if "sameSite" in cookie:
                valid_cookie["sameSite"] = cookie["sameSite"]
            if "expires" in cookie and cookie["expires"]:
                valid_cookie["expires"] = float(cookie["expires"])
            
            valid.append(valid_cookie)
        
        return valid
