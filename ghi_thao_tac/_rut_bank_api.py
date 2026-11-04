"""Thử Bank:MoveItemToPacket trên Gao Cá Mặp: liệt kê, rút đúng 1 ô, đối túi."""
import os
import sys
import traceback
import win32gui
import win32process

sys.path.insert(0, r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc")
OUT = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\ghi_thao_tac\_live.txt"
DLL = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\dong_goi\AutoHoc\dll\autohoc_lua.dll"

LIET = r'''
local s = "win=" .. tostring(IsWindowShow("Bank")) .. " present=" .. tostring(Bank:IsPresent()) .. "\n"
local tong = 0
for r = 1, (tonumber(Bank:GetRentBoxNum()) or 0) do
  local dau, so = Bank:GetRentBoxInfo(r)
  tong = math.max(tong, (tonumber(dau) or 0) + (tonumber(so) or 0))
  s = s .. "box " .. r .. " dau=" .. tostring(dau) .. " so=" .. tostring(so) .. "\n"
end
s = s .. "tong=" .. tong .. "\n"
local n = 0
for i = 0, math.max(tong, 1) - 1 do
  local a = Bank:EnumItem(i)
  if a and a:GetID() ~= 0 then
    n = n + 1
    if n <= 12 then
      s = s .. i .. "\t" .. (a:GetName() or "?") .. "\t" .. tostring(a:GetNum() or 1) .. "\n"
    end
  end
end
s = s .. "n=" .. n
return s
'''

THU = r'''
local i = %d
local function tui(ten)
  local n = 0
  for o = 0, 99 do
    local b = PlayerPackage:EnumItem("base", o)
    if b and b:GetID() ~= 0 and b:GetName() == ten then n = n + (b:GetNum() or 1) end
  end
  return n
end
local function kho()
  local a = Bank:EnumItem(i)
  if not a or a:GetID() == 0 then return 0, "" end
  return a:GetNum() or 1, a:GetName() or "?"
end
local so, ten = kho()
if so == 0 then return "trong" end
local goc = tui(ten)
local function thu(mo_ta, fn)
  local ok, loi = pcall(fn)
  local so2 = kho()
  local t2 = tui(ten)
  local dong = mo_ta .. " ok=" .. tostring(ok) .. " loi=" .. tostring(loi) .. " kho=" .. tostring(so2) .. " tui=" .. tostring(t2)
  if t2 > goc or so2 < so then return dong .. " DOI", true end
  return dong, false
end
local s = "ten=" .. ten .. " goc_tui=" .. goc .. " goc_kho=" .. so .. "\n"
local trong = -1
for o = 0, 99 do
  local b = PlayerPackage:EnumItem("base", o)
  if not b or b:GetID() == 0 then trong = o break end
end
local ds = {
  {"1arg", function() Bank:MoveItemToPacket(i) end},
  {"1arg+1", function() Bank:MoveItemToPacket(i + 1) end},
  {"2arg trong", function() Bank:MoveItemToPacket(i, trong) end},
  {"rent0", function() Bank:SetCurRentIndex(0) Bank:MoveItemToPacket(i) end},
  {"rent1", function() Bank:SetCurRentIndex(1) Bank:MoveItemToPacket(i) end},
}
for _, cap in ipairs(ds) do
  local dong, doi = thu(cap[1], cap[2])
  s = s .. dong .. "\n"
  if doi then return s end
end
local ok, loi = pcall(function() OpenWindow("Bank") end)
s = s .. "open=" .. tostring(ok) .. " " .. tostring(loi) .. " win=" .. tostring(IsWindowShow("Bank"))
return s
'''


def main():
    from bang_ma_viscii import giai_ma
    from cua_so_game import _la_cua_so_game_hop_le
    from lua_game import TEN_DLL, LuaGame, nap_dll_duong_dan

    hwnds = []

    def cb(hwnd, _):
        if _la_cua_so_game_hop_le(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if isinstance(pid, int) and pid > 0:
                hwnds.append((hwnd, pid))
        return True

    win32gui.EnumWindows(cb, None)
    dong = []
    lua = None
    for hwnd, pid in hwnds:
        try:
            if os.path.isfile(DLL):
                try:
                    nap_dll_duong_dan(pid, DLL, TEN_DLL)
                except Exception:
                    pass
            thu = LuaGame(hwnd)
            ten = giai_ma(thu.chay('return Player:GetName()'))
            if "Mặp" in ten:
                lua = thu
                dong.append(f"{ten} hwnd={hwnd}")
                break
        except Exception as loi:
            dong.append(f"loi {hwnd}: {loi}")
    if lua is None:
        open(OUT, "w", encoding="utf-8").write("khong thay\n" + "\n".join(dong))
        return

    def chay(ma):
        return giai_ma(lua.chay(ma, giay_cho=8))

    try:
        liet = chay(LIET)
        dong.append(liet)
        dong.append(chay(
            'local s = "" for o = 0, 99 do local b = PlayerPackage:EnumItem("base", o) '
            'if b and b:GetID() ~= 0 then local t = b:GetName() or "" '
            'if string.find(t, "KNB") or string.find(t, "Th") then '
            's = s .. o .. "\\t" .. t .. "\\t" .. tostring(b:GetNum() or 1) .. "\\n" end end end return s'
        ))
    except Exception:
        dong.append(traceback.format_exc())
    open(OUT, "w", encoding="utf-8").write("\n".join(dong))


if __name__ == "__main__":
    main()
