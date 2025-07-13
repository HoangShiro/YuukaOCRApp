"""
YuukaOCR/
├── main.py                  # Điểm khởi đầu, điều phối chính của ứng dụng
├── RUN.bat                    # Script để chạy app, đảm bảo môi trường đúng
├── INSTALL.bat                # Script cài đặt/cập nhật thư viện
│
├── config/
│   └── app_configs.json       # Cấu hình mặc định, ít thay đổi của app
│
├── core/
│   ├── __init__.py
│   ├── app_window.py          # Lớp MainWindow: Giao diện chính, quản lý cửa sổ con
│   ├── physics.py             # Lớp PhysicsMovableWidget: Xử lý vật lý di chuyển
│   ├── update.py              # Logic kiểm tra và thực hiện update qua Git
│   ├── utils.py               # Các hàm tiện ích cấp thấp (Win32, Registry)
│   ├── logging.py             # # MỚI # Hệ thống ghi log trung tâm (Logger class)
│   │
│   └── ui/
│       ├── __init__.py
│       ├── config_window.py   # Lớp ConfigWindow: Cửa sổ cài đặt chính
│       ├── themed_sub_window.py # Lớp cơ sở cho các cửa sổ phụ (Result, Notification)
│       ├── snipping_widgets.py  # Lớp cho việc cắt màn hình (Snipping, Overlay)
│       ├── hotkey_button.py     # Lớp nút bấm để ghi lại phím tắt
│       ├── console_stream.py    # # MỚI # Lớp để chuyển hướng output console vào UI
│       │
│       └── config_tabs/       # # MỚI # Module chứa code cho từng tab trong ConfigWindow
│           ├── __init__.py
│           ├── system_tab.py
│           ├── theme_tab.py
│           ├── layout_physics_tab.py
│           ├── hooking_tab.py
│           ├── log_tab.py
│           └── console_tab.py
│
├── plugins/
│   ├── __init__.py
│   └── gemini_ocr.py          # Lớp GeminiOCRPlugin: "Bộ não" xử lý backend, API
│
└── user/                      # Thư mục dành riêng cho người dùng
    ├── .env                   # Lưu trữ API key bí mật
    ├── user_config.json       # Lưu trữ tất cả cài đặt của người dùng
    ├── log.json               # # MỚI # File log ghi lại hoạt động của app
    └── ui.png                 # (Tùy chọn) Giao diện tùy chỉnh của người dùng

    
graph TD
    subgraph "Người dùng"
        A[Tương tác: Kéo/Thả, Click, Gõ phím]
    end

    subgraph "Lớp Giao diện (Frontend)"
        B[MainWindow - app_window.py]
        B1[ConfigWindow - config_window.py]
        B2[SnippingWidget]
        B3[Result/Notification Window]
        C[HotkeyListener - Thread]

        A --> B
        A --> C
        B -- Mở --> B1
        B -- Mở --> B2
        B -- Hiển thị --> B3
    end

    subgraph "Lớp Logic (Backend)"
        D[GeminiOCRPlugin - gemini_ocr.py]
        D1[Clipboard Poller - QTimer]
        D2[API Call - Thread]

        D -- Chạy nền --> D1
    end

    subgraph "Hệ thống Phụ trợ"
        E[Logger - logging.py]
        F[user_config.json]
        G[log.json]
        H[API Gemini]
    end

    %% -- Luồng Tương tác --

    %% UI -> Backend (Request)
    B -- requestFileProcessing / requestHookedOCR --> D
    B1 -- apiKeySubmitted --> D
    C -- hotkeyTriggered --> B -- trigger_hooked_ocr --> D

    %% Backend Polling
    D1 -- Tìm thấy ảnh/file/text --> D

    %% Backend Processing
    D -- Bắt đầu xử lý --> D2
    D2 -- Gọi API --> H

    %% Backend -> UI (Response)
    H -- Trả kết quả --> D2
    D2 -- Xử lý xong --> D
    D -- updateStatus / showResult / apiKeyVerified / processingComplete --> B
    
    %% Tương tác với hệ thống Log
    B -- Sử dụng/Ghi log --> E
    D -- Sử dụng/Ghi log --> E
    B1 -- Đọc log --> E
    E -- Đọc/Ghi --> G

    %% Tương tác với Config
    B1 -- Đọc/Ghi --> F
    D -- Đọc --> F
    B -- Đọc --> F
    

### **Yuuka OCR - Simplified Functional Diagram (English)**

#### 1. Startup & Main Flow (`main.py`)
The application's entry point and coordinator.
- **On Launch**: Loads `user_config.json` to check the `auto_update` setting.
- **If Auto-Update is `true` & Update Found**:
    - Executes `update.perform_update()` (a `git reset --hard`).
    - Runs `INSTALL.bat` to update dependencies.
    - Exits the application.
- **Normal Launch**:
    - Initializes `QApplication`.
    - Creates `MainWindow` (the UI layer).
    - Creates `GeminiOCRPlugin` (the backend engine).
    - **Connects signals and slots**: This is the crucial communication link.
        - UI requests (`MainWindow`) → Backend actions (`GeminiOCRPlugin`).
        - Backend results (`GeminiOCRPlugin`) → UI updates (`MainWindow`).
    - Shows the `MainWindow` and starts the application event loop.

---

#### 2. MainWindow: The UI & Interaction Layer (`core/app_window.py`)
The user-facing component that handles all direct interactions and visual state.

- **Core UI & State**:
    - Based on `PhysicsMovableWidget` for smooth, bouncy movement.
    - Borderless/transparent, with its appearance defined by `ui.png`.
    - Manages the lifecycle and positioning of all sub-windows (`Config`, `Result`, `Notification`).
    - Tracks internal states like `is_hooked`, `is_processing_request`.

- **Window Hooking System**:
    - **Detect**: On drag-and-drop, it scans for nearby windows.
    - **Hook**: Attaches to the top or bottom edge of the closest valid window.
    - **Maintain**: A `QTimer` (`maintain_hook_position`) keeps it "stuck" to the target window, following its movements and resizes.
    - **Unhook**: Detaches if the target window closes or if Yuuka is dragged too far away.

- **On-Demand OCR Flow (Click-to-Text)**:
    - **Trigger**: User presses the `hook_ocr_hotkey` while hooked to a window.
    - **First-time Snip**: If no area is selected, it hides the main UI and shows the full-screen `SnippingWidget`.
    - **On Area Selection**:
        - `SnippingWidget` emits a signal with the selected `QRect`.
        - `MainWindow` saves this region, shows a dashed `SelectionOverlayWidget` over it.
        - **Emits `requestHookedOCR` signal** with the region's physical screen coordinates.
    - **Re-OCR**: If an area was already selected, pressing the hotkey again re-runs OCR on the same saved region.

- **Other User Interactions**:
    - **Mouse Click**: Checks pixel color on `ui.png` to trigger Close/Config actions, or initiates dragging.
    - **Mouse Wheel**: Adjusts UI scale.
    - **File Drop**: Accepts a file drop and **emits `requestFileProcessing` signal**.

---

#### 3. GeminiOCRPlugin: The Backend Engine (`plugins/gemini_ocr.py`)
The non-visual "engine room" that handles all background tasks and API communication.

- **Initialization & Authentication**:
    - On startup, a **background thread** loads the API key from `.env`.
    - **Emits `apiKeyVerified`** with available models on success.
    - **Emits `apiKeyNeeded` or `apiKeyFailed`** on failure, guiding the user.

- **Clipboard Polling (`QTimer`)**:
    - Every second, `_check_clipboard_content` runs.
    - It checks for new **Images**, copied **Files** (`CF_HDROP`), or **Text**.
    - To prevent duplicates, it compares the new content against `last_clipboard_content`.
    - If new, valid content is found, it **starts a new processing thread** (e.g., `process_image_in_thread`).

- **Core Task Processing (in Threads)**:
    - **All API calls are non-blocking**, running in separate threads to keep the UI responsive.
    - A task is started by a signal from `MainWindow` or by the clipboard poller.
    - **Emits `processingStarted`** to notify `MainWindow`.
    - Builds a prompt (base prompt + optional user prompt).
    - Calls the Gemini API (`model.generate_content`), uploading files if necessary.
    - The entire process is wrapped in a `try...except` block for robust error handling.

- **Result Handling & Response**:
    - After the API call, `process_and_copy_result` is executed.
    - It parses the JSON response from Gemini.
    - Copies the extracted text to the system clipboard.
    - **Emits `showResult`** (for `ResultDisplayWindow`).
    - **Emits `updateStatus`** (for a temporary notification, e.g., "Copied!").
    - **Emits `processingComplete`** to reset `MainWindow`'s `is_processing_request` state.

---

#### 4. Supporting Modules
Utilities and self-contained components that support the main layers.

- **`core/utils.py`**: Low-level, OS-specific helper functions (e.g., `get_true_window_rect` via Win32 API, `set_startup_status` in registry).
- **`core/physics.py`**: The `PhysicsMovableWidget` class, providing the physics simulation for widget movement.
- **`core/update.py`**: Standalone functions for interacting with Git to check for and apply updates.
- **`core/ui/` (Package)**: A dedicated package containing all sub-window and component classes, keeping the UI code organized (`ConfigWindow`, `SnippingWidget`, `themed_sub_window.py`, etc.).
"""