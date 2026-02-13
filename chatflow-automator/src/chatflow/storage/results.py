"""Results management - saving and loading execution results."""

import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import logging

from ..core.types import SessionResult, TaskResult
from ..core.exceptions import StorageError

logger = logging.getLogger(__name__)


class ResultsManager:
    """
    Manages execution results.
    
    Handles saving, loading, and exporting results.
    """
    
    def __init__(self, results_dir: Optional[Path] = None):
        """
        Initialize results manager.
        
        Args:
            results_dir: Directory for storing results
        """
        self.results_dir = Path(results_dir) if results_dir else Path("data/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def save_session(self, session: SessionResult) -> Path:
        """
        Save a session result to file.
        
        Args:
            session: Session result to save
            
        Returns:
            Path to saved file
        """
        filename = f"{session.session_id}.json"
        file_path = self.results_dir / filename
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Session saved to {file_path}")
            return file_path
            
        except Exception as e:
            raise StorageError(f"Failed to save session: {e}")
    
    def load_session(self, session_id: str) -> SessionResult:
        """
        Load a session result from file.
        
        Args:
            session_id: Session ID to load
            
        Returns:
            SessionResult object
        """
        file_path = self.results_dir / f"{session_id}.json"
        
        if not file_path.exists():
            raise StorageError(f"Session not found: {session_id}")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            return SessionResult.from_dict(data)
            
        except json.JSONDecodeError as e:
            raise StorageError(f"Invalid session JSON: {e}")
    
    def list_sessions(self) -> List[dict]:
        """
        List all saved sessions.
        
        Returns:
            List of session info dictionaries
        """
        sessions = []
        
        for file_path in self.results_dir.glob("session_*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                sessions.append({
                    "session_id": data.get("session_id"),
                    "sequence_name": data.get("sequence_name"),
                    "started_at": data.get("started_at"),
                    "completed_at": data.get("completed_at"),
                    "total_tasks": data.get("total_tasks", 0),
                    "completed_tasks": data.get("completed_tasks", 0),
                    "failed_tasks": data.get("failed_tasks", 0),
                    "file_path": str(file_path),
                })
            except Exception as e:
                logger.warning(f"Failed to read session file {file_path}: {e}")
        
        # Sort by date, newest first
        sessions.sort(key=lambda x: x.get("started_at", ""), reverse=True)
        
        return sessions
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session file.
        
        Args:
            session_id: Session ID to delete
            
        Returns:
            True if deleted
        """
        file_path = self.results_dir / f"{session_id}.json"
        
        if file_path.exists():
            file_path.unlink()
            logger.info(f"Session deleted: {session_id}")
            return True
        
        return False
    
    def get_session_path(self, session_id: str) -> Path:
        """Get path to session file."""
        return self.results_dir / f"{session_id}.json"
    
    def session_exists(self, session_id: str) -> bool:
        """Check if session file exists."""
        return self.get_session_path(session_id).exists()
