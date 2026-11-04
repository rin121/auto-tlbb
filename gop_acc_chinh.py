"""
GỘP ĐỒ VỀ ACC CHÍNH: lần lượt đăng nhập các acc nguồn (user nhập: tài khoản, mật khẩu, tên nhân vật),
giao đồ về một acc chính nhận. Acc nguồn về Đại Lý, rút Mảnh Ngọc Vip, Phiếu KNB 100/300/2000/3000,
Thiên Mệnh Thần Thạch, Mảnh Vỡ Trân Thú, Mảnh vỡ Thiên Ngoại từ Thiên Cơ Cẩm Nang (mỗi lần nhập 250, cách 3 giây)
và Thương khố, rồi giao các món đó. Không dùng xoay vòng / sổ túi đồ.
"""
import re
import threading
import unicodedata
import traceback
from datetime import date

import cau_hinh
from auto_chuyen_sinh import chuan_hoa
from giao_acc_chinh import GiaoAccChinhEngine, LoiGiaoAccChinh, MA_DONG_CUA_SO, _Dung
from lua_game import LoiLua
from so_tui_do import LOAI_TRU_MAC_DINH, cac_tu_loai_tru

KHOA_CAI_DAT = "gop_acc_chinh"
MAC_DINH = {"tai_khoan": "", "mat_khau": "", "nhan_vat": "", "loai_tru": LOAI_TRU_MAC_DINH,
            "danh_sach": "", "tien_trinh": {}}
# Luồng gộp đang chạy — xoay vòng giữ hwnd, không logout chéo.
_luong_gop_hien_tai = None


def cai_dat():
    gia_tri = dict(MAC_DINH)
    gia_tri.update(cau_hinh.chung().get(KHOA_CAI_DAT) or {})
    return gia_tri


def luu_cai_dat(**thay_doi):
    cau_hinh.dat_chung({KHOA_CAI_DAT: dict(cai_dat(), **thay_doi)})


def luong_gop_dang_chay():
    luong = _luong_gop_hien_tai
    return luong if luong is not None and luong.is_alive() else None


def cac_tai_khoan_gop_cau_hinh():
    """Tên đăng nhập (chữ thường) acc nhận + mọi acc nguồn trong cấu hình gộp."""
    cd = cai_dat()
    kq = set()
    tk_nhan = (cd.get("tai_khoan") or "").strip().lower()
    if tk_nhan:
        kq.add(tk_nhan)
    try:
        for tk, _ in parse_danh_sach(cd.get("danh_sach") or ""):
            ten = (tk.get("ten_dang_nhap") or "").strip().lower()
            if ten:
                kq.add(ten)
    except ValueError:
        pass
    return kq


def hwnd_giu_khi_gop():
    """
    Cửa sổ gộp đồ (acc nhận / nguồn) — xoay vòng không được tắt hoặc đăng xuất.
    Gồm tài khoản trong cấu hình đang mở + hwnd luồng gộp đang điều khiển (kể cả lúc đăng nhập).
    """
    from cua_so_game import tim_cua_so_game
    from xoay_vong import tim_hwnd_cua_tai_khoan
    giu = set()
    for tk in cac_tai_khoan_gop_cau_hinh():
        hwnd = tim_hwnd_cua_tai_khoan(tk)
        if hwnd:
            giu.add(hwnd)
    luong = luong_gop_dang_chay()
    if luong is None:
        return giu
    chinh = getattr(luong, "chinh", None)
    if chinh is not None:
        try:
            giu.add(chinh.lua.hwnd)
        except (AttributeError, OSError):
            pass
    hwnd_truong = getattr(luong, "hwnd_truong", None)
    if hwnd_truong:
        giu.add(hwnd_truong)
    pids = set(getattr(luong, "pid_dieu_khien", None) or ())
    for con in list(getattr(luong, "cac_luong_con", None) or []):
        if getattr(con, "pid", None):
            pids.add(con.pid)
    if pids:
        for cua_so in tim_cua_so_game():
            if cua_so["pid"] in pids:
                giu.add(cua_so["hwnd"])
    return giu


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
        tk, mk, ten = cot[0], cot[1], unicodedata.normalize("NFC", cot[2])
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
        # Một acc nguồn thì giữ trong game. Nhiều acc thì giao xong đăng xuất để vào acc kế.
        self.thoat_sau_giao = len(self.ds_nguon) > 1
        self.rut_truoc_giao = True
        self.chi_giao_gop = True
        self.kiem_tra_rule_ten = False
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
        global _luong_gop_hien_tai
        _luong_gop_hien_tai = self
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
            if _luong_gop_hien_tai is self:
                _luong_gop_hien_tai = None

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
