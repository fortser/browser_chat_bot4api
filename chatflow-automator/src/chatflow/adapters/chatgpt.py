"""
ChatGPT Adapter - адаптер для https://chatgpt.com/

Селекторы актуальны для ChatGPT 5.2 Pro (январь 2026).
"""
import asyncio
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import ChatAdapter

if TYPE_CHECKING:
    from ..browser.threadsafe_browser import ThreadsafeBrowser

logger = logging.getLogger(__name__)


class ChatGPTSelectors:
    """CSS селекторы для интерфейса ChatGPT."""
    
    # Поле ввода (ProseMirror редактор)
    INPUT_FIELD = "#prompt-textarea"
    
    # Кнопка отправки
    SEND_BUTTON = "button[data-testid='send-button']"
    SEND_BUTTON_BY_ID = "#composer-submit-button"
    
    # Кнопка остановки генерации (заменяет кнопку отправки)
    STOP_BUTTON = "button[data-testid='stop-button']"
    
    # Сообщения
    USER_MESSAGE = "[data-message-author-role='user']"
    ASSISTANT_MESSAGE = "[data-message-author-role='assistant']"
    
    # Контейнеры turn (весь блок сообщения)
    USER_TURN = "article[data-turn='user']"
    ASSISTANT_TURN = "article[data-turn='assistant']"
    
    # Контент ответа (markdown)
    RESPONSE_CONTENT = ".markdown.prose"
    
    # Проверка авторизации - поле ввода видно только авторизованным
    AUTH_INDICATOR = "#prompt-textarea"


