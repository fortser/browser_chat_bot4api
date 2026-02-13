"""History management - tracking execution history."""

import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime
import logging

from ..core.exceptions import StorageError

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Manages execution history.
    
    Tracks session metadata for quick access without loading full results.
    """
    
    MAX_HISTORY_ENTRIES = 100
    
    def __init__(self, history_file: Optional[Path] = None):
        """
        Initialize history manager.
        
        Args:
            history_file: Path to history file
        """
        self.history_file = Path(history_file) if history_file else Path("data/history.json")
        self._history: List[dict] = []
        self._load()
    
    def _load(self) -> None:
        """Load history from file."""
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")
                self._history = []
    
    def _save(self) -> None:
        """Save history to file."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump(self._history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save history: {e}")
    
    def add_entry(
        self,
        session_id: str,
        sequence_name: str,
        total_tasks: int,
        completed_tasks: int,
        failed_tasks: int,
    ) -> None:
        """
        Add a history entry.
        
        Args:
            session_id: Session identifier
            sequence_name: Name of executed sequence
            total_tasks: Total number of tasks
            completed_tasks: Number of completed tasks
            failed_tasks: Number of failed tasks
        """
        entry = {
            "session_id": session_id,
            "sequence_name": sequence_name,
            "timestamp": datetime.now().isoformat(),
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "failed_tasks": failed_tasks,
        }
        
        self._history.insert(0, entry)
        
        # Trim history if too long
        if len(self._history) > self.MAX_HISTORY_ENTRIES:
            self._history = self._history[:self.MAX_HISTORY_ENTRIES]
        
        self._save()
    
    def get_entries(self, limit: int = 20) -> List[dict]:
        """
        Get recent history entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of history entries
        """
        return self._history[:limit]
    
    def clear(self) -> None:
        """Clear all history."""
        self._history = []
        self._save()
    
    def search(self, query: str) -> List[dict]:
        """
        Search history by sequence name.
        
        Args:
            query: Search query
            
        Returns:
            Matching history entries
        """
        query = query.lower()
        return [
            entry for entry in self._history
            if query in entry.get("sequence_name", "").lower()
        ]
    
    def get_by_session_id(self, session_id: str) -> Optional[dict]:
        """Get history entry by session ID."""
        for entry in self._history:
            if entry.get("session_id") == session_id:
                return entry
        return None
