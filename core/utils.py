# core/utils.py
import ctypes
from ctypes import wintypes
import os
import win32gui, win32process
import psutil
from PySide6.QtCore import QRect, QPoint
from PySide6.QtWidgets import QApplication
import hashlib # YUUKA: Thêm thư viện hash ổn định
import winreg # YUUKA: Thêm thư viện để chỉnh sửa registry

def get_true_window_rect(hwnd):
    """
    Lấy toạ độ vật lý (physical pixels) thực của cửa sổ, loại bỏ phần bóng mờ.
    """
    try:
        dwmapi = ctypes.windll.dwmapi
        DWMWA_EXTENDED_FRAME_BOUNDS = 9
        rect = ctypes.wintypes.RECT()
        dwmapi.DwmGetWindowAttribute(
            ctypes.wintypes.HWND(hwnd),
            ctypes.wintypes.DWORD(DWMWA_EXTENDED_FRAME_BOUNDS),
            ctypes.byref(rect),
            ctypes.sizeof(rect)
        )
        if rect.left == 0 and rect.top == 0 and rect.right == 0 and rect.bottom == 0:
             return win32gui.GetWindowRect(hwnd)
        return rect.left, rect.top, rect.right, rect.bottom
    except (AttributeError, Exception):
        return win32gui.GetWindowRect(hwnd)

def get_process_name_from_hwnd(hwnd):
    """Lấy tên tiến trình từ HWND."""
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        return psutil.Process(pid).name().lower()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return None

def get_screen_dpi_ratio(point):
    """Lấy tỉ lệ DPI của màn hình tại một điểm cụ thể."""
    screen = QApplication.screenAt(point) or QApplication.primaryScreen()
    return screen.devicePixelRatio()

def get_display_config_hash():
    """
    Tạo một hash duy nhất và ỔN ĐỊNH dựa trên cấu hình màn hình hiện tại.
    """
    screens = QApplication.screens()
    # Sắp xếp các màn hình theo toạ độ (x, y) để đảm bảo thứ tự nhất quán
    sorted_screens = sorted(screens, key=lambda s: (s.geometry().x(), s.geometry().y()))
    
    config_str = ";".join([
        f"{s.name()}:{s.geometry().x()},{s.geometry().y()},{s.geometry().width()},{s.geometry().height()}"
        for s in sorted_screens
    ])
    
    # YUUKA FIX: Sử dụng hashlib.sha256 thay vì hash() để đảm bảo hash là nhất quán
    # giữa các lần chạy chương trình.
    return hashlib.sha256(config_str.encode('utf-8')).hexdigest()

def set_startup_status(enabled: bool):
    """
    Thêm hoặc gỡ ứng dụng khỏi danh sách khởi động cùng Windows.
    Sử dụng RUN.bat để đảm bảo môi trường được thiết lập đúng.
    """
    APP_NAME = "YuukaOCR"
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        # Lấy đường dẫn tuyệt đối tới file RUN.bat trong thư mục gốc của project
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        run_bat_path = os.path.join(project_root, "RUN.bat")

        if not os.path.exists(run_bat_path):
            print(f"Yuuka Startup: Lỗi - Không tìm thấy file '{run_bat_path}' để cấu hình startup.")
            return

        # Mở key trong registry của user hiện tại, không cần quyền admin
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
            if enabled:
                # Thêm hoặc cập nhật entry, đặt đường dẫn trong dấu ngoặc kép để xử lý space
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, f'"{run_bat_path}"')
                print("Yuuka Startup: Đã đăng ký khởi động cùng hệ thống.")
            else:
                # Gỡ entry khỏi startup
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    print("Yuuka Startup: Đã gỡ khỏi danh sách khởi động cùng hệ thống.")
                except FileNotFoundError:
                    # Không sao nếu không tìm thấy, có nghĩa là đã được gỡ từ trước
                    pass
    except Exception as e:
        print(f"Yuuka Startup: Lỗi khi thay đổi cài đặt startup: {e}")