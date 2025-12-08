# plugins/gemini_ocr.py
"""
OCR Plugin - supports both Gemini (native) and OpenAI-compatible APIs
"""
import os
import json
import threading
import re
import pyperclip

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    from dotenv import load_dotenv
    from PIL import Image, ImageGrab, PngImagePlugin
    import win32clipboard
    import win32con
except ImportError:
    print("Yuuka: Lỗi! Thiếu thư viện cho Gemini OCR (pywin32, pillow, google-generativeai, python-dotenv).")
    print("Yuuka: Vui lòng cài đặt bằng lệnh: pip install pywin32 pillow google-generativeai python-dotenv")

from PySide6.QtCore import QTimer, QObject, Signal, QRect
from core.logging import Logger
from plugins.openai_compatible import OpenAICompatibleService, PROVIDERS, detect_provider_from_key


class GeminiOCRPlugin(QObject):
    updateStatus = Signal(str, int)
    resetStatus = Signal()
    showResult = Signal(str)
    apiKeyVerified = Signal(str, list)
    apiKeyNeeded = Signal()
    apiKeyFailed = Signal(str) 
    
    processingStarted = Signal()
    processingComplete = Signal()

    def __init__(self, user_config_path, app_configs, logger: Logger):
        super().__init__()
        self.user_config_path = user_config_path
        self.app_configs = app_configs
        self.logger = logger
        self.user_config = {}
        self._load_user_config()

        # Gemini native model
        self.model = None
        self.api_key = None
        
        # OpenAI compatible service
        self.openai_service = OpenAICompatibleService()
        self.current_provider = self._get_user_config_value('api_provider', 'gemini')
        self.current_model_name = self._get_user_config_value('gemini_model', 'gemini-2.5-flash')
        
        self.last_clipboard_content = None
        self.just_copied_by_yuuka = False
        
        self.clipboard_timer = QTimer(self)
        self.clipboard_timer.timeout.connect(self._check_clipboard_content)
        self.clipboard_timer.start(1000)
        
        threading.Thread(target=self._initial_api_setup, daemon=True).start()

    def _load_user_config(self):
        try:
            if os.path.exists(self.user_config_path):
                with open(self.user_config_path, 'r', encoding='utf-8') as f:
                    self.user_config = json.load(f)
        except Exception as e:
            self.logger.console_log(f"Plugin: Lỗi đọc user config: {e}")
        return {}

    def _get_user_config_value(self, key, default=None):
        return self.user_config.get(key, default)

    def _is_gemini_provider(self):
        """Check if current provider is Gemini (uses native SDK)"""
        return self.current_provider == 'gemini'

    def _initial_api_setup(self):
        """Initial setup - load API key from .env and verify"""
        user_dir = os.path.dirname(self.user_config_path)
        env_filepath = os.path.join(user_dir, '.env')
        os.makedirs(user_dir, exist_ok=True)
        load_dotenv(dotenv_path=env_filepath)
        
        # Try to get API key from environment
        api_key = os.getenv('API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            self.apiKeyNeeded.emit()
            return
        
        self._verify_api_key_and_configure(api_key)

    def _verify_api_key_and_configure(self, key):
        """Verify API key and configure the appropriate service"""
        provider = self._get_user_config_value('api_provider', 'gemini')
        self.current_provider = provider
        
        if self._is_gemini_provider():
            self._verify_gemini_key(key)
        else:
            self._verify_openai_compatible_key(key)

    def _verify_gemini_key(self, key):
        """Verify Gemini API key using native SDK"""
        try:
            temp_genai = genai
            temp_genai.configure(api_key=key)
            
            models_list = []
            for m in temp_genai.list_models():
                if 'generateContent' in m.supported_generation_methods and any(name in m.name for name in ['flash', 'pro', 'gemma']):
                    models_list.append(m.name.replace('models/', ''))
            
            if not models_list:
                raise ValueError("Không tìm thấy model Gemini nào khả dụng.")

            # Save API key to .env
            self._save_api_key(key)
            
            self.api_key = key
            self._update_model()
            self.logger.console_log("Đã kết nối với Gemini API thành công!")
            self.apiKeyVerified.emit(key, sorted(models_list, reverse=True))

        except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated, ValueError) as e:
            error_msg = f"Lỗi Gemini API! Key có thể không hợp lệ. Lỗi: {e}"
            self.logger.console_log(error_msg)
            self.api_key = None
            self.model = None
            self.apiKeyFailed.emit(key)
        except Exception as e:
            error_msg = f"Lỗi không xác định khi cấu hình Gemini. Lỗi: {e}"
            self.logger.console_log(error_msg)
            self.api_key = None
            self.model = None
            self.apiKeyFailed.emit(key)

    def _verify_openai_compatible_key(self, key):
        """Verify OpenAI-compatible API key"""
        try:
            custom_base_url = self._get_user_config_value('custom_base_url', '')
            self.openai_service.set_provider(self.current_provider, key, custom_base_url)
            
            provider_name = PROVIDERS.get(self.current_provider, {}).get('name', self.current_provider)
            self.logger.console_log(f"Đang xác thực API key cho {provider_name}...")
            
            success, message, models_list = self.openai_service.verify_api_key()
            
            if success:
                self._save_api_key(key)
                self.api_key = key
                self.model = True  # Mark as ready (not using Gemini model object)
                self.logger.console_log(f"Đã kết nối với {provider_name} thành công! Có {len(models_list)} models.")
                self.apiKeyVerified.emit(key, models_list[:50])  # Limit to 50 models for UI
            else:
                self.logger.console_log(f"Lỗi xác thực {provider_name}: {message}")
                self.api_key = None
                self.model = None
                self.apiKeyFailed.emit(key)
                
        except Exception as e:
            error_msg = f"Lỗi không xác định khi xác thực API: {e}"
            self.logger.console_log(error_msg)
            self.api_key = None
            self.model = None
            self.apiKeyFailed.emit(key)

    def _save_api_key(self, key):
        """Save API key to .env file"""
        user_dir = os.path.dirname(self.user_config_path)
        env_filepath = os.path.join(user_dir, '.env')
        os.makedirs(user_dir, exist_ok=True)
        with open(env_filepath, 'w') as f:
            f.write(f'API_KEY={key}\n')
            # Also keep GOOGLE_API_KEY for backward compatibility
            if self._is_gemini_provider():
                f.write(f'GOOGLE_API_KEY={key}\n')

    def _update_model(self):
        """Update the current model (for Gemini provider only)"""
        if not self._is_gemini_provider():
            return
            
        model_name = self._get_user_config_value('gemini_model', 'gemini-2.5-flash')
        self.current_model_name = model_name
        try:
            if self.model is None or (hasattr(self.model, 'model_name') and self.model.model_name != f"models/{model_name}"):
                self.logger.console_log(f"Đang sử dụng model '{model_name}'")
                self.model = genai.GenerativeModel(model_name, generation_config={"response_mime_type": "application/json"})
        except Exception as e:
            self.logger.console_log(f"Không thể khởi tạo model '{model_name}'. Lỗi: {e}")
            self.updateStatus.emit(f"Lỗi model: {model_name}", 4000)

    def handle_api_key_attempt(self, key):
        if not self.model or self.api_key != key:
            threading.Thread(target=self._verify_api_key_and_configure, args=(key,), daemon=True).start()

    def _check_clipboard_content(self):
        if self.just_copied_by_yuuka: self.just_copied_by_yuuka = False; return
        if not self.model:
            # Auto-detect API key from clipboard for any provider
            try:
                cb_text = pyperclip.paste()
                if cb_text and cb_text.strip() and self._is_new_content(cb_text.strip()):
                    key = cb_text.strip()
                    # Check if it looks like an API key
                    detected_provider = detect_provider_from_key(key)
                    if detected_provider or (len(key) > 20 and key.isalnum() or key.startswith('sk-')):
                        self.last_clipboard_content = key
                        self.handle_api_key_attempt(key)
            except Exception: pass
            return
        
        if self._get_user_config_value('process_snipping_clipboard', True):
            try:
                img = ImageGrab.grabclipboard()
                if isinstance(img, (Image.Image, PngImagePlugin.PngImageFile)) and self._is_new_content(img.tobytes()):
                    self.last_clipboard_content = img.tobytes()
                    self.logger.log_source("image_clipboard")
                    threading.Thread(target=self._process_with_error_handling, args=(self.process_image_in_thread, img), daemon=True).start()
                    return
            except Exception: pass

        if self._get_user_config_value('process_file_clipboard', True):
            try: 
                win32clipboard.OpenClipboard()
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_HDROP):
                    files = win32clipboard.GetClipboardData(win32con.CF_HDROP)
                    if files and self._is_new_content(files[0]):
                        self.last_clipboard_content = files[0]
                        if self._is_valid_file(self.last_clipboard_content):
                            self.logger.log_source("file_clipboard", self.last_clipboard_content)
                            threading.Thread(target=self._process_with_error_handling, args=(self.process_file_in_thread, self.last_clipboard_content), daemon=True).start()
                            try: win32clipboard.CloseClipboard()
                            except Exception: pass
                            return
            except Exception: pass
            finally:
                try: win32clipboard.CloseClipboard()
                except Exception: pass

        if self._get_user_config_value('process_text_clipboard', False):
            try:
                cb_text = pyperclip.paste()
                if cb_text and cb_text.strip() and self._is_new_content(cb_text):
                    self.last_clipboard_content = cb_text
                    self.logger.log_source("text_clipboard")
                    threading.Thread(target=self._process_with_error_handling, args=(self.process_text_in_thread, cb_text), daemon=True).start()
            except Exception: pass

    def _is_new_content(self, content): return content != self.last_clipboard_content
    def _is_valid_file(self, filepath):
        try:
            _, ext = os.path.splitext(filepath); size = os.path.getsize(filepath)
            max_size = self.app_configs["MAX_FILE_SIZE_MB"] * 1024 * 1024
            if ext.lower() not in self.app_configs["ACCEPTED_FILE_EXTENSIONS"]: self.updateStatus.emit("Yuuka: File không hỗ trợ!", 3000); return False
            if size > max_size: self.updateStatus.emit(f"Yuuka: File > {self.app_configs['MAX_FILE_SIZE_MB']}MB!", 3000); return False
            return True
        except Exception: self.updateStatus.emit("Yuuka: Lỗi đọc file!", 3000); return False

    def _get_combined_prompt(self, base_prompt):
        if self._get_user_config_value('prompt_enabled', False):
            custom_prompt = self._get_user_config_value('custom_prompt', '').strip()
            # YUUKA FIX: Chỉ log prompt khi nó thực sự được sử dụng
            if custom_prompt:
                self.logger.add_recent_prompt(custom_prompt)
                return f"{base_prompt}\n\nAdditionally, strictly follow this user instruction: {custom_prompt}"
        return base_prompt

    def process_and_copy_result(self, response_text, model_name):
        """Process response text and copy to clipboard - unified for both APIs"""
        data = None
        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```json"): clean_text = clean_text[7:-3].strip()
            elif clean_text.startswith("```"): clean_text = clean_text[3:-3].strip()
            
            try: 
                data = json.loads(clean_text)
            except json.JSONDecodeError:
                # Cố gắng sửa lỗi JSON không hoàn chỉnh
                key_marker = '"extracted_text": "'; start_idx = clean_text.find(key_marker)
                if start_idx != -1:
                    content_start = start_idx + len(key_marker)
                    end_idx = -1; i = len(clean_text) - 1
                    while i > content_start:
                        if clean_text[i] == '"' and clean_text[i-1] != '\\': end_idx = i; break
                        i -= 1
                    if end_idx != -1:
                         extracted = clean_text[content_start:end_idx].replace('\\"', '"')
                         data = {"extracted_text": extracted}
                if not data: raise # Nếu vẫn không sửa được, ném lỗi ra ngoài

            result_text = data.get("extracted_text", "") if isinstance(data, dict) else str(data)
            if not result_text: 
                self.updateStatus.emit("Yuuka: Hông thấy chữ...", 3000)
                self.logger.log_api_call(model_name, success=True)
                self.processingComplete.emit()
                return

            self.logger.log_api_call(model_name, success=True)
            # YUUKA FIX: Lưu toàn bộ object `data` vào log, không chỉ text
            self.logger.add_recent_output(data)
            
            self.just_copied_by_yuuka = True
            pyperclip.copy(result_text)
            self.last_clipboard_content = result_text
            self.showResult.emit(result_text)
            self.updateStatus.emit("Yuuka: Ctrl + v đi!", 3000)
            
        except Exception as e:
            error_msg = f"Lỗi JSON hoặc xử lý. Response: {response_text[:200]}. Lỗi: {e}"
            self.logger.log_api_call(model_name, success=False, error_message=error_msg)
            # YUUKA FIX: Vẫn lưu output lỗi vào log để debug
            if data: self.logger.add_recent_output(data) 
            else: self.logger.add_recent_output({"error": "Failed to parse JSON", "raw_response": response_text[:500]})
            self.updateStatus.emit("Yuuka: Lỗi response...", 3000)
        finally: 
            self.processingComplete.emit()

    def _process_with_error_handling(self, target_func, *args):
        self.processingStarted.emit()
        self.updateStatus.emit("Yuuka: Đợi chút nha...", 0)
        try:
            if not self.model: 
                self.apiKeyNeeded.emit()
                self.updateStatus.emit("Yuuka: Cần API key!", 3000)
                self.processingComplete.emit()
                return
            target_func(*args)
        except Exception as e:
            model_name = self.current_model_name
            error_msg = f"Lỗi trong thread {target_func.__name__}: {e}"
            self.logger.log_api_call(model_name, success=False, error_message=error_msg)
            self.updateStatus.emit(f"Yuuka: Lỗi! {str(e)[:40]}...", 3000)
            self.processingComplete.emit()

    def process_image_in_thread(self, img):
        """Process image - supports both Gemini and OpenAI-compatible APIs"""
        if img.mode == 'RGBA': img = img.convert('RGB')
        prompt = self._get_combined_prompt('Extract all text from this image. Respond in a strict JSON format like this: {"extracted_text": "all the text you found"}.')
        
        if self._is_gemini_provider():
            response = self.model.generate_content([prompt, img])
            self.process_and_copy_result(response.text, self.model.model_name)
        else:
            result = self.openai_service.generate_content(prompt, image=img, model=self.current_model_name)
            if result["success"]:
                self.process_and_copy_result(result["text"], self.current_model_name)
            else:
                self.logger.log_api_call(self.current_model_name, success=False, error_message=result["error"])
                self.updateStatus.emit(f"Yuuka: {result['error'][:40]}...", 3000)
                self.processingComplete.emit()

    def process_file_in_thread(self, filepath):
        """Process file - supports both Gemini and OpenAI-compatible APIs"""
        self.updateStatus.emit("Yuuka: Uploading file...", 0)
        prompt = self._get_combined_prompt('Analyze this file and extract all text from it. Respond in a strict JSON format like this: {"extracted_text": "all the text you found"}.')
        
        if self._is_gemini_provider():
            uploaded_file = genai.upload_file(path=filepath)
            self.updateStatus.emit("Yuuka: Đợi chút nha...", 0)
            response = self.model.generate_content([prompt, uploaded_file])
            self.process_and_copy_result(response.text, self.model.model_name)
        else:
            # For OpenAI-compatible APIs, check if file is an image
            _, ext = os.path.splitext(filepath)
            image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp']
            
            if ext.lower() in image_exts:
                result = self.openai_service.generate_content(prompt, image_path=filepath, model=self.current_model_name)
            else:
                # For non-image files, read text content (not all providers support file uploads)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        file_content = f.read()
                    full_prompt = f"{prompt}\n\nFile content:\n{file_content}"
                    result = self.openai_service.generate_content(full_prompt, model=self.current_model_name)
                except:
                    result = {"success": False, "text": "", "error": "Không thể đọc file hoặc provider không hỗ trợ."}
            
            if result["success"]:
                self.process_and_copy_result(result["text"], self.current_model_name)
            else:
                self.logger.log_api_call(self.current_model_name, success=False, error_message=result["error"])
                self.updateStatus.emit(f"Yuuka: {result['error'][:40]}...", 3000)
                self.processingComplete.emit()

    def process_text_in_thread(self, text_content):
        """Process text - supports both Gemini and OpenAI-compatible APIs"""
        prompt = self._get_combined_prompt('Process the following text. If a user instruction is provided, follow it. Otherwise, summarize the text. Respond in a strict JSON format like this: {"extracted_text": "your complete response here"}.')
        full_prompt = f"{prompt}\n\nText:\n{text_content}"
        
        if self._is_gemini_provider():
            response = self.model.generate_content(full_prompt)
            self.process_and_copy_result(response.text, self.model.model_name)
        else:
            result = self.openai_service.generate_content(full_prompt, model=self.current_model_name)
            if result["success"]:
                self.process_and_copy_result(result["text"], self.current_model_name)
            else:
                self.logger.log_api_call(self.current_model_name, success=False, error_message=result["error"])
                self.updateStatus.emit(f"Yuuka: {result['error'][:40]}...", 3000)
                self.processingComplete.emit()

    def process_hooked_region_in_thread(self, physical_roi_rect):
        """Process hooked region - supports both Gemini and OpenAI-compatible APIs"""
        self.logger.log_source("hooked_ocr")
        bbox = (physical_roi_rect.x(), physical_roi_rect.y(), physical_roi_rect.right() + 1, physical_roi_rect.bottom() + 1)
        img = ImageGrab.grab(bbox=bbox, all_screens=True)
        if img.mode == 'RGBA': img = img.convert('RGB')
        prompt = self._get_combined_prompt('Extract all text from this image. Respond in a strict JSON format like this: {"extracted_text": "all the text you found"}.')
        
        if self._is_gemini_provider():
            response = self.model.generate_content([prompt, img])
            self.process_and_copy_result(response.text, self.model.model_name)
        else:
            result = self.openai_service.generate_content(prompt, image=img, model=self.current_model_name)
            if result["success"]:
                self.process_and_copy_result(result["text"], self.current_model_name)
            else:
                self.logger.log_api_call(self.current_model_name, success=False, error_message=result["error"])
                self.updateStatus.emit(f"Yuuka: {result['error'][:40]}...", 3000)
                self.processingComplete.emit()

    def handle_hooked_ocr_request(self, physical_roi_rect):
        threading.Thread(target=self._process_with_error_handling, args=(self.process_hooked_region_in_thread, physical_roi_rect), daemon=True).start()

    def handle_file_drop_request(self, filepath):
        if self._is_valid_file(filepath):
            self.logger.log_source("file_drop", detail=filepath)
            threading.Thread(target=self._process_with_error_handling, args=(self.process_file_in_thread, filepath), daemon=True).start()
        else:
            self.processingComplete.emit()

    def handle_user_config_changed(self, new_config):
        old_provider = self.user_config.get('api_provider', 'gemini')
        new_provider = new_config.get('api_provider', 'gemini')
        old_model = self.user_config.get('gemini_model')
        new_model = new_config.get('gemini_model')
        
        # Update current model name
        self.current_model_name = new_model or self.current_model_name
        
        # Check if provider changed
        if old_provider != new_provider:
            self.logger.console_log(f"Provider được đổi từ '{old_provider}' thành '{new_provider}'.")
            self.current_provider = new_provider
            # Reset model state - need to re-verify API key
            self.model = None
            self.api_key = None
        elif old_model != new_model:
            self.logger.console_log(f"Model được đổi từ '{old_model}' thành '{new_model}'.")
            
        self.user_config = new_config
        
        # Update OpenAI service with new settings
        if not self._is_gemini_provider():
            custom_base_url = new_config.get('custom_base_url', '')
            if self.api_key:
                self.openai_service.set_provider(self.current_provider, self.api_key, custom_base_url)
        elif self.api_key:
            self._update_model()