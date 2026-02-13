"""
Browser Manager - управление браузером через ThreadsafeBrowser.
"""
import json
import logging
from pathlib import Path
from typing import Optional

from ..core.types import BrowserConfig, ProxyConfig
from ..core.exceptions import BrowserError
from .threadsafe_browser import ThreadsafeBrowser

logger = logging.getLogger(__name__)


class BrowserManager:
    """Менеджер браузера с потокобезопасным доступом."""
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        Инициализация менеджера.
        
        Args:
            config: Конфигурация браузера
        """
        self.config = config or BrowserConfig()
        self._browser: Optional[ThreadsafeBrowser] = None
        self._proxy: Optional[ProxyConfig] = None
        
        logger.info("BrowserManager initialized")
    
    @property
    def page(self):
        """Текущая страница."""
        if self._browser:
            return self._browser.page
        return None
    
    @property
    def context(self):
        """Текущий контекст."""
        if self._browser:
            return self._browser.context
        return None
    
    @property
    def is_launched(self) -> bool:
        """Запущен ли браузер."""
        return self._browser is not None and self._browser.is_launched
    
    @property
    def threadsafe_browser(self) -> Optional[ThreadsafeBrowser]:
        """Доступ к ThreadsafeBrowser."""
        return self._browser
    
    async def launch(self, proxy: Optional[ProxyConfig] = None):
        """
        Запустить браузер.
        
        Args:
            proxy: Конфигурация прокси
            
        Returns:
            Page объект
        """
        self._proxy = proxy
        
        logger.info(f"Launching browser (headless: {self.config.headless})")
        
        # Создаём ThreadsafeBrowser
        self._browser = ThreadsafeBrowser(self.config)
        
        # Запускаем браузерный поток
        self._browser.start()
        
        # Создаём контекст и страницу
        page = self._browser.create_context_and_page(proxy)
        
        logger.info("Browser launched successfully")
        return page
    
    def get_page(self):
        """Получить текущую страницу."""
        return self.page
    
    async def navigate(self, url: str, wait_until: str = 'domcontentloaded') -> bool:
        """
        Навигация к URL.
        
        Args:
            url: URL для навигации
            wait_until: Условие ожидания
            
        Returns:
            True при успехе
        """
        if not self._browser:
            raise BrowserError("Browser not launched")
        
        return self._browser.navigate(url, wait_until)
    
    async def load_cookies(self, path: str) -> bool:
        """
        Загрузить cookies из файла.
        
        Args:
            path: Путь к JSON файлу
            
        Returns:
            True при успехе
        """
        if not self._browser:
            raise BrowserError("Browser not launched")
        
        path_obj = Path(path)
        if not path_obj.exists():
            logger.warning(f"Cookies file not found: {path}")
            return False
        
        try:
            with open(path_obj, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            # Валидация cookies
            valid_cookies = self._validate_cookies(cookies)
            
            if valid_cookies:
                self._browser.add_cookies(valid_cookies)
                logger.info(f"Loaded {len(valid_cookies)} cookies from {path}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
            return False
    
    async def save_cookies(self, path: str) -> bool:
        """
        Сохранить cookies в файл.
        
        Args:
            path: Путь для сохранения
            
        Returns:
            True при успехе
        """
        if not self._browser or not self._browser.is_launched:
            logger.warning("Browser not available for saving cookies")
            return False
        
        try:
            cookies = self._browser.get_cookies()
            
            path_obj = Path(path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path_obj, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(cookies)} cookies to {path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
            return False
    
    def _validate_cookies(self, cookies: list) -> list:
        """Валидация cookies."""
        valid = []
        required_fields = {"name", "value", "domain"}
        
        for cookie in cookies:
            if not isinstance(cookie, dict):
                continue
            
            if not required_fields.issubset(cookie.keys()):
                continue
            
            valid_cookie = {
                "name": str(cookie["name"]),
                "value": str(cookie["value"]),
                "domain": str(cookie["domain"]),
                "path": cookie.get("path", "/"),
            }
            
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
    
    async def screenshot(self, path: str, full_page: bool = False) -> bool:
        """
        Сделать скриншот.
        
        Args:
            path: Путь для сохранения
            full_page: Вся страница
            
        Returns:
            True при успехе
        """
        if not self._browser:
            return False
        
        try:
            self._browser.screenshot(path, full_page)
            return True
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            return False
    
    async def close(self) -> None:
        """Закрыть браузер."""
        logger.info("Closing browser...")
        
        if self._browser:
            self._browser.stop()
            self._browser = None
        
        logger.info("Browser closed")
