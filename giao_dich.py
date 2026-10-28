"""
GIAO DỊCH: đội viên chuyển đồ cho trưởng nhóm (dò từ một lần giao dịch caychay9 -> caychay10).

Hàm Lua của game (Exchange.lua, ContexMenu.lua, MainMenuBar.lua):
    Mời          : chọn người kia làm mục tiêu (SetMainTargetFromList(id, true, false), id lấy từ GetPlayerFromList)
                   rồi Exchange:SendExchangeApply(), như menu chuột phải "Giao dịch".
    Nhận lời mời : Exchange:IsStillAnyAppInList() -> Exchange:OpenExchangeFrame(), như nút giao dịch nhấp nháy.
    Đặt đồ       : chuột phải ô túi (nút ô túi :DoAction()) khi cửa sổ Exchange đang mở; tối đa 5 món mỗi lần.
                   Đồ đã đặt: EnumAction(i, "ex_self"), i = 0..4.
    Khóa         : Exchange_Lock_Button_Clicked() (cửa sổ Exchange); khóa rồi mở lại phải chờ 10 giây mới khóa lại.
    Đồng ý       : Trade_Accept_Button_Clicked() khi cả hai đã khóa; xong thì cửa sổ Exchange tự đóng.
    Hủy          : Exchange_Cancel().
Hai người cách nhau quá 6 thì cửa sổ tự đóng, nên đội viên chạy tới sát trưởng nhóm trước.
Đồ mới nhặt = (túi, mã) có số lượng nhiều hơn ảnh túi gốc trong ngày (anh_tui_goc: lần đầu thấy nhân vật trong ngày,
lưu ra DUONG_DAN_ANH_TUI để dừng / chạy lại / vào lại game vẫn biết đồ đã nhặt trước đó). Không chuyển tiền.
"""
import json
import math
import os
import threading
import time
from datetime import date

from auto_chuyen_sinh import chuan_hoa
from bang_ma_viscii import giai_ma
from dang_nhap import chuoi_lua, trong_cua_so
from thu_muc import THU_MUC_APP

CAC_TUI = ("base", "material")
SO_O_GIAO_DICH = 5
KHOANG_CACH_GIAO_DICH = 3
GIAY_CHAY_TOI = 40
GIAY_GUI_LAI_VI_TRI = 3
GIAY_CHO = 6
SO_LAN_GIAO_DICH_TOI_DA = 20

MA_TUI = ('local s = "" for _, t in ipairs({' + ",".join(f'"{t}"' for t in CAC_TUI) + '}) do '
          'for i = 0, 99 do local a = PlayerPackage:EnumItem(t, i) '
          'if a and a:GetID() ~= 0 then s = s .. t .. "\\t" .. i .. "\\t" .. a:GetDefineID() .. "\\t" .. a:GetNum() '
          '.. "\\t" .. a:GetName() .. "\\n" end end end return s')
MA_CO_LOI_MOI = 'return tostring(Exchange:IsStillAnyAppInList())'
MA_DANG_MO = 'return tostring(IsWindowShow("Exchange"))'
MA_TRANG_THAI = ('if not IsWindowShow("Exchange") then return "dong" end '
                 'local n = 0 for i = 0, 4 do local a = EnumAction(i, "ex_self") if a and a:GetID() ~= 0 then n = n + 1 end end '
                 'return tostring(n) .. "\\t" .. tostring(Exchange:IsLocked("self")) .. "\\t" '
                 '.. tostring(Exchange:IsLocked("other"))')
MA_DAT_DO = trong_cua_so("Packet", 'local a = PlayerPackage:EnumItem("{tui}", {o}) '
                                   'if not a or a:GetID() == 0 then return "0" end '
                                   'Packet_Space_Line1_Row1_button:SetActionItem(a:GetID()) '
                                   'Packet_Space_Line1_Row1_button:DoAction() return "1"')
MA_KHOA = trong_cua_so("Exchange", 'if IsWindowShow("Exchange") and not Exchange:IsLocked("self") then '
                                   'Exchange_Lock_Button_Clicked() end')
MA_DONG_Y = trong_cua_so("Exchange", 'if IsWindowShow("Exchange") then Trade_Accept_Button_Clicked() end')
MA_HUY = trong_cua_so("Exchange", 'if IsWindowShow("Exchange") then Exchange_Cancel() end')


class LoiGiaoDich(Exception):
    pass


def doc_tui(lua):
    """{(túi, ô): (mã, số lượng, tên)} của túi đạo cụ và nguyên liệu."""
    tui = {}
    for dong in giai_ma(lua.chay(MA_TUI)).split("\n"):
        phan = dong.split("\t")
        if len(phan) == 5:
            tui[(phan[0], int(phan[1]))] = (int(float(phan[2])), int(float(phan[3])), phan[4])
    return tui


def chup_tui(lua):
    """{(túi, mã): tổng số lượng} để so sau phó bản."""
    tong = {}
    for (ten_tui, _), (ma, so, _) in doc_tui(lua).items():
        tong[(ten_tui, ma)] = tong.get((ten_tui, ma), 0) + so
    return tong


