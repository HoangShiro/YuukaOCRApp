# core/ui/themed_color_picker.py
from PySide6.QtWidgets import (QDialog, QWidget, QVBoxLayout, QHBoxLayout, 
                               QPushButton, QLabel, QLineEdit, QApplication, QFrame)
from PySide6.QtGui import (QPainter, QColor, QPen, QBrush, QLinearGradient, 
                           QFont, QIntValidator, QMouseEvent, QIcon, QPixmap, QCursor, QKeyEvent, QPainterPath)
from PySide6.QtCore import Qt, Signal, QPoint, QPointF, QSize, QRect

class _ScreenEyedropper(QWidget):
    color_picked = Signal(QColor)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self.setGeometry(QApplication.primaryScreen().virtualGeometry())
        self.setCursor(Qt.CrossCursor)
        self.desktop_pixmap = QApplication.primaryScreen().grabWindow(0)

        self.magnifier_pos_logical = QPoint()
        self.magnifier_pos_physical = QPoint()
        self.current_color = QColor()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 70))
        
        if not self.magnifier_pos_logical.isNull():
            size = 120; zoom = 8
            half_size = size // 2; half_grab_size = half_size // zoom
            
            draw_pos = self.magnifier_pos_logical + QPoint(20, 20)
            if draw_pos.x() + size > self.width(): draw_pos.setX(self.magnifier_pos_logical.x() - size - 20)
            if draw_pos.y() + size > self.height(): draw_pos.setY(self.magnifier_pos_logical.y() - size - 20)
            
            source_rect = QRect(
                self.magnifier_pos_physical.x() - half_grab_size, 
                self.magnifier_pos_physical.y() - half_grab_size, 
                half_grab_size * 2, 
                half_grab_size * 2
            )
            target_rect = QRect(draw_pos.x(), draw_pos.y(), size, size)
            
            clip_path = QPainterPath(); clip_path.addEllipse(QPointF(target_rect.center()), half_size, half_size)
            painter.setClipPath(clip_path)
            painter.drawPixmap(target_rect, self.desktop_pixmap, source_rect)
            painter.setClipping(False)

            painter.setPen(QPen(Qt.white, 2)); painter.drawEllipse(target_rect)
            painter.setPen(QPen(Qt.black, 1)); painter.drawEllipse(target_rect)
            painter.setPen(QPen(Qt.white, 1)); 
            center_pixel_rect = QRect(target_rect.center().x() - zoom // 2, target_rect.center().y() - zoom // 2, zoom, zoom)
            painter.drawRect(center_pixel_rect)

            hex_text = self.current_color.name(QColor.NameFormat.HexRgb).upper()
            font = QFont("Consolas", 10, QFont.Bold); painter.setFont(font)
            text_rect = QRect(draw_pos.x(), draw_pos.y() + size, size, 25)
            painter.setPen(Qt.NoPen); painter.setBrush(QColor(0,0,0,150)); painter.drawRoundedRect(text_rect, 5, 5)
            painter.setPen(Qt.white); painter.drawText(text_rect, Qt.AlignCenter, hex_text)

    def mouseMoveEvent(self, event: QMouseEvent):
        self.magnifier_pos_logical = event.position().toPoint()
        global_logical_pos = event.globalPosition().toPoint()
        
        screen = QApplication.screenAt(global_logical_pos)
        if not screen: return

        if hasattr(screen, 'physicalGeometry'):
            screen_logical_geo = screen.geometry()
            screen_physical_geo = screen.physicalGeometry()
            relative_logical_pos = global_logical_pos - screen_logical_geo.topLeft()
            relative_physical_pos = QPointF(relative_logical_pos) * screen.devicePixelRatio()
            self.magnifier_pos_physical = screen_physical_geo.topLeft() + relative_physical_pos.toPoint()
        else:
            ratio = screen.devicePixelRatio()
            self.magnifier_pos_physical = (QPointF(global_logical_pos) * ratio).toPoint()

        if self.desktop_pixmap.rect().contains(self.magnifier_pos_physical):
            self.current_color = self.desktop_pixmap.toImage().pixelColor(self.magnifier_pos_physical)
        
        self.update()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.color_picked.emit(self.current_color)
        else:
            self.cancelled.emit()
        self.close()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.close()

class _SaturationValuePicker(QWidget):
    sv_changed = Signal(float, float)
    def __init__(self, parent=None):
        super().__init__(parent); self._hue = 0.0; self._saturation = 1.0; self._value = 1.0; self._marker_pos = QPointF(); self.setMinimumSize(200, 150); self.update_marker()
    def set_hue(self, hue):
        if self._hue != hue: self._hue = hue; self.update()
    def set_sv(self, saturation, value):
        self._saturation = max(0.0, min(1.0, saturation)); self._value = max(0.0, min(1.0, value)); self.update_marker(); self.update()
    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing); painter.setPen(Qt.NoPen); base_color = QColor.fromHsvF(self._hue, 1.0, 1.0); painter.setBrush(base_color); painter.drawRoundedRect(self.rect(), 5, 5)
        s_gradient = QLinearGradient(0, 0, self.width(), 0); s_gradient.setColorAt(0, Qt.white); s_gradient.setColorAt(1, Qt.transparent); painter.setBrush(s_gradient); painter.drawRoundedRect(self.rect(), 5, 5)
        v_gradient = QLinearGradient(0, 0, 0, self.height()); v_gradient.setColorAt(0, Qt.transparent); v_gradient.setColorAt(1, Qt.black); painter.setBrush(v_gradient); painter.drawRoundedRect(self.rect(), 5, 5)
        painter.setPen(QPen(Qt.white, 2)); painter.setBrush(Qt.NoBrush); painter.drawEllipse(self._marker_pos, 5, 5); painter.setPen(QPen(Qt.black, 2)); painter.drawEllipse(self._marker_pos, 4, 4)
    def mousePressEvent(self, event): self._handle_mouse(event.position())
    def mouseMoveEvent(self, event): self._handle_mouse(event.position())
    def _handle_mouse(self, pos):
        s = max(0.0, min(1.0, pos.x() / self.width())); v = 1.0 - max(0.0, min(1.0, pos.y() / self.height())); self._saturation = s; self._value = v; self.update_marker(); self.update(); self.sv_changed.emit(s, v)
    def update_marker(self):
        self._marker_pos = QPointF(self._saturation * self.width(), (1.0 - self._value) * self.height())
