"""GUI utility functions."""

from PyQt6.QtWidgets import QWidget, QMessageBox
from PyQt6.QtCore import Qt


def show_error(parent: QWidget, title: str, message: str) -> None:
    """Show error message box."""
    QMessageBox.critical(parent, title, message)


def show_warning(parent: QWidget, title: str, message: str) -> None:
    """Show warning message box."""
    QMessageBox.warning(parent, title, message)


def show_info(parent: QWidget, title: str, message: str) -> None:
    """Show info message box."""
    QMessageBox.information(parent, title, message)


def confirm(parent: QWidget, title: str, message: str) -> bool:
    """Show confirmation dialog."""
    reply = QMessageBox.question(
        parent, title, message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    return reply == QMessageBox.StandardButton.Yes


def set_widget_enabled_recursive(widget: QWidget, enabled: bool) -> None:
    """Enable/disable widget and all children."""
    widget.setEnabled(enabled)
    for child in widget.findChildren(QWidget):
        child.setEnabled(enabled)
