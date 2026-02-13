"""Tests for storage module."""

import pytest
import json
from pathlib import Path
from datetime import datetime

from chatflow.core.types import SessionResult, TaskResult, TaskStatus
from chatflow.storage.config import ConfigManager
from chatflow.storage.results import ResultsManager


class TestConfigManager:
    """Tests for ConfigManager."""
    
    def test_default_config(self, config_manager):
        """Test default configuration."""
        assert config_manager.get("browser.headless") is False
        assert config_manager.get("defaults.timeout") == 120
    
    def test_set_and_get(self, config_manager):
        """Test setting and getting values."""
        config_manager.set("connection.url", "https://test.com")
        assert config_manager.get("connection.url") == "https://test.com"
    
    def test_nested_set(self, config_manager):
        """Test setting nested values."""
        config_manager.set("new.nested.value", 42)
        assert config_manager.get("new.nested.value") == 42
    
    def test_save_and_load(self, config_manager, temp_dir):
        """Test saving and loading config."""
        config_manager.set("test.value", "hello")
        config_manager.save()
        
        # Create new manager and load
        new_manager = ConfigManager(config_manager.config_path)
        new_manager.load()
        
        assert new_manager.get("test.value") == "hello"
    
    def test_get_connection_config(self, config_manager):
        """Test getting connection config object."""
        config_manager.set("connection.url", "https://example.com")
        config_manager.set("proxy.enabled", True)
        config_manager.set("proxy.host", "127.0.0.1")
        
        conn_config = config_manager.get_connection_config()
        
        assert conn_config.url == "https://example.com"
        assert conn_config.browser.proxy.enabled is True


class TestResultsManager:
    """Tests for ResultsManager."""
    
    def test_save_session(self, temp_dir):
        """Test saving a session."""
        manager = ResultsManager(temp_dir)
        
        session = SessionResult(
            session_id="test_session_123",
            sequence_name="Test Sequence",
            total_tasks=2,
            completed_tasks=1,
            failed_tasks=1,
        )
        
        session.results.append(TaskResult(
            task_id="task_1",
            task_name="Task 1",
            prompt="Hello",
            response="Hi there!",
            status=TaskStatus.COMPLETED,
            started_at=datetime.now(),
            duration_seconds=5.0,
        ))
        
        path = manager.save_session(session)
        
        assert path.exists()
        assert "test_session_123" in path.name
    
    def test_load_session(self, temp_dir):
        """Test loading a session."""
        manager = ResultsManager(temp_dir)
        
        # Save first
        session = SessionResult(
            session_id="test_session_456",
            sequence_name="Test",
            total_tasks=1,
        )
        manager.save_session(session)
        
        # Load
        loaded = manager.load_session("test_session_456")
        
        assert loaded.session_id == "test_session_456"
        assert loaded.sequence_name == "Test"
    
    def test_list_sessions(self, temp_dir):
        """Test listing sessions."""
        manager = ResultsManager(temp_dir)
        
        # Save multiple sessions
        for i in range(3):
            session = SessionResult(
                session_id=f"session_{i}",
                sequence_name=f"Sequence {i}",
            )
            manager.save_session(session)
        
        sessions = manager.list_sessions()
        
        assert len(sessions) == 3
    
    def test_delete_session(self, temp_dir):
        """Test deleting a session."""
        manager = ResultsManager(temp_dir)
        
        session = SessionResult(session_id="to_delete")
        manager.save_session(session)
        
        assert manager.session_exists("to_delete")
        
        manager.delete_session("to_delete")
        
        assert not manager.session_exists("to_delete")
