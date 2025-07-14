# core/ui/config_window.py
import os
import threading
from PySide6.QtWidgets import (QWidget, QApplication, QCheckBox, QLabel, QFrame, 
                               QLineEdit, QPushButton, QHBoxLayout,
                               QFontComboBox, QSpinBox, QSlider, QButtonGroup,
                               QFileDialog, QStackedWidget, QComboBox, QVBoxLayout, QTextEdit)
from PySide6.QtGui import QColor, QFont, QDragEnterEvent, QMouseEvent, QKeyEvent, QPixmap, QHideEvent, QShowEvent, QTextCursor
from PySide6.QtCore import Qt, Signal, QEvent, QTimer, QElapsedTimer, QPointF

from core.physics import PhysicsMovableWidget
from core import update
from core.logging import Logger

from .themed_color_picker import ThemedColorDialog
from .config_tabs.system_tab import create_system_tab
from .config_tabs.theme_tab import create_theme_tab
from .config_tabs.layout_physics_tab import create_layout_physics_tab
from .config_tabs.hooking_tab import create_hooking_tab
from .config_tabs.status_tab import create_status_tab
from .config_tabs.log_tab import create_log_tab
from .config_tabs.console_tab import create_console_tab


class ConfigWindow(PhysicsMovableWidget):
    config_changed = Signal(dict)
    apiKeySubmitted = Signal(str)
    uiImageChanged = Signal(str)
    requestRestart = Signal()
    updateCheckCompleted = Signal(int, str, object)
    window_hidden = Signal()

    def __init__(self, parent=None, physics_config=None, logger: Logger = None):
        super().__init__(parent, physics_config)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.logger = logger; self.constrain_to_screen = False; self.setMinimumWidth(800)
        self.drag_pos = None; self.current_pos_mode = 'auto'
        self.container = QWidget(self); self.container.setObjectName("container")
        self.session_timer = None
        self.color_picker_dialog = None # YUUKA: Thêm để quản lý dialog color picker

        self._setup_ui()
        self.apply_stylesheet({}, {}, {})
        self._connect_signals()

    def append_to_console_display(self, text: str):
        if self.console_output.property("isPlaceholder") is True:
            self.console_output.clear(); self.console_output.setProperty("isPlaceholder", False)
        self.console_output.moveCursor(QTextCursor.MoveOperation.End)
        self.console_output.insertPlainText(text)
        self.console_output.moveCursor(QTextCursor.MoveOperation.End)

    def _setup_ui(self):
        main_layout = QHBoxLayout(self.container)
        main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        self.stacked_widget = QStackedWidget()
        nav_widget = self._create_nav_bar()
        system_tab = create_system_tab(self); theme_tab = create_theme_tab(self)
        layout_physics_tab = create_layout_physics_tab(self); hooking_tab = create_hooking_tab(self)
        status_tab = create_status_tab(self); log_tab = create_log_tab(self)
        console_tab = create_console_tab(self)
        self.stacked_widget.addWidget(system_tab); self.stacked_widget.addWidget(theme_tab)
        self.stacked_widget.addWidget(layout_physics_tab); self.stacked_widget.addWidget(hooking_tab)
        self.stacked_widget.addWidget(status_tab); self.stacked_widget.addWidget(log_tab)
        self.stacked_widget.addWidget(console_tab)
        main_layout.addWidget(nav_widget); main_layout.addWidget(self._create_v_line())
        main_layout.addWidget(self.stacked_widget, stretch=1)
        root_layout = QVBoxLayout(self); root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.addWidget(self.container); self.setLayout(root_layout)
        self.nav_button_group.button(0).setChecked(True)
        self.console_output.setText("Console output will appear here when this window is open.\n")
        self.console_output.setProperty("isPlaceholder", True)

    def _create_nav_bar(self):
        nav_widget = QWidget(); nav_widget.setObjectName("navBar")
        nav_layout = QVBoxLayout(nav_widget); nav_layout.setContentsMargins(15, 10, 15, 10); nav_layout.setSpacing(5)
        self.nav_button_group = QButtonGroup(self); self.nav_button_group.setExclusive(True)
        tab_names = ["Hệ thống", "Giao diện", "Bố cục & Vật lý", "Hooking", "Trạng thái", "Log", "Console"]
        for i, name in enumerate(tab_names):
            button = QPushButton(name); button.setObjectName("navButton"); button.setCheckable(True)
            nav_layout.addWidget(button); self.nav_button_group.addButton(button, i)
        self.nav_button_group.idClicked.connect(self.stacked_widget.setCurrentIndex)
        nav_layout.addStretch()
        self.exit_button = QPushButton("Exit"); self.exit_button.setObjectName("exitButton")
        self.exit_button.clicked.connect(QApplication.instance().quit)
        nav_layout.addWidget(self.exit_button); nav_widget.setLayout(nav_layout)
        return nav_widget

    def _create_tab_content_widget(self, left_layout, right_layout):
        tab_widget = QWidget(); tab_layout = QHBoxLayout(tab_widget)
        tab_layout.setContentsMargins(15, 10, 15, 10); tab_layout.setSpacing(15)
        tab_layout.addLayout(left_layout, stretch=1); tab_layout.addWidget(self._create_v_line())
        tab_layout.addLayout(right_layout, stretch=1)
        return tab_widget

    def _connect_signals(self):
        self.auto_update_cb.stateChanged.connect(self._emit_changes); self.start_with_system_cb.stateChanged.connect(self._emit_changes)
        self.text_clipboard_cb.stateChanged.connect(self._emit_changes); self.file_clipboard_cb.stateChanged.connect(self._emit_changes)
        self.snipping_clipboard_cb.stateChanged.connect(self._emit_changes) # <<< YUUKA: THÊM MỚI
        self.prompt_enabled_cb.stateChanged.connect(self._emit_changes); self.custom_prompt_edit.textChanged.connect(self._emit_changes)
        self.gemini_model_combo.currentIndexChanged.connect(self._emit_changes); self.font_family_combo.currentFontChanged.connect(self._emit_changes)
        self.font_size_spinbox.valueChanged.connect(self._emit_changes); self.update_button.clicked.connect(self._on_update_button_clicked)
        self.api_key_save_button.clicked.connect(self._submit_api_key)
        self.theme_accent_pick_button.clicked.connect(lambda: self._pick_color('accent')); self.theme_bg_pick_button.clicked.connect(lambda: self._pick_color('bg', show_alpha=True))
        self.theme_text_pick_button.clicked.connect(lambda: self._pick_color('text')); self.theme_close_button_pick_button.clicked.connect(lambda: self._pick_color('close_button'))
        self.pos_button_group.buttonClicked.connect(self._on_pos_button_clicked); self.physic_reset_button.clicked.connect(self._reset_physic_sliders)
        self.hook_reset_button.clicked.connect(self._reset_hook_sliders); self.ocr_hotkey_button.hotkey_captured.connect(self._on_hotkey_captured)
        self.clear_outputs_button.clicked.connect(lambda: self._clear_log_and_reload("recent_outputs")); self.clear_prompts_button.clicked.connect(lambda: self._clear_log_and_reload("recent_prompts"))
        self.spacing_slider.valueChanged.connect(lambda value: self.spacing_value_label.setText(f"{value} px")); self.spacing_slider.sliderReleased.connect(self._emit_changes)
        self.min_sub_win_width_slider.valueChanged.connect(lambda value: self.min_sub_win_width_label.setText(f"{value} px")); self.min_sub_win_width_slider.sliderReleased.connect(self._emit_changes)
        self.ui_scale_slider.valueChanged.connect(lambda value: self.ui_scale_label.setText(f"{value}%")); self.ui_scale_slider.sliderReleased.connect(self._emit_changes)
        for param, (slider, label, scale) in self.physic_sliders.items():
            slider.valueChanged.connect(lambda val, l=label, s=scale: l.setText(f"{val*s:.2f}")); slider.sliderReleased.connect(self._emit_changes)
        for param, (slider, label) in self.hook_sliders.items():
            slider.valueChanged.connect(lambda val, l=label: l.setText(str(val))); slider.sliderReleased.connect(self._emit_changes)
        self.updateCheckCompleted.connect(self._on_update_check_completed); self.ui_drop_zone.installEventFilter(self)

    def _create_line(self): line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setFrameShadow(QFrame.Shadow.Sunken); line.setObjectName("separator_line"); return line
    def _create_v_line(self): line = QFrame(); line.setFrameShape(QFrame.Shape.VLine); line.setFrameShadow(QFrame.Shadow.Sunken); line.setObjectName("separator_line"); return line

    def apply_stylesheet(self, theme_config, user_config, app_configs):
        accent_color = theme_config.get('accent_color', '#E98973'); bg_color_str = theme_config.get('sub_win_bg', 'rgba(30,30,30,245)')
        text_color = theme_config.get('sub_win_text', '#FFFFFF'); font_family = theme_config.get('sub_win_font_family', 'Segoe UI')
        font_size = theme_config.get('sub_win_font_size', 10); default_close_color = app_configs.get("CLOSE_BUTTON_COLOR_RGB", [233, 115, 158])
        close_btn_rgb = user_config.get('close_button_color', default_close_color); close_btn_qcolor = QColor(*close_btn_rgb); close_btn_hex = close_btn_qcolor.name() 
        bg_qcolor = QColor(bg_color_str); nav_bg_color = bg_qcolor.lighter(110).name() if bg_qcolor.lightnessF() < 0.5 else bg_qcolor.darker(105).name()
        console_bg_color = QColor(bg_color_str).darker(150).name()
        
        self.container.setStyleSheet(f"""
            QToolTip {{ background-color: {nav_bg_color}; color: {text_color}; border: 1px solid {accent_color}; border-radius: 4px; padding: 5px; }}
            #container {{ background-color: {bg_color_str}; border: 1px solid {accent_color}; border-radius: 8px; }}
            #navBar {{ background-color: {nav_bg_color}; border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
            #separator_line {{ color: {QColor(accent_color).lighter(120).name(QColor.NameFormat.HexArgb)}; }}
            #dropZone {{ border: 2px dashed {accent_color}88; border-radius: 5px; padding: 10px; color: {text_color}aa; }}
            #uiPreview {{ border: none; padding: 5px; margin-top: 5px; color: {text_color}aa; }}
            #updateDetailsLabel, #status_display {{ background-color: rgba(0,0,0,0.15); border: 1px solid {accent_color}44; border-radius: 5px; padding: 8px; margin-top: 5px; color: {text_color}cc; text-align: left; }}
            #logContainer {{ background-color: rgba(0,0,0,0.1); border-radius: 5px; padding: 2px; }}
            QGroupBox {{ border: 1px solid {accent_color}66; border-radius: 5px; margin-top: 1ex; color: {text_color}; font-weight: bold; padding: 5px; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top center; padding: 0 3px; background-color: {bg_color_str}; }}
            QLabel, QCheckBox {{ color: {text_color}; font-family: "{font_family}"; font-size: {font_size}pt; font-weight: normal; }}
            QLabel b {{ font-weight: bold; color: {accent_color}; }}
            QCheckBox::indicator {{ border: 1px solid {accent_color}; border-radius: 3px; }}
            QCheckBox::indicator:checked {{ background-color: {accent_color}; }}
            QTextEdit, QLineEdit, QFontComboBox, QSpinBox, QComboBox, QScrollArea {{ background-color: transparent; border: 1px solid {accent_color}88; border-radius: 5px; color: {text_color}; padding: 5px; font-family: "{font_family}"; font-size: {font_size}pt; }}
            QTextEdit, QLineEdit, QFontComboBox, QSpinBox, QComboBox {{ background-color: rgba(0,0,0,0.2); }}
            QScrollArea {{ background-color: transparent; border: none; }}
            QTextEdit:focus, QLineEdit:focus, QFontComboBox:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {accent_color}; }}
            QPushButton {{ background-color: rgba(255,255,255,0.1); color: {text_color}; border: 1px solid {accent_color}88; border-radius: 5px; padding: 5px 8px; font-family: "{font_family}"; }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.2); }} 
            QPushButton:pressed {{ background-color: rgba(255,255,255,0.05); }}
            #logEntryButton {{ background-color: transparent; border: none; padding: 8px; color: {text_color}dd; text-align: left; }}
            #logEntryButton:hover {{ background-color: rgba(255,255,255,0.08); }}
            #navButton {{ text-align: left; background-color: transparent; border: 1px solid transparent; padding: 8px 13px; }}
            #navButton:hover {{ background-color: rgba(255,255,255,0.1); }}
            #navButton:checked {{ background-color: {accent_color}; color: #FFFFFF; font-weight: bold; border-color: {accent_color}; }}
            #exitButton {{ background-color: {close_btn_hex}; color: white; border: none; }}
            #exitButton:hover {{ background-color: {close_btn_qcolor.lighter(120).name()}; }}
            #pos_button {{ padding: 6px; font-size: {font_size+2}pt; font-weight: bold; }}
            #pos_button:checked {{ background-color: {accent_color}; border-color: {text_color}; }}
            QSlider::groove:horizontal {{ border: 1px solid {accent_color}55; height: 3px; background: {accent_color}33; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: {text_color}; border: 1px solid {accent_color}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px; }}
            QAbstractItemView {{ background-color: {bg_color_str}; color: {text_color}; border: 1px solid {accent_color}; selection-background-color: {accent_color}; selection-color: {text_color}; padding: 4px; }}
            #console_output {{ font-family: 'Consolas', 'Courier New', monospace; font-size: 9pt; background-color: {console_bg_color}; border: 1px solid {accent_color}88; color: {text_color}; }}
            QScrollBar:vertical {{ border: none; background-color: {bg_color_str}; width: 10px; margin: 0px 0px 0px 0px; border-radius: 5px;}}
            QScrollBar::handle:vertical {{ background: {accent_color}88; min-height: 20px; border-radius: 5px; }}
            QScrollBar::handle:vertical:hover {{ background: {accent_color}bb; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
            QScrollBar:horizontal {{ border: none; background-color: {bg_color_str}; height: 10px; margin: 0px 0px 0px 0px; border-radius: 5px;}}
            QScrollBar::handle:horizontal {{ background: {accent_color}88; min-width: 20px; border-radius: 5px; }}
            QScrollBar::handle:horizontal:hover {{ background: {accent_color}bb; }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        """)
        self.theme_accent_preview.setStyleSheet(f"background-color: {accent_color}; border: 1px solid {text_color}44; color: {text_color};"); self.theme_accent_preview.setText(accent_color)
        self.theme_bg_preview.setStyleSheet(f"background-color: {bg_color_str}; border: 1px solid {accent_color}; color: {text_color};"); self.theme_bg_preview.setText(bg_color_str)
        self.theme_text_preview.setStyleSheet(f"background-color: {text_color}; border: 1px solid {accent_color};"); self.theme_text_preview.setText(text_color)
        self.theme_close_button_preview.setStyleSheet(f"background-color: {close_btn_hex}; border: 1px solid {text_color}44;"); self.theme_close_button_preview.setText(close_btn_hex)
        self.adjustSize()

    def _run_update_check_in_thread(self): status, message, details, _ = update.check_for_updates(); self.updateCheckCompleted.emit(status, message, details)
    def _on_update_check_completed(self, status, message, details):
        self.update_status_label.setText(message)
        self.update_button.hide()
        
        # YUUKA: Chỉ cần ẩn/hiện QTextEdit là đủ
        self.update_details_label.hide()
        self.update_details_label.clear() # Dùng clear() cho QTextEdit

        if details:
            commit_msg = details.get('message', 'N/A')
            commit_date = details.get('date', 'N/A')
            title = "<b>Nội dung cập nhật:</b>"
            if status == update.UPDATE_STATUS['UP_TO_DATE']: 
                title = "<b>Thông tin phiên bản hiện tại:</b>"
            
            # YUUKA FIX: Vẫn giữ logic replace \n bằng <br/>
            commit_msg = commit_msg.replace(os.linesep, '<br/>').replace('\n', '<br/>')
            details_text = f"""<p>{title}<br/>{commit_msg}</p><p><b>Thời gian:</b> {commit_date}</p>"""
            
            # YUUKA FIX: Dùng setHtml() thay vì setText() cho QTextEdit
            self.update_details_label.setHtml(details_text)
            self.update_details_label.show()

        if status == update.UPDATE_STATUS['AHEAD']: 
            self.update_button.show()
            self.update_button.setEnabled(True)

    def _on_update_button_clicked(self):
        self.update_status_label.setText("Đang cập nhật... Vui lòng không tắt Yuuka nhé!")
        self.update_button.setEnabled(False)
        # YUUKA: Ẩn QTextEdit khi đang cập nhật
        self.update_details_label.hide()
        QApplication.processEvents()
        def update_and_restart_thread(): 
            update.perform_update()
            self.requestRestart.emit()
        threading.Thread(target=update_and_restart_thread, daemon=True).start()

    def _emit_changes(self, _=None):
        theme_data = {'accent_color': self.theme_accent_preview.text(), 'sub_win_bg': self.theme_bg_preview.text(), 'sub_win_text': self.theme_text_preview.text(), 'sub_win_font_family': self.font_family_combo.currentFont().family(), 'sub_win_font_size': self.font_size_spinbox.value()}
        hotkey_text = self.ocr_hotkey_button.text()
        if hotkey_text.startswith("Đang ghi...") or "không được hỗ trợ" in hotkey_text: hotkey_text = self.ocr_hotkey_button._original_text
        config_data = {
            'auto_update_enabled': self.auto_update_cb.isChecked(), 'start_with_system': self.start_with_system_cb.isChecked(), 
            'process_text_clipboard': self.text_clipboard_cb.isChecked(), 'process_file_clipboard': self.file_clipboard_cb.isChecked(), 
            'process_snipping_clipboard': self.snipping_clipboard_cb.isChecked(), # <<< YUUKA: THÊM MỚI
            'prompt_enabled': self.prompt_enabled_cb.isChecked(), 'custom_prompt': self.custom_prompt_edit.toPlainText().strip(), 
            'theme': theme_data, 'sub_window_position': self.current_pos_mode, 'sub_window_spacing': self.spacing_slider.value(), 
            'min_sub_win_width': self.min_sub_win_width_slider.value(), 'ui_scale': self.ui_scale_slider.value(), 
            'hook_ocr_hotkey': hotkey_text, 'gemini_model': self.gemini_model_combo.currentText()
        }
        close_color = QColor(self.theme_close_button_preview.text());
        if close_color.isValid(): config_data['close_button_color'] = list(close_color.getRgb()[:3])
        for param, (slider, _) in self.hook_sliders.items(): config_data[param] = slider.value()
        for param, (slider, _, scale) in self.physic_sliders.items(): config_data[param] = slider.value() * scale
        self.config_changed.emit(config_data)

    def _submit_api_key(self):
        key = self.api_key_edit.text().strip()
        if key: self.api_key_status_label.setText("Đang xác thực..."); self.api_key_status_label.setStyleSheet("color: #ccc;"); self.apiKeySubmitted.emit(key)

    # YUUKA: Cập nhật lại hoàn toàn logic pick color
    def _pick_color(self, color_type, show_alpha=False):
        if self.color_picker_dialog and self.color_picker_dialog.isVisible():
            self.color_picker_dialog.close()
            
        preview_button = getattr(self, f"theme_{'close_button' if color_type == 'close_button' else color_type}_preview")
        initial_color = QColor(preview_button.text())
        current_theme_config = {'accent_color': self.theme_accent_preview.text(), 'sub_win_bg': self.theme_bg_preview.text(), 'sub_win_text': self.theme_text_preview.text()}
        
        self.color_picker_dialog = ThemedColorDialog(initial_color, show_alpha, current_theme_config, self)
        
        # Kết nối signal từ dialog picker tới một slot để xử lý kết quả
        self.color_picker_dialog.color_accepted.connect(
            lambda color: self._on_color_picked_and_accepted(color, color_type)
        )
        self.color_picker_dialog.show()

    def _on_color_picked_and_accepted(self, new_color, color_type):
        if new_color and new_color.isValid():
            preview_button = getattr(self, f"theme_{'close_button' if color_type == 'close_button' else color_type}_preview")
            show_alpha = color_type == 'bg'
            new_color_str = new_color.name(QColor.NameFormat.HexArgb) if new_color.alpha() < 255 and show_alpha else new_color.name()
            preview_button.setText(new_color_str)
            self._emit_changes()
        
        self.color_picker_dialog = None


    def load_config(self, config_data, app_configs, api_key_info, base_pixmap, log_data, session_timer: QElapsedTimer):
        for widget in self.findChildren(QWidget): widget.blockSignals(True)
        self.session_timer = session_timer
        self.auto_update_cb.setChecked(config_data.get('auto_update_enabled', True))
        self.start_with_system_cb.setChecked(config_data.get('start_with_system', False))
        self.text_clipboard_cb.setChecked(config_data.get('process_text_clipboard', False))
        self.file_clipboard_cb.setChecked(config_data.get('process_file_clipboard', True))
        self.snipping_clipboard_cb.setChecked(config_data.get('process_snipping_clipboard', True)) # <<< YUUKA: THÊM MỚI
        self.prompt_enabled_cb.setChecked(config_data.get('prompt_enabled', False))
        self.custom_prompt_edit.setText(config_data.get('custom_prompt', ''))
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
        if config_data.get('gemini_model'): self.gemini_model_combo.setCurrentText(config_data.get('gemini_model'))
        self.apply_stylesheet(theme_config, config_data, app_configs); self._update_log_display(log_data); self.update_ui_preview(base_pixmap)
        for widget in self.findChildren(QWidget): widget.blockSignals(False)
        self.adjustSize()
        self.update_status_label.setText("Đang kiểm tra update...")
        self.update_button.hide()
        # YUUKA: Chỉ cần ẩn QTextEdit
        self.update_details_label.hide()
        threading.Thread(target=self._run_update_check_in_thread, daemon=True).start()

    def _update_log_display(self, log_data):
        for layout_name in ['output_layout', 'prompt_layout']:
            layout = self.log_widgets[layout_name]
            while layout.count():
                child = layout.takeAt(0)
                if child.widget(): child.widget().deleteLater()
        for output in log_data.get('recent_outputs', []): self.log_widgets['create_entry_func'](output, self.log_widgets['output_layout'], self)
        for prompt in log_data.get('recent_prompts', []): self.log_widgets['create_entry_func'](prompt, self.log_widgets['prompt_layout'], self)
        api_calls = log_data.get('api_calls', {}); runtime = log_data.get('app_runtime', {}); sources = log_data.get('source_stats', {})
        today_str = runtime.get('today_seconds', {}).get('date', 'N/A'); today_seconds = runtime.get('today_seconds', {}).get('seconds', 0)
        def format_time(seconds): m, s = divmod(seconds, 60); h, m = divmod(m, 60); return f"{int(h)}h {int(m)}m {int(s)}s"
        session_seconds = self.session_timer.elapsed() / 1000 if self.session_timer else 0
        model_stats = api_calls.get('by_model', {}); model_lines = [f" • {k}: {v}" for k, v in model_stats.items()]; model_details = "<br/>".join(model_lines) if model_lines else "Chưa có"
        status_text = (f"<b>Tổng thời gian chạy:</b> {format_time(runtime.get('total_seconds', 0))}<br/><b>Thời gian hôm nay ({today_str}):</b> {format_time(today_seconds)}<br/><b>Thời gian phiên này:</b> {format_time(session_seconds)}<br/><br/><b>Tổng API Calls:</b> {api_calls.get('total', 0)}<br/><b>Theo model:</b><br/>{model_details}<br/><br/><b>Thống kê nguồn:</b><br/> • Text Clipboard: {sources.get('text_clipboard', 0)} | Image Clipboard: {sources.get('image_clipboard', 0)}<br/> • File Clipboard: {sources.get('file_clipboard', 0)} | Hooking OCR: {sources.get('hooked_ocr', 0)}<br/> • File Drop: {', '.join([f'{k}: {v}' for k, v in sources.get('file_drop', {}).items()]) if sources.get('file_drop') else 'Chưa có'}")
        if hasattr(self, 'status_display'): self.status_display.setText(status_text)

    def _clear_log_and_reload(self, section_name):
        if self.logger: self.logger.clear_log_section(section_name); self._update_log_display(self.logger.get_logs())

    def update_ui_preview(self, pixmap: QPixmap):
        if not pixmap or pixmap.isNull(): self.ui_preview_label.setText("Không có giao diện"); return
        preview_width = self.ui_preview_label.width() - 10
        if preview_width > 10: self.ui_preview_label.setPixmap(pixmap.scaledToWidth(preview_width, Qt.SmoothTransformation)); self.ui_preview_label.setText("") 
        else: self.ui_preview_label.setText("Giao diện hiện tại")

    def update_api_key_status(self, key, is_verified, models=[]):
        self.gemini_model_combo.blockSignals(True); self.gemini_model_combo.clear()
        if is_verified:
            self.api_key_edit.setText(key); self.api_key_status_label.setText("Key hợp lệ và đã được lưu."); self.api_key_status_label.setStyleSheet("color: #77cc77;")
            if models: self.gemini_model_combo.addItems(models); self.gemini_model_combo.setEnabled(True)
            else: self.gemini_model_combo.addItem("Không tìm thấy model"); self.gemini_model_combo.setEnabled(False)
        elif key: self.api_key_edit.setText(key); self.api_key_status_label.setText("Key không hợp lệ hoặc đã hết hạn."); self.api_key_status_label.setStyleSheet("color: #ff7777;"); self.gemini_model_combo.setEnabled(False)
        else: self.api_key_edit.clear(); self.api_key_status_label.setText("Chưa có API key."); self.api_key_status_label.setStyleSheet("color: #aaa;"); self.gemini_model_combo.setEnabled(False)
        self.gemini_model_combo.blockSignals(False)
        
    def _on_pos_button_clicked(self, button): self.current_pos_mode = (['up', 'down', 'left', 'right', 'auto'])[self.pos_button_group.id(button)]; self._emit_changes()
    def _on_hotkey_captured(self, hotkey: str): self.ocr_hotkey_button.set_display_text(hotkey); self._emit_changes()
    def _reset_hook_sliders(self): app_configs = self.parent().app_configs; [slider.setValue(app_configs.get(param, 0)) for param, (slider, _) in self.hook_sliders.items()]; self._emit_changes()
    def _reset_physic_sliders(self): app_configs = self.parent().app_configs; [slider.setValue(int(app_configs.get(param, 0.1) / scale)) for param, (slider, _, scale) in self.physic_sliders.items()]; self._emit_changes()
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls(): url = event.mimeData().urls()[0]; (url.isLocalFile() and url.toLocalFile().lower().endswith('.png')) and event.acceptProposedAction()
    def dropEvent(self, event):
        if event.mimeData().hasUrls(): url = event.mimeData().urls()[0]; url.isLocalFile() and self.uiImageChanged.emit(url.toLocalFile())
    def eventFilter(self, watched, event):
        if watched == self.ui_drop_zone and event.type() == QEvent.MouseButtonPress:
            if event.button() == Qt.LeftButton: filepath, _ = QFileDialog.getOpenFileName(self, "Chọn file giao diện", "", "Image Files (*.png)"); filepath and self.uiImageChanged.emit(filepath); return True
        return super().eventFilter(watched, event)
    def keyPressEvent(self, event): (event.key() == Qt.Key_Escape and self.hide()); super().keyPressEvent(event)
    def mousePressEvent(self, event: QMouseEvent):
        if self.ocr_hotkey_button._is_capturing: event.accept(); return
        if event.button() == Qt.RightButton: self.hide(); event.accept(); return
        if event.button() == Qt.LeftButton: self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); self.velocity_f = QPointF(0, 0); event.accept()
        else: super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self.drag_pos is not None: self.set_animated_target(event.globalPosition().toPoint() - self.drag_pos); event.accept()
        else: super().mouseMoveEvent(event)
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton: self.drag_pos = None
        super().mouseReleaseEvent(event)
    def showEvent(self, event: QShowEvent): super().showEvent(event)
    def hideEvent(self, event: QHideEvent):
        if self.color_picker_dialog: self.color_picker_dialog.close()
        self.ocr_hotkey_button.stop_capture(); self.window_hidden.emit(); super().hideEvent(event)
    def closeEvent(self, event): super().closeEvent(event)