class _ColorSlider(QWidget):
    value_changed = Signal(float)
    def __init__(self, parent=None):
        super().__init__(parent); self.setFixedSize(20, 150); self._value = 0.0; self._marker_y = 0
    def get_value(self): return self._value
    def set_value(self, value):
        self._value = max(0.0, min(1.0, value)); self._marker_y = (1.0 - self._value) * self.height(); self.update()
    def paintEvent(self, event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing); self.draw_bar(painter); painter.setPen(QPen(Qt.white, 2)); painter.setBrush(Qt.NoBrush); painter.drawLine(0, self._marker_y, self.width(), self._marker_y)
    def mousePressEvent(self, event): self._handle_mouse(event.position())
    def mouseMoveEvent(self, event): self._handle_mouse(event.position())
    def _handle_mouse(self, pos):
        self._value = 1.0 - max(0.0, min(1.0, pos.y() / self.height())); self.set_value(self._value); self.value_changed.emit(self._value)
    def draw_bar(self, painter): pass
class _HueSlider(_ColorSlider):
    def draw_bar(self, painter):
        gradient = QLinearGradient(0, self.height(), 0, 0); [gradient.setColorAt(i / 6.0, QColor.fromHsvF(i / 6.0, 1, 1)) for i in range(7)]; painter.setBrush(gradient); painter.setPen(Qt.NoPen); painter.drawRoundedRect(self.rect(), 5, 5)
