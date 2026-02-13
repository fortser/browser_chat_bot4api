"""Main application window."""

import asyncio
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QStatusBar,
    QLabel,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QCloseEvent, QAction

from ..core.engine import Engine, get_engine
from ..core.events import EventEmitter, get_event_emitter
from ..core.types import BrowserStatus, TaskStatus, SessionResult
from ..storage.config import ConfigManager
from ..storage.results import ResultsManager
from ..utils.paths import get_config_path, get_data_dir
from ..utils.logging import get_logger

from .widgets.connection_tab import ConnectionTab
from .widgets.tasks_tab import TasksTab
from .widgets.execution_tab import ExecutionTab
from .widgets.results_tab import ResultsTab

logger = get_logger(__name__)


class DisconnectWorker(QThread):
    """Worker for disconnecting browser."""
    finished = pyqtSignal()
    
    def __init__(self, engine: Engine):
        super().__init__()
        self.engine = engine
    
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.engine.disconnect())
            loop.close()
        except Exception as e:
            logger.error(f"Disconnect error: {e}")
        self.finished.emit()


class MainWindow(QMainWindow):
    """
    Main application window.
    
    Contains tabs for connection, tasks, execution, and results.
    """
    
    # Signals for thread-safe UI updates
    status_changed = pyqtSignal(str)
    browser_status_changed = pyqtSignal(object)
    task_progress = pyqtSignal(object)
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.engine = get_engine()
        self.events = get_event_emitter()
        self.config = ConfigManager(get_config_path())
        self.results_manager = ResultsManager(get_data_dir() / "results")
        
        self._disconnect_worker: Optional[DisconnectWorker] = None
        
        # Load configuration
        try:
            self.config.load()
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
        
        # Setup UI
        self._setup_ui()
        self._setup_signals()
        self._setup_events()
        self._restore_window_state()
        
        logger.info("Main window initialized")
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        self.setWindowTitle("ChatFlow Automator")
        self.setMinimumSize(800, 600)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Create tabs
        self.connection_tab = ConnectionTab(self.config, self.engine)
        self.tasks_tab = TasksTab(self.config)
        self.execution_tab = ExecutionTab(self.engine, self.events)
        self.results_tab = ResultsTab(self.results_manager)
        
        # Add tabs
        self.tabs.addTab(self.connection_tab, "Подключение")
        self.tabs.addTab(self.tasks_tab, "Задачи")
        self.tabs.addTab(self.execution_tab, "Выполнение")
        self.tabs.addTab(self.results_tab, "Результаты")
        
        # Status bar
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)
        
        # Status indicator
        self.status_label = QLabel("● Отключено")
        self.status_label.setStyleSheet("color: gray;")
        self._status_bar.addPermanentWidget(self.status_label)
        
        # Menu bar
        self._setup_menu()
    
    def _setup_menu(self) -> None:
        """Setup menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("Файл")
        
        save_config_action = QAction("Сохранить конфигурацию", self)
        save_config_action.triggered.connect(self._save_config)
        file_menu.addAction(save_config_action)
        
        load_config_action = QAction("Загрузить конфигурацию...", self)
        load_config_action.triggered.connect(self._load_config)
        file_menu.addAction(load_config_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("Справка")
        
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_signals(self) -> None:
        """Setup Qt signals."""
        self.status_changed.connect(self._update_status)
        self.browser_status_changed.connect(self._on_browser_status)
        self.task_progress.connect(self._on_task_progress)
        
        # Connect tabs
        self.connection_tab.connection_ready.connect(self._on_connection_ready)
        self.execution_tab.execution_started.connect(self._on_execution_started)
        self.execution_tab.execution_finished.connect(self._on_execution_finished)
    
    def _setup_events(self) -> None:
        """Setup event listeners."""
        self.events.on("status_changed", 
                       lambda s: self.browser_status_changed.emit(s))
        self.events.on("task_completed",
                       lambda r: self.task_progress.emit(r))
        self.events.on("session_completed",
                       lambda s: self._on_session_completed(s))
    
    def _restore_window_state(self) -> None:
        """Restore window position and size."""
        width = self.config.get("ui.window_width", 1000)
        height = self.config.get("ui.window_height", 700)
        self.resize(width, height)
        
        x = self.config.get("ui.window_x")
        y = self.config.get("ui.window_y")
        if x is not None and y is not None:
            self.move(x, y)
    
    def _save_window_state(self) -> None:
        """Save window position and size."""
        self.config.set("ui.window_width", self.width())
        self.config.set("ui.window_height", self.height())
        self.config.set("ui.window_x", self.x())
        self.config.set("ui.window_y", self.y())
    
    def _update_status(self, status: str) -> None:
        """Update status bar text."""
        self._status_bar.showMessage(status, 5000)
    
    def _on_browser_status(self, status: BrowserStatus) -> None:
        """Handle browser status changes."""
        status_map = {
            BrowserStatus.DISCONNECTED: ("● Отключено", "gray"),
            BrowserStatus.CONNECTING: ("● Подключение...", "orange"),
            BrowserStatus.CONNECTED: ("● Подключено", "blue"),
            BrowserStatus.DISCONNECTING: ("● Отключение...", "orange"),
            BrowserStatus.NAVIGATING: ("● Навигация...", "blue"),
            BrowserStatus.READY: ("● Готов", "green"),
            BrowserStatus.ERROR: ("● Ошибка", "red"),
        }
        
        text, color = status_map.get(status, ("● Неизвестно", "gray"))
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")
    
    def _on_connection_ready(self) -> None:
        """Handle connection ready."""
        self.tabs.setCurrentWidget(self.tasks_tab)
        self.status_changed.emit("Подключение установлено")
    
    def _on_execution_started(self) -> None:
        """Handle execution started."""
        self.connection_tab.setEnabled(False)
        self.tasks_tab.setEnabled(False)
    
    def _on_execution_finished(self) -> None:
        """Handle execution finished."""
        self.connection_tab.setEnabled(True)
        self.tasks_tab.setEnabled(True)
        self.results_tab.refresh()
    
    def _on_task_progress(self, result) -> None:
        """Handle task progress."""
        if hasattr(result, 'status') and hasattr(result, 'task_name'):
            status = "✓" if result.status == TaskStatus.COMPLETED else "✗"
            self.status_changed.emit(f"Задача '{result.task_name}': {status}")
    
    def _on_session_completed(self, session: SessionResult) -> None:
        """Handle session completed."""
        # Save results
        try:
            self.results_manager.save_session(session)
            self.results_tab.refresh()
            self.status_changed.emit(
                f"Выполнено: {session.completed_tasks}/{session.total_tasks} задач"
            )
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def _save_config(self) -> None:
        """Save configuration."""
        try:
            # Update config from tabs
            self.connection_tab.save_to_config()
            self.tasks_tab.save_to_config()
            
            self._save_window_state()
            self.config.save()
            
            self.status_changed.emit("Конфигурация сохранена")
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить: {e}")
    
    def _load_config(self) -> None:
        """Load configuration from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить конфигурацию",
            str(get_data_dir()),
            "JSON файлы (*.json)"
        )
        
        if file_path:
            try:
                self.config.load(Path(file_path))
                self.connection_tab.load_from_config()
                self.tasks_tab.load_from_config()
                self.status_changed.emit("Конфигурация загружена")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить: {e}")
    
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            "О программе",
            "ChatFlow Automator v0.1.0\n\n"
            "Система автоматизации\n"
            "взаимодействия с веб-чатами.\n\n"
            "© 2026 ChatFlow Team"
        )
    # В файле src/chatflow/gui/main_window.py
