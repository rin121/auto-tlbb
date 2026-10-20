"""
TỰ CỘNG ĐIỂM TIỀM NĂNG VÀ TỰ DÙNG HỘP POINT (tab "Chuyển sinh", cài riêng từng nhân vật).

Điểm tiềm năng: bảng Alt+C là cửa sổ SelfEquip (SelfEquip.lua). Mỗi lần bấm "+" game cộng 1000 vào chỉ số và trừ
1000 ở Player:GetData("POINT_REMAIN"); bấm Duyệt gọi Player:SendAskManualAttr(STR, SPR, CON, INT, DEX) với đúng các
số đó. Auto gửi thẳng lệnh này: mỗi phần 1000 điểm cho lần lượt từng chỉ số đã tích (nối tiếp lượt trước), mỗi
lệnh tối đa 10000 điểm, phần lẻ dưới 1000 để lại giống bảng Alt+C.
Hộp Point: vật phẩm trong túi tên "Hộp Point 500" / "Hộp Point 800" (có mã màu ở đầu tên), dùng như chuột phải.
"""
import time

from auto_chuyen_sinh import chuan_hoa
from bang_ma_viscii import giai_ma
from dang_nhap import bo_ma_mau
from tu_dung_vat_pham import MA_DS_TUI

CAC_CHI_SO = (("str", "Cường lực"), ("spr", "Nội lực"), ("con", "Thể lực"), ("int", "Trí lực"),
              ("dex", "Thân pháp"))
DIEM_MOI_PHAN = 1000
# Server bỏ qua cả lệnh nếu cộng quá nhiều một lần (thử thật: 10000 nhận, 30000 / 42000 không nhận).
SO_PHAN_TOI_DA_MOI_LENH = 10
TEN_HOP_POINT = "hộp point"
GIAY_GIUA_MOI_LAN_XEM = 3
GIAY_CHO_GAME_TRA_LOI = 3
GIAY_NGHI_KHI_LOI = 60
SO_HOP_TOI_DA_MOI_LUOT = 20


def chia_diem(so_phan, cac_chi_so, bat_dau):
    """({khóa chỉ số: số điểm cộng}, thứ tự bắt đầu lượt sau): mỗi phần 1000 điểm cho lần lượt từng chỉ số."""
    cong = {khoa: 0 for khoa, _ in CAC_CHI_SO}
    for i in range(so_phan):
        cong[cac_chi_so[(bat_dau + i) % len(cac_chi_so)]] += DIEM_MOI_PHAN
    return cong, (bat_dau + so_phan) % len(cac_chi_so)


def mo_ta_cong(cong):
    return ", ".join(f"{ten} +{cong[khoa]}" for khoa, ten in CAC_CHI_SO if cong[khoa])


class TuCongDiem:
    def __init__(self, game, in_log):
        self.game = game
        self.in_log = in_log
        self.luc_xem = 0.0
        self.nghi_den = 0.0
        self.thu_tu = 0
        self.da_in_thu = None

    def cac_hop_point(self):
        """[(ô, số lượng, tên)] các Hộp Point trong túi, theo thứ tự ô."""
        ds = []
        for dong in self.game.lua.chay(MA_DS_TUI).split(b"\n"):
            if dong:
                o, so, ten = dong.split(b"\t", 2)
                ten = bo_ma_mau(giai_ma(ten)).strip()
                if chuan_hoa(ten).startswith(TEN_HOP_POINT):
                    ds.append((int(o), int(so), ten))
        return ds

    def _cho(self, dieu_kien):
        het_han = time.time() + GIAY_CHO_GAME_TRA_LOI
        while time.time() < het_han:
            time.sleep(0.2)
            if dieu_kien():
                return True
        return False

    def _in_thu(self, chu):
        if chu != self.da_in_thu:
            self.da_in_thu = chu
            self.in_log(chu)

    def _loi(self, chu):
        self.nghi_den = time.time() + GIAY_NGHI_KHI_LOI
        self.in_log(f"{chu}, thử lại sau {GIAY_NGHI_KHI_LOI} giây")

    def kiem_tra(self, ten, cai_dat, nen_dung=lambda: False):
        """Gọi mỗi lượt của vòng auto; tự giãn cách GIAY_GIUA_MOI_LAN_XEM giây."""
        cd = cai_dat.get("auto_cong_diem") or {}
        cac_chi_so = [khoa for khoa, _ in CAC_CHI_SO if khoa in cd.get("cac_chi_so", [])]
        cong_diem = bool(cd.get("bat") and cac_chi_so)
        if not (cong_diem or cd.get("tu_dung_hop_point")):
            return
        bay_gio = time.time()
        if bay_gio - self.luc_xem < GIAY_GIUA_MOI_LAN_XEM or bay_gio < self.nghi_den:
            return
        self.luc_xem = bay_gio
        chi_thu = cai_dat["chi_in_khong_bam"]
        if cd.get("tu_dung_hop_point"):
            self._dung_hop_point(ten, chi_thu, nen_dung)
        if cong_diem and not nen_dung() and time.time() >= self.nghi_den:
            self._cong_diem(ten, cac_chi_so, chi_thu)

    def _dung_hop_point(self, ten, chi_thu, nen_dung):
        for _ in range(SO_HOP_TOI_DA_MOI_LUOT):
            cac_hop = self.cac_hop_point()
            if not cac_hop or nen_dung():
                return
            o, _, ten_hop = cac_hop[0]
            if chi_thu:
                self._in_thu(f"  [THỬ] {ten}: sẽ dùng {ten_hop} ở ô {o + 1} của túi")
                return
            tong_truoc = sum(so for _, so, _ in cac_hop)
            diem_truoc = self.game.diem_tiem_nang()
            self.game.lua.chay(f"PlayerPackage:UseItem({o})")
            if not self._cho(lambda: sum(so for _, so, _ in self.cac_hop_point()) != tong_truoc):
                self._loi(f"{ten}: dùng {ten_hop} không được")
                return
            self.in_log(f"{ten}: đã dùng 1 {ten_hop}, điểm tiềm năng {diem_truoc} -> {self.game.diem_tiem_nang()}, "
                        f"còn {tong_truoc - 1} Hộp Point")

    def _cong_diem(self, ten, cac_chi_so, chi_thu):
        con = self.game.diem_tiem_nang()
        so_phan = con // DIEM_MOI_PHAN
        if so_phan <= 0:
            return
        if chi_thu:
            cong, _ = chia_diem(so_phan, cac_chi_so, self.thu_tu)
            self._in_thu(f"  [THỬ] {ten}: có {con} điểm tiềm năng, sẽ cộng {mo_ta_cong(cong)}")
            return
        tong = {khoa: 0 for khoa, _ in CAC_CHI_SO}
        while so_phan > 0:
            cong, thu_tu_sau = chia_diem(min(so_phan, SO_PHAN_TOI_DA_MOI_LENH), cac_chi_so, self.thu_tu)
            self.game.cong_diem_tiem_nang(cong)
            if not self._cho(lambda: self.game.diem_tiem_nang() < con):
                self._loi(f"{ten}: gửi cộng điểm tiềm năng ({mo_ta_cong(cong)}) mà game chưa nhận")
                break
            self.thu_tu = thu_tu_sau
            for khoa in tong:
                tong[khoa] += cong[khoa]
            con = self.game.diem_tiem_nang()
            so_phan = con // DIEM_MOI_PHAN
        if any(tong.values()):
            self.in_log(f"{ten}: tự cộng {sum(tong.values())} điểm tiềm năng ({mo_ta_cong(tong)}), còn {con} điểm")
