"""
GIAO DỊCH CHO ACC CHÍNH: lần lượt đăng nhập acc phó bản (mặc định: trưởng nhóm; tùy chọn: mọi acc trong nhóm xoay vòng,
từng nhân vật round 1..3), kiểm tra túi Đạo cụ + Nguyên liệu; có đồ thì giao cho acc chính (trừ loại trừ, đồ khóa),
chế độ «tất cả acc» thì không có đồ sẽ thoát game và sang acc tiếp. Acc chính đứng ở NPC Tân Thủ (Đại Lý).
Cả hai chế độ đều xem sổ túi đồ (so_tui_do.py, xoay vòng ghi cuối mỗi round): sổ ghi 0 ô thì bỏ qua, sổ ghi còn đồ /
chưa rõ thì đăng nhập giao dù không phải trưởng nhóm; giao xong đánh dấu đã giao cho acc chính trong sổ.
Bấm Bắt đầu: mọi client đang trong game (trừ acc chính đã đúng nhân vật) về chọn máy chủ, giữ client; acc chính rồi
lần lượt các acc giao dịch đăng nhập trên chính các client đó, không mở game mới (trừ khi không còn client nào).

Túi acc chính còn dưới SO_O_TOI_THIEU ô trống thì cất đồ đã nhận:
    Thiên Cơ Cẩm Nang (cửa sổ Packet_Temporary, mở bằng MainMenuBar_KuaiJieYiZhan()):
        Packet_Temporary_PutInItem(ô túi Đạo cụ); Phiếu KNB 2000 cũng cất TCCN; phiếu 100/300 giữ túi để hợp thành.
        Nếu Thương khố đầy mà túi vẫn chật: cất tạm mọi món Đạo cụ vào TCCN.
    Thương khố (NPC Tân Thủ, dòng (111111, 9993)): chuột phải ô túi khi cửa sổ Bank đang mở là cất vào kho.
        Số ô kho = Bank:GetRentBoxInfo(r) (ô đầu, số ô) của các ngăn r = 1..Bank:GetRentBoxNum().
Cả hai đều đầy thì dừng, giữ tiến trình. Tiến trình (trưởng nhóm đã giao xong trong ngày, mã đồ đã nhận) lưu ở
cau_hinh chung "giao_acc_chinh", bấm Bắt đầu lại thì đi tiếp từ trưởng nhóm chưa xong.
"""
import copy
import math
import os
import re
import threading
import time
import traceback
from datetime import date

import cau_hinh
from auto_chuyen_sinh import chuan_hoa
from bang_ma_viscii import giai_ma, ma_hoa
from chien_dau import KY_NANG_VE_THANH, ma_dung_ky_nang_theo_dinh_nghia
from cua_so_game import tim_cua_so_game
from dang_nhap import (LoiDangNhap, bo_dau, cho_cua_so, man_hinh_hien_tai, mo_game, tai_khoan_cua_pid,
                       thoat_ve_chon_may_chu, trong_cua_so, ve_chon_may_chu)
from game_api import Game
from giao_dich import GiaoDich, LoiGiaoDich, doc_tui
from keo_tha import LoiKeoTha, bam_phai
from lua_game import LoiLua
from nhan_vat_moi import NPC_TAN_THU, NhanDoTanThu, da_xong
from pho_ban_pmp import LoiPhoBan, _Dung as DungPhoBan, cai_dat_pmp, chuan_bi_ve_thanh, hom_nay, la_dai_ly
import so_tui_do
from so_tui_do import LOAI_TRU_MAC_DINH, bi_loai_tru, cac_tu_loai_tru
from xoay_vong import (SO_ROUND_TOI_DA, LuongVaoNhanVat, cac_tai_khoan_dang_tich, chia_nhom, khoa_sap_xep_tai_khoan,
                       ten_round, ten_trong_tieu_de, tim_game_cua_tai_khoan, tim_hwnd_cua_tai_khoan)

KHOA_CAI_DAT = "giao_acc_chinh"
MAC_DINH = {"tai_khoan": "", "mat_khau": "", "nhan_vat": "", "loai_tru": LOAI_TRU_MAC_DINH, "chi_hom_nay": True,
            "tat_ca_pho_ban": False, "tien_trinh": {}}
DONG_THUONG_KHO = (111111, 9993)
NPC_TRAO_DOI = ("Trao Đổi", (155, 173))
# XiaoXiang_DuiHuanUI2 — ghi tay 2026-11-04 (GaoDẻLâu):
# Clicked(6) → OK = Phiếu KNB 20K (mã 30004614); Clicked(7) → OK = Phiếu KNB 30K (mã 30004615).
O_PHIEU_KNB_20K = 6
O_PHIEU_KNB_30K = 7
MA_PHIEU_KNB_20K = 30004614
MA_PHIEU_KNB_30K = 30004615
O_DOI_PHIEU = (O_PHIEU_KNB_20K, O_PHIEU_KNB_30K)
# Game Lua cũ (không có string.match): dùng string.find lấy capture.
_MA_TIM_TEN_CUA = (
    'local function tim(chu, mau) local _, _, a = string.find(chu, mau) return a end '
    'local function ten_tu(k) return tim(k, "^([%w_]+)_[%w_]*Clicked$") '
    'or tim(k, "^([%w_]+)_OnEvent$") or tim(k, "^([%w_]+)_On_") or tim(k, "^([%w_]+)_SetCtl$") end ')
MA_CUA_SO_DOI = (
    _MA_TIM_TEN_CUA +
    'local bo = {Packet=1, Quest=1, Bank=1, Packet_Temporary=1, MainMenuBar=1, ChatFrame=1, '
    'MessageBox_Self=1, MessageBox_Other=1, ActionSkill=1, Target=1, Minimap=1, Exp=1, '
    'Friend=1, Team=1, Relive_Frame=1} '
    'local uu = {"Exchange","ExchangeShop","ExchangeFrame","ExchangeItem","Shop","Shop_Frame",'
    '"City_Shop","Compose","HeCheng","ItemCompose","ComposeItem","DuiHuan","ChangeItem",'
    '"Booth","IBShop","YuanbaoShop","PsShop","PlayerShop","SelfShop","ShopExchange","NPCShop",'
    '"DoiVatPham","HopThanhVatPham","HopThanh","DoiKNB","HeChengWuPin","ShopFitting"} '
    'for _, n in ipairs(uu) do if IsWindowShow(n) then return n end end '
    'local uu2, all, seen = "", "", {} '
    'for k, v in pairs(_G) do '
    'if type(k) == "string" then '
    'local ten = ten_tu(k) '
    'if ten and not seen[ten] and not bo[ten] then '
    'seen[ten] = 1 '
    'if IsWindowShow(ten) then '
    'all = all .. ten .. "," '
    'if _G[ten .. "_Item_Clicked"] or _G[ten .. "_OK_Clicked"] or _G[ten .. "_Accept_Clicked"] '
    'or _G[ten .. "_Queding_Clicked"] or _G[string.format("%s_Item01", ten)] '
    'or _G[string.format("%s_Item1", ten)] then uu2 = uu2 .. ten .. "," end '
    'end end end end '
    'if uu2 ~= "" then return tim(uu2, "^([^,]+)") end '
    'if all ~= "" then return tim(all, "^([^,]+)") end '
    'return ""')
MA_LIET_KE_CUA_SO_DOI = (
    _MA_TIM_TEN_CUA +
    'local bo = {Packet=1, Quest=1, Bank=1, Packet_Temporary=1, MainMenuBar=1, ChatFrame=1, '
    'MessageBox_Self=1, MessageBox_Other=1, ActionSkill=1, Target=1, Minimap=1, Exp=1} '
    'local s, seen = "", {} '
    'for k, v in pairs(_G) do '
    'if type(k) == "string" then '
    'local ten = ten_tu(k) '
    'if ten and not seen[ten] and not bo[ten] and IsWindowShow(ten) then '
    'seen[ten] = 1 s = s .. ten .. "," end end end return s')
# Cửa sổ IsWindowShow = XiaoXiang_DuiHuanUI2; ô công thức ActionButton thật = DuiHuanUI_Bk_Icon1..50.
MA_BAM_O_DOI = (
    'local mo = "{mo}" if mo == "" then return "dong" end '
    'if not IsWindowShow(mo) and not IsWindowShow("DuiHuanUI") then return "dong" end '
    'local i = {i} '
    'local goi = _G[mo .. "_Clicked"] '
    'if goi then goi(i) return "1" end '
    'goi = _G["DuiHuanUI_Clicked"] '
    'if goi then goi(i) return "1" end '
    'goi = _G[mo .. "_Item_Clicked"] or _G[mo .. "_Select"] or _G[mo .. "_Goods_Clicked"] '
    'if goi then goi(i) return "1" end '
    'goi = _G[string.format("%s_Item%02d_Clicked", mo, i)] or _G[string.format("%s_Item%d_Clicked", mo, i)] '
    'if goi then goi() return "1" end '
    'local nut = _G[string.format("DuiHuanUI_Bk_Icon%d", i)] '
    'or _G[string.format("%s_Bk_Icon%d", mo, i)] '
    'or _G[string.format("%s_Item%02d", mo, i)] or _G[string.format("%s_Item%d", mo, i)] '
    'or _G[string.format("%s_Goods%02d", mo, i)] or _G[string.format("%s_Goods%d", mo, i)] '
    'if nut and nut.DoAction then nut:DoAction() return "1" end '
    'if nut and nut.Click then nut:Click() return "1" end return "khong"')
MA_XAC_NHAN_DOI = (
    'local mo = "{mo}" if mo == "" then return "dong" end '
    'if not IsWindowShow(mo) and not IsWindowShow("DuiHuanUI") then return "dong" end '
    'local hs = {mo .. "_OK_Clicked", "DuiHuanUI_OK_Clicked", mo .. "_Accept_Clicked", '
    'mo .. "_Queding_Clicked", mo .. "_XN_Clicked", mo .. "_Confirm_Clicked", mo .. "_Yes_Clicked", '
    '"DuiHuanUI_Accept_Clicked", "DuiHuanUI_Queding_Clicked"} '
    'for _, ten in ipairs(hs) do local f = _G[ten] if f then f() return "1" end end '
    'local nut = _G[mo .. "_OK"] or _G["DuiHuanUI_OK"] or _G[mo .. "_Accept"] or _G[mo .. "_Queding"] '
    'if nut and nut.Click then nut:Click() return "1" end '
    'if nut and nut.DoAction then nut:DoAction() return "1" end return "khong"')
MA_CAC_O_DOI_CO_DO = (
    'local mo = "{mo}" '
    'if (mo == "" or not IsWindowShow(mo)) and not IsWindowShow("DuiHuanUI") then return "" end '
    'local s = "" '
    'for i = 1, 50 do '
    'local nut = _G[string.format("DuiHuanUI_Bk_Icon%d", i)] '
    'if nut and nut.GetActionItem then local ok, a = pcall(function() return nut:GetActionItem() end) '
    'if ok and a and a ~= 0 then '
    'if type(a) ~= "table" or (a.GetID and a:GetID() ~= 0) then s = s .. i .. "," end end end end '
    'if s == "" and mo ~= "" then '
    'local icons = _G[mo .. "_Bk_Icon"] '
    'if type(icons) == "table" then '
    'for i = 1, (table.getn(icons) or 0) do '
    'local nut = icons[i] '
    'if nut and nut.GetActionItem then local a = nut:GetActionItem() '
    'if a and a ~= 0 then s = s .. i .. "," end end end end '
    'for i = 1, 50 do '
    'local nut = _G[string.format("%s_Bk_Icon%d", mo, i)] '
    'if nut and nut.GetActionItem then local a = nut:GetActionItem() '
    'if a and a ~= 0 then s = s .. i .. "," end end end end '
    'return s')
MA_TEN_O_DOI = (
    'local mo = "{mo}" '
    'if mo ~= "" and not IsWindowShow(mo) and not IsWindowShow("DuiHuanUI") then return "" end '
    'local s, seen = "", {} '
    'local function ten_nut(nut) '
    'if not nut then return "" end '
    'if nut.GetText then local ok, t = pcall(function() return nut:GetText() end) '
    'if ok and t and t ~= "" then return t end end '
    'if nut.GetToolTip then local ok, t = pcall(function() return nut:GetToolTip() end) '
    'if ok and t and t ~= "" then return t end end '
    'if nut.GetActionItem then local ok, a = pcall(function() return nut:GetActionItem() end) '
    'if ok and type(a) == "table" and a.GetName then '
    'local ok2, id = pcall(function() return a:GetID() end) '
    'if ok2 and id and id ~= 0 then '
    'local ok3, ten = pcall(function() return a:GetName() end) '
    'if ok3 and ten and ten ~= "" then return ten end end end end '
    'return "" end '
    'local function them(i, ten) '
    'if ten ~= "" and not seen[i] then seen[i] = 1 s = s .. i .. "\\t" .. ten .. "\\n" end end '
    'for i = 1, 50 do them(i, ten_nut(_G[string.format("DuiHuanUI_Bk_Icon%d", i)])) end '
    'if s == "" and mo ~= "" then '
    'local icons = _G[mo .. "_Bk_Icon"] '
    'if type(icons) == "table" then '
    'for i = 1, (table.getn(icons) or 0) do them(i, ten_nut(icons[i])) end end '
    'for i = 1, 50 do '
    'them(i, ten_nut(_G[string.format("%s_Bk_Icon%d", mo, i)])) '
    'them(i, ten_nut(_G[string.format("%s_Item%d", mo, i)])) '
    'them(i, ten_nut(_G[string.format("%s_Item%02d", mo, i)])) '
    'end end '
    'return s')
