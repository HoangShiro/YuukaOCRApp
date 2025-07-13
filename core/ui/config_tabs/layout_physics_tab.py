# core/ui/config_tabs/layout_physics_tab.py
from PySide6.QtWidgets import (QVBoxLayout, QWidget, QLabel, QPushButton, 
                               QHBoxLayout, QSlider, QGridLayout, QButtonGroup)
from PySide6.QtCore import Qt

def create_layout_physics_tab(self: QWidget) -> QWidget:
    """
    Tạo nội dung cho tab Layout & Physics trong cửa sổ Config.
    'self' ở đây là instance của ConfigWindow.
    """
    # --- Cột trái ---
    left_layout = QVBoxLayout()
    left_layout.addWidget(QLabel("<b>Bố cục Sub-window</b>"))
    
    dpad_layout = QGridLayout()
    dpad_layout.setSpacing(2)
    self.pos_button_group = QButtonGroup(self)
    self.pos_up_button = QPushButton("▲"); self.pos_down_button = QPushButton("▼")
    self.pos_left_button = QPushButton("◀"); self.pos_right_button = QPushButton("▶")
    self.pos_auto_button = QPushButton("Auto")
    buttons = [self.pos_up_button, self.pos_down_button, self.pos_left_button, self.pos_right_button, self.pos_auto_button]
    for i, btn in enumerate(buttons):
        btn.setObjectName("pos_button"); btn.setCheckable(True); self.pos_button_group.addButton(btn, i)
    self.pos_auto_button.setChecked(True)
    dpad_layout.addWidget(self.pos_up_button, 0, 1); dpad_layout.addWidget(self.pos_down_button, 2, 1)
    dpad_layout.addWidget(self.pos_left_button, 1, 0); dpad_layout.addWidget(self.pos_right_button, 1, 2)
    dpad_layout.addWidget(self.pos_auto_button, 1, 1)
    
    self.spacing_slider = QSlider(Qt.Horizontal); self.spacing_slider.setRange(0, 100); self.spacing_value_label = QLabel("5 px"); self.spacing_value_label.setMinimumWidth(40)
    spacing_hbox = QHBoxLayout(); spacing_hbox.addWidget(self.spacing_slider); spacing_hbox.addWidget(self.spacing_value_label)
    
    self.min_sub_win_width_slider = QSlider(Qt.Horizontal); self.min_sub_win_width_slider.setRange(100, 400); self.min_sub_win_width_label = QLabel("200 px"); self.min_sub_win_width_label.setMinimumWidth(40)
    min_width_hbox = QHBoxLayout(); min_width_hbox.addWidget(self.min_sub_win_width_slider); min_width_hbox.addWidget(self.min_sub_win_width_label)
    
    self.ui_scale_slider = QSlider(Qt.Horizontal); self.ui_scale_slider.setRange(10, 100); self.ui_scale_label = QLabel("100%"); self.ui_scale_label.setMinimumWidth(40)
    scale_hbox = QHBoxLayout(); scale_hbox.addWidget(self.ui_scale_slider); scale_hbox.addWidget(self.ui_scale_label)

    left_layout.addWidget(QLabel("Vị trí:")); left_layout.addLayout(dpad_layout); left_layout.addSpacing(10)
    left_layout.addWidget(QLabel("Khoảng cách:")); left_layout.addLayout(spacing_hbox)
    left_layout.addWidget(QLabel("Độ rộng tối thiểu Sub-window:")); left_layout.addLayout(min_width_hbox)
    left_layout.addWidget(QLabel("Tỉ lệ UI:")); left_layout.addLayout(scale_hbox)
    left_layout.addStretch()

    # --- Cột phải ---
    right_layout = QVBoxLayout()
    right_layout.addWidget(QLabel("<b>Hiệu ứng vật lý</b>"))
    self.physic_sliders = {}
    physic_params = { 
        "PHYSICS_SPRING_CONSTANT": ("Hằng số lò xo", 0, 100, 0.01), 
        "PHYSICS_DAMPING_FACTOR": ("Lực cản", 0, 100, 0.01), 
        "PHYSICS_BOUNCE_DAMPING_FACTOR": ("Độ nảy", 0, 200, 0.01) 
    }
    for param, (label_text, p_min, p_max, p_scale) in physic_params.items():
        slider = QSlider(Qt.Horizontal); slider.setRange(p_min, p_max); slider.setObjectName(param)
        label = QLabel(f"0.0"); label.setMinimumWidth(40)
        hbox = QHBoxLayout(); hbox.addWidget(slider); hbox.addWidget(label)
        right_layout.addWidget(QLabel(label_text + ":")); right_layout.addLayout(hbox)
        self.physic_sliders[param] = (slider, label, p_scale)
        slider.valueChanged.connect(lambda val, l=label, s=p_scale: l.setText(f"{val*s:.2f}"))
    self.physic_reset_button = QPushButton("Reset Vật lý"); right_layout.addWidget(self.physic_reset_button)
    right_layout.addStretch()
    
    return self._create_tab_content_widget(left_layout, right_layout)