"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path
import tempfile
import shutil

from chatflow.core.types import TaskCard, TaskSequence, ProxyConfig, BrowserConfig
from chatflow.core.events import EventEmitter
from chatflow.storage.config import ConfigManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    path = Path(tempfile.mkdtemp())
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def event_emitter():
    """Create an event emitter."""
    return EventEmitter()


@pytest.fixture
def sample_task_card():
    """Create a sample task card."""
    return TaskCard(
        id="test_card_1",
        name="Test Card",
        prompt="Hello, how are you?",
        wait_before=0,
        wait_after=5,
        timeout=60,
    )


@pytest.fixture
def sample_sequence(sample_task_card):
    """Create a sample task sequence."""
    return TaskSequence(
        id="test_seq_1",
        name="Test Sequence",
        cards=[
            sample_task_card,
            TaskCard(id="test_card_2", name="Card 2", prompt="Second prompt"),
            TaskCard(id="test_card_3", name="Card 3", prompt="Third prompt", enabled=False),
        ],
    )


@pytest.fixture
def config_manager(temp_dir):
    """Create a config manager with temp directory."""
    config_path = temp_dir / "config.json"
    manager = ConfigManager(config_path)
    return manager


@pytest.fixture
def proxy_config():
    """Create a sample proxy config."""
    return ProxyConfig(
        enabled=True,
        type="socks5",
        host="127.0.0.1",
        port=1080,
    )


@pytest.fixture
def browser_config(proxy_config):
    """Create a sample browser config."""
    return BrowserConfig(
        headless=True,
        hide_automation=True,
        proxy=proxy_config,
    )
