# core/ui/hotkey_button.py
from PySide6.QtWidgets import QPushButton, QApplication
from PySide6.QtGui import QKeyEvent, QKeySequence, QMouseEvent
from PySide6.QtCore import Qt, Signal, QEvent, QTimer

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