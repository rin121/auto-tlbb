"""Chẩn đoán nhẹ trên GaoDẻLâu: túi phiếu + 1 lần chọn ô + dump tên UI (không spam 36 ô)."""
import sys
import time
import traceback

sys.path.insert(0, r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc")
OUT = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\ghi_thao_tac\_live.txt"


def ghi(*a):
    chu = " ".join(str(x) for x in a)
    print(chu)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(chu + "\n")


def main():
    open(OUT, "w", encoding="utf-8").write("")
    import win32api
    import win32gui
    import win32process
    from bang_ma_viscii import giai_ma
    from cua_so_game import _la_cua_so_game_hop_le
    from lua_game import LuaGame
    import lua_game as lg
    from giao_acc_chinh import (
        MA_DOC_TEN_O_DOI, MA_BAM_O_DOI, MA_XAC_NHAN_DOI, MA_DOI_DA_CHON,
        la_cong_thuc_phieu, NPC_TRAO_DOI, MA_CUA_SO_DOI, muc_phieu_knb,
    )
    from game_api import Game
    from nhan_vat_moi import NhanDoTanThu

    lg.nap_dll = lambda pid: True
    _cu = win32api.PostMessage

    def _post(hwnd, msg, w=0, l=0):
        try:
            return win32gui.PostMessage(hwnd, msg, w, l)
        except Exception:
            return _cu(hwnd, msg, w, l)

    win32api.PostMessage = _post

    hwnds = []

    def cb(hwnd, _):
        if _la_cua_so_game_hop_le(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid:
                hwnds.append((hwnd, pid))
        return True

    win32gui.EnumWindows(cb, None)

    lua = None
    ten_nv = ""
    for hwnd, pid in hwnds:
        try:
            thu = LuaGame(hwnd)
            ten = giai_ma(thu.chay(
                'if not IsWindowShow("PlayerFrame") then return "" end return Player:GetName()',
                giay_cho=8))
            ghi("pid", pid, "ten", repr(ten))
            if "Dẻ" in ten or ("Gao" in ten and "Lâu" in ten):
                lua, ten_nv = thu, ten
                break
        except Exception as e:
            ghi("loi", pid, e)

    if lua is None:
        ghi("KHONG TIM THAY")
        return

    def chay(ma, giay=8):
        return giai_ma(lua.chay(ma, giay_cho=giay))

    ghi("===", ten_nv, "===")

    # Liệt kê phiếu trong túi (raw)
    raw_tui = chay(r'''
local s = ""
for _, tui in ipairs({"base","material"}) do
  for i = 0, 59 do
    local a = PlayerPackage:EnumItem(tui, i)
    if a and a:GetID() ~= 0 then
      local nm = a:GetName() or ""
      local k = string.lower(nm)
      if string.find(k, "phieu") or string.find(k, "knb") then
        s = s .. tui .. i .. "\t" .. nm .. "\t" .. tostring(a:GetNum() or 1) .. "\n"
      end
    end
  end
end
if s == "" then return "KHONG_PHIEU" end
return s
''', giay=12)
    ghi("--- tui phieu ---")
    ghi(raw_tui[:2000])

    mo = ""
    if chay('return tostring(IsWindowShow("XiaoXiang_DuiHuanUI2"))') == "true":
        mo = "XiaoXiang_DuiHuanUI2"
    else:
        ghi("mo cua so doi...")
        try:
            game = Game(lua.hwnd)
            nd = NhanDoTanThu(game, ten_nv, lambda m: ghi("npc", m), lambda: False, lambda _: None)
            nd._noi_chuyen(NPC_TRAO_DOI, (("Hợp Thành Vật Phẩm",),))
            time.sleep(1.0)
            try:
                chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
            except Exception:
                pass
            mo = lua.chay(MA_CUA_SO_DOI, giay_cho=8).decode("utf-8", "replace").strip()
        except Exception as e:
            ghi("mo_loi", e)
            return
    ghi("mo=", mo)
    if not mo:
        return

    # Dump control GetText liên quan + thử chọn ô 1..8 (mỗi ô 1 lần, nghỉ 0.5s)
    ghi("--- thu chon o 1..8 + dump text ---")
    tim = {}
    for i in range(1, 9):
        try:
            dump = chay(f'''
local mo, i = "{mo}", {i}
local goi = _G[mo .. "_Clicked"] or _G["DuiHuanUI_Clicked"]
if goi then goi(i) end
local nut = _G["DuiHuanUI_Bk_Icon" .. i]
if nut and nut.DoAction and not goi then nut:DoAction() end
local s = "O=" .. i
local function add(n, w)
  if not w or not w.GetText then return end
  local ok, t = pcall(function() return w:GetText() end)
  if ok and t and t ~= "" and string.len(t) < 120 then
    s = s .. "|" .. n .. "=" .. t
  end
end
local ds = {{"XiaoXiang_DuiHuanUI2_ItemName","XiaoXiang_DuiHuanUI2_Name","XiaoXiang_DuiHuanUI2_Info",
  "XiaoXiang_DuiHuanUI2_Explain","XiaoXiang_DuiHuanUI2_ItemInfo","DuiHuanUI_ItemName","DuiHuanUI_Name",
  "DuiHuanUI_Info","DuiHuanUI_Explain","DuiHuanUI_ItemInfo","DuiHuanUI_Text"}}
for _, n in ipairs(ds) do add(n, _G[n]) end
if SuperTooltips and SuperTooltips.GetTitle then
  local ok, t = pcall(function() return SuperTooltips:GetTitle() end)
  if ok and t and t ~= "" then s = s .. "|ST=" .. t end
end
-- ActionItem tren icon sau click
if nut and nut.GetActionItem then
  local ok, a = pcall(function() return nut:GetActionItem() end)
  if ok and type(a) == "table" and a.GetName then
    local ok2, tn = pcall(function() return a:GetName() end)
    local ok3, id = pcall(function() return a:GetID() end)
    if ok2 and tn then s = s .. "|AI=" .. tn end
    if ok3 and id then s = s .. "|ID=" .. tostring(id) end
  elseif ok and a then s = s .. "|AIraw=" .. tostring(a) end
end
-- quet GetText co chu phieu/20/30
local n = 0
for k, v in pairs(_G) do
  if type(k) == "string" and type(v) == "table" and v.GetText then
    local kl = string.lower(k)
    if string.find(kl, "duihuan") or string.find(kl, "xiaoxiang") then
      local ok, t = pcall(function() return v:GetText() end)
      if ok and t and t ~= "" and string.len(t) < 80 then
        local tl = string.lower(t)
        if string.find(tl, "phieu") or string.find(tl, "20") or string.find(tl, "30")
           or string.find(tl, "knb") or string.find(tl, "kim") then
          s = s .. "|" .. k .. "=" .. t
          n = n + 1
          if n >= 6 then break end
        end
      end
    end
  end
end
return s
''', giay=10)
            ghi(dump[:500])
            # match
            for phan in dump.split("|"):
                if "=" in phan and not phan.startswith("O="):
                    ten = phan.split("=", 1)[1]
                    if la_cong_thuc_phieu(ten, 20000):
                        tim[20000] = i
                        ghi(">> 20K tai o", i)
                    elif la_cong_thuc_phieu(ten, 30000):
                        tim[30000] = i
                        ghi(">> 30K tai o", i)
            if 20000 in tim and 30000 in tim:
                break
        except Exception as e:
            ghi("o", i, "loi", e)
            break
        time.sleep(0.5)

    o_doi = [tim[m] for m in (20000, 30000) if m in tim]
    ghi("o_doi", o_doi)

    if len(o_doi) < 1:
        ghi("chua tim duoc — dung (khong bam OK lung tung)")
        return

    # Thử đổi 1 lần mỗi ô tìm được
    for o in o_doi:
        try:
            ghi("doi o", o)
            lua.chay(MA_BAM_O_DOI.replace("{mo}", mo).replace("{i}", str(o)), giay_cho=8)
            time.sleep(0.4)
            da = lua.chay(MA_DOI_DA_CHON.replace("{mo}", mo), giay_cho=5)
            ghi("da_chon", da)
            if da == b"1":
                kq = lua.chay(MA_XAC_NHAN_DOI.replace("{mo}", mo), giay_cho=8)
                ghi("xac_nhan", kq)
                time.sleep(0.5)
        except Exception as e:
            ghi("doi_loi", e)

    raw_sau = chay(r'''
local s = ""
for _, tui in ipairs({"base","material"}) do
  for i = 0, 59 do
    local a = PlayerPackage:EnumItem(tui, i)
    if a and a:GetID() ~= 0 then
      local nm = a:GetName() or ""
      local k = string.lower(nm)
      if string.find(k, "phieu") or string.find(k, "knb") then
        s = s .. nm .. "\t" .. tostring(a:GetNum() or 1) .. "\n"
      end
    end
  end
end
if s == "" then return "KHONG_PHIEU" end
return s
''', giay=12)
    ghi("--- tui sau ---")
    ghi(raw_sau[:1500])
    ghi("XONG")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise
