"""Results viewing tab."""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QSplitter,
    QFileDialog,
    QMessageBox,
    QHeaderView,
    QComboBox,
)
from PyQt6.QtCore import Qt

from ...core.types import SessionResult, TaskStatus
from ...storage.results import ResultsManager
from ...storage.export import get_exporter
from ...utils.paths import get_results_dir
from ...utils.logging import get_logger

logger = get_logger(__name__)


class ResultsTab(QWidget):
    """
    Results viewing tab.
    
    Displays execution results and allows exporting.
    """
    
    def __init__(self, results_manager: ResultsManager):
        super().__init__()
        self.results_manager = results_manager
        self._current_session: Optional[SessionResult] = None
        
        self._setup_ui()
        self.refresh()
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.refresh)
        controls_layout.addWidget(self.refresh_btn)
        
        controls_layout.addStretch()
        
        controls_layout.addWidget(QLabel("Экспорт в:"))
        self.export_format = QComboBox()
        self.export_format.addItems(["JSON", "Markdown", "CSV"])
        controls_layout.addWidget(self.export_format)
        
        self.export_btn = QPushButton("Экспорт...")
        self.export_btn.clicked.connect(self._export_results)
        self.export_btn.setEnabled(False)
        controls_layout.addWidget(self.export_btn)
        
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self._delete_session)
        self.delete_btn.setEnabled(False)
        controls_layout.addWidget(self.delete_btn)
        
        layout.addLayout(controls_layout)
        
        # Splitter
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Sessions table
        sessions_widget = QWidget()
        sessions_layout = QVBoxLayout(sessions_widget)
        sessions_layout.setContentsMargins(0, 0, 0, 0)
        
        sessions_layout.addWidget(QLabel("Сессии:"))
        
        self.sessions_table = QTableWidget()
        self.sessions_table.setColumnCount(5)
        self.sessions_table.setHorizontalHeaderLabels([
            "Дата", "Название", "Всего", "Выполнено", "Ошибки"
        ])
        self.sessions_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.sessions_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.sessions_table.itemSelectionChanged.connect(self._on_session_selected)
        
        header = self.sessions_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        sessions_layout.addWidget(self.sessions_table)
        splitter.addWidget(sessions_widget)
        
        # Results detail
        detail_widget = QWidget()
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        
        detail_layout.addWidget(QLabel("Результаты:"))
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels([
            "Задача", "Статус", "Время", "Ответ (превью)"
        ])
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.itemSelectionChanged.connect(self._on_result_selected)
        
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        
        detail_layout.addWidget(self.results_table)
        
        # Full response
        detail_layout.addWidget(QLabel("Полный ответ:"))
        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setMaximumHeight(150)
        detail_layout.addWidget(self.response_text)
        
        splitter.addWidget(detail_widget)
        splitter.setSizes([200, 300])
        layout.addWidget(splitter)
    
    def refresh(self) -> None:
        """Refresh sessions list."""
        self.sessions_table.setRowCount(0)
        self._current_session = None
        self.results_table.setRowCount(0)
        self.response_text.clear()
        
        sessions = self.results_manager.list_sessions()
        
        for session in sessions:
            row = self.sessions_table.rowCount()
            self.sessions_table.insertRow(row)
            
            started = session.get("started_at", "")
            date_str = started[:19].replace("T", " ") if started else "—"
            
            date_item = QTableWidgetItem(date_str)
            date_item.setData(Qt.ItemDataRole.UserRole, session.get("session_id"))
            self.sessions_table.setItem(row, 0, date_item)
            self.sessions_table.setItem(row, 1, QTableWidgetItem(session.get("sequence_name", "")))
            self.sessions_table.setItem(row, 2, QTableWidgetItem(str(session.get("total_tasks", 0))))
            self.sessions_table.setItem(row, 3, QTableWidgetItem(str(session.get("completed_tasks", 0))))
            self.sessions_table.setItem(row, 4, QTableWidgetItem(str(session.get("failed_tasks", 0))))
        
        self.export_btn.setEnabled(False)
        self.delete_btn.setEnabled(False)
    
    def _on_session_selected(self) -> None:
        """Handle session selection."""
        selected = self.sessions_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        session_id = self.sessions_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if session_id:
            try:
                self._current_session = self.results_manager.load_session(session_id)
                self._display_session(self._current_session)
                self.export_btn.setEnabled(True)
                self.delete_btn.setEnabled(True)
            except Exception as e:
                logger.error(f"Failed to load session: {e}")
    
    def _display_session(self, session: SessionResult) -> None:
        """Display session results."""
        self.results_table.setRowCount(0)
        self.response_text.clear()
        
        for result in session.results:
            row = self.results_table.rowCount()
            self.results_table.insertRow(row)
            
            name_item = QTableWidgetItem(result.task_name)
            name_item.setData(Qt.ItemDataRole.UserRole, result)
            self.results_table.setItem(row, 0, name_item)
            
            status_text = "✓" if result.status == TaskStatus.COMPLETED else "✗"
            self.results_table.setItem(row, 1, QTableWidgetItem(status_text))
            self.results_table.setItem(row, 2, QTableWidgetItem(f"{result.duration_seconds:.1f}с"))
            
            preview = result.response[:100].replace("\n", " ")
            if len(result.response) > 100:
                preview += "..."
            self.results_table.setItem(row, 3, QTableWidgetItem(preview))
    
    def _on_result_selected(self) -> None:
        """Handle result selection."""
        selected = self.results_table.selectedItems()
        if not selected:
            return
        
        row = selected[0].row()
        result = self.results_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        
        if result:
            text = f"Промпт:\n{result.prompt}\n\nОтвет:\n{result.response}"
            if result.error_message:
                text += f"\n\nОшибка: {result.error_message}"
            self.response_text.setPlainText(text)
    
    def _export_results(self) -> None:
        """Export current session."""
        if not self._current_session:
            return
        
        format_name = self.export_format.currentText().lower()
        ext_map = {"json": ".json", "markdown": ".md", "csv": ".csv"}
        ext = ext_map.get(format_name, ".txt")
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт результатов",
            str(get_results_dir() / f"{self._current_session.session_id}{ext}"),
            f"Файлы (*{ext})"
        )
        
        if file_path:
            try:
                exporter = get_exporter(format_name)
                exporter.export(self._current_session, file_path)
                QMessageBox.information(self, "Успех", "Результаты экспортированы")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось экспортировать: {e}")
    
    def _delete_session(self) -> None:
        """Delete current session."""
        if not self._current_session:
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение", "Удалить выбранную сессию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.results_manager.delete_session(self._current_session.session_id)
            self.refresh()
