"""Configuration management."""

import json
from pathlib import Path
from typing import Any, Optional
import logging

from ..core.types import ConnectionConfig, BrowserConfig, ProxyConfig
from ..core.exceptions import ConfigError

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Manages application configuration.
    
    Handles loading, saving, and accessing configuration values.
    """
    
    DEFAULT_CONFIG = {
        "version": "1.0",
        "connection": {
            "url": "",
            "cookies_file": None,
            "adapter_name": "generic",
        },
        "browser": {
            "headless": False,
            "hide_automation": True,
            "user_data_dir": None,
            "user_agent": None,
            "viewport_width": 1280,
            "viewport_height": 800,
            "extensions": [],
        },
        "proxy": {
            "enabled": False,
            "type": "http",
            "host": "",
            "port": 0,
            "username": None,
            "password": None,
        },
        "adapter_settings": {
            "generic": {
                "selectors": {
                    "input_field": "textarea",
                    "send_button": "button[type='submit']",
                    "stop_button": "button[aria-label='Stop']",
                    "response_container": "[data-message-author-role='assistant']",
                }
            }
        },
        "defaults": {
            "interval_after": 15,
            "timeout": 120,
        },
        "ui": {
            "window_width": 1000,
            "window_height": 700,
            "window_x": None,
            "window_y": None,
        },
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize config manager.
        
        Args:
            config_path: Path to configuration file
        """
        self.config_path = config_path
        self._config: dict[str, Any] = self._deep_copy(self.DEFAULT_CONFIG)
    
    def load(self, path: Optional[Path] = None) -> None:
        """
        Load configuration from file.
        
        Args:
            path: Path to config file (uses self.config_path if None)
        """
        file_path = path or self.config_path
        
        if not file_path:
            logger.info("No config path specified, using defaults")
            return
        
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.info(f"Config file not found: {file_path}, using defaults")
            return
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            
            # Merge with defaults
            self._config = self._deep_merge(self.DEFAULT_CONFIG, loaded)
            logger.info(f"Configuration loaded from {file_path}")
            
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid config JSON: {e}")
        except Exception as e:
            raise ConfigError(f"Failed to load config: {e}")
    
    def save(self, path: Optional[Path] = None) -> None:
        """
        Save configuration to file.
        
        Args:
            path: Path to save config (uses self.config_path if None)
        """
        file_path = path or self.config_path
        
        if not file_path:
            raise ConfigError("No config path specified")
        
        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration saved to {file_path}")
            
        except Exception as e:
            raise ConfigError(f"Failed to save config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Dot-separated key (e.g., "browser.headless")
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split(".")
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Dot-separated key
            value: Value to set
        """
        keys = key.split(".")
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_connection_config(self) -> ConnectionConfig:
        """Get connection configuration as ConnectionConfig object."""
        conn = self._config.get("connection", {})
        browser = self._config.get("browser", {})
        proxy = self._config.get("proxy", {})
        adapter_settings = self._config.get("adapter_settings", {})
        
        return ConnectionConfig(
            url=conn.get("url", ""),
            cookies_file=conn.get("cookies_file"),
            adapter_name=conn.get("adapter_name", "generic"),
            browser=BrowserConfig(
                headless=browser.get("headless", False),
                user_data_dir=browser.get("user_data_dir"),
                user_agent=browser.get("user_agent"),
                proxy=ProxyConfig.from_dict(proxy),
                extensions=browser.get("extensions", []),
                hide_automation=browser.get("hide_automation", True),
                viewport_width=browser.get("viewport_width", 1280),
                viewport_height=browser.get("viewport_height", 800),
            ),
            adapter_settings=adapter_settings,
        )
    
    def set_connection_config(self, config: ConnectionConfig) -> None:
        """Set connection configuration from ConnectionConfig object."""
        self._config["connection"] = {
            "url": config.url,
            "cookies_file": config.cookies_file,
            "adapter_name": config.adapter_name,
        }
        self._config["browser"] = {
            "headless": config.browser.headless,
            "hide_automation": config.browser.hide_automation,
            "user_data_dir": config.browser.user_data_dir,
            "user_agent": config.browser.user_agent,
            "viewport_width": config.browser.viewport_width,
            "viewport_height": config.browser.viewport_height,
            "extensions": config.browser.extensions,
        }
        self._config["proxy"] = config.browser.proxy.to_dict()
        self._config["adapter_settings"] = config.adapter_settings
    
    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigManager._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    @staticmethod
    def _deep_copy(data: dict) -> dict:
        """Deep copy a dictionary."""
        import copy
        return copy.deepcopy(data)
    
    @property
    def raw(self) -> dict[str, Any]:
        """Get raw configuration dictionary."""
        return self._deep_copy(self._config)
