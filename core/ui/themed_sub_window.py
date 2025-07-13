# core/ui/themed_sub_window.py
from PySide6.QtWidgets import QTextEdit, QVBoxLayout
from PySide6.QtGui import QMouseEvent
from PySide6.QtCore import Qt

from core.physics import PhysicsMovableWidget

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