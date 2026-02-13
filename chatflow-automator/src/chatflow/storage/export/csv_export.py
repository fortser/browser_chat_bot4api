"""CSV exporter."""

import csv
import io
from pathlib import Path
from typing import Union

from .base import Exporter
from ...core.types import SessionResult


class CSVExporter(Exporter):
    """Export results to CSV format."""
    
    name = "csv"
    extension = ".csv"
    description = "CSV format (Comma-Separated Values)"
    
    def __init__(self, delimiter: str = ",", include_response: bool = True):
        self.delimiter = delimiter
        self.include_response = include_response
    
    def export(
        self,
        session: SessionResult,
        output_path: Union[str, Path]
    ) -> Path:
        """Export to CSV file."""
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        content = self.export_string(session)
        
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(content)
        
        return path
    
    def export_string(self, session: SessionResult) -> str:
        """Export to CSV string."""
        output = io.StringIO()
        
        # Define fields
        if self.include_response:
            fieldnames = [
                "task_id",
                "task_name",
                "prompt",
                "response",
                "status",
                "duration_seconds",
                "started_at",
                "completed_at",
                "error_message",
            ]
        else:
            fieldnames = [
                "task_id",
                "task_name",
                "prompt",
                "status",
                "duration_seconds",
                "started_at",
                "completed_at",
                "error_message",
            ]
        
        writer = csv.DictWriter(
            output,
            fieldnames=fieldnames,
            delimiter=self.delimiter,
            quoting=csv.QUOTE_ALL
        )
        
        # Write header
        writer.writeheader()
        
        # Write rows
        for result in session.results:
            row = {
                "task_id": result.task_id,
                "task_name": result.task_name,
                "prompt": result.prompt,
                "status": result.status.name,
                "duration_seconds": f"{result.duration_seconds:.2f}",
                "started_at": result.started_at.isoformat() if result.started_at else "",
                "completed_at": result.completed_at.isoformat() if result.completed_at else "",
                "error_message": result.error_message or "",
            }
            
            if self.include_response:
                row["response"] = result.response
            
            writer.writerow(row)
        
        return output.getvalue()
