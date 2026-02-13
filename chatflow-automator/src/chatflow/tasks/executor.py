"""
Task Executor - выполнение задач с использованием адаптеров.
"""
import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Callable, Any

from ..core.types import (
    TaskCard, TaskSequence, TaskResult, SessionResult,
    TaskStatus, generate_id
)
from ..core.events import EventEmitter
from ..adapters.base import ChatAdapter

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Исполнитель задач."""
    
    def __init__(
        self, 
        adapter: ChatAdapter,
        event_emitter: Optional[EventEmitter] = None
    ):
        """
        Инициализация исполнителя.
        
        Args:
            adapter: Адаптер чата
            event_emitter: Система событий
        """
        self.adapter = adapter
        self.events = event_emitter or EventEmitter()
        
        self._is_running = False
        self._is_paused = False
        self._should_stop = False
        
        self._current_task: Optional[TaskCard] = None
        self._current_session: Optional[SessionResult] = None
        
        logger.info("TaskExecutor initialized")
    
    @property
    def is_running(self) -> bool:
        """Выполняется ли последовательность."""
        return self._is_running
    
    @property
    def is_paused(self) -> bool:
        """На паузе ли выполнение."""
        return self._is_paused
    
    async def execute_sequence(
        self, 
        sequence: TaskSequence,
        on_task_start: Optional[Callable] = None,
        on_task_complete: Optional[Callable] = None,
    ) -> SessionResult:
        """
        Выполнить последовательность задач.
        
        Args:
            sequence: Последовательность задач
            on_task_start: Callback при начале задачи
            on_task_complete: Callback при завершении задачи
            
        Returns:
            Результат сессии
        """
        self._is_running = True
        self._should_stop = False
        self._is_paused = False
        
        # Создаём сессию
        session = SessionResult(
            session_id=generate_id(),
            sequence_name=sequence.name,
            started_at=datetime.now(),
        )
        self._current_session = session
        
        logger.info(f"Starting sequence: {sequence.name}")
        self.events.emit('sequence_started', {'name': sequence.name})
        
        # Проверяем готовность адаптера
        try:
            is_ready = await self.adapter.is_ready()
            if not is_ready:
                logger.warning("Adapter reports not ready, but continuing...")
        except Exception as e:
            logger.warning(f"Adapter readiness check failed: {e}")
        
        # Выполняем задачи
        enabled_cards = [c for c in sequence.cards if c.enabled]
        total = len(enabled_cards)
        
        for index, card in enumerate(enabled_cards):
            if self._should_stop:
                logger.info("Execution stopped by user")
                break
            
            # Пауза
            while self._is_paused and not self._should_stop:
                await asyncio.sleep(0.1)
            
            if self._should_stop:
                break
            
            self._current_task = card
            
            # Callback начала
            if on_task_start:
                try:
                    on_task_start(card, index, total)
                except Exception as e:
                    logger.debug(f"on_task_start callback error: {e}")
            
            self.events.emit('task_started', {
                'card': card,
                'index': index,
                'total': total
            })
            
            # Выполняем задачу
            result = await self._execute_task(card)
            session.results.append(result)
            
            # Callback завершения
            if on_task_complete:
                try:
                    on_task_complete(result, index, total)
                except Exception as e:
                    logger.debug(f"on_task_complete callback error: {e}")
            
            self.events.emit('task_completed', {
                'result': result,
                'index': index,
                'total': total
            })
            
            # Интервал перед следующей задачей
            if index < total - 1 and not self._should_stop:
                interval = card.interval_after
                if interval > 0:
                    logger.info(f"Waiting {interval} seconds before next task")
                    await self._interruptible_sleep(interval)
        
        # Завершаем сессию
        session.completed_at = datetime.now()
        session.total_tasks = total
        session.successful_tasks = sum(
            1 for r in session.results if r.status == TaskStatus.COMPLETED
        )
        
        self._is_running = False
        self._current_task = None
        self._current_session = None
        
        logger.info(
            f"Sequence completed: {session.successful_tasks}/{session.total_tasks} tasks"
        )
        self.events.emit('sequence_completed', {'session': session})
        
        return session
    
    async def _execute_task(self, card: TaskCard) -> TaskResult:
        """
        Выполнить одну задачу.
        
        Args:
            card: Карточка задачи
            
        Returns:
            Результат выполнения
        """
        result = TaskResult(
            task_id=card.id,
            task_name=card.name,
            prompt=card.prompt,
            started_at=datetime.now(),
            status=TaskStatus.RUNNING,
        )
        
        logger.info(f"Executing task: {card.name}")
        
        retries = 0
        max_retries = card.retry_count
        
        while retries <= max_retries:
            try:
                # Отправляем сообщение
                sent = await self.adapter.send_message(card.prompt)
                
                if not sent:
                    raise Exception("Failed to send message")
                
                # Ждём ответа
                timeout = card.timeout * 1000  # в миллисекунды
                received = await self.adapter.wait_for_response(timeout=timeout)
                
                if received:
                    # Получаем ответ
                    response = await self.adapter.get_last_response()
                    
                    result.response = response
                    result.status = TaskStatus.COMPLETED
                    result.completed_at = datetime.now()
                    
                    logger.info(f"Task completed: {card.name}")
                    return result
                else:
                    raise Exception("Timeout waiting for response")
                    
            except Exception as e:
                retries += 1
                error_msg = str(e)
                
                if retries <= max_retries:
                    logger.warning(
                        f"Task failed (attempt {retries}/{max_retries + 1}): {error_msg}"
                    )
                    await asyncio.sleep(card.retry_delay)
                else:
                    result.status = TaskStatus.FAILED
                    result.error = error_msg
                    result.completed_at = datetime.now()
                    
                    logger.error(f"Task failed: {card.name} - {error_msg}")
                    return result
        
        return result
    
    async def _interruptible_sleep(self, seconds: float) -> None:
        """
        Прерываемая пауза.
        
        Args:
            seconds: Время в секундах
        """
        end_time = asyncio.get_event_loop().time() + seconds
        
        while asyncio.get_event_loop().time() < end_time:
            if self._should_stop:
                return
            while self._is_paused and not self._should_stop:
                await asyncio.sleep(0.1)
            await asyncio.sleep(0.1)
    
    def pause(self) -> None:
        """Приостановить выполнение."""
        if self._is_running:
            self._is_paused = True
            logger.info("Execution paused")
            self.events.emit('execution_paused')
    
    def resume(self) -> None:
        """Возобновить выполнение."""
        if self._is_paused:
            self._is_paused = False
            logger.info("Execution resumed")
            self.events.emit('execution_resumed')
    
    def stop(self) -> None:
        """Остановить выполнение."""
        self._should_stop = True
        self._is_paused = False
        logger.info("Stop requested")
        self.events.emit('execution_stop_requested')
