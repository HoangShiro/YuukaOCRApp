# plugins/gemini_ocr.py
import os
import json
import threading
import re
import pyperclip

try:
    import google.generativeai as genai
    from dotenv import load_dotenv
    from PIL import Image, ImageGrab, PngImagePlugin
    import win32clipboard
    import win32con
except ImportError:
    print("Yuuka: Lỗi! Thiếu thư viện cho Gemini OCR (pywin32, pillow, google-generativeai, python-dotenv).")
    print("Yuuka: Vui lòng cài đặt bằng lệnh: pip install pywin32 pillow google-generativeai python-dotenv")

from PySide6.QtCore import QTimer, QObject, Signal, QRect

class GeminiOCRPlugin(QObject):
    updateStatus = Signal(str, int)
    resetStatus = Signal()
    showResult = Signal(str)
    apiKeyVerified = Signal(str)
    apiKeyNeeded = Signal()
    apiKeyFailed = Signal(str) 
    processingComplete = Signal()

    def __init__(self, user_config_path, app_configs):
        super().__init__()
        self.user_config_path = user_config_path
        self.app_configs = app_configs
        self.model = None
        self.api_key = None
        self.last_clipboard_content = None
        self.just_copied_by_yuuka = False
        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.timeout.connect(self._check_clipboard_content)
        self.clipboard_timer.start(1000)
        threading.Thread(target=self._initial_gemini_setup, daemon=True).start()

    def _load_user_config_value(self, key, default=None):
        try:
            if os.path.exists(self.user_config_path):
                with open(self.user_config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get(key, default)
        except Exception as e:
            print(f"Yuuka Plugin: Lỗi đọc user config '{key}': {e}")
        return default

    def _initial_gemini_setup(self):
        user_dir = os.path.dirname(self.user_config_path)
        env_filepath = os.path.join(user_dir, '.env')
        os.makedirs(user_dir, exist_ok=True)
        load_dotenv(dotenv_path=env_filepath)
        api_key = os.getenv('GOOGLE_API_KEY')
        if not api_key: self.apiKeyNeeded.emit(); return
        self._verify_api_key_and_configure(api_key)

    def _verify_api_key_and_configure(self, key):
        try:
            temp_genai = genai; temp_genai.configure(api_key=key); _ = next(temp_genai.list_models()) 
            user_dir = os.path.dirname(self.user_config_path); env_filepath = os.path.join(user_dir, '.env')
            os.makedirs(user_dir, exist_ok=True)
            with open(env_filepath, 'w') as f: f.write(f'GOOGLE_API_KEY={key}\n')
            self.api_key = key
            self.model = genai.GenerativeModel('gemini-2.0-flash', generation_config={"response_mime_type": "application/json"})
            print("Yuuka Plugin: Đã kết nối với Gemini API thành công!")
            self.apiKeyVerified.emit(key)
        except Exception as e:
            print(f"Yuuka Plugin: Lỗi cấu hình Gemini! Key có thể không hợp lệ. Lỗi: {e}")
            self.api_key = None; self.model = None; self.apiKeyFailed.emit(key)

    def handle_api_key_attempt(self, key):
        if not self.model or self.api_key != key:
            self.updateStatus.emit("Yuuka: Đang thử key...", 0)
            threading.Thread(target=self._verify_api_key_and_configure, args=(key,), daemon=True).start()

    def _check_clipboard_content(self):
        if self.just_copied_by_yuuka: self.just_copied_by_yuuka = False; return
        if not self.model:
            try:
                cb_text = pyperclip.paste()
                if cb_text and cb_text.strip().startswith('AIza') and self._is_new_content(cb_text.strip()):
                    self.last_clipboard_content = cb_text.strip(); self.handle_api_key_attempt(self.last_clipboard_content)
            except Exception: pass
            return
        try: # Image
            img = ImageGrab.grabclipboard()
            if isinstance(img, (Image.Image, PngImagePlugin.PngImageFile)) and self._is_new_content(img.tobytes()):
                self.last_clipboard_content = img.tobytes()
                threading.Thread(target=self._process_with_error_handling, args=(self.process_image_in_thread, img), daemon=True).start()
                return
        except Exception: pass

        # NEW: Respect the user setting for file clipboard processing
        if self._load_user_config_value('process_file_clipboard', True):
            try: # File
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                    files = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                    if files and self._is_new_content(files[0]):
                        self.last_clipboard_content = files[0]
                        if self._is_valid_file(self.last_clipboard_content):
                            threading.Thread(target=self._process_with_error_handling, args=(self.process_file_in_thread, self.last_clipboard_content), daemon=True).start()
                            # Return here after closing clipboard
                            try: win32clipboard.CloseClipboard()
                            except Exception: pass
                            return
            except Exception: pass
            finally:
                try: win32clipboard.CloseClipboard()
                except Exception: pass

        if self._load_user_config_value('process_text_clipboard', False): # Text
            try:
                cb_text = pyperclip.paste()
                if cb_text and cb_text.strip() and self._is_new_content(cb_text):
                    self.last_clipboard_content = cb_text
                    threading.Thread(target=self._process_with_error_handling, args=(self.process_text_in_thread, cb_text), daemon=True).start()
            except Exception: pass

    def _is_new_content(self, content): return content != self.last_clipboard_content
    def _is_valid_file(self, filepath):
        try:
            _, ext = os.path.splitext(filepath)
            size = os.path.getsize(filepath)
            max_size = self.app_configs["MAX_FILE_SIZE_MB"] * 1024 * 1024
            if ext.lower() not in self.app_configs["ACCEPTED_FILE_EXTENSIONS"]: self.updateStatus.emit("Yuuka: File không hỗ trợ!", 3000); return False
            if size > max_size: self.updateStatus.emit(f"Yuuka: File > {self.app_configs['MAX_FILE_SIZE_MB']}MB!", 3000); return False
            return True
        except Exception: self.updateStatus.emit("Yuuka: Lỗi đọc file!", 3000); return False

    def _get_combined_prompt(self, base_prompt):
        if self._load_user_config_value('prompt_enabled', False):
            custom_prompt = self._load_user_config_value('custom_prompt', '').strip()
            if custom_prompt: return f"{base_prompt}\n\nAdditionally, strictly follow this user instruction: {custom_prompt}"
        return base_prompt

    def process_and_copy_result(self, response):
        try:
            clean_text = response.text.strip()
            if clean_text.startswith("```json"): clean_text = clean_text[7:-3].strip()
            elif clean_text.startswith("```"): clean_text = clean_text[3:-3].strip()
            data = None
            try: data = json.loads(clean_text)
            except json.JSONDecodeError:
                key_marker = '"extracted_text": "'; start_idx = clean_text.find(key_marker)
                if start_idx != -1 and clean_text.endswith('"}'):
                    content_start = start_idx + len(key_marker); content_end = len(clean_text) - 2
                    fixed_json = clean_text[:content_start] + re.sub(r'(?<!\\)"', r'\\"', clean_text[content_start:content_end]) + clean_text[content_end:]
                    data = json.loads(fixed_json)
                else: raise
            result_text = data.get("extracted_text", "") if data else ""
            if not result_text: self.updateStatus.emit("Yuuka: Hông thấy chữ...", 3000); return
            self.just_copied_by_yuuka = True; pyperclip.copy(result_text)
            self.last_clipboard_content = result_text
            self.showResult.emit(result_text)
            self.updateStatus.emit("Yuuka: Ctrl + v đi!", 3000)
        except Exception as e:
            failed_text = response.text if hasattr(response, 'text') else str(response)
            print(f"Yuuka Plugin: Lỗi JSON hoặc xử lý. Response: {failed_text}. Lỗi: {e}")
            self.updateStatus.emit("Yuuka: Lỗi response...", 3000)
        finally: self.processingComplete.emit()

    def _process_with_error_handling(self, target_func, *args):
        self.updateStatus.emit("Yuuka: Đợi chút nha...", 0)
        try:
            if not self.model:
                self.updateStatus.emit("Yuuka: Cần API key!", 3000)
                self.apiKeyNeeded.emit()
                self.processingComplete.emit() # Make sure to emit this
                return

            target_func(*args)
        except Exception as e:
            self.updateStatus.emit(f"Yuuka: Lỗi! {str(e)[:40]}...", 3000)
            print(f"Yuuka Plugin: Lỗi trong thread {target_func.__name__}: {e}")
            self.processingComplete.emit()

    def process_image_in_thread(self, img):
        if img.mode == 'RGBA': img = img.convert('RGB')
        prompt = self._get_combined_prompt('Extract all text from this image. Respond in a strict JSON format like this: {"extracted_text": "all the text you found"}.')
        response = self.model.generate_content([prompt, img]); self.process_and_copy_result(response)

    def process_file_in_thread(self, filepath):
        self.updateStatus.emit("Yuuka: Uploading file...", 0)
        uploaded_file = genai.upload_file(path=filepath)
        self.updateStatus.emit("Yuuka: Đợi chút nha...", 0)
        prompt = self._get_combined_prompt('Analyze this file and extract all text from it. Respond in a strict JSON format like this: {"extracted_text": "all the text you found"}.')
        response = self.model.generate_content([prompt, uploaded_file]); self.process_and_copy_result(response)

    def process_text_in_thread(self, text_content):
        prompt = self._get_combined_prompt('Process the following text. If a user instruction is provided, follow it. Otherwise, summarize the text. Respond in a strict JSON format like this: {"extracted_text": "your complete response here"}.')
        response = self.model.generate_content([prompt, text_content]); self.process_and_copy_result(response)

    def process_hooked_region_in_thread(self, physical_roi_rect):
        bbox = (physical_roi_rect.x(), physical_roi_rect.y(), physical_roi_rect.right() + 1, physical_roi_rect.bottom() + 1)
        img = ImageGrab.grab(bbox=bbox, all_screens=True)
        if img.mode == 'RGBA': img = img.convert('RGB')
        prompt = self._get_combined_prompt('Extract all text from this image. Respond in a strict JSON format like this: {"extracted_text": "all the text you found"}.')
        response = self.model.generate_content([prompt, img]); self.process_and_copy_result(response)

    def handle_hooked_ocr_request(self, physical_roi_rect):
        threading.Thread(target=self._process_with_error_handling, args=(self.process_hooked_region_in_thread, physical_roi_rect), daemon=True).start()

    # NEW: Slot for handling file drops on main window
    def handle_file_drop_request(self, filepath):
        if self._is_valid_file(filepath):
            threading.Thread(target=self._process_with_error_handling, args=(self.process_file_in_thread, filepath), daemon=True).start()
        else:
            self.processingComplete.emit() # Make sure to reset status if file is invalid

    def handle_user_config_changed(self, new_config): pass