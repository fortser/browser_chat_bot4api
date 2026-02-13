"""
ChatFlow Card Editor - Редактор карточек запросов
Автономный инструмент для создания последовательностей задач
Версия 1.4 - дублирование, история файлов, валидация
"""

import sys
import json
import uuid
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QLineEdit, QPushButton, QSpinBox, QScrollArea,
    QFrame, QFileDialog, QMessageBox, QGroupBox, QMenu, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QSettings
from PyQt6.QtGui import QFont, QKeySequence, QShortcut, QAction


class ExpandedEditorDialog(QDialog):
    """Диалоговое окно для развёрнутого редактирования запроса."""
    
    def __init__(self, card_name: str, card_index: int, prompt_text: str, parent=None):
        super().__init__(parent)
        self.prompt_text = prompt_text
        self.card_name = card_name
        self.card_index = card_index
        self._setup_ui()
        self._load_geometry()
    
    def _setup_ui(self):
        """Настройка интерфейса диалога."""
        self.setWindowTitle(f"Редактирование запроса #{self.card_index + 1}")
        self.setMinimumSize(800, 600)
        
        # Модальное окно
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Заголовок с информацией о карточке
        header_layout = QHBoxLayout()
        
        title_label = QLabel(f"Карточка #{self.card_index + 1}")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #6c5ce7;")
        header_layout.addWidget(title_label)
        
        if self.card_name:
            name_label = QLabel(f"— {self.card_name}")
            name_label.setStyleSheet("color: #6c757d; font-size: 14px;")
            header_layout.addWidget(name_label)
        
        header_layout.addStretch()
        
        # Счётчик символов и строк
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: #6c757d; font-size: 12px;")
        header_layout.addWidget(self.stats_label)
        
        layout.addLayout(header_layout)
        
        # Основное текстовое поле
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.prompt_text)
        self.text_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ced4da;
                border-radius: 8px;
                padding: 12px;
                background: white;
                font-size: 14px;
                font-family: 'Consolas', 'Monaco', monospace;
                line-height: 1.5;
            }
            QTextEdit:focus {
                border-color: #6c5ce7;
                border-width: 2px;
            }
        """)
        self.text_edit.setTabStopDistance(40)
        self.text_edit.textChanged.connect(self._update_stats)
        layout.addWidget(self.text_edit, 1)
        
        # Панель инструментов
        toolbar_layout = QHBoxLayout()
        
        # Кнопка очистки
        clear_btn = QPushButton("🗑 Очистить")
        clear_btn.setStyleSheet("""
            QPushButton {
                background: #ffebee;
                border: 1px solid #ef9a9a;
                border-radius: 4px;
                padding: 6px 12px;
                color: #c62828;
            }
            QPushButton:hover {
                background: #ffcdd2;
            }
        """)
        clear_btn.clicked.connect(self._clear_text)
        toolbar_layout.addWidget(clear_btn)
        
        # Кнопка форматирования (удаление лишних пробелов)
        format_btn = QPushButton("✨ Убрать лишние пробелы")
        format_btn.setStyleSheet("""
            QPushButton {
                background: #e3f2fd;
                border: 1px solid #90caf9;
                border-radius: 4px;
                padding: 6px 12px;
                color: #1565c0;
            }
            QPushButton:hover {
                background: #bbdefb;
            }
        """)
        format_btn.clicked.connect(self._format_text)
        toolbar_layout.addWidget(format_btn)
        
        toolbar_layout.addStretch()
        
        # Подсказка
        hint_label = QLabel("Ctrl+Enter — сохранить и закрыть | Esc — отмена")
        hint_label.setStyleSheet("color: #adb5bd; font-size: 11px;")
        toolbar_layout.addWidget(hint_label)
        
        layout.addLayout(toolbar_layout)
        
        # Кнопки диалога
        self.save_btn = QPushButton("💾 Сохранить")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #6c5ce7;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
                font-weight: bold;
                color: white;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #5b4cdb;
            }
        """)
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background: #e9ecef;
                border: 1px solid #ced4da;
                border-radius: 6px;
                padding: 10px 24px;
                color: #495057;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #dee2e6;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.save_btn)
        layout.addLayout(button_layout)
        
        # Горячие клавиши
        save_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        save_shortcut.activated.connect(self.accept)
        
        save_shortcut2 = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut2.activated.connect(self.accept)
        
        # Обновляем статистику
        self._update_stats()
        
        # Фокус на текстовое поле
        self.text_edit.setFocus()
        # Курсор в конец текста
        cursor = self.text_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.text_edit.setTextCursor(cursor)
    
    def _load_geometry(self):
        """Загрузить сохранённую геометрию окна."""
        settings = QSettings("ChatFlow", "CardEditor")
        geometry = settings.value("expanded_editor_geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(1000, 700)
    
    def _save_geometry(self):
        """Сохранить геометрию окна."""
        settings = QSettings("ChatFlow", "CardEditor")
        settings.setValue("expanded_editor_geometry", self.saveGeometry())
    
    def closeEvent(self, event):
        """Сохранить геометрию при закрытии."""
        self._save_geometry()
        super().closeEvent(event)
    
    def accept(self):
        """Сохранить геометрию при подтверждении."""
        self._save_geometry()
        super().accept()
    
    def reject(self):
        """Сохранить геометрию при отмене."""
        self._save_geometry()
        super().reject()
    
    def _update_stats(self):
        """Обновить статистику текста."""
        text = self.text_edit.toPlainText()
        chars = len(text)
        lines = text.count('\n') + 1 if text else 0
        words = len(text.split()) if text.strip() else 0
        self.stats_label.setText(f"{chars} символов | {words} слов | {lines} строк")
    
    def _clear_text(self):
        """Очистить текст с подтверждением."""
        if self.text_edit.toPlainText().strip():
            reply = QMessageBox.question(
                self, "Подтверждение",
                "Очистить весь текст запроса?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.text_edit.clear()
    
    def _format_text(self):
        """Убрать лишние пробелы и пустые строки."""
        text = self.text_edit.toPlainText()
        
        # Убираем trailing пробелы в каждой строке
        lines = [line.rstrip() for line in text.split('\n')]
        
        # Убираем множественные пустые строки (оставляем максимум одну)
        result_lines = []
        prev_empty = False
        for line in lines:
            is_empty = not line.strip()
            if is_empty and prev_empty:
                continue
            result_lines.append(line)
            prev_empty = is_empty
        
        # Убираем пустые строки в начале и конце
        while result_lines and not result_lines[0].strip():
            result_lines.pop(0)
        while result_lines and not result_lines[-1].strip():
            result_lines.pop()
        
        formatted = '\n'.join(result_lines)
        
        if formatted != text:
            self.text_edit.setPlainText(formatted)
    
    def get_text(self) -> str:
        """Получить отредактированный текст."""
        return self.text_edit.toPlainText()


class PromptCard(QFrame):
    """Виджет одной карточки с запросом."""
    
    deleted = pyqtSignal(object)
    moved_up = pyqtSignal(object)
    moved_down = pyqtSignal(object)
    duplicated = pyqtSignal(object)
    focused = pyqtSignal(object)
    
    def __init__(self, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self._setup_ui()
    
    def _setup_ui(self):
        """Настройка интерфейса карточки."""
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setStyleSheet("""
            PromptCard {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin: 4px;
            }
            PromptCard:hover {
                border-color: #6c5ce7;
            }
            PromptCard:focus {
                border: 2px solid #6c5ce7;
                background-color: #f0f0ff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # Заголовок с номером и кнопками
        header = QHBoxLayout()
        
        self.number_label = QLabel(f"#{self.index + 1}")
        self.number_label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.number_label.setStyleSheet("color: #6c5ce7;")
        header.addWidget(self.number_label)
        
        # Название карточки
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(f"Название запроса {self.index + 1}")
        self.name_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 4px 8px;
                background: white;
            }
            QLineEdit:focus {
                border-color: #6c5ce7;
            }
        """)
        header.addWidget(self.name_edit, 1)
        
        # Кнопки управления
        btn_style = """
            QPushButton {
                background: #e9ecef;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background: #dee2e6;
            }
            QPushButton:pressed {
                background: #ced4da;
            }
        """
        
        # Кнопка развернуть
        self.expand_btn = QPushButton("⛶")
        self.expand_btn.setFixedWidth(30)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                background: #e8f5e9;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                color: #2e7d32;
            }
            QPushButton:hover {
                background: #c8e6c9;
            }
            QPushButton:pressed {
                background: #a5d6a7;
            }
        """)
        self.expand_btn.setToolTip("Развернуть редактор (Ctrl+E)")
        self.expand_btn.clicked.connect(self._open_expanded_editor)
        header.addWidget(self.expand_btn)
        
        # Кнопка дублирования
        self.duplicate_btn = QPushButton("⧉")
        self.duplicate_btn.setFixedWidth(30)
        self.duplicate_btn.setStyleSheet("""
            QPushButton {
                background: #e3f2fd;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                color: #1565c0;
            }
            QPushButton:hover {
                background: #bbdefb;
            }
            QPushButton:pressed {
                background: #90caf9;
            }
        """)
        self.duplicate_btn.setToolTip("Дублировать карточку (Ctrl+D)")
        self.duplicate_btn.clicked.connect(lambda: self.duplicated.emit(self))
        header.addWidget(self.duplicate_btn)
        
        self.up_btn = QPushButton("▲")
        self.up_btn.setFixedWidth(30)
        self.up_btn.setStyleSheet(btn_style)
        self.up_btn.setToolTip("Переместить вверх")
        self.up_btn.clicked.connect(lambda: self.moved_up.emit(self))
        header.addWidget(self.up_btn)
        
        self.down_btn = QPushButton("▼")
        self.down_btn.setFixedWidth(30)
        self.down_btn.setStyleSheet(btn_style)
        self.down_btn.setToolTip("Переместить вниз")
        self.down_btn.clicked.connect(lambda: self.moved_down.emit(self))
        header.addWidget(self.down_btn)
        
        self.delete_btn = QPushButton("✕")
        self.delete_btn.setFixedWidth(30)
        self.delete_btn.setStyleSheet("""
            QPushButton {
                background: #fee2e2;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14px;
                color: #dc2626;
            }
            QPushButton:hover {
                background: #fecaca;
            }
        """)
        self.delete_btn.setToolTip("Удалить карточку")
        self.delete_btn.clicked.connect(lambda: self.deleted.emit(self))
        header.addWidget(self.delete_btn)
        
        layout.addLayout(header)
        
        # Поле для текста запроса
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setPlaceholderText("Введите текст запроса здесь...\n\nПоддерживается многострочный текст.\nДважды кликните или нажмите ⛶ для развёрнутого редактирования.")
        self.prompt_edit.setMinimumHeight(100)
        self.prompt_edit.setMaximumHeight(200)
        self.prompt_edit.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 8px;
                background: white;
                font-size: 13px;
            }
            QTextEdit:focus {
                border-color: #6c5ce7;
            }
        """)
        # Устанавливаем event filter для двойного клика
        self.prompt_edit.installEventFilter(self)
        layout.addWidget(self.prompt_edit)
        
        # Настройки карточки
        settings_layout = QHBoxLayout()
        settings_layout.setSpacing(16)
        
        # Пауза после
        settings_layout.addWidget(QLabel("Пауза после:"))
        self.wait_after = QSpinBox()
        self.wait_after.setRange(0, 300)
        self.wait_after.setValue(15)
        self.wait_after.setSuffix(" сек")
        self.wait_after.setStyleSheet("QSpinBox { padding: 2px 4px; }")
        settings_layout.addWidget(self.wait_after)
        
        # Таймаут
        settings_layout.addWidget(QLabel("Таймаут:"))
        self.timeout = QSpinBox()
        self.timeout.setRange(10, 600)
        self.timeout.setValue(120)
        self.timeout.setSuffix(" сек")
        self.timeout.setStyleSheet("QSpinBox { padding: 2px 4px; }")
        settings_layout.addWidget(self.timeout)
        
        settings_layout.addStretch()
        
        # Счётчик символов
        self.char_count = QLabel("0 символов")
        self.char_count.setStyleSheet("color: #6c757d; font-size: 11px;")
        settings_layout.addWidget(self.char_count)
        
        layout.addLayout(settings_layout)
        
        # Обновление счётчика
        self.prompt_edit.textChanged.connect(self._update_char_count)
    
    def eventFilter(self, obj, event) -> bool:
        """Обработка событий для prompt_edit."""
        if obj == self.prompt_edit and event.type() == QEvent.Type.MouseButtonDblClick:
            self._open_expanded_editor()
            return True
        return super().eventFilter(obj, event)
    
    def focusInEvent(self, event):
        """Обработка получения фокуса."""
        super().focusInEvent(event)
        self.focused.emit(self)
    
    def keyPressEvent(self, event):
        """Обработка нажатий клавиш."""
        if event.key() == Qt.Key.Key_Return and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._open_expanded_editor()
        elif event.key() == Qt.Key.Key_E and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self._open_expanded_editor()
        elif event.key() == Qt.Key.Key_D and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.duplicated.emit(self)
        else:
            super().keyPressEvent(event)
    
    def _open_expanded_editor(self):
        """Открыть развёрнутый редактор."""
        dialog = ExpandedEditorDialog(
            card_name=self.name_edit.text(),
            card_index=self.index,
            prompt_text=self.prompt_edit.toPlainText(),
            parent=self.window()
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.prompt_edit.setPlainText(dialog.get_text())
    
    def _update_char_count(self):
        """Обновить счётчик символов."""
        count = len(self.prompt_edit.toPlainText())
        self.char_count.setText(f"{count} символов")
    
    def update_index(self, index: int):
        """Обновить номер карточки."""
        self.index = index
        self.number_label.setText(f"#{index + 1}")
        if not self.name_edit.text():
            self.name_edit.setPlaceholderText(f"Название запроса {index + 1}")
    
    def get_data(self) -> dict:
        """Получить данные карточки."""
        name = self.name_edit.text().strip()
        if not name:
            name = f"Запрос {self.index + 1}"
        
        return {
            "id": f"card_{uuid.uuid4().hex[:8]}",
            "name": name,
            "prompt": self.prompt_edit.toPlainText(),
            "wait_before": 0,
            "wait_after": self.wait_after.value(),
            "timeout": self.timeout.value(),
            "enabled": True
        }
    
    def set_data(self, data: dict):
        """Установить данные карточки."""
        self.name_edit.setText(data.get("name", ""))
        self.prompt_edit.setPlainText(data.get("prompt", ""))
        self.wait_after.setValue(data.get("wait_after", 15))
        self.timeout.setValue(data.get("timeout", 120))


class CardEditor(QMainWindow):
    """Главное окно редактора карточек."""
    
    # Максимальное количество карточек
    MAX_CARDS = 50
    # Максимальное количество файлов в истории
    MAX_RECENT_FILES = 10
    
    def __init__(self):
        super().__init__()
        self.cards: List[PromptCard] = []
        self.current_file: Optional[Path] = None
        self._has_unsaved_changes = False
        self._current_card_index = 0
        self._recent_files: List[str] = []
        
        # Путь по умолчанию для экспорта
        self.default_export_path = Path("T:/test_python/bro_bot/chatflow-automator/data/tasks")
        
        self._load_settings()
        self._setup_ui()
        self._setup_shortcuts()
        
        # Добавляем одну карточку по умолчанию
        self._add_card()
        self._has_unsaved_changes = False  # Сбрасываем флаг после начальной карточки
    
    def _setup_ui(self):
        """Настройка интерфейса."""
        self.setWindowTitle("ChatFlow Card Editor v1.4")
        self.setMinimumSize(700, 600)
        
        # Стиль окна
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QLabel {
                font-size: 13px;
            }
            QPushButton {
                font-size: 13px;
            }
        """)
        
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)
        
        # === Заголовок и настройки последовательности ===
        header_group = QGroupBox("Настройки последовательности")
        header_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        header_layout = QVBoxLayout(header_group)
        
        # Название последовательности
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Название:"))
        self.sequence_name = QLineEdit()
        self.sequence_name.setPlaceholderText("Моя последовательность запросов")
        self.sequence_name.setText("Новая последовательность")
        self.sequence_name.textChanged.connect(self._mark_unsaved)
        name_row.addWidget(self.sequence_name, 1)
        header_layout.addLayout(name_row)
        
        # Настройки
        settings_row = QHBoxLayout()
        
        settings_row.addWidget(QLabel("Интервал по умолчанию:"))
        self.default_interval = QSpinBox()
        self.default_interval.setRange(0, 300)
        self.default_interval.setValue(15)
        self.default_interval.setSuffix(" сек")
        self.default_interval.valueChanged.connect(self._mark_unsaved)
        settings_row.addWidget(self.default_interval)
        
        settings_row.addSpacing(20)
        
        # Счётчик карточек (только отображение)
        self.cards_count_label = QLabel("Карточек: 0")
        self.cards_count_label.setStyleSheet("color: #6c757d;")
        settings_row.addWidget(self.cards_count_label)
        
        settings_row.addStretch()
        header_layout.addLayout(settings_row)
        
        main_layout.addWidget(header_group)
        
        # === Область с карточками (прокручиваемая) ===
        cards_group = QGroupBox("Запросы (Alt+↑↓ — навигация, Ctrl+D — дублировать, Ctrl+E — развернуть)")
        cards_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """)
        cards_layout = QVBoxLayout(cards_group)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()
        
        self.scroll.setWidget(self.cards_container)
        cards_layout.addWidget(self.scroll)
        
        main_layout.addWidget(cards_group, 1)
        
        # === Кнопки управления ===
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)
        
        # Кнопка добавления
        self.add_btn = QPushButton("➕ Добавить запрос")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background: #e8f5e9;
                border: 1px solid #a5d6a7;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                color: #2e7d32;
            }
            QPushButton:hover {
                background: #c8e6c9;
            }
        """)
        self.add_btn.clicked.connect(self._add_card)
        buttons_layout.addWidget(self.add_btn)
        
        # Кнопка очистки
        self.clear_btn = QPushButton("🗑 Очистить всё")
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background: #ffebee;
                border: 1px solid #ef9a9a;
                border-radius: 6px;
                padding: 8px 16px;
                color: #c62828;
            }
            QPushButton:hover {
                background: #ffcdd2;
            }
        """)
        self.clear_btn.clicked.connect(self._clear_all)
        buttons_layout.addWidget(self.clear_btn)
        
        buttons_layout.addStretch()
        
        # Кнопка вставки из буфера обмена
        self.paste_btn = QPushButton("📋 Вставить из буфера")
        self.paste_btn.setStyleSheet("""
            QPushButton {
                background: #e3f2fd;
                border: 1px solid #90caf9;
                border-radius: 6px;
                padding: 8px 16px;
                color: #1565c0;
            }
            QPushButton:hover {
                background: #bbdefb;
            }
        """)
        self.paste_btn.setToolTip("Вставить запросы из буфера обмена (Ctrl+Shift+V)")
        self.paste_btn.clicked.connect(self._import_from_clipboard)
        buttons_layout.addWidget(self.paste_btn)
        
        # Кнопка импорта с меню
        self.import_btn = QPushButton("📂 Импорт ▼")
        self.import_btn.setStyleSheet("""
            QPushButton {
                background: #fff3e0;
                border: 1px solid #ffcc80;
                border-radius: 6px;
                padding: 8px 16px;
                color: #e65100;
            }
            QPushButton:hover {
                background: #ffe0b2;
            }
        """)
        
        # Создаём меню для кнопки импорта
        self.import_menu = QMenu(self)
        self.import_menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #e3f2fd;
            }
            QMenu::separator {
                height: 1px;
                background: #dee2e6;
                margin: 4px 8px;
            }
        """)
        
        action_open = QAction("📁 Открыть файл (заменить всё)", self)
        action_open.triggered.connect(self._import_file_replace)
        self.import_menu.addAction(action_open)
        
        action_append = QAction("➕ Добавить из файла (в конец)", self)
        action_append.triggered.connect(self._import_file_append)
        self.import_menu.addAction(action_append)
        
        self.import_menu.addSeparator()
        
        action_append_separated = QAction("📝 Добавить из файла (разделитель — пустая строка)", self)
        action_append_separated.triggered.connect(self._import_file_append_separated)
        self.import_menu.addAction(action_append_separated)
        
        # Подменю недавних файлов
        self.import_menu.addSeparator()
        self.recent_menu = self.import_menu.addMenu("🕒 Недавние файлы")
        self._update_recent_files_menu()
        
        self.import_btn.setMenu(self.import_menu)
        buttons_layout.addWidget(self.import_btn)
        
        # Кнопка экспорта
        self.export_btn = QPushButton("💾 Экспорт")
        self.export_btn.setStyleSheet("""
            QPushButton {
                background: #6c5ce7;
                border: none;
                border-radius: 6px;
                padding: 8px 24px;
                font-weight: bold;
                color: white;
            }
            QPushButton:hover {
                background: #5b4cdb;
            }
            QPushButton:pressed {
                background: #4a3fc9;
            }
        """)
        self.export_btn.clicked.connect(self._export_file)
        buttons_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # Статусбар
        self.statusBar().showMessage("Готов к работе | Alt+↑↓ — навигация | Ctrl+D — дублировать | Двойной клик — развернуть")
        self.statusBar().setStyleSheet("color: #6c757d;")
    
    def _setup_shortcuts(self):
        """Настройка горячих клавиш."""
        # Ctrl+S - сохранить
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self)
        save_shortcut.activated.connect(self._export_file)
        
        # Ctrl+O - открыть
        open_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        open_shortcut.activated.connect(self._import_file_replace)
        
        # Ctrl+N - новая карточка
        new_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        new_shortcut.activated.connect(self._add_card)
        
        # Ctrl+Shift+O - добавить из файла
        append_shortcut = QShortcut(QKeySequence("Ctrl+Shift+O"), self)
        append_shortcut.activated.connect(self._import_file_append_separated)
        
        # Ctrl+Shift+V - вставить из буфера
        paste_shortcut = QShortcut(QKeySequence("Ctrl+Shift+V"), self)
        paste_shortcut.activated.connect(self._import_from_clipboard)
        
        # Ctrl+D - дублировать текущую карточку
        duplicate_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        duplicate_shortcut.activated.connect(self._duplicate_current_card)
        
        # Навигация между карточками
        up_shortcut = QShortcut(QKeySequence("Alt+Up"), self)
        up_shortcut.activated.connect(self._focus_previous_card)
        
        down_shortcut = QShortcut(QKeySequence("Alt+Down"), self)
        down_shortcut.activated.connect(self._focus_next_card)
        
        # Home/End для первой/последней карточки
        home_shortcut = QShortcut(QKeySequence("Alt+Home"), self)
        home_shortcut.activated.connect(self._focus_first_card)
        
        end_shortcut = QShortcut(QKeySequence("Alt+End"), self)
        end_shortcut.activated.connect(self._focus_last_card)
    
    def _load_settings(self):
        """Загрузить настройки приложения."""
        settings = QSettings("ChatFlow", "CardEditor")
        
        # Геометрия главного окна
        geometry = settings.value("main_window_geometry")
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.resize(800, 700)
        
        # Состояние окна
        state = settings.value("main_window_state")
        if state:
            self.restoreState(state)
        
        # История файлов
        self._recent_files = settings.value("recent_files", []) or []
        # Очищаем несуществующие файлы
        self._recent_files = [f for f in self._recent_files if Path(f).exists()]
    
    def _save_settings(self):
        """Сохранить настройки приложения."""
        settings = QSettings("ChatFlow", "CardEditor")
        settings.setValue("main_window_geometry", self.saveGeometry())
        settings.setValue("main_window_state", self.saveState())
        settings.setValue("recent_files", self._recent_files)
    
    def _add_to_recent_files(self, file_path: str):
        """Добавить файл в историю."""
        # Нормализуем путь
        file_path = str(Path(file_path).resolve())
        
        # Удаляем если уже есть
        if file_path in self._recent_files:
            self._recent_files.remove(file_path)
        
        # Добавляем в начало
        self._recent_files.insert(0, file_path)
        
        # Ограничиваем размер
        self._recent_files = self._recent_files[:self.MAX_RECENT_FILES]
        
        # Обновляем меню
        self._update_recent_files_menu()
        
        # Сохраняем
        self._save_settings()
    
    def _update_recent_files_menu(self):
        """Обновить меню недавних файлов."""
        self.recent_menu.clear()
        
        if not self._recent_files:
            action = QAction("(пусто)", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
            return
        
        for i, file_path in enumerate(self._recent_files):
            path = Path(file_path)
            # Показываем имя файла и папку
            display_name = f"{i+1}. {path.name}"
            if len(str(path.parent)) > 30:
                parent_str = "..." + str(path.parent)[-27:]
            else:
                parent_str = str(path.parent)
            
            action = QAction(display_name, self)
            action.setToolTip(str(path))
            action.setData(file_path)
            action.triggered.connect(lambda checked, p=file_path: self._open_recent_file(p))
            self.recent_menu.addAction(action)
        
        # Разделитель и очистка
        self.recent_menu.addSeparator()
        clear_action = QAction("🗑 Очистить историю", self)
        clear_action.triggered.connect(self._clear_recent_files)
        self.recent_menu.addAction(clear_action)
    
    def _open_recent_file(self, file_path: str):
        """Открыть файл из истории."""
        if not Path(file_path).exists():
            QMessageBox.warning(
                self, "Файл не найден",
                f"Файл больше не существует:\n{file_path}"
            )
            # Удаляем из истории
            if file_path in self._recent_files:
                self._recent_files.remove(file_path)
                self._update_recent_files_menu()
                self._save_settings()
            return
        
        # Проверяем несохранённые изменения
        if self._has_unsaved_changes:
            reply = QMessageBox.question(
                self, "Несохранённые изменения",
                "У вас есть несохранённые изменения. Продолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self._load_file(file_path)
    
    def _clear_recent_files(self):
        """Очистить историю файлов."""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Очистить историю недавних файлов?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._recent_files.clear()
            self._update_recent_files_menu()
            self._save_settings()
            self.statusBar().showMessage("История файлов очищена")
    
    def closeEvent(self, event):
        """Обработка закрытия окна."""
        if self._has_unsaved_changes:
            reply = QMessageBox.question(
                self, "Несохранённые изменения",
                "У вас есть несохранённые изменения.\n\n"
                "Сохранить перед выходом?",
                QMessageBox.StandardButton.Save | 
                QMessageBox.StandardButton.Discard | 
                QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self._export_file()
                if self._has_unsaved_changes:  # Если сохранение отменено
                    event.ignore()
                    return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        
        self._save_settings()
        event.accept()
    
    def _mark_unsaved(self):
        """Отметить наличие несохранённых изменений."""
        self._has_unsaved_changes = True
        self._update_window_title()
    
    def _mark_saved(self):
        """Отметить, что изменения сохранены."""
        self._has_unsaved_changes = False
        self._update_window_title()
    
    def _update_window_title(self):
        """Обновить заголовок окна."""
        title = "ChatFlow Card Editor v1.4"
        if self.current_file:
            title += f" — {self.current_file.name}"
        if self._has_unsaved_changes:
            title += " *"
        self.setWindowTitle(title)
    
    def _focus_card(self, index: int):
        """Установить фокус на карточку по индексу."""
        if 0 <= index < len(self.cards):
            self._current_card_index = index
            card = self.cards[index]
            card.setFocus()
            # Прокрутить к карточке
            self.scroll.ensureWidgetVisible(card)
            self.statusBar().showMessage(f"Карточка #{index + 1} из {len(self.cards)}")
    
    def _focus_previous_card(self):
        """Переключиться на предыдущую карточку."""
        if self._current_card_index > 0:
            self._focus_card(self._current_card_index - 1)
    
    def _focus_next_card(self):
        """Переключиться на следующую карточку."""
        if self._current_card_index < len(self.cards) - 1:
            self._focus_card(self._current_card_index + 1)
    
    def _focus_first_card(self):
        """Переключиться на первую карточку."""
        self._focus_card(0)
    
    def _focus_last_card(self):
        """Переключиться на последнюю карточку."""
        self._focus_card(len(self.cards) - 1)
    
    def _on_card_focused(self, card: PromptCard):
        """Обработка фокуса на карточке."""
        self._current_card_index = self.cards.index(card)
    
    def _update_cards_count(self):
        """Обновить счётчик карточек."""
        self.cards_count_label.setText(f"Карточек: {len(self.cards)}")
    
    def _add_card(self, prompt_text: Optional[str] = None) -> Optional[PromptCard]:
        """Добавить новую карточку."""
        if len(self.cards) >= self.MAX_CARDS:
            QMessageBox.warning(
                self, "Ограничение", 
                f"Максимум {self.MAX_CARDS} запросов в последовательности"
            )
            return None
        
        card = PromptCard(len(self.cards))
        card.wait_after.setValue(self.default_interval.value())
        card.deleted.connect(self._delete_card)
        card.moved_up.connect(self._move_card_up)
        card.moved_down.connect(self._move_card_down)
        card.duplicated.connect(self._duplicate_card)
        card.focused.connect(self._on_card_focused)
        
        # Отслеживание изменений
        card.name_edit.textChanged.connect(self._mark_unsaved)
        card.prompt_edit.textChanged.connect(self._mark_unsaved)
        card.wait_after.valueChanged.connect(self._mark_unsaved)
        card.timeout.valueChanged.connect(self._mark_unsaved)
        
        if prompt_text:
            card.prompt_edit.setPlainText(prompt_text)
        
        self.cards.append(card)
        self.cards_layout.insertWidget(self.cards_layout.count() - 1, card)
        
        self._update_card_buttons()
        self._update_cards_count()
        self._mark_unsaved()
        
        return card
    
    def _duplicate_card(self, card: PromptCard):
        """Дублировать указанную карточку."""
        if len(self.cards) >= self.MAX_CARDS:
            QMessageBox.warning(
                self, "Ограничение", 
                f"Максимум {self.MAX_CARDS} запросов в последовательности"
            )
            return
        
        # Получаем данные карточки
        data = card.get_data()
        
        # Создаём новую карточку
        new_card = PromptCard(card.index + 1)
        new_card.wait_after.setValue(self.default_interval.value())
        new_card.deleted.connect(self._delete_card)
        new_card.moved_up.connect(self._move_card_up)
        new_card.moved_down.connect(self._move_card_down)
        new_card.duplicated.connect(self._duplicate_card)
        new_card.focused.connect(self._on_card_focused)
        
        # Отслеживание изменений
        new_card.name_edit.textChanged.connect(self._mark_unsaved)
        new_card.prompt_edit.textChanged.connect(self._mark_unsaved)
        new_card.wait_after.valueChanged.connect(self._mark_unsaved)
        new_card.timeout.valueChanged.connect(self._mark_unsaved)
        
        # Копируем данные
        new_card.name_edit.setText(data.get("name", "") + " (копия)")
        new_card.prompt_edit.setPlainText(data.get("prompt", ""))
        new_card.wait_after.setValue(data.get("wait_after", 15))
        new_card.timeout.setValue(data.get("timeout", 120))
        
        # Вставляем после текущей карточки
        insert_index = card.index + 1
        self.cards.insert(insert_index, new_card)
        self.cards_layout.insertWidget(insert_index, new_card)
        
        # Обновляем индексы всех карточек
        for i, c in enumerate(self.cards):
            c.update_index(i)
        
        self._update_card_buttons()
        self._update_cards_count()
        self._mark_unsaved()
        
        # Фокус на новую карточку
        self._focus_card(insert_index)
        
        self.statusBar().showMessage(f"Карточка #{card.index + 1} дублирована → #{insert_index + 1}")
    
    def _duplicate_current_card(self):
        """Дублировать текущую (сфокусированную) карточку."""
        if self.cards and 0 <= self._current_card_index < len(self.cards):
            self._duplicate_card(self.cards[self._current_card_index])
    
    def _delete_card(self, card: PromptCard):
        """Удалить карточку."""
        if len(self.cards) <= 1:
            QMessageBox.warning(self, "Ошибка", "Должен остаться хотя бы один запрос")
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить запрос #{card.index + 1}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.cards.remove(card)
            self.cards_layout.removeWidget(card)
            card.deleteLater()
            
            # Обновляем индексы
            for i, c in enumerate(self.cards):
                c.update_index(i)
            
            self._update_card_buttons()
            self._update_cards_count()
            self._mark_unsaved()
            self.statusBar().showMessage("Запрос удалён")
    
    def _clear_all(self):
        """Очистить все карточки."""
        if len(self.cards) <= 1:
            # Просто очищаем единственную карточку
            self.cards[0].name_edit.clear()
            self.cards[0].prompt_edit.clear()
            self._mark_unsaved()
            return
        
        reply = QMessageBox.question(
            self, "Подтверждение",
            f"Удалить все {len(self.cards)} запросов?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Удаляем все кроме первой
            for card in self.cards[1:]:
                self.cards_layout.removeWidget(card)
                card.deleteLater()
            
            self.cards = self.cards[:1]
            self.cards[0].update_index(0)
            self.cards[0].name_edit.clear()
            self.cards[0].prompt_edit.clear()
            
            self._update_card_buttons()
            self._update_cards_count()
            self._mark_unsaved()
            self.statusBar().showMessage("Все запросы удалены")
    
    def _move_card_up(self, card: PromptCard):
        """Переместить карточку вверх."""
        idx = self.cards.index(card)
        if idx > 0:
            self.cards[idx], self.cards[idx - 1] = self.cards[idx - 1], self.cards[idx]
            self._rebuild_cards_layout()
            self._mark_unsaved()
            self.statusBar().showMessage(f"Запрос перемещён на позицию #{idx}")
    
    def _move_card_down(self, card: PromptCard):
        """Переместить карточку вниз."""
        idx = self.cards.index(card)
        if idx < len(self.cards) - 1:
            self.cards[idx], self.cards[idx + 1] = self.cards[idx + 1], self.cards[idx]
            self._rebuild_cards_layout()
            self._mark_unsaved()
            self.statusBar().showMessage(f"Запрос перемещён на позицию #{idx + 2}")
    
    def _rebuild_cards_layout(self):
        """Перестроить layout карточек."""
        for card in self.cards:
            self.cards_layout.removeWidget(card)
        
        for i, card in enumerate(self.cards):
            card.update_index(i)
            self.cards_layout.insertWidget(i, card)
        
        self._update_card_buttons()
    
    def _update_card_buttons(self):
        """Обновить состояние кнопок перемещения."""
        for i, card in enumerate(self.cards):
            card.up_btn.setEnabled(i > 0)
            card.down_btn.setEnabled(i < len(self.cards) - 1)
    
    def _validate_cards(self) -> tuple[bool, List[int]]:
        """
        Валидация карточек перед экспортом.
        
        Returns:
            (all_valid, empty_card_indices)
        """
        empty_indices = []
        for i, card in enumerate(self.cards):
            if not card.prompt_edit.toPlainText().strip():
                empty_indices.append(i + 1)  # 1-based индексы для отображения
        
        return len(empty_indices) == 0, empty_indices
    
    def _get_sequence_data(self) -> dict:
        """Получить данные последовательности."""
        name = self.sequence_name.text().strip()
        if not name:
            name = "Новая последовательность"
        
        return {
            "version": "1.0",
            "sequence": {
                "id": f"seq_{uuid.uuid4().hex[:8]}",
                "name": name,
                "description": f"Создано в Card Editor {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "default_interval": self.default_interval.value(),
                "cards": [card.get_data() for card in self.cards],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        }
    
    def _export_file(self):
        """Экспортировать в файл."""
        # Валидация карточек
        all_valid, empty_indices = self._validate_cards()
        
        if not all_valid:
            if len(empty_indices) == len(self.cards):
                # Все карточки пустые
                QMessageBox.warning(
                    self, "Ошибка валидации",
                    "Все карточки пустые. Добавьте хотя бы один запрос."
                )
                return
            
            # Есть пустые карточки
            empty_list = ", ".join(f"#{i}" for i in empty_indices[:5])
            if len(empty_indices) > 5:
                empty_list += f" и ещё {len(empty_indices) - 5}"
            
            reply = QMessageBox.warning(
                self, "Предупреждение",
                f"Обнаружены пустые карточки: {empty_list}\n\n"
                f"Пустых карточек: {len(empty_indices)} из {len(self.cards)}\n\n"
                "Продолжить сохранение?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                # Фокус на первую пустую карточку
                self._focus_card(empty_indices[0] - 1)
                return
        
        # Создаём папку если не существует
        try:
            self.default_export_path.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            pass  # Используем текущую директорию если нет доступа
        
        # Предлагаем имя файла
        default_name = self.sequence_name.text().strip()
        if not default_name:
            default_name = "sequence"
        default_name = "".join(c for c in default_name if c.isalnum() or c in " _-").strip()
        default_name = default_name.replace(" ", "_")
        
        start_path = self.default_export_path if self.default_export_path.exists() else Path.cwd()
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить последовательность",
            str(start_path / f"{default_name}.json"),
            "JSON файлы (*.json)"
        )
        
        if file_path:
            try:
                data = self._get_sequence_data()
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                self.current_file = Path(file_path)
                self._add_to_recent_files(file_path)
                self._mark_saved()
                self.statusBar().showMessage(f"Сохранено: {file_path}")
                
                # Формируем сообщение с учётом пустых карточек
                msg = (
                    f"Последовательность сохранена!\n\n"
                    f"Файл: {file_path}\n"
                    f"Запросов: {len(self.cards)}"
                )
                if not all_valid:
                    msg += f"\n⚠️ Пустых карточек: {len(empty_indices)}"
                msg += "\n\nТеперь вы можете загрузить её в ChatFlow Automator."
                
                QMessageBox.information(self, "Успех", msg)
                
            except PermissionError:
                QMessageBox.critical(self, "Ошибка", f"Нет доступа для записи в: {file_path}")
            except OSError as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка записи файла: {e}")
    
    def _load_file(self, file_path: str):
        """Загрузить файл."""
        try:
            path = Path(file_path)
            
            # Очищаем текущие карточки
            for card in self.cards[:]:
                self.cards.remove(card)
                self.cards_layout.removeWidget(card)
                card.deleteLater()
            self.cards = []
            
            if path.suffix.lower() == '.txt':
                self._import_txt_lines(path)
            else:
                self._import_json(path)
            
            # Если нет карточек, добавляем одну
            if not self.cards:
                self._add_card()
            
            self.current_file = path
            self._add_to_recent_files(file_path)
            self._update_card_buttons()
            self._update_cards_count()
            self._mark_saved()
            self.statusBar().showMessage(f"Загружено: {file_path}")
            
        except json.JSONDecodeError as e:
            QMessageBox.critical(self, "Ошибка", f"Некорректный JSON: {e}")
            if not self.cards:
                self._add_card()
        except FileNotFoundError:
            QMessageBox.critical(self, "Ошибка", f"Файл не найден: {file_path}")
            if not self.cards:
                self._add_card()
        except PermissionError:
            QMessageBox.critical(self, "Ошибка", f"Нет доступа к файлу: {file_path}")
            if not self.cards:
                self._add_card()
        except UnicodeDecodeError:
            QMessageBox.critical(self, "Ошибка", f"Ошибка кодировки файла. Используйте UTF-8.")
            if not self.cards:
                self._add_card()
    
    def _import_file_replace(self):
        """Импортировать из файла (заменить всё)."""
        if self._has_unsaved_changes:
            reply = QMessageBox.question(
                self, "Несохранённые изменения",
                "У вас есть несохранённые изменения. Продолжить?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        start_path = self.default_export_path if self.default_export_path.exists() else Path.cwd()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Открыть последовательность",
            str(start_path),
            "JSON файлы (*.json);;Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        
        if file_path:
            self._load_file(file_path)
    
    def _import_file_append(self):
        """Импортировать из файла (добавить в конец, каждая строка — запрос)."""
        start_path = self.default_export_path if self.default_export_path.exists() else Path.cwd()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Добавить запросы из файла",
            str(start_path),
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        
        if file_path:
            try:
                path = Path(file_path)
                added = self._import_txt_lines(path, append=True)
                
                self._add_to_recent_files(file_path)
                self._update_card_buttons()
                self._update_cards_count()
                self.statusBar().showMessage(f"Добавлено {added} запросов из {path.name}")
                
                QMessageBox.information(
                    self, "Импорт завершён",
                    f"Добавлено запросов: {added}\n"
                    f"Всего карточек: {len(self.cards)}"
                )
                
            except FileNotFoundError:
                QMessageBox.critical(self, "Ошибка", f"Файл не найден: {file_path}")
            except PermissionError:
                QMessageBox.critical(self, "Ошибка", f"Нет доступа к файлу: {file_path}")
            except UnicodeDecodeError:
                QMessageBox.critical(self, "Ошибка", f"Ошибка кодировки файла. Используйте UTF-8.")
    
    def _import_file_append_separated(self):
        """Импортировать из файла (добавить в конец, разделитель — пустая строка)."""
        start_path = self.default_export_path if self.default_export_path.exists() else Path.cwd()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Добавить запросы из файла (разделитель — пустая строка)",
            str(start_path),
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        
        if file_path:
            try:
                path = Path(file_path)
                content = path.read_text(encoding='utf-8')
                prompts = self._parse_separated_prompts(content)
                added = self._add_prompts(prompts)
                
                self._add_to_recent_files(file_path)
                self._update_card_buttons()
                self._update_cards_count()
                self.statusBar().showMessage(f"Добавлено {added} запросов из {path.name}")
                
                QMessageBox.information(
                    self, "Импорт завершён",
                    f"Добавлено запросов: {added}\n"
                    f"Всего карточек: {len(self.cards)}"
                )
                
            except FileNotFoundError:
                QMessageBox.critical(self, "Ошибка", f"Файл не найден: {file_path}")
            except PermissionError:
                QMessageBox.critical(self, "Ошибка", f"Нет доступа к файлу: {file_path}")
            except UnicodeDecodeError:
                QMessageBox.critical(self, "Ошибка", f"Ошибка кодировки файла. Используйте UTF-8.")
    
    def _import_json(self, path: Path):
        """Импорт из JSON файла."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if "sequence" in data:
            seq_data = data["sequence"]
        else:
            seq_data = data
        
        self.sequence_name.setText(seq_data.get("name", "Импортировано"))
        self.default_interval.setValue(seq_data.get("default_interval", 15))
        
        cards_data = seq_data.get("cards", [])
        for i, card_data in enumerate(cards_data[:self.MAX_CARDS]):
            card = PromptCard(i)
            card.set_data(card_data)
            card.deleted.connect(self._delete_card)
            card.moved_up.connect(self._move_card_up)
            card.moved_down.connect(self._move_card_down)
            card.duplicated.connect(self._duplicate_card)
            card.focused.connect(self._on_card_focused)
            
            # Отслеживание изменений
            card.name_edit.textChanged.connect(self._mark_unsaved)
            card.prompt_edit.textChanged.connect(self._mark_unsaved)
            card.wait_after.valueChanged.connect(self._mark_unsaved)
            card.timeout.valueChanged.connect(self._mark_unsaved)
            
            self.cards.append(card)
            self.cards_layout.insertWidget(i, card)
    
    def _import_txt_lines(self, path: Path, append: bool = False) -> int:
        """
        Импорт из текстового файла (каждая строка — отдельный запрос).
        
        Returns:
            Количество добавленных запросов
        """
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if not append:
            self.sequence_name.setText(path.stem)
        
        prompts = [line.strip() for line in lines if line.strip() and not line.strip().startswith('#')]
        return self._add_prompts(prompts)
    
    def _parse_separated_prompts(self, content: str) -> List[str]:
        """
        Парсинг текста с запросами, разделёнными пустой строкой.
        
        Args:
            content: Текст для парсинга
            
        Returns:
            Список непустых запросов
        """
        # Разделяем по пустым строкам
        blocks = re.split(r'\n\s*\n', content)
        
        # Фильтруем и очищаем
        prompts = []
        for block in blocks:
            block = block.strip()
            # Пропускаем пустые блоки и комментарии
            if block and not block.startswith('#'):
                prompts.append(block)
        
        return prompts
    
    def _add_prompts(self, prompts: List[str]) -> int:
        """
        Добавить список промптов как карточки.
        
        Args:
            prompts: Список текстов запросов
            
        Returns:
            Количество добавленных запросов
        """
        added = 0
        for prompt in prompts:
            if len(self.cards) >= self.MAX_CARDS:
                QMessageBox.warning(
                    self, "Ограничение",
                    f"Достигнут лимит в {self.MAX_CARDS} карточек.\n"
                    f"Импортировано {added} из {len(prompts)} запросов."
                )
                break
            
            card = self._add_card(prompt)
            if card:
                added += 1
        
        return added
    
    def _import_from_clipboard(self):
        """Импорт запросов из буфера обмена с предварительной валидацией."""
        
        # Получаем текст из буфера обмена
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        # Проверка на пустой буфер
        if not text or not text.strip():
            QMessageBox.warning(
                self, "Буфер пуст",
                "Буфер обмена пуст или не содержит текста.\n\n"
                "Скопируйте запросы и попробуйте снова."
            )
            return
        
        # Парсим запросы (используем общий метод)
        prompts = self._parse_separated_prompts(text)
        
        # Проверка на наличие запросов
        if not prompts:
            QMessageBox.warning(
                self, "Нет запросов",
                "В буфере обмена не найдено запросов.\n\n"
                "Убедитесь, что запросы разделены пустой строкой."
            )
            return
        
        # Проверка лимита
        available_slots = self.MAX_CARDS - len(self.cards)
        will_add = min(len(prompts), available_slots)
        
        # Формируем сообщение для подтверждения
        if len(prompts) > available_slots:
            message = (
                f"В буфере обмена найдено запросов: {len(prompts)}\n"
                f"Доступно слотов: {available_slots}\n\n"
                f"Будет добавлено: {will_add} запросов\n"
                f"(остальные {len(prompts) - available_slots} будут пропущены)\n\n"
                f"Продолжить?"
            )
        else:
            # Превью первых запросов
            preview_lines = []
            for i, p in enumerate(prompts[:3]):
                short = p[:50] + "..." if len(p) > 50 else p
                short = short.replace('\n', ' ')
                preview_lines.append(f"  {i+1}. {short}")
            
            if len(prompts) > 3:
                preview_lines.append(f"  ... и ещё {len(prompts) - 3}")
            
            preview = "\n".join(preview_lines)
            
            message = (
                f"Добавить из буфера обмена {len(prompts)} запросов?\n\n"
                f"Превью:\n{preview}\n\n"
                f"Текущих карточек: {len(self.cards)}\n"
                f"После добавления: {len(self.cards) + will_add}"
            )
        
        # Диалог подтверждения
        reply = QMessageBox.question(
            self, "Подтверждение импорта",
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            self.statusBar().showMessage("Импорт отменён")
            return
        
        # Добавляем запросы
        added = self._add_prompts(prompts)
        
        self._update_card_buttons()
        self._update_cards_count()
        self.statusBar().showMessage(f"Добавлено {added} запросов из буфера обмена")
        
        QMessageBox.information(
            self, "Импорт завершён",
            f"Успешно добавлено: {added} запросов\n"
            f"Всего карточек: {len(self.cards)}"
        )


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Настройки для QSettings
    app.setOrganizationName("ChatFlow")
    app.setApplicationName("CardEditor")
    
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = CardEditor()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
