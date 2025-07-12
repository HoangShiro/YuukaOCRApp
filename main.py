# main.py
import sys
import os
import json
import subprocess
import threading

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import update
from core.app_window import MainWindow
from plugins.gemini_ocr import GeminiOCRPlugin

CONFIG_DIR = "config"
USER_DIR = "user"
APP_CONFIG_FILENAME = os.path.join(CONFIG_DIR, "app_configs.json")
USER_CONFIG_FILENAME = os.path.join(USER_DIR, "user_config.json")
ENV_FILENAME = os.path.join(USER_DIR, ".env")

def load_configs(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} # Trả về dict rỗng nếu file không tồn tại hoặc lỗi

def run_install_and_exit():
    """Chạy INSTALL.bat và thoát ứng dụng hiện tại."""
    install_bat_path = os.path.abspath("INSTALL.bat")
    if os.path.exists(install_bat_path):
        try:
            print("Yuuka: Running INSTALL.bat for dependency updates...")
            subprocess.Popen(f'start cmd /c "{install_bat_path}"', shell=True)
        except Exception as e:
            print(f"Yuuka: Could not run INSTALL.bat automatically: {e}")
    else:
        print("Yuuka: INSTALL.bat not found.")
    sys.exit(0)
    
def restart_application():
    """Khởi động lại ứng dụng bằng cách chạy RUN.bat và thoát process hiện tại."""
    print("Yuuka: Restarting application...")
    run_bat_path = os.path.abspath("RUN.bat")
    if os.path.exists(run_bat_path):
        subprocess.Popen([run_bat_path], shell=True)
    else:
        # Fallback nếu không có RUN.bat
        subprocess.Popen([sys.executable] + sys.argv, shell=True)
    QApplication.quit()


def main():
    app = QApplication(sys.argv)

    # Tải cấu hình người dùng trước để kiểm tra cài đặt auto-update
    user_config = load_configs(USER_CONFIG_FILENAME)
    if user_config.get('auto_update_enabled', True):
        # YUUKA FIX: Nhận 3 giá trị trả về từ check_for_updates
        status, message, _ = update.check_for_updates()
        if status == update.UPDATE_STATUS['AHEAD']:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText("Có phiên bản Yuuka mới!")
            msg_box.setInformativeText("Đang tiến hành cập nhật và cài đặt lại các thư viện cần thiết. Vui lòng đợi nhé senpai!")
            msg_box.setWindowTitle("Đang cập nhật")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.show()
            QApplication.processEvents() # Đảm bảo messagebox hiện ra
            
            update.perform_update()
            run_install_and_exit()

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(USER_DIR, exist_ok=True)

    app_configs = load_configs(APP_CONFIG_FILENAME)
    if not app_configs:
         print(f"Yuuka: Lỗi! Không thể tải file cấu hình chính: {APP_CONFIG_FILENAME}")
         sys.exit(1)

    main_window = MainWindow(app_configs, USER_CONFIG_FILENAME)
    gemini_plugin = GeminiOCRPlugin(USER_CONFIG_FILENAME, app_configs)

    # --- Kết nối Signals và Slots ---
    main_window.config_window.requestRestart.connect(restart_application)
    
    gemini_plugin.updateStatus.connect(main_window.update_status)
    gemini_plugin.resetStatus.connect(main_window.reset_status)
    gemini_plugin.showResult.connect(main_window.handle_show_result)
    gemini_plugin.apiKeyVerified.connect(main_window.handle_api_key_verified)
    gemini_plugin.apiKeyNeeded.connect(main_window.handle_api_key_needed)
    gemini_plugin.apiKeyFailed.connect(main_window.handle_api_key_failed)
    
    gemini_plugin.processingStarted.connect(main_window.handle_processing_started)
    gemini_plugin.processingComplete.connect(main_window.handle_processing_complete)

    main_window.requestHookedOCR.connect(gemini_plugin.handle_hooked_ocr_request)
    main_window.requestApiKeyVerification.connect(gemini_plugin.handle_api_key_attempt)
    main_window.userConfigChanged.connect(gemini_plugin.handle_user_config_changed)
    main_window.requestFileProcessing.connect(gemini_plugin.handle_file_drop_request)
    
    main_window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()