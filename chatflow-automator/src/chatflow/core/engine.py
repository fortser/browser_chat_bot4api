"""
ChatFlow Core Engine - основной движок системы.
"""
import asyncio
import logging
from typing import Optional, Dict, Any

from .types import ConnectionConfig, BrowserConfig, ProxyConfig, BrowserStatus
from .events import EventEmitter
from .exceptions import BrowserError, ConnectionError
from ..browser.manager import BrowserManager
from ..browser.threadsafe_browser import ThreadsafeBrowser
from ..adapters import get_adapter, ChatAdapter

logger = logging.getLogger(__name__)

# Глобальный экземпляр Engine
_engine_instance: Optional["Engine"] = None


def get_engine() -> "Engine":
    """Получить глобальный экземпляр Engine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = Engine()
    return _engine_instance


def set_engine(engine: "Engine") -> None:
    """Установить глобальный экземпляр Engine."""
    global _engine_instance
    _engine_instance = engine


class Engine:
    """Основной движок ChatFlow."""
    
    def __init__(self, event_emitter: Optional[EventEmitter] = None):
        """
        Инициализация движка.
        
        Args:
            event_emitter: Эмиттер событий
        """
        self.events = event_emitter or EventEmitter()
        self._browser_manager: Optional[BrowserManager] = None
        self._adapter: Optional[ChatAdapter] = None
        self._status = BrowserStatus.DISCONNECTED
        self._current_url: Optional[str] = None
        self._is_running = False
        self._is_connected = False
        
        logger.info("Engine initialized")
    
    @property
    def status(self) -> BrowserStatus:
        """Текущий статус."""
        return self._status
    
    @property
    def browser_manager(self) -> Optional[BrowserManager]:
        """Менеджер браузера."""
        return self._browser_manager
    
    @property
    def threadsafe_browser(self) -> Optional[ThreadsafeBrowser]:
        """ThreadsafeBrowser для прямого доступа."""
        if self._browser_manager:
            return self._browser_manager.threadsafe_browser
        return None
    
    @property
    def adapter(self) -> Optional[ChatAdapter]:
        """Текущий адаптер чата."""
        return self._adapter
    
    @property
    def page(self):
        """Текущая страница браузера."""
        if self._browser_manager:
            return self._browser_manager.page
        return None
    
    @property
    def is_running(self) -> bool:
        """Выполняется ли задача."""
        return self._is_running
    
    @is_running.setter
    def is_running(self, value: bool) -> None:
        """Установить флаг выполнения."""
        self._is_running = value
    
    @property
    def is_connected(self) -> bool:
        """Подключен ли браузер."""
        return self._is_connected and self._browser_manager is not None
    
    def _set_status(self, status: BrowserStatus) -> None:
        """Установить статус и отправить событие."""
        self._status = status
        self.events.emit('status_changed', status)
        logger.info(f"Status changed to: {status.value}")
    
    async def connect(self, config: ConnectionConfig) -> bool:
        """
        Подключиться к целевому сайту.
        
        Args:
            config: Конфигурация подключения
            
        Returns:
            True при успешном подключении
        """
        try:
            self._set_status(BrowserStatus.CONNECTING)
            
            # Создаём конфигурацию браузера
            browser_config = BrowserConfig(
                headless=config.browser.headless,
                user_agent=config.browser.user_agent,
                timeout=config.browser.timeout,
                stealth=config.browser.stealth,
                viewport_width=config.browser.viewport_width,
                viewport_height=config.browser.viewport_height,
            )
            
            # Создаём менеджер браузера
            self._browser_manager = BrowserManager(browser_config)
            
            # Прокси
            proxy = None
            if config.browser.proxy.enabled:
                proxy = config.browser.proxy
            
            # Запуск браузера (синхронный вызов async метода для совместимости)
            await self._browser_manager.launch(proxy)
            
            # Загрузка cookies при наличии
            if config.cookies_file:
                await self._browser_manager.load_cookies(config.cookies_file)
            
            # Навигация к URL
            await self._browser_manager.navigate(config.url)
            self._current_url = config.url
            
            # Создание адаптера
            AdapterClass = get_adapter(config.adapter_name)
            if not AdapterClass:
                logger.warning(f"Adapter '{config.adapter_name}' not found, using generic")
                AdapterClass = get_adapter('generic')
            
            # Получаем страницу и ThreadsafeBrowser для адаптера
            page = self._browser_manager.page
            if not page:
                raise BrowserError("Failed to get page from browser")
            
            threadsafe_browser = self._browser_manager.threadsafe_browser
            
            adapter_settings = config.adapter_settings or {}
            self._adapter = AdapterClass(page, adapter_settings, threadsafe_browser)
            
            logger.info(f"Created adapter: {AdapterClass.name}")
            
            # Ждём загрузки страницы
            await asyncio.sleep(2)
            
            self._is_connected = True
            self._set_status(BrowserStatus.CONNECTED)
            self.events.emit('connected', {'url': config.url, 'adapter': config.adapter_name})
            
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._set_status(BrowserStatus.ERROR)
            self.events.emit('connection_error', str(e))
            await self.disconnect()
            raise ConnectionError(f"Connection failed: {e}")
    
    async def disconnect(self) -> None:
        """Отключиться от браузера."""
        try:
            self._set_status(BrowserStatus.DISCONNECTING)
            
            # Сохранение cookies перед отключением
            if self._browser_manager and self._current_url:
                if self._browser_manager.is_launched:
                    try:
                        from ..utils.paths import get_cookies_dir
                        import urllib.parse
                        domain = urllib.parse.urlparse(self._current_url).netloc
                        cookies_path = get_cookies_dir() / f"{domain}_cookies.json"
                        await self._browser_manager.save_cookies(str(cookies_path))
                    except Exception as e:
                        logger.warning(f"Failed to save cookies: {e}")
            
            # Очистка адаптера
            self._adapter = None
            
            # Закрытие браузера
            if self._browser_manager:
                await self._browser_manager.close()
                self._browser_manager = None
            
            self._is_connected = False
            self._set_status(BrowserStatus.DISCONNECTED)
            self.events.emit('disconnected')
            
        except Exception as e:
            logger.error(f"Error during disconnect: {e}")
            self._is_connected = False
            self._browser_manager = None
            self._adapter = None
            self._set_status(BrowserStatus.DISCONNECTED)
    
    async def navigate(self, url: str) -> bool:
        """Перейти на указанный URL."""
        if not self._browser_manager:
            raise BrowserError("Browser not launched")
            
        result = await self._browser_manager.navigate(url)
        if result:
            self._current_url = url
        return result
    
    async def screenshot(self, path: str) -> bool:
        """Сделать скриншот."""
        if not self._browser_manager:
            return False
        return await self._browser_manager.screenshot(path)
    
    def stop(self) -> None:
        """Остановить выполнение задач."""
        self._is_running = False
        self.events.emit('execution_stopped')
    
    def cleanup(self) -> None:
        """Очистка ресурсов при завершении."""
        logger.info("Engine cleanup")
