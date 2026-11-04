"""Probe cửa sổ đổi phiếu trên GaoDẻLâu — dùng DLL AutoHoc đã nạp (không inject lại)."""
import os
import sys
import traceback
import win32gui
import win32process

sys.path.insert(0, r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc")
OUT = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\ghi_thao_tac\_live.txt"


def main():
    import win32api
    import win32gui as wgui
    from bang_ma_viscii import giai_ma
    from cua_so_game import _la_cua_so_game_hop_le
    from lua_game import LuaGame

    # AutoHoc đã nạp DLL: bỏ qua inject. PostMessage qua win32gui (win32api đôi khi Access denied).
    def nap_noop(pid):
        return True

    import lua_game as lg
    lg.nap_dll = nap_noop
    _post_cu = win32api.PostMessage

    def _post(hwnd, msg, w=0, l=0):
        try:
            return wgui.PostMessage(hwnd, msg, w, l)
        except Exception:
            return _post_cu(hwnd, msg, w, l)

    win32api.PostMessage = _post

    hwnds = []

    def cb(hwnd, _):
        if _la_cua_so_game_hop_le(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if isinstance(pid, int) and pid > 0:
                hwnds.append((hwnd, pid, win32gui.GetWindowText(hwnd)))
        return True

    win32gui.EnumWindows(cb, None)
    dong = [f"so_cua_so={len(hwnds)}"]
    for h, p, t in hwnds:
        dong.append(f"hwnd={h} pid={p} title={t}")

    lua = None
    ten_nv = ""
    for hwnd, pid, _tieu in hwnds:
        try:
            thu = LuaGame(hwnd)
            ten = giai_ma(thu.chay(
                'if not IsWindowShow("PlayerFrame") then return "" end return Player:GetName()',
                giay_cho=8))
            dong.append(f"pid={pid} ten={ten!r}")
            bo = ten.replace(" ", "").lower()
            if "gaod" in bo and ("lau" in bo or "lâu" in ten.lower() or "ẻ" in ten or "de" in bo):
                lua, ten_nv = thu, ten
                if "Dẻ" in ten or "ẻLâu" in ten or "gaodẻ" in bo:
                    break
        except Exception as e:
            dong.append(f"pid={pid} loi={type(e).__name__}: {e}")
            continue

    if lua is None:
        open(OUT, "w", encoding="utf-8").write("\n".join(dong) + "\nKHONG TIM THAY GaoDeLau\n")
        return

    def chay(ma, giay=12):
        return giai_ma(lua.chay(ma, giay_cho=giay))

    dong.append(f"=== NV={ten_nv} ===")
    dong.append("show XX=" + chay('return tostring(IsWindowShow("XiaoXiang_DuiHuanUI2"))'))
    dong.append("show DH=" + chay('return tostring(IsWindowShow("DuiHuanUI"))'))

    # Mở cửa sổ đổi qua NPC Trao Đổi nếu chưa mở
    if chay('return tostring(IsWindowShow("XiaoXiang_DuiHuanUI2"))') != "true":
        dong.append("--- mo NPC Trao Doi ---")
        try:
            from game_api import Game
            from nhan_vat_moi import NhanDoTanThu, NPC_TAN_THU
            from giao_acc_chinh import NPC_TRAO_DOI
            game = Game(lua.hwnd)
            # NhanDoTanThu cần dung callback
            def khong():
                return False
            nd = NhanDoTanThu(game, ten_nv, lambda m: dong.append("npc:" + m), khong, lambda _: None)
            try:
                nd._noi_chuyen(NPC_TRAO_DOI, (("Hợp Thành Vật Phẩm",),))
            except Exception as e:
                dong.append(f"noi_chuyen: {e}")
            import time
            time.sleep(1.5)
        except Exception as e:
            dong.append(f"mo_npc: {e}")

    dong.append("show XX2=" + chay('return tostring(IsWindowShow("XiaoXiang_DuiHuanUI2"))'))
    dong.append("show DH2=" + chay('return tostring(IsWindowShow("DuiHuanUI"))'))

    dong.append("--- _G keys ---")
    keys = chay(r'''
local s, n = "", 0
for k, v in pairs(_G) do
  if type(k) == "string" then
    local kl = string.lower(k)
    if string.find(kl, "duihuan") or string.find(kl, "xiaoxiang") then
      s = s .. k .. "=" .. type(v) .. ","
      n = n + 1
      if n > 100 then break end
    end
  end
end
return s
''')
    dong.append(keys[:3000])

    dong.append("--- icon dump ---")
    dump = chay(r'''
local s = ""
local function them(i, nut, nguon)
  if not nut then return end
  local ten, id = "?", "?"
  if nut.GetActionItem then
    local ok, a = pcall(function() return nut:GetActionItem() end)
    if ok and a then
      if type(a) == "table" then
        local ok2, xid = pcall(function() return a:GetID() end)
        local ok3, xn = pcall(function() return a:GetName() end)
        if ok2 then id = tostring(xid) end
        if ok3 then ten = tostring(xn) end
      else
        id = tostring(a)
      end
    end
  end
  if nut.GetText then
    local ok, t = pcall(function() return nut:GetText() end)
    if ok and t and t ~= "" then ten = tostring(t) end
  end
  if (id ~= "?" and id ~= "0" and id ~= "nil") or (ten ~= "?" and ten ~= "" and ten ~= "nil") then
    s = s .. i .. "|" .. nguon .. "|id=" .. id .. "|ten=" .. ten .. "\n"
  end
end
for i = 1, 50 do
  them(i, _G["DuiHuanUI_Bk_Icon" .. i], "DH")
  them(i, _G["XiaoXiang_DuiHuanUI2_Bk_Icon" .. i], "XX")
end
local t = _G["DuiHuanUI_Bk_Icon"]
if type(t) == "table" then
  s = s .. "DHtab_n=" .. tostring(table.getn(t) or -1) .. "\n"
  for i = 1, (table.getn(t) or 0) do them(i, t[i], "DHtab") end
end
t = _G["XiaoXiang_DuiHuanUI2_Bk_Icon"]
if type(t) == "table" then
  s = s .. "XXtab_n=" .. tostring(table.getn(t) or -1) .. "\n"
  for i = 1, (table.getn(t) or 0) do them(i, t[i], "XXtab") end
end
-- co nut khong
local co = 0
for i = 1, 50 do if _G["DuiHuanUI_Bk_Icon" .. i] then co = co + 1 end end
s = s .. "DHicon_exist=" .. co .. "\n"
co = 0
for i = 1, 50 do if _G["XiaoXiang_DuiHuanUI2_Bk_Icon" .. i] then co = co + 1 end end
s = s .. "XXicon_exist=" .. co .. "\n"
if s == "" then return "EMPTY" end
return s
''', giay=20)
    dong.append(dump[:5000])

    dong.append("--- click + scan text ---")
    for i in range(1, 25):
        try:
            kq = chay(f'''
local i = {i}
if type(XiaoXiang_DuiHuanUI2_Clicked) == "function" then XiaoXiang_DuiHuanUI2_Clicked(i)
elseif type(DuiHuanUI_Clicked) == "function" then DuiHuanUI_Clicked(i) end
local s = "o=" .. i
local nscan = 0
for k, v in pairs(_G) do
  if type(k) == "string" and type(v) == "table" and v.GetText then
    local kl = string.lower(k)
    if string.find(kl, "duihuan") or string.find(kl, "xiaoxiang") or string.find(kl, "tooltip") then
      local ok, t = pcall(function() return v:GetText() end)
      if ok and t and t ~= "" and string.len(t) < 100 then
        s = s .. "|" .. k .. "=" .. t
        nscan = nscan + 1
        if nscan >= 8 then break end
      end
    end
  end
end
return s
''')
            if kq.count("|") >= 1:
                dong.append(kq[:600])
        except Exception as e:
            dong.append(f"click{i}:{e}")

    # Thử đổi thật ô nếu thấy 20k/30k trong dump trước — hoặc brute: click rồi OK nếu túi giảm
    dong.append("--- thu doi: click + OK, do phieu ---")
    truoc = chay(r'''
local function dem(muc)
  local n, tui = 0, {"base","material"}
  for _, ten in ipairs(tui) do
    local i = 0
    while i < 60 do
      local a = PlayerPackage:EnumItem(ten, i)
      if a and a:GetID() ~= 0 then
        local nm = a:GetName() or ""
        if string.find(nm, tostring(muc)) and string.find(string.lower(nm), "phieu") then
          n = n + (a:GetNum() or 1)
        end
      end
      i = i + 1
    end
  end
  return n
end
return "100=" .. dem(100) .. ",300=" .. dem(300)
''')
    dong.append("phieu_truoc=" + truoc)

    open(OUT, "w", encoding="utf-8").write("\n".join(dong) + "\n")
    print("wrote", OUT, "lines", len(dong))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        open(OUT, "w", encoding="utf-8").write(traceback.format_exc())
        raise