MA_DOI_DA_CHON = (
    'local mo = "{mo}" '
    'if (mo == "" or not IsWindowShow(mo)) and not IsWindowShow("DuiHuanUI") then return "0" end '
    'local ok = _G[mo .. "_OK"] or _G["DuiHuanUI_OK"] '
    'if ok then '
    'if ok.IsEnable and ok:IsEnable() then return "1" end '
    'if ok.IsEnabled and ok:IsEnabled() then return "1" end '
    'end '
    'for i = 1, 50 do '
    'local nut = _G[string.format("DuiHuanUI_Bk_Icon%d", i)] '
    'if nut and nut.GetPushed and tonumber(nut:GetPushed()) == 1 then return "1" end '
    'end '
    'local icons = mo ~= "" and _G[mo .. "_Bk_Icon"] or nil '
    'if type(icons) == "table" then '
    'for i = 1, (table.getn(icons) or 0) do '
    'local nut = icons[i] '
    'if nut and nut.GetPushed and tonumber(nut:GetPushed()) == 1 then return "1" end '
    'end end return "0"')
# Chọn 1 ô (không Xác nhận) rồi đọc tên công thức từ nhãn / tooltip / ActionItem sau khi chọn.
MA_DOC_TEN_O_DOI = (
    'local mo, i = "{mo}", {i} '
    'if mo == "" then return "" end '
    'if not IsWindowShow(mo) and not IsWindowShow("DuiHuanUI") then return "dong" end '
    'local goi = _G[mo .. "_Clicked"] or _G["DuiHuanUI_Clicked"] '
    'if goi then goi(i) end '
    'local nut = _G[string.format("DuiHuanUI_Bk_Icon%d", i)] '
    'or _G[string.format("%s_Bk_Icon%d", mo, i)] '
    'if nut and nut.DoAction and not goi then nut:DoAction() end '
    'local function lay(w) '
    'if not w then return "" end '
    'if w.GetText then local ok, t = pcall(function() return w:GetText() end) '
    'if ok and t and t ~= "" then return t end end '
    'if w.GetActionItem then local ok, a = pcall(function() return w:GetActionItem() end) '
    'if ok and type(a) == "table" and a.GetName then '
    'local ok2, id = pcall(function() return a:GetID() end) '
    'if ok2 and id and id ~= 0 then '
    'local ok3, ten = pcall(function() return a:GetName() end) '
    'if ok3 and ten and ten ~= "" then return ten end end end end '
    'return "" end '
    'local ds = {"XiaoXiang_DuiHuanUI2_ItemName", "XiaoXiang_DuiHuanUI2_Name", '
    '"XiaoXiang_DuiHuanUI2_Info", "XiaoXiang_DuiHuanUI2_Explain", "XiaoXiang_DuiHuanUI2_ItemInfo", '
    '"DuiHuanUI_ItemName", "DuiHuanUI_Name", "DuiHuanUI_Info", "DuiHuanUI_Explain", '
    '"DuiHuanUI_ItemInfo", "DuiHuanUI_Text", "SuperTooltips_ItemName"} '
    'for _, n in ipairs(ds) do local t = lay(_G[n]) if t ~= "" then return t end end '
    'if SuperTooltips then '
    'if SuperTooltips.GetTitle then local ok, t = pcall(function() return SuperTooltips:GetTitle() end) '
    'if ok and t and t ~= "" then return t end end '
    'if SuperTooltips.GetOwner then local ok, o = pcall(function() return SuperTooltips:GetOwner() end) '
    'if ok then local t = lay(o) if t ~= "" then return t end end end end '
    'local t = lay(nut) if t ~= "" then return t end '
    'return ""')
SO_O_TOI_THIEU = 5
SO_O_MOT_LAN = 5
SO_LAN_THU_GIAO_DICH = 3
KHOANG_CACH_DUNG_CHO = 3
GIAY_CHAY_TOI = 90
GIAY_GUI_LAI_CHAY = 5
GIAY_CHO_VE_DAI_LY = 90
GIAY_GIUA_HAI_LAN_VE_THANH = 15
GIAY_CHO_CUA_SO = 6
GIAY_CHO_CAT = 2.5
# Nghỉ giữa hai lần cất túi→rương / túi→TCCN (đổi phiếu + dọn túi).
GIAY_GIUA_HAI_LAN_CAT = 0.5
# Rút Thương khố (MoveItemToPacket) giữa hai lần — đổi phiếu rút 100/300. Thiên Cơ vẫn 3 giây.
GIAY_GIUA_RUT_KHO = 0.5
SO_LAN_THU_CAT = 2
SO_LAN_HOP_THANH_TOI_DA = 40
GIAY_XAC_NHAN_PHIEU = 0.5
# Giữ hằng cũ cho test / tool — auto không còn quét từng ô để tìm tên.
SO_O_DOI_TIM_TOI_DA = 36
GIAY_GIUA_HAI_LAN_TIM_O_DOI = 0.35
GIAY_SAU_CHON_O_DOI = 0.25

MA_KICH_THUOC_TUI = 'return DataPool:GetBaseBag_Num() .. "\\t" .. DataPool:GetMatBag_Num()'
MA_MO_TCCN = trong_cua_so("MainMenuBar", "MainMenuBar_KuaiJieYiZhan()")
MA_TCCN_DANG_MO = 'return tostring(IsWindowShow("Packet_Temporary"))'
MA_CAT_TCCN = trong_cua_so("Packet_Temporary", 'if not IsWindowShow("Packet_Temporary") then return "dong" end '
                                               'Packet_Temporary_PutInItem({o}) return "1"')
MA_KHO_DANG_MO = 'return tostring(IsWindowShow("Bank"))'
MA_O_TRONG_KHO = ('if not IsWindowShow("Bank") then return "-1" end local tong, n = 0, 0 '
                  'for r = 1, (tonumber(Bank:GetRentBoxNum()) or 0) do local dau, so = Bank:GetRentBoxInfo(r) '
                  'tong = math.max(tong, (tonumber(dau) or 0) + (tonumber(so) or 0)) end '
                  'for i = 0, tong - 1 do local a = Bank:EnumItem(i) if a and a:GetID() ~= 0 then n = n + 1 end end '
                  'return tostring(tong - n)')
# Chuột phải ô túi lúc cửa sổ kho đóng là DÙNG món đó (Phiếu KNB thành KNB): kiểm tra kho đang mở ngay trong lệnh.
MA_CAT_KHO = trong_cua_so("Packet", 'if not IsWindowShow("Bank") then return "dong" end '
                                    'local a = PlayerPackage:EnumItem("{tui}", {o}) '
                                    'if not a or a:GetID() == 0 then return "0" end '
                                    'Packet_Space_Line1_Row1_button:SetActionItem(a:GetID()) '
                                    'Packet_Space_Line1_Row1_button:DoAction() return "1"')
MA_DONG_CUA_SO = ('for _, w in ipairs({"Packet_Temporary", "Bank", "Quest"}) do '
                  'if IsWindowShow(w) then CloseWindow(w, true) end end')
# Thiên Cơ: bảng Packet_Temporary_ItemID (upvalue Update_II). Rút = g_EveryNum 250 + Packet_Temporary_Select(ô).
_LUA_TCCN_THAT = (
    'local function that(fn) '
    'if type(fn) ~= "function" or not debug or not debug.getupvalue then return fn end '
    'local i = 1 '
    'while i < 8 do '
    'local n, v = debug.getupvalue(fn, i) '
    'if n == nil then break end '
    'if n == "f" and type(v) == "function" then return v end '
    'if n == "g_EveryNum" or n == "Packet_Temporary_ItemID" then return fn end '
    'i = i + 1 end '
    'return fn end ')
MA_LIET_KE_TCCN_THAT = (
    _LUA_TCCN_THAT +
    'if not IsWindowShow("Packet_Temporary") then return "dong" end '
    'if type(Packet_Temporary_Update_II) ~= "function" then return "khong" end '
    'local fn = that(Packet_Temporary_Update_II) '
    'local ids, sos, i = nil, nil, 1 '
    'while i < 15 do '
    'local n, v = debug.getupvalue(fn, i) '
    'if n == nil then break end '
    'if n == "Packet_Temporary_ItemID" then ids = v end '
    'if n == "Packet_Temporary_ItemNum_Data" then sos = v end '
    'i = i + 1 end '
    'if type(ids) ~= "table" then return "khong" end '
    'local s = "" '
    'for o = 1, 60 do '
    'local id = ids[o] '
    'if id and id ~= 0 then '
    'local ten = tostring(id) '
    'if GemMelting and GemMelting.UpdateProductAction then '
    'local ok, a = pcall(function() return GemMelting:UpdateProductAction(id) end) '
    'if ok and a and a.GetName and a:GetID() ~= 0 then ten = a:GetName() end end '
    'local so = (type(sos) == "table" and sos[o]) or 1 '
    's = s .. o .. "\\t" .. ten .. "\\t" .. tostring(so) .. "\\n" '
    'end end return s')
MA_LIET_KE_TCCN = trong_cua_so("Packet_Temporary", MA_LIET_KE_TCCN_THAT)
MA_RUT_TCCN_THAT = (
    _LUA_TCCN_THAT +
    'if not IsWindowShow("Packet_Temporary") then return "dong" end '
    'if type(Packet_Temporary_Select) ~= "function" then return "khong" end '
    'local sel = that(Packet_Temporary_Select) '
    'local i, dat = 1, 0 '
    'while i < 15 do '
    'local n = debug.getupvalue(sel, i) '
    'if n == nil then break end '
    'if n == "g_EveryNum" then debug.setupvalue(sel, i, 250) dat = 1 end '
    'if n == "nIsMbuy" then debug.setupvalue(sel, i, 0) end '
    'i = i + 1 end '
    'if dat == 0 then return "khong" end '
    'sel({i}) return "1|250"')
MA_RUT_TCCN = trong_cua_so("Packet_Temporary", MA_RUT_TCCN_THAT)
MA_LIET_KE_KHO = (
    'if not IsWindowShow("Bank") then return "dong" end local s = "" '
    'local tong = 0 for r = 1, (tonumber(Bank:GetRentBoxNum()) or 0) do '
    'local dau, so = Bank:GetRentBoxInfo(r) '
    'tong = math.max(tong, (tonumber(dau) or 0) + (tonumber(so) or 0)) end '
    'for i = 0, tong - 1 do local a = Bank:EnumItem(i) '
    'if a and a:GetID() ~= 0 then s = s .. i .. "\\t" .. a:GetName() .. "\\t" .. a:GetNum() .. "\\n" end end return s')
# Rút rương = Bank:MoveItemToPacket(ô). Cả chồng ra túi. Ô tính từ 0.
MA_RUT_KHO = (
    'if not Bank:IsPresent() and not IsWindowShow("Bank") then return "dong" end '
    'local i = {i} '
    'local a = Bank:EnumItem(i) if not a or a:GetID() == 0 then return "0" end '
    'Bank:MoveItemToPacket(i) return "1"')
# Toạ độ ô (GetPixelRect) giữ để đối chiếu; luồng rút không dùng chuột.
MA_TOA_DO_O_KHO_THAT = (
    'if not IsWindowShow("Bank") then return "dong" end '
    'local i = {i} '
    'local a = Bank:EnumItem(i) if not a or a:GetID() == 0 then return "0" end '
    'local id = a:GetID() '
    'local function rect(nut) '
    'if not nut or not nut.GetPixelRect then return nil end '
    'local l, r, t, b = nut:GetPixelRect() '
    'if l == nil then return nil end '
    'return string.format("%s,%s,%s,%s", tostring(l), tostring(r), tostring(t), tostring(b)) end '
    'local function cung_mon(nut) '
    'if not nut or not nut.GetActionItem then return false end '
    'local ai = nut:GetActionItem() '
    'local aid = ai and ai.GetID and ai:GetID() or 0 '
    'return aid == id end '
    'local function thu_ten(ten) '
    'local f = loadstring("return " .. ten) '
    'if not f then return nil end '
    'local nut = f() '
    'if not cung_mon(nut) then return nil end '
    'return rect(nut) end '
    'local env = rawget(getfenv(0), "Bank_Env") '
    'if env then for k, v in pairs(env) do '
    'if type(k) == "string" and cung_mon(v) then '
    'local s = rect(v) '
    'if s then return "1|" .. s .. "|" .. k end end end end '
    'local vi_tri = i '
    'for r = 1, (tonumber(Bank:GetRentBoxNum()) or 0) do '
    'local dau, so = Bank:GetRentBoxInfo(r) '
    'dau, so = tonumber(dau) or 0, tonumber(so) or 0 '
    'if i >= dau and i < dau + so then vi_tri = i - dau break end end '
    'local ds_ten = { '
    '"Bank_Item" .. (i + 1), "Bank_SelfItem" .. (i + 1), '
    '"Bank_Item" .. i, "Bank_SelfItem" .. i } '
    'for _, cot in ipairs({10, 8}) do '
    'local line = math.floor(vi_tri / cot) + 1 '
    'local row = math.mod(vi_tri, cot) + 1 '
    'table.insert(ds_ten, string.format("Bank_Space_Line%d_Row%d_button", line, row)) '
    'table.insert(ds_ten, string.format("Bank_Space_Line%d_Row%d", line, row)) end '
    'for _, ten in ipairs(ds_ten) do '
    'local s = thu_ten(ten) '
    'if s then return "1|" .. s .. "|" .. ten end end '
    'local ten_fb = "Bank_Item" .. (i + 1) '
    'local f = loadstring("return " .. ten_fb) '
    'local s = f and rect(f()) or nil '
    'if s then return "1|" .. s .. "|" .. ten_fb end '
    'local ds = "" '
    'if env then for k, v in pairs(env) do '
    'if type(k) == "string" and v and v.GetPixelRect and v.GetActionItem then '
    'local ai = v:GetActionItem() '
    'local aid = ai and ai.GetID and ai:GetID() or 0 '
    'if aid ~= 0 then ds = ds .. k .. "=" .. tostring(aid) .. ";" end '
    'if string.len(ds) > 220 then break end end end end '
    'return "0|" .. ds')
MA_TOA_DO_O_KHO = trong_cua_so("Bank", MA_TOA_DO_O_KHO_THAT)
MA_TEN_NUT_KHO = MA_TOA_DO_O_KHO


class _Dung(Exception):
    pass


class LoiGiaoAccChinh(Exception):
    pass


def cai_dat():
    gia_tri = dict(MAC_DINH)
    gia_tri.update(cau_hinh.chung().get(KHOA_CAI_DAT) or {})
    return gia_tri


def luu_cai_dat(**thay_doi):
    cau_hinh.dat_chung({KHOA_CAI_DAT: dict(cai_dat(), **thay_doi)})


def la_phieu_knb(ten):
    khoa = bo_dau(ten)
    return "phieu knb" in khoa or "phieu kim nguyen bao" in khoa


def muc_phieu_knb(ten):
    """100, 300, 2000, 3000 nếu là Phiếu KNB các mệnh giá đó (kể cả 2K / 3K)."""
    if not la_phieu_knb(ten):
        return None
    k = bo_dau(re.sub(r"#[-0-9a-fA-F]*", "", ten or ""))
    if re.search(r"(?<![a-z0-9])2k(?![a-z0-9])", k):
        return 2000
    if re.search(r"(?<![a-z0-9])3k(?![a-z0-9])", k):
        return 3000
    so = re.findall(r"\d+", k)
    if so and so[-1] in {"100", "300", "2000", "3000"}:
        return int(so[-1])
    return None


def la_phieu_nho(ten):
    """Phiếu KNB 100 và 300: giữ trong túi để hợp thành, không cất rương."""
    return muc_phieu_knb(ten) in (100, 300)


def la_phieu_cat_tccn(ten):
    """Phiếu KNB 2000 (kể cả «2K»): acc chính cất vào Thiên Cơ Cẩm Nang."""
    return muc_phieu_knb(ten) == 2000


def la_cong_thuc_phieu(ten, muc):
    """Tên ô công thức «Phiếu KNB 20K» / «Phiếu KNB 30K» (kể cả 20000 / 30000)."""
    k = bo_dau(re.sub(r"#[-0-9a-fA-F]*", "", ten or ""))
    if "phieu knb" not in k and "phieu kim nguyen bao" not in k:
        return False
    if muc == 20000:
        return bool(re.search(r"(?<![a-z0-9])20k(?![a-z0-9])", k) or re.search(r"(?<!\d)20000(?!\d)", k))
    if muc == 30000:
        return bool(re.search(r"(?<![a-z0-9])30k(?![a-z0-9])", k) or re.search(r"(?<!\d)30000(?!\d)", k))
    return False


# Gộp đồ: giao mọi món, trừ ba loại mảnh vỡ bên dưới.
SO_RUT_TCCN = 250
GIAY_GIUA_RUT_TCCN = 3


def la_vat_pham_gop(ten):
    """Mọi vật phẩm, trừ Mảnh vỡ Thời trang, Thú cưỡi và Trang bị (không gồm bản VIP)."""
    k = bo_dau(re.sub(r"#[-0-9a-fA-F]*", "", ten or "")).strip()
    if not k:
        return False
    if "thoi trang" in k or "thu cuoi" in k:
        return False
    if "trang bi" in k and "vip" not in k:
        return False
    return True


def ten_nhan_vat_acc_chinh_online():
    """Tên nhân vật acc chính nếu đang trong game, None nếu không."""
    cd = cai_dat()
    tk = (cd.get("tai_khoan") or "").strip()
    ten = (cd.get("nhan_vat") or "").strip()
    if not tk or not ten:
        return None
    import win32gui
    hwnd = tim_game_cua_tai_khoan(tk)
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None
    try:
        tt = Game(hwnd).thong_tin()
    except (LoiLua, OSError):
        return None
    except Exception:
        return None
    if tt and chuan_hoa(tt["ten"]) == chuan_hoa(ten):
        return ten
    return None


def hwnd_acc_chinh_train():
    """Cửa sổ game acc chính đang train (tab Giao dịch cho acc chính), None nếu chưa online đúng nhân vật."""
    if not ten_nhan_vat_acc_chinh_online():
        return None
    tk = (cai_dat().get("tai_khoan") or "").strip()
    return tim_game_cua_tai_khoan(tk) if tk else None


def tk_acc_chinh_bo_pho_ban():
    """Tài khoản acc chính đang online (để train), không đưa vào nhóm phó bản xoay vòng."""
    if not ten_nhan_vat_acc_chinh_online():
        return None
    return (cai_dat().get("tai_khoan") or "").strip().lower() or None


def _ma_thu_muc(ten):
    """Tên thư mục / file game ghi cho tài khoản, nhân vật: "#" + hex bytes VISCII (caychay72 -> #636179636861793732)."""
    try:
        du_lieu = ma_hoa(ten)
    except KeyError:
        du_lieu = ten.encode("utf-8")
    return "#" + du_lieu.hex()


def thu_muc_accounts():
    return os.path.join(cau_hinh.doc_tai_khoan().get("thu_muc_game") or "", "Accounts")


def cac_nhan_vat_dang_online():
    ten = set()
    for cua_so in tim_cua_so_game():
        khop = ten_trong_tieu_de(cua_so["hwnd"])
        if khop:
            ten.add(chuan_hoa(khop))
    return ten


def ly_do_khong_co_nhan_vat(tk, ten, thu_muc, da_tao=(), online=()):
    """
    Game ghi Accounts\\#<hex tài khoản>\\#<hex nhân vật>.pfc cho tài khoản đã từng đăng nhập / nhân vật đã từng vào game
    (file nhân vật ghi lúc thoát). Lý do bỏ qua (chưa từng đăng nhập / chưa có nhân vật), None nếu có nhân vật hoặc
    không xác định được (không thấy thư mục Accounts). Nhân vật auto đã tạo (da_tao) hoặc đang online thì luôn có.
    """
    if not thu_muc or not os.path.isdir(thu_muc):
        return None
    khoa = chuan_hoa(ten)
    if khoa in online or khoa in da_tao:
        return None
    thu_muc_tk = os.path.join(thu_muc, _ma_thu_muc(tk))
    if not os.path.isdir(thu_muc_tk):
        return "tài khoản chưa từng đăng nhập"
    if not os.path.isfile(os.path.join(thu_muc_tk, _ma_thu_muc(ten) + ".pfc")):
        return "chưa có nhân vật"
    return None


class _KiemTraNhanVat:
    """Gom lý do bỏ qua nhân vật không có thật, đọc thư mục Accounts / client online một lần cho cả danh sách."""

    def __init__(self, bo_qua):
        self.bo_qua = bo_qua
        self.thu_muc = thu_muc_accounts()
        self.online = cac_nhan_vat_dang_online()

    def co(self, tk, ten):
        da_tao = {chuan_hoa(t) for t in da_xong(tk["ten_dang_nhap"])}
        ly_do = ly_do_khong_co_nhan_vat(tk["ten_dang_nhap"], ten, self.thu_muc, da_tao, self.online)
        if ly_do and self.bo_qua is not None:
            self.bo_qua.append((tk["ten_dang_nhap"], ten, ly_do))
        return ly_do is None


def _loc_nhan_vat_pho_ban(tk, ten, chi_hom_nay):
    if chi_hom_nay:
        dem = hom_nay(cai_dat_pmp(cau_hinh.cua_nhan_vat(ten)))
        if not (dem["so_vong"] or dem["st_vong"] or dem["st_het"]):
            return False
    elif chuan_hoa(ten) not in {chuan_hoa(t) for t in da_xong(tk["ten_dang_nhap"])}:
        return False
    return True


def _ung_vien_truong_nhom(tk_chinh):
    """[(tài khoản, tên nhân vật)] có thể là trưởng nhóm (nhận đồ của cả round), chưa lọc."""
    ds = [tk for tk in cac_tai_khoan_dang_tich() if tk["ten_dang_nhap"].lower() != tk_chinh.lower()]
    theo_tk = {tk["ten_dang_nhap"].lower(): tk for tk in ds}
    ung_vien = [(nhom[0], ten_round(nhom[0]["ten_dang_nhap"], r))
                for nhom in chia_nhom(ds) for r in range(SO_ROUND_TOI_DA)]
    # Nhóm có người bù vào thì trưởng nhóm thay đổi; xoay vòng ghi lại các trưởng nhóm thật.
    ung_vien += [(theo_tk[tk.lower()], ten) for tk, ten in cau_hinh.chung()["xv_truong_nhom"]
                 if tk.lower() in theo_tk]
    return ung_vien


def ten_cac_truong_nhom(tk_chinh):
    return {chuan_hoa(ten) for _, ten in _ung_vien_truong_nhom(tk_chinh)}


def bo_qua_cung_tai_khoan(tk, ten, tk_khong_co_do, ten_truong):
    """
    Chế độ «tất cả acc»: một nhân vật của tài khoản không có đồ thì các nhân vật khác của tài khoản đó cũng đã giao
    hết cho trưởng nhóm, bỏ qua — trừ nhân vật là trưởng nhóm (nhận đồ cả round, có thể đang giữ đồ).
    """
    return tk["ten_dang_nhap"].lower() in tk_khong_co_do and chuan_hoa(ten) not in ten_truong


def cac_truong_nhom(tk_chinh, chi_hom_nay, bo_qua=None):
    """
    [(tài khoản, tên nhân vật)] các trưởng nhóm theo thứ tự xoay vòng; chi_hom_nay: chỉ nhân vật đã đi hôm nay.
    Bỏ nhân vật không có thật (tài khoản chưa từng đăng nhập / chưa tạo nhân vật), ghi (tk, tên, lý do) vào bo_qua.
    """
    kiem_tra = _KiemTraNhanVat(bo_qua)
    kq, da_co = [], set()
    for tk, ten in _ung_vien_truong_nhom(tk_chinh):
        if chuan_hoa(ten) in da_co:
            continue
        da_co.add(chuan_hoa(ten))
        if not kiem_tra.co(tk, ten) or not _loc_nhan_vat_pho_ban(tk, ten, chi_hom_nay):
            continue
        kq.append((tk, ten))
    return kq


