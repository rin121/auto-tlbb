"""Liệt kê API Lua mở/rút Thương khố trên client Gao Cá Mặp."""
import os
import sys
import traceback
import win32gui
import win32process

sys.path.insert(0, r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc")
OUT = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\ghi_thao_tac\_live.txt"
DLL = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\dong_goi\AutoHoc\dll\autohoc_lua.dll"

MA = r'''
local s = ""
local function them(x)
  if string.len(s) > 12000 then return end
  s = s .. x .. "\n"
end
local function nguon(fn)
  if type(fn) ~= "function" or not debug or not debug.getinfo then return "" end
  local ok, inf = pcall(debug.getinfo, fn, "S")
  if not ok or not inf then return "" end
  local src = inf.source or ""
  if string.sub(src, 1, 1) == "@" then src = string.sub(src, 2) end
  return (inf.what or "") .. ":" .. tostring(inf.linedefined or 0) .. ":" .. string.sub(src, 1, 80)
end
local function that(fn)
  if type(fn) ~= "function" or not debug or not debug.getupvalue then return fn end
  local i = 1
  while i < 6 do
    local n, v = debug.getupvalue(fn, i)
    if n == nil then break end
    if n == "f" and type(v) == "function" then return v end
    i = i + 1
  end
  return fn
end
local da = {}
local quet = 0
for k, v in pairs(_G) do
  if type(v) == "function" then
    quet = quet + 1
    local ok, inf = pcall(debug.getinfo, that(v), "S")
    local src = ok and inf and inf.source or nil
    if src and not da[src] and string.find(src, "MoveItemToPacket", 1, true) then
      da[src] = 1
      local p = string.find(src, "MoveItemToPacket", 1, true)
      them("HIT " .. tostring(k) .. " @" .. tostring(p))
      them(string.sub(src, math.max(1, p - 300), p + 350))
      them("---")
    end
  end
end
them("quet=" .. quet)
local fn = that(Bank_UpdateFrame)
local ok, inf = pcall(debug.getinfo, fn, "S")
local src = (ok and inf and inf.source) or ""
local i, nfn = 1, 0
while true do
  local a, b, ten = string.find(src, "function%s+([%w_]+)", i)
  if not a then break end
  nfn = nfn + 1
  them("def " .. ten .. " @" .. a)
  i = b + 1
  if nfn > 80 then break end
end
local p3 = string.find(src, "MoveItem", 1, true)
them("---MOVE pos=" .. tostring(p3))
if p3 then them(string.sub(src, math.max(1, p3 - 250), p3 + 500)) end
local p4 = string.find(src, "EnumItem", 1, true)
them("---ENUM pos=" .. tostring(p4))
if p4 then them(string.sub(src, math.max(1, p4 - 200), p4 + 500)) end
them("---ENV---")
local env = rawget(_G, "Bank_Env")
if type(env) == "table" then
  local n = 0
  for k, v in pairs(env) do
    if type(v) == "function" and type(k) == "string" then
      n = n + 1
      if n <= 40 then them("envfn " .. k) end
    end
  end
  them("envfn_n=" .. n)
end
them("win=" .. (IsWindowShow("Bank") and "mo" or "dong"))
local nten = 0
for k, v in pairs(_G) do
  if type(k) == "string" and (string.find(string.lower(k), "bank") or string.find(k, "Depot") or string.find(k, "CangKu")) then
    nten = nten + 1
    if type(v) == "function" then
      them("fn " .. k .. " " .. nguon(that(v)))
    else
      them("obj " .. k .. " " .. type(v))
    end
  end
end
them("so_ten=" .. nten)
if type(Bank) == "table" then
  for k, v in pairs(Bank) do
    them("Bank." .. tostring(k) .. " " .. type(v) .. " " .. (type(v) == "function" and nguon(v) or ""))
  end
end
local mt = getmetatable(Bank)
if mt and type(mt.__index) == "table" then
  for k, v in pairs(mt.__index) do
    them("mt." .. tostring(k) .. " " .. type(v))
  end
end
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
    dong = [f"so_cua_so={len(hwnds)}"]
    lua = None
    for hwnd, pid in hwnds:
        try:
            if os.path.isfile(DLL):
                try:
                    nap_dll_duong_dan(pid, DLL, TEN_DLL)
                except Exception as loi:
                    dong.append(f"nap {hwnd}/{pid}: {loi}")
            thu = LuaGame(hwnd)
            ten = giai_ma(thu.chay('if not IsWindowShow("PlayerFrame") then return "" end return Player:GetName()'))
            dong.append(f"hwnd={hwnd} pid={pid} ten={ten}")
            if "Mặp" in ten:
                lua = thu
                break
        except Exception as loi:
            dong.append(f"loi {hwnd}/{pid}: {loi}")
    if lua is None:
        open(OUT, "w", encoding="utf-8").write("\n".join(dong))
        return
    try:
        raw = lua.chay(MA, giay_cho=40)
        dong.append(giai_ma(raw) if isinstance(raw, (bytes, bytearray)) else str(raw))
    except Exception:
        dong.append(traceback.format_exc())
    open(OUT, "w", encoding="utf-8").write("\n".join(dong))


if __name__ == "__main__":
    main()
