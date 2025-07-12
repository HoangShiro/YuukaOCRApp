# core/sub_windows.py
import os
import threading
from PySide6.QtWidgets import (QTextEdit, QVBoxLayout, QWidget, QApplication, QCheckBox,
                               QLabel, QFrame, QLineEdit, QPushButton, QHBoxLayout, QColorDialog,
                               QFontComboBox, QSpinBox, QSlider, QGridLayout, QButtonGroup,
                               QSizePolicy, QFileDialog, QAbstractItemView, QStackedWidget,
                               QComboBox, QGroupBox)
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QDragEnterEvent, QMouseEvent, QKeyEvent, QPixmap, QKeySequence
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QUrl, QEvent, QTimer

from core.physics import PhysicsMovableWidget
from core import update

class HotkeyCaptureButton(QPushButton):
    hotkey_captured = Signal(str)

    MODIFIER_MAP = {
        Qt.ShiftModifier: "shift",
        Qt.ControlModifier: "ctrl",
        Qt.AltModifier: "alt",
        Qt.MetaModifier: "meta"
    }

    MOUSE_MAP = {
        Qt.MiddleButton: "middle",
        Qt.XButton1: "x1",
        Qt.XButton2: "x2"
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_capturing = False
        self._original_text = ""
        self.clicked.connect(self._toggle_capture_mode)

    def _toggle_capture_mode(self):
        self._is_capturing = not self._is_capturing
        if self._is_capturing:
            self._original_text = self.text()
            self.setText("Đang ghi... (ESC để hủy)")
            self.setFocus(Qt.OtherFocusReason)
            self.grabKeyboard()
            QApplication.instance().installEventFilter(self)
        else:
            self.stop_capture()

    def keyPressEvent(self, event: QKeyEvent):
        if self._is_capturing and event.key() != Qt.Key_unknown:
            if event.key() == Qt.Key_Escape:
                self.stop_capture()
                return

            if event.key() in [Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta]:
                return

            mods = []
            modifiers = QApplication.keyboardModifiers()
            for mod, name in self.MODIFIER_MAP.items():
                if modifiers & mod:
                    mods.append(name)

            is_f_key = Qt.Key_F1 <= event.key() <= Qt.Key_F35
            if mods and is_f_key:
                original_text = self._original_text
                self.stop_capture("Tổ hợp phím F không được hỗ trợ")
                self._original_text = original_text 
                QTimer.singleShot(2000, lambda: self.set_display_text(self._original_text))
                return

            key_name = QKeySequence(event.key()).toString(QKeySequence.NativeText).lower()
            if not key_name or len(key_name)>10:
                 key_name = QKeySequence(event.key()).toString().lower().strip()
            if not key_name:
                return

            hotkey_str = "+".join(mods + [key_name])
            self.set_hotkey(hotkey_str)
        else:
            super().keyPressEvent(event)

    def eventFilter(self, watched, event):
        if self._is_capturing and event.type() == QEvent.MouseButtonPress:
            button = event.button()
            if button in self.MOUSE_MAP:
                mods = []
                modifiers = QApplication.keyboardModifiers()
                for mod, name in self.MODIFIER_MAP.items():
                    if modifiers & mod:
                        mods.append(name)

                mouse_str = self.MOUSE_MAP[button]
                hotkey_str = "+".join(mods + [mouse_str])
                self.set_hotkey(hotkey_str)
                return True
        return super().eventFilter(watched, event)

    def set_hotkey(self, hotkey_str):
        self.stop_capture(hotkey_str)
        self.hotkey_captured.emit(hotkey_str)

    def set_display_text(self, text):
        if not self._is_capturing:
            self.setText(text)
            self._original_text = text

    def stop_capture(self, new_text=None):
        if not self._is_capturing:
            return
        self._is_capturing = False
        self.releaseKeyboard()
        QApplication.instance().removeEventFilter(self)
        self.setText(new_text if new_text is not None else self._original_text)

class ThemedSubWindow(PhysicsMovableWidget):
    def __init__(self, parent=None, physics_config=None):
        super().__init__(parent, physics_config)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.text_edit = QTextEdit(self)
        self.text_edit.installEventFilter(self)
        self.container_layout = QVBoxLayout(self)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.addWidget(self.text_edit)
        self.setLayout(self.container_layout)
        self.setMaximumHeight(600)
        self.min_width = 200

    def apply_stylesheet(self, theme_config):
        bg = theme_config.get('sub_win_bg', 'rgba(30, 30, 30, 245)')
        text = theme_config.get('sub_win_text', '#FFFFFF')
        accent = theme_config.get('accent_color', '#E98973')
        font_family = theme_config.get('sub_win_font_family', 'Segoe UI')
        font_size = theme_config.get('sub_win_font_size', 10)
        self.text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg}; border: 1px solid {accent}; border-radius: 8px;
                color: {text}; padding: 8px;
                font-family: "{font_family}", sans-serif; font-size: {font_size}pt;
            }}""")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.hide()
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton: self.hide(); event.accept(); return
        super().mousePressEvent(event)
        
    def setText(self, text): self.text_edit.setText(text); self.adjustSize()
    def toPlainText(self): return self.text_edit.toPlainText()
    def setFixedWidth(self, width):
        # YUUKA: Ghi đè để sử dụng min_width
        effective_width = max(self.min_width, width)
        super().setFixedWidth(effective_width); self.text_edit.setFixedWidth(effective_width)
    def setMinimumWidth(self, width):
        self.min_width = width
        super().setMinimumWidth(width)

class ResultDisplayWindow(ThemedSubWindow):
    def __init__(self, parent=None, physics_config=None):
        super().__init__(parent, physics_config)
        self.text_edit.setReadOnly(True)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton: event.accept(); return
        super().mousePressEvent(event)
    
    def eventFilter(self, obj, event):
        return super().eventFilter(obj, event)

class NotificationWindow(ThemedSubWindow):
    def __init__(self, parent=None, physics_config=None):
        super().__init__(parent, physics_config)
        self.text_edit.setReadOnly(True)
        self.text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
    def setText(self, text):
        super().setText(text)
        doc_height = self.text_edit.document().size().height()
        margins = self.text_edit.contentsMargins()
        self.text_edit.setFixedHeight(doc_height + margins.top() + margins.bottom())
        self.adjustSize()

class ConfigWindow(PhysicsMovableWidget):
    config_changed = Signal(dict)
    apiKeySubmitted = Signal(str)
    uiImageChanged = Signal(str)
    requestRestart = Signal()
    updateCheckCompleted = Signal(int, str)

    def __init__(self, parent=None, physics_config=None):
        super().__init__(parent, physics_config)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.constrain_to_screen = False
        self.setMinimumWidth(800)
        self.drag_pos = None
        self.current_pos_mode = 'auto'
        self.container = QWidget(self); self.container.setObjectName("container")
        
        self._setup_ui()
        self.apply_stylesheet({}, {}, {})
        self._connect_signals()

    def _setup_ui(self):
        main_layout = QHBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.stacked_widget = QStackedWidget()
        nav_widget = self._create_nav_bar()
        
        system_tab = self._create_system_tab()
        theme_tab = self._create_theme_tab()
        layout_physics_tab = self._create_layout_physics_tab()
        hooking_tab = self._create_hooking_tab()

        self.stacked_widget.addWidget(system_tab)
        self.stacked_widget.addWidget(theme_tab)
        self.stacked_widget.addWidget(layout_physics_tab)
        self.stacked_widget.addWidget(hooking_tab)
        
        main_layout.addWidget(nav_widget)
        main_layout.addWidget(self._create_v_line())
        main_layout.addWidget(self.stacked_widget, stretch=1)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.container)
        self.setLayout(root_layout)
        
        self.nav_button_group.button(0).setChecked(True)

    def _create_nav_bar(self):
        nav_widget = QWidget(); nav_widget.setObjectName("navBar")
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(15, 10, 15, 10); nav_layout.setSpacing(5)
        
        self.nav_button_group = QButtonGroup(self)
        self.nav_button_group.setExclusive(True)

        tab_names = ["Hệ thống", "Giao diện", "Bố cục & Vật lý", "Hooking"]
        for i, name in enumerate(tab_names):
            button = QPushButton(name); button.setObjectName("navButton"); button.setCheckable(True)
            nav_layout.addWidget(button)
            self.nav_button_group.addButton(button, i)

        self.nav_button_group.idClicked.connect(self.stacked_widget.setCurrentIndex)
        
        nav_layout.addStretch()
        nav_widget.setLayout(nav_layout)
        return nav_widget

    def _create_tab_content_widget(self, left_layout, right_layout):
        tab_widget = QWidget()
        tab_layout = QHBoxLayout(tab_widget)
        tab_layout.setContentsMargins(15, 10, 15, 10); tab_layout.setSpacing(15)
        tab_layout.addLayout(left_layout, stretch=1)
        tab_layout.addWidget(self._create_v_line())
        tab_layout.addLayout(right_layout, stretch=1)
        return tab_widget

    def _create_system_tab(self):
        # --- Cột trái ---
        left = QVBoxLayout()
        
        # Group Cài đặt chung
        general_group = QGroupBox("Cài đặt chung")
        general_layout = QVBoxLayout()
        self.auto_update_cb = QCheckBox("Tự động update khi khởi động")
        self.text_clipboard_cb = QCheckBox("Bật đọc text clipboard")
        self.file_clipboard_cb = QCheckBox("Xử lý file từ clipboard (Ctrl+C)")
        general_layout.addWidget(self.auto_update_cb)
        general_layout.addWidget(self.text_clipboard_cb)
        general_layout.addWidget(self.file_clipboard_cb)
        general_group.setLayout(general_layout)
        left.addWidget(general_group)

        # Group Kiểm tra Update
        update_group = QGroupBox("Kiểm tra Update")
        update_layout = QVBoxLayout()
        self.update_status_label = QLabel("Đang kiểm tra...")
        self.update_status_label.setWordWrap(True)
        self.update_button = QPushButton("Cập nhật & Khởi động lại")
        self.update_button.hide() # Ẩn ban đầu
        update_layout.addWidget(self.update_status_label)
        update_layout.addWidget(self.update_button)
        update_group.setLayout(update_layout)
        left.addWidget(update_group)
        
        left.addStretch()

        # --- Cột phải (không đổi) ---
        right = QVBoxLayout(); right.addWidget(QLabel("<b>Cài đặt Prompt & API</b>"))
        self.prompt_enabled_cb = QCheckBox("Bật prompt tùy chỉnh")
        self.custom_prompt_edit = QTextEdit(); self.custom_prompt_edit.setPlaceholderText("Nhập prompt của bạn..."); self.custom_prompt_edit.setFixedHeight(100)
        self.api_key_label = QLabel("Gemini API Key:")
        self.api_key_edit = QLineEdit(); self.api_key_edit.setPlaceholderText("Dán key (AIza...) vào đây"); self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_status_label = QLabel(""); self.api_key_save_button = QPushButton("Xác thực"); self.api_key_status_label.setObjectName("api_key_status_label")
        api_hbox = QHBoxLayout(); api_hbox.addWidget(self.api_key_edit); api_hbox.addWidget(self.api_key_save_button)
        self.gemini_model_label = QLabel("Model Gemini (mặc định: gemini-2.0-flash):")
        self.gemini_model_combo = QComboBox()
        right.addWidget(self.prompt_enabled_cb); right.addWidget(self.custom_prompt_edit); right.addWidget(self._create_line()); right.addWidget(self.api_key_label); right.addLayout(api_hbox); right.addWidget(self.api_key_status_label)
        right.addWidget(self.gemini_model_label); right.addWidget(self.gemini_model_combo); right.addStretch()
        
        return self._create_tab_content_widget(left, right)

    def _create_theme_tab(self):
        left = QVBoxLayout(); left.addWidget(QLabel("<b>Màu sắc & Font</b>"))
        self.theme_accent_label = QLabel("Màu nhấn (viền):"); self.theme_accent_preview = QPushButton("..."); self.theme_accent_pick_button = self.theme_accent_preview
        self.theme_bg_label = QLabel("Nền sub-window:"); self.theme_bg_preview = QPushButton("..."); self.theme_bg_pick_button = self.theme_bg_preview
        self.theme_text_label = QLabel("Chữ sub-window:"); self.theme_text_preview = QPushButton("..."); self.theme_text_pick_button = self.theme_text_preview
        self.theme_close_button_label = QLabel("Màu nút Close:"); self.theme_close_button_preview = QPushButton("..."); self.theme_close_button_pick_button = self.theme_close_button_preview
        self.font_label = QLabel("Font chữ:"); self.font_family_combo = QFontComboBox(); self.font_size_spinbox = QSpinBox(); self.font_size_spinbox.setRange(8, 24); self.font_size_spinbox.setSuffix(" pt")
        font_hbox = QHBoxLayout(); font_hbox.addWidget(self.font_family_combo); font_hbox.addWidget(self.font_size_spinbox)
        left.addWidget(self.theme_accent_label); left.addWidget(self.theme_accent_preview); left.addWidget(self.theme_bg_label); left.addWidget(self.theme_bg_preview)
        left.addWidget(self.theme_text_label); left.addWidget(self.theme_text_preview); left.addWidget(self.theme_close_button_label); left.addWidget(self.theme_close_button_preview); left.addWidget(self._create_line())
        left.addWidget(self.font_label); left.addLayout(font_hbox); left.addStretch()

        right = QVBoxLayout(); right.addWidget(QLabel("<b>Tùy chỉnh UI</b>"))
        self.ui_drop_zone = QLabel("Kéo file giao diện .png tuỳ chỉnh vào đây"); self.ui_drop_zone.setObjectName("dropZone"); self.ui_drop_zone.setAlignment(Qt.AlignCenter); self.ui_drop_zone.setAcceptDrops(True)
        self.ui_drop_zone.dragEnterEvent = self.dragEnterEvent; self.ui_drop_zone.dropEvent = self.dropEvent
        self.ui_preview_label = QLabel("Giao diện hiện tại"); self.ui_preview_label.setObjectName("uiPreview"); self.ui_preview_label.setAlignment(Qt.AlignCenter); self.ui_preview_label.setMinimumHeight(100)
        self.ui_preview_label.setMaximumWidth(250)
        right.addWidget(self.ui_drop_zone); right.addWidget(self.ui_preview_label, alignment=Qt.AlignCenter); right.addStretch()

        return self._create_tab_content_widget(left, right)

    def _create_layout_physics_tab(self):
        left = QVBoxLayout(); left.addWidget(QLabel("<b>Bố cục Sub-window</b>"))
        dpad_layout = QGridLayout(); dpad_layout.setSpacing(2); self.pos_button_group = QButtonGroup(self)
        self.pos_up_button = QPushButton("▲"); self.pos_down_button = QPushButton("▼"); self.pos_left_button = QPushButton("◀"); self.pos_right_button = QPushButton("▶"); self.pos_auto_button = QPushButton("Auto")
        buttons = [self.pos_up_button, self.pos_down_button, self.pos_left_button, self.pos_right_button, self.pos_auto_button]
        for i, btn in enumerate(buttons): btn.setObjectName("pos_button"); btn.setCheckable(True); self.pos_button_group.addButton(btn, i)
        self.pos_auto_button.setChecked(True)
        dpad_layout.addWidget(self.pos_up_button, 0, 1); dpad_layout.addWidget(self.pos_down_button, 2, 1); dpad_layout.addWidget(self.pos_left_button, 1, 0); dpad_layout.addWidget(self.pos_right_button, 1, 2); dpad_layout.addWidget(self.pos_auto_button, 1, 1)
        
        self.spacing_slider = QSlider(Qt.Horizontal); self.spacing_slider.setRange(0, 100); self.spacing_value_label = QLabel("5 px"); self.spacing_value_label.setMinimumWidth(40)
        spacing_hbox = QHBoxLayout(); spacing_hbox.addWidget(self.spacing_slider); spacing_hbox.addWidget(self.spacing_value_label)
        
        self.min_sub_win_width_slider = QSlider(Qt.Horizontal); self.min_sub_win_width_slider.setRange(100, 400); self.min_sub_win_width_label = QLabel("200 px"); self.min_sub_win_width_label.setMinimumWidth(40)
        min_width_hbox = QHBoxLayout(); min_width_hbox.addWidget(self.min_sub_win_width_slider); min_width_hbox.addWidget(self.min_sub_win_width_label)
        
        self.ui_scale_slider = QSlider(Qt.Horizontal); self.ui_scale_slider.setRange(10, 100); self.ui_scale_label = QLabel("100%"); self.ui_scale_label.setMinimumWidth(40)
        scale_hbox = QHBoxLayout(); scale_hbox.addWidget(self.ui_scale_slider); scale_hbox.addWidget(self.ui_scale_label)

        left.addWidget(QLabel("Vị trí:")); left.addLayout(dpad_layout); left.addSpacing(10)
        left.addWidget(QLabel("Khoảng cách:")); left.addLayout(spacing_hbox)
        left.addWidget(QLabel("Độ rộng tối thiểu Sub-window:")); left.addLayout(min_width_hbox)
        left.addWidget(QLabel("Tỉ lệ UI:")); left.addLayout(scale_hbox)
        left.addStretch()

        right = QVBoxLayout(); right.addWidget(QLabel("<b>Hiệu ứng vật lý</b>")); self.physic_sliders = {}
        physic_params = { "PHYSICS_SPRING_CONSTANT": ("Hằng số lò xo", 0, 100, 0.01), "PHYSICS_DAMPING_FACTOR": ("Lực cản", 0, 100, 0.01), "PHYSICS_BOUNCE_DAMPING_FACTOR": ("Độ nảy", 0, 200, 0.01) }
        for param, (label_text, p_min, p_max, p_scale) in physic_params.items():
            slider = QSlider(Qt.Horizontal); slider.setRange(p_min, p_max); slider.setObjectName(param)
            label = QLabel(f"0.0"); label.setMinimumWidth(40)
            hbox = QHBoxLayout(); hbox.addWidget(slider); hbox.addWidget(label)
            right.addWidget(QLabel(label_text + ":")); right.addLayout(hbox)
            self.physic_sliders[param] = (slider, label, p_scale)
            slider.valueChanged.connect(lambda val, l=label, s=p_scale: l.setText(f"{val*s:.2f}"))
        self.physic_reset_button = QPushButton("Reset Vật lý"); right.addWidget(self.physic_reset_button)
        right.addStretch()
        
        return self._create_tab_content_widget(left, right)

    def _create_hooking_tab(self):
        left = QVBoxLayout()
        left.addWidget(QLabel("<b>Cài đặt Hooking</b>"))
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
            left.addWidget(QLabel(label_text + ":")); left.addLayout(hbox)
            self.hook_sliders[param] = (slider, label)
            slider.valueChanged.connect(lambda val, l=label: l.setText(str(val)))
        self.hook_reset_button = QPushButton("Reset Hooking"); left.addWidget(self.hook_reset_button)
        left.addStretch()

        right = QVBoxLayout()
        right.addWidget(QLabel("<b>Phím tắt</b>"))
        self.ocr_hotkey_label = QLabel("Phím tắt OCR khi Hook:")
        self.ocr_hotkey_button = HotkeyCaptureButton("middle")
        right.addWidget(self.ocr_hotkey_label)
        right.addWidget(self.ocr_hotkey_button)
        right.addStretch()
        
        return self._create_tab_content_widget(left, right)
    
    def _connect_signals(self):
        self.auto_update_cb.stateChanged.connect(self._emit_changes)
        self.update_button.clicked.connect(self._on_update_button_clicked)
        self.updateCheckCompleted.connect(self._on_update_check_completed)
        self.text_clipboard_cb.stateChanged.connect(self._emit_changes)
        self.file_clipboard_cb.stateChanged.connect(self._emit_changes)
        self.prompt_enabled_cb.stateChanged.connect(self._emit_changes)
        self.custom_prompt_edit.textChanged.connect(self._emit_changes)
        self.api_key_save_button.clicked.connect(self._submit_api_key)
        self.gemini_model_combo.currentIndexChanged.connect(self._emit_changes)
        self.theme_accent_pick_button.clicked.connect(lambda: self._pick_color('accent'))
        self.theme_bg_pick_button.clicked.connect(lambda: self._pick_color('bg'))
        self.theme_text_pick_button.clicked.connect(lambda: self._pick_color('text'))
        self.theme_close_button_pick_button.clicked.connect(lambda: self._pick_color('close_button'))
        self.font_family_combo.currentFontChanged.connect(self._emit_changes)
        self.font_size_spinbox.valueChanged.connect(self._emit_changes)
        self.ui_drop_zone.installEventFilter(self)
        self.pos_button_group.buttonClicked.connect(self._on_pos_button_clicked)
        self.spacing_slider.valueChanged.connect(self._on_spacing_changed)
        self.min_sub_win_width_slider.valueChanged.connect(self._on_min_width_changed)
        self.ui_scale_slider.valueChanged.connect(self._on_ui_scale_changed)
        for slider, _, _ in self.physic_sliders.values(): slider.valueChanged.connect(self._emit_changes)
        self.physic_reset_button.clicked.connect(self._reset_physic_sliders)
        for slider, _ in self.hook_sliders.values(): slider.valueChanged.connect(self._emit_changes)
        self.hook_reset_button.clicked.connect(self._reset_hook_sliders)
        self.ocr_hotkey_button.hotkey_captured.connect(self._on_hotkey_captured)

    def _create_line(self): line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setFrameShadow(QFrame.Shadow.Sunken); line.setObjectName("separator_line"); return line
    def _create_v_line(self): line = QFrame(); line.setFrameShape(QFrame.Shape.VLine); line.setFrameShadow(QFrame.Shadow.Sunken); line.setObjectName("separator_line"); return line

    def apply_stylesheet(self, theme_config, user_config, app_configs):
        accent_color = theme_config.get('accent_color', '#E98973')
        bg_color_str = theme_config.get('sub_win_bg', 'rgba(30, 30, 30, 245)')
        text_color = theme_config.get('sub_win_text', '#FFFFFF')
        font_family = theme_config.get('sub_win_font_family', 'Segoe UI')
        font_size = theme_config.get('sub_win_font_size', 10)
        
        default_close_color = app_configs.get("CLOSE_BUTTON_COLOR_RGB", [233, 115, 158])
        close_btn_rgb = user_config.get('close_button_color', default_close_color)
        close_btn_qcolor = QColor(*close_btn_rgb); close_btn_hex = close_btn_qcolor.name() 

        bg_qcolor = QColor(bg_color_str)
        nav_bg_color = bg_qcolor.lighter(110).name() if bg_qcolor.lightnessF() < 0.5 else bg_qcolor.darker(105).name()
        btn_bg, btn_hover, btn_pressed = (bg_qcolor.lighter(130).name(), bg_qcolor.lighter(160).name(), bg_qcolor.lighter(110).name()) if bg_qcolor.lightnessF() < 0.5 else (bg_qcolor.darker(115).name(), bg_qcolor.darker(130).name(), bg_qcolor.darker(105).name())
        
        self.container.setStyleSheet(f"""
            #container {{ background-color: {bg_color_str}; border: 1px solid {accent_color}; border-radius: 8px; }}
            #navBar {{ background-color: {nav_bg_color}; border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
            #separator_line {{ color: {QColor(accent_color).lighter(120).name(QColor.NameFormat.HexArgb)}; }}
            #dropZone {{ border: 2px dashed {accent_color}88; border-radius: 5px; padding: 10px; color: {text_color}aa; }}
            #uiPreview {{ border: none; padding: 5px; margin-top: 5px; color: {text_color}aa; }}
            
            QGroupBox {{ border: 1px solid {accent_color}66; border-radius: 5px; margin-top: 1ex; color: {accent_color}; font-weight: bold; padding: 5px; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; background-color: {bg_color_str}; }}
            
            QLabel, QCheckBox {{ color: {text_color}; font-family: "{font_family}"; font-size: {font_size}pt; font-weight: normal; }}
            QLabel b {{ font-weight: bold; color: {accent_color}; }}
            QCheckBox::indicator {{ border: 1px solid {accent_color}; border-radius: 3px; }}
            QCheckBox::indicator:checked {{ background-color: {accent_color}; }}
            
            QTextEdit, QLineEdit, QFontComboBox, QSpinBox, QComboBox {{ background-color: rgba(0,0,0,0.2); border: 1px solid {accent_color}88; border-radius: 5px; color: {text_color}; padding: 5px; font-family: "{font_family}"; font-size: {font_size}pt; }}
            
            QTextEdit:focus, QLineEdit:focus, QFontComboBox:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {accent_color}; }}
            
            QPushButton {{ background-color: {btn_bg}; color: {text_color}; border: 1px solid {accent_color}88; border-radius: 5px; padding: 5px 8px; font-family: "{font_family}"; }}
            QPushButton:hover {{ background-color: {btn_hover}; }} 
            QPushButton:pressed {{ background-color: {btn_pressed}; }}
            
            #navButton {{ text-align: left; background-color: transparent; border: 1px solid transparent; padding: 8px; }}
            #navButton:hover {{ background-color: {btn_hover}; }}
            #navButton:checked {{ background-color: {accent_color}; color: #FFFFFF; font-weight: bold; border-color: {accent_color}; }}

            #pos_button {{ padding: 6px; font-size: {font_size+2}pt; font-weight: bold; }}
            #pos_button:checked {{ background-color: {accent_color}; border-color: {text_color}; }}
            
            QSlider::groove:horizontal {{ border: 1px solid {accent_color}55; height: 3px; background: {accent_color}33; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: {text_color}; border: 1px solid {accent_color}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; }}
            
            QAbstractItemView {{
                background-color: {bg_color_str}; color: {text_color};
                border: 1px solid {accent_color}; selection-background-color: {accent_color};
                selection-color: {text_color}; padding: 4px;
            }}
        """)
        self.theme_accent_preview.setStyleSheet(f"background-color: {accent_color}; border: 1px solid {text_color}44; color: {text_color};"); self.theme_accent_preview.setText(accent_color)
        self.theme_bg_preview.setStyleSheet(f"background-color: {bg_color_str}; border: 1px solid {accent_color}; color: {text_color};"); self.theme_bg_preview.setText(bg_color_str)
        self.theme_text_preview.setStyleSheet(f"background-color: {text_color}; border: 1px solid {accent_color};"); self.theme_text_preview.setText(text_color)
        self.theme_close_button_preview.setStyleSheet(f"background-color: {close_btn_hex}; border: 1px solid {text_color}44;"); self.theme_close_button_preview.setText(close_btn_hex)
        self.adjustSize()

    def _run_update_check_in_thread(self):
        """Chạy check_for_updates trong thread riêng để không block UI."""
        status, message = update.check_for_updates()
        self.updateCheckCompleted.emit(status, message)
        
    def _on_update_check_completed(self, status, message):
        """Slot xử lý kết quả khi thread check update hoàn thành."""
        self.update_status_label.setText(message)
        if status == update.UPDATE_STATUS['AHEAD']:
            self.update_button.show()
            self.update_button.setEnabled(True)
        else:
            self.update_button.hide()

    def _on_update_button_clicked(self):
        """Slot xử lý khi người dùng nhấn nút update."""
        self.update_status_label.setText("Đang cập nhật... Vui lòng không tắt Yuuka nhé!")
        self.update_button.setEnabled(False)
        QApplication.processEvents() # Cập nhật UI ngay lập tức

        # Chạy update và restart trong thread riêng
        def update_and_restart_thread():
            update.perform_update()
            self.requestRestart.emit()

        threading.Thread(target=update_and_restart_thread, daemon=True).start()

    def _emit_changes(self, _=None):
        theme_data = {'accent_color': self.theme_accent_preview.text(), 'sub_win_bg': self.theme_bg_preview.text(), 'sub_win_text': self.theme_text_preview.text(), 'sub_win_font_family': self.font_family_combo.currentFont().family(), 'sub_win_font_size': self.font_size_spinbox.value()}
        
        hotkey_text = self.ocr_hotkey_button.text()
        if hotkey_text.startswith("Đang ghi...") or "không được hỗ trợ" in hotkey_text:
             hotkey_text = self.ocr_hotkey_button._original_text

        config_data = {
            'auto_update_enabled': self.auto_update_cb.isChecked(),
            'process_text_clipboard': self.text_clipboard_cb.isChecked(), 'process_file_clipboard': self.file_clipboard_cb.isChecked(),
            'prompt_enabled': self.prompt_enabled_cb.isChecked(), 'custom_prompt': self.custom_prompt_edit.toPlainText().strip(), 
            'theme': theme_data, 
            'sub_window_position': self.current_pos_mode, 'sub_window_spacing': self.spacing_slider.value(),
            'min_sub_win_width': self.min_sub_win_width_slider.value(), 'ui_scale': self.ui_scale_slider.value(),
            'hook_ocr_hotkey': hotkey_text,
            'gemini_model': self.gemini_model_combo.currentText()
        }
        
        close_color = QColor(self.theme_close_button_preview.text())
        if close_color.isValid(): config_data['close_button_color'] = list(close_color.getRgb()[:3])

        for param, (slider, _) in self.hook_sliders.items(): config_data[param] = slider.value()
        for param, (slider, _, scale) in self.physic_sliders.items(): config_data[param] = slider.value() * scale

        self.config_changed.emit(config_data)

    def _submit_api_key(self):
        key = self.api_key_edit.text().strip()
        if key: 
            self.api_key_status_label.setText("Đang xác thực...")
            self.api_key_status_label.setStyleSheet("color: #ccc;")
            self.apiKeySubmitted.emit(key)

    def _pick_color(self, color_type):
        is_close_btn = color_type == 'close_button'; preview_button = self.theme_close_button_preview if is_close_btn else getattr(self, f"theme_{color_type}_preview")
        initial_color = QColor(preview_button.text()); dialog = QColorDialog(self); dialog.setOption(QColorDialog.DontUseNativeDialog, True); dialog.setCurrentColor(initial_color)
        if color_type == 'bg': dialog.setOption(QColorDialog.ShowAlphaChannel, True)
        
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)
        title_bar = QWidget(dialog); title_bar.setObjectName("customTitleBar"); title_bar_layout = QHBoxLayout(title_bar); title_bar_layout.setContentsMargins(10, 5, 5, 5)
        title_label = QLabel(f"Chọn màu {color_type}", title_bar); title_label.setObjectName("customTitleLabel"); close_button = QPushButton("✕", title_bar); close_button.setObjectName("customCloseButton"); close_button.clicked.connect(dialog.reject)
        title_bar_layout.addWidget(title_label); title_bar_layout.addStretch(); title_bar_layout.addWidget(close_button)
        def mouse_press(event):
            if event.button() == Qt.LeftButton: self.drag_pos = event.globalPosition().toPoint() - dialog.pos(); event.accept()
        def mouse_move(event):
            if event.buttons() == Qt.LeftButton and self.drag_pos: dialog.move(event.globalPosition().toPoint() - self.drag_pos); event.accept()
        title_bar.mousePressEvent = mouse_press; title_bar.mouseMoveEvent = mouse_move; title_bar.mouseReleaseEvent = lambda e: setattr(self, 'drag_pos', None)
        dialog.layout().insertWidget(0, title_bar)
        
        theme_config = self.parent().user_config.get('theme', {}); accent_color = theme_config.get('accent_color', '#E98973'); bg_color_str = theme_config.get('sub_win_bg', 'rgba(30, 30, 30, 245)'); text_color = theme_config.get('sub_win_text', '#FFFFFF')
        bg_qcolor = QColor(bg_color_str); btn_bg = (bg_qcolor.lighter(130).name() if bg_qcolor.lightnessF() < 0.5 else bg_qcolor.darker(115).name()); btn_hover = (bg_qcolor.lighter(160).name() if bg_qcolor.lightnessF() < 0.5 else bg_qcolor.darker(130).name())
        dialog.setStyleSheet(f""" QDialog {{ background-color: {bg_color_str}; border: 1px solid {accent_color}; border-radius: 8px; }} #customTitleBar {{ background: transparent; }} #customTitleLabel {{ color: {text_color}; font-weight: bold; }} #customCloseButton {{ font-family: "Segoe UI Symbol"; font-size: 14px; color: {text_color}; background: transparent; border: none; padding: 0px 5px; min-width: 20px; max-width: 20px; }} #customCloseButton:hover {{ background-color: #E81123; color: white; border-radius: 4px; }} QColorDialog, QColorDialog * {{ color: {text_color}; }} QColorDialog #qt_color_patch, QColorDialog #qt_color_new_patch, QColorDialog #qt_color_luma, QColorDialog #qt_color_alpha {{ border: 1px solid {text_color}44; border-radius: 4px; }} QColorDialog QLabel, QColorDialog QRadioButton {{ color: {text_color}; }} QColorDialog QSpinBox, QColorDialog QLineEdit {{ color: {text_color}; background-color: rgba(0,0,0,0.2); border: 1px solid {accent_color}88; border-radius: 4px; padding: 2px; }} QColorDialog QPushButton {{ color: {text_color}; background-color: {btn_bg}; border: 1px solid {accent_color}88; border-radius: 4px; padding: 5px 10px; min-width: 60px; }} QColorDialog QPushButton:hover {{ background-color: {btn_hover}; }} QColorDialog QPushButton:default {{ border: 2px solid {accent_color}; }} """)
        
        if dialog.exec():
            color = dialog.currentColor()
            if color.isValid():
                new_color_str = color.name(QColor.NameFormat.HexArgb) if color.alpha() < 255 and color_type == 'bg' else color.name()
                preview_button.setText(new_color_str); self._emit_changes()

    def load_config(self, config_data, app_configs, api_key_info, base_pixmap):
        for widget in self.findChildren(QWidget): widget.blockSignals(True)
        self.auto_update_cb.setChecked(config_data.get('auto_update_enabled', True))
        self.text_clipboard_cb.setChecked(config_data.get('process_text_clipboard', False)); self.file_clipboard_cb.setChecked(config_data.get('process_file_clipboard', True))
        self.prompt_enabled_cb.setChecked(config_data.get('prompt_enabled', False)); self.custom_prompt_edit.setText(config_data.get('custom_prompt', ''))
        theme_config = config_data.get('theme', {}); self.theme_accent_preview.setText(theme_config.get('accent_color', '#E98973')); self.theme_bg_preview.setText(theme_config.get('sub_win_bg', 'rgba(30,30,30,245)')); self.theme_text_preview.setText(theme_config.get('sub_win_text', '#FFFFFF'))
        font = QFont(); font.setFamily(theme_config.get('sub_win_font_family', 'Segoe UI')); self.font_family_combo.setCurrentFont(font); self.font_size_spinbox.setValue(theme_config.get('sub_win_font_size', 10))
        
        self.current_pos_mode = config_data.get('sub_window_position', 'auto'); self.pos_button_group.button(({'up':0, 'down':1, 'left':2, 'right':3, 'auto':4}).get(self.current_pos_mode, 4)).setChecked(True)
        spacing = config_data.get('sub_window_spacing', 5); self.spacing_slider.setValue(spacing); self.spacing_value_label.setText(f"{spacing} px")
        min_width = config_data.get('min_sub_win_width', 200); self.min_sub_win_width_slider.setValue(min_width); self.min_sub_win_width_label.setText(f"{min_width} px")
        ui_scale = config_data.get('ui_scale', 100); self.ui_scale_slider.setValue(ui_scale); self.ui_scale_label.setText(f"{ui_scale}%")
        
        for param, (slider, label) in self.hook_sliders.items(): val = config_data.get(param, app_configs.get(param, 0)); slider.setValue(val); label.setText(str(val))
        for param, (slider, label, scale) in self.physic_sliders.items(): val = config_data.get(param, app_configs.get(param, 0.1)); slider.setValue(int(val / scale)); label.setText(f"{val:.2f}")

        hotkey = config_data.get('hook_ocr_hotkey', app_configs.get('HOOK_OCR_HOTKEY', 'middle')); self.ocr_hotkey_button.set_display_text(hotkey)

        self.update_api_key_status(api_key_info.get('key'), api_key_info.get('verified', False), api_key_info.get('models', []))
        if config_data.get('gemini_model'):
            self.gemini_model_combo.setCurrentText(config_data.get('gemini_model'))

        self.apply_stylesheet(theme_config, config_data, app_configs)
        self.update_ui_preview(base_pixmap)
        for widget in self.findChildren(QWidget): widget.blockSignals(False)
        self.adjustSize()
        
        self.update_status_label.setText("Đang kiểm tra update...")
        self.update_button.hide()
        threading.Thread(target=self._run_update_check_in_thread, daemon=True).start()

    def update_ui_preview(self, pixmap: QPixmap):
        if not pixmap or pixmap.isNull(): self.ui_preview_label.setText("Không có giao diện"); return
        preview_width = self.ui_preview_label.width() - 10
        if preview_width > 10:
            scaled_pixmap = pixmap.scaledToWidth(preview_width, Qt.SmoothTransformation)
            self.ui_preview_label.setPixmap(scaled_pixmap); self.ui_preview_label.setText("") 
        else: self.ui_preview_label.setText("Giao diện hiện tại")

    def update_api_key_status(self, key, is_verified, models=[]):
        self.gemini_model_combo.blockSignals(True)
        self.gemini_model_combo.clear()
        if is_verified:
            self.api_key_edit.setText(key)
            self.api_key_status_label.setText("Key hợp lệ và đã được lưu."); self.api_key_status_label.setStyleSheet("color: #77cc77;")
            if models:
                self.gemini_model_combo.addItems(models)
                self.gemini_model_combo.setEnabled(True)
            else:
                self.gemini_model_combo.addItem("Không tìm thấy model"); self.gemini_model_combo.setEnabled(False)
        elif key:
            self.api_key_edit.setText(key)
            self.api_key_status_label.setText("Key không hợp lệ hoặc đã hết hạn."); self.api_key_status_label.setStyleSheet("color: #ff7777;")
            self.gemini_model_combo.setEnabled(False)
        else:
            self.api_key_edit.clear()
            self.api_key_status_label.setText("Chưa có API key."); self.api_key_status_label.setStyleSheet("color: #aaa;")
            self.gemini_model_combo.setEnabled(False)
        self.gemini_model_combo.blockSignals(False)
        
    def _on_pos_button_clicked(self, button): self.current_pos_mode = (['up', 'down', 'left', 'right', 'auto'])[self.pos_button_group.id(button)]; self._emit_changes()
    def _on_spacing_changed(self, value): self.spacing_value_label.setText(f"{value} px"); self._emit_changes()
    def _on_min_width_changed(self, value): self.min_sub_win_width_label.setText(f"{value} px"); self._emit_changes()
    def _on_ui_scale_changed(self, value): self.ui_scale_label.setText(f"{value}%"); self._emit_changes()
    
    def _reset_hook_sliders(self):
        app_configs = self.parent().app_configs
        for param, (slider, _) in self.hook_sliders.items(): slider.setValue(app_configs.get(param, 0)); self._emit_changes()
    
    def _reset_physic_sliders(self):
        app_configs = self.parent().app_configs
        for param, (slider, _, scale) in self.physic_sliders.items(): slider.setValue(int(app_configs.get(param, 0.1) / scale)); self._emit_changes()

    def _on_hotkey_captured(self, hotkey: str): self.ocr_hotkey_button.set_display_text(hotkey); self._emit_changes()

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile() and url.toLocalFile().lower().endswith('.png'): event.acceptProposedAction()
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile(): self.uiImageChanged.emit(url.toLocalFile())
    
    def eventFilter(self, watched, event):
        if watched == self.ui_drop_zone and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                filepath, _ = QFileDialog.getOpenFileName(self, "Chọn file giao diện", "", "Image Files (*.png)")
                if filepath: self.uiImageChanged.emit(filepath)
                return True
        return super().eventFilter(watched, event)
        
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.hide()
        super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent):
        if self.ocr_hotkey_button._is_capturing: event.accept(); return
        if event.button() == Qt.RightButton: self.hide(); event.accept(); return
        super().mousePressEvent(event)

    def hideEvent(self, event):
        self.ocr_hotkey_button.stop_capture(); super().hideEvent(event)

