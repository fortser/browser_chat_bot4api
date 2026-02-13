"""Tasks management tab."""

from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QFileDialog,
    QMessageBox,
    QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal

from ...core.types import TaskCard, TaskSequence, generate_id
from ...storage.config import ConfigManager
from ...tasks.loader import TaskLoader
from ...utils.paths import get_tasks_dir
from ...utils.logging import get_logger

logger = get_logger(__name__)


class TaskCardWidget(QListWidgetItem):
    """List item representing a task card."""
    
    def __init__(self, card: TaskCard):
        super().__init__()
        self.card = card
        self._update_display()
    
    def _update_display(self) -> None:
        """Update display text."""
        status = "✓" if self.card.enabled else "○"
        self.setText(f"{status} {self.card.name}")
        
        # Set tooltip
        prompt_preview = self.card.prompt[:50] + "..." if len(self.card.prompt) > 50 else self.card.prompt
        self.setToolTip(prompt_preview)
    
    def update_from_card(self) -> None:
        """Update display from card data."""
        self._update_display()


class TasksTab(QWidget):
    """
    Tasks management tab.
    
    Allows creating, editing, and organizing task cards.
    """
    
    sequence_changed = pyqtSignal()
    
    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config = config
        self.loader = TaskLoader()
        self.sequence = TaskSequence(name="Новая последовательность")
        self._current_card: Optional[TaskCard] = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Sequence info
        info_group = QGroupBox("Последовательность задач")
        info_layout = QVBoxLayout(info_group)
        
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Название:"))
        self.sequence_name = QLineEdit()
        self.sequence_name.textChanged.connect(self._on_sequence_name_changed)
        name_row.addWidget(self.sequence_name)
        info_layout.addLayout(name_row)
        
        # Buttons row
        buttons_row = QHBoxLayout()
        
        self.import_btn = QPushButton("Импорт из файла...")
        self.import_btn.clicked.connect(self._import_tasks)
        buttons_row.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("Экспорт...")
        self.export_btn.clicked.connect(self._export_tasks)
        buttons_row.addWidget(self.export_btn)
        
        self.load_prompts_btn = QPushButton("Загрузить промпты...")
        self.load_prompts_btn.clicked.connect(self._load_prompts)
        buttons_row.addWidget(self.load_prompts_btn)
        
        buttons_row.addStretch()
        info_layout.addLayout(buttons_row)
        
        layout.addWidget(info_group)
        
        # Splitter for cards list and editor
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Cards list
        cards_widget = QWidget()
        cards_layout = QVBoxLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        
        cards_layout.addWidget(QLabel("Карточки:"))
        
        self.cards_list = QListWidget()
        self.cards_list.currentItemChanged.connect(self._on_card_selected)
        cards_layout.addWidget(self.cards_list)
        
        # Card buttons
        card_buttons = QHBoxLayout()
        
        self.add_card_btn = QPushButton("+")
        self.add_card_btn.setMaximumWidth(40)
        self.add_card_btn.clicked.connect(self._add_card)
        card_buttons.addWidget(self.add_card_btn)
        
        self.remove_card_btn = QPushButton("-")
        self.remove_card_btn.setMaximumWidth(40)
        self.remove_card_btn.clicked.connect(self._remove_card)
        card_buttons.addWidget(self.remove_card_btn)
        
        self.move_up_btn = QPushButton("↑")
        self.move_up_btn.setMaximumWidth(40)
        self.move_up_btn.clicked.connect(self._move_card_up)
        card_buttons.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("↓")
        self.move_down_btn.setMaximumWidth(40)
        self.move_down_btn.clicked.connect(self._move_card_down)
        card_buttons.addWidget(self.move_down_btn)
        
        card_buttons.addStretch()
        cards_layout.addLayout(card_buttons)
        
        splitter.addWidget(cards_widget)
        
        # Card editor
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        
        editor_layout.addWidget(QLabel("Редактор карточки:"))
        
        # Name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Название:"))
        self.card_name = QLineEdit()
        name_row.addWidget(self.card_name)
        editor_layout.addLayout(name_row)
        
        # Prompt
        editor_layout.addWidget(QLabel("Промпт:"))
        self.card_prompt = QTextEdit()
        self.card_prompt.setMinimumHeight(100)
        editor_layout.addWidget(self.card_prompt)
        
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
        editor_layout.addLayout(settings_layout)
        
        # Enabled checkbox
        self.card_enabled = QCheckBox("Включена")
        self.card_enabled.setChecked(True)
        editor_layout.addWidget(self.card_enabled)
        
        # Save button
        self.save_card_btn = QPushButton("Сохранить карточку")
        self.save_card_btn.clicked.connect(self._save_current_card)
        editor_layout.addWidget(self.save_card_btn)
        
        editor_layout.addStretch()
        
        splitter.addWidget(editor_widget)
        
        # Set splitter sizes
        splitter.setSizes([300, 400])
        
        layout.addWidget(splitter)
        
        # Default interval
        default_row = QHBoxLayout()
        default_row.addWidget(QLabel("Интервал по умолчанию:"))
        self.default_interval = QSpinBox()
        self.default_interval.setRange(0, 3600)
        self.default_interval.setValue(15)
        self.default_interval.setSuffix(" сек")
        self.default_interval.valueChanged.connect(self._on_default_interval_changed)
        default_row.addWidget(self.default_interval)
        default_row.addStretch()
        layout.addLayout(default_row)
        
        # Update UI state
        self._update_editor_state(False)
    
    def _update_cards_list(self) -> None:
        """Update the cards list widget."""
        self.cards_list.clear()
        
        for card in self.sequence.cards:
            item = TaskCardWidget(card)
            self.cards_list.addItem(item)
    
    def _update_editor_state(self, enabled: bool) -> None:
        """Enable/disable editor."""
        self.card_name.setEnabled(enabled)
        self.card_prompt.setEnabled(enabled)
        self.wait_before.setEnabled(enabled)
        self.wait_after.setEnabled(enabled)
        self.timeout.setEnabled(enabled)
        self.card_enabled.setEnabled(enabled)
        self.save_card_btn.setEnabled(enabled)
    
    def _load_card_to_editor(self, card: TaskCard) -> None:
        """Load card data to editor."""
        self.card_name.setText(card.name)
        self.card_prompt.setPlainText(card.prompt)
        self.wait_before.setValue(card.wait_before)
        self.wait_after.setValue(card.wait_after)
        self.timeout.setValue(card.timeout)
        self.card_enabled.setChecked(card.enabled)
    
    def _save_editor_to_card(self, card: TaskCard) -> None:
        """Save editor data to card."""
        card.name = self.card_name.text().strip()
        card.prompt = self.card_prompt.toPlainText()
        card.wait_before = self.wait_before.value()
        card.wait_after = self.wait_after.value()
        card.timeout = self.timeout.value()
        card.enabled = self.card_enabled.isChecked()
    
    def _on_card_selected(self, current: QListWidgetItem, previous: QListWidgetItem) -> None:
        """Handle card selection change."""
        if current and isinstance(current, TaskCardWidget):
            self._current_card = current.card
            self._load_card_to_editor(current.card)
            self._update_editor_state(True)
        else:
            self._current_card = None
            self._update_editor_state(False)
    
    def _on_sequence_name_changed(self, text: str) -> None:
        """Handle sequence name change."""
        self.sequence.name = text
        self.sequence_changed.emit()
    
    def _on_default_interval_changed(self, value: int) -> None:
        """Handle default interval change."""
        self.sequence.default_interval = value
    
    def _add_card(self) -> None:
        """Add a new card."""
        card = TaskCard(
            name=f"Задача {len(self.sequence.cards) + 1}",
            wait_after=self.default_interval.value(),
        )
        self.sequence.add_card(card)
        
        item = TaskCardWidget(card)
        self.cards_list.addItem(item)
        self.cards_list.setCurrentItem(item)
        
        self.sequence_changed.emit()
    
    def _remove_card(self) -> None:
        """Remove selected card."""
        current = self.cards_list.currentItem()
        if current and isinstance(current, TaskCardWidget):
            self.sequence.remove_card(current.card.id)
            self.cards_list.takeItem(self.cards_list.row(current))
            self.sequence_changed.emit()
    
    def _move_card_up(self) -> None:
        """Move selected card up."""
        current = self.cards_list.currentItem()
        if current and isinstance(current, TaskCardWidget):
            if self.sequence.move_card(current.card.id, -1):
                self._update_cards_list()
                # Reselect
                for i in range(self.cards_list.count()):
                    item = self.cards_list.item(i)
                    if isinstance(item, TaskCardWidget) and item.card.id == current.card.id:
                        self.cards_list.setCurrentItem(item)
                        break
    
    def _move_card_down(self) -> None:
        """Move selected card down."""
        current = self.cards_list.currentItem()
        if current and isinstance(current, TaskCardWidget):
            if self.sequence.move_card(current.card.id, 1):
                self._update_cards_list()
                # Reselect
                for i in range(self.cards_list.count()):
                    item = self.cards_list.item(i)
                    if isinstance(item, TaskCardWidget) and item.card.id == current.card.id:
                        self.cards_list.setCurrentItem(item)
                        break
    
    def _save_current_card(self) -> None:
        """Save current card from editor."""
        if self._current_card:
            self._save_editor_to_card(self._current_card)
            
            # Update list item
            current = self.cards_list.currentItem()
            if isinstance(current, TaskCardWidget):
                current.update_from_card()
            
            self.sequence_changed.emit()
    
    def _import_tasks(self) -> None:
        """Import tasks from file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт задач",
            str(get_tasks_dir()),
            "JSON файлы (*.json);;YAML файлы (*.yaml *.yml);;Все файлы (*)"
        )
        
        if file_path:
            try:
                self.sequence = self.loader.load_from_file(file_path)
                self.sequence_name.setText(self.sequence.name)
                self.default_interval.setValue(self.sequence.default_interval)
                self._update_cards_list()
                self.sequence_changed.emit()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить: {e}")
    
    def _export_tasks(self) -> None:
        """Export tasks to file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт задач",
            str(get_tasks_dir() / f"{self.sequence.name}.json"),
            "JSON файлы (*.json);;YAML файлы (*.yaml)"
        )
        
        if file_path:
            try:
                fmt = "yaml" if file_path.endswith((".yaml", ".yml")) else "json"
                self.loader.save_to_file(self.sequence, file_path, fmt)
                QMessageBox.information(self, "Успех", "Задачи экспортированы")
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить: {e}")
    
    def _load_prompts(self) -> None:
        """Load prompts from text file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Загрузить промпты",
            str(get_tasks_dir()),
            "Текстовые файлы (*.txt);;Все файлы (*)"
        )
        
        if file_path:
            try:
                self.sequence = self.loader.load_from_file(file_path)
                self.sequence_name.setText(self.sequence.name)
                self._update_cards_list()
                self.sequence_changed.emit()
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить: {e}")
    
    def get_sequence(self) -> TaskSequence:
        """Get current task sequence."""
        return self.sequence
    
    def load_from_config(self) -> None:
        """Load from config."""
        self.default_interval.setValue(self.config.get("defaults.interval_after", 15))
    
    def save_to_config(self) -> None:
        """Save to config."""
        self.config.set("defaults.interval_after", self.default_interval.value())
