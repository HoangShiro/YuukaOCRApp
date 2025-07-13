# core/ui/config_tabs/console_tab.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextEdit
from PySide6.QtGui import QColor, QFont

def create_console_tab(self: QWidget) -> QWidget:
    """
    Tạo nội dung cho tab Console trong cửa sổ Config.
    'self' ở đây là instance của ConfigWindow.
    """
    tab_widget = QWidget()
    layout = QVBoxLayout(tab_widget)
    layout.setContentsMargins(15, 10, 15, 10)

    # Chỉ tạo widget, không style ở đây
    self.console_output = QTextEdit()
    self.console_output.setReadOnly(True)
    
    layout.addWidget(self.console_output)
    return tab_widget