def cac_nhan_vat_pho_ban(tk_chinh, chi_hom_nay, bo_qua=None):
    """[(tài khoản, tên nhân vật)] mọi tài khoản XV theo thứ tự bảng; một NV/acc (cột Nhân vật hoặc round 1)."""
    kiem_tra = _KiemTraNhanVat(bo_qua)
    tk_chinh_l = (tk_chinh or "").lower()
    thu_muc = kiem_tra.thu_muc
    online = kiem_tra.online
    kq = []
    for tk in cac_tai_khoan_dang_tich():
        if (tk.get("ten_dang_nhap") or "").lower() == tk_chinh_l:
            continue
        ten_nv = (tk.get("nhan_vat") or "").strip()
        ten = ten_nv if ten_nv else ten_round(tk["ten_dang_nhap"], 0)
        if not ten_nv:
            ly_do = ly_do_khong_co_nhan_vat(
                tk["ten_dang_nhap"], ten, thu_muc,
                {chuan_hoa(t) for t in da_xong(tk["ten_dang_nhap"])}, online)
            if ly_do:
                if bo_qua is not None:
                    bo_qua.append((tk["ten_dang_nhap"], ten, ly_do))
                continue
        if not kiem_tra.co(tk, ten) or not _loc_nhan_vat_pho_ban(tk, ten, chi_hom_nay):
            continue
        kq.append((tk, ten))
    return kq


def ap_dung_so_tui(ds, tk_chinh, so):
    """
    Lọc danh sách [(tài khoản, tên)] theo sổ túi đồ: bỏ nhân vật sổ ghi chắc 0 ô; thêm nhân vật sổ ghi còn đồ / chưa rõ
    mà chưa có trong danh sách (đội viên giao lỗi, nhân vật không đi hôm nay...). Chỉ thêm acc đang tick (bat);
    acc bỏ tích không bị kéo vào dù sổ còn chua_ro / còn đồ. Trả về (danh sách, tên bỏ, thêm).
    """
    kq, bo = [], []
    for tk, ten in ds:
        if so_tui_do.chac_khong_co_do(so_tui_do.muc_cua(so, ten)):
            bo.append(ten)
        else:
            kq.append((tk, ten))
    co = {chuan_hoa(ten) for _, ten in ds}
    # Chỉ acc đã tick — tránh sổ túi (vd. chua_ro của cosato3333) kéo lại acc đã bỏ tích.
    theo_tk = {tk["ten_dang_nhap"].lower(): tk for tk in cac_tai_khoan_dang_tich()}
    them = []
    for khoa, muc in so.items():
        tk = theo_tk.get((muc.get("tk") or "").lower())
        if khoa in co or tk is None or tk["ten_dang_nhap"].lower() == tk_chinh.lower() or not so_tui_do.can_giao(muc):
            continue
        them.append((tk, muc.get("ten") or khoa))
    kq = sorted(kq + them, key=lambda x: khoa_sap_xep_tai_khoan(x[0]["ten_dang_nhap"]))
    return kq, bo, them


