# core/ui/config_tabs/log_tab.py
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

    # YUUKA: Dùng QPushButton và cắt ngắn text theo ký tự
    def create_log_entry(entry_data, layout, parent_window):
        if not isinstance(entry_data, dict): return

        timestamp = entry_data.get("timestamp", "")
        text_content = entry_data.get("text", "")
        display_text = text_content.replace('\n', ' ')

        # Cắt ngắn text theo số ký tự
        char_limit = 35
        if len(display_text) > char_limit:
            elided_text = display_text[:char_limit] + "..."
        else:
            elided_text = display_text
            
        entry_button = QPushButton(elided_text)
        entry_button.setObjectName("logEntryButton")

        full_tooltip = f"{timestamp}\n\n{text_content}"
        entry_button.setToolTip(full_tooltip)
        
        entry_button.clicked.connect(lambda: copy_text(text_content, parent_window))
        layout.addWidget(entry_button)

    self.log_widgets['create_entry_func'] = create_log_entry
    return tab_widget