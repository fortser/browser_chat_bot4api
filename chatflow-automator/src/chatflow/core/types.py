"""Core data types and models."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Optional
import uuid


class TaskStatus(Enum):
    """Status of a task execution."""
    PENDING = auto()
    RUNNING = auto()
    WAITING_RESPONSE = auto()
    COMPLETED = auto()
    FAILED = auto()
    PAUSED = auto()
    CANCELLED = auto()


class BrowserStatus(Enum):
    """Status of browser connection."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    NAVIGATING = "navigating"
    READY = "ready"
    ERROR = "error"


@dataclass
class ProxyConfig:
    """Proxy configuration."""
    enabled: bool = False
    type: str = "http"  # http, https, socks5
    host: str = ""
    port: int = 0
    username: Optional[str] = None
    password: Optional[str] = None
    
    @property
    def protocol(self) -> str:
        """Get proxy protocol."""
        return self.type
    
    @property
    def url(self) -> str:
        """Get proxy URL string."""
        if not self.enabled or not self.host:
            return ""
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.type}://{auth}{self.host}:{self.port}"
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.enabled,
            "type": self.type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProxyConfig":
        """Create from dictionary."""
        return cls(
            enabled=data.get("enabled", False),
            type=data.get("type", "http"),
            host=data.get("host", ""),
            port=data.get("port", 0),
            username=data.get("username"),
            password=data.get("password"),
        )


@dataclass
class BrowserConfig:
    """Browser configuration."""
    headless: bool = False
    user_data_dir: Optional[str] = None
    user_agent: Optional[str] = None
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    extensions: list[str] = field(default_factory=list)
    hide_automation: bool = True
    stealth: bool = True
    viewport_width: int = 1280
    viewport_height: int = 800
    timeout: int = 30000
    locale: Optional[str] = None
    args: Optional[list[str]] = None
    executable_path: Optional[str] = None
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "headless": self.headless,
            "user_data_dir": self.user_data_dir,
            "user_agent": self.user_agent,
            "proxy": self.proxy.to_dict(),
            "extensions": self.extensions,
            "hide_automation": self.hide_automation,
            "stealth": self.stealth,
            "viewport_width": self.viewport_width,
            "viewport_height": self.viewport_height,
            "timeout": self.timeout,
            "locale": self.locale,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BrowserConfig":
        """Create from dictionary."""
        proxy_data = data.get("proxy", {})
        return cls(
            headless=data.get("headless", False),
            user_data_dir=data.get("user_data_dir"),
            user_agent=data.get("user_agent"),
            proxy=ProxyConfig.from_dict(proxy_data) if proxy_data else ProxyConfig(),
            extensions=data.get("extensions", []),
            hide_automation=data.get("hide_automation", True),
            stealth=data.get("stealth", True),
            viewport_width=data.get("viewport_width", 1280),
            viewport_height=data.get("viewport_height", 800),
            timeout=data.get("timeout", 30000),
            locale=data.get("locale"),
        )