class GiaoAccChinhEngine:
    """Đăng nhập, di chuyển, giao dịch, cất túi acc nhận — dùng chung «Giao acc chính» và «Gộp acc chính»."""

    ghi_so_tui = True
    thoat_sau_giao = False

    def _kiem_tra_dung(self):
        if self.dung.is_set():
            raise _Dung()

    def _cho(self, dieu_kien, giay, buoc=0.5):
        het_han = time.time() + giay
        while True:
            self._kiem_tra_dung()
            ket_qua = dieu_kien()
            if ket_qua or time.time() > het_han:
                return ket_qua
            self.dung.wait(buoc)

    def _luu_tien_trinh(self):
        luu_cai_dat(tien_trinh=self.tien_trinh)

    @staticmethod
    def _doc(game):
        try:
            return game.thong_tin()
        except (LoiLua, OSError):
            return None

    def _ve_chon_may_chu(self, game, ten):
        try:
            game.lua.chay(MA_DONG_CUA_SO)
        except LoiLua:
            pass
        try:
            ve_chon_may_chu(game, self.dung.is_set, lambda chu: self.in_log(f"{ten}: {chu}"))
        except LoiDangNhap as loi:
            raise LoiGiaoAccChinh(f"{ten}: {loi}") from loi

    def _dang_nhap(self, tai_khoan, hwnd):
        acc_chinh = tai_khoan["ten_dang_nhap"].lower() == self.tk_chinh["ten_dang_nhap"].lower()
        # Xoay vòng mới bắt tên caychay10 / 100 / 1000. Gộp đồ nhập tên tự do (GaoCáMặp...),
        # acc đó còn nhân vật khác (titi22) thì vẫn đăng nhập đúng tên đã nhập.
        bat_rule = getattr(self, "kiem_tra_rule_ten", True) and not acc_chinh
        luong = LuongVaoNhanVat(tai_khoan, cau_hinh.doc_tai_khoan(), self.hang_doi, hwnd,
                                kiem_tra_rule_ten=bat_rule)
        self.cac_luong_con.append(luong)
        luong.start()
        while luong.is_alive():
            if self.dung.is_set():
                luong.dung.set()
            time.sleep(1)
        self.cac_luong_con.remove(luong)
        self._kiem_tra_dung()
        if not (luong.thanh_cong and luong.game):
            return None
        self.pid_dieu_khien.add(luong.game.lua.pid)
        return luong.game

    def _hwnd_giu_xoay_vong(self):
        """Khi gộp đồ song song XV: giữ mọi client thuộc nhóm xoay vòng."""
        if not getattr(self, "chi_giao_gop", False):
            return set()
        try:
            from xoay_vong import hwnd_cua_nhom_xoay_vong
            return hwnd_cua_nhom_xoay_vong()
        except Exception:
            return set()

    def _cac_hwnd_giu(self, *them):
        """hwnd cần giữ: tham số + mọi client đang online thuộc ten_giu_online / tk_giu_online (+ nhóm XV nếu gộp)."""
        giu = {h for h in them if h} | self._hwnd_giu_xoay_vong()
        giu_ten = getattr(self, "ten_giu_online", set())
        giu_tk = getattr(self, "tk_giu_online", set())
        for cua_so in tim_cua_so_game():
            if cua_so["hwnd"] in giu:
                continue
            try:
                game = Game(cua_so["hwnd"])
                tt = game.thong_tin()
            except (LoiLua, OSError):
                continue
            ten_nv = (tt or {}).get("ten") or ""
            if ten_nv and chuan_hoa(ten_nv) in giu_ten:
                giu.add(cua_so["hwnd"])
                continue
            tk = ((tt or {}).get("tai_khoan") or tai_khoan_cua_pid(cua_so["pid"]) or "").strip().lower()
            if tk and tk in giu_tk:
                giu.add(cua_so["hwnd"])
        return giu

    def _thoat_cac_client(self, giu=()):
        """Client đang trong game (trừ hwnd trong giu) về chọn máy chủ cùng lúc; giữ client để đăng nhập acc khác."""
        can_thoat = []
        giu = set(giu) | self._cac_hwnd_giu()
        giu_ten = getattr(self, "ten_giu_online", set())
        giu_tk = getattr(self, "tk_giu_online", set())
        for cua_so in tim_cua_so_game():
            if cua_so["hwnd"] in giu:
                continue
            try:
                game = Game(cua_so["hwnd"])
                tt = game.thong_tin()
                if not tt and man_hinh_hien_tai(game.lua) != "vao_game":
                    continue
            except (LoiLua, OSError):
                continue
            ten_nv = (tt or {}).get("ten") or ""
            if ten_nv and chuan_hoa(ten_nv) in giu_ten:
                self.in_log(f"{ten_nv} đang trong game, không đăng xuất")
                continue
            tk = ((tt or {}).get("tai_khoan") or tai_khoan_cua_pid(cua_so["pid"]) or "").strip().lower()
            if tk and tk in giu_tk:
                self.in_log(f"{ten_nv or tk} (acc nguồn/chính) đang trong game, không đăng xuất")
                continue
            if tk:
                self.tk_da_thoat.add(tk)
            can_thoat.append((cua_so["pid"], (tt or {}).get("ten") or cua_so["tieu_de"].split(" - ")[0]))
        if not can_thoat:
            return
        self.in_log(f"Đăng xuất {len(can_thoat)} client về chọn máy chủ: {', '.join(ten for _, ten in can_thoat)}")
        self.pid_dieu_khien |= {pid for pid, _ in can_thoat}
        cac_luong = [threading.Thread(target=thoat_ve_chon_may_chu, daemon=True,
                                      args=(pid, lambda chu, t=ten: self.in_log(f"{t}: {chu}"), self.dung.is_set))
                     for pid, ten in can_thoat]
        for luong in cac_luong:
            luong.start()
        for luong in cac_luong:
            luong.join()
        self._kiem_tra_dung()

    def _hwnd_acc_chinh_dung_nhan_vat(self):
        hwnd = tim_game_cua_tai_khoan(self.tk_chinh["ten_dang_nhap"])
        if not hwnd:
            return None
        try:
            tt = Game(hwnd).thong_tin()
        except (LoiLua, OSError):
            return None
        return hwnd if tt and chuan_hoa(tt["ten"]) == chuan_hoa(self.tk_chinh["nhan_vat"]) else None

    def _mo_du_hai_client(self):
        """Gộp đồ: mở đủ 2 Game.exe rảnh (không thuộc nhóm XV) trước khi đăng nhập."""
        if not getattr(self, "chi_giao_gop", False):
            return
        giu_xv = self._hwnd_giu_xoay_vong()
        ranh = [c for c in tim_cua_so_game() if c["hwnd"] not in giu_xv]
        thieu = 2 - len(ranh)
        if thieu <= 0:
            return
        cd = cau_hinh.doc_tai_khoan()
        self.in_log(f"Mở {thieu} client gộp (đang có {len(ranh)} rảnh, {len(giu_xv)} thuộc XV)")
        try:
            pids = [mo_game(cd["thu_muc_game"]) for _ in range(thieu)]
        except LoiDangNhap as loi:
            raise LoiGiaoAccChinh(str(loi)) from loi
        giay = cd["giay_cho_truoc_khi_nap_dll"]
        loi_mo = []

        def cho_mot(pid):
            try:
                cho_cua_so(pid, giay, self.dung.is_set)
            except LoiDangNhap as loi:
                loi_mo.append(str(loi))

        cac = [threading.Thread(target=cho_mot, args=(pid,), daemon=True) for pid in pids]
        for luong in cac:
            luong.start()
        for luong in cac:
            luong.join()
        self._kiem_tra_dung()
        if loi_mo:
            raise LoiGiaoAccChinh(loi_mo[0])
        ranh_sau = sum(1 for c in tim_cua_so_game() if c["hwnd"] not in self._hwnd_giu_xoay_vong())
        self.in_log(f"Đã có {ranh_sau} client rảnh cho gộp, bắt đầu đăng nhập acc chính")

    def _vao_acc_chinh(self):
        self._mo_du_hai_client()
        ten = self.tk_chinh["nhan_vat"]
        self.bao_trang_thai(f"Vào acc chính {ten}")
        hwnd = self._hwnd_acc_chinh_dung_nhan_vat()
        self._thoat_cac_client(giu=self._cac_hwnd_giu(hwnd))
        if hwnd:
            self.in_log(f"Acc chính {ten} đang trong game, giữ nguyên")
        else:
            giu_xv = self._hwnd_giu_xoay_vong()
            hwnd = tim_hwnd_cua_tai_khoan(self.tk_chinh["ten_dang_nhap"]) \
                or next((c["hwnd"] for c in tim_cua_so_game() if c["hwnd"] not in giu_xv), None)
            if hwnd:
                self.in_log(f"Đăng nhập acc chính {ten} trên client đang mở (không mở game mới)")
        game = self._dang_nhap(self.tk_chinh, hwnd)
        if game is None:
            raise LoiGiaoAccChinh(f"không đăng nhập được acc chính {ten} (xem log Đăng nhập)")
        self.chinh = game
        self._cho(lambda: self._doc(game), 60)
        game.lua.chay(MA_DONG_CUA_SO)
        self._ve_dai_ly(game, ten)
        self._chay_toi(game, ten, NPC_TAN_THU[1])

    def _hwnd_dll_san(self, hwnd):
        if not hwnd:
            return None
        try:
            Game(hwnd).lua.ket_noi()
            return hwnd
        except (LoiLua, OSError):
            return None

    def _chon_game_truong(self, tk):
        hwnd_chinh = self.chinh.lua.hwnd
        giu_xv = self._hwnd_giu_xoay_vong()
        hwnd = self._hwnd_dll_san(tim_game_cua_tai_khoan(tk["ten_dang_nhap"]))
        if hwnd in giu_xv:
            hwnd = None
        cac_cua_so = [c["hwnd"] for c in tim_cua_so_game()
                      if c["hwnd"] != hwnd_chinh and c["hwnd"] not in giu_xv]
        if hwnd is None:
            ung = self.hwnd_truong if self.hwnd_truong in cac_cua_so else None
            if ung is None:
                for h in cac_cua_so:
                    if self._hwnd_dll_san(h):
                        ung = h
                        break
            hwnd = ung
        self._thoat_cac_client(giu=self._cac_hwnd_giu(hwnd_chinh, hwnd))
        return hwnd

    def _ve_dai_ly(self, game, ten):
        luc_ve = 0.0
        het_han = time.time() + GIAY_CHO_VE_DAI_LY
        while time.time() < het_han:
            self._kiem_tra_dung()
            tt = self._doc(game)
            if tt and la_dai_ly(tt["map"]):
                return
            if tt and time.time() - luc_ve >= GIAY_GIUA_HAI_LAN_VE_THANH:
                luc_ve = time.time()
                try:
                    chuan_bi_ve_thanh(game)
                    game.lua.chay(ma_dung_ky_nang_theo_dinh_nghia(KY_NANG_VE_THANH))
                except LoiLua:
                    pass
            self.dung.wait(1)
        raise LoiGiaoAccChinh(f"{ten} chưa về được Đại Lý")

    def _chay_toi(self, game, ten, xy):
        lan_gui = [0.0]

        def toi():
            tt = self._doc(game)
            if tt and math.hypot(tt["x"] - xy[0], tt["y"] - xy[1]) <= KHOANG_CACH_DUNG_CHO:
                return True
            if tt and time.time() - lan_gui[0] >= GIAY_GUI_LAI_CHAY:
                if not la_dai_ly(tt["map"]):
                    self._ve_dai_ly(game, ten)
                lan_gui[0] = time.time()
                game.lua.chay(f"AutoRunToTarget({int(xy[0])}, {int(xy[1]) + 2})")
            return False
        if not self._cho(toi, GIAY_CHAY_TOI):
            raise LoiGiaoAccChinh(f"{ten} chạy {GIAY_CHAY_TOI} giây chưa tới ({xy[0]}, {xy[1]})")

    def _thoat_game_pho_ban(self, game, ten):
        if not game:
            return
        hwnd = game.lua.hwnd
        pid = game.lua.pid
        self.pid_dieu_khien.discard(pid)
        try:
            self._ve_chon_may_chu(game, ten)
        except (LoiGiaoAccChinh, LoiDangNhap, LoiLua, OSError) as loi:
            self.in_log(f"{ten}: không về chọn máy chủ ({loi}), thử tắt game")
            thoat_ve_chon_may_chu(pid, self.in_log, self.dung.is_set)
            if self.hwnd_truong == hwnd:
                self.hwnd_truong = None
            return
        self.in_log(f"{ten}: đã về chọn máy chủ, sang nhân vật tiếp theo")
        self.hwnd_truong = hwnd

    def _do_can_giao(self, game, bo_qua):
        cac_o = []
        for (ten_tui, o), (ma, _, ten) in sorted(doc_tui(game.lua).items()):
            if (ten_tui, o, ma) in bo_qua:
                continue
            if getattr(self, "chi_giao_gop", False):
                if not la_vat_pham_gop(ten):
                    continue
            elif bi_loai_tru(ten, self.loai_tru):
                continue
            cac_o.append((ten_tui, o))
        return cac_o

    def _mot_truong_nhom(self, tk, ten):
        ten_chinh = self.tk_chinh["nhan_vat"]
        self.in_log(f"{ten}: đăng nhập")
        game = self._dang_nhap(dict(tk, nhan_vat=ten), self._chon_game_truong(tk))
        if game is None:
            self.in_log(f"{ten}: đăng nhập thất bại nhiều lần, bỏ qua (lần sau bấm Bắt đầu sẽ thử lại)")
            return False
        self.hwnd_truong = game.lua.hwnd
        self._cho(lambda: self._doc(game), 60)
        bo_qua = set()
        if getattr(self, "rut_truoc_giao", False):
            self._ve_dai_ly(game, ten)
            try:
                self._chay_toi(game, ten, NPC_TAN_THU[1])
            except LoiGiaoAccChinh as loi:
                self.in_log(f"{loi} — vẫn thử rút rương / Thiên Cơ Cẩm Nang")
        # Gộp: túi → rương (rút+giao đến trống) → Thiên Cơ (250, 3 giây/lần).
        if getattr(self, "rut_truoc_giao", False):
            cac_pha = (
                ("tui", "túi"),
                ("kho", "Thương khố"),
                ("tccn", "Thiên Cơ Cẩm Nang"),
            )
        else:
            cac_pha = (("tui", "túi"),)
        for pha, mo_ta_pha in cac_pha:
            self._nguon_rut = pha
            if pha != "tui":
                ghi_chu = " (sau khi rương trống)" if pha == "tccn" else ""
                self.in_log(f"{ten}: rút {mo_ta_pha}{ghi_chu}")
                kq_rut = self._rut_do_gop(game, ten)
                if kq_rut is None:
                    # Túi có thể đã nhận đồ (Lua báo fail vì client chậm) — vẫn giao phần trong túi.
                    cac_o_tam = self._do_can_giao(game, bo_qua)
                    if not cac_o_tam:
                        self.in_log(f"{ten}: chưa kiểm tra/rút được {mo_ta_pha}, chưa đánh dấu xong")
                        return False
                    self.in_log(f"{ten}: rút {mo_ta_pha} chưa chắc xong, vẫn giao {len(cac_o_tam)} ô trong túi")
            cac_o = self._do_can_giao(game, bo_qua)
            if not cac_o:
                if pha == "kho":
                    self.in_log(f"{ten}: Thương khố trống (không còn món gộp), sang Thiên Cơ Cẩm Nang")
                if pha != "tccn":
                    continue
                break
            self.in_log(f"{ten}: có {len(cac_o)} ô đồ ({mo_ta_pha}), giao dịch cho {ten_chinh}")
            if not getattr(self, "rut_truoc_giao", False):
                self._ve_dai_ly(game, ten)
                try:
                    self._chay_toi(game, ten, NPC_TAN_THU[1])
                except LoiGiaoAccChinh as loi:
                    self.in_log(f"{loi} — vẫn giao dịch (tự chạy lại gần {ten_chinh})")
            lan_loi = 0
            while cac_o:
                self._kiem_tra_dung()
                self._don_tui_chinh()
                lan_nay = cac_o[:SO_O_MOT_LAN]
                tui = doc_tui(game.lua)
                ma_moi = {tui[o][0] for o in lan_nay} - set(self.tien_trinh["ma_da_nhan"])
                if ma_moi:
                    self.tien_trinh["ma_da_nhan"] += sorted(ma_moi)
                    self._luu_tien_trinh()
                try:
                    GiaoDich(game, self.chinh, ten, ten_chinh, self.in_log, self.dung.is_set).chuyen(lan_nay)
                    lan_loi = 0
                    self._xep_tui_chinh()
                except LoiGiaoDich as loi:
                    self._kiem_tra_dung()
                    lan_loi += 1
                    self.in_log(f"{ten}: giao dịch lỗi ({loi}), thử lại {lan_loi}/{SO_LAN_THU_GIAO_DICH}")
                    if lan_loi >= SO_LAN_THU_GIAO_DICH:
                        self.in_log(f"{ten}: giao dịch lỗi nhiều lần, bỏ qua (lần sau bấm Bắt đầu sẽ thử lại)")
                        if self.ghi_so_tui:
                            try:
                                so_tui_do.ghi_so_o(tk["ten_dang_nhap"], ten, doc_tui(game.lua), self.loai_tru)
                            except (LoiLua, OSError):
                                pass
                        return False
                    self.dung.wait(3)
                    continue
                sau = doc_tui(game.lua)
                for o in lan_nay:
                    if o in sau and sau[o] == tui[o]:
                        bo_qua.add((o[0], o[1], tui[o][0]))
                cac_o = self._do_can_giao(game, bo_qua)
                # Rương/TCCN: túi trống sau giao → kiểm còn món trong kho đó, còn thì rút tiếp.
                if not cac_o and getattr(self, "rut_truoc_giao", False) and pha in ("kho", "tccn"):
                    kq_rut = self._rut_do_gop(game, ten)
                    if kq_rut is True:
                        cac_o = self._do_can_giao(game, bo_qua)
                        if cac_o:
                            self.in_log(f"{ten}: {mo_ta_pha} còn đồ, rút thêm {len(cac_o)} ô rồi giao tiếp")
                    elif kq_rut is False:
                        if pha == "kho":
                            self.in_log(f"{ten}: Thương khố đã trống sau giao, lần sau mở Thiên Cơ Cẩm Nang")
                    elif kq_rut is None:
                        self._don_tui_chinh()
                        self.in_log(f"{ten}: chưa rút tiếp được {mo_ta_pha}, chưa đánh dấu xong")
                        return False
        if getattr(self, "rut_truoc_giao", False) and not self._het_do_gop_nguon(game, ten):
            self.in_log(f"{ten}: túi đã giao hết nhưng Thiên Cơ/rương còn đồ gộp (hoặc chưa đọc được), "
                        "chưa đánh dấu xong")
            return False
        self.in_log(f"{ten}: đã giao xong (túi + Thiên Cơ + rương hết món gộp)"
                    + (f", còn {len(bo_qua)} ô không giao được (đồ khóa?)" if bo_qua else ""))
        if self.ghi_so_tui:
            so_tui_do.ghi_da_giao(tk["ten_dang_nhap"], ten, {ma for _, _, ma in bo_qua})
        if self.thoat_sau_giao:
            self.in_log(f"{ten}: đăng xuất sau khi giao xong, sang nhân vật tiếp theo")
            self._thoat_game_pho_ban(game, ten)
        return True

    def _o_trong_dao_cu(self, game):
        so_o = [int(float(x)) for x in game.lua.chay(MA_KICH_THUOC_TUI).decode().split("\t")]
        dung = sum(1 for ten_tui, _ in doc_tui(game.lua) if ten_tui == "base")
        return so_o[0] - dung

    @staticmethod
    def _doc_bang_vat(raw):
        if raw in (b"dong", b"khong"):
            return raw.decode()
        hang = []
        for dong in giai_ma(raw).splitlines():
            phan = dong.split("\t")
            if len(phan) >= 3 and phan[0] != "debug":
                try:
                    hang.append((int(float(phan[0])), phan[1], int(float(phan[2]))))
                except ValueError:
                    pass
        return hang

    def _tong_trong_tui(self, game, ten_vat):
        khoa = bo_dau(ten_vat)
        return sum(so for (_, _), (_, so, ten) in doc_tui(game.lua).items() if bo_dau(ten) == khoa)

    def _rut_do_gop(self, game, ten):
        """Rút một nguồn theo `_nguon_rut`: 'kho' (Thương khố) hoặc 'tccn'.

        True = đã rút được ít nhất 1 món; False = đã liệt kê, không còn món gộp;
        None = không mở / không liệt kê được (chưa được coi là hết đồ).
        """
        try:
            return self._rut_do_gop_that(game, ten)
        except (LoiLua, OSError) as loi:
            self.in_log(f"{ten}: lỗi khi rút rương / Thiên Cơ ({loi})")
            try:
                game.lua.chay(MA_DONG_CUA_SO)
            except (LoiLua, OSError):
                pass
            return None

    def _rut_do_gop_that(self, game, ten):
        if self._o_trong_dao_cu(game) < 2:
            self.in_log(f"{ten}: túi gần đầy, giao bớt rồi rút tiếp")
            return False
        if getattr(self, "_nguon_rut", "kho") == "tccn":
            return self._rut_mot_kho(game, ten, "Thiên Cơ Cẩm Nang", self._mo_tccn, MA_LIET_KE_TCCN,
                                     MA_RUT_TCCN, GIAY_GIUA_RUT_TCCN)
        return self._rut_mot_kho(game, ten, "Thương khố", lambda g: self._mo_kho_game(g, ten),
                                 MA_LIET_KE_KHO, MA_RUT_KHO, GIAY_GIUA_RUT_KHO)

    def _het_do_gop_nguon(self, game, ten):
        """True chỉ khi túi + Thương khố + Thiên Cơ không còn món gộp (rương kiểm trước)."""
        if self._do_can_giao(game, set()):
            return False
        for ten_kho, mo, ma_liet_ke in (
            ("Thương khố", lambda g: self._mo_kho_game(g, ten), MA_LIET_KE_KHO),
            ("Thiên Cơ Cẩm Nang", self._mo_tccn, MA_LIET_KE_TCCN),
        ):
            if not mo(game):
                self.in_log(f"{ten}: không mở được {ten_kho} để kiểm tra hết đồ")
                return False
            bang = self._liet_ke_vat(game, ma_liet_ke)
            try:
                game.lua.chay(MA_DONG_CUA_SO)
            except (LoiLua, OSError):
                pass
            if bang in ("khong", "dong"):
                self.in_log(f"{ten}: không liệt kê được {ten_kho}, chưa coi là xong")
                return False
            con = [ten_vat for _, ten_vat, _ in bang if la_vat_pham_gop(ten_vat)]
            if con:
                self.in_log(f"{ten}: {ten_kho} còn {len(con)} ô đồ gộp (vd: {con[0]})")
                return False
        return True

    def _mo_tccn(self, game):
        lua = game.lua
        if lua.chay(MA_TCCN_DANG_MO) == b"true":
            return True
        lua.chay(MA_DONG_CUA_SO)
        lua.chay(MA_MO_TCCN)
        if not self._cho(lambda: lua.chay(MA_TCCN_DANG_MO) == b"true", GIAY_CHO_CUA_SO):
            return False
        # Server đổ ItemID vào ô ActionButton sau khi mở — chờ một nhịp.
        self.dung.wait(0.8)
        return True

    def _mo_kho_game(self, game, ten):
        lua = game.lua
        if lua.chay(MA_KHO_DANG_MO) == b"true":
            return True
        lua.chay(MA_DONG_CUA_SO)
        try:
            NhanDoTanThu(game, ten, self.in_log, self.dung.is_set, lambda _: None)._noi_chuyen(
                NPC_TAN_THU, (DONG_THUONG_KHO,))
        except DungPhoBan:
            raise _Dung()
        except LoiPhoBan as loi:
            self.in_log(f"{ten}: không mở được Thương khố ({loi})")
            return False
        return bool(self._cho(lambda: lua.chay(MA_KHO_DANG_MO) == b"true", GIAY_CHO_CUA_SO))

    def _liet_ke_vat(self, game, ma_liet_ke):
        """Đọc danh sách ô. Cửa sổ vừa mở thường trả rỗng trước khi server đổ đồ — đọc lại vài lần."""
        raw = game.lua.chay(ma_liet_ke)
        self._raw_liet_ke = raw
        bang = self._doc_bang_vat(raw)
        lan = 0
        while bang == [] and lan < 6 and getattr(self, "dung", None) is not None:
            self.dung.wait(0.5)
            self._kiem_tra_dung()
            raw = game.lua.chay(ma_liet_ke)
            self._raw_liet_ke = raw
            bang = self._doc_bang_vat(raw)
            lan += 1
        return bang

    def _cho_tui_tang(self, game, ten_vat, truoc, lan=24):
        for _ in range(lan):
            if self._tong_trong_tui(game, ten_vat) > truoc:
                return True
            self.dung.wait(0.15)
        return False

    def _ruong_mat_o(self, game, ma_liet_ke, loc_ten, chi_so, ten_vat):
        bang2 = self._doc_bang_vat(game.lua.chay(ma_liet_ke))
        if not isinstance(bang2, list):
            return False
        con = [(i, t) for i, t, _ in bang2 if loc_ten(t)]
        if not any(bo_dau(t) == bo_dau(ten_vat) for _, t in con):
            return True
        return (chi_so, ten_vat) not in {(i, t) for i, t in con} and not any(
            i == chi_so and bo_dau(t) == bo_dau(ten_vat) for i, t in con)

    @staticmethod
    def _parse_toa_do_o_kho(kq):
        """Từ '1|l,r,t,b|ten' hoặc '0|l,r,t,b|ten' → ((cx, cy), ten_nut)."""
        chu = kq.decode("utf-8", "replace") if isinstance(kq, (bytes, bytearray)) else str(kq)
        if not (chu.startswith("1|") or chu.startswith("0|")):
            return None, chu
        phan = chu.split("|", 2)
        if len(phan) < 2 or "," not in phan[1]:
            return None, phan[1] if len(phan) > 1 else chu
        try:
            so = phan[1].split(",")
            if len(so) != 4:
                return None, chu
            l, r, t, b = (int(float(x)) for x in so)
        except (TypeError, ValueError):
            return None, chu
        ten_nut = phan[2] if len(phan) > 2 else ""
        return ((l + r) // 2, (t + b) // 2), ten_nut

    def _chuot_phai_o_kho(self, game, ten, chi_so, ten_nut=""):
        """Chuột phải thật lên ô rương — toạ độ lấy bằng GetPixelRect trong Bank_Env."""
        try:
            game.lua.chay('if not IsWindowShow("Packet") then OpenWindow("Packet") end')
            self.dung.wait(0.35)
        except (LoiLua, OSError):
            pass
        try:
            kq = game.lua.chay(MA_TOA_DO_O_KHO.replace("{i}", str(chi_so)))
        except (LoiLua, OSError) as loi:
            self.in_log(f"{ten}: không đọc được toạ độ ô rương ({loi})")
            return False
        diem, ten_hien = self._parse_toa_do_o_kho(kq)
        if diem is None:
            self.in_log(f"{ten}: không có GetPixelRect cho ô rương"
                        + (f" (thấy: {ten_hien[:120]})" if ten_hien else ""))
            return False
        try:
            bam_phai(game.lua.hwnd, diem)
            self.in_log(f"{ten}: chuột phải thật {ten_hien or ten_nut or f'ô{chi_so}'} @ {diem}")
            return True
        except (LoiKeoTha, OSError) as loi:
            self.in_log(f"{ten}: không chuột phải thật được ô rương ({loi})")
            return False

    def _rut_mot_kho(self, game, ten, ten_kho, mo, ma_liet_ke, ma_rut, giay_cho, loc=None):
        """True = rút được ≥1; False = liệt kê được, hết món khớp; None = lỗi / rút trượt còn món.

        Rương/TCCN: mỗi lần rút xong liệt kê lại (ô dồn chỉ số), rút hết món gộp
        cho đến khi túi gần đầy — không dừng ở ô đầu.
        """
        if not mo(game):
            self.in_log(f"{ten}: không mở được {ten_kho}")
            return None
        loc_ten = loc or la_vat_pham_gop
        la_ruong = "khố" in ten_kho or ten_kho.startswith("Thương")
        la_tccn = ten_kho.startswith("Thiên")
        lay = False
        da_liet_ke = False
        while True:
            self._kiem_tra_dung()
            bang = self._liet_ke_vat(game, ma_liet_ke)
            if bang == "khong":
                self.in_log(f"{ten}: game không có lệnh liệt kê {ten_kho}")
                game.lua.chay(MA_DONG_CUA_SO)
                return None
            if bang == "dong":
                self.in_log(f"{ten}: {ten_kho} bị đóng")
                return None
            da_liet_ke = True
            khop = [(i, ten_vat, so) for i, ten_vat, so in bang if loc_ten(ten_vat)]
            if not khop:
                if not lay:
                    mau = ", ".join(ten_vat for _, ten_vat, _ in bang[:3])
                    raw = getattr(self, "_raw_liet_ke", b"") or b""
                    them = ""
                    if raw.startswith(b"debug"):
                        them = " (" + raw.decode("utf-8", "replace")[:160] + ")"
                    self.in_log(f"{ten}: {ten_kho} liệt kê {len(bang)} ô"
                                + (f", không có món cần rút (vd: {mau})" if bang else ", không thấy ô nào")
                                + them)
                break
            if self._o_trong_dao_cu(game) < 2:
                self.in_log(f"{ten}: túi gần đầy sau khi rút {ten_kho}, giao bớt rồi rút tiếp")
                break
            # Luôn lấy ô đầu trong danh sách mới (sau rút, chỉ số ô cũ lệch).
            chi_so, ten_vat, _so = khop[0]
            truoc = self._tong_trong_tui(game, ten_vat)
            kq = b""
            if la_ruong:
                try:
                    kq = game.lua.chay(ma_rut.replace("{i}", str(chi_so)))
                except (LoiLua, OSError) as loi:
                    self.in_log(f"{ten}: không gọi được Bank:MoveItemToPacket ({loi})")
                    game.lua.chay(MA_DONG_CUA_SO)
                    if lay or self._do_can_giao(game, set()):
                        return True
                    return None
                self.in_log(f"{ten}: Thương khố MoveItemToPacket({chi_so}) → {kq.decode('utf-8', 'replace')}")
                self.dung.wait(giay_cho)
            elif la_tccn:
                try:
                    kq = game.lua.chay(ma_rut.replace("{i}", str(chi_so)))
                except (LoiLua, OSError) as loi:
                    self.in_log(f"{ten}: không gọi được Packet_Temporary_Select ({loi})")
                    game.lua.chay(MA_DONG_CUA_SO)
                    if lay or self._do_can_giao(game, set()):
                        return True
                    return None
                self.in_log(f"{ten}: Thiên Cơ Select({chi_so}) số {SO_RUT_TCCN} → {kq.decode('utf-8', 'replace')}")
                self.dung.wait(giay_cho)
            else:
                kq = game.lua.chay(ma_rut.replace("{i}", str(chi_so)))
                self.dung.wait(giay_cho)
            tang = self._cho_tui_tang(game, ten_vat, truoc)
            if not tang and kq not in (b"dong",):
                tang = self._ruong_mat_o(game, ma_liet_ke, loc_ten, chi_so, ten_vat)
            if tang:
                lay = True
                self.in_log(f"{ten}: đã rút {ten_vat} từ {ten_kho}"
                            + (f" (nhập {SO_RUT_TCCN})" if la_tccn else "")
                            + (f", còn {len(khop) - 1}+ ô" if len(khop) > 1 else ""))
                continue
            if not la_ruong and (kq in (b"dong", b"khong") or kq == b"0"
                                 or kq.startswith(b"khong")):
                self.in_log(f"{ten}: không rút được {ten_vat} ở {ten_kho}")
            else:
                self.in_log(f"{ten}: bấm rút {ten_vat} ở {ten_kho} nhưng túi không tăng")
            game.lua.chay(MA_DONG_CUA_SO)
            if lay or self._do_can_giao(game, set()):
                return True
            return None
        game.lua.chay(MA_DONG_CUA_SO)
        if not da_liet_ke:
            return None
        return lay

    def _xep_tui_chinh(self):
        """Sau mỗi lần giao: acc chính bấm Xếp trong túi đồ (Packet_PackUp_Clicked)."""
        ten = self.tk_chinh["nhan_vat"]
        try:
            self.chinh.lua.chay('if not IsWindowShow("Packet") then OpenWindow("Packet") end')
            time.sleep(0.4)
            self.chinh.lua.chay(trong_cua_so("Packet", "Packet_PackUp_Clicked()"))
            time.sleep(0.6)
            self.in_log(f"{ten}: đã bấm Xếp túi đồ")
        except (LoiLua, OSError) as loi:
            self.in_log(f"{ten}: không bấm được Xếp túi ({loi})")

    def _o_trong(self):
        so_o = [int(float(x)) for x in self.chinh.lua.chay(MA_KICH_THUOC_TUI).decode().split("\t")]
        dung = {"base": 0, "material": 0}
        for ten_tui, _ in doc_tui(self.chinh.lua):
            dung[ten_tui] += 1
        return {"base": so_o[0] - dung["base"], "material": so_o[1] - dung["material"]}

    def _tui_chinh(self):
        return doc_tui(self.chinh.lua)

    def _do_da_nhan(self):
        ma = set(self.tien_trinh["ma_da_nhan"])
        return {o: v for o, v in self._tui_chinh().items() if v[0] in ma}

    def _don_tui_chinh(self):
        trong = self._o_trong()
        if min(trong.values()) >= SO_O_TOI_THIEU:
            return
        ten = self.tk_chinh["nhan_vat"]
        self.in_log(f"{ten}: túi còn {trong['base']} ô Đạo cụ, {trong['material']} ô Nguyên liệu trống, cất đồ")
        self.bao_trang_thai(f"{ten}: cất đồ vào Thiên Cơ Cẩm Nang / Thương khố")
        # Gộp đồ: cất TCCN → rút 100/300 từ rương + đổi 20K/30K → cất Thương khố.
        # Giao dịch cho acc chính: chỉ cất TCCN + Thương khố.
        self._cat_tccn()
        if getattr(self, "chi_giao_gop", False):
            self._hop_thanh_phieu()
        kho_day = self._cat_kho(cat_het=True)
        trong = self._o_trong()
        if min(trong.values()) < SO_O_TOI_THIEU:
            # Rương đầy (hoặc không cất hết) mà túi vẫn chật → cất tạm mọi món Đạo cụ vào TCCN.
            self.in_log(f"{ten}: túi vẫn chật"
                        + (" — Thương khố đã đầy" if kho_day else "")
                        + ", cất tạm mọi món Đạo cụ vào Thiên Cơ Cẩm Nang")
            self._cat_tccn(cat_bat_ky=True)
            trong = self._o_trong()
        if min(trong.values()) < SO_O_TOI_THIEU:
            raise LoiGiaoAccChinh(f"Thiên Cơ Cẩm Nang và Thương khố đã đầy (túi {ten} còn {trong['base']} ô Đạo cụ, "
                                  f"{trong['material']} ô Nguyên liệu trống)")

    def _cat_mot_o(self, o, ma_cat):
        lua = self.chinh.lua
        truoc = doc_tui(lua).get(o)
        if truoc is None:
            return "0"
        for _ in range(SO_LAN_THU_CAT):
            self._cho(lambda: time.time() - self.luc_cat >= GIAY_GIUA_HAI_LAN_CAT, GIAY_GIUA_HAI_LAN_CAT, 0.1)
            kq = lua.chay(ma_cat)
            self.luc_cat = time.time()
            if kq == b"dong":
                return "dong"
            if self._cho(lambda: doc_tui(lua).get(o) != truoc, GIAY_CHO_CAT, 0.3):
                return "1"
        return "0"

    def _cat_tccn(self, cat_bat_ky=False):
        """Cất Đạo cụ vào TCCN.

        Mặc định: đồ thường + Phiếu KNB 2000 (giữ 100/300 để hợp thành).
        cat_bat_ky: cất mọi ô Đạo cụ (kể cả phiếu) — dùng khi rương đầy, tạm giải phóng túi.
        """
        lua = self.chinh.lua
        if cat_bat_ky:
            cac_o = [o for o, _ in sorted(self._tui_chinh().items()) if o[0] == "base"]
        else:
            cac_o = [o for o, (_, _, ten) in sorted(self._tui_chinh().items())
                     if o[0] == "base" and (not la_phieu_knb(ten) or la_phieu_cat_tccn(ten))]
        if not cac_o:
            return
        lua.chay(MA_DONG_CUA_SO)
        lua.chay(MA_MO_TCCN)
        if not self._cho(lambda: lua.chay(MA_TCCN_DANG_MO) == b"true", GIAY_CHO_CUA_SO):
            self.in_log("Không mở được Thiên Cơ Cẩm Nang")
            return
        da_cat = 0
        for o in cac_o:
            kq = self._cat_mot_o(o, MA_CAT_TCCN.replace("{o}", str(o[1])))
            if kq == "dong":
                self.in_log("Cửa sổ Thiên Cơ Cẩm Nang bị đóng giữa chừng")
                break
            da_cat += kq == "1"
        lua.chay(MA_DONG_CUA_SO)
        self.in_log(f"Đã cất {da_cat}/{len(cac_o)} ô vào Thiên Cơ Cẩm Nang"
                    + (" (tạm, mọi món)" if cat_bat_ky else ""))

    def _mo_kho(self):
        lua = self.chinh.lua
        if lua.chay(MA_KHO_DANG_MO) == b"true":
            return True
        lua.chay(MA_DONG_CUA_SO)
        try:
            NhanDoTanThu(self.chinh, self.tk_chinh["nhan_vat"], self.in_log, self.dung.is_set,
                         lambda _: None)._noi_chuyen(NPC_TAN_THU, (DONG_THUONG_KHO,))
        except DungPhoBan:
            raise _Dung()
        except LoiPhoBan as loi:
            self.in_log(f"Không mở được Thương khố: {loi}")
            return False
        return bool(self._cho(lambda: lua.chay(MA_KHO_DANG_MO) == b"true", GIAY_CHO_CUA_SO))

    def _co_phieu_nho(self):
        return any(la_phieu_nho(ten) for (_, _), (_, _, ten) in doc_tui(self.chinh.lua).items())

    def _so_phieu_nho(self):
        return sum(so for (_, _), (_, so, ten) in self._tui_chinh().items() if la_phieu_nho(ten))

    def _so_phieu_theo_muc(self):
        tong = {100: 0, 300: 0}
        for (_, _), (_, so, ten) in self._tui_chinh().items():
            m = muc_phieu_knb(ten)
            if m in tong:
                tong[m] += so
        return tong

    def _chua_o_truoc_doi(self):
        """Chừa ≥1 ô trống Đạo cụ để nhận phiếu 20K/30K; nếu vừa mở rương cất đồ thì rút 100/300."""
        da_mo_kho = False
        while self._o_trong()["base"] < 1:
            self._kiem_tra_dung()
            tui = self._tui_chinh()
            nho = [o for o, (_, _, ten) in tui.items() if o[0] == "base" and la_phieu_nho(ten)]
            khac = [o for o, (_, _, ten) in tui.items() if o[0] == "base" and not la_phieu_nho(ten)]
            o = (khac or (nho if len(nho) > 1 else [None]))[0]
            if o is None:
                self.in_log(f"{self.tk_chinh['nhan_vat']}: không còn ô nào cất được để chừa chỗ hợp thành")
                return False
            if not self._mo_kho():
                return False
            da_mo_kho = True
            if self._cat_mot_o(o, MA_CAT_KHO.replace("{tui}", o[0]).replace("{o}", str(o[1]))) != "1":
                self.chinh.lua.chay(MA_DONG_CUA_SO)
                return False
        if da_mo_kho:
            self._rut_phieu_nho_tu_kho()
        elif getattr(self, "chinh", None):
            self.chinh.lua.chay(MA_DONG_CUA_SO)
        return True

    def _rut_phieu_nho_tu_kho(self):
        """Mở Thương khố, rút Phiếu KNB 100/300 ra túi; dừng khi túi còn ≤1 ô trống (chừa chỗ đổi 20K/30K)."""
        ten = self.tk_chinh["nhan_vat"]
        if not getattr(self, "chinh", None):
            return False
        self.in_log(f"{ten}: rút Phiếu KNB 100/300 từ Thương khố (chừa 1 ô trống)")
        kq = self._rut_mot_kho(
            self.chinh, ten, "Thương khố",
            lambda _g: self._mo_kho(),
            MA_LIET_KE_KHO, MA_RUT_KHO, GIAY_GIUA_RUT_KHO,
            loc=la_phieu_nho,
        )
        return bool(kq)

    def _mo_cua_so_doi(self, ten):
        """Mở NPC Trao Đổi → Hợp Thành Vật Phẩm, trả về tên cửa sổ hoặc ""."""
        lua = self.chinh.lua
        try:
            lua.chay(MA_DONG_CUA_SO)
            NhanDoTanThu(self.chinh, ten, self.in_log, self.dung.is_set, lambda _: None)._noi_chuyen(
                NPC_TRAO_DOI, (("Hợp Thành Vật Phẩm",),))
        except DungPhoBan:
            raise _Dung()
        except (LoiPhoBan, LoiLua, OSError) as loi:
            self.in_log(f"{ten}: không mở được Hợp Thành Vật Phẩm ({loi})")
            return ""
        try:
            lua.chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
        except LoiLua:
            pass
        if self._cho(lambda: bool(lua.chay(MA_CUA_SO_DOI)), 12):
            return lua.chay(MA_CUA_SO_DOI).decode("utf-8", "replace").strip()
        dang_mo = lua.chay(MA_LIET_KE_CUA_SO_DOI).decode("utf-8", "replace").strip(",")
        self.in_log(f"{ten}: không nhận ra cửa sổ Đổi vật phẩm"
                    + (f" (đang mở: {dang_mo})" if dang_mo else " (không quét được tên cửa sổ nào)"))
        return ""

    def _o_phieu_20k_30k_tu_chuoi(self, raw):
        """Parse «ô\\ttên» → [ô_20K, ô_30K] (thiếu loại nào thì bỏ loại đó)."""
        tim = {}
        for dong in (raw or "").splitlines():
            phan = dong.split("\t", 1)
            if len(phan) < 2 or not phan[0].isdigit():
                continue
            o = int(phan[0])
            if la_cong_thuc_phieu(phan[1], 20000):
                tim.setdefault(20000, o)
            elif la_cong_thuc_phieu(phan[1], 30000):
                tim.setdefault(30000, o)
        return [tim[m] for m in (20000, 30000) if m in tim]

    def _o_phieu_20k_30k(self, mo, bao_raw=False):
        """Ô cố định Phiếu KNB 20K/30K (ghi tay); mo chỉ để tương thích chỗ gọi cũ."""
        del mo, bao_raw
        return list(O_DOI_PHIEU)

    def _tim_o_phieu_20k_30k(self, mo):
        """Trả về [ô 20K, ô 30K] theo ghi tay XiaoXiang_DuiHuanUI2_Clicked(6)/(7)."""
        del mo
        return list(O_DOI_PHIEU)

    def _mot_lan_doi_phieu(self, mo, ten, o, im_lang=False):
        """Clicked(o) rồi OK_Clicked — True nếu túi giảm phiếu 100 hoặc 300."""
        lua = self.chinh.lua
        try:
            truoc = self._so_phieu_theo_muc()
            kq = lua.chay(MA_BAM_O_DOI.replace("{mo}", mo).replace("{i}", str(o)))
            if kq != b"1":
                if not im_lang:
                    self.in_log(f"{ten}: không bấm được ô {o} ({kq.decode('utf-8', 'replace')})")
                return False
            self.dung.wait(GIAY_SAU_CHON_O_DOI)
            kq = lua.chay(MA_XAC_NHAN_DOI.replace("{mo}", mo))
            if kq != b"1":
                if not im_lang:
                    self.in_log(f"{ten}: không bấm được Xác nhận ô {o} ({kq.decode('utf-8', 'replace')})")
                return False
            time.sleep(GIAY_XAC_NHAN_PHIEU)
            sau = self._so_phieu_theo_muc()
        except LoiLua as loi:
            if not im_lang:
                self.in_log(f"{ten}: đổi phiếu ô {o} lỗi Lua ({loi})")
            return False
        if sau[100] < truoc[100] or sau[300] < truoc[300]:
            self.in_log(f"{ten}: ô {o} đổi được — phiếu 100: {truoc[100]}→{sau[100]}, "
                        f"300: {truoc[300]}→{sau[300]}")
            return True
        return False

    def _hop_thanh_phieu(self):
        """Rút 100/300 từ rương (chừa 1 ô) rồi đổi ô 6 (20K) / 7 (30K)."""
        ten = self.tk_chinh["nhan_vat"]
        lua = self.chinh.lua
        self.bao_trang_thai(f"{ten}: hợp thành Phiếu KNB 100/300 → 20K/30K")
        self._rut_phieu_nho_tu_kho()
        if not self._co_phieu_nho():
            self.in_log(f"{ten}: không có Phiếu KNB 100/300 trong túi/rương — bỏ qua hợp thành")
            return
        mo = ""
        da_doi = 0
        o_ten = list(O_DOI_PHIEU)
        while da_doi < SO_LAN_HOP_THANH_TOI_DA:
            self._kiem_tra_dung()
            try:
                muc = self._so_phieu_theo_muc()
            except LoiLua as loi:
                self.in_log(f"{ten}: dừng hợp thành — đọc túi lỗi ({loi})")
                break
            if muc[100] <= 0 and muc[300] <= 0:
                self._rut_phieu_nho_tu_kho()
                try:
                    muc = self._so_phieu_theo_muc()
                except LoiLua:
                    break
                if muc[100] <= 0 and muc[300] <= 0:
                    self.in_log(f"{ten}: hết phiếu KNB 100/300 trong túi/rương sau {da_doi} lần đổi")
                    break
                mo = ""
            if not self._chua_o_truoc_doi():
                self.in_log(f"{ten}: túi không còn ô trống để nhận 20K/30K, dừng hợp thành (đã đổi {da_doi} lần)")
                break
            try:
                con_mo = mo and lua.chay(f'return tostring(IsWindowShow("{mo}"))') == b"true"
            except LoiLua:
                con_mo = False
            if not con_mo:
                mo = self._mo_cua_so_doi(ten)
                if not mo:
                    break
                self.dung.wait(0.8)
                self.in_log(f"{ten}: cửa sổ đổi «{mo}», túi còn {self._o_trong()['base']} ô trống, "
                            f"phiếu 100={muc[100]}, 300={muc[300]} — ô {o_ten} (20K rồi 30K)")
            if not o_ten:
                self.in_log(f"{ten}: không có khung «Phiếu KNB 20K» / «30K» — dừng đổi phiếu")
                break
            giam_vong = False
            dung_som = False
            for o in o_ten:
                self._kiem_tra_dung()
                if not self._co_phieu_nho() or not self._chua_o_truoc_doi():
                    dung_som = True
                    break
                while da_doi < SO_LAN_HOP_THANH_TOI_DA and self._mot_lan_doi_phieu(mo, ten, o):
                    da_doi += 1
                    giam_vong = True
                    if not self._chua_o_truoc_doi() or not self._co_phieu_nho():
                        dung_som = True
                        break
                if dung_som:
                    break
            if dung_som:
                break
            if not giam_vong:
                self.in_log(f"{ten}: ô 20K/30K không đổi thêm được phiếu 100/300, dừng hợp thành "
                            f"(đã đổi {da_doi} lần; ô: {o_ten})")
                break
        if da_doi >= SO_LAN_HOP_THANH_TOI_DA:
            self.in_log(f"{ten}: đã đổi {da_doi} lần (tới giới hạn), dừng hợp thành")
        try:
            muc = self._so_phieu_theo_muc()
            self.in_log(f"{ten}: xong hợp thành — còn phiếu 100={muc[100]}, 300={muc[300]} (đổi {da_doi} lần)")
        except LoiLua:
            self.in_log(f"{ten}: xong hợp thành (đổi {da_doi} lần; không đọc lại được túi)")
        try:
            if mo and lua.chay(f'return tostring(IsWindowShow("{mo}"))') == b"true":
                lua.chay(f'CloseWindow("{mo}", true)')
        except LoiLua:
            pass
        try:
            lua.chay(MA_DONG_CUA_SO)
        except LoiLua:
            pass

    def _cat_kho(self, cat_het=False):
        lua = self.chinh.lua
        tui = self._tui_chinh()
        if cat_het or getattr(self, "chi_giao_gop", False):
            cac_o = [o for o in sorted(tui)]
        else:
            cac_o = [o for o, (_, _, ten_vat) in sorted(tui.items()) if not la_phieu_nho(ten_vat)]
        if not cac_o:
            return False
        if not self._mo_kho():
            self.in_log("Thương khố không mở")
            return False
        da_cat = 0
        for o in cac_o:
            o_trong = int(lua.chay(MA_O_TRONG_KHO))
            if o_trong < 0:
                self.in_log("Cửa sổ Thương khố bị đóng giữa chừng")
                break
            if o_trong == 0:
                self.in_log("Thương khố đã đầy")
                lua.chay(MA_DONG_CUA_SO)
                self.in_log(f"Đã cất {da_cat}/{len(cac_o)} ô vào Thương khố")
                return True
            kq = self._cat_mot_o(o, MA_CAT_KHO.replace("{tui}", o[0]).replace("{o}", str(o[1])))
            if kq == "dong":
                self.in_log("Cửa sổ Thương khố bị đóng giữa chừng")
                break
            da_cat += kq == "1"
        lua.chay(MA_DONG_CUA_SO)
        self.in_log(f"Đã cất {da_cat}/{len(cac_o)} ô vào Thương khố")
        return False

    def _chay_giao_don(self, con, mo_ta_loai):
        """Acc chính online rồi lần lượt giao từng nhân vật trong con."""
        self.ten_giu_online = {chuan_hoa(self.tk_chinh["nhan_vat"])} | {chuan_hoa(ten) for _, ten in con}
        self.tk_giu_online = {(self.tk_chinh["ten_dang_nhap"] or "").lower()} | {
            (tk["ten_dang_nhap"] or "").lower() for tk, _ in con}
        self._vao_acc_chinh()
        for so, (tk, ten) in enumerate(con, 1):
            self.bao_trang_thai(f"{so}/{len(con)}: {ten}")
            if getattr(self, "chi_giao_gop", False):
                self.thoat_sau_giao = so < len(con)
            if self._mot_truong_nhom(tk, ten):
                self.tien_trinh["da_xong"].append(ten)
                self._luu_tien_trinh()
        self.in_log(f"Xong tất cả nhân vật ({mo_ta_loai})")
        self.bao_trang_thai("Xong")


class LuongGiaoAccChinh(threading.Thread, GiaoAccChinhEngine):
    def __init__(self, hang_doi):
        super().__init__(daemon=True)
        self.hang_doi = hang_doi
        self.dung = threading.Event()
        self.cd = cai_dat()
        self.tk_chinh = {"ten_dang_nhap": self.cd["tai_khoan"], "mat_khau": self.cd["mat_khau"],
                         "nhan_vat": self.cd["nhan_vat"]}
        self.loai_tru = cac_tu_loai_tru(self.cd["loai_tru"])
        self.tat_ca_pho_ban = bool(self.cd.get("tat_ca_pho_ban"))
        self.bo_qua = []
        self.tk_khong_co_do = set()
        if self.tat_ca_pho_ban:
            ds = cac_nhan_vat_pho_ban(self.cd["tai_khoan"], self.cd["chi_hom_nay"], self.bo_qua)
        else:
            ds = cac_truong_nhom(self.cd["tai_khoan"], self.cd["chi_hom_nay"], self.bo_qua)
        self.ds_truong, self.bo_vi_so, self.them_tu_so = ap_dung_so_tui(ds, self.cd["tai_khoan"], so_tui_do.doc())
        self.chinh = None
        self.hwnd_truong = None
        self.pid_dieu_khien = set()
        self.cac_luong_con = []
        self.tien_trinh = {}
        self.luc_cat = 0.0
        self._pho_ban_da_luu = {}
        # Tài khoản đã bị đăng xuất để nhường client: tự đăng nhập khi diss không mở lại trong lúc giao.
        self.tk_da_thoat = set()
        self.ghi_so_tui = True
        self.thoat_sau_giao = self.tat_ca_pho_ban

    # ---------- dùng từ giao diện ----------

    def cac_tai_khoan(self):
        if not self.is_alive():
            return set()
        return ({self.tk_chinh["ten_dang_nhap"].lower()} | {tk["ten_dang_nhap"].lower() for tk, _ in self.ds_truong}
                | self.tk_da_thoat)

    def dang_dieu_khien(self, pid):
        if not self.is_alive():
            return False
        return pid in self.pid_dieu_khien or any(l.pid == pid and l.is_alive() for l in list(self.cac_luong_con))

    # ---------- chung ----------

    def in_log(self, chu):
        self.hang_doi.put(("log", f"[Giao acc chính] {chu}"))

    def bao_trang_thai(self, chu):
        self.hang_doi.put(("trang_thai_giao_acc_chinh", chu))

    def _luu_tien_trinh(self):
        luu_cai_dat(tien_trinh=self.tien_trinh)

    def run(self):
        try:
            self._chay()
        except _Dung:
            self.in_log("Đã dừng (tiến trình đã lưu, bấm Bắt đầu để đi tiếp)")
            self.bao_trang_thai("Đã dừng")
        except LoiGiaoAccChinh as loi:
            self.in_log(f"Dừng: {loi} (tiến trình đã lưu)")
            self.bao_trang_thai(f"Dừng: {loi}")
        except Exception:
            self.in_log(f"Lỗi không mong đợi\n{traceback.format_exc()}")
            self.bao_trang_thai("Lỗi, xem log")
        finally:
            self._khoi_phuc_phó_ban()
            for luong in self.cac_luong_con:
                luong.dung.set()
            if self.chinh:
                try:
                    self.chinh.lua.chay(MA_DONG_CUA_SO)
                except (LoiLua, OSError):
                    pass
            self.pid_dieu_khien.clear()

    def _tam_tat_phó_ban(self):
        """Tắt phó bản trên cấu hình để luồng auto đang chạy thoát vòng PMP/Sát Tinh ngay."""
        if self._pho_ban_da_luu:
            return
        for ten in cau_hinh.cac_nhan_vat():
            cd = cau_hinh.cua_nhan_vat(ten)
            pmp = cai_dat_pmp(cd)
            if not pmp.get("bat"):
                continue
            self._pho_ban_da_luu[ten] = copy.deepcopy(pmp)

            def sua(c):
                moi = dict(cai_dat_pmp(c))
                moi["bat"] = False
                c["pho_ban_pmp"] = moi

            cau_hinh.sua_nhan_vat(ten, sua)
        if self._pho_ban_da_luu:
            self.in_log(f"Tạm tắt phó bản {len(self._pho_ban_da_luu)} nhân vật trong lúc giao dịch")

    def _khoi_phuc_phó_ban(self):
        if not self._pho_ban_da_luu:
            return
        so = len(self._pho_ban_da_luu)
        for ten, pmp in self._pho_ban_da_luu.items():

            def sua(c, luu=pmp):
                c["pho_ban_pmp"] = copy.deepcopy(luu)

            cau_hinh.sua_nhan_vat(ten, sua)
        self._pho_ban_da_luu = {}
        self.in_log(f"Bật lại phó bản {so} nhân vật")

    def _chay(self):
        hom_nay_chu = date.today().isoformat()
        self.tien_trinh = dict(self.cd.get("tien_trinh") or {})
        if self.tien_trinh.get("ngay") != hom_nay_chu:
            self.tien_trinh = {"ngay": hom_nay_chu, "da_xong": [], "ma_da_nhan": []}
        for ly_do in dict.fromkeys(l for _, _, l in self.bo_qua):
            cac = list(dict.fromkeys(tk if ly_do.startswith("tài khoản") else ten
                                     for tk, ten, l in self.bo_qua if l == ly_do))
            self.in_log(f"Bỏ qua {len(cac)} ({ly_do}): {', '.join(cac)}")
        if self.bo_vi_so:
            self.in_log(f"Bỏ qua {len(self.bo_vi_so)} (sổ túi đồ ghi không có đồ): {', '.join(self.bo_vi_so)}")
        so = so_tui_do.doc()
        if self.them_tu_so:
            self.in_log(f"Thêm {len(self.them_tu_so)} nhân vật sổ túi đồ ghi còn đồ: " + ", ".join(
                f"{ten} ({so_tui_do.mo_ta(so_tui_do.muc_cua(so, ten))})" for _, ten in self.them_tu_so))
        da_xong_ds = {chuan_hoa(t) for t in self.tien_trinh["da_xong"]}
        # Đã giao hôm nay nhưng sau đó đi phó bản tiếp (sổ ghi lại có đồ) thì giao lại.
        con = [(tk, ten) for tk, ten in self.ds_truong
               if chuan_hoa(ten) not in da_xong_ds or so_tui_do.can_giao(so_tui_do.muc_cua(so, ten))]
        loai = "mọi acc phó bản" if self.tat_ca_pho_ban else "trưởng nhóm"
        self.in_log(f"Bắt đầu: acc chính {self.tk_chinh['nhan_vat']}, {len(self.ds_truong)} nhân vật ({loai})"
                    + (" đã đi hôm nay" if self.cd["chi_hom_nay"] else "")
                    + f", đã xong {len(self.ds_truong) - len(con)}, còn {len(con)}: "
                    + ", ".join(ten for _, ten in con))
        if not con:
            self.bao_trang_thai(f"Xong (không còn nhân vật {loai})")
            return
        self._tam_tat_phó_ban()
        try:
            self._chay_giao(con, loai)
        finally:
            self._khoi_phuc_phó_ban()

    def _chay_giao(self, con, loai):
        self.ten_giu_online = {chuan_hoa(self.tk_chinh["nhan_vat"])} | {chuan_hoa(ten) for _, ten in con}
        self.tk_giu_online = {(self.tk_chinh["ten_dang_nhap"] or "").lower()} | {
            (tk["ten_dang_nhap"] or "").lower() for tk, _ in con}
        self._vao_acc_chinh()
        ten_truong = ten_cac_truong_nhom(self.tk_chinh["ten_dang_nhap"]) if self.tat_ca_pho_ban else set()
        so_tui = so_tui_do.doc()
        for so, (tk, ten) in enumerate(con, 1):
            self.bao_trang_thai(f"{so}/{len(con)}: {ten}")
            # Chỉ đoán theo tài khoản khi sổ chưa có nhân vật này; sổ ghi còn đồ / chưa rõ thì luôn đăng nhập.
            if self.tat_ca_pho_ban and so_tui_do.muc_cua(so_tui, ten) is None \
                    and bo_qua_cung_tai_khoan(tk, ten, self.tk_khong_co_do, ten_truong):
                self.in_log(f"{ten}: nhân vật khác của {tk['ten_dang_nhap']} không có đồ (đã giao cho trưởng nhóm), "
                            "bỏ qua không đăng nhập")
                self.tien_trinh["da_xong"].append(ten)
                self._luu_tien_trinh()
                continue
            if self._mot_truong_nhom(tk, ten):
                self.tien_trinh["da_xong"].append(ten)
                self._luu_tien_trinh()
        self.in_log(f"Xong tất cả nhân vật ({loai})")
        self._thoat_acc_chinh()
        self.bao_trang_thai("Xong")

    def _thoat_acc_chinh(self):
        """Giao xong thì acc chính về chọn máy chủ, xoay vòng dùng lại client."""
        if not self.chinh:
            return
        ten = self.tk_chinh["nhan_vat"]
        self.in_log(f"{ten}: giao xong, thoát acc chính")
        self._thoat_game_pho_ban(self.chinh, ten)
        tk = (self.tk_chinh.get("ten_dang_nhap") or "").lower()
        if tk:
            self.tk_da_thoat.add(tk)
        self.chinh = None
