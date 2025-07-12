# core/physics.py
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRect

class PhysicsMovableWidget(QWidget):
    # YUUKA: Các hằng số vật lý giờ sẽ được khởi tạo qua constructor
    def __init__(self, parent=None, physics_config=None):
        super().__init__(parent)
        
        # YUUKA: Đặt giá trị mặc định nếu không có config
        if physics_config is None:
            physics_config = {}
        
        self.SPRING_CONSTANT = physics_config.get('spring_constant', 0.1)
        self.DAMPING_FACTOR = physics_config.get('damping_factor', 0.55)
        self.BOUNCE_DAMPING_FACTOR = physics_config.get('bounce_damping', 0.3)

        self.current_pos_f = QPointF(self.pos())
        self.target_pos_f = QPointF(self.pos())
        self.velocity_f = QPointF(0, 0)
        self.current_screen = QApplication.screenAt(self.pos()) or QApplication.primaryScreen()
        
        self.constrain_to_screen = True

        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(16) # ~60 FPS

    def set_physics_params(self, physics_config):
        """Cho phép cập nhật các thông số vật lý sau khi đã khởi tạo."""
        self.SPRING_CONSTANT = physics_config.get('spring_constant', self.SPRING_CONSTANT)
        self.DAMPING_FACTOR = physics_config.get('damping_factor', self.DAMPING_FACTOR)
        self.BOUNCE_DAMPING_FACTOR = physics_config.get('bounce_damping', self.BOUNCE_DAMPING_FACTOR)

    def _update_animation(self):
        """Vòng lặp animation dựa trên vật lý, được gọi bởi QTimer."""
        if not self.isVisible(): return

        if (self.target_pos_f - self.current_pos_f).manhattanLength() < 0.1 and self.velocity_f.manhattanLength() < 0.1:
            return

        force = self.target_pos_f - self.current_pos_f
        force *= self.SPRING_CONSTANT
        force -= self.velocity_f * self.DAMPING_FACTOR
        self.velocity_f += force
        self.current_pos_f += self.velocity_f

        if self.constrain_to_screen:
            screen_rect = self.current_screen.availableGeometry()

            if self.current_pos_f.x() < screen_rect.left():
                self.current_pos_f.setX(screen_rect.left()); self.velocity_f.setX(-self.velocity_f.x() * self.BOUNCE_DAMPING_FACTOR)
            elif self.current_pos_f.x() + self.width() > screen_rect.right():
                self.current_pos_f.setX(screen_rect.right() - self.width()); self.velocity_f.setX(-self.velocity_f.x() * self.BOUNCE_DAMPING_FACTOR)
            if self.current_pos_f.y() < screen_rect.top():
                self.current_pos_f.setY(screen_rect.top()); self.velocity_f.setY(-self.velocity_f.y() * self.BOUNCE_DAMPING_FACTOR)
            elif self.current_pos_f.y() + self.height() > screen_rect.bottom():
                self.current_pos_f.setY(screen_rect.bottom() - self.height()); self.velocity_f.setY(-self.velocity_f.y() * self.BOUNCE_DAMPING_FACTOR)

        super().move(self.current_pos_f.toPoint())

    def move(self, pos):
        """Ghi đè hàm move để 'snap' widget đến vị trí mới ngay lập tức."""
        self.target_pos_f = QPointF(pos)
        self.current_pos_f = QPointF(pos)
        self.velocity_f = QPointF(0, 0)
        self.current_screen = QApplication.screenAt(pos) or self.current_screen
        super().move(pos)

    def set_animated_target(self, pos):
        """Đặt mục tiêu mới cho hệ thống animation di chuyển tới."""
        self.target_pos_f = QPointF(pos)
        new_screen = QApplication.screenAt(pos)
        if new_screen:
            self.current_screen = new_screen