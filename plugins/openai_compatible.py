# plugins/openai_compatible.py
"""
OpenAI Compatible API Service for Yuuka OCR
Supports multiple providers: OpenRouter, Groq, GitHub Models, Cerebras, etc.
"""
import os
import json
import base64
import requests
from typing import Optional, Dict, List, Any, Tuple
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    print("Yuuka: Lỗi! Thiếu thư viện Pillow.")

# Provider configurations with base URLs and model list endpoints
PROVIDERS = {
    "gemini": {
        "name": "Google AI Studio (Gemini)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "api_type": "gemini",  # Uses native Gemini SDK
        "key_prefix": "AIza",
        "docs_url": "https://aistudio.google.com/",
        "supports_vision": True,
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "api_type": "openai",
        "key_prefix": "sk-or-",
        "docs_url": "https://openrouter.ai/",
        "supports_vision": True,
        "extra_headers": {
            "HTTP-Referer": "https://github.com/HoangShiro/YuukaOCR",
            "X-Title": "YuukaOCR"
        }
    },
    "groq": {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "api_type": "openai",
        "key_prefix": "gsk_",
        "docs_url": "https://console.groq.com/",
        "supports_vision": True,
    },
    "github": {
        "name": "GitHub Models",
        "base_url": "https://models.inference.ai.azure.com",
        "api_type": "openai",
        "key_prefix": "github_pat_",  # or ghp_
        "docs_url": "https://github.com/marketplace/models",
        "supports_vision": True,
    },
    "cerebras": {
        "name": "Cerebras",
        "base_url": "https://api.cerebras.ai/v1",
        "api_type": "openai",
        "key_prefix": "csk-",
        "docs_url": "https://cloud.cerebras.ai/",
        "supports_vision": False,
    },
    "mistral": {
        "name": "Mistral AI",
        "base_url": "https://api.mistral.ai/v1",
        "api_type": "openai",
        "key_prefix": "",  # Mistral uses various formats
        "docs_url": "https://console.mistral.ai/",
        "supports_vision": True,
    },
    "sambanova": {
        "name": "SambaNova",
        "base_url": "https://api.sambanova.ai/v1",
        "api_type": "openai",
        "key_prefix": "",
        "docs_url": "https://cloud.sambanova.ai/",
        "supports_vision": False,
    },
    "huggingface": {
        "name": "HuggingFace Inference",
        "base_url": "https://api-inference.huggingface.co/v1",
        "api_type": "openai",
        "key_prefix": "hf_",
        "docs_url": "https://huggingface.co/docs/inference-providers/",
        "supports_vision": True,
    },
    "custom": {
        "name": "Custom (OpenAI Compatible)",
        "base_url": "",  # User provides
        "api_type": "openai",
        "key_prefix": "",
        "docs_url": "",
        "supports_vision": True,
    }
}


