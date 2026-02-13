"""
Qwen AI Chat Adapter - оптимизированная версия с фиксированными селекторами.
"""
import asyncio
import logging
from typing import Optional, Dict, Any, TYPE_CHECKING
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from .base import ChatAdapter

if TYPE_CHECKING:
    from ..browser.threadsafe_browser import ThreadsafeBrowser

logger = logging.getLogger(__name__)


class QwenSelectors:
    """Фиксированные CSS селекторы для Qwen Chat."""
    
    # Поле ввода
    INPUT_FIELD = "#chat-input"
    INPUT_FIELD_ALT = "textarea.chat-input"
    
    # Кнопка отправки
    SEND_BUTTON = ".chat-prompt-send-button button.send-button"
    SEND_BUTTON_ENABLED = ".chat-prompt-send-button button.send-button:not(.disabled)"
    
    # Контейнер сообщений
    MESSAGES_CONTAINER = "#chat-message-container"
    
    # Сообщения пользователя
    USER_MESSAGE = ".qwen-chat-message-user"
    USER_MESSAGE_CONTENT = ".user-message-content"
    
    # Ответы ассистента
    ASSISTANT_MESSAGE = ".qwen-chat-message-assistant"
    ASSISTANT_RESPONSE = ".chat-response-message"
    RESPONSE_CONTENT = ".response-message-content .qwen-markdown"
    RESPONSE_TEXT = ".qwen-markdown-paragraph"
    
    # Индикаторы загрузки/генерации
    THINKING_CARD = ".qwen-chat-status-card"
    THINKING_TITLE = ".qwen-chat-status-card-title"
    
    # Кнопка остановки (появляется во время генерации)
    STOP_BUTTON = ".chat-prompt-send-button button.send-button.stop-button"
    STOP_BUTTON_ALT = "button.stop-button"
    
    # Проверка готовности интерфейса
    CHAT_LAYOUT = ".chat-layout"
    CHAT_CONTENT = ".chat-content"
    PROMPT_INPUT_CONTAINER = ".prompt-input-container"
    
    # Индикатор "печатает" / streaming
    STREAMING_INDICATOR = ".response-message-content.streaming"
    PHASE_THINKING = ".response-message-content.phase-thinking"
    PHASE_ANSWER = ".response-message-content.phase-answer"


