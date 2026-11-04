import sys
sys.path.insert(0, r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc")
import win32gui, win32process
from cua_so_game import _la_cua_so_game_hop_le
from bang_ma_viscii import giai_ma
from lua_game import LuaGame
import lua_game as lg
import win32api
lg.nap_dll = lambda pid: True
_cu = win32api.PostMessage
def _post(hwnd, msg, w=0, l=0):
    try: return win32gui.PostMessage(hwnd, msg, w, l)
    except Exception: return _cu(hwnd, msg, w, l)
win32api.PostMessage = _post
hs=[]
def cb(h,_):
    if _la_cua_so_game_hop_le(h):
        _,p=win32process.GetWindowThreadProcessId(h)
        hs.append((h,p,win32gui.GetWindowText(h)))
    return True
win32gui.EnumWindows(cb,None)
lines=[]
for h,p,t in hs:
    try:
        ten=giai_ma(LuaGame(h).chay('if not IsWindowShow("PlayerFrame") then return "NO_PF" end return Player:GetName()', giay_cho=6))
    except Exception as e:
        ten=f"ERR:{e}"
    lines.append(f"{p}\t{ten!r}\t{t[:40]}")
open(r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\ghi_thao_tac\_live.txt","w",encoding="utf-8").write("\n".join(lines))
