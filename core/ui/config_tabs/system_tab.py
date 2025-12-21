# core/ui/config_tabs/system_tab.py
from PySide6.QtWidgets import (QVBoxLayout, QWidget, QCheckBox, QLabel, QFrame,
                               QLineEdit, QPushButton, QHBoxLayout, QStackedWidget,
                               QComboBox, QGroupBox, QTextEdit, QScrollArea, QCompleter)
from PySide6.QtGui import QDesktopServices, QIcon, QPixmap, QPainter
from PySide6.QtCore import QUrl, Qt, QStringListModel, QByteArray

try:
    from PySide6.QtSvg import QSvgRenderer
except Exception:
    QSvgRenderer = None

from plugins.openai_compatible import get_provider_list, PROVIDERS, get_providers_with_api_keys


def _make_edit_icon() -> QIcon:
    """Create a small pencil/edit icon from inline SVG."""
    # Note: Qt's SVG renderer doesn't reliably resolve `currentColor`, so we use white.
    svg = """<svg xmlns=\"http://www.w3.org/2000/svg\" width=\"24\" height=\"24\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"#FFFFFF\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M12 20h9\"/><path d=\"M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z\"/></svg>"""
    if QSvgRenderer is None:
        # Fallback: empty icon (button can still show tooltip)
        return QIcon()
    renderer = QSvgRenderer(QByteArray(svg.encode('utf-8')))
    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


def populate_provider_combo(combo: QComboBox, recent_providers: list = None, providers_with_keys: list = None):
    """
    Populate provider combo with recent providers first, then remaining providers.
    Adds 🔑 icon to providers that have API keys saved.
    
    Args:
        combo: QComboBox to populate
        recent_providers: List of recently used provider IDs (max 5)
        providers_with_keys: List of provider IDs that have API keys saved
    """
    combo.clear()
    if recent_providers is None:
        recent_providers = []
    if providers_with_keys is None:
        providers_with_keys = []
    
    all_providers = get_provider_list()
    provider_dict = {p["id"]: p for p in all_providers}
    added_ids = set()
    
    # Helper function to get display name with key icon
    def get_display_name(provider_id: str, name: str) -> str:
        if provider_id in providers_with_keys:
            return f"{name} 🔑✅"
        return name
    
    # Add recent providers first (up to 5)
    for provider_id in recent_providers[:5]:
        if provider_id in provider_dict and provider_id not in added_ids:
            p = provider_dict[provider_id]
            display_name = get_display_name(provider_id, p["name"])
            combo.addItem(display_name, provider_id)
            added_ids.add(provider_id)
    
    # Add separator if we have recent providers
    if added_ids:
        combo.insertSeparator(combo.count())
    
    # Add remaining providers
    for p in all_providers:
        if p["id"] not in added_ids:
            display_name = get_display_name(p["id"], p["name"])
            combo.addItem(display_name, p["id"])
            added_ids.add(p["id"])


def populate_model_combo(combo: QComboBox, models: list, recent_models: list = None):
    """
    Populate model combo with recent models first, then remaining models.
    Sets up search/filter functionality with QCompleter.
    
    Args:
        combo: QComboBox to populate
        models: Full list of available models
        recent_models: List of recently used model names for this provider (max 5)
    """
    combo.blockSignals(True)
    combo.clear()
    
    if not models:
        combo.addItem("Vui lòng xác thực API key")
        combo.setEnabled(False)
        combo.setEditable(False)
        combo.blockSignals(False)
        return
    
    if recent_models is None:
        recent_models = []
    
    added_models = set()
    all_model_names = []  # For completer
    
    # Add recent models first (up to 5)
    for model in recent_models[:5]:
        if model in models and model not in added_models:
            combo.addItem(model, model)
            added_models.add(model)
            all_model_names.append(model)
    
    # Add separator if we have recent models
    if added_models:
        combo.insertSeparator(combo.count())
    
    # Add remaining models
    for model in models:
        if model not in added_models:
            combo.addItem(model, model)
            added_models.add(model)
            all_model_names.append(model)
    
    # Setup editable mode for search functionality
    combo.setEditable(True)
    combo.setInsertPolicy(QComboBox.NoInsert)  # Don't add typed text as new item
    combo.lineEdit().setPlaceholderText("🔍 Tìm model...")
    
    # Setup completer for filtering
    completer = QCompleter(all_model_names, combo)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)  # Match anywhere in the string
    completer.setCompletionMode(QCompleter.PopupCompletion)
    combo.setCompleter(completer)
    
    combo.setEnabled(True)
    combo.blockSignals(False)

