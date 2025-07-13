# launcher.pyw
import sys
import ctypes
import traceback

def show_error_message(title, text):
    """Sử dụng ctypes để hiển thị một MessageBox của Windows gốc."""
    # MB_OK = 0x00000000
    # MB_ICONERROR = 0x00000010
    ctypes.windll.user32.MessageBoxW(0, str(text), str(title), 0x10)

def main():
    try:
        # Tạm thời chuyển hướng stderr để bắt lỗi từ các module C (nếu có)
        # mà không ghi ra console.
        original_stderr = sys.stderr
        sys.stderr = open('startup_error.log', 'w', encoding='utf-8')

        # Đây là nơi chúng ta thực sự chạy ứng dụng chính
        from main import main as run_app
        run_app()

    except Exception as e:
        # Nếu có bất kỳ lỗi nào xảy ra trong quá trình khởi tạo,
        # chúng ta sẽ bắt nó ở đây.
        
        # Lấy thông tin traceback chi tiết
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb_details = traceback.format_exception(exc_type, exc_value, exc_traceback)
        error_string = "".join(tb_details)

        # Tạo một thông báo lỗi thân thiện với người dùng
        title = "Yuuka OCR - Lỗi Khởi Động"
        message = (
            "Senpai ơi, Yuuka gặp sự cố khi đang khởi động! (╥_╥)\n\n"
            "Đây là chi tiết lỗi, senpai có thể chụp ảnh màn hình và gửi cho developer nhé:\n\n"
            f"{error_string}"
        )
        show_error_message(title, message)
        
    finally:
        # Đảm bảo đóng file log và khôi phục stderr
        if 'original_stderr' in locals() and sys.stderr != original_stderr:
            sys.stderr.close()
            sys.stderr = original_stderr
        
if __name__ == "__main__":
    main()