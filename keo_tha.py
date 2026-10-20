"""
KÉO THẢ BẰNG CHUỘT THẬT TRONG CỬA SỔ GAME.

Game đọc vị trí chuột từ con trỏ thật (GetCurMousePos chỉ đổi khi cửa sổ game đang được chọn), nên PostMessage
WM_LBUTTONDOWN / WM_MOUSEMOVE không kéo được gì. Kéo thả qua engine thì game tự lưu lên server (vd. thanh phím tắt);
Button:SetActionItem chỉ đổi hình trên giao diện.
Cách làm: đưa cửa sổ game lên trước, đặt con trỏ, nhấn - di từ từ - thả, rồi trả con trỏ và cửa sổ cũ về.
Mất khoảng 1-2 giây, trong lúc đó người dùng đừng động chuột.
"""
import threading
import time

import win32api
import win32con
import win32gui

from dang_nhap import trong_cua_so

KHOA_CHUOT = threading.Lock()
SO_BUOC_DI = 10
SO_LAN_LEN_TRUOC = 5


class LoiKeoTha(Exception):
    pass


def tam_nut(lua, cua_so, ten_nut):
    """Tâm nút (toạ độ trong vùng client) theo Button:GetPixelRect() -> trái, phải, trên, dưới."""
    phan = lua.chay(trong_cua_so(cua_so, f'local l, r, t, b = {ten_nut}:GetPixelRect() '
                                         f'return l .. "," .. r .. "," .. t .. "," .. b')).split(b",")
    trai, phai, tren, duoi = (int(float(x)) for x in phan)
    return (trai + phai) // 2, (tren + duoi) // 2


def _len_truoc(hwnd):
    """Đưa cửa sổ lên trước. Windows có lúc vẫn từ chối (vừa có cửa sổ khác giành) nên thử lại vài lần."""
    if win32gui.IsIconic(hwnd):
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    for _ in range(SO_LAN_LEN_TRUOC):
        # Windows chặn SetForegroundWindow từ tiến trình nền; nhấn-thả Alt giả thì được phép.
        win32api.keybd_event(win32con.VK_MENU, 0, 0, 0)
        try:
            win32gui.SetForegroundWindow(hwnd)
        except win32gui.error:
            pass
        finally:
            win32api.keybd_event(win32con.VK_MENU, 0, win32con.KEYEVENTF_KEYUP, 0)
        time.sleep(0.3)
        if win32gui.GetForegroundWindow() == hwnd:
            return
        try:
            win32gui.BringWindowToTop(hwnd)
        except win32gui.error:
            pass
        time.sleep(0.5)
    raise LoiKeoTha("không đưa được cửa sổ game lên trước")


def _thuoc_game(hwnd, diem):
    return win32gui.GetAncestor(win32gui.WindowFromPoint(diem), win32con.GA_ROOT) == hwnd


def bam(hwnd, diem):
    """Bấm chuột trái tại điểm (toạ độ client của cửa sổ game hwnd)."""
    keo(hwnd, diem, diem)


def keo(hwnd, tu, toi):
    """Kéo từ điểm tu tới điểm toi (toạ độ client của cửa sổ game hwnd)."""
    with KHOA_CHUOT:
        cu_truoc, cu_chuot = win32gui.GetForegroundWindow(), win32api.GetCursorPos()
        try:
            _len_truoc(hwnd)
            a, b = win32gui.ClientToScreen(hwnd, tu), win32gui.ClientToScreen(hwnd, toi)
            if not (_thuoc_game(hwnd, a) and _thuoc_game(hwnd, b)):
                raise LoiKeoTha("cửa sổ game đang bị cửa sổ khác che")
            win32api.SetCursorPos(a)
            time.sleep(0.2)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            try:
                time.sleep(0.15)
                for i in range(1, SO_BUOC_DI + 1):
                    win32api.SetCursorPos((a[0] + (b[0] - a[0]) * i // SO_BUOC_DI,
                                           a[1] + (b[1] - a[1]) * i // SO_BUOC_DI))
                    time.sleep(0.03)
                time.sleep(0.15)
            finally:
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.3)
        finally:
            win32api.SetCursorPos(cu_chuot)
            if cu_truoc and cu_truoc != hwnd and win32gui.IsWindow(cu_truoc):
                try:
                    _len_truoc(cu_truoc)
                except (win32gui.error, LoiKeoTha):
                    pass
