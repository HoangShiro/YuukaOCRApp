# core/logging.py
import json
import os
import sys
import threading
from datetime import datetime
from collections import deque
from PySide6.QtCore import QObject, Signal

class Logger(QObject):
    message_logged = Signal(str)

    def __init__(self, log_path: str):
        super().__init__()
        self.log_path = log_path
        self.lock = threading.Lock()
        self.log_data = self._load_log()
        self.start_time = datetime.now()

    def _get_default_log_structure(self):
        return {
            "api_calls": {"total": 0, "by_model": {}, "daily": {}},
            "recent_outputs": [],
            "app_runtime": {"total_seconds": 0, "today_seconds": {"date": "1970-01-01", "seconds": 0}},
            "last_session_seconds": 0,
            "source_stats": {
                "text_clipboard": 0, "image_clipboard": 0, "file_clipboard": 0,
                "hooked_ocr": 0, "file_drop": {}
            },
            "recent_prompts": []
        }

    def _load_log(self):
        with self.lock:
            try:
                if os.path.exists(self.log_path):
                    with open(self.log_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    default_data = self._get_default_log_structure()
                    for key, value in default_data.items():
                        if key not in data:
                            data[key] = value
                        elif isinstance(value, dict):
                            for sub_key, sub_value in value.items():
                                if sub_key not in data[key]:
                                    data[key][sub_key] = sub_value
                    return data
                return self._get_default_log_structure()
            except (json.JSONDecodeError, IOError):
                return self._get_default_log_structure()

    def _save_log(self):
        with self.lock:
            try:
                log_copy = self.log_data.copy()
                log_copy['recent_outputs'] = list(log_copy.get('recent_outputs', []))
                log_copy['recent_prompts'] = list(log_copy.get('recent_prompts', []))
                os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
                with open(self.log_path, 'w', encoding='utf-8') as f:
                    json.dump(log_copy, f, ensure_ascii=False, indent=4)
            except IOError as e:
                # YUUKA: Nếu không thể ghi file, in ra console gốc (nếu có)
                if sys.__stderr__:
                    sys.__stderr__.write(f"Lỗi nghiêm trọng khi lưu log: {e}\n")

    def console_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] Yuuka: {message}\n"
        
        # Signal này là cơ chế chính để hiển thị log trong UI, luôn hoạt động
        self.message_logged.emit(formatted_message)

        # YUUKA FIX: Chỉ ghi ra console hệ thống NẾU nó tồn tại.
        # Điều này ngăn ngừa lỗi 'NoneType' object has no attribute 'write'
        # khi chạy với pythonw.exe (không có console).
        if sys.__stdout__:
            sys.__stdout__.write(formatted_message)
            sys.__stdout__.flush()

    def get_logs(self):
        with self.lock:
            return self.log_data.copy()

    def log_api_call(self, model_name: str, success: bool, error_message: str = None):
        with self.lock:
            if success:
                self.console_log(f"Gọi API model '{model_name}' thành công.")
                self.log_data["api_calls"]["total"] = self.log_data["api_calls"].get("total", 0) + 1
                self.log_data["api_calls"]["by_model"][model_name] = self.log_data["api_calls"]["by_model"].get(model_name, 0) + 1
                today_str = datetime.now().strftime("%Y-%m-%d")
                if today_str not in self.log_data["api_calls"]["daily"]:
                    self.log_data["api_calls"]["daily"][today_str] = {}
                daily_model_log = self.log_data["api_calls"]["daily"][today_str]
                daily_model_log[model_name] = daily_model_log.get(model_name, 0) + 1
            else:
                self.console_log(f"Lỗi API: {error_message}")
        self._save_log()

    def add_recent_output(self, text: str):
        with self.lock:
            if 'recent_outputs' not in self.log_data or not isinstance(self.log_data['recent_outputs'], list):
                self.log_data['recent_outputs'] = []
            
            # YUUKA: Tăng giới hạn lên 100
            outputs = deque(self.log_data['recent_outputs'], maxlen=100)
            log_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": text
            }
            outputs.appendleft(log_entry)
            self.log_data['recent_outputs'] = list(outputs)
        self._save_log()

    def add_recent_prompt(self, text: str):
        with self.lock:
            if not text: return
            if 'recent_prompts' not in self.log_data or not isinstance(self.log_data['recent_prompts'], list):
                self.log_data['recent_prompts'] = []

            # YUUKA: Tăng giới hạn lên 100
            prompts = deque(self.log_data['recent_prompts'], maxlen=100)
            if not any(entry['text'] == text for entry in prompts):
                log_entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "text": text
                }
                prompts.appendleft(log_entry)
                self.log_data['recent_prompts'] = list(prompts)
                self.console_log("Prompt tùy chỉnh đã được cập nhật.")
        self._save_log()

    def log_source(self, source_type: str, detail: str = None):
        with self.lock:
            stats = self.log_data["source_stats"]
            if source_type in stats:
                if source_type == "file_drop" and detail:
                    ext = os.path.splitext(detail)[1].lower()
                    if not ext: return
                    stats["file_drop"][ext] = stats["file_drop"].get(ext, 0) + 1
                else:
                    stats[source_type] = stats.get(source_type, 0) + 1
        self._save_log()

    def update_runtime(self):
        with self.lock:
            runtime = self.log_data["app_runtime"]
            session_seconds = (datetime.now() - self.start_time).total_seconds()
            runtime["total_seconds"] = runtime.get("total_seconds", 0) + session_seconds
            today_str = datetime.now().strftime("%Y-%m-%d")
            if runtime["today_seconds"].get("date") == today_str:
                runtime["today_seconds"]["seconds"] += session_seconds
            else:
                runtime["today_seconds"]["date"] = today_str
                runtime["today_seconds"]["seconds"] = session_seconds
            runtime["last_session_seconds"] = session_seconds
        self.start_time = datetime.now()
        self._save_log()

    def clear_log_section(self, section_name: str):
        with self.lock:
            if section_name == "recent_outputs":
                self.log_data["recent_outputs"] = []
                self.console_log("Đã xóa lịch sử output.")
            elif section_name == "recent_prompts":
                self.log_data["recent_prompts"] = []
                self.console_log("Đã xóa lịch sử prompt.")
        self._save_log()