class QwenAdapter(ChatAdapter):
    """Адаптер для Qwen AI Chat с фиксированными селекторами."""
    
    name = "qwen"
    description = "Adapter for Qwen AI Chat (chat.qwen.ai)"
    
    def __init__(
        self,
        page: Page,
        settings: Optional[Dict[str, Any]] = None,
        threadsafe_browser: Optional["ThreadsafeBrowser"] = None
    ):
        super().__init__(page, settings, threadsafe_browser)
        self.selectors = QwenSelectors()
        self.settings = settings or {}
        
        # Таймауты
        self.element_timeout = self.settings.get('element_timeout', 5000)
        self.response_timeout = self.settings.get('response_timeout', 120000)
        
        # Счётчик ответов для отслеживания новых
        self._response_count_before = 0
        
        logger.info("QwenAdapter initialized with fixed selectors")
    
    async def is_ready(self) -> bool:
        """Проверить готовность интерфейса."""
        if not self.page:
            return False
        
        try:
            # Проверяем наличие поля ввода
            input_field = self.page.locator(self.selectors.INPUT_FIELD)
            await input_field.wait_for(timeout=self.element_timeout, state="visible")
            
            # Проверяем что оно доступно
            is_visible = await input_field.is_visible()
            is_enabled = await input_field.is_enabled()
            
            logger.debug(f"Input field visible: {is_visible}, enabled: {is_enabled}")
            return is_visible and is_enabled
            
        except PlaywrightTimeout:
            logger.warning("Timeout waiting for input field")
            return False
        except Exception as e:
            logger.error(f"Error checking readiness: {e}")
            return False
    
    async def send_message(self, message: str) -> bool:
        """Отправить сообщение."""
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
            
            # Очищаем и вводим текст
            await input_field.fill('')
            await input_field.fill(message)
            await asyncio.sleep(0.3)
            
            # Ждём активации кнопки отправки
            send_button = self.page.locator(self.selectors.SEND_BUTTON_ENABLED)
            try:
                await send_button.wait_for(timeout=2000, state="visible")
                await send_button.click()
                logger.info("Message sent via button click")
                return True
            except PlaywrightTimeout:
                # Кнопка не активировалась, пробуем Enter
                logger.debug("Send button not enabled, trying Enter key")
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
        
        while elapsed < max_wait:
            try:
                # Проверяем, идёт ли генерация
                is_generating = await self.is_generating()
                
                if is_generating:
                    logger.debug("Response is being generated...")
                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval
                    continue
                
                # Проверяем, появился ли новый ответ
                current_count = await self.get_response_count()
                
                if current_count > self._response_count_before:
                    # Ждём немного для полной загрузки
                    await asyncio.sleep(0.5)
                    
                    # Проверяем ещё раз, что генерация завершена
                    if not await self.is_generating():
                        logger.info(f"Response received (count: {current_count})")
                        return True
                
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval
                
            except Exception as e:
                logger.debug(f"Error during wait: {e}")
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
            if await stop_button.count() > 0 and await stop_button.first.is_visible():
                return True
            
            # Проверяем альтернативный селектор кнопки Stop
            stop_button_alt = self.page.locator(self.selectors.STOP_BUTTON_ALT)
            if await stop_button_alt.count() > 0 and await stop_button_alt.first.is_visible():
                return True
            
            # Проверяем фазу "thinking" в последнем ответе
            thinking_phase = self.page.locator(self.selectors.PHASE_THINKING)
            if await thinking_phase.count() > 0:
                last_thinking = thinking_phase.last
                if await last_thinking.is_visible():
                    return True
            
            # Проверяем статус-карточку "Мысль..."
            status_cards = self.page.locator(self.selectors.THINKING_CARD)
            if await status_cards.count() > 0:
                last_card = status_cards.last
                if await last_card.is_visible():
                    title = self.page.locator(self.selectors.THINKING_TITLE).last
                    title_text = await title.inner_text() if await title.count() > 0 else ""
                    # Если статус не "завершена", значит ещё думает
                    if "завершена" not in title_text.lower() and "completed" not in title_text.lower():
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking generation status: {e}")
            return False
    
    async def get_last_response(self) -> Optional[str]:
        """Получить последний ответ."""
        if not self.page:
            return None
        
        try:
            # Ищем все блоки ответов ассистента
            responses = self.page.locator(self.selectors.ASSISTANT_MESSAGE)
            count = await responses.count()
            
            if count == 0:
                logger.warning("No assistant messages found")
                return None
            
            # Берём последний ответ
            last_response = responses.nth(count - 1)
            
            # Ищем контент внутри
            content = last_response.locator(self.selectors.RESPONSE_CONTENT)
            
            if await content.count() > 0:
                text = await content.inner_text()
                text = text.strip()
                logger.debug(f"Got response: {len(text)} chars")
                return text
            
            # Альтернативный способ - через параграфы
            paragraphs = last_response.locator(self.selectors.RESPONSE_TEXT)
            if await paragraphs.count() > 0:
                texts = []
                for i in range(await paragraphs.count()):
                    p_text = await paragraphs.nth(i).inner_text()
                    texts.append(p_text.strip())
                return "\n".join(texts)
            
            # Fallback - весь текст из блока ответа
            response_block = last_response.locator(self.selectors.ASSISTANT_RESPONSE)
            if await response_block.count() > 0:
                text = await response_block.inner_text()
                return text.strip()
            
            return None
            
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
        """Остановить генерацию."""
        if not self.page:
            return False
        
        try:
            # Пробуем основной селектор
            stop_button = self.page.locator(self.selectors.STOP_BUTTON)
            if await stop_button.count() > 0 and await stop_button.first.is_visible():
                await stop_button.first.click()
                logger.info("Generation stopped")
                return True
            
            # Пробуем альтернативный
            stop_button_alt = self.page.locator(self.selectors.STOP_BUTTON_ALT)
            if await stop_button_alt.count() > 0 and await stop_button_alt.first.is_visible():
                await stop_button_alt.first.click()
                logger.info("Generation stopped (alt)")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error stopping generation: {e}")
            return False
