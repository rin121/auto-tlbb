import os
import sys
import time
import traceback
sys.path.insert(0, r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc")
OUT = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\ghi_thao_tac\_live.txt"
HWND = 3934236
O = (4, 5, 6, 7, 8)
try:
    from bang_ma_viscii import giai_ma
    from keo_tha import bam_phai
    from lua_game import TEN_DLL, LuaGame, nap_dll_duong_dan
    dll = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\dong_goi\AutoHoc\dll\autohoc_lua.dll"
    if not os.path.isfile(dll):
        raise SystemExit("khong co dll " + dll)
    import win32process
    _, pid = win32process.GetWindowThreadProcessId(HWND)
    nap_dll_duong_dan(pid, dll, TEN_DLL)
    lua = LuaGame(HWND)
    ten = giai_ma(lua.chay('if not IsWindowShow("PlayerFrame") then return "" end return Player:GetName()'))
    dong = [f"nv={ten}"]
    chay = lambda ma: lua.chay(ma, giay_cho=8).decode("utf-8", "replace")
    mo = chay(
        'local mt = getmetatable(getfenv(0)) local cu = mt.__index '
        'mt.__index = rawget(getfenv(0), "MainMenuBar_Env") '
        'local ok, ket = pcall(function() '
        'if not IsWindowShow("Packet_Temporary") then MainMenuBar_KuaiJieYiZhan() end '
        'return "1" end) '
        'mt.__index = cu if not ok then error(ket) end return ket'
    )
    time.sleep(1.2)
    dong.append("mo=" + mo + " show=" + chay('return tostring(IsWindowShow("Packet_Temporary"))'))
    if "Mặp" not in ten:
        open(OUT, "w", encoding="utf-8").write("khong phai Gao Ca Map: " + ten)
        sys.exit(0)

    def chay(ma):
        return lua.chay(ma, giay_cho=8).decode("utf-8", "replace")

    for i, o in enumerate(O):
        raw = chay(
            'if not IsWindowShow("Packet_Temporary") then return "dong" end '
            'local g = Packet_Temporary_Gold '
            'if g and g.SetProperty then g:SetProperty("Text", "250") end '
            'if g and g.SetText then g:SetText("250") end '
            'local _, sel = debug.getupvalue(Packet_Temporary_Select, 2) '
            'local i = 1 '
            'while i < 15 do '
            'local n = debug.getupvalue(sel, i) '
            'if n == nil then break end '
            'if n == "g_EveryNum" then debug.setupvalue(sel, i, 250) end '
            'i = i + 1 end '
            'local _, upd = debug.getupvalue(Packet_Temporary_Update_II, 2) '
            'local _, grids = debug.getupvalue(upd, 2) '
            f'local nut = grids[{o}] '
            'local l, r, t, b = nut:GetPixelRect() '
            'local gold = "" '
            'if g and g.GetProperty then gold = tostring(g:GetProperty("Text") or "") end '
            'if gold == "" and g and g.GetText then gold = tostring(g:GetText() or "") end '
            'return l .. "," .. r .. "," .. t .. "," .. b .. "|" .. tostring(gold)'
        )
        if raw == "dong":
            dong.append(f"o{o} cua so dong")
            break
        so = [int(float(x)) for x in raw.split("|")[0].split(",")]
        diem = ((so[0] + so[1]) // 2, (so[2] + so[3]) // 2)
        bam_phai(HWND, diem)
        dong.append(f"o{o} gold={raw.split('|')[1]} click={diem}")
        if i != len(O) - 1:
            time.sleep(3)
    open(OUT, "w", encoding="utf-8").write("\n".join(dong))
except SystemExit as loi:
    open(OUT, "w", encoding="utf-8").write(str(loi))
except Exception:
    open(OUT, "w", encoding="utf-8").write(traceback.format_exc())
