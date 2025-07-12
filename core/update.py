# core/update.py
import subprocess
import sys
import os

UPDATE_STATUS = {
    "CHECKING": -1,
    "UP_TO_DATE": 0,
    "AHEAD": 1,         # Có bản cập nhật
    "GIT_NOT_FOUND": 2,
    "NOT_A_GIT_REPO": 3,
    "FETCH_FAILED": 4,
    "ERROR": 5,         # Lỗi chung
    "UPDATED": 6,       # Đã cập nhật thành công
    "UPDATE_FAILED": 7, # Cập nhật thất bại
}

def run_command(command):
    """Chạy một command và trả về output, ẩn cửa sổ console."""
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding='utf-8',
        startupinfo=startupinfo,
        cwd=project_root
    )

def check_for_updates():
    """
    Kiểm tra xem có bản cập nhật hay không.
    Trả về một tuple: (status_code, message, commit_details).
    commit_details là một dict {'message': str, 'date': str} hoặc None.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(os.path.join(project_root, '.git')):
        return UPDATE_STATUS["NOT_A_GIT_REPO"], "Đây không phải là một repo Git.", None

    if run_command(['git', '--version']).returncode != 0:
        return UPDATE_STATUS["GIT_NOT_FOUND"], "Không tìm thấy Git trên hệ thống.", None
    
    fetch_result = run_command(['git', 'fetch', 'origin'])
    if fetch_result.returncode != 0:
        return UPDATE_STATUS["FETCH_FAILED"], f"Lỗi khi fetch: {fetch_result.stderr.strip()}", None

    local_hash = run_command(['git', 'rev-parse', 'HEAD']).stdout.strip()
    remote_hash = run_command(['git', 'rev-parse', 'origin/main']).stdout.strip()
    
    if not local_hash or not remote_hash:
        return UPDATE_STATUS["ERROR"], "Không thể lấy thông tin commit.", None

    if local_hash == remote_hash:
        return UPDATE_STATUS["UP_TO_DATE"], "Bạn đang ở phiên bản mới nhất.", None
    else:
        is_ancestor = run_command(['git', 'merge-base', '--is-ancestor', 'HEAD', 'origin/main'])
        if is_ancestor.returncode == 0:
            # Có update, lấy thông tin commit mới nhất từ remote
            commit_message_res = run_command(['git', 'log', '-1', '--pretty=%B', 'origin/main'])
            commit_date_res = run_command(['git', 'log', '-1', '--pretty=%ci', 'origin/main'])

            if commit_message_res.returncode == 0 and commit_date_res.returncode == 0:
                commit_details = {
                    "message": commit_message_res.stdout.strip(),
                    "date": commit_date_res.stdout.strip()
                }
                return UPDATE_STATUS["AHEAD"], "Có phiên bản mới! Sẵn sàng cập nhật.", commit_details
            else:
                return UPDATE_STATUS["AHEAD"], "Có phiên bản mới! (Không lấy được chi tiết).", None
        else:
             return UPDATE_STATUS["UP_TO_DATE"], "Repo đã bị thay đổi. Vui lòng cập nhật thủ công.", None


def perform_update():
    """
    Thực hiện việc cập nhật bằng git reset.
    Trả về một status code và một thông báo.
    """
    print("Yuuka: Performing hard reset to origin/main...")
    reset_result = run_command(['git', 'reset', '--hard', 'origin/main'])
    
    if reset_result.returncode == 0:
        msg = "Cập nhật thành công!"
        print(f"  {msg}")
        return UPDATE_STATUS["UPDATED"], msg
    else:
        msg = f"Cập nhật thất bại: {reset_result.stderr.strip()}"
        print(f"  [ERROR] {msg}")
        return UPDATE_STATUS["UPDATE_FAILED"], msg