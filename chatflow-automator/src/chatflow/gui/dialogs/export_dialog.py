"""Export dialog."""

from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QDialogButtonBox,
    QFileDialog,
    QComboBox,
)

from ...utils.paths import get_results_dir


class ExportDialog(QDialog):
    """Dialog for exporting results."""
    
    def __init__(self, default_name: str = "export", parent=None):
        super().__init__(parent)
        self.default_name = default_name
        self.file_path = ""
        self.format = "json"
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        self.setWindowTitle("Экспорт результатов")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Format selection
        format_row = QHBoxLayout()
        format_row.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["JSON", "Markdown", "CSV"])
        self.format_combo.currentTextChanged.connect(self._update_extension)
        format_row.addWidget(self.format_combo)
        format_row.addStretch()
        layout.addLayout(format_row)
        
        # File selection
        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Файл:"))
        self.file_edit = QLineEdit()
        file_row.addWidget(self.file_edit)
        
        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)
        
        # Set default path
        self._update_extension()
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _update_extension(self) -> None:
        """Update file extension based on format."""
        ext_map = {"JSON": ".json", "Markdown": ".md", "CSV": ".csv"}
        ext = ext_map.get(self.format_combo.currentText(), ".json")
        self.file_edit.setText(str(get_results_dir() / f"{self.default_name}{ext}"))
    
    def _browse_file(self) -> None:
        """Browse for save location."""
        ext_map = {"JSON": "*.json", "Markdown": "*.md", "CSV": "*.csv"}
        ext_filter = ext_map.get(self.format_combo.currentText(), "*.*")
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить как",
            self.file_edit.text(),
            f"Файлы ({ext_filter})"
        )
        if file_path:
            self.file_edit.setText(file_path)
    
    def _validate_and_accept(self) -> None:
        """Validate and accept."""
        if self.file_edit.text():
            self.file_path = self.file_edit.text()
            self.format = self.format_combo.currentText().lower()
            self.accept()
    
    def get_file_path(self) -> str:
        """Get selected file path."""
        return self.file_path
    
    def get_format(self) -> str:
        """Get selected format."""
        return self.format
