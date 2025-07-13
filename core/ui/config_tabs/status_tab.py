# core/ui/config_tabs/status_tab.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QScrollArea)
from PySide6.QtCore import Qt

def create_status_tab(self: QWidget) -> QWidget:
    """
    Tạo nội dung cho tab Status trong cửa sổ Config.
    'self' ở đây là instance của ConfigWindow.
    """
    tab_widget = QWidget()
    layout = QVBoxLayout(tab_widget)
    layout.setContentsMargins(15, 10, 15, 10)

    layout.addWidget(QLabel("<b>Thống kê sử dụng Yuuka</b>"))

    # Widget này được tạo ở đây, nhưng được định nghĩa và cập nhật trong ConfigWindow
    self.status_display = QLabel("Đang tải dữ liệu log...")
    self.status_display.setObjectName("status_display") # Đặt tên để CSS nhận diện
    self.status_display.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    self.status_display.setWordWrap(True)

    status_scroll = QScrollArea()
    status_scroll.setWidgetResizable(True)
    status_scroll.setWidget(self.status_display)
    
    layout.addWidget(status_scroll)
    
    return tab_widget