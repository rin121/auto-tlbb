"""Đóng hộp «客户端过多» (client quá nhiều) trước khi Lua sẵn sàng — dự phòng khi hook DLL chưa kịp."""
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