class OpenAICompatibleService:
    """Service for interacting with OpenAI-compatible APIs"""
    
    def __init__(self, provider: str = "openrouter", api_key: str = "", custom_base_url: str = ""):
        self.provider = provider
        self.api_key = api_key
        self.custom_base_url = custom_base_url
        self._session = requests.Session()
        
    @property
    def provider_config(self) -> Dict:
        """Get current provider configuration"""
        return PROVIDERS.get(self.provider, PROVIDERS["openrouter"])
    
    @property
    def base_url(self) -> str:
        """Get the base URL for the current provider"""
        if self.provider == "custom":
            return self.custom_base_url.rstrip('/')
        return self.provider_config.get("base_url", "")
    
    def set_provider(self, provider: str, api_key: str = "", custom_base_url: str = ""):
        """Change the active provider"""
        self.provider = provider
        self.api_key = api_key
        self.custom_base_url = custom_base_url
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        # Add provider-specific headers
        extra_headers = self.provider_config.get("extra_headers", {})
        headers.update(extra_headers)
        return headers
    
    def verify_api_key(self) -> Tuple[bool, str, List[str]]:
        """
        Verify API key and fetch available models.
        Returns: (success, message, models_list)
        """
        if not self.api_key:
            return False, "API key không được để trống.", []
        
        if not self.base_url:
            return False, "Base URL không được để trống.", []
        
        try:
            response = self._session.get(
                f"{self.base_url}/models",
                headers=self._get_headers(),
                timeout=15
            )
            
            if response.status_code == 401:
                return False, "API key không hợp lệ hoặc đã hết hạn.", []
            
            if response.status_code == 403:
                return False, "Không có quyền truy cập API.", []
                
            if response.status_code != 200:
                return False, f"Lỗi API: {response.status_code} - {response.text[:100]}", []
            
            data = response.json()
            models = self._parse_models_response(data)
            
            if not models:
                return False, "Không tìm thấy model nào khả dụng.", []
            
            return True, "Xác thực thành công!", models
            
        except requests.exceptions.Timeout:
            return False, "Timeout khi kết nối đến API.", []
        except requests.exceptions.RequestException as e:
            return False, f"Lỗi kết nối: {str(e)[:50]}", []
        except Exception as e:
            return False, f"Lỗi không xác định: {str(e)[:50]}", []
    
    def _parse_models_response(self, data: Dict) -> List[str]:
        """Parse models list from API response"""
        models = []
        
        if "data" in data and isinstance(data["data"], list):
            # Standard OpenAI format
            for model in data["data"]:
                model_id = model.get("id", "")
                if model_id:
                    models.append(model_id)
        elif isinstance(data, list):
            # Some providers return a direct list
            for model in data:
                if isinstance(model, dict):
                    model_id = model.get("id", model.get("name", ""))
                elif isinstance(model, str):
                    model_id = model
                else:
                    continue
                if model_id:
                    models.append(model_id)
        
        # Filter and sort models - prioritize chat/vision models
        priority_keywords = ['gpt', 'claude', 'llama', 'gemma', 'mistral', 'qwen', 'vision', 'chat']
        
        def model_priority(m):
            m_lower = m.lower()
            for i, kw in enumerate(priority_keywords):
                if kw in m_lower:
                    return (i, m)
            return (len(priority_keywords), m)
        
        models.sort(key=model_priority)
        return models
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string"""
        if image.mode == 'RGBA':
            image = image.convert('RGB')
        
        buffer = BytesIO()
        image.save(buffer, format="JPEG", quality=85)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    def _file_to_base64(self, filepath: str) -> Tuple[str, str]:
        """
        Read file and return base64 + mime type.
        Returns: (base64_data, mime_type)
        """
        ext = os.path.splitext(filepath)[1].lower()
        mime_types = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg', 
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp',
            '.bmp': 'image/bmp',
        }
        
        mime_type = mime_types.get(ext, 'application/octet-stream')
        
        with open(filepath, 'rb') as f:
            data = base64.b64encode(f.read()).decode('utf-8')
        
        return data, mime_type
    
    def generate_content(self, prompt: str, image: Optional[Image.Image] = None, 
                         image_path: Optional[str] = None, model: str = "") -> Dict[str, Any]:
        """
        Generate content using the API.
        Returns: {"success": bool, "text": str, "error": str}
        """
        if not model:
            return {"success": False, "text": "", "error": "Chưa chọn model."}
        
        messages = []
        content = []
        
        # Add text prompt
        content.append({"type": "text", "text": prompt})
        
        # Add image if provided
        if image is not None:
            base64_data = self._image_to_base64(image)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_data}"
                }
            })
        elif image_path and os.path.exists(image_path):
            base64_data, mime_type = self._file_to_base64(image_path)
            content.append({
                "type": "image_url", 
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_data}"
                }
            })
        
        messages.append({"role": "user", "content": content})
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 4096,
        }
        
        # Only add response_format for non-vision requests or if provider supports it
        # Some providers don't support JSON mode with vision
        has_image = image is not None or (image_path and os.path.exists(image_path))
        if not has_image:
            payload["response_format"] = {"type": "json_object"}
        
        try:
            response = self._session.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=payload,
                timeout=60
            )
            
            if response.status_code != 200:
                error_text = response.text[:300] if response.text else f"Status {response.status_code}"
                # Parse error message for better user feedback
                user_error = self._parse_error_message(error_text, model)
                return {"success": False, "text": "", "error": user_error}
            
            data = response.json()
            
            # Extract text from response
            if "choices" in data and len(data["choices"]) > 0:
                message = data["choices"][0].get("message", {})
                text = message.get("content", "")
                return {"success": True, "text": text, "error": ""}
            else:
                return {"success": False, "text": "", "error": "Không có response từ API."}
                
        except requests.exceptions.Timeout:
            return {"success": False, "text": "", "error": "Timeout khi gọi API."}
        except Exception as e:
            return {"success": False, "text": "", "error": f"Lỗi: {str(e)[:100]}"}

    def _parse_error_message(self, error_text: str, model: str) -> str:
        """Parse API error and return user-friendly message"""
        error_lower = error_text.lower()
        
        # Check for vision not supported error
        if "image input is not enabled" in error_lower or "vision" in error_lower and "not supported" in error_lower:
            return f"Model '{model}' không hỗ trợ xử lý ảnh! Hãy chọn model có hỗ trợ vision (ví dụ: pixtral, llava, gpt-4o, claude-3)."
        
        # Check for model not found
        if "model not found" in error_lower or "does not exist" in error_lower:
            return f"Model '{model}' không tồn tại hoặc không khả dụng."
        
        # Check for rate limit
        if "rate limit" in error_lower or "too many requests" in error_lower:
            return "Đã vượt quá giới hạn request. Vui lòng đợi một chút."
        
        # Check for invalid API key
        if "unauthorized" in error_lower or "invalid api key" in error_lower:
            return "API key không hợp lệ hoặc đã hết hạn."
        
        # Check for content too large
        if "too large" in error_lower or "maximum" in error_lower and "token" in error_lower:
            return "Nội dung quá lớn, vui lòng thử với ảnh nhỏ hơn."
        
        # Default: return truncated error
        return f"API Error: {error_text[:150]}"


def get_provider_list() -> List[Dict[str, str]]:
    """Get list of available providers for UI dropdown"""
    return [
        {"id": pid, "name": pconfig["name"], "docs_url": pconfig.get("docs_url", "")}
        for pid, pconfig in PROVIDERS.items()
    ]


def detect_provider_from_key(api_key: str) -> Optional[str]:
    """Try to detect provider based on API key prefix"""
    if not api_key:
        return None
    
    for pid, pconfig in PROVIDERS.items():
        prefix = pconfig.get("key_prefix", "")
        if prefix and api_key.startswith(prefix):
            return pid
    
    return None
