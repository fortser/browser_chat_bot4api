"""Base exporter interface."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union

from ...core.types import SessionResult


class Exporter(ABC):
    """
    Base class for result exporters.
    
    Subclasses implement export to specific formats.
    """
    
    name: str = "base"
    extension: str = ".txt"
    description: str = "Base exporter"
    
    @abstractmethod
    def export(
        self,
        session: SessionResult,
        output_path: Union[str, Path]
    ) -> Path:
        """
        Export session results to file.
        
        Args:
            session: Session result to export
            output_path: Output file path
            
        Returns:
            Path to exported file
        """
        pass
    
    @abstractmethod
    def export_string(self, session: SessionResult) -> str:
        """
        Export session results to string.
        
        Args:
            session: Session result to export
            
        Returns:
            Exported content as string
        """
        pass
    
    def get_default_filename(self, session: SessionResult) -> str:
        """Get default filename for export."""
        return f"{session.session_id}{self.extension}"
