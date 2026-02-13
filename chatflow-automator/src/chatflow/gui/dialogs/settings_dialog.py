"""Settings dialog."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QDialogButtonBox,
    QGroupBox,
    QTextEdit,
)

from ...storage.config import ConfigManager


class SettingsDialog(QDialog):
    """Application settings dialog."""
    
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self.config = config
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        self.setWindowTitle("Настройки")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Tabs
        tabs = QTabWidget()
        
        # General tab
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        defaults_group = QGroupBox("Значения по умолчанию")
        defaults_layout = QVBoxLayout(defaults_group)
        
        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Интервал после ответа:"))
        self.default_interval = QSpinBox()
        self.default_interval.setRange(0, 3600)
        self.default_interval.setSuffix(" сек")
        interval_row.addWidget(self.default_interval)
        interval_row.addStretch()
        defaults_layout.addLayout(interval_row)
        
        timeout_row = QHBoxLayout()
        timeout_row.addWidget(QLabel("Таймаут ожидания:"))
        self.default_timeout = QSpinBox()
        self.default_timeout.setRange(1, 3600)
        self.default_timeout.setSuffix(" сек")
        timeout_row.addWidget(self.default_timeout)
        timeout_row.addStretch()
        defaults_layout.addLayout(timeout_row)
        
        general_layout.addWidget(defaults_group)
        general_layout.addStretch()
        tabs.addTab(general_tab, "Общие")
        
        # Adapter tab
        adapter_tab = QWidget()
        adapter_layout = QVBoxLayout(adapter_tab)
        
        selectors_group = QGroupBox("CSS селекторы (Generic адаптер)")
        selectors_layout = QVBoxLayout(selectors_group)
        
        selectors_layout.addWidget(QLabel("Поле ввода:"))
        self.selector_input = QLineEdit()
        selectors_layout.addWidget(self.selector_input)
        
        selectors_layout.addWidget(QLabel("Кнопка отправки:"))
        self.selector_send = QLineEdit()
        selectors_layout.addWidget(self.selector_send)
        
        selectors_layout.addWidget(QLabel("Кнопка остановки:"))
        self.selector_stop = QLineEdit()
        selectors_layout.addWidget(self.selector_stop)
        
        selectors_layout.addWidget(QLabel("Контейнер ответа:"))
        self.selector_response = QLineEdit()
        selectors_layout.addWidget(self.selector_response)
        
        adapter_layout.addWidget(selectors_group)
        adapter_layout.addStretch()
        tabs.addTab(adapter_tab, "Адаптер")
        
        layout.addWidget(tabs)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_settings(self) -> None:
        """Load settings from config."""
        self.default_interval.setValue(self.config.get("defaults.interval_after", 15))
        self.default_timeout.setValue(self.config.get("defaults.timeout", 120))
        
        selectors = self.config.get("adapter_settings.generic.selectors", {})
        self.selector_input.setText(selectors.get("input_field", "textarea"))
        self.selector_send.setText(selectors.get("send_button", "button[type='submit']"))
        self.selector_stop.setText(selectors.get("stop_button", "button[aria-label='Stop']"))
        self.selector_response.setText(selectors.get("response_container", "[data-message-author-role='assistant']"))
    
    def _save_and_accept(self) -> None:
        """Save settings and accept."""
        self.config.set("defaults.interval_after", self.default_interval.value())
        self.config.set("defaults.timeout", self.default_timeout.value())
        
        self.config.set("adapter_settings.generic.selectors.input_field", self.selector_input.text())
        self.config.set("adapter_settings.generic.selectors.send_button", self.selector_send.text())
        self.config.set("adapter_settings.generic.selectors.stop_button", self.selector_stop.text())
        self.config.set("adapter_settings.generic.selectors.response_container", self.selector_response.text())
        
        self.accept()
