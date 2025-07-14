# main.py
import sys
import os
import json
import subprocess
import time

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTimer

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core import update
from core.app_window import MainWindow
from plugins.gemini_ocr import GeminiOCRPlugin
from core.logging import Logger

CONFIG_DIR = "config"
USER_DIR = "user"
APP_CONFIG_FILENAME = os.path.join(CONFIG_DIR, "app_configs.json")
USER_CONFIG_FILENAME = os.path.join(USER_DIR, "user_config.json")
LOG_FILENAME = os.path.join(USER_DIR, "log.json")
ENV_FILENAME = os.path.join(USER_DIR, ".env")

def load_configs(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {} 

def run_install_and_exit():
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
    print("Yuuka: Restarting application...")
    run_bat_path = os.path.abspath("RUN.bat")
    if os.path.exists(run_bat_path):
        subprocess.Popen([run_bat_path], shell=True)
    else:
        # Fallback if RUN.bat is missing
        subprocess.Popen([sys.executable] + sys.argv, shell=True)
    QApplication.quit()


def main():
    app = QApplication(sys.argv)
    
    # Logger giờ là QObject, phải được tạo sau QApplication
    logger = Logger(LOG_FILENAME)
    # Tạm thời print ra console gốc trước khi logger sẵn sàng
    print(f"[{time.strftime('%H:%M:%S')}] Yuuka: Ứng dụng đang khởi động...")
    
    user_config = load_configs(USER_CONFIG_FILENAME)
    if user_config.get('auto_update_enabled', True):
        # YUUKA: Unpack giá trị boolean mới (requirements_changed)
        status, message, _, requirements_changed = update.check_for_updates()
        if status == update.UPDATE_STATUS['AHEAD']:
            logger.console_log("Phát hiện phiên bản mới, bắt đầu cập nhật.")
            
            update_msg = "Đang tiến hành cập nhật."
            if requirements_changed:
                update_msg += "\nCác thư viện sẽ được cài đặt lại. Vui lòng đợi nhé senpai!"
            else:
                update_msg += "\nSẽ khởi động lại ngay sau khi xong!"

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText("Có phiên bản Yuuka mới!")
            msg_box.setInformativeText(update_msg)
            msg_box.setWindowTitle("Đang cập nhật")
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.show()
            QApplication.processEvents()
            
            update.perform_update()

            # YUUKA: Logic điều kiện mới
            if requirements_changed:
                logger.console_log("`requirements.txt` đã thay đổi, đang chạy INSTALL.bat...")
                run_install_and_exit()
            else:
                logger.console_log("`requirements.txt` không thay đổi, chỉ khởi động lại ứng dụng.")
                restart_application()
                sys.exit(0) # Thoát tiến trình hiện tại sau khi đã yêu cầu khởi động lại

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(USER_DIR, exist_ok=True)

    app_configs = load_configs(APP_CONFIG_FILENAME)
    if not app_configs:
         logger.console_log(f"LỖI NGHIÊM TRỌNG! Không thể tải file cấu hình chính: {APP_CONFIG_FILENAME}")
         sys.exit(1)

    runtime_timer = QTimer()
    runtime_timer.timeout.connect(logger.update_runtime)
    runtime_timer.start(60000)
    app.aboutToQuit.connect(logger.update_runtime)

    main_window = MainWindow(app_configs, USER_CONFIG_FILENAME, logger)
    gemini_plugin = GeminiOCRPlugin(USER_CONFIG_FILENAME, app_configs, logger)

    # KẾT NỐI VÀNG: Kết nối signal của Logger tới slot của ConfigWindow một cách an toàn
    logger.message_logged.connect(main_window.config_window.append_to_console_display)

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

    logger.console_log("Giao diện chính đã được hiển thị.")
    sys.exit(app.exec())

if __name__ == "__main__":
    main()