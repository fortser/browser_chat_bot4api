"""Task card editor dialog."""

from typing import Optional

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QCheckBox,
    QDialogButtonBox,
)

from ...core.types import TaskCard


class TaskCardEditor(QDialog):
    """Dialog for editing a task card."""
    
    def __init__(self, card: Optional[TaskCard] = None, parent=None):
        super().__init__(parent)
        self.card = card or TaskCard()
        self._setup_ui()
        self._load_card()
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        self.setWindowTitle("Редактор карточки")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Название:"))
        self.name_edit = QLineEdit()
        name_row.addWidget(self.name_edit)
        layout.addLayout(name_row)
        
        # Prompt
        layout.addWidget(QLabel("Промпт:"))
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setMinimumHeight(150)
        layout.addWidget(self.prompt_edit)
        
        # Settings
        settings_layout = QHBoxLayout()
        
        settings_layout.addWidget(QLabel("Интервал до:"))
        self.wait_before = QSpinBox()
        self.wait_before.setRange(0, 3600)
        self.wait_before.setSuffix(" сек")
        settings_layout.addWidget(self.wait_before)
        
        settings_layout.addWidget(QLabel("После:"))
        self.wait_after = QSpinBox()
        self.wait_after.setRange(0, 3600)
        self.wait_after.setValue(15)
        self.wait_after.setSuffix(" сек")
        settings_layout.addWidget(self.wait_after)
        
        settings_layout.addWidget(QLabel("Таймаут:"))
        self.timeout = QSpinBox()
        self.timeout.setRange(1, 3600)
        self.timeout.setValue(120)
        self.timeout.setSuffix(" сек")
        settings_layout.addWidget(self.timeout)
        
        settings_layout.addStretch()
        layout.addLayout(settings_layout)
        
        # Enabled
        self.enabled_check = QCheckBox("Включена")
        self.enabled_check.setChecked(True)
        layout.addWidget(self.enabled_check)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_card(self) -> None:
        """Load card data to form."""
        self.name_edit.setText(self.card.name)
        self.prompt_edit.setPlainText(self.card.prompt)
        self.wait_before.setValue(self.card.wait_before)
        self.wait_after.setValue(self.card.wait_after)
        self.timeout.setValue(self.card.timeout)
        self.enabled_check.setChecked(self.card.enabled)
    
    def _save_and_accept(self) -> None:
        """Save form data to card and accept."""
        self.card.name = self.name_edit.text().strip()
        self.card.prompt = self.prompt_edit.toPlainText()
        self.card.wait_before = self.wait_before.value()
        self.card.wait_after = self.wait_after.value()
        self.card.timeout = self.timeout.value()
        self.card.enabled = self.enabled_check.isChecked()
        self.accept()
    
    def get_card(self) -> TaskCard:
        """Get the edited card."""
        return self.card