def create_system_tab(self: QWidget) -> QWidget:
    """
    Tạo nội dung cho tab System trong cửa sổ Config.
    'self' ở đây là instance của ConfigWindow.
    """
    # --- Cột trái ---
    left_layout = QVBoxLayout()
    
    general_group = QGroupBox("Cài đặt chung")
    general_layout = QVBoxLayout()
    self.auto_update_cb = QCheckBox("Tự động update khi khởi động")
    self.start_with_system_cb = QCheckBox("Khởi động cùng System")
    self.text_clipboard_cb = QCheckBox("Bật đọc text clipboard")
    self.file_clipboard_cb = QCheckBox("Xử lý file từ clipboard (Ctrl+C)")
    self.snipping_clipboard_cb = QCheckBox("Xử lý Snipping Screen") # <<< YUUKA: THÊM MỚI
    general_layout.addWidget(self.auto_update_cb)
    general_layout.addWidget(self.start_with_system_cb)
    general_layout.addWidget(self.text_clipboard_cb)
    general_layout.addWidget(self.file_clipboard_cb)
    general_layout.addWidget(self.snipping_clipboard_cb) # <<< YUUKA: THÊM MỚI
    general_group.setLayout(general_layout)
    left_layout.addWidget(general_group)

    # Group Kiểm tra Update
    update_group = QGroupBox("Kiểm tra Update")
    update_layout = QVBoxLayout()
    self.update_status_label = QLabel("Đang kiểm tra...")
    self.update_status_label.setWordWrap(True)
    
    # YUUKA FIX: Thay QLabel bằng QTextEdit để xử lý word-wrap và scroll tốt hơn
    self.update_details_label = QTextEdit()
    self.update_details_label.setReadOnly(True) # Không cho người dùng sửa
    self.update_details_label.setObjectName("updateDetailsLabel") # Giữ lại tên để CSS nhận diện
    self.update_details_label.setMaximumHeight(200) # Vẫn giới hạn chiều cao
    self.update_details_label.hide()

    self.update_button = QPushButton("Cập nhật & Khởi động lại")
    self.update_button.hide()
    
    update_layout.addWidget(self.update_status_label)
    # YUUKA: Thêm QTextEdit trực tiếp vào layout, không cần QScrollArea nữa
    update_layout.addWidget(self.update_details_label)
    update_layout.addSpacing(5)
    update_layout.addWidget(self.update_button)
    update_group.setLayout(update_layout)
    left_layout.addWidget(update_group)
    left_layout.addStretch()

    # --- Cột phải ---
    right_layout = QVBoxLayout()
    
    # Header with edit button
    header_layout = QHBoxLayout()
    header_layout.addWidget(QLabel("<b>Cài đặt Prompt & API</b>"))
    header_layout.addStretch()
    self.api_key_editor_toggle_btn = QPushButton()
    self.api_key_editor_toggle_btn.setObjectName("api_key_editor_toggle_btn")
    self.api_key_editor_toggle_btn.setFixedSize(24, 24)
    self.api_key_editor_toggle_btn.setToolTip("Mở Key Editor")
    self.api_key_editor_toggle_btn.setCursor(Qt.PointingHandCursor)
    self.api_key_editor_toggle_btn.setIcon(_make_edit_icon())
    header_layout.addWidget(self.api_key_editor_toggle_btn)
    right_layout.addLayout(header_layout)

    # Stack: normal Prompt & API UI vs Key Editor
    self.prompt_api_stack = QStackedWidget()

    normal_page = QWidget()
    normal_layout = QVBoxLayout(normal_page)
    normal_layout.setContentsMargins(0, 0, 0, 0)
    normal_layout.setSpacing(8)
    self.prompt_enabled_cb = QCheckBox("Bật prompt tùy chỉnh")
    self.custom_prompt_edit = QTextEdit()
    self.custom_prompt_edit.setPlaceholderText("Nhập prompt của bạn...")
    self.custom_prompt_edit.setFixedHeight(100)
    
    # YUUKA UPDATE: Provider selector with link button
    self.provider_label = QLabel("Provider:")
    self.provider_link_button = QPushButton("🔗")
    self.provider_link_button.setObjectName("provider_link_button")
    self.provider_link_button.setFixedSize(24, 24)
    self.provider_link_button.setToolTip("Mở trang web của provider để lấy API key")
    self.provider_link_button.setCursor(Qt.PointingHandCursor)
    
    provider_header_layout = QHBoxLayout()
    provider_header_layout.addWidget(self.provider_label)
    provider_header_layout.addWidget(self.provider_link_button)
    provider_header_layout.addStretch()
    
    self.provider_combo = QComboBox()
    # Initial population with all providers (will be repopulated with recent in load_config)
    providers = get_provider_list()
    for p in providers:
        self.provider_combo.addItem(p["name"], p["id"])
    self.provider_combo.setToolTip("Chọn nhà cung cấp API. Xem danh sách free providers tại:\nhttps://github.com/cheahjs/free-llm-api-resources")
    
    # Custom Base URL (chỉ hiện khi chọn Custom provider)
    self.custom_base_url_label = QLabel("Custom Base URL:")
    self.custom_base_url_edit = QLineEdit()
    self.custom_base_url_edit.setPlaceholderText("https://api.example.com/v1")
    self.custom_base_url_label.hide()
    self.custom_base_url_edit.hide()
    
    # YUUKA UPDATE: Đổi tên từ "Gemini API Key" thành "API Key"
    self.api_key_label = QLabel("API Key:")
    self.api_key_edit = QLineEdit()
    self.api_key_edit.setPlaceholderText("Dán API key vào đây")
    self.api_key_edit.setEchoMode(QLineEdit.Password)
    self.api_key_status_label = QLabel("")
    self.api_key_save_button = QPushButton("Xác thực")
    self.api_key_status_label.setObjectName("api_key_status_label")
    api_hbox = QHBoxLayout()
    api_hbox.addWidget(self.api_key_edit)
    api_hbox.addWidget(self.api_key_save_button)
    
    # YUUKA UPDATE: Đổi tên từ "Model Gemini" thành "Model list"
    self.gemini_model_label = QLabel("Model list:")
    self.gemini_model_combo = QComboBox()
    self.gemini_model_combo.setToolTip("Danh sách model sẽ được tự động lấy sau khi xác thực API key")
    
    normal_layout.addWidget(self.prompt_enabled_cb)
    normal_layout.addWidget(self.custom_prompt_edit)
    normal_layout.addWidget(self._create_line())
    normal_layout.addLayout(provider_header_layout)
    normal_layout.addWidget(self.provider_combo)
    normal_layout.addWidget(self.custom_base_url_label)
    normal_layout.addWidget(self.custom_base_url_edit)
    normal_layout.addWidget(self.api_key_label)
    normal_layout.addLayout(api_hbox)
    normal_layout.addWidget(self.api_key_status_label)
    normal_layout.addWidget(self.gemini_model_label)
    normal_layout.addWidget(self.gemini_model_combo)
    normal_layout.addStretch()

    # Key editor page
    editor_page = QWidget()
    editor_layout = QVBoxLayout(editor_page)
    editor_layout.setContentsMargins(0, 0, 0, 0)
    editor_layout.setSpacing(8)
    editor_layout.addWidget(QLabel("<b>Key Editor</b>"))
    editor_layout.addWidget(QLabel("Mỗi dòng là 1 API key. Lưu xong nhớ bấm 'Xác thực' ở provider bạn dùng để lấy model list."))

    self.key_editor_scroll = QScrollArea()
    self.key_editor_scroll.setObjectName("key_editor_scroll")
    self.key_editor_scroll.setWidgetResizable(True)
    self.key_editor_container = QWidget()
    self.key_editor_container_layout = QVBoxLayout(self.key_editor_container)
    self.key_editor_container_layout.setContentsMargins(0, 0, 0, 0)
    self.key_editor_container_layout.setSpacing(8)
    self.key_editor_text_edits = {}

    for p in get_provider_list():
        pid = p.get('id')
        pname = p.get('name', pid)
        group = QGroupBox(pname)
        group.setObjectName("key_editor_group")
        gl = QVBoxLayout(group)
        te = QTextEdit()
        te.setObjectName("key_editor_text")
        te.setPlaceholderText("key1\nkey2\n...")
        te.setFixedHeight(80)
        gl.addWidget(te)
        self.key_editor_text_edits[pid] = te
        self.key_editor_container_layout.addWidget(group)

    self.key_editor_container_layout.addStretch()
    self.key_editor_scroll.setWidget(self.key_editor_container)
    editor_layout.addWidget(self.key_editor_scroll, stretch=1)

    self.key_editor_status_label = QLabel("")
    self.key_editor_status_label.setObjectName("api_key_status_label")
    self.key_editor_save_button = QPushButton("Lưu Keys")
    self.key_editor_save_button.setObjectName("key_editor_save_button")
    editor_layout.addWidget(self.key_editor_status_label)
    editor_layout.addWidget(self.key_editor_save_button)

    self.prompt_api_stack.addWidget(normal_page)
    self.prompt_api_stack.addWidget(editor_page)
    right_layout.addWidget(self.prompt_api_stack, stretch=1)
    
    return self._create_tab_content_widget(left_layout, right_layout)