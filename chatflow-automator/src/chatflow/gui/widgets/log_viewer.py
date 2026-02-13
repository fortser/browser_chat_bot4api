"""Log viewer widget."""

from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QCheckBox,
    QPushButton,
    QComboBox,
    QLabel,
)
from PyQt6.QtGui import QTextCharFormat, QColor, QFont


class LogViewer(QWidget):
    """Log viewer widget with filtering and auto-scroll."""
    
    def __init__(self):
        super().__init__()
        self._all_logs: list[tuple[str, str, str]] = []
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Controls
        controls = QHBoxLayout()
        
        controls.addWidget(QLabel("Уровень:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["Все", "INFO", "WARNING", "ERROR"])
        self.level_filter.currentTextChanged.connect(self._apply_filter)
        controls.addWidget(self.level_filter)
        
        controls.addStretch()
        
        self.auto_scroll = QCheckBox("Автопрокрутка")
        self.auto_scroll.setChecked(True)
        controls.addWidget(self.auto_scroll)
        
        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self.clear)
        controls.addWidget(self.clear_btn)
        
        layout.addLayout(controls)
        
        # Log text
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log_text)
    
    def log(self, message: str, level: str = "INFO") -> None:
        """Add a log message."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._all_logs.append((timestamp, level, message))
        
        current_filter = self.level_filter.currentText()
        if current_filter != "Все" and level != current_filter:
            return
        
        self._append_formatted(timestamp, level, message)
    
    def _append_formatted(self, timestamp: str, level: str, message: str) -> None:
        """Append formatted log entry."""
        colors = {
            "INFO": QColor(0, 128, 0),
            "WARNING": QColor(255, 165, 0),
            "ERROR": QColor(255, 0, 0),
        }
        color = colors.get(level, QColor(0, 0, 0))
        
        fmt = QTextCharFormat()
        fmt.setForeground(color)
        
        cursor = self.log_text.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(f"{timestamp} [{level}] ", fmt)
        
        default_fmt = QTextCharFormat()
        cursor.insertText(f"{message}\n", default_fmt)
        
        if self.auto_scroll.isChecked():
            scrollbar = self.log_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
    
    def _apply_filter(self) -> None:
        """Apply level filter."""
        self.log_text.clear()
        current_filter = self.level_filter.currentText()
        
        for timestamp, level, message in self._all_logs:
            if current_filter == "Все" or level == current_filter:
                self._append_formatted(timestamp, level, message)
    
    def clear(self) -> None:
        """Clear all logs."""
        self._all_logs.clear()
        self.log_text.clear()
    
    def get_logs(self) -> str:
        """Get all logs as text."""
        return self.log_text.toPlainText()
