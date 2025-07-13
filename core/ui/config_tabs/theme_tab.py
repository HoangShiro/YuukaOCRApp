# core/ui/config_tabs/theme_tab.py
from PySide6.QtWidgets import (QVBoxLayout, QWidget, QLabel, QPushButton, 
                               QHBoxLayout, QFontComboBox, QSpinBox)
from PySide6.QtCore import Qt

def create_theme_tab(self: QWidget) -> QWidget:
    """
    Tạo nội dung cho tab Theme trong cửa sổ Config.
    'self' ở đây là instance của ConfigWindow.
    """
    # --- Cột trái ---
    left_layout = QVBoxLayout()
    left_layout.addWidget(QLabel("<b>Màu sắc & Font</b>"))
    
    self.theme_accent_label = QLabel("Màu nhấn (viền):")
    self.theme_accent_preview = QPushButton("...")
    self.theme_accent_pick_button = self.theme_accent_preview
    
    self.theme_bg_label = QLabel("Nền sub-window:")
    self.theme_bg_preview = QPushButton("...")
    self.theme_bg_pick_button = self.theme_bg_preview
    
    self.theme_text_label = QLabel("Chữ sub-window:")
    self.theme_text_preview = QPushButton("...")
    self.theme_text_pick_button = self.theme_text_preview

    self.theme_close_button_label = QLabel("Màu nút Close:")
    self.theme_close_button_preview = QPushButton("...")
    self.theme_close_button_pick_button = self.theme_close_button_preview

    self.font_label = QLabel("Font chữ:")
    self.font_family_combo = QFontComboBox()
    self.font_size_spinbox = QSpinBox()
    self.font_size_spinbox.setRange(8, 24)
    self.font_size_spinbox.setSuffix(" pt")
    font_hbox = QHBoxLayout()
    font_hbox.addWidget(self.font_family_combo)
    font_hbox.addWidget(self.font_size_spinbox)
    
    left_layout.addWidget(self.theme_accent_label); left_layout.addWidget(self.theme_accent_preview)
    left_layout.addWidget(self.theme_bg_label); left_layout.addWidget(self.theme_bg_preview)
    left_layout.addWidget(self.theme_text_label); left_layout.addWidget(self.theme_text_preview)
    left_layout.addWidget(self.theme_close_button_label); left_layout.addWidget(self.theme_close_button_preview)
    left_layout.addWidget(self._create_line())
    left_layout.addWidget(self.font_label); left_layout.addLayout(font_hbox)
    left_layout.addStretch()

    # --- Cột phải ---
    right_layout = QVBoxLayout()
    right_layout.addWidget(QLabel("<b>Tùy chỉnh UI</b>"))
    
    self.ui_drop_zone = QLabel("Kéo file giao diện .png tuỳ chỉnh vào đây")
    self.ui_drop_zone.setObjectName("dropZone")
    self.ui_drop_zone.setAlignment(Qt.AlignCenter)
    self.ui_drop_zone.setAcceptDrops(True)
    self.ui_drop_zone.dragEnterEvent = self.dragEnterEvent
    self.ui_drop_zone.dropEvent = self.dropEvent
    
    self.ui_preview_label = QLabel("Giao diện hiện tại")
    self.ui_preview_label.setObjectName("uiPreview")
    self.ui_preview_label.setAlignment(Qt.AlignCenter)
    self.ui_preview_label.setMinimumHeight(100)
    self.ui_preview_label.setMaximumWidth(250)
    
    right_layout.addWidget(self.ui_drop_zone)
    right_layout.addWidget(self.ui_preview_label, alignment=Qt.AlignCenter)
    right_layout.addStretch()

    return self._create_tab_content_widget(left_layout, right_layout)