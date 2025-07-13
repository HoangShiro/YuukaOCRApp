# core/ui/config_tabs/hooking_tab.py
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel, QPushButton, QHBoxLayout, QSlider
from ..hotkey_button import HotkeyCaptureButton
from PySide6.QtCore import Qt

def create_hooking_tab(self: QWidget) -> QWidget:
    """
    Tạo nội dung cho tab Hooking trong cửa sổ Config.
    'self' ở đây là instance của ConfigWindow.
    """
    # --- Cột trái ---
    left_layout = QVBoxLayout()
    left_layout.addWidget(QLabel("<b>Cài đặt Hooking</b>"))
    self.hook_sliders = {}
    hook_params = {
        "HOOK_PROXIMITY_Y": "Khoảng cách hút (trên)", "HOOK_PROXIMITY_Y_BOTTOM": "Khoảng cách hút (dưới)",
        "HOOK_OFFSET_Y_TOP": "Vị trí neo (trên)", "HOOK_OFFSET_Y_BOTTOM": "Vị trí neo (dưới)",
        "UNHOOK_DISTANCE": "Khoảng cách thả"
    }
    for param, label_text in hook_params.items():
        slider = QSlider(Qt.Horizontal); slider.setRange(-200, 200); slider.setObjectName(param)
        label = QLabel("0"); label.setMinimumWidth(40)
        hbox = QHBoxLayout(); hbox.addWidget(slider); hbox.addWidget(label)
        left_layout.addWidget(QLabel(label_text + ":")); left_layout.addLayout(hbox)
        self.hook_sliders[param] = (slider, label)
        slider.valueChanged.connect(lambda val, l=label: l.setText(str(val)))
    self.hook_reset_button = QPushButton("Reset Hooking"); left_layout.addWidget(self.hook_reset_button)
    left_layout.addStretch()

    # --- Cột phải ---
    right_layout = QVBoxLayout()
    right_layout.addWidget(QLabel("<b>Phím tắt</b>"))
    self.ocr_hotkey_label = QLabel("Phím tắt OCR khi Hook:")
    self.ocr_hotkey_button = HotkeyCaptureButton("middle")
    right_layout.addWidget(self.ocr_hotkey_label)
    right_layout.addWidget(self.ocr_hotkey_button)
    right_layout.addStretch()
    
    return self._create_tab_content_widget(left_layout, right_layout)