DUONG_DAN_ANH_TUI = os.path.join(THU_MUC_APP, "anh_tui_goc.json")
_khoa_anh_tui = threading.Lock()


def _doc_file_anh_tui(duong_dan):
    try:
        with open(duong_dan, encoding="utf-8") as f:
            du_lieu = json.load(f)
    except (OSError, ValueError):
        return {}
    return du_lieu if isinstance(du_lieu, dict) else {}


def anh_tui_goc(ten, lua, duong_dan=None, hom_nay=None):
    """
    Ảnh túi gốc hôm nay của nhân vật ten: đã lưu (cùng ngày) thì dùng lại, chưa thì chụp túi bây giờ và lưu.
    Dừng / bắt đầu lại / vào lại game không chụp lại, nên đồ nhặt trước đó vẫn được tính là đồ mới.
    """
    duong_dan = duong_dan or DUONG_DAN_ANH_TUI
    ngay = (hom_nay or date.today()).isoformat()
    khoa = chuan_hoa(ten)
    with _khoa_anh_tui:
        du_lieu = _doc_file_anh_tui(duong_dan)
        muc = du_lieu.get(khoa)
        if isinstance(muc, dict) and muc.get("ngay") == ngay:
            return {(t, int(m)): int(s) for t, m, s in muc.get("tui", [])}
        anh = chup_tui(lua)
        du_lieu = {k: v for k, v in du_lieu.items() if isinstance(v, dict) and v.get("ngay") == ngay}
        du_lieu[khoa] = {"ngay": ngay, "tui": [[t, m, s] for (t, m), s in sorted(anh.items())]}
        tam = f"{duong_dan}.{os.getpid()}.tmp"
        try:
            with open(tam, "w", encoding="utf-8") as f:
                json.dump(du_lieu, f, ensure_ascii=False)
            os.replace(tam, duong_dan)
        except OSError:
            pass
        return anh


def o_do_moi(lua, anh_truoc):
    """
    Các ô (túi, ô) chứa đồ mới nhặt so với anh_truoc. Một mã nhiều hơn lúc chụp thì lấy các ô của mã đó (ô sau trước)
    tới khi đủ số tăng thêm; ô chồng lẫn đồ cũ và đồ mới thì đưa cả ô.
    """
    tui = doc_tui(lua)
    cac_o = []
    theo_ma = {}
    for (ten_tui, o), (ma, so, _) in tui.items():
        theo_ma.setdefault((ten_tui, ma), []).append((o, so))
    for khoa, ds in theo_ma.items():
        tang = sum(so for _, so in ds) - anh_truoc.get(khoa, 0)
        for o, so in sorted(ds, reverse=True):
            if tang <= 0:
                break
            cac_o.append((khoa[0], o))
            tang -= so
    return sorted(cac_o)


