"""
RÚT NGỌC TỪ THIÊN CƠ CẨM NANG (tab Giao dịch, khung «Rút ngọc từ Thiên Cơ Cẩm Nang»).

Nhân vật đang trong game (user chọn tên) rút Mảnh Ngọc từ Thiên Cơ Cẩm Nang về túi cho đủ số viên user nhập
(MANH_MOT_VIEN mảnh = 1 viên). Rút như Gộp đồ về acc chính: Packet_Temporary_Select(ô) với g_EveryNum = số mảnh mỗi lần
(tối đa SO_RUT_TCCN, lần cuối chỉ rút phần còn thiếu), cách GIAY_GIUA_RUT_TCCN giây.
Túi không nhận thêm (hết ô): về Đại Lý, mở Thương khố ở NPC Tân Thủ, cất các ô Mảnh Ngọc (túi không có Mảnh Ngọc thì
cất mọi ô như Gộp đồ), rồi rút tiếp. Cất xong mà vẫn rút không được thì dừng.
"""
import re
import threading
import traceback

import cau_hinh
from dang_nhap import bo_dau
from giao_acc_chinh import (GIAY_GIUA_RUT_TCCN, MA_DONG_CUA_SO, MA_LIET_KE_TCCN, MA_RUT_TCCN_SO, SO_RUT_TCCN,
                            GiaoAccChinhEngine, LoiGiaoAccChinh, _Dung)
from giao_dich import doc_tui
from lua_game import LoiLua
from nhan_vat_moi import NPC_TAN_THU

KHOA_CAI_DAT = "rut_ngoc_tccn"
MAC_DINH = {"nhan_vat": "", "so_vien": 1}
MANH_MOT_VIEN = 500
SO_VIEN_TOI_DA = 10000
# Đọc lại túi sau mỗi lần rút (game cập nhật túi trễ vài nhịp).
LAN_CHO_TUI = 24
GIAY_CHO_TUI = 0.15


def cai_dat():
    gia_tri = dict(MAC_DINH)
    gia_tri.update(cau_hinh.chung().get(KHOA_CAI_DAT) or {})
    return gia_tri


def luu_cai_dat(**thay_doi):
    cau_hinh.dat_chung({KHOA_CAI_DAT: dict(cai_dat(), **thay_doi)})


def la_manh_ngoc(ten):
    """Mảnh Ngọc (kể cả «Mảnh Ngọc Vip»), bỏ mã màu #...."""
    return "manh ngoc" in bo_dau(re.sub(r"#[-0-9a-fA-F]*", "", ten or ""))


def so_manh_can(so_vien):
    try:
        return max(0, int(so_vien)) * MANH_MOT_VIEN
    except (TypeError, ValueError):
        return 0


def so_manh_lan_rut(con_lai, trong_o=None):
    """Số mảnh nhập cho một lần rút: không quá SO_RUT_TCCN, số còn thiếu, số trong ô Thiên Cơ (nếu đọc được)."""
    so = min(SO_RUT_TCCN, con_lai)
    if trong_o and trong_o > 1:
        so = min(so, trong_o)
    return max(0, so)


def mo_ta_manh(so_manh):
    vien, du = divmod(max(0, so_manh), MANH_MOT_VIEN)
    return f"{so_manh} mảnh ({vien} viên" + (f" + {du} mảnh" if du else "") + ")"


def ma_rut_tccn(chi_so, so):
    return MA_RUT_TCCN_SO.replace("{i}", str(int(chi_so))).replace("{so}", str(int(so)))