class _AlphaSlider(_ColorSlider):
    def __init__(self, parent=None):
        super().__init__(parent); self.color = QColor(Qt.red)
    def set_color(self, color): self.color = QColor(color); self.update()
    def draw_bar(self, painter):
        painter.setPen(Qt.NoPen); size = 8
        for y in range(0, self.height(), size):
            for x in range(0, self.width(), size): painter.setBrush(QColor(200, 200, 200) if (x // size + y // size) % 2 == 0 else QColor(255, 255, 255)); painter.drawRect(x, y, size, size)
        gradient = QLinearGradient(0, self.height(), 0, 0); start_color = QColor(self.color); start_color.setAlpha(0); end_color = QColor(self.color); end_color.setAlpha(255); gradient.setColorAt(0, start_color); gradient.setColorAt(1, end_color); painter.setBrush(gradient); painter.setPen(Qt.NoPen); painter.drawRoundedRect(self.rect(), 5, 5)

class ThemedColorDialog(QDialog):
    color_accepted = Signal(QColor)
    def __init__(self, initial_color=QColor("#E98973"), show_alpha=False, theme_config=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint); self.setAttribute(Qt.WA_TranslucentBackground)
        self.initial_color = initial_color; self.current_color = QColor(initial_color); self.theme_config = theme_config or {}; self.show_alpha = show_alpha
        self.drag_pos = None; self.eyedropper_widget = None
        self._setup_ui(); self._connect_signals(); self._update_controls_from_color(self.current_color); self.setFixedSize(self.sizeHint()); self._apply_theme()
    def _setup_ui(self):
        self.container = QFrame(self); self.container.setObjectName("container"); main_layout = QVBoxLayout(self.container); main_layout.setContentsMargins(10, 10, 10, 10)
        picker_layout = QHBoxLayout(); picker_layout.setSpacing(10); self.sv_picker = _SaturationValuePicker(); self.hue_slider = _HueSlider(); self.alpha_slider = _AlphaSlider()
        picker_layout.addWidget(self.sv_picker, stretch=1); picker_layout.addWidget(self.hue_slider)
        if self.show_alpha: picker_layout.addWidget(self.alpha_slider)
        preview_layout = QHBoxLayout(); self.preview_old = self._create_preview_box(self.initial_color); self.preview_new = self._create_preview_box(self.current_color)
        self.eyedropper_button = QPushButton(); self.eyedropper_button.setObjectName("eyedropperButton"); self.eyedropper_button.setFixedSize(32, 32); self.eyedropper_button.setToolTip("Lấy màu từ màn hình")
        icon_svg = b'<svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px" fill="#FFFFFF"><path d="M0 0h24v24H0V0z" fill="none"/><path d="M11.5 2C6.81 2 3 5.81 3 10.5S6.81 19 11.5 19h.5v3c0 .55.45 1 1 1s1-.45 1-1v-3h.5c4.69 0 8.5-3.81 8.5-8.5S18.19 2 13.5 2h-2zm0 15c-2.49 0-4.5-2.01-4.5-4.5S9.01 6 11.5 6s4.5 2.01 4.5 4.5-2.01 4.5-4.5 4.5z"/></svg>'
        pixmap = QPixmap(); pixmap.loadFromData(icon_svg); self.eyedropper_button.setIcon(QIcon(pixmap)); self.eyedropper_button.setIconSize(QSize(24, 24))
        preview_layout.addWidget(self.preview_old); preview_layout.addWidget(self.preview_new); preview_layout.addStretch(); preview_layout.addWidget(self.eyedropper_button)
        input_layout = QHBoxLayout(); self.hex_edit = QLineEdit(); self.hex_edit.setPlaceholderText("#RRGGBB"); input_layout.addWidget(QLabel("HEX:")); input_layout.addWidget(self.hex_edit)
        button_layout = QHBoxLayout(); self.ok_button = QPushButton("OK"); self.cancel_button = QPushButton("Hủy"); button_layout.addStretch(); button_layout.addWidget(self.ok_button); button_layout.addWidget(self.cancel_button)
        main_layout.addLayout(picker_layout); main_layout.addLayout(preview_layout); main_layout.addLayout(input_layout); main_layout.addLayout(button_layout)
        root_layout = QVBoxLayout(self); root_layout.setContentsMargins(0,0,0,0); root_layout.addWidget(self.container)
    def _create_preview_box(self, color):
        box = QLabel(); box.setFixedSize(50, 50); self._update_preview_box(box, color); return box
    def _update_preview_box(self, box, color):
        border_color = QColor(self.theme_config.get('sub_win_text', '#FFFFFF')).name(); box.setStyleSheet(f"background-color: {color.name(QColor.NameFormat.HexArgb)}; border: 1px solid {border_color}88; border-radius: 5px;")
    def _apply_theme(self):
        accent = self.theme_config.get('accent_color', '#E98973'); bg = self.theme_config.get('sub_win_bg', 'rgba(30,30,30,245)'); text = self.theme_config.get('sub_win_text', '#FFFFFF')
        self.container.setStyleSheet(f"""
            #container {{ background-color: {bg}; border: 1px solid {accent}; border-radius: 8px; }} QToolTip {{ background-color: {bg}; color: {text}; border: 1px solid {accent}; border-radius: 4px; padding: 5px; }}
            QLabel {{ color: {text}; font-family: Segoe UI; }} QLineEdit {{ background-color: rgba(0,0,0,0.2); border: 1px solid {accent}88; border-radius: 4px; color: {text}; padding: 4px; }}
            QPushButton {{ background-color: rgba(255,255,255,0.1); color: {text}; border: 1px solid {accent}88; border-radius: 4px; padding: 5px 15px; }}
            QPushButton:hover {{ background-color: rgba(255,255,255,0.2); }} #eyedropperButton {{ padding: 0; }}
        """); self._update_preview_box(self.preview_old, self.initial_color); self._update_preview_box(self.preview_new, self.current_color)
    def _connect_signals(self):
        self.sv_picker.sv_changed.connect(self._sv_changed); self.hue_slider.value_changed.connect(self._hue_changed); self.alpha_slider.value_changed.connect(self._alpha_changed); self.hex_edit.textChanged.connect(self._hex_changed)
        self.ok_button.clicked.connect(self._accept_and_emit); self.cancel_button.clicked.connect(self.reject); self.eyedropper_button.clicked.connect(self._start_color_picking)
    def _accept_and_emit(self):
        self.color_accepted.emit(self.current_color); self.accept()
    def _start_color_picking(self):
        self.hide(); self.eyedropper_widget = _ScreenEyedropper(); self.eyedropper_widget.color_picked.connect(self._on_color_picked); self.eyedropper_widget.cancelled.connect(self._on_picking_cancelled); self.eyedropper_widget.show()
    def _cleanup_eyedropper(self):
        if self.eyedropper_widget:
            self.eyedropper_widget.close(); self.eyedropper_widget.deleteLater(); self.eyedropper_widget = None
    def _on_color_picked(self, color):
        self._cleanup_eyedropper()
        if color.isValid(): self._update_controls_from_color(color, source='eyedropper')
        self.show(); self.activateWindow()
    def _on_picking_cancelled(self):
        self._cleanup_eyedropper(); self.show(); self.activateWindow()
    def _sv_changed(self, s, v):
        h, _, _, a = self.current_color.getHsvF(); new_color = QColor.fromHsvF(h, s, v, a); self._update_controls_from_color(new_color, source='sv')
    def _hue_changed(self, h):
        _, s, v, a = self.current_color.getHsvF(); new_color = QColor.fromHsvF(h, s, v, a); self._update_controls_from_color(new_color, source='hue')
    def _alpha_changed(self, alpha_float):
        self.current_color.setAlphaF(alpha_float); self._update_controls_from_color(self.current_color, source='alpha')
    def _hex_changed(self):
        color_str = self.hex_edit.text();
        if not color_str.startswith("#"): color_str = "#" + color_str
        color = QColor(color_str)
        if color.isValid(): self._update_controls_from_color(color, source='hex')

    def _update_controls_from_color(self, color, source=None):
        self.current_color = QColor(color)
        self._update_preview_box(self.preview_new, self.current_color)
        h, s, v, a = color.getHsvF()

        # YUUKA'S FIX: Tách logic cập nhật SV picker để sửa lỗi
        if source != 'sv':
            # Cập nhật cả màu nền (hue) và vị trí marker (s,v)
            # khi nguồn thay đổi không phải là chính SV picker.
            self.sv_picker.set_hue(h)
            self.sv_picker.set_sv(s, v)
        
        # Cập nhật các control còn lại, tránh vòng lặp feedback
        if source != 'hue':
            self.hue_slider.set_value(h)
        
        if self.show_alpha:
            if source != 'alpha':
                self.alpha_slider.set_value(a)
            self.alpha_slider.set_color(color)
        
        if source != 'hex':
            format = QColor.NameFormat.HexArgb if self.show_alpha and color.alpha() < 255 else QColor.NameFormat.HexRgb
            self.hex_edit.blockSignals(True)
            self.hex_edit.setText(color.name(format).upper())
            self.hex_edit.blockSignals(False)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton: self.drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft(); event.accept()
    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() & Qt.LeftButton and self.drag_pos is not None: self.move(event.globalPosition().toPoint() - self.drag_pos); event.accept()
    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and self.drag_pos: self.drag_pos = None; event.accept()