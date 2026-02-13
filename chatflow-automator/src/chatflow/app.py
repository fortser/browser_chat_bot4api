"""Application initialization and main entry point."""

import sys
from typing import Optional


def main(args: Optional[list[str]] = None) -> int:
    """
    Main application entry point.
    
    Initializes and runs the GUI application.
    """
    from PyQt6.QtWidgets import QApplication
    from chatflow.gui.main_window import MainWindow
    from chatflow.utils.logging import setup_logging
    
    # Setup logging
    setup_logging()
    
    # Create application
    app = QApplication(args or sys.argv)
    app.setApplicationName("ChatFlow Automator")
    app.setApplicationVersion("0.1.0")
    app.setOrganizationName("ChatFlow")
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
