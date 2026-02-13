"""Connection settings tab."""

import asyncio
from typing import Optional
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QFileDialog,
    QSpinBox,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, QThread

from ...core.engine import Engine
from ...core.types import ConnectionConfig, BrowserConfig, ProxyConfig
from ...storage.config import ConfigManager
from ...adapters import list_adapter_names
from ...utils.validators import validate_url, validate_proxy_host
from ...utils.paths import get_cookies_dir
from ...utils.logging import get_logger

logger = get_logger(__name__)


class ConnectionWorker(QThread):
    """Worker thread for browser connection."""
    
    finished = pyqtSignal(bool, str)
    
    def __init__(self, engine: Engine, config: ConnectionConfig):
        super().__init__()
        self.engine = engine
        self.config = config
    
    def run(self):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.engine.connect(self.config))
            loop.close()
            self.finished.emit(True, "")
        except Exception as e:
            self.finished.emit(False, str(e))


class DisconnectWorker(QThread):
    """Worker thread for browser disconnection."""
    
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


class ConnectionTab(QWidget):
    """
    Connection settings tab.
    
    Allows configuring URL, proxy, cookies, and browser settings.
    """
    
    connection_ready = pyqtSignal()
    
    def __init__(self, config: ConfigManager, engine: Engine):
        super().__init__()
        self.config = config
        self.engine = engine
        self._worker: Optional[QThread] = None
        
        self._setup_ui()
        self.load_from_config()
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # URL Group
        url_group = QGroupBox("Подключение")
        url_layout = QVBoxLayout(url_group)
        
        # URL input
        url_row = QHBoxLayout()
        url_row.addWidget(QLabel("URL чата:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://chat.example.com")
        url_row.addWidget(self.url_input)
        url_layout.addLayout(url_row)
        
        # Adapter selection
        adapter_row = QHBoxLayout()
        adapter_row.addWidget(QLabel("Адаптер:"))
        self.adapter_combo = QComboBox()
        self.adapter_combo.addItems(list_adapter_names())
        adapter_row.addWidget(self.adapter_combo)
        adapter_row.addStretch()
        url_layout.addLayout(adapter_row)
        
        layout.addWidget(url_group)
        
        # Proxy Group
        proxy_group = QGroupBox("Прокси")
        proxy_layout = QVBoxLayout(proxy_group)
        
        self.proxy_enabled = QCheckBox("Использовать прокси")
        proxy_layout.addWidget(self.proxy_enabled)
        
        proxy_settings = QHBoxLayout()
        
        proxy_settings.addWidget(QLabel("Тип:"))
        self.proxy_type = QComboBox()
        self.proxy_type.addItems(["http", "https", "socks5"])
        proxy_settings.addWidget(self.proxy_type)
        
        proxy_settings.addWidget(QLabel("Хост:"))
        self.proxy_host = QLineEdit()
        self.proxy_host.setPlaceholderText("127.0.0.1")
        proxy_settings.addWidget(self.proxy_host)
        
        proxy_settings.addWidget(QLabel("Порт:"))
        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(1, 65535)
        self.proxy_port.setValue(1080)
        proxy_settings.addWidget(self.proxy_port)
        
        proxy_layout.addLayout(proxy_settings)
        
        proxy_auth = QHBoxLayout()
        proxy_auth.addWidget(QLabel("Логин:"))
        self.proxy_username = QLineEdit()
        proxy_auth.addWidget(self.proxy_username)
        proxy_auth.addWidget(QLabel("Пароль:"))
        self.proxy_password = QLineEdit()
        self.proxy_password.setEchoMode(QLineEdit.EchoMode.Password)
        proxy_auth.addWidget(self.proxy_password)
        proxy_layout.addLayout(proxy_auth)
        
        layout.addWidget(proxy_group)
        
        # Cookies Group
        cookies_group = QGroupBox("Cookies")
        cookies_layout = QVBoxLayout(cookies_group)
        
        cookies_row = QHBoxLayout()
        cookies_row.addWidget(QLabel("Файл cookies:"))
        self.cookies_path = QLineEdit()
        cookies_row.addWidget(self.cookies_path)
        self.cookies_browse_btn = QPushButton("...")
        self.cookies_browse_btn.clicked.connect(self._browse_cookies)
        cookies_row.addWidget(self.cookies_browse_btn)
        cookies_layout.addLayout(cookies_row)
        
        layout.addWidget(cookies_group)
        
        # Browser Group
        browser_group = QGroupBox("Браузер")
        browser_layout = QVBoxLayout(browser_group)
        
        self.headless_check = QCheckBox("Headless режим (без окна)")
        browser_layout.addWidget(self.headless_check)
        
        self.hide_automation_check = QCheckBox("Скрывать автоматизацию")
        self.hide_automation_check.setChecked(True)
        browser_layout.addWidget(self.hide_automation_check)
        
        layout.addWidget(browser_group)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.connect_btn = QPushButton("Подключиться")
        self.connect_btn.clicked.connect(self._connect)
        buttons_layout.addWidget(self.connect_btn)
        
        self.disconnect_btn = QPushButton("Отключиться")
        self.disconnect_btn.clicked.connect(self._disconnect)
        self.disconnect_btn.setEnabled(False)
        buttons_layout.addWidget(self.disconnect_btn)
        
        layout.addLayout(buttons_layout)
        
        layout.addStretch()
    
    def _browse_cookies(self) -> None:
        """Browse for cookies file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать файл cookies",
            str(get_cookies_dir()),
            "JSON файлы (*.json);;Все файлы (*)"
        )
        if file_path:
            self.cookies_path.setText(file_path)
    
    def _validate(self) -> bool:
        """Validate input fields."""
        url = self.url_input.text().strip()
        valid, error = validate_url(url)
        if not valid:
            QMessageBox.warning(self, "Ошибка", f"Неверный URL: {error}")
            return False
        
        if self.proxy_enabled.isChecked():
            host = self.proxy_host.text().strip()
            if host:
                valid, error = validate_proxy_host(host)
                if not valid:
                    QMessageBox.warning(self, "Ошибка", f"Неверный адрес прокси: {error}")
                    return False
        
        return True
    
    def _get_connection_config(self) -> ConnectionConfig:
        """Build ConnectionConfig from form values."""
        proxy = ProxyConfig(
            enabled=self.proxy_enabled.isChecked(),
            type=self.proxy_type.currentText(),
            host=self.proxy_host.text().strip(),
            port=self.proxy_port.value(),
            username=self.proxy_username.text() or None,
            password=self.proxy_password.text() or None,
        )
        
        browser = BrowserConfig(
            headless=self.headless_check.isChecked(),
            hide_automation=self.hide_automation_check.isChecked(),
            proxy=proxy,
        )
        
        cookies_file = self.cookies_path.text().strip() or None
        
        return ConnectionConfig(
            url=self.url_input.text().strip(),
            cookies_file=cookies_file,
            adapter_name=self.adapter_combo.currentText(),
            browser=browser,
        )
    
    def _connect(self) -> None:
        """Connect to the target site."""
        if not self._validate():
            return
        
        config = self._get_connection_config()
        
        self._set_ui_enabled(False)
        self.connect_btn.setText("Подключение...")
        
        self._worker = ConnectionWorker(self.engine, config)
        self._worker.finished.connect(self._on_connect_finished)
        self._worker.start()
    
    def _on_connect_finished(self, success: bool, error: str) -> None:
        """Handle connection result."""
        self._set_ui_enabled(True)
        self.connect_btn.setText("Подключиться")
        
        if success:
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.connection_ready.emit()
        else:
            QMessageBox.warning(self, "Ошибка подключения", error)
    
    def _disconnect(self) -> None:
        """Disconnect from browser."""
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setText("Отключение...")
        
        self._worker = DisconnectWorker(self.engine)
        self._worker.finished.connect(self._on_disconnect_finished)
        self._worker.start()
    
    def _on_disconnect_finished(self) -> None:
        """Handle disconnect result."""
        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setText("Отключиться")
    
    def _set_ui_enabled(self, enabled: bool) -> None:
        """Enable/disable UI elements."""
        self.url_input.setEnabled(enabled)
        self.adapter_combo.setEnabled(enabled)
        self.proxy_enabled.setEnabled(enabled)
        self.proxy_type.setEnabled(enabled)
        self.proxy_host.setEnabled(enabled)
        self.proxy_port.setEnabled(enabled)
        self.proxy_username.setEnabled(enabled)
        self.proxy_password.setEnabled(enabled)
        self.cookies_path.setEnabled(enabled)
        self.cookies_browse_btn.setEnabled(enabled)
        self.headless_check.setEnabled(enabled)
        self.hide_automation_check.setEnabled(enabled)
    
    def load_from_config(self) -> None:
        """Load values from config."""
        self.url_input.setText(self.config.get("connection.url", ""))
        
        adapter = self.config.get("connection.adapter_name", "generic")
        index = self.adapter_combo.findText(adapter)
        if index >= 0:
            self.adapter_combo.setCurrentIndex(index)
        
        self.proxy_enabled.setChecked(self.config.get("proxy.enabled", False))
        self.proxy_type.setCurrentText(self.config.get("proxy.type", "http"))
        self.proxy_host.setText(self.config.get("proxy.host", ""))
        self.proxy_port.setValue(self.config.get("proxy.port", 1080))
        self.proxy_username.setText(self.config.get("proxy.username", "") or "")
        self.proxy_password.setText(self.config.get("proxy.password", "") or "")
        
        self.cookies_path.setText(self.config.get("connection.cookies_file", "") or "")
        
        self.headless_check.setChecked(self.config.get("browser.headless", False))
        self.hide_automation_check.setChecked(self.config.get("browser.hide_automation", True))
    
    def save_to_config(self) -> None:
        """Save values to config."""
        self.config.set("connection.url", self.url_input.text().strip())
        self.config.set("connection.adapter_name", self.adapter_combo.currentText())
        self.config.set("connection.cookies_file", self.cookies_path.text().strip() or None)
        
        self.config.set("proxy.enabled", self.proxy_enabled.isChecked())
        self.config.set("proxy.type", self.proxy_type.currentText())
        self.config.set("proxy.host", self.proxy_host.text().strip())
        self.config.set("proxy.port", self.proxy_port.value())
        self.config.set("proxy.username", self.proxy_username.text() or None)
        self.config.set("proxy.password", self.proxy_password.text() or None)
        
        self.config.set("browser.headless", self.headless_check.isChecked())
        self.config.set("browser.hide_automation", self.hide_automation_check.isChecked())
