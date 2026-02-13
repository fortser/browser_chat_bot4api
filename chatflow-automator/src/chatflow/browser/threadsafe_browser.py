"""
ThreadsafeBrowser - потокобезопасная обёртка для Playwright.

Основан на паттерне из проекта minet:
https://github.com/medialab/minet/blob/master/minet/browser/threadsafe_browser.py
"""

import asyncio
import logging
from typing import Optional, Any, Callable, TypeVar, Coroutine, Set
from concurrent.futures import Future
from threading import Thread, Event, Lock

from playwright.async_api import (
    async_playwright,
    Playwright,
    Browser,
    BrowserContext,
    Page,
    Error as PlaywrightError,
)

from ..core.types import BrowserConfig, ProxyConfig
from ..core.exceptions import BrowserError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ThreadsafeBrowser:
    """
    Потокобезопасный браузер на основе Playwright.
    
    Создаёт отдельный поток с постоянным event loop,
    в котором работает Playwright. Все операции выполняются
    через asyncio.run_coroutine_threadsafe().
    """
    
    def __init__(self, config: Optional[BrowserConfig] = None):
        """
        Инициализация.
        
        Args:
            config: Конфигурация браузера
        """
        self.config = config or BrowserConfig()
        
        # Playwright objects
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        
        # Thread management
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[Thread] = None
        self._start_event = Event()
        self._stop_requested = False
        
        # Future tracking for cleanup
        self._running_futures: Set[Future] = set()
        self._futures_lock = Lock()
        
        # State
        self._is_launched = False
        self._current_url: Optional[str] = None
        
        logger.info("ThreadsafeBrowser initialized")
    
    @property
    def page(self) -> Optional[Page]:
        """Текущая страница."""
        return self._page
    
    @property
    def context(self) -> Optional[BrowserContext]:
        """Текущий контекст."""
        return self._context
    
    @property
    def browser(self) -> Optional[Browser]:
        """Текущий браузер."""
        return self._browser
    
    @property
    def is_launched(self) -> bool:
        """Запущен ли браузер."""
        return self._is_launched and self._browser is not None
    
    @property
    def loop(self) -> Optional[asyncio.AbstractEventLoop]:
        """Event loop браузерного потока."""
        return self._loop
    
    def _thread_worker(self) -> None:
        """Главная функция рабочего потока."""
        # Создаём новый event loop для этого потока
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        logger.info("Browser thread started")
        
        try:
            # Запускаем Playwright
            self._loop.run_until_complete(self._start_playwright())
            
            # Сигнализируем о готовности
            self._start_event.set()
            
            # Запускаем event loop
            self._loop.run_forever()
            
        except Exception as e:
            logger.error(f"Browser thread error: {e}")
            self._start_event.set()  # Разблокируем ожидающих
        finally:
            # Cleanup
            try:
                self._loop.run_until_complete(self._loop.shutdown_asyncgens())
            except Exception as e:
                logger.debug(f"Error shutting down asyncgens: {e}")
            
            # Останавливаем Playwright
            try:
                self._loop.run_until_complete(self._stop_playwright())
            except Exception as e:
                logger.debug(f"Error stopping playwright: {e}")
            
            try:
                self._loop.close()
            except Exception as e:
                logger.debug(f"Error closing loop: {e}")
            
            self._loop = None
            logger.info("Browser thread stopped")
    
    async def _start_playwright(self) -> None:
        """Запуск Playwright (выполняется в browser thread)."""
        logger.info("Starting Playwright...")
        
        self._playwright = await async_playwright().start()
        
        # Опции запуска
        launch_options = {
            'headless': self.config.headless,
        }
        
        # Аргументы браузера
        args = [
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
        ]
        
        if self.config.args:
            args.extend(self.config.args)
        
        launch_options['args'] = args
        
        if self.config.executable_path:
            launch_options['executable_path'] = self.config.executable_path
        
        # Запускаем браузер
        self._browser = await self._playwright.chromium.launch(**launch_options)
        
        logger.info("Playwright started successfully")
    
    async def _stop_playwright(self) -> None:
        """Остановка Playwright (выполняется в browser thread)."""
        logger.info("Stopping Playwright...")
        
        try:
            if self._page:
                await self._page.close()
                self._page = None
        except Exception as e:
            logger.debug(f"Error closing page: {e}")
        
        try:
            if self._context:
                await self._context.close()
                self._context = None
        except Exception as e:
            logger.debug(f"Error closing context: {e}")
        
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None
        except Exception as e:
            logger.debug(f"Error closing browser: {e}")
        
        try:
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
        except Exception as e:
            logger.debug(f"Error stopping playwright: {e}")
        
        logger.info("Playwright stopped")
    
    def start(self) -> None:
        """Запустить браузерный поток."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Browser thread already running")
            return
        
        self._stop_requested = False
        self._start_event.clear()
        
        self._thread = Thread(
            name=f"Thread-browser-{id(self)}",
            target=self._thread_worker,
            daemon=True
        )
        self._thread.start()
        
        # Ждём запуска
        self._start_event.wait(timeout=30)
        
        if self._browser is None:
            raise BrowserError("Failed to start browser")
        
        self._is_launched = True
        logger.info("Browser thread ready")
    
    def stop(self) -> None:
        """Остановить браузерный поток."""
        if self._thread is None or not self._thread.is_alive():
            return
        
        logger.info("Stopping browser thread...")
        self._stop_requested = True
        
        # Отменяем все pending futures
        with self._futures_lock:
            for fut in self._running_futures:
                if not fut.done():
                    fut.cancel()
        
        # Останавливаем event loop
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        # Ждём завершения потока
        self._thread.join(timeout=10)
        
        if self._thread.is_alive():
            logger.warning("Browser thread did not stop gracefully")
        
        self._is_launched = False
        self._thread = None
        logger.info("Browser thread stopped")
    
    def _handle_future(self, future: Future) -> Any:
        """Обработка future с отслеживанием."""
        with self._futures_lock:
            self._running_futures.add(future)
        
        try:
            return future.result()
        finally:
            with self._futures_lock:
                self._running_futures.discard(future)
    
    def run_coroutine(self, coro: Coroutine[Any, Any, T], timeout: float = 60.0) -> T:
        """
        Выполнить корутину в браузерном потоке.
        
        Args:
            coro: Корутина для выполнения
            timeout: Таймаут в секундах
            
        Returns:
            Результат корутины
        """
        if self._loop is None or not self._is_launched:
            raise BrowserError("Browser not launched")
        
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        
        try:
            return self._handle_future(future)
        except asyncio.TimeoutError:
            future.cancel()
            raise BrowserError(f"Operation timed out after {timeout}s")
        except Exception as e:
            raise BrowserError(f"Operation failed: {e}")
    
    async def _create_context_and_page(self, proxy: Optional[ProxyConfig] = None) -> Page:
        """Создать контекст и страницу (выполняется в browser thread)."""
        if self._browser is None:
            raise BrowserError("Browser not started")
        
        # Опции контекста
        context_options = {
            'viewport': {
                'width': self.config.viewport_width,
                'height': self.config.viewport_height
            },
            'user_agent': self.config.user_agent or (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
        }
        
        # Прокси
        if proxy and proxy.enabled and proxy.host:
            context_options['proxy'] = {
                'server': f"{proxy.type}://{proxy.host}:{proxy.port}"
            }
            if proxy.username:
                context_options['proxy']['username'] = proxy.username
            if proxy.password:
                context_options['proxy']['password'] = proxy.password
            logger.info(f"Proxy configured: {proxy.host}:{proxy.port}")
        
        # Locale
        if self.config.locale:
            context_options['locale'] = self.config.locale
        
        # Создаём контекст
        self._context = await self._browser.new_context(**context_options)
        
        # Stealth mode
        if self.config.stealth:
            await self._apply_stealth(self._context)
        
        # Создаём страницу
        self._page = await self._context.new_page()
        
        # Таймауты
        self._page.set_default_timeout(self.config.timeout)
        self._page.set_default_navigation_timeout(self.config.timeout)
        
        return self._page
    
    async def _apply_stealth(self, context: BrowserContext) -> None:
        """Применить stealth настройки."""
        stealth_js = """
        () => {
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
            window.chrome = { runtime: {} };
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        }
        """
        await context.add_init_script(stealth_js)
        logger.info("Stealth mode applied")
    
    def create_context_and_page(self, proxy: Optional[ProxyConfig] = None) -> Page:
        """Создать контекст и страницу (thread-safe)."""
        return self.run_coroutine(self._create_context_and_page(proxy))
    
    async def _navigate(self, url: str, wait_until: str = 'domcontentloaded') -> bool:
        """Навигация (выполняется в browser thread)."""
        if self._page is None:
            raise BrowserError("Page not created")
        
        await self._page.goto(url, wait_until=wait_until)
        self._current_url = url
        return True
    
    def navigate(self, url: str, wait_until: str = 'domcontentloaded') -> bool:
        """Навигация (thread-safe)."""
        logger.info(f"Navigating to: {url}")
        result = self.run_coroutine(self._navigate(url, wait_until))
        logger.info("Navigation complete")
        return result
    
    async def _get_cookies(self) -> list:
        """Получить cookies (выполняется в browser thread)."""
        if self._context is None:
            return []
        return await self._context.cookies()
    
    async def _add_cookies(self, cookies: list) -> None:
        """Добавить cookies (выполняется в browser thread)."""
        if self._context is None:
            raise BrowserError("Context not created")
        await self._context.add_cookies(cookies)
    
    def get_cookies(self) -> list:
        """Получить cookies (thread-safe)."""
        return self.run_coroutine(self._get_cookies())
    
    def add_cookies(self, cookies: list) -> None:
        """Добавить cookies (thread-safe)."""
        self.run_coroutine(self._add_cookies(cookies))
    
    async def _screenshot(self, path: str, full_page: bool = False) -> None:
        """Скриншот (выполняется в browser thread)."""
        if self._page is None:
            raise BrowserError("Page not created")
        await self._page.screenshot(path=path, full_page=full_page)
    
    def screenshot(self, path: str, full_page: bool = False) -> None:
        """Скриншот (thread-safe)."""
        self.run_coroutine(self._screenshot(path, full_page))
        logger.info(f"Screenshot saved: {path}")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()