class LuongRutNgoc(threading.Thread, GiaoAccChinhEngine):
    def __init__(self, hang_doi, game, ten, so_vien):
        super().__init__(daemon=True)
        self.hang_doi = hang_doi
        self.dung = threading.Event()
        self.chinh = game
        self.ten = ten
        self.tk_chinh = {"ten_dang_nhap": "", "mat_khau": "", "nhan_vat": ten}
        self.so_vien = so_vien
        self.can = so_manh_can(so_vien)
        self.da_rut = 0
        self.luc_cat = 0.0

    def dang_dieu_khien(self, pid):
        return self.is_alive() and pid == self.chinh.lua.pid

    def in_log(self, chu):
        self.hang_doi.put(("log", f"[Rút ngọc] {chu}"))

    def bao_trang_thai(self, chu):
        self.hang_doi.put(("trang_thai_rut_ngoc", chu))

    def run(self):
        try:
            self._chay()
        except _Dung:
            self.in_log(f"{self.ten}: đã dừng, đã rút {mo_ta_manh(self.da_rut)}")
            self.bao_trang_thai("Đã dừng")
        except LoiGiaoAccChinh as loi:
            self.in_log(f"{self.ten}: dừng: {loi} — đã rút {mo_ta_manh(self.da_rut)}")
            self.bao_trang_thai(f"Dừng: {loi}")
        except (LoiLua, OSError) as loi:
            self.in_log(f"{self.ten}: dừng vì lỗi game ({loi}) — đã rút {mo_ta_manh(self.da_rut)}")
            self.bao_trang_thai("Dừng: lỗi game, xem log")
        except Exception:
            self.in_log(f"Lỗi không mong đợi\n{traceback.format_exc()}")
            self.bao_trang_thai("Lỗi, xem log")
        finally:
            try:
                self.chinh.lua.chay(MA_DONG_CUA_SO)
            except (LoiLua, OSError, AttributeError):
                pass

    def _tong_ngoc_tui(self):
        return sum(so for (_, _), (_, so, ten) in doc_tui(self.chinh.lua).items() if la_manh_ngoc(ten))

    def _cho_tong_tang(self, truoc):
        sau = self._tong_ngoc_tui()
        for _ in range(LAN_CHO_TUI):
            if sau > truoc:
                break
            self.dung.wait(GIAY_CHO_TUI)
            sau = self._tong_ngoc_tui()
        return sau

    def _rut_mot_lan(self, chi_so, so):
        kq = self.chinh.lua.chay(ma_rut_tccn(chi_so, so))
        if kq in (b"dong", b"khong"):
            raise LoiGiaoAccChinh(f"Thiên Cơ Cẩm Nang không rút được ({kq.decode()})")

    def _o_ngoc_tccn(self):
        """[(ô, tên, số)] các ô Mảnh Ngọc trong Thiên Cơ."""
        if not self._mo_tccn(self.chinh):
            raise LoiGiaoAccChinh("không mở được Thiên Cơ Cẩm Nang")
        bang = self._liet_ke_vat(self.chinh, MA_LIET_KE_TCCN)
        if bang in ("dong", "khong"):
            raise LoiGiaoAccChinh("không liệt kê được Thiên Cơ Cẩm Nang")
        return [(i, ten, so) for i, ten, so in bang if la_manh_ngoc(ten)]

    def _cat_ruong(self):
        """Túi hết chỗ: về Đại Lý, cất Mảnh Ngọc vào Thương khố (không có Mảnh Ngọc trong túi thì cất mọi ô)."""
        game, ten = self.chinh, self.ten
        self.bao_trang_thai("Túi đầy — cất đồ vào Thương khố")
        game.lua.chay(MA_DONG_CUA_SO)
        self._ve_dai_ly(game, ten)
        self._chay_toi(game, ten, NPC_TAN_THU[1])
        ngoc = [o for o, (_, _, ten_vat) in sorted(self._tui_chinh().items()) if la_manh_ngoc(ten_vat)]
        if ngoc:
            self.in_log(f"{ten}: túi hết chỗ, cất {len(ngoc)} ô Mảnh Ngọc vào Thương khố")
            kho_day = self._cat_kho(cac_o=ngoc)
        else:
            self.in_log(f"{ten}: túi hết chỗ mà không có ô Mảnh Ngọc, cất mọi ô vào Thương khố")
            kho_day = self._cat_kho(cat_het=True)
        if kho_day and max(self._o_trong().values()) == 0:
            raise LoiGiaoAccChinh("túi và Thương khố đều đầy")

    def _chay(self):
        ten = self.ten
        if self.can <= 0:
            raise LoiGiaoAccChinh("số ngọc phải lớn hơn 0")
        self.in_log(f"{ten}: rút {self.so_vien} viên ngọc = {self.can} mảnh từ Thiên Cơ Cẩm Nang")
        vua_cat = False
        while self.da_rut < self.can:
            self._kiem_tra_dung()
            self.bao_trang_thai(f"{ten}: đã rút {mo_ta_manh(self.da_rut)} / {self.so_vien} viên")
            if not vua_cat and max(self._o_trong().values()) == 0:
                self._cat_ruong()
                vua_cat = True
            khop = self._o_ngoc_tccn()
            if not khop:
                self.in_log(f"{ten}: Thiên Cơ Cẩm Nang hết Mảnh Ngọc")
                break
            chi_so, ten_vat, trong_o = khop[0]
            so = so_manh_lan_rut(self.can - self.da_rut, trong_o)
            truoc = self._tong_ngoc_tui()
            self._rut_mot_lan(chi_so, so)
            self.dung.wait(GIAY_GIUA_RUT_TCCN)
            self._kiem_tra_dung()
            sau = self._cho_tong_tang(truoc)
            if sau > truoc:
                self.da_rut += sau - truoc
                vua_cat = False
                self.in_log(f"{ten}: rút {sau - truoc} {ten_vat} (nhập {so}), tổng {mo_ta_manh(self.da_rut)}")
                continue
            if vua_cat:
                raise LoiGiaoAccChinh("đã cất Thương khố mà túi vẫn không nhận thêm Mảnh Ngọc")
            self.in_log(f"{ten}: rút {ten_vat} mà túi không tăng — túi hết chỗ, cất Thương khố")
            self._cat_ruong()
            vua_cat = True
        self.chinh.lua.chay(MA_DONG_CUA_SO)
        if self.da_rut >= self.can:
            self.in_log(f"{ten}: xong, đã rút {mo_ta_manh(self.da_rut)}")
            self.bao_trang_thai(f"Xong: {mo_ta_manh(self.da_rut)}")
        else:
            self.in_log(f"{ten}: xong (Thiên Cơ hết Mảnh Ngọc), đã rút {mo_ta_manh(self.da_rut)} / {self.so_vien} viên")
            self.bao_trang_thai(f"Xong (Thiên Cơ hết): {mo_ta_manh(self.da_rut)}")
