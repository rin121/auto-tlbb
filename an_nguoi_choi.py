"""Ẩn người chơi bằng F12 khi nhân vật đứng yên. Dịch chuyển rồi đứng lại thì bấm F12 lần nữa."""
import time

import win32api
import win32con

from lua_game import LoiLua

NGUONG_DUNG = 0.45
GIAY_GIUA_HAI_LAN_DOC = 0.4
VK_F12 = 0x7B
MA_TOA_DO = (
    'if not IsWindowShow("PlayerFrame") then return "" end '
    'local x, y = Player:GetPos() '
    'return x .. "," .. y')


def nen_bam_f12(truoc, x, y, da_bam, bay_gio, luc_dung, nguong=NGUONG_DUNG):
    """True khi đã đứng yên đủ lâu và lần đứng này chưa bấm F12.

    Trả về (bam, toa_do, da_bam, luc_dung).
    """
    if truoc is None:
        return False, (x, y), False, bay_gio
    if abs(x - truoc[0]) + abs(y - truoc[1]) >= 1:
        return False, (x, y), False, bay_gio
    if da_bam:
        return False, truoc, True, luc_dung
    if bay_gio - luc_dung >= nguong:
        return True, truoc, True, luc_dung
    return False, truoc, False, luc_dung


def bam_f12(hwnd):
    scan = win32api.MapVirtualKey(VK_F12, 0)
    xuong = 1 | (scan << 16)
    len = xuong | 0xC0000000
    win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, VK_F12, xuong)
    win32api.PostMessage(hwnd, win32con.WM_KEYUP, VK_F12, len)


def vong_an_nguoi_choi(luong):
    """Luồng phụ của mỗi cửa sổ game. Dừng khi luong.dung được set."""
    truoc = None
    da_bam = False
    luc_dung = 0.0
    while not luong.dung.is_set():
        luong.dung.wait(GIAY_GIUA_HAI_LAN_DOC)
        if luong.dung.is_set():
            break
        game = getattr(luong, "game", None)
        if game is None:
            continue
        try:
            raw = game.lua.chay(MA_TOA_DO)
        except (LoiLua, OSError):
            truoc = None
            da_bam = False
            continue
        if not raw or b"," not in raw:
            truoc = None
            da_bam = False
            continue
        try:
            x_chu, y_chu = raw.split(b",", 1)
            x, y = int(float(x_chu)), int(float(y_chu))
        except ValueError:
            continue
        bam, truoc, da_bam, luc_dung = nen_bam_f12(truoc, x, y, da_bam, time.time(), luc_dung)
        if not bam:
            continue
        try:
            bam_f12(luong.hwnd)
        except OSError:
            da_bam = False
            continue
        ten = getattr(luong, "ten", None) or ""
        if getattr(luong, "in_log", None):
            luong.in_log(f"{ten + ': ' if ten else ''}đứng yên, bấm F12 ẩn người chơi")