@dataclass
class ConnectionConfig:
    """Connection configuration."""
    url: str = ""
    cookies_file: Optional[str] = None
    adapter_name: str = "generic"
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    adapter_settings: dict[str, Any] = field(default_factory=dict)
    
    @property
    def cookies_path(self) -> Optional[str]:
        """Alias for cookies_file."""
        return self.cookies_file
    
    @property
    def adapter(self) -> str:
        """Alias for adapter_name."""
        return self.adapter_name
    
    @property
    def headless(self) -> bool:
        """Get headless setting from browser config."""
        return self.browser.headless
    
    @property
    def user_agent(self) -> Optional[str]:
        """Get user_agent from browser config."""
        return self.browser.user_agent
    
    @property
    def timeout(self) -> int:
        """Get timeout from browser config."""
        return self.browser.timeout
    
    @property
    def stealth(self) -> bool:
        """Get stealth from browser config."""
        return self.browser.stealth
    
    @property
    def proxy_enabled(self) -> bool:
        """Check if proxy is enabled."""
        return self.browser.proxy.enabled
    
    @property
    def proxy(self) -> ProxyConfig:
        """Get proxy config."""
        return self.browser.proxy
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "cookies_file": self.cookies_file,
            "adapter_name": self.adapter_name,
            "browser": self.browser.to_dict(),
            "adapter_settings": self.adapter_settings,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ConnectionConfig":
        """Create from dictionary."""
        browser_data = data.get("browser", {})
        return cls(
            url=data.get("url", ""),
            cookies_file=data.get("cookies_file"),
            adapter_name=data.get("adapter_name", "generic"),
            browser=BrowserConfig.from_dict(browser_data) if browser_data else BrowserConfig(),
            adapter_settings=data.get("adapter_settings", {}),
        )


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID."""
    unique = uuid.uuid4().hex[:8]
    return f"{prefix}_{unique}" if prefix else unique


@dataclass
class TaskCard:
    """A single task card containing a prompt and settings."""
    id: str = field(default_factory=lambda: generate_id("card"))
    name: str = ""
    prompt: str = ""
    wait_before: int = 0  # Seconds before sending
    wait_after: int = 15  # Seconds after receiving response
    timeout: int = 120  # Timeout for waiting response
    save_response: bool = True
    enabled: bool = True
    retry_count: int = 0
    retry_delay: int = 5
    
    # For future extension
    next_task_id: Optional[str] = None
    condition: Optional[str] = None
    variables: dict[str, str] = field(default_factory=dict)
    
    @property
    def interval_after(self) -> int:
        """Alias for wait_after."""
        return self.wait_after
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "prompt": self.prompt,
            "wait_before": self.wait_before,
            "wait_after": self.wait_after,
            "timeout": self.timeout,
            "save_response": self.save_response,
            "enabled": self.enabled,
            "retry_count": self.retry_count,
            "retry_delay": self.retry_delay,
            "next_task_id": self.next_task_id,
            "condition": self.condition,
            "variables": self.variables,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskCard":
        """Create from dictionary."""
        return cls(
            id=data.get("id", generate_id("card")),
            name=data.get("name", ""),
            prompt=data.get("prompt", ""),
            wait_before=data.get("wait_before", 0),
            wait_after=data.get("wait_after", 15),
            timeout=data.get("timeout", 120),
            save_response=data.get("save_response", True),
            enabled=data.get("enabled", True),
            retry_count=data.get("retry_count", 0),
            retry_delay=data.get("retry_delay", 5),
            next_task_id=data.get("next_task_id"),
            condition=data.get("condition"),
            variables=data.get("variables", {}),
        )


@dataclass
class TaskSequence:
    """A sequence of task cards."""
    id: str = field(default_factory=lambda: generate_id("seq"))
    name: str = ""
    description: str = ""
    cards: list[TaskCard] = field(default_factory=list)
    default_interval: int = 15
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "cards": [card.to_dict() for card in self.cards],
            "default_interval": self.default_interval,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskSequence":
        """Create from dictionary."""
        cards_data = data.get("cards", [])
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        
        return cls(
            id=data.get("id", generate_id("seq")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            cards=[TaskCard.from_dict(c) for c in cards_data],
            default_interval=data.get("default_interval", 15),
            created_at=datetime.fromisoformat(created_at) if created_at else datetime.now(),
            updated_at=datetime.fromisoformat(updated_at) if updated_at else datetime.now(),
        )
    
    def add_card(self, card: TaskCard) -> None:
        """Add a card to the sequence."""
        self.cards.append(card)
        self.updated_at = datetime.now()
    
    def remove_card(self, card_id: str) -> bool:
        """Remove a card by ID."""
        for i, card in enumerate(self.cards):
            if card.id == card_id:
                self.cards.pop(i)
                self.updated_at = datetime.now()
                return True
        return False
    
    def get_card(self, card_id: str) -> Optional[TaskCard]:
        """Get a card by ID."""
        for card in self.cards:
            if card.id == card_id:
                return card
        return None
    
    def move_card(self, card_id: str, direction: int) -> bool:
        """Move a card up (-1) or down (1)."""
        for i, card in enumerate(self.cards):
            if card.id == card_id:
                new_index = i + direction
                if 0 <= new_index < len(self.cards):
                    self.cards[i], self.cards[new_index] = self.cards[new_index], self.cards[i]
                    self.updated_at = datetime.now()
                    return True
        return False
    
    @property
    def enabled_cards(self) -> list[TaskCard]:
        """Get only enabled cards."""
        return [c for c in self.cards if c.enabled]


@dataclass
class TaskResult:
    """Result of a single task execution."""
    task_id: str
    task_name: str
    prompt: str
    response: str = ""
    status: TaskStatus = TaskStatus.PENDING
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    duration_seconds: float = 0.0
    
    @property
    def error(self) -> Optional[str]:
        """Alias for error_message."""
        return self.error_message
    
    @error.setter
    def error(self, value: Optional[str]) -> None:
        """Set error_message."""
        self.error_message = value
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "task_name": self.task_name,
            "prompt": self.prompt,
            "response": self.response,
            "status": self.status.name.lower(),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "duration_seconds": self.duration_seconds,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TaskResult":
        """Create from dictionary."""
        status_str = data.get("status", "pending").upper()
        started_at = data.get("started_at")
        completed_at = data.get("completed_at")
        
        return cls(
            task_id=data.get("task_id", ""),
            task_name=data.get("task_name", ""),
            prompt=data.get("prompt", ""),
            response=data.get("response", ""),
            status=TaskStatus[status_str],
            started_at=datetime.fromisoformat(started_at) if started_at else datetime.now(),
            completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
            error_message=data.get("error_message"),
            duration_seconds=data.get("duration_seconds", 0.0),
        )


@dataclass
class SessionResult:
    """Result of a complete session execution."""
    session_id: str = field(default_factory=lambda: f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    sequence_name: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    results: list[TaskResult] = field(default_factory=list)
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    
    @property
    def successful_tasks(self) -> int:
        """Alias for completed_tasks."""
        return self.completed_tasks
    
    @successful_tasks.setter
    def successful_tasks(self, value: int) -> None:
        """Set completed_tasks."""
        self.completed_tasks = value
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "sequence_name": self.sequence_name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "results": [r.to_dict() for r in self.results],
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionResult":
        """Create from dictionary."""
        started_at = data.get("started_at")
        completed_at = data.get("completed_at")
        results_data = data.get("results", [])
        
        return cls(
            session_id=data.get("session_id", ""),
            sequence_name=data.get("sequence_name", ""),
            started_at=datetime.fromisoformat(started_at) if started_at else datetime.now(),
            completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
            results=[TaskResult.from_dict(r) for r in results_data],
            total_tasks=data.get("total_tasks", 0),
            completed_tasks=data.get("completed_tasks", 0),
            failed_tasks=data.get("failed_tasks", 0),
        )
    
    def add_result(self, result: TaskResult) -> None:
        """Add a task result."""
        self.results.append(result)
        if result.status == TaskStatus.COMPLETED:
            self.completed_tasks += 1
        elif result.status == TaskStatus.FAILED:
            self.failed_tasks += 1
    
    @property
    def progress_percent(self) -> float:
        """Get progress as percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks + self.failed_tasks) / self.total_tasks * 100
    
    @property
    def duration_seconds(self) -> float:
        """Get total session duration."""
        end = self.completed_at or datetime.now()
        return (end - self.started_at).total_seconds()
