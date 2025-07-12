# core/update.py
import subprocess
import sys
import os

UPDATE_STATUS = {
    "UP_TO_DATE": 0,
    "UPDATED": 1,
    "GIT_NOT_FOUND": 2,
    "NOT_A_GIT_REPO": 3,
    "FETCH_FAILED": 4,
    "UPDATE_FAILED": 5,
}

def run_command(command):
    """Chạy một command và trả về output, ẩn cửa sổ console."""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    # YUUKA: Chạy command trong thư mục gốc của project
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding='utf-8',
        startupinfo=startupinfo,
        cwd=project_root # Đảm bảo lệnh git chạy đúng chỗ
    )

def check_for_updates():
    """
    Kiểm tra và cập nhật repo Git.
    Trả về một status code từ UPDATE_STATUS và một thông báo.
    """
    print("Yuuka: Checking for updates...")

    # Kiểm tra xem có phải là repo Git không
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(os.path.join(project_root, '.git')):
        print("  [INFO] Not a Git repository. Skipping auto-update.")
        return UPDATE_STATUS["NOT_A_GIT_REPO"], "Not a Git repository. Skipping auto-update."

    # Kiểm tra Git có được cài đặt không
    result = run_command(['git', '--version'])
    if result.returncode != 0:
        print("  [INFO] Git not found. Skipping auto-update.")
        return UPDATE_STATUS["GIT_NOT_FOUND"], "Git not found. Skipping auto-update."
    
    # 1. Fetch updates
    print("  Fetching updates from server...")
    result = run_command(['git', 'fetch', 'origin'])
    if result.returncode != 0:
        print(f"  [ERROR] Failed to fetch from origin: {result.stderr.strip()}")
        return UPDATE_STATUS["FETCH_FAILED"], f"Fetch failed: {result.stderr.strip()}"

    # 2. Lấy local và remote hash
    local_hash_res = run_command(['git', 'rev-parse', 'HEAD'])
    remote_hash_res = run_command(['git', 'rev-parse', 'origin/main']) # Giả sử nhánh chính là 'main'

    if local_hash_res.returncode != 0 or remote_hash_res.returncode != 0:
        error_msg = local_hash_res.stderr.strip() or remote_hash_res.stderr.strip()
        print(f"  [ERROR] Could not get commit hashes. {error_msg}")
        return UPDATE_STATUS["FETCH_FAILED"], f"Could not get commit hashes: {error_msg}"

    local_hash = local_hash_res.stdout.strip()
    remote_hash = remote_hash_res.stdout.strip()

    # 3. So sánh và cập nhật
    if local_hash == remote_hash:
        print("  Application is up to date.")
        return UPDATE_STATUS["UP_TO_DATE"], "Application is up to date."
    else:
        print("  New version available! Forcing update...")
        reset_result = run_command(['git', 'reset', '--hard', 'origin/main'])
        
        if reset_result.returncode == 0:
            msg = "Update successful! Please run INSTALL.bat again to update dependencies before relaunching."
            print(f"  {msg}")
            return UPDATE_STATUS["UPDATED"], msg
        else:
            msg = f"Update failed: {reset_result.stderr.strip()}"
            print(f"  [ERROR] {msg}")
            return UPDATE_STATUS["UPDATE_FAILED"], msg