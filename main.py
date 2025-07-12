# main.py
import sys
import os
import json
import subprocess

from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt

project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# YUUKA: Import module update mới
from core import update
from core.app_window import MainWindow
from plugins.gemini_ocr import GeminiOCRPlugin

CONFIG_DIR = "config"
USER_DIR = "user"
APP_CONFIG_FILENAME = os.path.join(CONFIG_DIR, "app_configs.json")
USER_CONFIG_FILENAME = os.path.join(USER_DIR, "user_config.json")
ENV_FILENAME = os.path.join(USER_DIR, ".env")

def load_app_configs(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Yuuka: Lỗi! Không tìm thấy file cấu hình ứng dụng: {filepath}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Yuuka: Lỗi định dạng JSON trong file cấu hình ứng dụng: {filepath}")
        sys.exit(1)
    except Exception as e:
        print(f"Yuuka: Lỗi không xác định khi tải cấu hình ứng dụng: {e}")
        sys.exit(1)

def handle_update_result(status_code, message):
    """Xử lý kết quả từ `check_for_updates`, hiển thị UI nếu cần."""
    if status_code == update.UPDATE_STATUS["UPDATED"]:
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)
        msg_box.setText("Yuuka đã được cập nhật!")
        msg_box.setWindowTitle("Cập nhật thành công")
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        install_bat_path = os.path.abspath("INSTALL.bat")
        if os.path.exists(install_bat_path):
            try:
                # Dùng `start` để nó chạy trong một cửa sổ cmd riêng biệt, không block app
                subprocess.Popen(f'start cmd /k "{install_bat_path}"', shell=True)
                msg_box.setInformativeText(
                    "Một phiên bản mới đã được tải về.\n"
                    "File `INSTALL.bat` đang được tự động chạy để cập nhật thư viện.\n\n"
                    "Vui lòng đợi quá trình cài đặt hoàn tất và khởi động lại Yuuka nhé!"
                )
            except Exception as e:
                print(f"Không thể tự động chạy INSTALL.bat: {e}")
                msg_box.setInformativeText(
                    "Một phiên bản mới đã được tải về.\n"
                    "Vui lòng chạy lại `INSTALL.bat` để cập nhật các thư viện cần thiết."
                )
        else:
             msg_box.setInformativeText(
                "Một phiên bản mới đã được tải về.\n"
                "Vui lòng chạy lại `INSTALL.bat` để cập nhật các thư viện cần thiết."
            )

        msg_box.exec()
        sys.exit(0) # Thoát ứng dụng sau khi thông báo để người dùng chạy lại

def main():
    # YUUKA: Chạy check update (chỉ in ra console) trước tiên
    status, message = update.check_for_updates()

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)

    # YUUKA: Xử lý kết quả update (hiển thị GUI nếu cần) sau khi đã có app instance
    handle_update_result(status, message)

    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(USER_DIR, exist_ok=True)

    app_configs = load_app_configs(APP_CONFIG_FILENAME)

    main_window = MainWindow(app_configs, USER_CONFIG_FILENAME)
    gemini_plugin = GeminiOCRPlugin(USER_CONFIG_FILENAME, app_configs)

    # --- Kết nối Signals và Slots giữa Main Window và Plugin ---
    
    # Từ Plugin tới Main Window (cập nhật UI)
    gemini_plugin.updateStatus.connect(main_window.update_status)
    gemini_plugin.resetStatus.connect(main_window.reset_status)
    gemini_plugin.showResult.connect(main_window.handle_show_result)
    gemini_plugin.apiKeyVerified.connect(main_window.handle_api_key_verified)
    gemini_plugin.apiKeyNeeded.connect(main_window.handle_api_key_needed)
    gemini_plugin.apiKeyFailed.connect(main_window.handle_api_key_failed)
    gemini_plugin.processingComplete.connect(main_window.handle_processing_complete)

    # Từ Main Window tới Plugin (yêu cầu xử lý)
    main_window.requestHookedOCR.connect(gemini_plugin.handle_hooked_ocr_request)
    main_window.requestApiKeyVerification.connect(gemini_plugin.handle_api_key_attempt)
    main_window.userConfigChanged.connect(gemini_plugin.handle_user_config_changed)
    main_window.requestFileProcessing.connect(gemini_plugin.handle_file_drop_request)
    
    main_window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()