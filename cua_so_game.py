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
DUONG_DAN_PID_CLIENT_AN = os.path.join(THU_MUC_APP, "pid_client_an.json")
_cua_so_da_an = {}
_pid_can_an = set()
_pid_client_an = set()
_khoa_an = threading.RLock()


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


def _la_cua_so_game_hop_le(hwnd):
    """Cửa sổ top-level Game.exe đủ lớn (kể cả IsWindowVisible=False — cột Ẩn AutoHoc)."""
    if not win32gui.IsWindow(hwnd):
        return False
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    try:
        if psutil.Process(pid).name().lower() != TEN_TIEN_TRINH_GAME:
            return False
    except psutil.Error:
        return False
    if win32gui.IsIconic(hwnd):
        return True
    try:
        _, _, rong, cao = vung_client(hwnd)
    except win32gui.error:
        return False
    return rong >= KICH_THUOC_TOI_THIEU[0] and cao >= KICH_THUOC_TOI_THIEU[1]


def _dien_tich_client(hwnd):
    try:
        _, _, rong, cao = vung_client(hwnd)
        return rong * cao
    except win32gui.error:
        return 0


def tim_hwnd_chinh_game_pid(pid):
    """Cửa sổ game chính của pid (kể cả đang ẩn), None nếu không có."""
    if not pid:
        return None
    candidates = []

    def cb(hwnd, _):
        if win32process.GetWindowThreadProcessId(hwnd)[1] != pid:
            return True
        if _la_cua_so_game_hop_le(hwnd):
            candidates.append(hwnd)
        return True

    try:
        win32gui.EnumWindows(cb, None)
    except win32gui.error:
        return None
    if not candidates:
        return None
    return max(candidates, key=_dien_tich_client)


def tim_cua_so_game():
    """
    Duyệt tất cả cửa sổ đang mở, giữ lại những cửa sổ thuộc tiến trình Game.exe.
    Mỗi phần tử trả về là dict gồm: hwnd (mã cửa sổ), pid (mã tiến trình), tieu_de.
    Client ẩn (SW_HIDE) vẫn được liệt kê nếu process Game.exe còn chạy.
    """
    ket_qua = []
    da_hwnd = set()

    def them(hwnd):
        if hwnd in da_hwnd:
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        da_hwnd.add(hwnd)
        ket_qua.append({
            "hwnd": hwnd,
            "pid": pid,
            "tieu_de": win32gui.GetWindowText(hwnd),
        })

    def xu_ly_tung_cua_so(hwnd, _):
        if _la_cua_so_game_hop_le(hwnd):
            them(hwnd)
        return True

    win32gui.EnumWindows(xu_ly_tung_cua_so, None)

    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if (proc.info.get("name") or "").lower() != TEN_TIEN_TRINH_GAME:
                continue
            pid = proc.info["pid"]
        except (psutil.Error, TypeError):
            continue
        if any(c["pid"] == pid for c in ket_qua):
            continue
        hwnd = tim_hwnd_chinh_game_pid(pid)
        if hwnd:
            them(hwnd)
    with _khoa_an:
        for pid in list(_pid_client_an):
            if not _process_game_con_song(pid):
                _pid_client_an.discard(pid)
                continue
            if any(c["pid"] == pid for c in ket_qua):
                continue
            hwnd = tim_hwnd_chinh_game_pid(pid)
            if hwnd:
                them(hwnd)
        if _pid_client_an:
            _luu_pid_client_an()
    return ket_qua


def _process_game_con_song(pid):
    try:
        if not isinstance(pid, int) or pid <= 0:
            return False
        return psutil.Process(pid).name().lower() == TEN_TIEN_TRINH_GAME
    except (psutil.Error, ValueError, TypeError):
        return False


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


def _tai_pid_client_an():
    global _pid_client_an
    try:
        with open(DUONG_DAN_PID_CLIENT_AN, encoding="utf-8") as f:
            ds = json.load(f)
    except (OSError, ValueError, TypeError):
        return
    if isinstance(ds, list):
        _pid_client_an = {int(p) for p in ds if p and int(p) > 0}


def _luu_pid_client_an():
    try:
        with open(DUONG_DAN_PID_CLIENT_AN, "w", encoding="utf-8") as f:
            json.dump(sorted(_pid_client_an), f)
    except OSError:
        pass


def ghi_pid_client_an(pid):
    """Client ẩn (cột Ẩn AutoHoc): nhớ pid để lần mở AutoHoc sau vẫn quét được process."""
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return
    if pid <= 0:
        return
    with _khoa_an:
        if pid not in _pid_client_an:
            _pid_client_an.add(pid)
            _luu_pid_client_an()


def xoa_pid_client_an(pid=None):
    with _khoa_an:
        if pid is None:
            _pid_client_an.clear()
        else:
            try:
                _pid_client_an.discard(int(pid))
            except (TypeError, ValueError):
                pass
        _luu_pid_client_an()


_tai_pid_client_an()


def cac_cua_so_da_an():
    """Các hwnd auto đã ẩn mà game vẫn còn mở."""
    with _khoa_an:
        for hwnd, pid in list(_cua_so_da_an.items()):
            if not _con_la_cua_so_da_an(hwnd, pid):
                del _cua_so_da_an[hwnd]
        return set(_cua_so_da_an)


def duy_tri_an():
    """Re-hide cửa sổ game đã ẩn (client tự ShowWindow sau đổi map / đăng nhập). Trả về số lần gọi SW_HIDE."""
    so = 0
    pids = set()
    with _khoa_an:
        for hwnd, pid in list(_cua_so_da_an.items()):
            if not _con_la_cua_so_da_an(hwnd, pid):
                del _cua_so_da_an[hwnd]
                continue
            if win32gui.IsWindowVisible(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                so += 1
        pids = set(_pid_can_an)
    if pids:
        for cua_so in tim_cua_so_game():
            hwnd, pid = cua_so["hwnd"], cua_so["pid"]
            if pid not in pids:
                continue
            with _khoa_an:
                if hwnd not in _cua_so_da_an:
                    _cua_so_da_an[hwnd] = pid
            if win32gui.IsWindowVisible(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_HIDE)
                so += 1
    if so:
        with _khoa_an:
            _luu_cua_so_da_an()
    return so


def an_cua_so(cac_hwnd):
    """Ẩn các cửa sổ game (không đổi vị trí, game vẫn chạy). Trả về số cửa sổ đã ẩn."""
    so = 0
    with _khoa_an:
        for hwnd in cac_hwnd:
            if win32gui.IsWindow(hwnd) and win32gui.IsWindowVisible(hwnd):
                pid = _pid_cua(hwnd)
                _cua_so_da_an[hwnd] = pid
                _pid_can_an.add(pid)
                ghi_pid_client_an(pid)
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
        _pid_can_an.clear()
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
