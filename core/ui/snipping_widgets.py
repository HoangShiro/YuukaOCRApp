# core/ui/snipping_widgets.py
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtCore import Qt, Signal, QRect, QPoint

from core.physics import PhysicsMovableWidget

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