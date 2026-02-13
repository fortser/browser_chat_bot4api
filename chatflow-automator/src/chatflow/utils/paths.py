"""Path utilities for application directories."""

import os
import sys
from pathlib import Path
from typing import Optional


def get_app_dir() -> Path:
    """
    Get the application directory.
    
    Returns the directory containing the chatflow package.
    """
    # Get the package directory
    package_dir = Path(__file__).parent.parent
    return package_dir


def get_project_root() -> Path:
    """
    Get the project root directory.
    
    Returns the root directory of the project (contains src/).
    """
    app_dir = get_app_dir()
    # Go up from src/chatflow to project root
    return app_dir.parent.parent


def get_data_dir() -> Path:
    """
    Get the data directory for user data.
    
    Creates the directory if it doesn't exist.
    """
    # Check for environment variable
    env_data_dir = os.environ.get("CHATFLOW_DATA_DIR")
    if env_data_dir:
        data_dir = Path(env_data_dir)
    else:
        # Default to project_root/data
        data_dir = get_project_root() / "data"
    
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_config_path() -> Path:
    """Get the default configuration file path."""
    return get_data_dir() / "config.json"


def get_cookies_dir() -> Path:
    """Get the cookies directory."""
    cookies_dir = get_data_dir() / "cookies"
    cookies_dir.mkdir(parents=True, exist_ok=True)
    return cookies_dir


def get_tasks_dir() -> Path:
    """Get the tasks directory."""
    tasks_dir = get_data_dir() / "tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    return tasks_dir


def get_results_dir() -> Path:
    """Get the results directory."""
    results_dir = get_data_dir() / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def get_logs_dir() -> Path:
    """Get the logs directory."""
    logs_dir = get_data_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def ensure_dir(path: Path) -> Path:
    """
    Ensure a directory exists.
    
    Args:
        path: Directory path
        
    Returns:
        The path (for chaining)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def resolve_path(path: str, base_dir: Optional[Path] = None) -> Path:
    """
    Resolve a path, making it absolute if relative.
    
    Args:
        path: Path string (may be relative)
        base_dir: Base directory for relative paths
        
    Returns:
        Absolute Path
    """
    p = Path(path)
    
    if p.is_absolute():
        return p
    
    if base_dir:
        return (base_dir / p).resolve()
    
    return p.resolve()


def get_resource_path(resource_name: str) -> Path:
    """
    Get path to a bundled resource.
    
    Works both in development and when packaged.
    
    Args:
        resource_name: Name of the resource
        
    Returns:
        Path to resource
    """
    # Check if running from PyInstaller bundle
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = get_app_dir()
    
    return base_path / "gui" / "resources" / resource_name
