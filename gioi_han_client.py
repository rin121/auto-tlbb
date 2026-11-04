"""Đóng hộp «客户端过多» (client quá nhiều) trước khi Lua sẵn sàng — dự phòng khi hook DLL chưa kịp.

Hộp Microsoft Visual C++ Runtime Library («Runtime Error!») là Game.exe abort. Process không chết
cho đến khi bấm OK, nên auto tưởng client còn sống. Bấm OK để process thoát, luồng đăng nhập / xoay vòng mở lại.
"""
import time

import win32con
import win32gui


def thu_dong_hop_client_qua_nhieu():
    """Trả về True nếu vừa bấm OK một hộp giới hạn client."""
    ket = False

    def enum_cb(hwnd, _):
        nonlocal ket
        if not win32gui.IsWindowVisible(hwnd):
            return True
        if win32gui.GetClassName(hwnd) != "#32770":
            return True
        tieu_de = win32gui.GetWindowText(hwnd) or ""
        if "Thien Long" not in tieu_de and "Bat Bo" not in tieu_de:
            return True
        win32gui.PostMessage(hwnd, win32con.WM_COMMAND, 1, 0)
        ket = True
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except win32gui.error:
        pass
    return ket


BM_CLICK = 0x00F5


def la_hop_runtime_error(tieu_de):
    chu = tieu_de or ""
    return "Visual C++" in chu or "Runtime Error" in chu


def _chu_con(hwnd):
    chu = []

    def con(h, _):
        try:
            t = win32gui.GetWindowText(h) or ""
        except win32gui.error:
            t = ""
        if t:
            chu.append(t)
        return True

    try:
        win32gui.EnumChildWindows(hwnd, con, None)
    except win32gui.error:
        pass
    return chu


def _bam_ok(hwnd):
    """MessageBox chỉ đóng khi BM_CLICK đúng nút OK, không chỉ WM_COMMAND lên khung."""
    nut = 0
    try:
        nut = win32gui.GetDlgItem(hwnd, win32con.IDOK) or 0
    except (win32gui.error, AttributeError):
        nut = 0
    if not nut:
        def tim(h, _):
            nonlocal nut
            try:
                if win32gui.GetClassName(h) == "Button" and (win32gui.GetWindowText(h) or "").strip().lower() == "ok":
                    nut = h
            except win32gui.error:
                pass
            return True
        try:
            win32gui.EnumChildWindows(hwnd, tim, None)
        except win32gui.error:
            pass
    if nut:
        win32gui.PostMessage(nut, BM_CLICK, 0, 0)
        win32gui.PostMessage(hwnd, win32con.WM_COMMAND, win32con.IDOK, nut)
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, win32con.VK_RETURN, 0)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, win32con.VK_RETURN, 0)


def dong_hop_runtime_error():
    """Bấm OK mọi hộp Runtime Error của Game.exe. Trả về tiêu đề các hộp vừa đóng."""
    dong = []

    def enum_cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        try:
            if win32gui.GetClassName(hwnd) != "#32770":
                return True
            tieu_de = win32gui.GetWindowText(hwnd) or ""
        except win32gui.error:
            return True
        if not la_hop_runtime_error(tieu_de) and not any(la_hop_runtime_error(c) for c in _chu_con(hwnd)):
            return True
        try:
            _bam_ok(hwnd)
        except win32gui.error:
            return True
        dong.append(tieu_de or "Runtime Error")
        return True

    try:
        win32gui.EnumWindows(enum_cb, None)
    except win32gui.error:
        pass
    return dong


def vong_dong_hop_runtime(in_log, nen_dung=None):
    """Luồng nền: thấy hộp Runtime Error thì bấm OK. nen_dung không được đụng Tk."""
    while True:
        if nen_dung is not None:
            try:
                if nen_dung():
                    return
            except Exception:
                nen_dung = None
        try:
            ds = dong_hop_runtime_error()
        except OSError:
            ds = []
        if ds and in_log:
            try:
                in_log("Game.exe crash (Runtime Error) — đã bấm OK để client tắt, auto sẽ đăng nhập lại")
            except Exception:
                pass
        time.sleep(0.4)
