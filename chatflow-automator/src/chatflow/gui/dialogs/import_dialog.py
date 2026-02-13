"""Import dialog."""

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

from ...utils.paths import get_tasks_dir


class ImportDialog(QDialog):
    """Dialog for importing tasks."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.file_path = ""
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        self.setWindowTitle("Импорт задач")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # File selection
        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Файл:"))
        self.file_edit = QLineEdit()
        self.file_edit.setReadOnly(True)
        file_row.addWidget(self.file_edit)
        
        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self._browse_file)
        file_row.addWidget(browse_btn)
        layout.addLayout(file_row)
        
        # Format info
        layout.addWidget(QLabel("Поддерживаемые форматы: JSON, YAML, TXT"))
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _browse_file(self) -> None:
        """Browse for file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Выберите файл",
            str(get_tasks_dir()),
            "Все поддерживаемые (*.json *.yaml *.yml *.txt);;JSON (*.json);;YAML (*.yaml *.yml);;Text (*.txt)"
        )
        if file_path:
            self.file_edit.setText(file_path)
            self.file_path = file_path
    
    def _validate_and_accept(self) -> None:
        """Validate and accept."""
        if self.file_path and Path(self.file_path).exists():
            self.accept()
    
    def get_file_path(self) -> str:
        """Get selected file path."""
        return self.file_path