class GiaoDich:
    """Một đội viên (dua) chuyển đồ cho trưởng nhóm (nhan); dua / nhan là Game, ten_nhan là tên nhân vật nhận."""

    def __init__(self, dua, nhan, ten_dua, ten_nhan, in_log, nen_dung=lambda: False):
        self.dua, self.nhan = dua, nhan
        self.ten_dua, self.ten_nhan = ten_dua, ten_nhan
        self.in_log, self.nen_dung = in_log, nen_dung
        # [(tên món, số lượng)] đã sang tay người nhận, cộng dồn sau mỗi lần giao dịch (kể cả khi lần sau lỗi).
        self.chi_tiet = []

    def _cho(self, dieu_kien, giay):
        het_han = time.time() + giay
        while True:
            if self.nen_dung():
                raise LoiGiaoDich("đã dừng")
            ket_qua = dieu_kien()
            if ket_qua or time.time() > het_han:
                return ket_qua
            time.sleep(0.3)

    def _khoang_cach(self):
        a, b = self.dua.thong_tin(), self.nhan.thong_tin()
        if not (a and b) or a["map"] != b["map"]:
            return None, b
        return math.hypot(a["x"] - b["x"], a["y"] - b["y"]), b

    def _lai_gan(self):
        kc, b = self._khoang_cach()
        if kc is None:
            raise LoiGiaoDich(f"{self.ten_dua} và {self.ten_nhan} không cùng map")
        if kc <= KHOANG_CACH_GIAO_DICH:
            return
        lan_gui = [0.0]

        def toi_noi():
            kc, b = self._khoang_cach()
            if kc is not None and kc <= KHOANG_CACH_GIAO_DICH:
                return True
            # Lệnh chạy có thể bị bỏ (đang tải map, bị chặn đường): gửi lại vị trí trưởng nhóm định kỳ.
            if b and time.time() - lan_gui[0] >= GIAY_GUI_LAI_VI_TRI:
                lan_gui[0] = time.time()
                self.dua.lua.chay(f"AutoRunToTarget({int(b['x']) + 1}, {int(b['y'])})")
            return False
        if not self._cho(toi_noi, GIAY_CHAY_TOI):
            raise LoiGiaoDich(f"{self.ten_dua} chạy {GIAY_CHAY_TOI} giây chưa tới chỗ {self.ten_nhan}")

    def _trang_thai(self, game):
        phan = game.lua.chay(MA_TRANG_THAI).decode().split("\t")
        if phan == ["dong"]:
            return None
        return int(phan[0]), phan[1] == "true", phan[2] == "true"

    def _mo(self):
        for g in (self.dua, self.nhan):
            g.lua.chay(MA_HUY)
        ma_moi = ('UpdatePlayerList(true) for i = 0, 15 do local id, ten = GetPlayerFromList(i) '
                  f'if ten == {chuoi_lua(self.ten_nhan)} then SetMainTargetFromList(id, true, false) '
                  'Exchange:SendExchangeApply() return "1" end end return "0"')
        if self.dua.lua.chay(ma_moi) != b"1":
            raise LoiGiaoDich(f"{self.ten_dua} không thấy {self.ten_nhan} ở gần")
        if not self._cho(lambda: self.nhan.lua.chay(MA_CO_LOI_MOI) == b"true", GIAY_CHO):
            raise LoiGiaoDich(f"{self.ten_nhan} không nhận được lời mời giao dịch")
        self.nhan.lua.chay("Exchange:OpenExchangeFrame()")
        if not self._cho(lambda: all(g.lua.chay(MA_DANG_MO) == b"true" for g in (self.dua, self.nhan)), GIAY_CHO):
            raise LoiGiaoDich("cửa sổ giao dịch không mở")

    def _mot_lan(self, cac_o):
        """Giao dịch tối đa 5 ô. Trả về các ô đã đặt được vào giao dịch."""
        self._mo()
        da_dat = []
        for ten_tui, o in cac_o:
            truoc = (self._trang_thai(self.dua) or (0,))[0]
            self.dua.lua.chay(MA_DAT_DO.replace("{tui}", ten_tui).replace("{o}", str(o)))
            if self._cho(lambda: (self._trang_thai(self.dua) or (0,))[0] > truoc, 2):
                da_dat.append((ten_tui, o))
        if not da_dat:
            self.dua.lua.chay(MA_HUY)
            return []
        # Hai bên khóa cùng lúc thì một bên có thể không thấy bên kia khóa, bấm đồng ý lúc đó là hủy giao dịch:
        # khóa lần lượt, chờ bên kia thấy rồi mới khóa tiếp / đồng ý.
        for g, ben_kia in ((self.dua, self.nhan), (self.nhan, self.dua)):
            g.lua.chay(MA_KHOA)
            if not self._cho(lambda: (self._trang_thai(ben_kia) or (0, False, False))[2], GIAY_CHO):
                self.dua.lua.chay(MA_HUY)
                raise LoiGiaoDich("hai bên chưa khóa được giao dịch")
        if not self._cho(lambda: all((self._trang_thai(g) or (0, False, False))[1:] == (True, True)
                                     for g in (self.dua, self.nhan)), GIAY_CHO):
            self.dua.lua.chay(MA_HUY)
            raise LoiGiaoDich("hai bên chưa thấy nhau khóa")
        for g in (self.dua, self.nhan):
            g.lua.chay(MA_DONG_Y)
            time.sleep(0.5)
        if not self._cho(lambda: all(g.lua.chay(MA_DANG_MO) != b"true" for g in (self.dua, self.nhan)), GIAY_CHO):
            self.dua.lua.chay(MA_HUY)
            raise LoiGiaoDich("bấm đồng ý mà giao dịch chưa xong")
        return da_dat

    def chuyen(self, cac_o):
        """Chuyển các ô (túi, ô) của dua cho nhan. Trả về số món (ô) đã chuyển."""
        if not cac_o:
            return 0
        self._lai_gan()
        tui_dau = doc_tui(self.dua.lua)
        con, da_chuyen, bo_qua = list(cac_o), 0, []
        for _ in range(SO_LAN_GIAO_DICH_TOI_DA):
            # Ô bị đổi chỗ sau mỗi lần giao dịch: lọc lại theo món đang nằm ở ô đó.
            tui = doc_tui(self.dua.lua)
            con = [o for o in con if o in tui and tui[o] == tui_dau.get(o)]
            if not con:
                break
            lan_nay = con[:SO_O_GIAO_DICH]
            da_dat = self._mot_lan(lan_nay)
            for o in lan_nay:
                if o not in da_dat:
                    bo_qua.append(o)
            con = [o for o in con if o not in lan_nay]
            tui_sau = doc_tui(self.dua.lua)
            for o in da_dat:
                if tui_sau.get(o) != tui_dau.get(o):
                    _, so, ten = tui_dau[o]
                    self.chi_tiet.append((ten, so))
                    da_chuyen += 1
        for o in bo_qua:
            ma, so, ten = tui_dau[o]
            self.in_log(f"{self.ten_dua}: không giao dịch được {ten} x{so} (đã khóa?)")
        self.in_log(f"{self.ten_dua}: đã chuyển {da_chuyen} món cho {self.ten_nhan}")
        return da_chuyen
