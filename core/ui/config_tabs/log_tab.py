# core/ui/config_tabs/log_tab.py
import json
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QFrame, QApplication)
from PySide6.QtGui import QFontMetrics
from PySide6.QtCore import Qt
import pyperclip

def _create_v_line():
    line = QFrame()
    line.setFrameShape(QFrame.Shape.VLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    line.setObjectName("separator_line")
    return line

def create_log_tab(self: QWidget) -> QWidget:
    self.log_widgets = {}

    left_layout = QVBoxLayout()
    left_layout.addWidget(QLabel("<b>Output gần nhất (Click để copy)</b>"))
    self.output_log_scroll = QScrollArea()
    self.output_log_scroll.setWidgetResizable(True)
    self.output_log_container = QWidget()
    self.output_log_container.setObjectName("logContainer")
    self.log_widgets['output_layout'] = QVBoxLayout(self.output_log_container)
    self.log_widgets['output_layout'].setAlignment(Qt.AlignTop)
    self.output_log_scroll.setWidget(self.output_log_container)
    self.clear_outputs_button = QPushButton("Xóa lịch sử Output")
    left_layout.addWidget(self.output_log_scroll)
    left_layout.addWidget(self.clear_outputs_button)

    right_layout = QVBoxLayout()
    right_layout.addWidget(QLabel("<b>Prompt gần nhất (Click để copy)</b>"))
    self.prompt_log_scroll = QScrollArea()
    self.prompt_log_scroll.setWidgetResizable(True)
    self.prompt_log_container = QWidget()
    self.prompt_log_container.setObjectName("logContainer")
    self.log_widgets['prompt_layout'] = QVBoxLayout(self.prompt_log_container)
    self.log_widgets['prompt_layout'].setAlignment(Qt.AlignTop)
    self.prompt_log_scroll.setWidget(self.prompt_log_container)
    self.clear_prompts_button = QPushButton("Xóa lịch sử Prompt")
    right_layout.addWidget(self.prompt_log_scroll)
    right_layout.addWidget(self.clear_prompts_button)

    tab_widget = QWidget()
    tab_layout = QHBoxLayout(tab_widget)
    tab_layout.setContentsMargins(15, 10, 15, 10)
    tab_layout.setSpacing(15)
    tab_layout.addLayout(left_layout, stretch=1)
    tab_layout.addWidget(_create_v_line())
    tab_layout.addLayout(right_layout, stretch=1)

    def copy_text(text, parent_window):
        pyperclip.copy(text)
        parent_window.parent().update_status("Đã copy vào clipboard!", 2000)

    def create_log_entry(entry_data, layout, parent_window):
        if not isinstance(entry_data, dict): return

        timestamp = entry_data.get("timestamp", "")
        content = entry_data.get("text", "")
        
        # --- YUUKA'S ROBUST FIX ---
        text_to_copy = "Lỗi Log"
        display_text_full = "Lỗi Log"

        if isinstance(content, dict):
            # Luôn hiển thị đầy đủ JSON trong tooltip để debug
            display_text_full = json.dumps(content, ensure_ascii=False, indent=2)
            
            # Ưu tiên lấy `extracted_text`
            extracted = content.get("extracted_text", "")
            
            # Xử lý trường hợp `extracted_text` là một chuỗi JSON
            if isinstance(extracted, str) and extracted.strip().startswith('{'):
                try:
                    inner_data = json.loads(extracted)
                    # Ưu tiên lấy text đã dịch từ JSON bên trong
                    text_to_copy = inner_data.get("translated_text", inner_data.get("original_text", extracted))
                except json.JSONDecodeError:
                    text_to_copy = extracted # Nếu parse lỗi, dùng chuỗi gốc
            else:
                 # Trường hợp bình thường, `extracted` là text
                 text_to_copy = extracted if extracted else content.get("translated_text", "")

            # Fallback cuối cùng nếu không tìm thấy gì
            if not text_to_copy:
                 text_to_copy = display_text_full

        elif isinstance(content, str):
            # Xử lý log cũ có định dạng là string
            text_to_copy = content
            display_text_full = content
        
        # Cắt ngắn text để hiển thị trên button
        elided_text = text_to_copy.replace('\n', ' ')
        if len(elided_text) > 40:
            elided_text = elided_text[:40] + "..."
            
        entry_button = QPushButton(elided_text)
        entry_button.setObjectName("logEntryButton")

        # Tooltip sẽ là timestamp + nội dung đầy đủ
        full_tooltip = f"{timestamp}\n\n{display_text_full}"
        entry_button.setToolTip(full_tooltip)
        
        entry_button.clicked.connect(lambda: copy_text(text_to_copy, parent_window))
        layout.addWidget(entry_button)

    self.log_widgets['create_entry_func'] = create_log_entry
    return tab_widget