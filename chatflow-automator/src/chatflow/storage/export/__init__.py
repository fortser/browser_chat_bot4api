"""Export module - various export formats."""

from .base import Exporter
from .json_export import JSONExporter
from .markdown_export import MarkdownExporter
from .csv_export import CSVExporter

# Registry of exporters
EXPORTERS = {
    "json": JSONExporter,
    "markdown": MarkdownExporter,
    "md": MarkdownExporter,
    "csv": CSVExporter,
}


def get_exporter(format_name: str) -> Exporter:
    """Get an exporter by format name."""
    format_name = format_name.lower()
    if format_name not in EXPORTERS:
        raise ValueError(f"Unknown export format: {format_name}")
    return EXPORTERS[format_name]()


def list_formats() -> list:
    """List available export formats."""
    return list(EXPORTERS.keys())


__all__ = [
    "Exporter",
    "JSONExporter",
    "MarkdownExporter",
    "CSVExporter",
    "get_exporter",
    "list_formats",
]
