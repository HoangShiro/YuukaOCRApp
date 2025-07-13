# core/ui/config_tabs/system_tab.py
from PySide6.QtWidgets import (QVBoxLayout, QWidget, QCheckBox, QLabel, QFrame,
                               QLineEdit, QPushButton, QHBoxLayout, QStackedWidget,
                               QComboBox, QGroupBox, QTextEdit)

def create_system_tab(self: QWidget) -> QWidget:
    """
    Tạo nội dung cho tab System trong cửa sổ Config.
    'self' ở đây là instance của ConfigWindow.
    """
    # --- Cột trái ---
    left_layout = QVBoxLayout()
    
    general_group = QGroupBox("Cài đặt chung")
    general_layout = QVBoxLayout()
    self.auto_update_cb = QCheckBox("Tự động update khi khởi động")
    self.start_with_system_cb = QCheckBox("Khởi động cùng System")
    self.text_clipboard_cb = QCheckBox("Bật đọc text clipboard")
    self.file_clipboard_cb = QCheckBox("Xử lý file từ clipboard (Ctrl+C)")
    general_layout.addWidget(self.auto_update_cb)
    general_layout.addWidget(self.start_with_system_cb)
    general_layout.addWidget(self.text_clipboard_cb)
    general_layout.addWidget(self.file_clipboard_cb)
    general_group.setLayout(general_layout)
    left_layout.addWidget(general_group)

    # Group Kiểm tra Update
    update_group = QGroupBox("Kiểm tra Update")
    update_layout = QVBoxLayout()
    self.update_status_label = QLabel("Đang kiểm tra...")
    self.update_status_label.setWordWrap(True)
    self.update_details_label = QLabel("")
    self.update_details_label.setWordWrap(True)
    self.update_details_label.setObjectName("updateDetailsLabel")
    self.update_details_label.hide()
    self.update_button = QPushButton("Cập nhật & Khởi động lại")
    self.update_button.hide()
    update_layout.addWidget(self.update_status_label)
    update_layout.addWidget(self.update_details_label)
    update_layout.addSpacing(5)
    update_layout.addWidget(self.update_button)
    update_group.setLayout(update_layout)
    left_layout.addWidget(update_group)
    left_layout.addStretch()

    # --- Cột phải ---
    right_layout = QVBoxLayout()
    right_layout.addWidget(QLabel("<b>Cài đặt Prompt & API</b>"))
    self.prompt_enabled_cb = QCheckBox("Bật prompt tùy chỉnh")
    self.custom_prompt_edit = QTextEdit()
    self.custom_prompt_edit.setPlaceholderText("Nhập prompt của bạn...")
    self.custom_prompt_edit.setFixedHeight(100)
    self.api_key_label = QLabel("Gemini API Key:")
    self.api_key_edit = QLineEdit()
    self.api_key_edit.setPlaceholderText("Dán key (AIza...) vào đây")
    self.api_key_edit.setEchoMode(QLineEdit.Password)
    self.api_key_status_label = QLabel("")
    self.api_key_save_button = QPushButton("Xác thực")
    self.api_key_status_label.setObjectName("api_key_status_label")
    api_hbox = QHBoxLayout()
    api_hbox.addWidget(self.api_key_edit)
    api_hbox.addWidget(self.api_key_save_button)
    self.gemini_model_label = QLabel("Model Gemini (mặc định: gemini-2.0-flash):")
    self.gemini_model_combo = QComboBox()
    right_layout.addWidget(self.prompt_enabled_cb)
    right_layout.addWidget(self.custom_prompt_edit)
    right_layout.addWidget(self._create_line())
    right_layout.addWidget(self.api_key_label)
    right_layout.addLayout(api_hbox)
    right_layout.addWidget(self.api_key_status_label)
    right_layout.addWidget(self.gemini_model_label)
    right_layout.addWidget(self.gemini_model_combo)
    right_layout.addStretch()
    
    return self._create_tab_content_widget(left_layout, right_layout)