# Замените метод closeEvent на этот:

def closeEvent(self, event: QCloseEvent) -> None:
    """Handle window close."""
    # Check if execution is running
    if hasattr(self, '_worker') and self._worker:
        if self._worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                "Выполнение задач в процессе. Остановить и выйти?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
    
    # Сохраняем cookies перед закрытием
    if self.engine.is_connected:
        try:
            import asyncio
            from pathlib import Path
            from chatflow.utils.paths import get_cookies_dir
            import urllib.parse
            
            # Получаем URL и формируем имя файла
            if hasattr(self.engine, '_current_url') and self.engine._current_url:
                domain = urllib.parse.urlparse(self.engine._current_url).netloc
                cookies_path = get_cookies_dir() / f"{domain}_cookies.json"
                
                logger.info(f"Saving cookies to {cookies_path}")
                
                # Сохраняем cookies синхронно через ThreadsafeBrowser
                if self.engine.browser_manager and self.engine.browser_manager.is_launched:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(
                            self.engine.browser_manager.save_cookies(str(cookies_path))
                        )
                        logger.info(f"Cookies saved successfully")
                    except Exception as e:
                        logger.error(f"Failed to save cookies: {e}")
                    finally:
                        loop.close()
        except Exception as e:
            logger.error(f"Error saving cookies on close: {e}")
    
    # Disconnect browser
    if self.engine.is_connected:
        self._disconnect_worker = DisconnectWorker(self.engine)
        self._disconnect_worker.start()
        self._disconnect_worker.wait(5000)
    
    # Save config
    try:
        self._save_window_state()
        self.config.save()
    except Exception as e:
        logger.error(f"Failed to save config on close: {e}")
    
    # Cleanup engine
    self.engine.cleanup()
    
    event.accept()
