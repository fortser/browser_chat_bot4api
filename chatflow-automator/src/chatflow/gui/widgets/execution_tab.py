"""
Execution control tab - исправленная версия.
"""

import logging
from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QProgressBar,
    QPlainTextEdit,
    QCheckBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QThread, QObject

from ...core.engine import Engine
from ...core.events import EventEmitter
from ...core.types import TaskStatus, TaskResult, SessionResult, TaskSequence, TaskCard
from ...utils.logging import get_logger

logger = get_logger(__name__)


class TaskSignals(QObject):
    """Сигналы для коммуникации между worker thread и GUI."""
    task_started = pyqtSignal(object, int, int)  # card, index, total
    task_completed = pyqtSignal(object)  # TaskResult
    sequence_completed = pyqtSignal(object)  # SessionResult
    error_occurred = pyqtSignal(str)
    log_message = pyqtSignal(str)
    progress_update = pyqtSignal(int)


class TaskExecutionWorker(QThread):
    """
    Worker thread для выполнения задач.
    
    Работает в отдельном потоке и использует
    синхронные методы адаптера через ThreadsafeBrowser.
    """
    
    def __init__(self, engine: Engine, sequence: TaskSequence, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.sequence = sequence
        self.signals = TaskSignals()
        
        self._stop_requested = False
        self._pause_requested = False
    
    def run(self):
        """Основной метод потока."""
        try:
            self._execute_sequence()
        except Exception as e:
            logger.error(f"Execution error: {e}")
            self.signals.error_occurred.emit(str(e))
    
    def _execute_sequence(self):
        """Выполнить последовательность задач."""
        session = SessionResult(
            sequence_name=self.sequence.name,
            total_tasks=len(self.sequence.enabled_cards),
        )
        
        self.signals.log_message.emit(f"[INFO] Начало выполнения: {self.sequence.name}")
        
        enabled_cards = self.sequence.enabled_cards
        total = len(enabled_cards)
        
        for index, card in enumerate(enabled_cards):
            if self._stop_requested:
                self.signals.log_message.emit("[INFO] Выполнение остановлено")
                break
            
            # Пауза
            while self._pause_requested and not self._stop_requested:
                self.msleep(100)
            
            if self._stop_requested:
                break
            
            self.signals.task_started.emit(card, index, total)
            self.signals.log_message.emit(f"[INFO] Задача {index + 1}/{total}: {card.name}")
            
            # Выполняем задачу
            result = self._execute_task(card)
            session.add_result(result)
            
            self.signals.task_completed.emit(result)
            self.signals.progress_update.emit(index + 1)
            
            status_text = "OK" if result.status == TaskStatus.COMPLETED else "ОШИБКА"
            self.signals.log_message.emit(
                f"[INFO] {card.name}: {status_text} ({result.duration_seconds:.1f}с)"
            )
            
            if result.error_message:
                self.signals.log_message.emit(f"[ERROR] {result.error_message}")
        
        session.completed_at = datetime.now()
        self.signals.sequence_completed.emit(session)
        
        self.signals.log_message.emit(
            f"[INFO] Завершено: {session.completed_tasks}/{session.total_tasks} успешно"
        )
    
    def _execute_task(self, card: TaskCard) -> TaskResult:
        """Выполнить одну задачу."""
        started_at = datetime.now()
        
        try:
            # Пауза перед отправкой
            if card.wait_before > 0:
                self.signals.log_message.emit(f"[DEBUG] Пауза перед отправкой {card.wait_before}с...")
                self.msleep(card.wait_before * 1000)
            
            # Получаем адаптер
            adapter = self.engine.adapter
            if not adapter:
                raise RuntimeError("Adapter not available")
            
            # Проверяем готовность
            if not adapter.is_ready_sync():
                # Ждём готовности
                self.signals.log_message.emit("[DEBUG] Ожидание готовности интерфейса...")
                for _ in range(10):  # 10 попыток по 1 секунде
                    self.msleep(1000)
                    if adapter.is_ready_sync():
                        break
                else:
                    raise RuntimeError("Interface not ready after waiting")
            
            # Отправляем сообщение
            prompt_preview = card.prompt[:50] + "..." if len(card.prompt) > 50 else card.prompt
            self.signals.log_message.emit(f"[DEBUG] Отправка: {prompt_preview}")
            
            success = adapter.send_message_sync(card.prompt)
            if not success:
                raise RuntimeError("Failed to send message")
            
            # Ждём ответ
            self.signals.log_message.emit("[DEBUG] Ожидание ответа...")
            
            response_received = adapter.wait_for_response_sync(card.timeout)
            
            if response_received:
                # Получаем ответ
                response = adapter.get_last_response_sync() or ""
                status = TaskStatus.COMPLETED
                error = None
                self.signals.log_message.emit(f"[DEBUG] Получен ответ: {len(response)} символов")
            else:
                response = ""
                status = TaskStatus.FAILED
                error = "Timeout waiting for response"
                self.signals.log_message.emit("[WARNING] Таймаут ожидания ответа")
            
            # Пауза после получения
            if card.wait_after > 0 and not self._stop_requested:
                self.signals.log_message.emit(f"[DEBUG] Пауза {card.wait_after}с...")
                self.msleep(card.wait_after * 1000)
            
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            
            return TaskResult(
                task_id=card.id,
                task_name=card.name,
                prompt=card.prompt,
                response=response,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                error_message=error,
                duration_seconds=duration,
            )
            
        except Exception as e:
            logger.error(f"Task execution error: {e}")
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            
            return TaskResult(
                task_id=card.id,
                task_name=card.name,
                prompt=card.prompt,
                response="",
                status=TaskStatus.FAILED,
                started_at=started_at,
                completed_at=completed_at,
                error_message=str(e),
                duration_seconds=duration,
            )
    
    def request_stop(self):
        """Запросить остановку."""
        self._stop_requested = True
        self._pause_requested = False
    
    def request_pause(self):
        """Запросить паузу."""
        self._pause_requested = True
    
    def request_resume(self):
        """Возобновить выполнение."""
        self._pause_requested = False


class ExecutionTab(QWidget):
    """Вкладка управления выполнением."""
    
    execution_started = pyqtSignal()
    execution_finished = pyqtSignal()
    
    def __init__(self, engine: Engine, events: EventEmitter):
        super().__init__()
        self.engine = engine
        self.events = events
        self._sequence: Optional[TaskSequence] = None
        self._worker: Optional[TaskExecutionWorker] = None
        self._session: Optional[SessionResult] = None
        self._start_time: Optional[datetime] = None
        
        self._setup_ui()
        self._setup_timers()
    
    def _setup_ui(self) -> None:
        """Настроить интерфейс."""
        layout = QVBoxLayout(self)
        
        # Управление
        controls_group = QGroupBox("Управление")
        controls_layout = QHBoxLayout(controls_group)
        
        self.start_btn = QPushButton("▶ Запустить")
        self.start_btn.clicked.connect(self._start_execution)
        controls_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton("⏸ Пауза")
        self.pause_btn.clicked.connect(self._toggle_pause)
        self.pause_btn.setEnabled(False)
        controls_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton("⏹ Стоп")
        self.stop_btn.clicked.connect(self._stop_execution)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)
        
        controls_layout.addStretch()
        layout.addWidget(controls_group)
        
        # Прогресс
        progress_group = QGroupBox("Прогресс")
        progress_layout = QVBoxLayout(progress_group)
        
        self.task_label = QLabel("Ожидание запуска...")
        progress_layout.addWidget(self.task_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        status_row = QHBoxLayout()
        self.status_label = QLabel("Статус: Готов")
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        self.time_label = QLabel("Время: 00:00:00")
        status_row.addWidget(self.time_label)
        progress_layout.addLayout(status_row)
        
        layout.addWidget(progress_group)
        
        # Лог
        log_group = QGroupBox("Журнал")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        log_layout.addWidget(self.log_text)
        
        self.auto_scroll = QCheckBox("Автопрокрутка")
        self.auto_scroll.setChecked(True)
        log_layout.addWidget(self.auto_scroll)
        
        layout.addWidget(log_group)
    
    def _setup_timers(self) -> None:
        """Настроить таймеры."""
        self._time_timer = QTimer(self)
        self._time_timer.timeout.connect(self._update_time)
    
    def _log(self, message: str) -> None:
        """Добавить сообщение в лог."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.appendPlainText(f"{timestamp} {message}")
        
        if self.auto_scroll.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def _update_time(self) -> None:
        """Обновить отображение времени."""
        if self._start_time:
            elapsed = datetime.now() - self._start_time
            hours, remainder = divmod(int(elapsed.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.time_label.setText(f"Время: {hours:02d}:{minutes:02d}:{seconds:02d}")
    
    def _start_execution(self) -> None:
        """Начать выполнение."""
        if not self.engine.is_connected:
            QMessageBox.warning(self, "Ошибка", "Сначала подключитесь к браузеру")
            return
        
        if not self.engine.adapter:
            QMessageBox.warning(self, "Ошибка", "Адаптер не инициализирован")
            return
        
        # Получаем последовательность из вкладки задач
        parent = self.parent()
        while parent:
            if hasattr(parent, 'tasks_tab'):
                self._sequence = parent.tasks_tab.get_sequence()
                break
            parent = parent.parent()
        
        if not self._sequence or not self._sequence.enabled_cards:
            QMessageBox.warning(self, "Ошибка", "Нет задач для выполнения")
            return
        
        # Настраиваем UI
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        
        total = len(self._sequence.enabled_cards)
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(0)
        
        self._start_time = datetime.now()
        self._time_timer.start(1000)
        
        self.status_label.setText("Статус: Выполняется")
        self.log_text.clear()
        
        # Создаём и запускаем worker
        self._worker = TaskExecutionWorker(self.engine, self._sequence, self)
        
        # Подключаем сигналы
        self._worker.signals.task_started.connect(self._on_task_started)
        self._worker.signals.task_completed.connect(self._on_task_completed)
        self._worker.signals.sequence_completed.connect(self._on_sequence_completed)
        self._worker.signals.error_occurred.connect(self._on_error)
        self._worker.signals.log_message.connect(self._log)
        self._worker.signals.progress_update.connect(self._on_progress_update)
        self._worker.finished.connect(self._on_worker_finished)
        
        self._worker.start()
        self.execution_started.emit()
    
    def _on_task_started(self, card: TaskCard, index: int, total: int) -> None:
        """Обработчик начала задачи."""
        self.task_label.setText(f"Задача {index + 1}/{total}: {card.name}")
    
    def _on_task_completed(self, result: TaskResult) -> None:
        """Обработчик завершения задачи."""
        pass  # Обновление через progress_update
    
    def _on_progress_update(self, value: int) -> None:
        """Обновить прогресс."""
        self.progress_bar.setValue(value)
    
    def _on_sequence_completed(self, session: SessionResult) -> None:
        """Обработчик завершения последовательности."""
        self._session = session
        
        # Сохраняем результаты
        try:
            from ...storage.results import ResultsManager
            from ...utils.paths import get_results_dir
            manager = ResultsManager(get_results_dir())
            manager.save_session(session)
            self._log("[INFO] Результаты сохранены")
        except Exception as e:
            self._log(f"[ERROR] Ошибка сохранения: {e}")
    
    def _on_error(self, error: str) -> None:
        """Обработчик ошибки."""
        self._log(f"[ERROR] {error}")
    
    def _on_worker_finished(self) -> None:
        """Обработчик завершения worker."""
        self._time_timer.stop()
        self._reset_ui()
        self.execution_finished.emit()
    
    def _toggle_pause(self) -> None:
        """Переключить паузу."""
        if not self._worker:
            return
        
        if self.pause_btn.text() == "⏸ Пауза":
            self._worker.request_pause()
            self.pause_btn.setText("▶ Продолжить")
            self.status_label.setText("Статус: Пауза")
            self._log("[INFO] Приостановлено")
        else:
            self._worker.request_resume()
            self.pause_btn.setText("⏸ Пауза")
            self.status_label.setText("Статус: Выполняется")
            self._log("[INFO] Возобновлено")
    
    def _stop_execution(self) -> None:
        """Остановить выполнение."""
        if self._worker:
            self._worker.request_stop()
            self._log("[INFO] Остановка...")
    
    def _reset_ui(self) -> None:
        """Сбросить UI."""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸ Пауза")
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Статус: Готов")
        self.task_label.setText("Ожидание запуска...")
        self._worker = None
