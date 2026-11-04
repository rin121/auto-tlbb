import ctypes, win32gui
TIN = 0x8000 + 0x2B1
out=[]
def cb(hwnd, _):
    t = win32gui.GetWindowText(hwnd)
    if "Thien Long" in t:
        try:
            win32gui.PostMessage(hwnd, TIN, 0, 0)
            out.append(f"pywin ok {hwnd}")
        except Exception as e:
            out.append(f"pywin fail {hwnd} {e}")
        ctypes.windll.kernel32.SetLastError(0)
        r = ctypes.windll.user32.PostMessageW(hwnd, TIN, 0, 0)
        out.append(f"ctypes {hwnd} r={r} err={ctypes.get_last_error()}")
    return True
win32gui.EnumWindows(cb, None)
open(r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\ghi_thao_tac\_post_out.txt","w",encoding="utf-8").write("\n".join(out))
