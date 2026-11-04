"""Rút hết ô Thiên Cơ (trừ 3 món blacklist), mỗi lần Select 250, cách 3 giây."""
import os
import sys
import time
import traceback
import win32gui
import win32process

sys.path.insert(0, r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc")
OUT = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\ghi_thao_tac\_live.txt"
DLL = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\dong_goi\AutoHoc\dll\autohoc_lua.dll"

MA_LIET = r'''
if not IsWindowShow("Packet_Temporary") then return "dong" end
local _, upd = debug.getupvalue(Packet_Temporary_Update_II, 2)
local _, ids = debug.getupvalue(upd, 3)
local _, sos = debug.getupvalue(upd, 4)
local s = ""
for i = 1, 60 do
  local id = ids[i] or 0
  if id ~= 0 then
    local ten = tostring(id)
    local ok, a = pcall(function() return GemMelting:UpdateProductAction(id) end)
    if ok and a and a.GetName then
      local ok2, tn = pcall(function() return a:GetName() end)
      if ok2 and tn and tn ~= "" then ten = tn end
    end
    s = s .. i .. "\t" .. ten .. "\t" .. tostring(sos[i] or 0) .. "\n"
  end
end
return s
'''

MA_DAT_250 = r'''
local _, sel = debug.getupvalue(Packet_Temporary_Select, 2)
local i = 1
while i < 15 do
  local n = debug.getupvalue(sel, i)
  if n == nil then break end
  if n == "g_EveryNum" then debug.setupvalue(sel, i, 250) end
  if n == "nIsMbuy" then debug.setupvalue(sel, i, 0) end
  i = i + 1
end
sel(%d)
return "1"
'''


def main():
    from bang_ma_viscii import giai_ma
    from cua_so_game import _la_cua_so_game_hop_le
    from giao_acc_chinh import la_vat_pham_gop
    from lua_game import TEN_DLL, LuaGame, nap_dll_duong_dan

    hwnds = []

    def cb(hwnd, _):
        if _la_cua_so_game_hop_le(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if isinstance(pid, int) and pid > 0:
                hwnds.append((hwnd, pid))
        return True

    win32gui.EnumWindows(cb, None)
    lua = None
    ten_nv = ""
    for hwnd, pid in hwnds:
        try:
            if os.path.isfile(DLL):
                try:
                    nap_dll_duong_dan(pid, DLL, TEN_DLL)
                except Exception:
                    pass
            thu = LuaGame(hwnd)
            ten = giai_ma(thu.chay('if not IsWindowShow("PlayerFrame") then return "" end return Player:GetName()'))
            if "Mặp" in ten:
                lua, ten_nv = thu, ten
                break
        except Exception:
            continue
    if lua is None:
        open(OUT, "w", encoding="utf-8").write("khong thay Gao Ca Map")
        return

    def chay(ma):
        return giai_ma(lua.chay(ma, giay_cho=8))

    chay(
        'local mt = getmetatable(getfenv(0)) local cu = mt.__index '
        'mt.__index = rawget(getfenv(0), "MainMenuBar_Env") '
        'local ok, ket = pcall(function() '
        'if not IsWindowShow("Packet_Temporary") then MainMenuBar_KuaiJieYiZhan() end return "1" end) '
        'mt.__index = cu if not ok then error(ket) end return ket'
    )
    time.sleep(1.0)
    da_rut = []
    bo = []
    lan_truoc = {}
    ket = set()
    for _ in range(40):
        raw = chay(MA_LIET)
        if raw == "dong":
            da_rut.append("cua so dong")
            break
        muc = None
        for dong in raw.splitlines():
            phan = dong.split("\t")
            if len(phan) < 3:
                continue
            try:
                o, ten, so = int(phan[0]), phan[1], int(float(phan[2]))
            except ValueError:
                continue
            if so <= 0 or o in ket:
                continue
            if not la_vat_pham_gop(ten):
                if ten not in bo:
                    bo.append(ten)
                continue
            if lan_truoc.get(o) == so:
                ket.add(o)
                da_rut.append(f"o{o} khong giam, bo qua")
                continue
            muc = (o, ten, so)
            break
        if muc is None:
            break
        o, ten, so = muc
        lan_truoc[o] = so
        chay(MA_DAT_250 % o)
        da_rut.append(f"o{o} {ten} (con {so} truoc lenh)")
        time.sleep(3)
    open(OUT, "w", encoding="utf-8").write(
        ten_nv + "\nDA RUT\n" + "\n".join(da_rut) + "\nBO QUA\n" + "\n".join(bo))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        open(OUT, "w", encoding="utf-8").write(traceback.format_exc())
