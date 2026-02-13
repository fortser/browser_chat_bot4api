"""JSON exporter."""

import json
from pathlib import Path
from typing import Union

from .base import Exporter
from ...core.types import SessionResult


class JSONExporter(Exporter):
    """Export results to JSON format."""
    
    name = "json"
    extension = ".json"
    description = "JSON format"
    
    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        self.indent = indent
        self.ensure_ascii = ensure_ascii
    
    def export(
        self,
        session: SessionResult,
        output_path: Union[str, Path]
    ) -> Path:
        """Export to JSON file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        content = self.export_string(session)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return path
    
    def export_string(self, session: SessionResult) -> str:
        """Export to JSON string."""
        return json.dumps(
            session.to_dict(),
            indent=self.indent,
            ensure_ascii=self.ensure_ascii
        )
