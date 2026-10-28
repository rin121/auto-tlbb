"""
Nút "Giao dịch ngay" khi không chạy xoay vòng: nhân vật đang chạy trong auto cùng nhóm game với một trưởng nhóm cũng
đang trong auto, túi có đồ mới nhặt (so với ảnh túi gốc trong ngày, giao_dich.anh_tui_goc) thì tạm dừng auto, chạy tới
trưởng nhóm giao đồ, xong bật lại auto như cũ. Không ai có đồ mới thì bỏ qua, không tạm dừng auto.
"""
import threading
import traceback

import bao_cao_giao_dich
import cau_hinh
from auto_chuyen_sinh import chuan_hoa
from giao_dich import GiaoDich, LoiGiaoDich, o_do_moi
from lua_game import LoiLua
from moi_nhom import doc_nhom
from pho_ban_pmp import cai_dat_pmp

GIAY_CHO_DUNG_AUTO = 3
SO_LAN_THU = 3
GIAY_GIUA_HAI_LAN = 5


def tam_dung_auto(cac_ten):
    """Tắt Auto + Phó bản (giữ nguyên bộ đếm hôm nay); trả về {tên: (bat_auto, bat phó bản)} để bật lại."""
    da_luu = {}
    for ten in cac_ten:
        def sua(cai_dat, ten=ten):
            da_luu[ten] = (cai_dat["bat_auto"], cai_dat_pmp(cai_dat)["bat"])
            cai_dat["bat_auto"] = False
            cai_dat["pho_ban_pmp"] = dict(cai_dat_pmp(cai_dat), bat=False)
        cau_hinh.sua_nhan_vat(ten, sua)
    return da_luu


def bat_lai_auto(da_luu):
    for ten, (bat_auto, bat_pho_ban) in da_luu.items():
        def sua(cai_dat, bat_auto=bat_auto, bat_pho_ban=bat_pho_ban):
            cai_dat["bat_auto"] = bat_auto
            cai_dat["pho_ban_pmp"] = dict(cai_dat_pmp(cai_dat), bat=bat_pho_ban)
        cau_hinh.sua_nhan_vat(ten, sua)


def chia_doi(cac_luong, doc_thanh_vien):
    """
    [(trưởng nhóm, [đội viên])] theo nhóm trong game; chỉ tính trưởng nhóm và đội viên đều có trong cac_luong.
    doc_thanh_vien(luong) -> tên các thành viên nhóm (trưởng nhóm đứng đầu), rỗng / None nếu không có nhóm.
    """
    theo_ten = {chuan_hoa(luong.ten): luong for luong in cac_luong}
    cac_doi = {}
    for luong in cac_luong:
        ds = doc_thanh_vien(luong)
        if not ds:
            continue
        khoa = chuan_hoa(ds[0])
        truong = theo_ten.get(khoa)
        if truong is None or truong is luong:
            continue
        cac_doi.setdefault(khoa, (truong, []))[1].append(luong)
    return list(cac_doi.values())


class LuongGiaoDichNgay(threading.Thread):
    """cac_luong: LuongNhanVat của các cửa sổ game (cần .ten, .dang_trong_game, .game, .anh_tui, .anh_tui_cua)."""

    def __init__(self, cac_luong, hang_doi):
        super().__init__(daemon=True)
        self.cac_luong = [luong for luong in cac_luong if luong.ten and luong.dang_trong_game]
        self.hang_doi = hang_doi
        self.dung = threading.Event()
        self.pid_dieu_khien = set()

    def in_log(self, chu):
        self.hang_doi.put(("log", f"[Giao dịch ngay] {chu}"))

    def dang_dieu_khien(self, pid):
        return self.is_alive() and pid in self.pid_dieu_khien

    def run(self):
        try:
            self._chay()
        except Exception:
            self.in_log(f"Lỗi không mong đợi\n{traceback.format_exc()}")

    @staticmethod
    def _doc_thanh_vien(luong):
        try:
            return doc_nhom(luong.game.lua)["thanh_vien"]
        except (LoiLua, OSError, ValueError):
            return None

    def _co_do_moi(self, dv):
        """Xem túi trước khi tạm dừng auto: đội viên có đồ mới (so với ảnh túi gốc trong ngày) không."""
        if dv.anh_tui is None or dv.anh_tui_cua != dv.ten:
            self.in_log(f"{dv.ten}: auto chưa chụp túi lúc vào game, chưa biết đồ nào mới nhặt — bỏ qua")
            return False
        try:
            cac_o = o_do_moi(dv.game.lua, dv.anh_tui)
        except (LoiLua, OSError):
            return False
        if not cac_o:
            self.in_log(f"{dv.ten}: không có đồ mới trong túi, khỏi giao dịch")
        return bool(cac_o)

    def _chay(self):
        cac_doi = chia_doi(self.cac_luong, self._doc_thanh_vien)
        if not cac_doi:
            self.in_log("Không có đội viên nào đang cùng nhóm (trong game) với trưởng nhóm cũng đang chạy trong auto")
            return
        cac_doi = [(truong, [dv for dv in doi_vien if self._co_do_moi(dv)]) for truong, doi_vien in cac_doi]
        cac_doi = [(truong, doi_vien) for truong, doi_vien in cac_doi if doi_vien]
        if not cac_doi:
            self.in_log("Không đội viên nào có đồ mới trong túi, bỏ qua (không tạm dừng auto)")
            return
        thanh_vien = [luong for truong, doi_vien in cac_doi for luong in [truong, *doi_vien]]
        self.in_log("Tạm dừng auto để giao dịch: " + "; ".join(
            f"{', '.join(dv.ten for dv in doi_vien)} → {truong.ten}" for truong, doi_vien in cac_doi))
        da_luu = tam_dung_auto([luong.ten for luong in thanh_vien])
        self.pid_dieu_khien = {luong.game.lua.pid for luong in thanh_vien}
        try:
            self.dung.wait(GIAY_CHO_DUNG_AUTO)
            for truong, doi_vien in cac_doi:
                for dv in doi_vien:
                    if self.dung.is_set():
                        return
                    self._chuyen_do(dv, truong)
        finally:
            self.pid_dieu_khien = set()
            bat_lai_auto(da_luu)
            self.in_log("Xong, bật lại auto như trước khi giao dịch")

    def _chuyen_do(self, dv, truong):
        for lan in range(1, SO_LAN_THU + 1):
            try:
                cac_o = o_do_moi(dv.game.lua, dv.anh_tui)
                if not cac_o:
                    if lan == 1:
                        self.in_log(f"{dv.ten}: không có đồ mới nhặt, khỏi giao dịch")
                    return
                self.in_log(f"{dv.ten}: có {len(cac_o)} ô đồ mới, giao dịch cho {truong.ten}")
                gd = GiaoDich(dv.game, truong.game, dv.ten, truong.ten, self.in_log, self.dung.is_set)
                try:
                    gd.chuyen(cac_o)
                finally:
                    bao_cao_giao_dich.ghi_va_bao(self.in_log, f"Giao dịch ngay (nhóm {truong.ten})", dv.ten,
                                                 truong.ten, gd.chi_tiet)
                return
            except (LoiGiaoDich, LoiLua, OSError) as loi:
                if self.dung.is_set():
                    return
                if lan >= SO_LAN_THU:
                    self.in_log(f"{dv.ten}: giao dịch cho {truong.ten} thất bại: {loi}")
                    return
                self.in_log(f"{dv.ten}: giao dịch cho {truong.ten} lỗi ({loi}), thử lại lần {lan + 1}")
            self.dung.wait(GIAY_GIUA_HAI_LAN)
