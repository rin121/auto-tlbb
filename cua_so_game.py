"""
Các hàm dùng chung để tìm và chụp cửa sổ game.
"""
import ctypes
import json
import os
import sys
import threading
import time

import psutil
import win32con
import win32gui
import win32process

from thu_muc import THU_MUC_APP

# Máy chạy client TLBB thường để locale tiếng Trung (bảng mã GBK), in tiếng Việt sẽ bị lỗi nếu không đổi.
# Chạy bằng pythonw (không có cửa sổ console) thì sys.stdout là None.
if sys.stdout:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TEN_TIEN_TRINH_GAME = "game.exe"

# Cửa sổ nhỏ hơn kích thước này thường là cửa sổ phụ (bộ gõ, popup...), không phải màn hình game.
KICH_THUOC_TOI_THIEU = (400, 300)

# Cửa sổ game auto đã ẩn vẫn tính là game đang mở. Lưu ra file (hwnd, pid) để AutoHoc bị tắt ngang
# thì lần mở sau hiện lại được, không để game chạy mà không thấy cửa sổ.
DUONG_DAN_CUA_SO_DA_AN = os.path.join(THU_MUC_APP, "cua_so_da_an.json")
_cua_so_da_an = {}
_khoa_an = threading.Lock()


def bat_dpi_awareness():
    """
    Nếu Windows đang để Scale 125%/150%, tọa độ Python đọc được sẽ bị lệch so với thực tế.
    Gọi hàm này một lần ở đầu chương trình để tọa độ khớp với pixel thật trên màn hình.
    """
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        ctypes.windll.user32.SetProcessDPIAware()


def vung_client(hwnd):
    """
    Trả về (x, y, rộng, cao) của phần bên trong cửa sổ game (không tính viền và thanh tiêu đề),
    tính theo tọa độ màn hình.
    """
    _, _, rong, cao = win32gui.GetClientRect(hwnd)
    x, y = win32gui.ClientToScreen(hwnd, (0, 0))
    return x, y, rong, cao


def chup_cua_so(hwnd):
    """Chụp vùng client của HWND (game hoặc GAuto/ChickenAuto)."""
    from PIL import ImageGrab

    x, y, rong, cao = vung_client(hwnd)
    return ImageGrab.grab(bbox=(x, y, x + rong, y + cao), all_screens=True)


def dua_cua_so_len_truoc(hwnd):
    """Chụp ảnh theo vùng màn hình nên cửa sổ game phải nằm trên cùng, không bị che."""
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    try:
        win32gui.SetForegroundWindow(hwnd)
    except win32gui.error:
        pass
    time.sleep(0.5)


def tim_cua_so_game():
    """
    Duyệt tất cả cửa sổ đang mở, giữ lại những cửa sổ thuộc tiến trình Game.exe.
    Mỗi phần tử trả về là dict gồm: hwnd (mã cửa sổ), pid (mã tiến trình), tieu_de.
    """
    ket_qua = []

    def xu_ly_tung_cua_so(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd) and hwnd not in _cua_so_da_an:
            return True

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        try:
            ten_tien_trinh = psutil.Process(pid).name().lower()
        except psutil.Error:
            return True
        if ten_tien_trinh != TEN_TIEN_TRINH_GAME:
            return True

        if not win32gui.IsIconic(hwnd):
            _, _, rong, cao = vung_client(hwnd)
            if rong < KICH_THUOC_TOI_THIEU[0] or cao < KICH_THUOC_TOI_THIEU[1]:
                return True

        ket_qua.append({
            "hwnd": hwnd,
            "pid": pid,
            "tieu_de": win32gui.GetWindowText(hwnd),
        })
        return True

    win32gui.EnumWindows(xu_ly_tung_cua_so, None)
    return ket_qua


def _pid_cua(hwnd):
    return win32process.GetWindowThreadProcessId(hwnd)[1]


def _con_la_cua_so_da_an(hwnd, pid):
    return win32gui.IsWindow(hwnd) and _pid_cua(hwnd) == pid


def _luu_cua_so_da_an():
    try:
        with open(DUONG_DAN_CUA_SO_DA_AN, "w", encoding="utf-8") as f:
            json.dump([[hwnd, pid] for hwnd, pid in _cua_so_da_an.items()], f)
    except OSError:
        pass


def cac_cua_so_da_an():
    """Các hwnd auto đã ẩn mà game vẫn còn mở."""
    with _khoa_an:
        for hwnd, pid in list(_cua_so_da_an.items()):
            if not _con_la_cua_so_da_an(hwnd, pid):
                del _cua_so_da_an[hwnd]
        return set(_cua_so_da_an)


def an_cua_so(cac_hwnd):
    """Ẩn các cửa sổ game (không đổi vị trí, game vẫn chạy). Trả về số cửa sổ đã ẩn."""
    so = 0
    with _khoa_an:
        for hwnd in cac_hwnd:
            if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                _cua_so_da_an[hwnd] = _pid_cua(hwnd)
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                so += 1
        _luu_cua_so_da_an()
    return so


def hien_cua_so():
    """Hiện lại mọi cửa sổ auto đã ẩn, đúng vị trí và kích thước lúc ẩn. Trả về số cửa sổ đã hiện."""
    so = 0
    with _khoa_an:
        for hwnd, pid in list(_cua_so_da_an.items()):
            if _con_la_cua_so_da_an(hwnd, pid):
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWNA)
                so += 1
        _cua_so_da_an.clear()
        _luu_cua_so_da_an()
    return so


def hien_lai_cua_so_an_lan_truoc():
    """Lần trước AutoHoc tắt lúc còn ẩn game thì hiện lại. Trả về số cửa sổ đã hiện."""
    try:
        with open(DUONG_DAN_CUA_SO_DA_AN, encoding="utf-8") as f:
            ds = json.load(f)
    except (OSError, ValueError):
        return 0
    with _khoa_an:
        for hwnd, pid in ds:
            _cua_so_da_an[hwnd] = pid
    return hien_cua_so()
