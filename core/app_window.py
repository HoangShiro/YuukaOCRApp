# core/app_window.py
import os, sys
import json
import shutil
import threading
import win32gui
import win32process
import time

try:
    from pynput import mouse, keyboard
except ImportError:
    print("Yuuka: Lỗi! Thiếu thư viện 'pynput' để lắng nghe phím tắt toàn cục.")
    print("Yuuka: Vui lòng cài đặt bằng lệnh: pip install pynput")
    sys.exit(1)


from PySide6.QtWidgets import QApplication, QLabel
from PySide6.QtGui import QPixmap, QPainter, QFont, QCloseEvent, QColor, QWheelEvent, QDragEnterEvent
from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, Signal, QRect, QElapsedTimer

from core.physics import PhysicsMovableWidget
from core.ui import (ConfigWindow, NotificationWindow, ResultDisplayWindow, 
                     SnippingWidget, SelectionOverlayWidget)
from core.utils import get_true_window_rect, get_process_name_from_hwnd, get_screen_dpi_ratio, get_display_config_hash, set_startup_status
from core.logging import Logger

class HotkeyListener(threading.Thread):
    def __init__(self, hotkey_str, callback, logger):
        super().__init__(daemon=True)
        self.callback = callback
        self.logger = logger
        self.keyboard_listener = None
        self.mouse_listener = None
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        
        self.active_modifiers = set()
        self.required_modifiers = set()
        self.target_mouse_button = None
        self.target_key = None
        
        self.hotkey_str = "" 
        self.update_hotkey(hotkey_str)


    def run(self):
        self._start_listeners()
        self.stop_event.wait()
        self._stop_listeners_internal()

    def _parse_hotkey_parts(self):
        if not self.hotkey_str: return set(), None
        parts = [p.strip() for p in self.hotkey_str.split('+')]
        mods = {p for p in parts if p in ['ctrl', 'shift', 'alt', 'meta']}
        main_keys = [p for p in parts if p not in mods]
        return mods, main_keys[0] if main_keys else None
    
    def _is_mouse_hotkey(self, main_key):
        return (main_key and main_key.startswith("mouse:")) or main_key in ["middle", "x1", "x2"]

    def _start_listeners(self):
        with self.lock:
            self._stop_listeners_internal()
            if not self.hotkey_str:
                self.logger.console_log("Hotkey: Chuỗi phím tắt rỗng, không thể lắng nghe.")
                return

            self.required_modifiers, main_key = self._parse_hotkey_parts()
            
            mod_key_map = {
                keyboard.Key.ctrl_l: 'ctrl', keyboard.Key.ctrl_r: 'ctrl',
                keyboard.Key.shift: 'shift', keyboard.Key.shift_r: 'shift',
                keyboard.Key.alt_l: 'alt', keyboard.Key.alt_r: 'alt',
                keyboard.Key.cmd: 'meta', keyboard.Key.cmd_r: 'meta'
            }

            def on_mod_press(key):
                mod_name = mod_key_map.get(key)
                if mod_name: self.active_modifiers.add(mod_name)
            
            def on_mod_release(key):
                mod_name = mod_key_map.get(key)
                if mod_name in self.active_modifiers: self.active_modifiers.remove(mod_name)

            if self._is_mouse_hotkey(main_key):
                self._setup_mouse_listener(on_mod_press, on_mod_release, main_key)
            elif main_key:
                self._setup_keyboard_listener(on_mod_press, on_mod_release, main_key)

    def _setup_mouse_listener(self, on_mod_press, on_mod_release, main_key):
        button_map = { "middle": mouse.Button.middle, "mouse:middle": mouse.Button.middle, "x1": mouse.Button.x1, "mouse:x1": mouse.Button.x1, "x2": mouse.Button.x2, "mouse:x2": mouse.Button.x2 }
        self.target_mouse_button = button_map.get(main_key)
        
        if not self.target_mouse_button:
            self.logger.console_log(f"Hotkey: Nút chuột không hợp lệ: {main_key}")
            return

        def on_click(x, y, button, pressed):
            if pressed and button == self.target_mouse_button:
                if self.active_modifiers == self.required_modifiers:
                    self.callback()
        
        self.keyboard_listener = keyboard.Listener(on_press=on_mod_press, on_release=on_mod_release, daemon=True)
        self.mouse_listener = mouse.Listener(on_click=on_click, daemon=True)
        self.keyboard_listener.start()
        self.mouse_listener.start()

    def _setup_keyboard_listener(self, on_mod_press, on_mod_release, main_key):
        try:
            if hasattr(keyboard.Key, main_key):
                self.target_key = getattr(keyboard.Key, main_key)
            elif len(main_key) == 1:
                self.target_key = keyboard.KeyCode.from_char(main_key)
            else:
                raise ValueError(f"Không nhận dạng được phím '{main_key}'")

            def on_key_press(key):
                on_mod_press(key)
                
                canonical_key = self.keyboard_listener.canonical(key)
                if canonical_key == self.target_key:
                    if self.active_modifiers == self.required_modifiers:
                        self.callback()

            def on_key_release(key):
                on_mod_release(key)

            self.keyboard_listener = keyboard.Listener(on_press=on_key_press, on_release=on_key_release, daemon=True)
            self.keyboard_listener.start()
        except Exception as e:
            self.logger.console_log(f"Hotkey: Không thể gán phím tắt '{self.hotkey_str}'. Lỗi: {e}")

    def update_hotkey(self, new_hotkey_str):
        with self.lock:
            self.hotkey_str = new_hotkey_str.lower().strip() if new_hotkey_str else ""

    def _stop_listeners_internal(self):
        if self.keyboard_listener:
            try: self.keyboard_listener.stop()
            except Exception: pass
            self.keyboard_listener = None
        if self.mouse_listener:
            try: self.mouse_listener.stop()
            except Exception: pass
            self.mouse_listener = None
        
        self.active_modifiers.clear()
        self.required_modifiers.clear()
        self.target_key = None
        self.target_mouse_button = None
            
    def stop(self):
        self.stop_event.set()

