"""
GỘP ĐỒ VỀ ACC CHÍNH: lần lượt đăng nhập các acc nguồn (user nhập: tài khoản, mật khẩu, tên nhân vật),
giao đồ về một acc chính nhận — cùng quy tắc giao / cất túi như giao_acc_chinh.py, không dùng xoay vòng / sổ túi đồ.
"""
import re
import threading
import traceback
from datetime import date

import cau_hinh
from auto_chuyen_sinh import chuan_hoa
from giao_acc_chinh import GiaoAccChinhEngine, LoiGiaoAccChinh, MA_DONG_CUA_SO, _Dung
from so_tui_do import LOAI_TRU_MAC_DINH, cac_tu_loai_tru

KHOA_CAI_DAT = "gop_acc_chinh"
MAC_DINH = {"tai_khoan": "", "mat_khau": "", "nhan_vat": "", "loai_tru": LOAI_TRU_MAC_DINH,
            "danh_sach": "", "tien_trinh": {}}


def cai_dat():
    gia_tri = dict(MAC_DINH)
    gia_tri.update(cau_hinh.chung().get(KHOA_CAI_DAT) or {})
    return gia_tri


def luu_cai_dat(**thay_doi):
    cau_hinh.dat_chung({KHOA_CAI_DAT: dict(cai_dat(), **thay_doi)})


def parse_danh_sach(text):
    """
    Mỗi dòng: tài khoản, mật khẩu, tên nhân vật (phẩy hoặc tab).
    Dòng trống và dòng bắt đầu # bỏ qua. Trả về [(tk_dict, ten_nv), ...].
    """
    kq = []
    for so, dong in enumerate((text or "").splitlines(), 1):
        dong = dong.strip()
        if not dong or dong.startswith("#"):
            continue
        cot = [c.strip() for c in re.split(r"[,;\t]", dong) if c.strip()]
        if len(cot) < 3:
            raise ValueError(f"Dòng {so}: cần 3 trường (tài khoản, mật khẩu, tên nhân vật)")
        tk, mk, ten = cot[0], cot[1], cot[2]
        kq.append(({"ten_dang_nhap": tk, "mat_khau": mk}, ten))
    if not kq:
        raise ValueError("Danh sách acc nguồn trống (mỗi dòng: tài khoản, mật khẩu, tên nhân vật)")
    return kq


class LuongGopAccChinh(threading.Thread, GiaoAccChinhEngine):
    def __init__(self, hang_doi):
        super().__init__(daemon=True)
        self.hang_doi = hang_doi
        self.dung = threading.Event()
        self.cd = cai_dat()
        self.tk_chinh = {"ten_dang_nhap": self.cd["tai_khoan"], "mat_khau": self.cd["mat_khau"],
                         "nhan_vat": self.cd["nhan_vat"]}
        self.loai_tru = cac_tu_loai_tru(self.cd["loai_tru"])
        self.ds_nguon = parse_danh_sach(self.cd["danh_sach"])
        self.ghi_so_tui = False
        self.thoat_sau_giao = True
        self.tk_khong_co_do = set()
        self.chinh = None
        self.hwnd_truong = None
        self.pid_dieu_khien = set()
        self.cac_luong_con = []
        self.tien_trinh = {}
        self.luc_cat = 0.0
        self.tk_da_thoat = set()

    def cac_tai_khoan(self):
        if not self.is_alive():
            return set()
        tk_nhan = (self.tk_chinh["ten_dang_nhap"] or "").lower()
        tk_nguon = {tk["ten_dang_nhap"].lower() for tk, _ in self.ds_nguon}
        return {tk_nhan} | tk_nguon | self.tk_da_thoat

    def dang_dieu_khien(self, pid):
        if not self.is_alive():
            return False
        return pid in self.pid_dieu_khien or any(l.pid == pid and l.is_alive() for l in list(self.cac_luong_con))

    def in_log(self, chu):
        self.hang_doi.put(("log", f"[Gộp acc chính] {chu}"))

    def bao_trang_thai(self, chu):
        self.hang_doi.put(("trang_thai_gop_acc_chinh", chu))

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
        except ValueError as loi:
            self.in_log(f"Dừng: {loi}")
            self.bao_trang_thai(f"Dừng: {loi}")
        except Exception:
            self.in_log(f"Lỗi không mong đợi\n{traceback.format_exc()}")
            self.bao_trang_thai("Lỗi, xem log")
        finally:
            for luong in self.cac_luong_con:
                luong.dung.set()
            if self.chinh:
                from lua_game import LoiLua
                try:
                    self.chinh.lua.chay(MA_DONG_CUA_SO)
                except (LoiLua, OSError):
                    pass
            self.pid_dieu_khien.clear()

    def _chay(self):
        hom_nay_chu = date.today().isoformat()
        self.tien_trinh = dict(self.cd.get("tien_trinh") or {})
        if self.tien_trinh.get("ngay") != hom_nay_chu:
            self.tien_trinh = {"ngay": hom_nay_chu, "da_xong": [], "ma_da_nhan": []}
        da_xong_ds = {chuan_hoa(t) for t in self.tien_trinh["da_xong"]}
        con = [(tk, ten) for tk, ten in self.ds_nguon if chuan_hoa(ten) not in da_xong_ds]
        self.in_log(f"Bắt đầu: acc nhận {self.tk_chinh['nhan_vat']}, {len(self.ds_nguon)} acc nguồn, "
                    f"đã xong {len(self.ds_nguon) - len(con)}, còn {len(con)}: "
                    + ", ".join(ten for _, ten in con))
        if not con:
            self.bao_trang_thai("Xong (không còn acc nguồn)")
            return
        self._chay_giao_don(con, "acc nguồn đã nhập")