class ChatGPTAdapter(ChatAdapter):
    """
    Адаптер для ChatGPT (chatgpt.com).
    
    Поддерживает:
    - Отправку сообщений через ProseMirror редактор
    - Ожидание ответа с детекцией через кнопку Stop
    - Получение текста ответа
    """
    
    name = "chatgpt"
    description = "Adapter for ChatGPT (chatgpt.com)"
    
    def __init__(
        self,
        page: Page,
        settings: Optional[Dict[str, Any]] = None,
        threadsafe_browser: Optional["ThreadsafeBrowser"] = None
    ):
        super().__init__(page, settings, threadsafe_browser)
        self.selectors = ChatGPTSelectors()
        self.settings = settings or {}
        
        # Таймауты
        self.element_timeout = self.settings.get('element_timeout', 5000)
        self.response_timeout = self.settings.get('response_timeout', 120000)
        
        # Счётчик ответов для отслеживания новых
        self._response_count_before = 0
        
        logger.info("ChatGPTAdapter initialized")
    
    async def is_ready(self) -> bool:
        """Проверить готовность интерфейса."""
        if not self.page:
            return False
        
        try:
            # Проверяем наличие поля ввода
            input_field = self.page.locator(self.selectors.INPUT_FIELD)
            await input_field.wait_for(timeout=self.element_timeout, state="visible")
            
            is_visible = await input_field.is_visible()
            logger.debug(f"Input field visible: {is_visible}")
            return is_visible
            
        except PlaywrightTimeout:
            logger.warning("Timeout waiting for input field")
            return False
        except Exception as e:
            logger.error(f"Error checking readiness: {e}")
            return False
    
    async def is_authenticated(self) -> bool:
        """Проверить авторизацию пользователя."""
        return await self.is_ready()
    
    async def send_message(self, message: str) -> bool:
        """Отправить сообщение в чат."""
        if not self.page:
            return False
        
        try:
            logger.info(f"Sending message: {message[:50]}...")
            
            # Сохраняем текущее количество ответов
            self._response_count_before = await self.get_response_count()
            logger.debug(f"Response count before: {self._response_count_before}")
            
            # Находим поле ввода
            input_field = self.page.locator(self.selectors.INPUT_FIELD)
            await input_field.wait_for(timeout=self.element_timeout, state="visible")
            
            # Кликаем для фокуса
            await input_field.click()
            await asyncio.sleep(0.2)
            
            # ProseMirror требует особого подхода - используем fill для contenteditable
            # Сначала очищаем
            await input_field.fill('')
            await asyncio.sleep(0.1)
            
            # Вводим текст
            await input_field.fill(message)
            await asyncio.sleep(0.3)
            
            # Ждём активации кнопки отправки и кликаем
            send_button = self.page.locator(self.selectors.SEND_BUTTON)
            try:
                await send_button.wait_for(timeout=2000, state="visible")
                await send_button.click()
                logger.info("Message sent via button click")
                return True
            except PlaywrightTimeout:
                # Пробуем альтернативный способ - Enter
                logger.debug("Send button not found, trying Enter key")
                await input_field.press('Enter')
                logger.info("Message sent via Enter key")
                return True
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    async def wait_for_response(self, timeout: Optional[int] = None) -> bool:
        """Ждать завершения ответа."""
        if not self.page:
            return False
        
        timeout = timeout or (self.response_timeout // 1000)
        max_wait = timeout
        poll_interval = 0.5
        elapsed = 0
        
        logger.info(f"Waiting for response (timeout: {timeout}s)")
        
        # Даём время на начало генерации
        await asyncio.sleep(1)
        
        # Ждём появления кнопки Stop (начало генерации) или нового ответа
        generation_started = False
        start_wait = 10  # секунд на ожидание начала
        
        while elapsed < start_wait and not generation_started:
            # Проверяем появление кнопки Stop
            if await self.is_generating():
                generation_started = True
                logger.debug("Generation started (stop button detected)")
                break
            
            # Или появление нового ответа
            current_count = await self.get_response_count()
            if current_count > self._response_count_before:
                generation_started = True
                logger.debug("New response appeared")
                break
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        if not generation_started:
            logger.warning("Generation did not start within expected time")
            # Продолжаем ждать на случай медленного старта
        
        # Ждём завершения генерации (исчезновения кнопки Stop)
        elapsed = 0
        while elapsed < max_wait:
            if not await self.is_generating():
                # Двойная проверка - ждём немного и проверяем снова
                await asyncio.sleep(0.5)
                if not await self.is_generating():
                    # Проверяем что ответ действительно появился
                    current_count = await self.get_response_count()
                    if current_count > self._response_count_before:
                        logger.info(f"Response completed (count: {current_count})")
                        return True
                    else:
                        logger.debug("Stop button gone but no new response yet, waiting...")
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        logger.warning(f"Timeout waiting for response after {timeout}s")
        return False
    
    async def is_generating(self) -> bool:
        """Проверить, идёт ли генерация ответа."""
        if not self.page:
            return False
        
        try:
            # Проверяем наличие кнопки Stop
            stop_button = self.page.locator(self.selectors.STOP_BUTTON)
            count = await stop_button.count()
            
            if count > 0:
                is_visible = await stop_button.first.is_visible()
                return is_visible
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking generation status: {e}")
            return False
    
    async def get_last_response(self) -> Optional[str]:
        """Получить последний ответ ассистента."""
        if not self.page:
            return None
        
        try:
            # Ищем все сообщения ассистента
            responses = self.page.locator(self.selectors.ASSISTANT_MESSAGE)
            count = await responses.count()
            
            if count == 0:
                logger.warning("No assistant messages found")
                return None
            
            # Берём последнее сообщение
            last_response = responses.nth(count - 1)
            
            # Ищем контент внутри (markdown)
            content = last_response.locator(self.selectors.RESPONSE_CONTENT)
            
            if await content.count() > 0:
                text = await content.first.inner_text()
                text = text.strip()
                logger.debug(f"Got response: {len(text)} chars")
                return text
            
            # Fallback - весь текст из блока
            text = await last_response.inner_text()
            return text.strip()
            
        except Exception as e:
            logger.error(f"Error getting last response: {e}")
            return None
    
    async def get_response_count(self) -> int:
        """Получить количество ответов ассистента."""
        if not self.page:
            return 0
        
        try:
            responses = self.page.locator(self.selectors.ASSISTANT_MESSAGE)
            count = await responses.count()
            return count
        except Exception:
            return 0
    
    async def clear_input(self) -> bool:
        """Очистить поле ввода."""
        if not self.page:
            return False
        
        try:
            input_field = self.page.locator(self.selectors.INPUT_FIELD)
            await input_field.fill('')
            return True
        except Exception as e:
            logger.debug(f"Error clearing input: {e}")
            return False
    
    async def stop_generation(self) -> bool:
        """Остановить генерацию ответа."""
        if not self.page:
            return False
        
        try:
            stop_button = self.page.locator(self.selectors.STOP_BUTTON)
            
            if await stop_button.count() > 0 and await stop_button.first.is_visible():
                await stop_button.first.click()
                logger.info("Generation stopped")
                return True
            
            logger.debug("Stop button not found or not visible")
            return False
            
        except Exception as e:
            logger.error(f"Error stopping generation: {e}")
            return False