class SnippingWidget(QWidget):
    snipping_finished = Signal(QRect); snipping_cancelled = Signal()
    def __init__(self, parent=None):
        super().__init__(parent); self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool); self.setAttribute(Qt.WA_TranslucentBackground); self.setCursor(Qt.CrossCursor)
        all_screens_geometry = QRect(); [all_screens_geometry := all_screens_geometry.united(s.geometry()) for s in QApplication.screens()]
        self.setGeometry(all_screens_geometry); self.start_point, self.end_point = QPoint(), QPoint(); self.is_snipping = False; self.color = QColor("#E98973")
    def set_color(self, color_str): self.color = QColor(color_str); self.update()
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: self.start_point = event.position().toPoint(); self.end_point = self.start_point; self.is_snipping = True; self.update()
    def mouseMoveEvent(self, event):
        if self.is_snipping: self.end_point = event.position().toPoint(); self.update()
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.is_snipping: self.is_snipping = False; self.snipping_finished.emit(QRect(self.start_point, self.end_point).normalized())
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape: self.snipping_cancelled.emit(); self.close()
    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing); painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
        if self.is_snipping:
            selection_rect = QRect(self.start_point, self.end_point).normalized()
            painter.setCompositionMode(QPainter.CompositionMode_Clear); painter.fillRect(selection_rect, Qt.transparent)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver); pen = QPen(self.color, 2, Qt.SolidLine); painter.setPen(pen); painter.drawRect(selection_rect)

class SelectionOverlayWidget(PhysicsMovableWidget):
    def __init__(self, parent=None, physics_config=None):
        super().__init__(parent, physics_config); self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.WindowTransparentForInput); self.setAttribute(Qt.WA_TranslucentBackground); self.setAttribute(Qt.WA_TransparentForMouseEvents); self.color = QColor("#E98973")
    def set_color(self, color_str): self.color = QColor(color_str); self.update()
    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing); pen = QPen(self.color, 2, Qt.DashLine); pen.setDashPattern([4, 4]); painter.setPen(pen); painter.drawRect(self.rect().adjusted(1, 1, -1, -1))