class MainWindow(PhysicsMovableWidget):
    requestApiKeyVerification = Signal(str)
    requestClipboardProcessing = Signal(object)
    requestHookedOCR = Signal(QRect)
    userConfigChanged = Signal(dict)
    requestFileProcessing = Signal(str)
    hotkeyTriggered = Signal()

    def __init__(self, app_configs, user_config_path, logger: Logger):
        self.app_configs = app_configs
        self.user_config_path = user_config_path
        self.logger = logger
        self.user_dir = os.path.dirname(user_config_path)
        self.user_config = {}
        self.my_pid = os.getpid()

        self.session_timer = QElapsedTimer()
        self.session_timer.start()

        self.drag_position = None
        self.is_api_key_needed = True
        self.last_known_api_key = ""
        self.available_models = []
        self.is_hooked = False
        self.hook_edge = None
        self.hooked_hwnd = None
        self.hooked_win_rect_physical = None
        self.hook_offset_logical = QPoint(0, 0)
        self.hooked_roi_logical = None
        self.hooked_roi_physical = None
        self.overlay_relative_offset_logical = QPoint()
        self.is_processing_request = False
        self.SCALE_LEVELS = [i for i in range(10, 101, 10)] 
        self.hotkey_listener = None

        self._load_user_config()
        
        physics_cfg = self._get_current_physics_config()
        super().__init__(physics_config=physics_cfg)

        self.config_window = ConfigWindow(self, physics_cfg, self.logger)
        self.result_window = ResultDisplayWindow(self, physics_cfg)
        self.notification_window = NotificationWindow(self, physics_cfg)
        self.snipping_widget = None
        self.selection_overlay = SelectionOverlayWidget(self, physics_cfg)

        self.setup_ui()
        self.connect_internal_signals()
        self.start_timers()
        self._apply_scale()
        self._apply_global_theme()
        self._apply_sub_window_min_width()
        
        self.start_hotkey_listener()
        self._initial_startup_status_check()

    def _initial_startup_status_check(self):
        env_path = os.path.join(self.user_dir, '.env')
        key_found = False

        if os.path.exists(env_path):
            try:
                with open(env_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip().startswith('GOOGLE_API_KEY='):
                            key_value = line.split('=', 1)[1].strip()
                            if key_value:
                                key_found = True
                                break
            except Exception as e:
                self.logger.console_log(f"Lỗi khi đọc file .env ban đầu: {e}")

        if key_found:
            self.is_api_key_needed = False
            self.update_status("...")
            self.update_status("Wake wake~", 3000)
            QTimer.singleShot(2100, self.reset_status)
        else:
            self.is_api_key_needed = True
            self.update_status("...")
            self.update_status("Copy Gemini API key đi~")

    def _get_current_physics_config(self):
        return {
            'spring_constant': self.user_config.get("PHYSICS_SPRING_CONSTANT", self.app_configs.get("PHYSICS_SPRING_CONSTANT")),
            'damping_factor': self.user_config.get("PHYSICS_DAMPING_FACTOR", self.app_configs.get("PHYSICS_DAMPING_FACTOR")),
            'bounce_damping': self.user_config.get("PHYSICS_BOUNCE_DAMPING_FACTOR", self.app_configs.get("PHYSICS_BOUNCE_DAMPING_FACTOR"))
        }

    def setup_ui(self):
        self.setAcceptDrops(True)
        user_ui_path = os.path.join(self.user_dir, 'ui.png')
        default_ui_path = self.app_configs["UI_FILENAME"]
        ui_path_to_load = user_ui_path if os.path.exists(user_ui_path) else default_ui_path
        
        try:
            self.base_ui_pixmap = QPixmap(ui_path_to_load)
            if self.base_ui_pixmap.isNull():
                self.logger.console_log(f"Lỗi! Không thể tải '{ui_path_to_load}'. Thử lại với UI mặc định.")
                self.base_ui_pixmap = QPixmap(default_ui_path)
                if self.base_ui_pixmap.isNull(): raise FileNotFoundError
        except FileNotFoundError:
            self.logger.console_log(f"Lỗi! Không tìm thấy file giao diện mặc định '{default_ui_path}'.")
            sys.exit(1)

        self.ui_pixmap = self.base_ui_pixmap
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        display_hash = get_display_config_hash()
        last_pos_config = self.user_config.get('positions', {}).get(display_hash, {'x': 50, 'y': 50})
        self.move(QPoint(last_pos_config['x'], last_pos_config['y']))
        self.current_pos_f = QPointF(self.pos())
        self.target_pos_f = QPointF(self.pos())

    def connect_internal_signals(self):
        self.config_window.config_changed.connect(self._on_config_changed)
        self.config_window.apiKeySubmitted.connect(self._on_api_key_submitted)
        self.config_window.uiImageChanged.connect(self._on_ui_image_changed)
        self.hotkeyTriggered.connect(self.trigger_hooked_ocr)
        self.config_window.window_hidden.connect(self.start_hotkey_listener)


    def start_timers(self):
        self.hook_timer = QTimer(self); self.hook_timer.timeout.connect(self.maintain_hook_position); self.hook_timer.start(50)

    def stop_hotkey_listener(self):
        if self.hotkey_listener:
            self.hotkey_listener.stop()
            self.hotkey_listener.join(timeout=1)
            if self.hotkey_listener.is_alive():
                 self.logger.console_log("CẢNH BÁO: Luồng HotkeyListener không dừng kịp thời.")
            self.hotkey_listener = None

    def start_hotkey_listener(self):
        self.stop_hotkey_listener()
        hotkey_str = self.user_config.get('hook_ocr_hotkey', self.app_configs.get('HOOK_OCR_HOTKEY', 'middle'))
        self.hotkey_listener = HotkeyListener(hotkey_str, self.hotkeyTriggered.emit, self.logger)
        self.hotkey_listener.start()

    def _load_user_config(self):
        default_config = {
            'positions': {}, 'custom_prompt': "LUÔN LUÔN dịch text sang tiếng việt với tone phù hợp với ngữ cảnh/giọng điệu/ngôn ngữ trẻ trung/anime. Chỉ trả về duy nhất text được dịch.",
            'prompt_enabled': False, 'process_text_clipboard': False, 
            'process_file_clipboard': True, 
            'process_snipping_clipboard': True,
            'auto_update_enabled': True,
            'start_with_system': False,
            'ui_scale': 100, 'close_button_color': self.app_configs.get("CLOSE_BUTTON_COLOR_RGB"), 
            'sub_window_position': 'auto', 'sub_window_spacing': 5,
            'theme': { 'accent_color': '#E98973', 'sub_win_bg': '#eb74515f', 'sub_win_text': '#FFFFFF', 'sub_win_font_family': 'Segoe UI', 'sub_win_font_size': 10 },
            'PHYSICS_SPRING_CONSTANT': self.app_configs.get('PHYSICS_SPRING_CONSTANT'),
            'PHYSICS_DAMPING_FACTOR': self.app_configs.get('PHYSICS_DAMPING_FACTOR'),
            'PHYSICS_BOUNCE_DAMPING_FACTOR': self.app_configs.get('PHYSICS_BOUNCE_DAMPING_FACTOR'),
            'hook_ocr_hotkey': self.app_configs.get('HOOK_OCR_HOTKEY'),
            'min_sub_win_width': 200,
            'gemini_model': 'gemini-2.0-flash'
        }
        try:
            if os.path.exists(self.user_config_path):
                with open(self.user_config_path, 'r', encoding='utf-8') as f: self.user_config = json.load(f)
                for key, value in default_config.items():
                    if key == 'theme':
                        self.user_config.setdefault('theme', {})
                        for t_key, t_value in value.items():
                            self.user_config['theme'].setdefault(t_key, t_value)
                    else:
                        self.user_config.setdefault(key, value)
            else: self.user_config = default_config; self._save_user_config()
        except Exception as e:
            self.logger.console_log(f"Không thể tải cấu hình người dùng. Dùng cấu hình mặc định. Lỗi: {e}"); self.user_config = default_config
        
    def _save_user_config(self, from_config_window=False):
        try:
            if not self.is_hooked:
                display_hash = get_display_config_hash()
                self.user_config.setdefault('positions', {})[display_hash] = {'x': self.pos().x(), 'y': self.pos().y()}
            os.makedirs(self.user_dir, exist_ok=True)
            with open(self.user_config_path, 'w', encoding='utf-8') as f: json.dump(self.user_config, f, ensure_ascii=False, indent=4)
            if from_config_window:
                self.logger.console_log("Cài đặt đã được lưu.")
        except Exception as e: self.logger.console_log(f"Không thể lưu cấu hình người dùng. Lỗi: {e}")

    def _on_config_changed(self, new_config_values):
        changed = False; layout_changed = False; theme_related_changed = False
        physics_changed = False; hotkey_changed = False; sub_width_changed = False

        for key, value in new_config_values.items():
            current_value = self.user_config.get(key)
            is_different = current_value is None or (current_value != value)

            if is_different:
                self.user_config[key] = value; changed = True
                
                if key == 'start_with_system': set_startup_status(value)
                if key == 'hook_ocr_hotkey':
                    hotkey_changed = True
                    self.logger.console_log(f"Hotkey OCR được đổi thành: '{value}'")
                if key in ['sub_window_position', 'sub_window_spacing']: layout_changed = True
                if key in ['theme', 'ui_scale', 'close_button_color']: theme_related_changed = True
                if key.startswith('PHYSICS_'): physics_changed = True
                if key == 'min_sub_win_width': sub_width_changed = True
                
        if changed:
            self._save_user_config(from_config_window=True)
            self.userConfigChanged.emit(self.user_config)
            if theme_related_changed:
                if 'ui_scale' in new_config_values: self._apply_scale()
                self._apply_global_theme()
            if physics_changed:
                physics_cfg = self._get_current_physics_config()
                for win in [self, self.config_window, self.result_window, self.notification_window, self.selection_overlay]:
                    if win: win.set_physics_params(physics_cfg)
            if sub_width_changed: self._apply_sub_window_min_width()
            if hotkey_changed:
                new_hotkey = self.user_config.get('hook_ocr_hotkey')
                if self.hotkey_listener and new_hotkey:
                     self.hotkey_listener.update_hotkey(new_hotkey)
            if layout_changed or sub_width_changed:
                for sub_win in [self.config_window, self.result_window, self.notification_window]:
                    if sub_win.isVisible(): self._position_sub_window(sub_win, self.pos())
            
            # YUUKA'S PERFECT FIX: Gỡ bỏ việc gọi reset_status() ở đây.
            # Việc này ngăn cửa sổ config bị đóng một cách không mong muốn khi chỉnh slider.
            # self.reset_status()

    def _on_api_key_submitted(self, key): self.last_known_api_key = key; self.requestApiKeyVerification.emit(key)
    
    def _on_ui_image_changed(self, image_path):
        try:
            new_user_ui_path = os.path.join(self.user_dir, 'ui.png')
            shutil.copy(image_path, new_user_ui_path)
            self.base_ui_pixmap = QPixmap(new_user_ui_path)
            if self.base_ui_pixmap.isNull(): raise ValueError("Failed to load new pixmap")
            self._apply_scale()
            self.update_status("Giao diện đã được cập nhật!", 3000)
            self.logger.console_log("Giao diện người dùng đã được thay đổi.")
            if self.config_window.isVisible():
                self.config_window.update_ui_preview(self.base_ui_pixmap)
        except Exception as e:
            self.logger.console_log(f"Lỗi khi đổi giao diện: {e}"); self.update_status("Lỗi đổi giao diện!", 3000)

    def _apply_scale(self):
        scale_percent = self.user_config.get('ui_scale', 100); scale_factor = scale_percent / 100.0
        new_size = self.base_ui_pixmap.size() * scale_factor
        self.setFixedSize(new_size)
        self.ui_pixmap = self.base_ui_pixmap.scaled(new_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.update()
        for sub_win in [self.config_window, self.result_window, self.notification_window]:
            if sub_win.isVisible(): self._position_sub_window(sub_win, self.pos())

    def _apply_global_theme(self):
        theme_config = self.user_config.get('theme', {})
        self.config_window.apply_stylesheet(theme_config, self.user_config, self.app_configs)
        self.result_window.apply_stylesheet(theme_config); self.notification_window.apply_stylesheet(theme_config)
        self.selection_overlay.set_color(theme_config.get('accent_color', '#E98973'))

    def _apply_sub_window_min_width(self):
        min_width = self.user_config.get('min_sub_win_width', 200)
        self.result_window.setMinimumWidth(min_width)
        self.notification_window.setMinimumWidth(min_width)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing); painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(self.rect(), self.ui_pixmap)
        
    def wheelEvent(self, event: QWheelEvent):
        if not self.rect().contains(event.position().toPoint()): return
        current_scale = self.user_config.get('ui_scale', 100)
        delta = 5 if event.angleDelta().y() > 0 else -5
        new_scale = max(10, min(100, current_scale + delta))
        if new_scale != current_scale: 
            self._on_config_changed({'ui_scale': new_scale})
            if self.config_window.isVisible():
                 self.config_window.ui_scale_slider.setValue(new_scale)

    def closeEvent(self, event: QCloseEvent):
        self.logger.console_log("Ứng dụng đang tắt...")
        self.stop_hotkey_listener()
        for window in [self.config_window, self.result_window, self.notification_window, self.snipping_widget, self.selection_overlay]:
            if window: window.close()
        self._save_user_config(); super().closeEvent(event)

    def mousePressEvent(self, event):
        pos = event.position().toPoint(); scale = self.user_config.get('ui_scale', 100) / 100.0
        original_size = self.base_ui_pixmap.size()
        original_pos = QPoint(int(pos.x() / scale), int(pos.y() / scale))
        
        pixel_color = QColor() 
        if original_pos.x() >= 0 and original_pos.y() >= 0 and original_pos.x() < original_size.width() and original_pos.y() < original_size.height():
            pixel_color = self.base_ui_pixmap.toImage().pixelColor(original_pos)
        
        r, g, b = pixel_color.red(), pixel_color.green(), pixel_color.blue()
        close_btn_color = self.user_config.get('close_button_color', self.app_configs["CLOSE_BUTTON_COLOR_RGB"])

        self.velocity_f += QPointF(0, -2)
        if event.button() == Qt.LeftButton:
            if (r, g, b) == tuple(close_btn_color): QApplication.instance().quit(); return
            if (r, g, b) == tuple(self.app_configs["CONFIG_BUTTON_COLOR_RGB"]): self.toggle_config_window(); return
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); self.velocity_f = QPointF(0, 0); event.accept(); return
        
        if event.button() == Qt.RightButton:
            if self.result_window.isVisible(): self.result_window.hide(); event.accept(); return
            self.toggle_config_window(); event.accept(); return
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        if self.is_processing_request: return
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and os.path.splitext(urls[0].toLocalFile())[1].lower() in self.app_configs.get("ACCEPTED_FILE_EXTENSIONS", []):
                event.acceptProposedAction()

    def dropEvent(self, event):
        if self.is_processing_request: return
        if event.mimeData().hasUrls():
            filepath = event.mimeData().urls()[0].toLocalFile()
            self.is_processing_request = True
            self.requestFileProcessing.emit(filepath)

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_position is not None:
            new_screen = QApplication.screenAt(event.globalPosition().toPoint())
            if new_screen and new_screen != self.current_screen: self.current_screen = new_screen
            target_pos = event.globalPosition().toPoint() - self.drag_position
            
            if self.is_hooked:
                unhook_dist = self.user_config.get("UNHOOK_DISTANCE", self.app_configs["UNHOOK_DISTANCE"])
                dpi = get_screen_dpi_ratio(self.pos())
                if self.hook_edge == 'top':
                    hooked_top_logical = self.hooked_win_rect_physical[1] / dpi
                    if abs((target_pos.y() + self.height()) - hooked_top_logical) > unhook_dist: self.unhook()
                    else: target_pos.setY(self.pos().y())
                elif self.hook_edge == 'bottom':
                    hooked_bottom_logical = self.hooked_win_rect_physical[3] / dpi
                    if abs(target_pos.y() - hooked_bottom_logical) > unhook_dist: self.unhook()
                    else: target_pos.setY(self.pos().y())
            
            self.set_animated_target(target_pos)
            for sub_win in [self.config_window, self.result_window, self.notification_window]:
                if sub_win.isVisible(): self._position_sub_window(sub_win, target_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        if self.drag_position is not None and event.button() == Qt.LeftButton:
            self.current_screen = QApplication.screenAt(event.globalPosition().toPoint()); self.drag_position = None
            if not self.is_hooked: self.check_for_hookable_window()
            else:
                dpi = get_screen_dpi_ratio(self.pos())
                hooked_win_qpoint_physical = QPoint(self.hooked_win_rect_physical[0], self.hooked_win_rect_physical[1])
                self.hook_offset_logical = self.pos() - (hooked_win_qpoint_physical / dpi)
            self._save_user_config(from_config_window=False)
        event.accept()

    def update_status(self, text, duration=0):
        # Không hiển thị status notification nếu cửa sổ config đang mở,
        # TRỪ KHI đó là một thông báo xử lý thực sự (không có duration).
        # Điều này cho phép OCR ẩn cửa sổ config.
        if self.config_window.isVisible() and duration > 0:
             return
        
        # Nếu là thông báo xử lý, ẩn cửa sổ config đi
        if self.config_window.isVisible() and duration == 0:
            self.config_window.hide()
        
        self.notification_window.setText(text)
        self._position_sub_window(self.notification_window, self.pos())
        self.notification_window.show()
        if duration > 0: QTimer.singleShot(duration, self.notification_window.hide)

    def reset_status(self): QTimer.singleShot(50, self._perform_reset_status)
    
    def _perform_reset_status(self):
        if self.is_processing_request or self.notification_window.isVisible(): return
        hotkey = self.user_config.get('hook_ocr_hotkey', 'phím tắt').upper()
        
        if self.is_api_key_needed:
            self.update_status("Copy Gemini API key đi~")
        elif self.is_hooked:
            self.update_status(f"Nhấn '{hotkey}' để OCR.")
        elif self.user_config.get('process_text_clipboard', False):
            self.update_status("Copy text đi~")
        else:
            self.update_status("Cap ảnh/file đi~")

    def check_for_hookable_window(self):
        my_rect = self.geometry()
        def is_top_level_at_point(hwnd, point):
            hwnd_at_point = win32gui.WindowFromPoint(point)
            while win32gui.GetParent(hwnd_at_point) != 0: hwnd_at_point = win32gui.GetParent(hwnd_at_point)
            return hwnd == hwnd_at_point
        
        def callback(hwnd, all_windows):
            if hwnd == self.winId() or (win32process.GetWindowThreadProcessId(hwnd)[1] == self.my_pid): return True
            try:
                if not win32gui.IsWindowVisible(hwnd) or not win32gui.GetWindowText(hwnd): return True
                win_rect_physical = get_true_window_rect(hwnd)
                if win_rect_physical[2] - win_rect_physical[0] < 200 or win_rect_physical[3] - win_rect_physical[1] < 200: return True
                center_point = (int((win_rect_physical[0] + win_rect_physical[2]) / 2), int((win_rect_physical[1] + win_rect_physical[3]) / 2))
                if not is_top_level_at_point(hwnd, center_point): return True
                if get_process_name_from_hwnd(hwnd) in ["explorer.exe", "shellexperiencehost.exe", "searchhost.exe", "startmenuexperiencehost.exe", "applicationframehost.exe"]: return True
            except Exception: return True
            
            dpi = get_screen_dpi_ratio(QPoint(win_rect_physical[0], win_rect_physical[1]))
            win_rect_logical = QRect(*(int(c / dpi) for c in (win_rect_physical[0], win_rect_physical[1], win_rect_physical[2]-win_rect_physical[0], win_rect_physical[3]-win_rect_physical[1])))
            is_horizontally_aligned = my_rect.left() < win_rect_logical.right() and my_rect.right() > win_rect_logical.left()
            
            hook_prox_y = self.user_config.get("HOOK_PROXIMITY_Y", self.app_configs["HOOK_PROXIMITY_Y"])
            hook_prox_y_bottom = self.user_config.get("HOOK_PROXIMITY_Y_BOTTOM", self.app_configs["HOOK_PROXIMITY_Y_BOTTOM"])

            if is_horizontally_aligned and abs(my_rect.bottom() - win_rect_logical.top()) < hook_prox_y:
                all_windows.append((hwnd, win_rect_physical, abs(my_rect.bottom() - win_rect_logical.top()), 'top'))
            if is_horizontally_aligned and abs(my_rect.top() - win_rect_logical.bottom()) < hook_prox_y_bottom:
                all_windows.append((hwnd, win_rect_physical, abs(my_rect.top() - win_rect_logical.bottom()), 'bottom'))
            return True

        windows = []; win32gui.EnumWindows(callback, windows)
        if windows: self.hook_to_window(*min(windows, key=lambda w: w[2]))
        else: self.unhook()

    def hook_to_window(self, hwnd, rect_physical, _, edge):
        if self.is_hooked and self.hooked_hwnd == hwnd and self.hook_edge == edge: return
        try: self.logger.console_log(f"Hooking to {edge} of window {hwnd} (PID: {win32process.GetWindowThreadProcessId(hwnd)[1]}, Process: {get_process_name_from_hwnd(hwnd) or 'N/A'})")
        except: self.logger.console_log(f"Hooking to {edge} of window {hwnd}")
        
        self.is_hooked = True; self.hook_edge = edge; self.hooked_hwnd = hwnd
        self.hooked_win_rect_physical = rect_physical; self._reset_roi_state()
        if self.config_window.isVisible(): self.config_window.hide()
        
        if self.notification_window.isVisible(): self.notification_window.hide()

        dpi = get_screen_dpi_ratio(QPoint(rect_physical[0], rect_physical[1]))
        target_x = self.pos().x()
        if edge == 'top':
            offset = self.user_config.get("HOOK_OFFSET_Y_TOP", self.app_configs["HOOK_OFFSET_Y_TOP"])
            target_y_phys = rect_physical[1] - self.height() * dpi + (offset * dpi)
        else:
            offset = self.user_config.get("HOOK_OFFSET_Y_BOTTOM", self.app_configs["HOOK_OFFSET_Y_BOTTOM"])
            target_y_phys = rect_physical[3] + (offset * dpi)
        
        target_pos = QPoint(target_x, int(target_y_phys / dpi))
        self.set_animated_target(target_pos)
        self.hook_offset_logical = target_pos - QPoint(int(rect_physical[0]/dpi), int(rect_physical[1]/dpi))
        self.reset_status()
        for sub_win in [self.result_window, self.notification_window]:
            if sub_win.isVisible(): self._position_sub_window(sub_win, target_pos)

    def unhook(self):
        if self.is_hooked:
            self.logger.console_log("Unhooked."); self.velocity_f += QPointF(0, -2)
            self.is_hooked = False; self.hooked_hwnd = None; self.hook_edge = None
            self.hooked_win_rect_physical = None; self.hook_offset_logical = QPoint(0,0)
            self._reset_roi_state()
            if self.is_api_key_needed:
                self.update_status("Copy Gemini API key đi~")
            else:   
                self.update_status("Cap ảnh/file đi~", 3000)
            if self.config_window.isVisible(): self.config_window.hide()

    def maintain_hook_position(self):
        if not self.is_hooked or self.hooked_hwnd is None or self.drag_position is not None: return
        try:
            if not win32gui.IsWindow(self.hooked_hwnd) or not win32gui.IsWindowVisible(self.hooked_hwnd): self.unhook(); return
            center_x = self.hooked_win_rect_physical[0] + (self.hooked_win_rect_physical[2] - self.hooked_win_rect_physical[0]) // 2
            center_y = self.hooked_win_rect_physical[1] + (self.hooked_win_rect_physical[3] - self.hooked_win_rect_physical[1]) // 2
            hwnd_at_center = win32gui.WindowFromPoint((center_x, center_y))
            while win32gui.GetParent(hwnd_at_center) != 0: hwnd_at_center = win32gui.GetParent(hwnd_at_center)
            if hwnd_at_center != self.hooked_hwnd: self.unhook(); return
            
            new_rect = get_true_window_rect(self.hooked_hwnd)
            if new_rect != self.hooked_win_rect_physical:
                self.hooked_win_rect_physical = new_rect
                dpi = get_screen_dpi_ratio(QPoint(new_rect[0], new_rect[1]))
                new_win_pos = QPoint(int(new_rect[0] / dpi), int(new_rect[1] / dpi))
                new_main_pos = new_win_pos + self.hook_offset_logical
                self.set_animated_target(new_main_pos)
                
                for sub_win in [self.result_window, self.notification_window]:
                    if sub_win.isVisible(): self._position_sub_window(sub_win, new_main_pos)
                if self.selection_overlay.isVisible() and self.hooked_roi_logical:
                    new_overlay_pos = new_win_pos + self.overlay_relative_offset_logical
                    self.hooked_roi_logical.moveTo(new_overlay_pos)
                    self.hooked_roi_physical = QRect(*(int(c * dpi) for c in self.hooked_roi_logical.getRect()))
                    self.selection_overlay.set_animated_target(new_overlay_pos)
        except Exception: self.unhook()

    def trigger_hooked_ocr(self):
        if not self.is_hooked or self.is_processing_request or self.is_api_key_needed: return
        if self.hooked_roi_physical:
            self.is_processing_request = True; self.update_status("Đọc lại...")
            self.requestHookedOCR.emit(QRect(self.hooked_roi_physical))
        else:
            self.hook_timer.stop()
            hotkey = self.user_config.get('hook_ocr_hotkey', 'phím tắt').upper()
            self.update_status(f"Kẻ vùng cần đọc đi (hoặc nhấn '{hotkey}' lần nữa để hủy)."); self.hide(); self._reset_roi_state()
            QApplication.processEvents()
            self.snipping_widget = SnippingWidget()
            self.snipping_widget.set_color(self.user_config.get('theme', {}).get('accent_color', '#E98973'))
            self.snipping_widget.snipping_finished.connect(self._on_area_selected)
            self.snipping_widget.snipping_cancelled.connect(self._on_snipping_cancelled)
            self.snipping_widget.show()

    def _on_snipping_cancelled(self):
        if self.snipping_widget: self.snipping_widget.close(); self.snipping_widget = None
        self.show(); self.reset_status(); self.hook_timer.start(50)

    def _on_area_selected(self, local_rect):
        if not self.snipping_widget: return
        global_rect = QRect(self.snipping_widget.mapToGlobal(local_rect.topLeft()), local_rect.size())
        
        self.show(); self.snipping_widget.close(); self.snipping_widget = None; self.hook_timer.start(50)
        if not self.is_hooked or not self.hooked_win_rect_physical: self.reset_status(); return
        if global_rect.width() < 5 or global_rect.height() < 5: self.reset_status(); return
        
        self.is_processing_request = True; self.update_status("Gemini đọc...")
        self.hooked_roi_logical = global_rect
        dpi = get_screen_dpi_ratio(global_rect.center())
        win_top_left = QPoint(int(self.hooked_win_rect_physical[0] / dpi), int(self.hooked_win_rect_physical[1] / dpi))
        
        self.overlay_relative_offset_logical = self.hooked_roi_logical.topLeft() - win_top_left
        self.hooked_roi_physical = QRect(*(int(c * dpi) for c in global_rect.getRect()))
        
        self.selection_overlay.setFixedSize(self.hooked_roi_logical.size())
        self.selection_overlay.move(self.hooked_roi_logical.topLeft())
        self.selection_overlay.show(); self.reset_status() 
        self.requestHookedOCR.emit(QRect(self.hooked_roi_physical))

    def _reset_roi_state(self):
        self.hooked_roi_logical = None; self.hooked_roi_physical = None
        self.overlay_relative_offset_logical = QPoint()
        if self.selection_overlay: self.selection_overlay.hide()

    def toggle_config_window(self):
        if self.config_window.isVisible():
            self.config_window.hide()
        else:
            if self.is_hooked: self.unhook()
            self.stop_hotkey_listener()
            time.sleep(0.1)
            api_info = {'key': self.last_known_api_key, 'verified': not self.is_api_key_needed, 'models': self.available_models}
            self.config_window.load_config(
                self.user_config, self.app_configs, api_info, 
                self.base_ui_pixmap, self.logger.get_logs(),
                self.session_timer 
            )
            self._position_sub_window(self.config_window, self.pos())
            self.config_window.show(); self.config_window.activateWindow(); self.config_window.setFocus()

    def _position_sub_window(self, sub_window, main_window_pos):
        main_rect = QRect(main_window_pos, self.size())
        if not isinstance(sub_window, ConfigWindow):
             main_w = main_rect.width()
             sub_win_min_w = self.user_config.get('min_sub_win_width', 200)
             width = max(sub_win_min_w, main_w)
             sub_window.setFixedWidth(width)
        sub_window.adjustSize()
        sub_size = sub_window.size()

        pos_mode = self.user_config.get('sub_window_position', 'auto'); spacing = self.user_config.get('sub_window_spacing', 5)
        target_pos = QPoint()
        effective_mode = 'up' if pos_mode == 'auto' and self.is_hooked and self.hook_edge == 'bottom' else ('down' if pos_mode == 'auto' else pos_mode)

        if effective_mode == 'up': target_pos.setX(main_rect.x() + (main_rect.width() - sub_size.width()) // 2); target_pos.setY(main_rect.top() - sub_size.height() - spacing)
        elif effective_mode == 'down': target_pos.setX(main_rect.x() + (main_rect.width() - sub_size.width()) // 2); target_pos.setY(main_rect.bottom() + spacing)
        elif effective_mode == 'left': target_pos.setX(main_rect.left() - sub_size.width() - spacing); target_pos.setY(main_rect.y() + (main_rect.height() - sub_size.height()) // 2)
        elif effective_mode == 'right': target_pos.setX(main_rect.right() + spacing); target_pos.setY(main_rect.y() + (main_rect.height() - sub_size.height()) // 2)
        
        if sub_window is self.notification_window and self.result_window.isVisible():
            result_rect = self.result_window.geometry()
            if effective_mode == 'down': target_pos.setY(result_rect.bottom() + spacing)
            elif effective_mode == 'up': target_pos.setY(result_rect.top() - sub_size.height() - spacing)
        elif sub_window is self.result_window and self.notification_window.isVisible():
            noti_rect = self.notification_window.geometry(); sub_rect = QRect(target_pos, sub_size)
            if effective_mode == 'down' and sub_rect.intersects(noti_rect):
                self.notification_window.set_animated_target(QPoint(noti_rect.x(), target_pos.y() + sub_size.height() + spacing))
            elif effective_mode == 'up' and sub_rect.intersects(noti_rect):
                self.notification_window.set_animated_target(QPoint(noti_rect.x(), target_pos.y() - noti_rect.height() - spacing))

        if not sub_window.isVisible(): sub_window.move(target_pos)
        else: sub_window.set_animated_target(target_pos)

    def handle_api_key_needed(self):
        self.is_api_key_needed = True; self.last_known_api_key = ""; self.available_models = []
        self.config_window.update_api_key_status(self.last_known_api_key, False, [])
        self.update_status("Copy Gemini API key đi~")
        
    def handle_api_key_failed(self, attempted_key):
        self.is_api_key_needed = True; self.last_known_api_key = attempted_key; self.available_models = []
        self.config_window.update_api_key_status(self.last_known_api_key, False, [])
        self.update_status("Key không hợp lệ!", 3000)
        QTimer.singleShot(3100, self.reset_status)
        
    def handle_api_key_verified(self, key, models):
        self.is_api_key_needed = False; self.last_known_api_key = key; self.available_models = models
        self.config_window.update_api_key_status(key, True, models)
        if not self.config_window.isVisible():
            self.update_status("Key OK!", 2000)
            QTimer.singleShot(2100, self.reset_status)
        
    def handle_processing_started(self):
        self.is_processing_request = True

    def handle_processing_complete(self): 
        self.is_processing_request = False
        self.reset_status()
    
    def handle_show_result(self, result_text):
        if self.config_window.isVisible(): self.config_window.hide()
        self.result_window.setText(result_text)
        self._position_sub_window(self.result_window, self.pos())
        self.result_window.show(); self.result_window.activateWindow(); self.result_window.text_edit.setFocus()