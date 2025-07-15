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
        self.lock = threading.RLock() 
        self.log_data = self._load_log()
        
        # YUUKA FIX: Chạy hàm dọn dẹp prompt trùng lặp khi khởi tạo
        self._cleanup_duplicate_prompts()

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
                    # Đảm bảo các key mới nhất tồn tại trong file log cũ
                    default_data = self._get_default_log_structure()
                    for key, value in default_data.items():
                        if key not in data:
                            data[key] = value
                        elif isinstance(value, dict):
                            # Đảm bảo các sub-key cũng tồn tại
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
                # Tạo bản sao sâu để tránh lỗi thread-safety với deque
                log_copy = self.log_data.copy()
                log_copy['recent_outputs'] = list(log_copy.get('recent_outputs', []))
                log_copy['recent_prompts'] = list(log_copy.get('recent_prompts', []))
                
                os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
                with open(self.log_path, 'w', encoding='utf-8') as f:
                    json.dump(log_copy, f, ensure_ascii=False, indent=4)
            except IOError as e:
                # Ghi ra stderr nếu có lỗi nghiêm trọng
                if sys.__stderr__:
                    sys.__stderr__.write(f"Lỗi nghiêm trọng khi lưu log: {e}\n")

    def console_log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] Yuuka: {message}\n"
        self.message_logged.emit(formatted_message)
        # In ra console gốc nếu có thể
        if sys.__stdout__:
            sys.__stdout__.write(formatted_message)
            sys.__stdout__.flush()

    def get_logs(self):
        with self.lock:
            # Trả về một bản sao để đảm bảo an toàn thread
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

    def add_recent_output(self, data: object):
        """ YUUKA FIX: Thay đổi signature từ text: str sang data: object để lưu trữ nhất quán """
        with self.lock:
            if 'recent_outputs' not in self.log_data or not isinstance(self.log_data['recent_outputs'], list):
                self.log_data['recent_outputs'] = []
            
            outputs = deque(self.log_data['recent_outputs'], maxlen=100)
            log_entry = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "text": data # Lưu object `data` trực tiếp
            }
            outputs.appendleft(log_entry)
            self.log_data['recent_outputs'] = list(outputs)
        self._save_log()

    def add_recent_prompt(self, text: str):
        with self.lock:
            if not text: return
            if 'recent_prompts' not in self.log_data or not isinstance(self.log_data['recent_prompts'], list):
                self.log_data['recent_prompts'] = []

            prompts = deque(self.log_data['recent_prompts'], maxlen=100)
            
            # Chỉ thêm nếu prompt chưa tồn tại trong lịch sử gần đây
            if not any(entry.get('text') == text for entry in prompts):
                log_entry = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "text": text
                }
                prompts.appendleft(log_entry)
                self.log_data['recent_prompts'] = list(prompts)
                self.console_log("Prompt đã được sử dụng và lưu vào lịch sử.")
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
            
            if runtime.get("today_seconds", {}).get("date") == today_str:
                runtime["today_seconds"]["seconds"] += session_seconds
            else:
                runtime["today_seconds"] = {"date": today_str, "seconds": session_seconds}
                
            runtime["last_session_seconds"] = session_seconds
        
        self.start_time = datetime.now() # Reset timer cho session tiếp theo
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

    def _cleanup_duplicate_prompts(self):
        """ YUUKA'S NEW FUNCTION: Dọn dẹp các prompt trùng lặp, chỉ giữ lại cái mới nhất """
        with self.lock:
            all_prompts = self.log_data.get('recent_prompts', [])
            if not all_prompts:
                return

            latest_prompts = {}
            # Lặp qua tất cả các prompt và lưu lại prompt mới nhất cho mỗi nội dung text
            for entry in all_prompts:
                # Bỏ qua các entry không hợp lệ
                if not isinstance(entry, dict) or 'text' not in entry or 'timestamp' not in entry:
                    continue
                
                text = entry['text']
                if text not in latest_prompts or entry['timestamp'] > latest_prompts[text]['timestamp']:
                    latest_prompts[text] = entry
            
            # Sắp xếp lại danh sách duy nhất theo timestamp giảm dần
            unique_list = sorted(latest_prompts.values(), key=lambda x: x['timestamp'], reverse=True)
            
            # Nếu có sự thay đổi, ghi lại vào log
            if len(unique_list) < len(all_prompts):
                num_removed = len(all_prompts) - len(unique_list)
                self.log_data['recent_prompts'] = unique_list
                self.console_log(f"Đã dọn dẹp, loại bỏ {num_removed} prompt trùng lặp.")
                self._save_log()