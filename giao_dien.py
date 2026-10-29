"""
GIAO DIỆN AUTO CHUYỂN SINH.

Cách chạy: bấm đúp chay_auto.bat, hoặc
    .venv\\Scripts\\python giao_dien.py

- Danh sách trên cùng là mọi cửa sổ game đang mở. Bấm vào ô ☐ ở cột "Auto" để bật/tắt auto cho riêng nhân vật đó.
- Chọn một nhân vật để xem thông tin và chỉnh cài đặt riêng (nhớ bấm Lưu).
- Tab "Chuyển sinh": level chuyển sinh (dùng ô 1,1), tùy chọn dịch chuyển tới map trước khi chuyển sinh,
  các mốc level -> map -> hàng vật phẩm trong túi, tự cộng điểm tiềm năng / dùng Hộp Point (auto_cong_diem.py).
  Tab "Config": danh sách map dùng chung.
- Tab "Cài đặt": vào game thì tắt âm thanh, giảm đồ họa xuống thấp nhất (cai_dat_game.py).
- Mỗi cửa sổ game có một luồng riêng đọc game và dùng vật phẩm, nên nhân vật này đang chờ
  dịch chuyển không làm chậm nhân vật khác. Giao diện chỉ nhận tin qua hàng đợi, không gọi game trực tiếp.
- Tab "Tài khoản": hai bảng — phó bản (xoay vòng) và train (chỉ train). Mỗi tài khoản là một cửa sổ game.
  Tài khoản không có cửa sổ (bị diss) thì auto tự mở game đăng nhập lại nếu được bật (dang_nhap.py).
  Nhiều tài khoản thì mở game theo từng đợt (vd. 2 game mỗi 2 giây), mở dồn một lúc thì client bị chặn.
  Mất kết nối thì game không tự tắt mà hiện hộp hỏi: auto bấm Duyệt / Đóng cho game tắt (mat_ket_noi.py).
- Tab "Tạo nhân vật": bấm Tạo nhân vật trong game thì auto tự nhập mã kiểm tra (tao_nhan_vat.py).
- Tab "Tiện ích": vứt rác (vut_rac.py), auto duyệt popup hỏi xác nhận (tu_duyet.py),
  tự mua và dùng Thiên Linh Đan / Càn Khôn Hồ khi hết hiệu ứng (tu_dung_vat_pham.py), auto chat Thế giới
  (chat_the_gioi.py).
- Tab "Chiến đấu": tự đánh quái, cài riêng cho nhân vật đang chọn (chien_dau.py).
- Tab "Auto click": bấm liên tục các ô F1-F10 đã tích, cài riêng cho nhân vật đang chọn (auto_click.py).
- Tab "Phó bản": tự về Đại Lý và đi Phiêu Miễu Phong một mình hoặc tổ đội (đội trưởng dẫn các đội viên trong auto),
  cài riêng từng nhân vật (pho_ban_pmp.py).
- Kéo tên tab sang trái / phải, kéo dòng nhân vật lên / xuống để sắp xếp lại; thứ tự được nhớ cho lần mở sau.
- Bản dùng thử (dong_goi\\build_dung_thu.ps1) hết hạn thì không mở được và đang chạy cũng tự tắt (han_dung.py).
"""
import ctypes
import ctypes.wintypes
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import tkinter as tk
import traceback
from datetime import date
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter import font as tkfont

import psutil
import pywintypes
import win32gui

import cau_hinh
import auto_click
import cai_dat_game
import han_dung
import kich_hoat
from auto_cong_diem import CAC_CHI_SO, TuCongDiem
from auto_chuyen_sinh import cac_o_cua_viec, chuan_hoa, mo_ta_o, tim_cac_o, xu_ly_nhan_vat
from chat_the_gioi import GIAY_TOI_THIEU as GIAY_CHAT_TOI_THIEU, LoiChat, gui_the_gioi, ma_lua_chat
from chien_dau import (CAC_PHIM_SKILL, KY_NANG_VE_THANH, MAU_HET_AN_THAN, MON_PHAI_NGA_MY, PHIM_BUFF_DU_PHONG,
                       TEN_KY_NANG_AN_DON, TEN_KY_NANG_BUFF_MAU, ChienDau, LoiChienDau, cai_dat_chien_dau,
                       ma_dung_ky_nang_theo_dinh_nghia)
from cua_so_game import (an_cua_so, bat_dpi_awareness, cac_cua_so_da_an, hien_cua_so, hien_lai_cua_so_an_lan_truoc,
                         tim_cua_so_game)
from dang_nhap import LoiDangNhap, LuongDangNhap, chuoi_lua, client_dang_dang_nhap
import proxy_mang
import proxy_broker_ui
from game_api import Game
from giao_acc_chinh import LuongGiaoAccChinh, cai_dat as cai_dat_giao_acc_chinh, luu_cai_dat as luu_giao_acc_chinh
from giai_captcha import LoiGiaiCaptcha, kiem_tra_ocr_win7, lam_nong_ocr
from lua_game import THONG_BAO_LOI, LoiLua, da_nap_dll
from mat_ket_noi import XuLyMatKetNoi
from pho_ban_pmp import (MA_DANG_THEO_DOI, MAP_DAI_LY, MAP_LAC_DUONG, MAP_PMP, MO_TA as MO_TA_PHO_BAN, DoiPMP,
                         PhoBanPMP, cap_nhat_di_lac_duong_doi_vien, cap_nhat_doi_vien_cho_sat_tinh,
                         cap_nhat_doi_vien_toi_truong, cap_nhat_doi_vien_tu_lac_duong, cap_nhat_hoi_mau_dai_ly,
                         cap_nhat_trieu_tap_doi_vien,
                         cac_doan_hom_nay, chuan_bi_ve_thanh,
                         can_ve_khi_het_luot, cai_dat_pmp, con_sat_tinh, nen_ve_thanh_theo_doi,
                         dat_phien_xoay_vong,
                         hom_nay, la_dai_ly, pmp_dang_duoc_phep_chay, xoa_co_xoay_vong_luu_tat_ca,
                         la_lac_duong, la_map_pho_ban, la_map_trong_pho_ban, GIAY_RETRY_VE_THANH_THEO_DOI)
from chien_dau import khoang_cach
from su_kien_ac_tac import (HUB_CUA_MAP as HUB_CUA_MAP_AC_TAC, MO_TA as MO_TA_AC_TAC, AcTacRunner, DoiAcTac, buoc_doi_vien,
                            cac_map_da_chon, cai_dat_ac_tac, cung_ten_map, khung_hien_tai, mo_ta_lich, ten_map_chuan,
                            ve_thanh_neu_o_map_ac_tac)
import gauto_ac_tac
from giao_dich import anh_tui_goc
from giao_dich_ngay import LuongGiaoDichNgay
from moi_nhom import SO_NGUOI_TOI_DA, doc_nhom, doc_xung_quanh, xu_ly_nhom
from nhat_do import NhatDo
from nang_cap_nhan_vat import LuongNangCapOnline
from nhan_vat_moi import LuongTaoNhanVat, doc_danh_sach
from xoay_vong import (SO_NGUOI_MOT_NHOM_TOI_DA, SO_ROUND_TOI_DA, LuongXoayVong, cac_tai_khoan_dang_tich,
                       nhom_dang_online, xoa_xv_tien_trinh)
from tao_nhan_vat import dang_hoi_ma_kiem_tra, giai_ma_kiem_tra
from tu_dung_vat_pham import TuDungCanKhonHo, TuDungX2
from tang_cap import GIAY_GIUA_MOI_LAN as GIAY_GIUA_MOI_LAN_TANG_CAP, thu_tang_cap
from tu_duyet import LoiTuDuyet, TuDuyet
from tran_thu import TuXuatChien
from vut_rac import LoiVutRac, vut_rac
from thu_muc import THU_MUC_APP

O_BAT, O_TAT = "☑", "☐"
SO_DONG_LOG_TOI_DA = 500
NHAT_KY_CANH_EXE = os.path.join(THU_MUC_APP, "nhat_ky_auto.log")


def _chon_duong_dan_nhat_ky():
    """
    Ghi log cạnh AutoHoc.exe; nếu không được (máy ảo, ổ map Desktop từ host chỉ đọc) thì dùng
    %LOCALAPPDATA%\\AutoHoc\\nhat_ky_auto.log — luôn ghi được trong VM Windows.
    """
    for duong_dan in (NHAT_KY_CANH_EXE,):
        try:
            with open(duong_dan, "a", encoding="utf-8"):
                pass
            return duong_dan
        except OSError:
            pass
    local = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    duong_dan = os.path.join(local, "AutoHoc", "nhat_ky_auto.log")
    try:
        os.makedirs(os.path.dirname(duong_dan), exist_ok=True)
        with open(duong_dan, "a", encoding="utf-8"):
            pass
        return duong_dan
    except OSError:
        return NHAT_KY_CANH_EXE


DUONG_DAN_NHAT_KY = _chon_duong_dan_nhat_ky()
_MAU_NGAY_NHAT_KY = re.compile(r"^\[(\d{4}-\d{2}-\d{2})")


def _ngay_cuoi_trong_nhat_ky(duong_dan_log):
    """Ngày của dòng log cuối (nếu đọc được), dùng khi chưa có file .ngay."""
    try:
        with open(duong_dan_log, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size <= 0:
                return None
            f.seek(max(0, size - 16384))
            chunk = f.read().decode("utf-8", errors="ignore")
    except OSError:
        return None
    for dong in reversed(chunk.splitlines()):
        khop = _MAU_NGAY_NHAT_KY.match(dong.strip())
        if khop:
            return khop.group(1)
    return None


def _doc_ngay_nhat_ky_lan_truoc(duong_dan_log):
    marker = duong_dan_log + ".ngay"
    try:
        if os.path.isfile(marker):
            with open(marker, encoding="utf-8") as f:
                ngay = f.read().strip()
                if ngay:
                    return ngay
    except OSError:
        pass
    return _ngay_cuoi_trong_nhat_ky(duong_dan_log)


def _luu_ngay_nhat_ky(duong_dan_log, hom_nay):
    try:
        with open(duong_dan_log + ".ngay", "w", encoding="utf-8") as f:
            f.write(hom_nay)
    except OSError:
        pass


def don_nhat_ky_sang_ngay_moi(duong_dan_log):
    """
    Sang ngày mới (sau 00:00) thì xóa nhat_ky_auto.log: khi mở AutoHoc hoặc khi đang chạy qua 00:00.
    Trả về True nếu đã xóa file log.
    """
    hom_nay = time.strftime("%Y-%m-%d")
    ngay_cu = _doc_ngay_nhat_ky_lan_truoc(duong_dan_log)
    if ngay_cu is not None and ngay_cu >= hom_nay:
        return False
    da_xoa = False
    if ngay_cu is not None and ngay_cu < hom_nay:
        try:
            if os.path.isfile(duong_dan_log):
                os.remove(duong_dan_log)
                da_xoa = True
        except OSError:
            pass
    _luu_ngay_nhat_ky(duong_dan_log, hom_nay)
    return da_xoa
# Tiêu đề ChickenAuto đặt khi đã nhận nhân vật, vd. "MỹNhânNgư (130) [Nga My] - ChickenAuto (ver.116)".
MAU_TIEU_DE_DA_VAO_GAME = re.compile(r"^(.*) \(\d+\) \[.*\] - ChickenAuto")
CAI_DAT_CHUNG = (
    ("giay_giua_moi_lan_kiem_tra", "Giây giữa mỗi lần kiểm tra"),
    ("giay_cho_toi_da", "Giây chờ tối đa sau khi dùng vật phẩm"),
    ("giay_nghi_sau_khi_toi_map", "Giây nghỉ sau khi tới map"),
    ("so_lan_thu_toi_da", "Thất bại bao nhiêu lần thì tạm dừng"),
    ("giay_cho_game_khoi_dong", "Giây chờ game mới mở khởi động xong"),
)
CAI_DAT_DANG_NHAP = (
    ("thu_muc_game", "Thư mục game", 44),
    ("may_chu", "Máy chủ", 18),
    ("ma_kiem_tra", "Mã kiểm tra", 8),
    ("giay_cho_truoc_khi_nap_dll", "Giây chờ game tải xong", 6),
    ("giay_toi_da_moi_buoc", "Giây tối đa mỗi bước", 6),
    ("so_lan_thu_toi_da", "Số lần thử", 6),
    ("so_game_mo_cung_luc", "Số game đăng nhập cùng lúc", 6),
    ("so_game_moi_dot", "Số game mỗi đợt", 6),
    ("giay_giua_moi_dot", "Giây giữa mỗi đợt", 6),
)
CAC_O_SO_DANG_NHAP = ("giay_cho_truoc_khi_nap_dll", "giay_toi_da_moi_buoc", "so_lan_thu_toi_da",
                      "so_game_mo_cung_luc", "so_game_moi_dot", "giay_giua_moi_dot")
GIAY_CHO_SAU_KHI_VAO_GAME = 60
GIAY_GIUA_MOI_LAN_XEM_POPUP = 0.3
MOI_NHAN_VAT_CHAT = "Mọi nhân vật đang bật Auto"
GIAY_GIUA_MOI_LAN_XEM_MAT_KET_NOI = 1.0
GIAY_GIUA_MOI_LUOT_DANH = 0.4
# Auto chuyển sinh đang dùng vật phẩm (Thổ Linh Châu phải vận công) hoặc nhân vật chết thì ngừng tự đánh.
MO_TA_TAM_DUNG_DANH = ("Dịch chuyển", "Đang chuyển sinh", "HP = 0", "Đã chết")
CAC_KHOA_CHIEN_DAU_CHUNG = ("ban_kinh", "dung_f1", "lua_quai", "so_quai_lua", "danh_theo_key", "ten_key",
                            "dung_skill_pet", "cac_phim_skill", "uu_tien_nguoi_choi", "xuong_thu", "nhat_do",
                            "an_don", "phan_tram_an_don", "xuat_chien_tran_thu", "hoan_hi_toi_thieu")
CAC_O_TICH_CHIEN_DAU = ("bat", "quanh_diem", "dung_f1", "lua_quai", "danh_theo_key", "dung_skill_pet",
                        "uu_tien_nguoi_choi", "xuong_thu", "nhat_do", "buff_mau", "an_don", "xuat_chien_tran_thu",
                        "tu_tang_cap")
# Thành viên hỏi mục tiêu của Key thì Key đọc mục tiêu của mình trong GIAY_KEY_DOC_MUC_TIEU giây tới;
# tin mục tiêu cũ hơn GIAY_TIN_KEY_CON_DUNG thì coi như không biết Key đang đánh gì.
GIAY_KEY_DOC_MUC_TIEU = 3
GIAY_TIN_KEY_CON_DUNG = 2
GIAY_DOC_LAI_NHOM_KHI_PK = 5
TIEU_DE = "AutoHoc - Chuyển sinh"
# Kích thước cửa sổ khi mở (đơn vị 96 DPI; nhân he_so trong px()).
RONG_CUA_SO_MAC_DINH = 680
CAO_CUA_SO_MAC_DINH = 520
RONG_CUA_SO_TOI_THIEU = 600
CAO_CUA_SO_TOI_THIEU = 400
DOAN_WRAP_GHI_CHU = 400
# "Cài đặt chung" luôn ẩn (mở bằng cách khác); "Cài đặt" chứa ô ẩn / hiện tab nên không cho ẩn.
TAB_LUON_HIEN = ("Cài đặt", "Cài đặt chung")
GIAY_VE_LAI_KHI_CO_TIN = 0.5
GIAY_VE_LAI_TOI_DA = 1.0
MILI_GIAY_GOP_CAP_NHAT_TAB = 30
MILI_GIAY_GIUA_MOI_LAN_XEM_HAN_DUNG = 10_000
SO_HANG_TUI_TOI_DA = 12
CAC_HANG_TUI = [str(hang) for hang in range(1, SO_HANG_TUI_TOI_DA + 1)]
CAI_DAT_GAME = (("tat_am_thanh", "Vào game thì tắt âm thanh", "đã tắt âm thanh"),
                ("giam_do_hoa", "Vào game thì giảm đồ họa xuống thấp nhất (số mô hình, hiệu ứng, profile)",
                 "đã giảm đồ họa xuống thấp nhất (số mô hình, hiệu ứng, profile)"))


def ten_trong_tieu_de(hwnd):
    khop = MAU_TIEU_DE_DA_VAO_GAME.search(win32gui.GetWindowText(hwnd))
    return khop.group(1) if khop else None


def doc_hang(chu, noi):
    """Hàng trong túi đồ đã chọn ở noi. Chưa chọn / sai thì báo ValueError."""
    if not str(chu).strip():
        raise ValueError(f"Chưa chọn hàng vật phẩm ở {noi}")
    hang = so_nguyen(chu, f"Hàng vật phẩm ở {noi}")
    if not 1 <= hang <= SO_HANG_TUI_TOI_DA:
        raise ValueError(f"Hàng vật phẩm ở {noi} phải từ 1 tới {SO_HANG_TUI_TOI_DA}")
    return hang


def giu_co_map_pk(cac_moc, cac_moc_cu):
    """Chép các mốc nhưng giữ "dang_dung_map_pk" riêng của từng nhân vật (theo level mốc)."""
    da_dung = {moc["level"] for moc in cac_moc_cu if moc.get("dang_dung_map_pk")}
    return [dict(moc, dang_dung_map_pk=moc["level"] in da_dung) if "map_khi_bi_pk" in moc else dict(moc)
            for moc in cac_moc]


def dat_o_bang(bang, iid, cot, gia_tri):
    """Ghi ô Treeview chỉ khi chữ đổi: ghi lại y nguyên vẫn bắt Tk vẽ lại bảng (vòng vẽ lại chạy mỗi giây, mỗi dòng)."""
    if str(bang.set(iid, cot)) != str(gia_tri):
        bang.set(iid, cot, gia_tri)


def dat_dong_bang(bang, iid, gia_tri):
    """Như dat_o_bang cho cả dòng."""
    if tuple(map(str, bang.item(iid, "values"))) != tuple(map(str, gia_tri)):
        bang.item(iid, values=gia_tri)


def so_nguyen(chu, ten_o):
    try:
        return int(str(chu).strip())
    except ValueError:
        raise ValueError(f"{ten_o} phải là số nguyên") from None


class LuongNhanVat(threading.Thread):
    """Luồng riêng của một cửa sổ game: đọc thông tin gửi lên giao diện, và chạy auto nếu nhân vật được bật."""

    def __init__(self, hwnd, hang_doi, lay_nhom, dang_tu_dang_nhap, dang_giao_acc_chinh, lay_cac_luong):
        super().__init__(daemon=True)
        self.hwnd = hwnd
        self.hang_doi = hang_doi
        self.lay_nhom = lay_nhom
        self.dang_tu_dang_nhap = dang_tu_dang_nhap
        self.dang_giao_acc_chinh = dang_giao_acc_chinh
        self.lay_cac_luong = lay_cac_luong
        self.game = Game(hwnd)
        # (khóa bật/tắt trong cài đặt chung, việc tự mua và dùng)
        self.tu_mua_dung = [("tu_dung_x2", TuDungX2(self.game.lua, self.in_log)),
                            ("tu_dung_can_khon_ho", TuDungCanKhonHo(self.game.lua, self.in_log))]
        self.tu_cong_diem = TuCongDiem(self.game, self.in_log)
        self.pho_ban = PhoBanPMP(self.game, self.in_log)
        # (x, y, bán kính) chỗ phó bản đang cần đánh, None nếu không đánh (luồng chiến đấu đọc)
        self.vung_pho_ban = None
        self.doi_pmp = None      # DoiPMP khi nhân vật này đang dẫn đội đi PMP
        self.truong_pmp = None   # DoiPMP của đội trưởng mà nhân vật này đang theo
        self.ac_tac = AcTacRunner(self.game, self.in_log)
        self.dang_ac_tac = False     # đang trong khung Ác Tặc (dẫn đội / một mình / theo đội trưởng)
        self.doi_ac_tac = None       # DoiAcTac khi nhân vật này đang đi Ác Tặc (đội trưởng hoặc một mình)
        self.truong_ac_tac = None    # DoiAcTac của đội trưởng mà nhân vật này đang theo
        self.ac_tac_state = {}
        self.luc_ve_thanh_theo_doi = 0.0
        self.luc_chay_gan_sat_tinh = 0.0
        self.luc_log_gan_sat_tinh = 0.0
        self.pmp_gom_state = {}
        self.pmp_di_ld_state = {}
        self.pmp_ld_chay_npc_state = {}
        self.pmp_trieu_tap_state = {}
        self.hoi_mau_dai_ly_state = {}
        self.trieu_tap_den = None  # (x, y, map, het_han) khi đội trưởng triệu tập
        self.da_bao_cho_truong = None
        self.luc_bao_truong_danh = 0.0
        self.dang_theo_doi = False
        self.trang_thai = {}
        self.trang_thai_nhom = {}
        self.yeu_cau_rac = None
        self.luc_vut_rac = 0.0
        self.luc_chat_the_gioi = 0.0
        self.loi_rac_cuoi = None
        self.loi_ma_cuoi = None
        self.ten = None
        self.tai_khoan = None
        # Túi lúc auto thấy nhân vật vào game (nút Giao dịch ngay so với ảnh này để biết đồ mới nhặt).
        self.anh_tui = None
        self.anh_tui_cua = None
        self.luc_tao = time.time()
        self.da_noi = False
        self.dang_trong_game = False
        self.map_hien_tai = None
        self.mo_ta_chien_dau = ""
        self.mo_ta_auto_click = ""
        self.duoc_theo_den = 0.0
        self.muc_tieu_key = None  # (id server quái đang chọn hoặc None, map, lúc đọc) khi nhân vật này là Key
        # (id server người chơi phe địch đang chọn hoặc None, map, lúc đọc) khi nhân vật này là trưởng nhóm lúc PK
        self.muc_tieu_nguoi = None
        self.duoc_hoi_nguoi_den = 0.0
        self.ke_danh = None  # (id server người chơi đang đánh mình, map, lúc đọc)
        self.thanh_vien_nhom = []
        self.luc_doc_nhom = 0.0
        self.mon_phai = None
        self.da_cai_dat_game = set()
        self.dung = threading.Event()

    def in_log(self, chu):
        self.hang_doi.put(("log", chu))

    def cai_dat_game(self, chung):
        """Vào game thì tắt âm thanh / giảm đồ họa (tab Cài đặt), mỗi mục một lần cho mỗi lần vào game."""
        for khoa, _, da_lam in CAI_DAT_GAME:
            if not chung[khoa]:
                self.da_cai_dat_game.discard(khoa)
                continue
            if khoa in self.da_cai_dat_game:
                continue
            try:
                so_muc = cai_dat_game.ap_dung(self.game.lua, khoa == "tat_am_thanh", khoa == "giam_do_hoa")
            except LoiLua:
                return
            self.da_cai_dat_game.add(khoa)
            if so_muc:
                self.in_log(f"{self.ten}: {da_lam} ({so_muc} mục)")

    def nen_dung(self):
        return self.dung.is_set() or not cau_hinh.cua_nhan_vat(self.ten)["bat_auto"]

    def nen_dung_chuyen_sinh(self):
        cai_dat = cau_hinh.cua_nhan_vat(self.ten)
        return self.nen_dung() or not cai_dat["bat_chuyen_sinh"] \
            or (not self.dang_giao_acc_chinh() and (self.ac_tac_dang_chen(cai_dat) or self.dang_theo_ac_tac(cai_dat)))

    def nen_dung_pho_ban(self):
        # Đang tự đi mà đội trưởng bắt đầu dẫn mình thì dừng để theo đội trưởng; tới giờ Ác Tặc thì bỏ dở phó bản.
        cai_dat = cau_hinh.cua_nhan_vat(self.ten)
        return self.nen_dung() or self.dang_giao_acc_chinh() \
            or not pmp_dang_duoc_phep_chay(cai_dat) \
            or self.ac_tac_dang_chen(cai_dat) or self.dang_theo_ac_tac(cai_dat) \
            or (self.doi_pmp is None and self.doi_theo_truong() is not None)

    def nen_dung_ac_tac(self):
        return self.nen_dung() or self.dang_giao_acc_chinh() or not cai_dat_ac_tac()["bat"]

    def la_doi_truong_nhom_game(self):
        """Người đầu danh sách nhóm trong game (đội trưởng); không nhóm / một mình coi như trưởng."""
        try:
            thanh_vien = doc_nhom(self.game.lua)["thanh_vien"]
        except LoiLua:
            return True
        if not thanh_vien:
            return True
        return chuan_hoa(thanh_vien[0]) == chuan_hoa(self.ten)

    def dang_theo_ac_tac(self, cai_dat):
        """Đội viên: đội trưởng trong auto đang đi Ác Tặc (cài chung mac_dinh)."""
        if not cai_dat["bat_auto"] or not cai_dat_ac_tac()["bat"]:
            return False
        at = cai_dat_ac_tac()
        if khung_hien_tai(at) is None:
            return False
        truong, _ = self.truong_ac_tac_trong_auto()
        return truong is not None

    def ac_tac_dang_chen(self, cai_dat):
        """Bật Ác Tặc, đang trong khung giờ và chưa đi xong khung này: Ác Tặc được ưu tiên hơn PMP / Sát Tinh."""
        at = cai_dat_ac_tac()
        return bool(cai_dat["bat_auto"]) and at["bat"] and self.la_doi_truong_nhom_game() \
            and self.ac_tac.can_chen(at)

    def dat_vung_pho_ban(self, vung):
        self.vung_pho_ban = vung

    def vung_danh_pho_ban(self):
        """Vùng phó bản cần đánh: của chính mình, hoặc của đội trưởng đang theo (khi đã ở trong phó bản)."""
        if self.vung_pho_ban:
            return self.vung_pho_ban
        if self.dang_ac_tac:
            doi_at = self.truong_ac_tac
            return doi_at.vung_cho(self.map_hien_tai) if doi_at is not None else None
        doi = self.truong_pmp
        if doi and la_map_trong_pho_ban(self.map_hien_tai):
            return doi.vung
        return None

    def doi_dang_dan(self):
        """DoiPMP mà nhân vật này đang làm đội trưởng: của chính luồng, hoặc đội viên nào đang theo mình."""
        if self.doi_pmp is not None:
            return self.doi_pmp
        if not self.ten:
            return None
        khoa = chuan_hoa(self.ten)
        for luong in self.lay_cac_luong():
            for doi in (luong.doi_pmp, luong.truong_pmp):
                if doi is not None and chuan_hoa(doi.truong) == khoa:
                    return doi
        return None

    def tam_dung_vi_pho_ban(self):
        """Chưa tới lúc đánh ải (đang chạy / nói chuyện NPC): không tự đánh, tránh chọn nhầm NPC chưa hóa quái."""
        if self.dang_ac_tac:
            # Ác Tặc: chỉ đánh khi đội trưởng (hoặc chính mình) đã ghi vùng quanh Ác Tặc, không đánh quái thường.
            return self.vung_danh_pho_ban() is None
        dan = self.doi_dang_dan()
        if dan is not None and dan.truong_dang_khong_danh():
            return True
        doi = self.doi_pmp or self.truong_pmp
        if doi is not None:
            return doi.giai_doan != "danh"
        return (self.trang_thai.get("mo_ta") or "").startswith(MO_TA_PHO_BAN) and self.vung_danh_pho_ban() is None

    def truong_pmp_phai_dung(self, cai_dat_nv):
        """
        Lưới an toàn cho "đội trưởng luôn cưỡi thú": là trưởng nhóm PMP, đang ở trong phó bản, đã bật tùy chọn và có
        đội viên trong auto cùng map thì không tự đánh dù không tìm thấy DoiPMP.
        """
        if self.da_bao_cho_truong != self.ten or chuan_hoa(self.map_hien_tai or "") != chuan_hoa(MAP_PMP) \
                or not cai_dat_pmp(cai_dat_nv)["truong_khong_danh"]:
            return False
        dan = self.doi_dang_dan()
        if dan is not None and dan.truong_vao_danh:
            return False
        khoa = chuan_hoa(self.ten)
        co_doi_vien = any(luong is not self and luong.ten and luong.map_hien_tai == self.map_hien_tai
                          and luong.da_bao_cho_truong and chuan_hoa(luong.da_bao_cho_truong) == khoa
                          for luong in self.lay_cac_luong())
        if co_doi_vien and time.time() - self.luc_bao_truong_danh >= 60:
            self.luc_bao_truong_danh = time.time()
            dan = self.doi_dang_dan()
            self.in_log(f"{self.ten}: đội trưởng PMP không tự đánh (doi_pmp={'có' if self.doi_pmp else 'không'}, "
                        f"cờ={'bật' if dan and dan.truong_khong_danh else 'tắt'}, "
                        f"đội viên={len(dan.cac_doi_vien) if dan else 0})")
        return co_doi_vien

    def tim_doi_pmp(self):
        """DoiPMP của đội trưởng (nhân vật khác trong auto) đang dẫn mình đi PMP, None nếu không có."""
        doi = self.doi_theo_truong()
        if doi is None:
            return None
        truong = self.tim_luong(doi.truong)
        if truong is not None and truong.doi_pmp is doi:
            return doi
        return None

    def doi_theo_truong(self):
        """
        Đội viên trong nhóm game: luôn trả DoiPMP của đội trưởng (cùng object khi trưởng đã chạy PMP)
        để tự về thành / Di Chuyển / chạy tới trưởng — không chờ đến khi được ghi trong cac_doi_vien.
        """
        try:
            thanh_vien = doc_nhom(self.game.lua)["thanh_vien"]
        except LoiLua:
            return None
        if not thanh_vien or chuan_hoa(thanh_vien[0]) == chuan_hoa(self.ten):
            return None
        if not cai_dat_pmp(cau_hinh.cua_nhan_vat(self.ten))["bat"]:
            return None
        ten_truong = thanh_vien[0]
        truong = self.tim_luong(ten_truong)
        if truong is None:
            return None
        if not cai_dat_pmp(cau_hinh.cua_nhan_vat(truong.ten))["bat"]:
            return None
        if truong.doi_pmp and chuan_hoa(truong.doi_pmp.truong) == chuan_hoa(ten_truong):
            return truong.doi_pmp
        return DoiPMP(ten_truong, {}, None)

    def lap_doi_pmp(self, cai_dat):
        """
        None: đi PMP một mình (không có nhóm trong game); False: là đội viên, chờ đội trưởng dẫn (đội viên không nói
        chuyện được với NPC vào phó bản); DoiPMP: là đội trưởng, dẫn các đội viên trong auto đã bật Auto + Phó bản.
        """
        try:
            thanh_vien = doc_nhom(self.game.lua)["thanh_vien"]
        except LoiLua:
            return False
        if not thanh_vien:
            return None
        if chuan_hoa(thanh_vien[0]) != chuan_hoa(self.ten):
            if self.da_bao_cho_truong != thanh_vien[0]:
                self.da_bao_cho_truong = thanh_vien[0]
                self.in_log(f"{self.ten}: PMP tổ đội — tự về thành và theo đội trưởng {thanh_vien[0]} "
                            f"(không train khi đang đi phó bản)")
            return False
        if self.da_bao_cho_truong != self.ten:
            self.in_log(f"{self.ten}: PMP đi tổ đội, là đội trưởng")
        self.da_bao_cho_truong = self.ten
        return DoiPMP(self.ten, self.chon_doi_vien_pmp(thanh_vien), self.doc_doi_vien_pmp)

    def chon_doi_vien_pmp(self, thanh_vien):
        """{tên: luồng} các đội viên (trừ đội trưởng) đang trong auto và đã bật Auto + Tự đi Phiêu Miễu Phong."""
        cac_doi_vien = {}
        for ten in thanh_vien[1:]:
            luong = self.tim_luong(ten)
            if luong is None:
                continue
            cai_dat_dv = cau_hinh.cua_nhan_vat(luong.ten)
            if cai_dat_dv["bat_auto"] and cai_dat_pmp(cai_dat_dv)["bat"]:
                cac_doi_vien[luong.ten] = luong
        return cac_doi_vien

    def doc_doi_vien_pmp(self):
        """Đọc lại nhóm trong game (đội trưởng gọi trong lúc gom đội), None nếu đọc lỗi."""
        try:
            return self.chon_doi_vien_pmp(doc_nhom(self.game.lua)["thanh_vien"])
        except LoiLua:
            return None

    def theo_doi_pmp(self, doi, tt, cai_dat):
        """
        Đội viên theo đội trưởng (Theo đội) suốt PMP; chỉ tự chạy tới đội trưởng khi đội trưởng đang gom ở Đại Lý.
        Trong Phiêu Miểu Phong / lôi đài: đánh theo vùng trưởng ghi.
        """
        if self.dang_giao_acc_chinh() or self.dang_ac_tac:
            return
        map_dang_o = tt["map"]
        bay_gio = time.time()
        pmp = cai_dat_pmp(cai_dat)
        dem = hom_nay(pmp)
        la_doi_vien = chuan_hoa(self.ten) != chuan_hoa(doi.truong)
        try:
            self.dang_theo_doi = self.game.lua.chay(MA_DANG_THEO_DOI) == b"1"
        except LoiLua:
            self.dang_theo_doi = False
        if self.dang_theo_doi:
            self.trieu_tap_den = None
        elif self.trieu_tap_den and time.time() >= self.trieu_tap_den[3]:
            self.trieu_tap_den = None
        if la_doi_vien and pmp["bat"]:
            cap_nhat_trieu_tap_doi_vien(self.game, self.trieu_tap_den, self.pmp_trieu_tap_state)
        if la_dai_ly(map_dang_o) and pmp["bat"]:
            cap_nhat_hoi_mau_dai_ly(self.game, map_dang_o, self.ten, self.in_log, self.hoi_mau_dai_ly_state,
                                    self.nen_dung)
        if la_doi_vien and pmp["bat"] and not self.dang_theo_doi and (doi.npc_gom or doi.di_lac_duong):
            cap_nhat_doi_vien_tu_lac_duong(self.game, map_dang_o, pmp, dem, self.pmp_di_ld_state,
                                           self.pmp_ld_chay_npc_state)
        if la_doi_vien and getattr(doi, "cho_ve_sau_boss", None) and not la_dai_ly(map_dang_o):
            if bay_gio - self.luc_ve_thanh_theo_doi >= GIAY_RETRY_VE_THANH_THEO_DOI:
                self.luc_ve_thanh_theo_doi = bay_gio
                self.in_log(f"{self.ten}: PMP — thử lại về {MAP_DAI_LY} (sau boss)")
                chuan_bi_ve_thanh(self.game, self.in_log, self.ten)
                self.game.lua.chay(ma_dung_ky_nang_theo_dinh_nghia(KY_NANG_VE_THANH))
            return
        gom_truong = la_doi_vien and doi.gom_truong and not self.dang_theo_doi
        self.trang_thai["mo_ta"] = (f"{MO_TA_PHO_BAN}: chạy tới đội trưởng {doi.truong}" if gom_truong
                                    else f"{MO_TA_PHO_BAN}: theo đội trưởng {doi.truong}")
        o_dai_ly = la_dai_ly(map_dang_o)
        if gom_truong and pmp["bat"]:
            cap_nhat_doi_vien_toi_truong(self.game, doi, self.tim_luong(doi.truong), map_dang_o, self.pmp_gom_state)
        if la_doi_vien and doi.di_lac_duong and o_dai_ly and pmp["bat"]:
            self.trang_thai["mo_ta"] = f"{MO_TA_PHO_BAN}: bị bỏ lại, tự Di Chuyển sang {MAP_LAC_DUONG}"
            cap_nhat_di_lac_duong_doi_vien(self.game, map_dang_o, self.pmp_di_ld_state)
        o_lac_duong = la_lac_duong(map_dang_o)
        if la_doi_vien and o_lac_duong and pmp["bat"] and not self.dang_theo_doi \
                and dem["het_luot"] and con_sat_tinh(pmp, dem):
            cap_nhat_doi_vien_cho_sat_tinh(self.game, map_dang_o, self.pmp_gom_state)
        het_luot = can_ve_khi_het_luot(pmp, dem, map_dang_o)
        map_truong = None
        luong_tr = None
        if la_doi_vien:
            luong_tr = self.tim_luong(doi.truong)
            if luong_tr:
                try:
                    tt_tr = luong_tr.game.thong_tin()
                    map_truong = (tt_tr or {}).get("map") or luong_tr.map_hien_tai
                except (LoiLua, OSError, AttributeError):
                    map_truong = luong_tr.map_hien_tai
                # Flag het_luot lưu riêng từng acc; theo trưởng thì chỉ về thành khi TRƯỞNG hết lượt PMP.
                dem_tr = hom_nay(cai_dat_pmp(cau_hinh.cua_nhan_vat(luong_tr.ten)))
                if not dem_tr["het_luot"]:
                    het_luot = False
        can_ve, ly_do_ve = nen_ve_thanh_theo_doi(
            doi, map_dang_o, map_truong, het_luot, la_doi_vien and self.dang_theo_doi)
        if not can_ve or bay_gio - self.luc_ve_thanh_theo_doi < GIAY_RETRY_VE_THANH_THEO_DOI:
            return
        self.luc_ve_thanh_theo_doi = bay_gio
        self.in_log(f"{self.ten}: PMP — tự về {MAP_DAI_LY} ({ly_do_ve})")
        chuan_bi_ve_thanh(self.game, self.in_log, self.ten)
        self.game.lua.chay(ma_dung_ky_nang_theo_dinh_nghia(KY_NANG_VE_THANH))

    # ---------- Ác Tặc ----------

    def chon_doi_vien_ac_tac(self, thanh_vien):
        """{tên: luồng} các đội viên (trừ đội trưởng) đang trong auto (cài Ác Tặc chung trên đội trưởng)."""
        cac_doi_vien = {}
        for ten in thanh_vien[1:]:
            luong = self.tim_luong(ten)
            if luong is None:
                continue
            cai_dat_dv = cau_hinh.cua_nhan_vat(luong.ten)
            if cai_dat_dv["bat_auto"]:
                cac_doi_vien[luong.ten] = luong
        return cac_doi_vien

    def doc_doi_vien_ac_tac(self):
        try:
            return self.chon_doi_vien_ac_tac(doc_nhom(self.game.lua)["thanh_vien"])
        except LoiLua:
            return None

    def truong_ac_tac_trong_auto(self):
        """Luồng của đội trưởng (người đầu nhóm trong game) nếu đội trưởng là nhân vật khác trong auto đã bật Ác Tặc."""
        try:
            thanh_vien = doc_nhom(self.game.lua)["thanh_vien"]
        except LoiLua:
            return None, []
        if not thanh_vien or chuan_hoa(thanh_vien[0]) == chuan_hoa(self.ten):
            return None, thanh_vien
        truong = self.tim_luong(thanh_vien[0])
        if truong is None or not truong.ten:
            return None, []
        cai_dat_tr = cau_hinh.cua_nhan_vat(truong.ten)
        if not (cai_dat_tr["bat_auto"] and cai_dat_ac_tac()["bat"]):
            return None, []
        return truong, thanh_vien

    def xu_ly_ac_tac(self, tt, cai_dat):
        """
        Trong khung Ác Tặc: đội trưởng / đi một mình thì chạy AcTacRunner (chặn tới hết khung / đi hết map); đội viên
        theo đội trưởng trong auto. True nếu lượt này đã dành cho Ác Tặc (không đi PMP / chuyển sinh).
        """
        at = cai_dat_ac_tac()
        if at.get("dung_gauto") and (at.get("duong_dan_gauto") or "").strip():
            return self.xu_ly_gauto_ac_tac(tt, cai_dat, at)
        truong, thanh_vien = self.truong_ac_tac_trong_auto()
        if truong is not None:
            khung = khung_hien_tai(at)
            if khung is not None and truong.ac_tac.khung_xong == khung:
                # Đội trưởng đã đi hết các map khung này: đội viên cũng thôi, quay lại PMP / Sát Tinh.
                self.ac_tac.khung_xong = khung
                self.ket_thuc_ac_tac(tt)
                return False
            self.dang_ac_tac = True
            self.doi_pmp = self.truong_pmp = None
            self.doi_ac_tac = None
            self.truong_ac_tac = truong.doi_ac_tac
            if self.truong_ac_tac is None:
                self.trang_thai["mo_ta"] = f"{MO_TA_AC_TAC}: chờ đội trưởng {truong.ten}"
                return True
            loai, gia_tri = buoc_doi_vien(self.game, self.truong_ac_tac, tt, self.ac_tac_state, at=at)
            if loai == "di":
                self.ac_tac.di_rieng(self.ten, cai_dat, self.trang_thai, self.nen_dung_ac_tac, gia_tri)
            else:
                self.trang_thai["mo_ta"] = f"{MO_TA_AC_TAC}: {gia_tri}"
            return True
        self.dang_ac_tac = True
        self.doi_pmp = self.truong_pmp = None
        self.truong_ac_tac = None
        cac_doi_vien = self.chon_doi_vien_ac_tac(thanh_vien) if thanh_vien else {}
        bao_doi = tuple(sorted(cac_doi_vien))
        if cac_doi_vien and self.ac_tac_state.get("bao_doi") != bao_doi:
            self.ac_tac_state["bao_doi"] = bao_doi
            self.in_log(f"{self.ten}: {MO_TA_AC_TAC} đi tổ đội, là đội trưởng ({', '.join(cac_doi_vien)})")
        self.doi_ac_tac = DoiAcTac(self.ten, cac_doi_vien, self.doc_doi_vien_ac_tac)
        if time.time() < self.ac_tac.nghi_den:
            self.trang_thai["mo_ta"] = (f"{MO_TA_AC_TAC}: nghỉ sau lỗi, "
                                        f"thử lại sau {int(self.ac_tac.nghi_den - time.time())} giây")
            return True
        try:
            self.ac_tac.chay(self.ten, cai_dat, self.trang_thai, self.nen_dung_ac_tac, self.dat_vung_pho_ban,
                             self.doi_ac_tac)
        finally:
            self.doi_ac_tac = None
            self.vung_pho_ban = None
        if not self.ac_tac.can_chen(at):
            self.dang_ac_tac = False
        return True

    def xu_ly_gauto_ac_tac(self, tt, cai_dat, at):
        """
        AutoHoc đưa đội trưởng tới map Ác Tặc; khi đã tới map thì bật Ác Tặc GAuto chỉ cho đội trưởng (vd. caychay28).
        """
        truong, thanh_vien = self.truong_ac_tac_trong_auto()
        khung = khung_hien_tai(at)
        if khung is None:
            return False
        phut = gauto_ac_tac.phut_gauto(at)
        maps = cac_map_da_chon(at)
        map_dich = maps[0] if maps else None
        gauto_dang_chay = bool(self.ac_tac.gauto_het_luc > time.time())

        if truong is not None:
            if truong.ac_tac.khung_xong == khung:
                self.ket_thuc_ac_tac(tt)
                return False
            self.dang_ac_tac = True
            self.doi_pmp = self.truong_pmp = None
            self.doi_ac_tac = None
            if truong.ac_tac.gauto_het_luc > time.time():
                con = int(truong.ac_tac.gauto_het_luc - time.time())
                self.trang_thai["mo_ta"] = (f"{MO_TA_AC_TAC} (GAuto): theo đội trưởng, "
                                            f"còn {con // 60}p{con % 60:02d}s")
                return True
            self.truong_ac_tac = truong.doi_ac_tac
            if self.truong_ac_tac is None:
                self.trang_thai["mo_ta"] = f"{MO_TA_AC_TAC}: chờ đội trưởng {truong.ten} ra map"
                return True
            loai, gia_tri = buoc_doi_vien(self.game, self.truong_ac_tac, tt, self.ac_tac_state, at=at)
            if loai == "di":
                self.ac_tac.di_rieng(self.ten, cai_dat, self.trang_thai, self.nen_dung_ac_tac, gia_tri)
            else:
                self.trang_thai["mo_ta"] = f"{MO_TA_AC_TAC}: {gia_tri}"
            return True

        self.dang_ac_tac = True
        self.doi_pmp = self.truong_pmp = None
        self.truong_ac_tac = None
        if self.ac_tac.khung_xong == khung:
            self.dang_ac_tac = False
            return False

        if gauto_dang_chay and time.time() >= self.ac_tac.gauto_het_luc:
            try:
                hwnd_ql = gauto_ac_tac.tim_cua_so_quan_ly(at["duong_dan_gauto"])
                gauto_ac_tac.tat_ac_tac(hwnd_ql, self.ten, self.ac_tac.gauto_chi_so, self.ac_tac.gauto_dong_cache)
            except gauto_ac_tac.LoiGautoAcTac as loi:
                self.in_log(f"{self.ten}: GAuto Ác Tặc: không bỏ tích được Ác Tặc trên GAuto ({loi}) — bỏ tích tay")
            self.ac_tac.khung_xong = khung
            self.ac_tac.gauto_khung = None
            self.ac_tac.gauto_het_luc = 0.0
            self.ac_tac.gauto_chi_so = None
            self.dang_ac_tac = False
            self.in_log(f"{self.ten}: {MO_TA_AC_TAC} — hết {phut} phút GAuto, tắt Ác Tặc")
            return False

        if not gauto_dang_chay:
            map_hien = ten_map_chuan(tt.get("map") or "")
            chua_toi_map = not map_dich or not map_hien or not cung_ten_map(map_hien, map_dich)
            if chua_toi_map:
                if self.doi_ac_tac is None:
                    cac_doi_vien = self.chon_doi_vien_ac_tac(thanh_vien) if thanh_vien else {}
                    bao_doi = tuple(sorted(cac_doi_vien))
                    if cac_doi_vien and self.ac_tac_state.get("bao_doi") != bao_doi:
                        self.ac_tac_state["bao_doi"] = bao_doi
                        self.in_log(f"{self.ten}: {MO_TA_AC_TAC} đi tổ đội tới map GAuto ({', '.join(cac_doi_vien)})")
                    self.doi_ac_tac = DoiAcTac(self.ten, cac_doi_vien, self.doc_doi_vien_ac_tac)
                self.trang_thai["mo_ta"] = f"{MO_TA_AC_TAC}: AutoHoc đi tới {map_dich or 'map'}"
                self.ac_tac.di_den_map_gauto(self.ten, cai_dat, self.trang_thai, self.nen_dung_ac_tac,
                                             map_dich, self.doi_ac_tac)
                return True
            self.doi_ac_tac = None
            if self.ac_tac.gauto_khung != khung:
                try:
                    hwnd_ql = gauto_ac_tac.tim_cua_so_quan_ly(at["duong_dan_gauto"])
                    tieu_de_ql = gauto_ac_tac.tom_tat_cua_so(hwnd_ql)
                    chi_so = gauto_ac_tac.tim_chi_so_dong_theo_ten(hwnd_ql, self.ten, self.ac_tac.gauto_dong_cache)
                    gauto_ac_tac.dat_cai_dat_ac_tac(
                        hwnd_ql, at, self.ten, chi_so, self.ac_tac.gauto_dong_cache, ten_map=map_dich,
                        in_log=lambda chu: self.in_log(f"{self.ten}: GAuto Ác Tặc: {chu}"))
                    self.ac_tac.gauto_khung = khung
                    self.ac_tac.khung = khung
                    self.ac_tac.gauto_chi_so = chi_so
                    self.ac_tac.gauto_het_luc = time.time() + phut * 60
                    self.ac_tac.gauto_loi_cuoi = None
                    self.in_log(f"{self.ten}: {MO_TA_AC_TAC} — đã tới {map_dich}, bật GAuto {phut} phút "
                                f"(cửa sổ «{tieu_de_ql}»)")
                except gauto_ac_tac.LoiGautoAcTac as loi:
                    if str(loi) != self.ac_tac.gauto_loi_cuoi:
                        self.in_log(f"{self.ten}: GAuto Ác Tặc: {loi}")
                    self.ac_tac.gauto_loi_cuoi = str(loi)
                    self.trang_thai["mo_ta"] = f"{MO_TA_AC_TAC} (GAuto): {loi}"
                    return True

        con = max(0, int(self.ac_tac.gauto_het_luc - time.time()))
        self.trang_thai["mo_ta"] = f"{MO_TA_AC_TAC} (GAuto): đang chạy trên {map_dich or 'map'}, còn {con // 60}p{con % 60:02d}s"
        return True

    def ket_thuc_ac_tac(self, tt):
        """Ra khỏi khung Ác Tặc: thôi chế độ Ác Tặc; còn đứng ở map Ác Tặc (đội viên) thì về Đại Lý."""
        if not self.dang_ac_tac:
            return
        at = cai_dat_ac_tac()
        if at["bat"] and self.ac_tac.can_chen(at):
            self.dang_ac_tac = False
            self.doi_ac_tac = self.truong_ac_tac = None
            self.ac_tac_state = {}
            return
        if ve_thanh_neu_o_map_ac_tac(self.game, tt, self.ac_tac_state, self.in_log, self.ten):
            return
        self.dang_ac_tac = False
        self.doi_ac_tac = self.truong_ac_tac = None
        self.ac_tac_state = {}

    def xu_ly_rac(self, chi_xem):
        self.luc_vut_rac = time.time()
        chung = cau_hinh.chung()
        sao_toi_thieu = chung["so_sao_toi_thieu"] if chung["vut_trang_bi_duoi_sao"] else 0
        try:
            rac = vut_rac(self.game.lua, self.ten, self.in_log, chi_xem, self.dung.is_set, sao_toi_thieu)
        except LoiVutRac as loi:
            if str(loi) != self.loi_rac_cuoi:
                self.in_log(f"{self.ten}: không vứt rác được: {loi}")
            self.loi_rac_cuoi = str(loi)
            return
        self.loi_rac_cuoi = None
        if chi_xem:
            self.in_log(f"{self.ten}: {len(rac)} món rác"
                        + (": " + ", ".join(f"{ten_mon} (ô {o + 1}, {ly_do})" for o, ten_mon, ly_do in rac)
                           if rac else ""))

    def nhap_ma_tao_nhan_vat(self):
        lua = self.game.lua
        if self.dang_tu_dang_nhap(lua.pid) or not dang_hoi_ma_kiem_tra(lua):
            return
        self.trang_thai["mo_ta"] = "Đang nhập mã kiểm tra tạo nhân vật"
        ten = f"Game {lua.pid}"
        try:
            giai_ma_kiem_tra(lua, lambda chu: self.in_log(f"{ten}: {chu}"), self.dung.is_set)
            self.loi_ma_cuoi = None
        except (LoiGiaiCaptcha, OSError, pywintypes.error) as loi:
            if str(loi) != self.loi_ma_cuoi:
                self.in_log(f"{ten}: không tự nhập được mã kiểm tra tạo nhân vật: {loi}")
            self.loi_ma_cuoi = str(loi)
        self.trang_thai["mo_ta"] = "Chờ nhân vật vào game"

    def chay_lai(self):
        self.trang_thai["so_lan_that_bai"] = 0
        self.trang_thai["viec_da_in"] = None
        self.trang_thai["mo_ta"] = ""

    def game_da_khoi_dong_xong(self, chung):
        """
        Nạp DLL lúc game đang khởi động (đang tải giao diện) làm game văng, nên chỉ nạp khi
        DLL đã có sẵn (vd. game do auto tự mở và đăng nhập), ChickenAuto đã nhận nhân vật
        (tiêu đề có level), hoặc game đã mở đủ lâu.
        """
        if ten_trong_tieu_de(self.hwnd):
            return True
        try:
            if da_nap_dll(self.game.lua.pid):
                return True
        except OSError:
            pass
        tuoi = time.time() - psutil.Process(self.game.lua.pid).create_time()
        return tuoi >= chung["giay_cho_game_khoi_dong"]

    def vong_tu_duyet(self):
        """Xem popup mỗi giây ở luồng phụ, không phải chờ vòng auto chính (có thể đang chờ dịch chuyển)."""
        tu_duyet = TuDuyet(self.game.lua, lambda chu: self.in_log(f"{self.ten or f'Game {self.game.lua.pid}'}: {chu}"))
        mat_ket_noi = XuLyMatKetNoi(self.game.lua,
                                    lambda chu: self.in_log(f"{self.ten or f'Game {self.game.lua.pid}'}: {chu}"))
        loi_cuoi = loi_mat_ket_noi_cuoi = None
        luc_xem_mat_ket_noi = luc_xem_tang_cap = 0.0
        cap_da_bam = None
        while not self.dung.is_set() and win32gui.IsWindow(self.hwnd):
            chung = cau_hinh.chung()
            if self.da_noi and self.ten and self.dang_trong_game \
                    and time.time() - luc_xem_tang_cap >= GIAY_GIUA_MOI_LAN_TANG_CAP \
                    and cai_dat_chien_dau(cau_hinh.cua_nhan_vat(self.ten))["tu_tang_cap"]:
                luc_xem_tang_cap = time.time()
                try:
                    cap = thu_tang_cap(self.game.lua)
                    if cap is not None and cap != cap_da_bam:
                        self.in_log(f"{self.ten}: đủ kinh nghiệm, tự tăng cấp {cap} -> {cap + 1}")
                    cap_da_bam = cap if cap is not None else cap_da_bam
                except LoiLua:
                    pass
            if self.da_noi and time.time() - luc_xem_mat_ket_noi >= GIAY_GIUA_MOI_LAN_XEM_MAT_KET_NOI \
                    and not self.dang_tu_dang_nhap(self.game.lua.pid):
                luc_xem_mat_ket_noi = time.time()
                try:
                    mat_ket_noi.kiem_tra(chung["tu_thoat_khi_mat_ket_noi"])
                    loi_mat_ket_noi_cuoi = None
                except LoiLua as loi:
                    if str(loi).startswith((THONG_BAO_LOI[2], THONG_BAO_LOI[3])) and str(loi) != loi_mat_ket_noi_cuoi:
                        self.in_log(f"{self.ten or f'Game {self.game.lua.pid}'}: không xem được hộp mất kết nối: {loi}")
                    loi_mat_ket_noi_cuoi = str(loi)
            if self.da_noi and chung["tu_duyet_popup"]:
                try:
                    tu_duyet.kiem_tra(chung["tu_nhan_ty_thi"])
                    loi_cuoi = None
                except (LoiLua, LoiTuDuyet) as loi:
                    # Game đang loading thì không phản hồi, lỗi đó vòng auto chính đã báo.
                    nen_bao = isinstance(loi, LoiTuDuyet) or str(loi).startswith((THONG_BAO_LOI[2], THONG_BAO_LOI[3]))
                    if nen_bao and str(loi) != loi_cuoi:
                        self.in_log(f"{self.ten or f'Game {self.game.lua.pid}'}: không tự duyệt được: {loi}")
                    loi_cuoi = str(loi)
            self.dung.wait(GIAY_GIUA_MOI_LAN_XEM_POPUP)

    def can_chat_the_gioi(self, chung):
        if not (chung["chat_the_gioi"] and chung["noi_dung_chat_the_gioi"].strip()
                and self.ten and self.dang_trong_game):
            return False
        chon = chung["nhan_vat_chat_the_gioi"]
        if chon:
            return chuan_hoa(chon) == chuan_hoa(self.ten)
        return cau_hinh.cua_nhan_vat(self.ten)["bat_auto"]

    def vong_chat_the_gioi(self):
        """Chat kênh Thế giới ở luồng phụ, đúng chu kỳ dù vòng auto chính đang bận đi phó bản / dịch chuyển."""
        loi_cuoi = None
        while not self.dung.is_set() and win32gui.IsWindow(self.hwnd):
            chung = cau_hinh.chung()
            if self.can_chat_the_gioi(chung) \
                    and time.time() - self.luc_chat_the_gioi >= max(chung["giay_chat_the_gioi"], GIAY_CHAT_TOI_THIEU):
                noi_dung = chung["noi_dung_chat_the_gioi"].strip()
                try:
                    gui_the_gioi(self.game.lua, noi_dung)
                    self.luc_chat_the_gioi = time.time()
                    loi_cuoi = None
                    self.in_log(f"{self.ten}: chat Thế giới: {noi_dung}")
                except (LoiLua, LoiChat) as loi:
                    if str(loi) != loi_cuoi:
                        self.in_log(f"{self.ten}: không chat Thế giới được: {loi}")
                    loi_cuoi = str(loi)
            self.dung.wait(1)

    def vong_chien_dau(self):
        """Tự đánh ở luồng phụ, mỗi lượt vài phần mười giây, không phải chờ vòng auto chính."""
        chien_dau = ChienDau(self.game.lua, lambda chu: self.in_log(f"{self.ten}: {chu}"))
        tran_thu = TuXuatChien(self.game.lua, lambda chu: self.in_log(f"{self.ten}: {chu}"))
        nhat_do = NhatDo(self.game.lua, lambda chu: self.in_log(f"{self.ten}: {chu}"))
        loi_cuoi = None
        while not self.dung.is_set() and win32gui.IsWindow(self.hwnd):
            try:
                if time.time() < self.duoc_theo_den and self.da_noi and self.dang_trong_game:
                    self.muc_tieu_key = (chien_dau.doc_muc_tieu_dang_chon(), self.map_hien_tai, time.time())
            except (LoiLua, LoiChienDau):
                self.muc_tieu_key = None
            try:
                if time.time() < self.duoc_hoi_nguoi_den and self.da_noi and self.dang_trong_game:
                    self.muc_tieu_nguoi = (chien_dau.doc_nguoi_dang_chon(), self.map_hien_tai, time.time())
            except (LoiLua, LoiChienDau):
                self.muc_tieu_nguoi = None
            cai_dat_nv = cau_hinh.cua_nhan_vat(self.ten) if self.ten else None
            cai_dat = cai_dat_chien_dau(cai_dat_nv) if cai_dat_nv else None
            vung = self.vung_danh_pho_ban()
            doi_pmp = self.doi_pmp or self.truong_pmp
            doi_at = (self.doi_ac_tac or self.truong_ac_tac) if self.dang_ac_tac else None
            if cai_dat and vung:
                cai_dat = dict(cai_dat, bat=True, quanh_diem=True, ban_kinh=vung[2], lua_quai=False,
                               danh_theo_key=False, uu_tien_nguoi_choi=False,
                               diem={"map": self.map_hien_tai, "x": vung[0], "y": vung[1]})
                chien_dau.khong_bo_qua_ten = True
                if doi_at is not None:
                    # Chưa có tên Ác Tặc (vùng vừa xóa) thì không đánh con nào, kẻo đánh quái thường quanh điểm.
                    chien_dau.chi_danh_ten = tuple(doi_at.quai_danh) or ("",)
                else:
                    chien_dau.chi_danh_ten = tuple(doi_pmp.quai_danh) if doi_pmp else ()
                chien_dau.ten_bo_qua.clear()
                chien_dau.lan_hong_theo_ten.clear()
            else:
                chien_dau.khong_bo_qua_ten = False
                chien_dau.chi_danh_ten = ()
            try:
                mo_ta = None
                if self.can_an_don(cai_dat_nv, cai_dat):
                    mo_ta = chien_dau.an_don(cai_dat)
                if not mo_ta and self.can_buff_mau(cai_dat_nv, cai_dat):
                    dong_minh = {chuan_hoa(ten) for ten in cau_hinh.chung()["dong_minh"]}
                    mo_ta = chien_dau.buff_mau(cai_dat, self.doc_lai_nhom() | dong_minh)
                if not mo_ta and self.can_xuat_chien_tran_thu(cai_dat_nv, cai_dat):
                    mo_ta = tran_thu.buoc(cai_dat["hoan_hi_toi_thieu"])
            except (LoiLua, LoiChienDau):
                mo_ta = None
            if mo_ta:
                self.mo_ta_chien_dau = mo_ta
                self.dung.wait(GIAY_GIUA_MOI_LUOT_DANH)
                continue
            ten_acc_chinh_giao = (cai_dat_giao_acc_chinh().get("nhan_vat") or "").strip()
            dung_danh_giao = self.dang_giao_acc_chinh() and self.ten \
                and chuan_hoa(self.ten) == chuan_hoa(ten_acc_chinh_giao)
            if not (cai_dat and cai_dat_nv["bat_auto"] and cai_dat["bat"] and self.da_noi and self.dang_trong_game) \
                    or (self.trang_thai.get("mo_ta") or "").startswith(MO_TA_TAM_DUNG_DANH) \
                    or self.tam_dung_vi_pho_ban() or dung_danh_giao:
                chien_dau.bo_muc_tieu()
                self.mo_ta_chien_dau = ""
                try:
                    if self.da_noi and self.dang_trong_game:
                        chien_dau.cap_nhat_bi_danh()
                        self.bao_ke_danh(chien_dau)
                    else:
                        self.ke_danh = None
                except LoiChienDau:
                    self.ke_danh = None
                self.dung.wait(GIAY_GIUA_MOI_LUOT_DANH)
                continue
            if self.truong_pmp_phai_dung(cai_dat_nv):
                chien_dau.bo_muc_tieu()
                self.mo_ta_chien_dau = ""
                self.dung.wait(GIAY_GIUA_MOI_LUOT_DANH)
                continue
            try:
                mo_ta = None
                if cai_dat["nhat_do"]:
                    diem = cai_dat["diem"]
                    tam = (diem["x"], diem["y"]) if cai_dat["quanh_diem"] and diem["map"] == self.map_hien_tai \
                        else None
                    mo_ta = nhat_do.buoc(chien_dau.bo_nho_game(), tam, cai_dat["ban_kinh"])
                else:
                    nhat_do.bo_tui()
                if mo_ta:
                    chien_dau.bo_muc_tieu()
                    self.mo_ta_chien_dau = mo_ta
                    self.dung.wait(GIAY_GIUA_MOI_LUOT_DANH)
                    continue
                theo_key, muc_tieu_key = self.tin_cua_key(cai_dat)
                pk = self.tin_pk() if cai_dat["uu_tien_nguoi_choi"] else None
                self.mo_ta_chien_dau = chien_dau.buoc(cai_dat, self.map_hien_tai, theo_key, muc_tieu_key, pk)
                self.bao_ke_danh(chien_dau)
                loi_cuoi = None
            except (LoiLua, LoiChienDau) as loi:
                self.mo_ta_chien_dau = ""
                # Game đang loading thì không phản hồi, lỗi đó vòng auto chính đã báo.
                nen_bao = isinstance(loi, LoiChienDau) or str(loi).startswith((THONG_BAO_LOI[2], THONG_BAO_LOI[3]))
                if nen_bao and str(loi) != loi_cuoi:
                    self.in_log(f"{self.ten}: không tự đánh được: {loi}")
                loi_cuoi = str(loi)
            self.dung.wait(GIAY_GIUA_MOI_LUOT_DANH)
        chien_dau.dong()

    def vong_auto_click(self):
        """Bấm các ô F1-F10 đã tích ở tab Auto click, luồng riêng để bấm đều tay, không chờ vòng auto chính."""
        loi_cuoi = None
        while not self.dung.is_set() and win32gui.IsWindow(self.hwnd):
            cai_dat_nv = cau_hinh.cua_nhan_vat(self.ten) if self.ten else None
            cai_dat = auto_click.cai_dat_auto_click(cai_dat_nv) if cai_dat_nv else None
            if not (cai_dat and cai_dat_nv["bat_auto"] and cai_dat["bat"] and cai_dat["cac_phim"]
                    and self.da_noi and self.dang_trong_game) \
                    or (self.trang_thai.get("mo_ta") or "").startswith(MO_TA_TAM_DUNG_DANH) \
                    or self.tam_dung_vi_pho_ban():
                self.mo_ta_auto_click = ""
                self.dung.wait(GIAY_GIUA_MOI_LUOT_DANH)
                continue
            try:
                self.game.lua.chay(auto_click.ma_bam_phim(cai_dat["cac_phim"]))
                self.mo_ta_auto_click = auto_click.mo_ta(cai_dat)
                loi_cuoi = None
            except LoiLua as loi:
                self.mo_ta_auto_click = ""
                # Game đang loading thì không phản hồi, lỗi đó vòng auto chính đã báo.
                if str(loi).startswith((THONG_BAO_LOI[2], THONG_BAO_LOI[3])) and str(loi) != loi_cuoi:
                    self.in_log(f"{self.ten}: không auto click được: {loi}")
                loi_cuoi = str(loi)
            self.dung.wait(cai_dat["giay"])

    def tim_luong(self, ten):
        khoa = chuan_hoa(ten)
        return next((luong for luong in self.lay_cac_luong() if luong.ten and chuan_hoa(luong.ten) == khoa), None)

    def bao_ke_danh(self, chien_dau):
        ke_danh = chien_dau.ke_danh_gan_day()
        self.ke_danh = None if ke_danh is None else (ke_danh, self.map_hien_tai, time.time())

    def doc_lai_nhom(self):
        """Tên (chuẩn hóa) người cùng nhóm trong game, đọc lại mỗi GIAY_DOC_LAI_NHOM_KHI_PK giây."""
        bay_gio = time.time()
        if bay_gio - self.luc_doc_nhom >= GIAY_DOC_LAI_NHOM_KHI_PK:
            self.luc_doc_nhom = bay_gio
            try:
                self.thanh_vien_nhom = doc_nhom(self.game.lua)["thanh_vien"]
            except LoiLua:
                pass
        return {chuan_hoa(ten) for ten in self.thanh_vien_nhom}

    def can_an_don(self, cai_dat_nv, cai_dat):
        """Bật "Ẩn độn khi bị PK" (tab Chiến đấu), đang ở trong game và không dịch chuyển / chuyển sinh."""
        return bool(cai_dat and cai_dat_nv["bat_auto"] and cai_dat["an_don"] and self.da_noi and self.dang_trong_game) \
            and not (self.trang_thai.get("mo_ta") or "").startswith(MO_TA_TAM_DUNG_DANH)

    def can_buff_mau(self, cai_dat_nv, cai_dat):
        """Nga My bật Buff máu (tab Chiến đấu), đang ở trong game và không dịch chuyển / chuyển sinh / đi phó bản."""
        return bool(cai_dat and cai_dat_nv["bat_auto"] and cai_dat["buff_mau"]
                    and self.mon_phai == MON_PHAI_NGA_MY and self.da_noi and self.dang_trong_game) \
            and not (self.trang_thai.get("mo_ta") or "").startswith(MO_TA_TAM_DUNG_DANH) \
            and not self.tam_dung_vi_pho_ban()

    def can_xuat_chien_tran_thu(self, cai_dat_nv, cai_dat):
        """Bật "Tự xuất chiến trân thú" (tab Chiến đấu), đang ở trong game và không dịch chuyển / chuyển sinh /
        đi phó bản."""
        return bool(cai_dat and cai_dat_nv["bat_auto"] and cai_dat["xuat_chien_tran_thu"]
                    and self.da_noi and self.dang_trong_game) \
            and not (self.trang_thai.get("mo_ta") or "").startswith(MO_TA_TAM_DUNG_DANH) \
            and not self.tam_dung_vi_pho_ban()

    def tin_pk(self):
        """
        {"ban_be": tên (chuẩn hóa) mọi nhân vật trong auto, người cùng nhóm, danh sách mời ở tab Nhóm và danh sách
         đồng minh ở tab Chiến đấu - không đánh,
         "ke_danh_nhom": id server kẻ đang đánh người cùng nhóm (nhân vật trong auto, cùng map), mới nhất trước,
         "muc_tieu_truong": id server người chơi trưởng nhóm (nhân vật trong auto, cùng map) đang chọn, hoặc None}.
        """
        bay_gio = time.time()
        trong_nhom = self.doc_lai_nhom()
        cac_luong = self.lay_cac_luong()
        ke_danh_nhom = sorted(
            ((luong.ke_danh[2], luong.ke_danh[0]) for luong in cac_luong
             if luong is not self and luong.ten and chuan_hoa(luong.ten) in trong_nhom and luong.ke_danh
             and luong.ke_danh[1] == self.map_hien_tai and bay_gio - luong.ke_danh[2] <= GIAY_TIN_KEY_CON_DUNG),
            reverse=True)
        muc_tieu_truong = None
        truong = self.tim_luong(self.thanh_vien_nhom[0]) if len(self.thanh_vien_nhom) > 1 else None
        if truong is not None and truong is not self:
            truong.duoc_hoi_nguoi_den = bay_gio + GIAY_KEY_DOC_MUC_TIEU
            tin = truong.muc_tieu_nguoi
            if tin and tin[1] == self.map_hien_tai and bay_gio - tin[2] <= GIAY_TIN_KEY_CON_DUNG:
                muc_tieu_truong = tin[0]
        chung = cau_hinh.chung()
        return {"ban_be": trong_nhom | {chuan_hoa(luong.ten) for luong in cac_luong if luong.ten}
                | {chuan_hoa(ten) for ten in chung["danh_sach_moi"] + chung["dong_minh"]},
                "ke_danh_nhom": [ma_id for _, ma_id in ke_danh_nhom],
                "muc_tieu_truong": muc_tieu_truong}

    def tin_cua_key(self, cai_dat):
        """
        (True, id server quái Key đang chọn hoặc None) nếu đang đánh theo Key; (False, None) nếu không bật, Key là
        chính mình, Key không có trong auto / chưa vào game / khác map - khi đó tự đánh như bình thường.
        """
        if not cai_dat["danh_theo_key"]:
            return False, None
        ten_key = cai_dat["ten_key"] or cau_hinh.chung()["truong_nhom"]
        key = self.tim_luong(ten_key) if ten_key else None
        if key is None or key is self:
            return False, None
        key.duoc_theo_den = time.time() + GIAY_KEY_DOC_MUC_TIEU
        tin = key.muc_tieu_key
        if tin is None or tin[1] != self.map_hien_tai or time.time() - tin[2] > GIAY_TIN_KEY_CON_DUNG:
            return False, None
        return True, tin[0]

    def run(self):
        threading.Thread(target=self.vong_tu_duyet, daemon=True).start()
        threading.Thread(target=self.vong_chien_dau, daemon=True).start()
        threading.Thread(target=self.vong_auto_click, daemon=True).start()
        threading.Thread(target=self.vong_chat_the_gioi, daemon=True).start()
        map_truoc = None
        while not self.dung.is_set() and win32gui.IsWindow(self.hwnd):
            chung = cau_hinh.chung()
            try:
                if not self.da_noi:
                    if not self.game_da_khoi_dong_xong(chung):
                        self.trang_thai["mo_ta"] = "Chờ game khởi động xong"
                        self.dung.wait(chung["giay_giua_moi_lan_kiem_tra"])
                        continue
                    self.da_noi = True

                tt = self.game.thong_tin()
                self.dang_trong_game = tt is not None
                if tt is None:
                    self.trang_thai["mo_ta"] = "Chờ nhân vật vào game"
                    self.hang_doi.put(("chua_vao_game", self.hwnd))
                    if chung["tu_nhap_ma_tao_nhan_vat"]:
                        self.nhap_ma_tao_nhan_vat()
                    self.dung.wait(chung["giay_giua_moi_lan_kiem_tra"])
                    continue
                self.ten = tt["ten"]
                self.tai_khoan = tt["tai_khoan"] or None
                self.mon_phai = tt["mon_phai"]
                if self.anh_tui_cua != self.ten:
                    self.anh_tui, self.anh_tui_cua = anh_tui_goc(self.ten, self.game.lua), self.ten
                if map_truoc is not None and tt["map"] != map_truoc:
                    self.in_log(f"{self.ten} đã tới [{tt['map']}]")
                map_truoc = self.map_hien_tai = tt["map"]
                self.hang_doi.put(("cap_nhat", self.hwnd, tt))
                if self.dang_tu_dang_nhap(self.game.lua.pid):
                    # Nhân vật mới đang nhận đồ tân thủ: không vứt rác / mời nhóm / chạy auto chen vào.
                    self.trang_thai["mo_ta"] = "Auto tạo nhân vật đang điều khiển"
                    self.dung.wait(chung["giay_giua_moi_lan_kiem_tra"])
                    continue
                self.cai_dat_game(chung)

                cai_dat = cau_hinh.cua_nhan_vat(self.ten)
                if cai_dat["bat_auto"] and tt["hp"] > 0:
                    cap_nhat_hoi_mau_dai_ly(self.game, tt["map"], self.ten, self.in_log, self.hoi_mau_dai_ly_state,
                                            self.nen_dung)

                xung_quanh = doc_xung_quanh(self.game.lua)
                self.hang_doi.put(("xung_quanh", self.hwnd, xung_quanh))
                nhom = self.lay_nhom()
                if nhom:
                    mo_ta, thanh_vien = xu_ly_nhom(
                        self.game.lua, self.ten, nhom, xung_quanh, self.trang_thai_nhom, self.in_log)
                    self.hang_doi.put(("nhom", self.hwnd, self.ten, mo_ta, thanh_vien))

                viec_rac, self.yeu_cau_rac = self.yeu_cau_rac, None
                if viec_rac is None and chung["bat_vut_rac"] \
                        and time.time() - self.luc_vut_rac >= chung["giay_giua_moi_lan_vut_rac"]:
                    viec_rac = "vut"
                if viec_rac:
                    self.xu_ly_rac(viec_rac == "xem")

                di_pho_ban = cai_dat_pmp(cai_dat)["bat"]
                for khoa, viec in self.tu_mua_dung:
                    # Nhân vật đi phó bản luôn giữ buff Càn Khôn Hồ như lúc tạo nhân vật mới.
                    if cai_dat["bat_auto"] and (chung[khoa] or (khoa == "tu_dung_can_khon_ho" and di_pho_ban)):
                        viec.kiem_tra(self.ten, self.nen_dung)
                if cai_dat["bat_auto"] and tt["hp"] > 0:
                    self.tu_cong_diem.kiem_tra(self.ten, cai_dat, self.nen_dung)
                # Đang đi phó bản (tự đi hoặc theo đội trưởng) thì chuyển sinh / mốc map train chờ đi xong mới chạy.
                khoa_giao = self.dang_giao_acc_chinh()
                # Giờ Ác Tặc được ưu tiên hơn PMP / Sát Tinh / chuyển sinh; chết thì để nhánh dưới Đầu thai trước.
                dang_at = not khoa_giao and (self.ac_tac_dang_chen(cai_dat) or self.dang_theo_ac_tac(cai_dat))
                if dang_at and tt["hp"] > 0 and self.xu_ly_ac_tac(tt, cai_dat):
                    self.dung.wait(chung["giay_giua_moi_lan_kiem_tra"])
                    continue
                if not dang_at:
                    self.ket_thuc_ac_tac(tt)
                self.truong_pmp = self.doi_theo_truong() if cai_dat["bat_auto"] and not khoa_giao else None
                if khoa_giao:
                    self.doi_pmp = None
                pmp_nv = cai_dat_pmp(cai_dat)
                if not khoa_giao and not dang_at and cai_dat["bat_auto"] and tt["hp"] > 0 \
                        and can_ve_khi_het_luot(pmp_nv, hom_nay(pmp_nv), tt["map"]) and not self.truong_pmp \
                        and not la_map_trong_pho_ban(tt["map"]):
                    self.trang_thai["mo_ta"] = f"{MO_TA_PHO_BAN}: hết lượt, về {MAP_DAI_LY}"
                    self.theo_doi_pmp(DoiPMP(self.ten, {}), tt, cai_dat)
                di_pmp = not khoa_giao and not dang_at and cai_dat["bat_auto"] and tt["hp"] > 0 \
                    and not self.truong_pmp and self.pho_ban.can_di(cai_dat)
                doi = self.lap_doi_pmp(cai_dat) if di_pmp else None
                if di_pmp and doi not in (None, False):
                    self.doi_pmp = doi
                elif not di_pmp:
                    self.doi_pmp = None
                if self.truong_pmp and tt["hp"] > 0:
                    self.theo_doi_pmp(self.truong_pmp, tt, cai_dat)
                elif di_pmp and doi is not False:
                    ten = self.ten
                    # Giữ đội giữa hai vòng (đội viên khỏi chạy đi train); không đi PMP nữa thì vòng sau xóa.
                    if doi and self.doi_pmp:
                        self.doi_pmp.cac_doi_vien, self.doi_pmp.doc_lai = doi.cac_doi_vien, doi.doc_lai
                        doi = self.doi_pmp
                    self.doi_pmp = doi
                    try:
                        self.pho_ban.chay(ten, cai_dat, self.trang_thai, self.nen_dung_pho_ban, self.dat_vung_pho_ban,
                                          lambda: self.hang_doi.put(("cai_dat_doi", ten)), doi)
                    except Exception:
                        self.doi_pmp = None
                        raise
                # Chết thì vẫn tự Đầu thai dù tắt chuyển sinh.
                elif cai_dat["bat_auto"] and (cai_dat["bat_chuyen_sinh"] or tt["hp"] <= 0):
                    ten = self.ten
                    if dang_at:
                        cai_dat = dict(cai_dat, bat_chuyen_sinh=False)
                    xu_ly_nhan_vat(self.game, ten, tt["level"], tt["map"], tt["hp"], cai_dat, chung,
                                   self.trang_thai, self.in_log,
                                   self.nen_dung_chuyen_sinh if cai_dat["bat_chuyen_sinh"] else self.nen_dung,
                                   lambda: self.hang_doi.put(("cai_dat_doi", ten)))
                elif cai_dat["bat_auto"]:
                    self.trang_thai.update(mo_ta="", da_in_chet=False, luc_hp_0=None)
                else:
                    self.trang_thai["mo_ta"] = "Chưa bật auto"
            except LoiLua as loi:
                self.hang_doi.put(("loi", self.hwnd, str(loi)))
            except Exception:
                self.in_log(f"Cửa sổ {self.hwnd}: lỗi không mong đợi\n{traceback.format_exc()}")
            self.dung.wait(chung["giay_giua_moi_lan_kiem_tra"])
        self.hang_doi.put(("mat", self.hwnd))

    def kiem_tra_tui(self):
        """Đọc ô (1,1) và các hàng đang dùng rồi ghi ra log, chạy ở luồng phụ để giao diện không bị đứng."""
        def lam():
            cai_dat = cau_hinh.cua_nhan_vat(self.ten)
            cs = cai_dat["chuyen_sinh"]
            can_xem = [(None, f"chuyển sinh (level {cs['level']})")]
            if cs.get("dich_chuyen_truoc_chuyen_sinh"):
                can_xem.append((cs["hang_vat_pham_truoc_chuyen_sinh"],
                                f"tới {cs['map_truoc_chuyen_sinh']} trước khi chuyển sinh"))
            for moc in cai_dat["moc_level"]:
                can_xem.append((moc["hang_vat_pham_dich_chuyen"], f"mốc level {moc['level']} tới {moc['map']}"))
                if moc.get("map_khi_bi_pk"):
                    can_xem.append((moc["hang_vat_pham_khi_bi_pk"],
                                    f"mốc level {moc['level']} bị PK tới {moc['map_khi_bi_pk']}"))
            try:
                for hang, viec in can_xem:
                    cac_o_dung, _ = tim_cac_o(self.game, cac_o_cua_viec(hang))
                    co_do = ", ".join(f"({h},{c}) {ten_vp}" for h, c, ten_vp in cac_o_dung) or "trống"
                    self.in_log(f"{self.ten} - {mo_ta_o(hang)} ({viec}): {co_do}")
            except LoiLua as loi:
                self.in_log(f"{self.ten}: không đọc được túi ({loi})")
        threading.Thread(target=lam, daemon=True).start()


class UngDung:
    def __init__(self, root):
        self.root = root
        self.hang_doi = queue.Queue()
        self.cac_luong = {}
        self.thong_tin = {}
        self.loi = {}
        self.ten_dang_sua = None
        self.cac_luong_dang_nhap = {}
        self.luong_tao_nv = None
        self.luong_nang_cap_online = None
        self.luong_xoay_vong = None
        self.luong_giao_acc_chinh = None
        self.luong_giao_dich_ngay = None
        dat_phien_xoay_vong(False)
        self.tai_khoan_tam_dung = set()
        self.trang_thai_tai_khoan = {}
        self._nhat_ky_file_loi = False
        self._duong_dan_nhat_ky = DUONG_DAN_NHAT_KY
        self._nhat_ky_hom_nay = time.strftime("%Y-%m-%d")
        don_nhat_ky_sang_ngay_moi(self._duong_dan_nhat_ky)
        self.nhom_hien_tai = None
        self.trang_thai_nhom = {}
        self.doi_hinh_nhom = {}
        self.xung_quanh = {}
        self.ds_xung_quanh_dang_hien = None
        self.cac_ds_xung_quanh = []
        self.cac_ve_lai_ds = []
        self.dang_doi_tat_ca = False
        self.luc_vao_game = {}
        self.ds_tai_khoan_dang_hien = None
        self._luc_ve_lai = 0.0
        self._tai_khoan_dem = None
        self._tai_khoan_luc_sua = -1.0
        self._luc_sap_xep_bang = 0.0
        self.loi_giam_sat = None
        self.he_so = root.winfo_fpixels("1i") / 96

        root.title(TIEU_DE)
        root.report_callback_exception = lambda *loi: self.in_log(
            "Lỗi giao diện:\n" + "".join(traceback.format_exception(*loi)))
        ttk.Style().configure("Treeview", rowheight=int(22 * self.he_so))

        self.bien_thanh_trang_thai = tk.StringVar()
        ttk.Label(root, textvariable=self.bien_thanh_trang_thai, relief="sunken", padding=(6, 2)).pack(
            side="bottom", fill="x")
        self._tao_danh_sach()
        self._tao_cac_tab()
        self._tao_log()
        self._dat_kich_thuoc_cua_so()
        root.protocol("WM_DELETE_WINDOW", self.thoat)
        # Vẽ cửa sổ ngay; các tab dựng dần, xong mới đọc license, tìm cửa sổ game, chạy vòng cập nhật.
        self.dang_khoi_dong = True
        self.bien_thanh_trang_thai.set("Đang tải giao diện...")
        root.update()
        self._buoc_tao_tab = self._cac_buoc_tao_tab()
        root.after(0, self._tao_tab_tiep)

    def _hoan_tat_khoi_dong(self):
        xoa_co_xoay_vong_luu_tat_ca()
        self.in_log("Mở auto. Bấm vào ô ☐ ở cột Auto để bật auto cho từng nhân vật "
                    "(bấm tiêu đề Auto để bật tất cả).")
        thong_bao_phuc_hoi = cau_hinh.cac_thong_bao_phuc_hoi()
        for dong in thong_bao_phuc_hoi:
            self.in_log(dong)
        if thong_bao_phuc_hoi:
            messagebox.showwarning("Phục hồi cấu hình", "\n\n".join(thong_bao_phuc_hoi), parent=self.root)
        if DUONG_DAN_NHAT_KY != NHAT_KY_CANH_EXE:
            self.in_log(f"Nhật ký file (máy ảo / thư mục không ghi được cạnh exe): {DUONG_DAN_NHAT_KY}")
        so_hien_lai = hien_lai_cua_so_an_lan_truoc()
        if so_hien_lai:
            self.in_log(f"Lần trước tắt auto lúc đang ẩn game, đã hiện lại {so_hien_lai} cửa sổ game")
        if han_dung.co_han_dung():
            self.in_log(f"Bản dùng thử, hết hạn lúc {han_dung.ngay_het_han()}")
            self.xem_han_dung()
        if kich_hoat.bat_buoc_kich_hoat():
            hop_le, mo_ta = kich_hoat.xac_thuc_license()
            self.in_log(f"Kích hoạt: {mo_ta}")
            if not hop_le:
                self.in_log("Chưa kích hoạt — mở tab Kích hoạt, gửi mã máy qua Zalo để nhận license.dat")
        canh_bao_ocr = kiem_tra_ocr_win7()
        if canh_bao_ocr:
            self.in_log(canh_bao_ocr)
        else:
            threading.Thread(target=lam_nong_ocr, daemon=True, name="lam-nong-ocr").start()
        self.quet_cua_so()
        self.xu_ly_hang_doi()
        self.giam_sat_dang_nhap()

    def xem_han_dung(self):
        giay = han_dung.giay_con_lai()
        if giay <= 0:
            self.in_log("Bản dùng thử đã hết hạn, tắt auto")
            messagebox.showerror("Hết hạn dùng thử", han_dung.THONG_BAO_HET_HAN)
            self.thoat()
            return
        self.root.title(f"{TIEU_DE} - Dùng thử ({han_dung.mo_ta_con_lai(giay)})")
        self.root.after(MILI_GIAY_GIUA_MOI_LAN_XEM_HAN_DUNG, self.xem_han_dung)

    def px(self, so):
        return int(so * self.he_so)

    @staticmethod
    def _vung_lam_viec():
        """(trái, trên, phải, dưới) của màn hình chính, đã trừ taskbar."""
        vung = ctypes.wintypes.RECT()
        if ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(vung), 0):  # SPI_GETWORKAREA
            return vung.left, vung.top, vung.right, vung.bottom
        return None

    def _dat_kich_thuoc_cua_so(self):
        """Chiều cao full vùng làm việc (trừ taskbar), chiều rộng gọn; không để trạng thái zoomed."""
        rong = self.px(RONG_CUA_SO_MAC_DINH)
        rong_min = self.px(RONG_CUA_SO_TOI_THIEU)
        cao_min = self.px(CAO_CUA_SO_TOI_THIEU)
        try:
            self.root.state("normal")
        except tk.TclError:
            pass
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        vung = self._vung_lam_viec() or (0, 0, sw, sh)
        user32 = ctypes.windll.user32
        # geometry chỉ tính phần ruột: trừ thanh tiêu đề + viền trên/dưới (SM_CYCAPTION, SM_CYSIZEFRAME, SM_CXPADDEDBORDER).
        vien = user32.GetSystemMetrics(4) + 2 * (user32.GetSystemMetrics(33) + user32.GetSystemMetrics(92))
        rong = min(rong, max(rong_min, vung[2] - vung[0]))
        cao = max(cao_min, vung[3] - vung[1] - vien)
        x = max(vung[0], vung[0] + (vung[2] - vung[0] - rong) // 2)
        self.root.minsize(rong_min, cao_min)
        self.root.geometry(f"{rong}x{cao}+{x}+{vung[1]}")

    # ---------- Tab cuộn được bằng chuột (màn hình laptop nhỏ) ----------

    def _tab_cuon(self, so_tay, ten):
        """Thêm một tab có thanh cuộn dọc vào so_tay, trả về khung để đặt nội dung."""
        ngoai = ttk.Frame(so_tay)
        so_tay.add(ngoai, text=ten)
        nen = ttk.Style().lookup("TFrame", "background") or "SystemButtonFace"
        canvas = tk.Canvas(ngoai, highlightthickness=0, borderwidth=0, background=nen,
                           yscrollincrement=self.px(20))
        thanh_cuon = ttk.Scrollbar(ngoai, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=thanh_cuon.set)
        tab = ttk.Frame(canvas, padding=8)
        cua_so = canvas.create_window((0, 0), window=tab, anchor="nw")
        canvas.pack(side="left", fill="both", expand=True)

        da_ve = {"cao": None, "rong": None, "toi_da": None}
        hen = {"id": None}

        def cap_nhat():
            hen["id"] = None
            cao = tab.winfo_reqheight()
            rong = tab.winfo_reqwidth()
            toi_da = self.chieu_cao_tab_toi_da()
            if (cao, rong, toi_da) != (da_ve["cao"], da_ve["rong"], da_ve["toi_da"]):
                da_ve.update(cao=cao, rong=rong, toi_da=toi_da)
                canvas.configure(scrollregion=(0, 0, rong, cao), width=rong, height=min(cao, toi_da))
            thua = canvas.winfo_height() > 1 and cao > canvas.winfo_height()
            if thua and not thanh_cuon.winfo_ismapped():
                thanh_cuon.pack(side="right", fill="y", before=canvas)
            elif not thua and thanh_cuon.winfo_ismapped():
                thanh_cuon.pack_forget()
                canvas.yview_moveto(0)

        def hen_cap_nhat(_su_kien=None):
            # Một lần sắp xếp lại sinh cả chuỗi <Configure>: gộp lại, chỉ tính một lần.
            if hen["id"] is None:
                hen["id"] = canvas.after(MILI_GIAY_GOP_CAP_NHAT_TAB, cap_nhat)

        def doi_co(su_kien):
            canvas.itemconfigure(cua_so, width=su_kien.width)
            hen_cap_nhat()
        tab.bind("<Configure>", hen_cap_nhat)
        canvas.bind("<Configure>", doi_co)
        self.cac_canvas_tab.add(canvas)
        self.cac_cap_nhat_tab.append(hen_cap_nhat)
        return tab

    def _tinh_cao_tab_toi_da(self):
        cao_cua_so = self.root.winfo_height()
        if cao_cua_so > 1:
            return max(self.px(160), cao_cua_so - self._khung_tren.winfo_reqheight() - self.px(130))
        return None

    def _lam_moi_cao_tab(self):
        self._cao_tab_toi_da = None
        for hen_cap_nhat in self.cac_cap_nhat_tab:
            hen_cap_nhat()

    def _keo_dai_duoc(self, bang, khoa, cha=None, khi_doi=None, **pack):
        """Thanh kéo dưới danh sách (Treeview / Listbox): giữ chuột kéo lên / xuống để đổi số dòng hiện, nhớ cho lần sau."""
        thanh = tk.Frame(cha or bang.master, height=self.px(8), cursor="sb_v_double_arrow")
        thanh.pack(fill="x", **pack)
        vach = ttk.Separator(thanh, orient="horizontal", cursor="sb_v_double_arrow")
        vach.place(relx=0.5, rely=0.5, relwidth=0.25, anchor="center")
        da_luu = cau_hinh.chung()["cao_bang"].get(khoa)
        if da_luu:
            bang.configure(height=da_luu)
        if isinstance(bang, ttk.Treeview):
            moi_dong = int(22 * self.he_so)
        else:
            moi_dong = tkfont.Font(font=bang.cget("font")).metrics("linespace") + 1
        luc_bat_dau = {}

        def bat_dau(su_kien):
            luc_bat_dau.update(y=su_kien.y_root, so_dong=int(bang.cget("height")))

        def keo(su_kien):
            if not luc_bat_dau:
                return
            so_dong = luc_bat_dau["so_dong"] + round((su_kien.y_root - luc_bat_dau["y"]) / moi_dong)
            so_dong = max(2, min(40, so_dong))
            if so_dong != int(bang.cget("height")):
                bang.configure(height=so_dong)

        def tha(_su_kien):
            if not luc_bat_dau:
                return
            luc_bat_dau.clear()
            cao_bang = cau_hinh.chung()["cao_bang"]
            cao_bang[khoa] = int(bang.cget("height"))
            cau_hinh.dat_chung({"cao_bang": cao_bang})
            if khi_doi:
                khi_doi()

        for w in (thanh, vach):
            w.bind("<ButtonPress-1>", bat_dau)
            w.bind("<B1-Motion>", keo)
            w.bind("<ButtonRelease-1>", tha)

    def chieu_cao_tab_toi_da(self):
        """Chiều cao tab: chừa chỗ cho danh sách nhân vật, ô log, thanh trạng thái (nhớ lại tới khi đổi cỡ cửa sổ)."""
        if self._cao_tab_toi_da is None:
            self._cao_tab_toi_da = self._tinh_cao_tab_toi_da()
        if self._cao_tab_toi_da is None:
            return max(self.px(160), self.px(CAO_CUA_SO_MAC_DINH - 200))
        return self._cao_tab_toi_da

    def _cua_so_doi_co(self, su_kien):
        """<Configure> của root nhận cả sự kiện của mọi widget con: chỉ xử lý khi chính cửa sổ đổi cỡ."""
        if su_kien.widget is not self.root:
            return
        moi = self._tinh_cao_tab_toi_da()
        if moi is not None and moi != self._cao_tab_toi_da:
            self._lam_moi_cao_tab()

    def _canvas_cua(self, w):
        """Canvas tab chứa widget w (nhớ theo đường dẫn widget để lăn chuột không phải dò lại cây)."""
        khoa = str(w)
        if khoa in self._canvas_theo_widget:
            return self._canvas_theo_widget[khoa]
        goc = w
        while goc is not None and goc not in self.cac_canvas_tab:
            goc = goc.master
        self._canvas_theo_widget[khoa] = goc
        return goc

    def _lan_chuot(self, su_kien):
        """Lăn chuột ở đâu trong một tab thì cuộn tab đó (trừ ô log / danh sách tự cuộn được)."""
        try:
            w = self.root.winfo_containing(su_kien.x_root, su_kien.y_root) or su_kien.widget
            if isinstance(w, str):
                w = self.root.nametowidget(w)
        except (KeyError, tk.TclError):
            return None
        if w is None or w.winfo_class() in ("Text", "Listbox", "Treeview"):
            return None
        canvas = self._canvas_cua(w)
        if canvas is not None and canvas.yview() != (0.0, 1.0):
            canvas.yview_scroll(-3 if su_kien.delta > 0 else 3, "units")
        return "break"

    # ---------- Danh sách nhân vật + khung thông tin ----------

    def _tao_danh_sach(self):
        tren = ttk.Frame(self.root, padding=(6, 6, 6, 0))
        tren.pack(fill="x")
        self._khung_tren = tren

        self.bang = ttk.Treeview(tren, columns=("bat", "an", "nhan_vat", "tai_khoan", "trang_thai"), show="headings",
                                 height=5, selectmode="browse")
        for cot, tieu_de, rong in (("bat", "Auto", 40), ("an", "Ẩn", 40), ("nhan_vat", "Nhân vật", 108),
                                   ("tai_khoan", "Tài khoản", 72), ("trang_thai", "Trạng thái", 118)):
            self.bang.heading(cot, text=tieu_de)
            self.bang.column(cot, width=self.px(rong), anchor="center" if cot in ("bat", "an") else "w",
                             stretch=cot not in ("bat", "an"))
        self.bang.heading("bat", command=self.bat_tat_ca_auto)
        self.bang.heading("an", command=self.an_hien_tat_ca)
        self.bang.pack(side="left", fill="both", expand=True)
        self.bang.bind("<Button-1>", self._bam_vao_bang)
        self.bang.bind("<<TreeviewSelect>>", self._chon_nhan_vat)
        self.dong_dang_keo = None
        self.bang.bind("<B1-Motion>", self._keo_dong_bang, add="+")
        self.bang.bind("<ButtonRelease-1>", self._tha_dong_bang, add="+")

        khung = ttk.Frame(tren, padding=(10, 0, 0, 0))
        khung.pack(side="left", fill="y")
        self.bien_thong_tin = {}
        for dong, (khoa, nhan) in enumerate((("level", "Level"), ("hp", "HP"), ("mp", "MP"), ("map", "Map"),
                                             ("toa_do", "Vị trí"), ("chuyen_sinh", "Chuyển sinh"))):
            ttk.Label(khung, text=nhan).grid(row=dong, column=0, sticky="w", pady=1)
            self.bien_thong_tin[khoa] = tk.StringVar(value="-")
            ttk.Label(khung, textvariable=self.bien_thong_tin[khoa], width=16).grid(
                row=dong, column=1, sticky="w", padx=(8, 0))
        self._keo_dai_duoc(self.bang, "nhan_vat", cha=self.root, khi_doi=self._lam_moi_cao_tab, padx=6, after=tren)

    def _keo_dong_bang(self, su_kien):
        """Giữ chuột vào một dòng rồi kéo lên / xuống để đổi chỗ nhân vật trong danh sách."""
        dich = self.bang.identify_row(su_kien.y)
        if self.dong_dang_keo is None:
            self.dong_dang_keo = self.bang.identify_row(su_kien.y) or None
            return
        if dich and dich != self.dong_dang_keo and self.bang.exists(self.dong_dang_keo):
            self.bang.move(self.dong_dang_keo, "", self.bang.index(dich))

    def _tha_dong_bang(self, _su_kien):
        if self.dong_dang_keo is None:
            return
        self.dong_dang_keo = None
        dang_hien = []
        for iid in self.bang.get_children():
            luong = self.cac_luong.get(int(iid))
            if luong and luong.ten:
                dang_hien.append(luong.ten)
        cu = cau_hinh.chung()["thu_tu_nhan_vat"]
        moi = dang_hien + [ten for ten in cu if ten not in dang_hien]
        if moi != cu:
            cau_hinh.dat_chung({"thu_tu_nhan_vat": moi})

    def sap_xep_bang(self):
        """Xếp các dòng theo thứ tự đã kéo thả (theo tên nhân vật); dòng chưa biết tên / chưa xếp thì để cuối."""
        if self.dong_dang_keo is not None:
            return
        bay_gio = time.monotonic()
        if bay_gio - self._luc_sap_xep_bang < GIAY_VE_LAI_TOI_DA:
            return
        self._luc_sap_xep_bang = bay_gio
        thu_tu = {ten: i for i, ten in enumerate(cau_hinh.chung()["thu_tu_nhan_vat"])}
        hien_tai = list(self.bang.get_children())

        def khoa(cap):
            vi_tri, iid = cap
            luong = self.cac_luong.get(int(iid))
            return thu_tu.get(luong.ten if luong else None, len(thu_tu)), vi_tri
        moi = [iid for _, iid in sorted(enumerate(hien_tai), key=khoa)]
        if moi != hien_tai:
            for vi_tri, iid in enumerate(moi):
                self.bang.move(iid, "", vi_tri)

    def _bam_vao_bang(self, su_kien):
        """Bấm vào cột Auto thì bật/tắt auto của nhân vật ở dòng đó."""
        if self.bang.identify_region(su_kien.x, su_kien.y) != "cell" or self.bang.identify_column(su_kien.x) != "#1":
            return
        dong = self.bang.identify_row(su_kien.y)
        luong = self.cac_luong.get(int(dong)) if dong else None
        if luong is None or luong.ten is None:
            return
        self.dat_bat_auto(luong.ten, not cau_hinh.cua_nhan_vat(luong.ten)["bat_auto"])

    def _chan_neu_chua_kich_hoat(self):
        if not kich_hoat.bat_buoc_kich_hoat() or kich_hoat.da_kich_hoat():
            return False
        messagebox.showwarning(
            "Chưa kích hoạt",
            f"Auto chưa được kích hoạt trên máy này.\n\n"
            f"Mở tab Kích hoạt → sao chép mã máy (HWID) gửi Zalo {kich_hoat.LIEN_HE_ZALO}, "
            f"nhận file license.dat rồi chọn file hoặc đặt cạnh AutoHoc.exe.")
        return True

    def dat_bat_auto(self, ten, bat):
        if bat and self._chan_neu_chua_kich_hoat():
            return
        cai_dat = cau_hinh.cua_nhan_vat(ten)
        cai_dat["bat_auto"] = bat
        cau_hinh.dat_nhan_vat(ten, cai_dat)
        if bat:
            for luong in self.cac_luong.values():
                if luong.ten == ten:
                    luong.chay_lai()
        self.in_log(f"{'BẬT' if bat else 'TẮT'} auto cho {ten}")
        self.ve_lai_bang()

    def bat_tat_ca_auto(self):
        """Bấm tiêu đề Auto: bật auto cho mọi nhân vật; tất cả đã bật rồi thì tắt hết."""
        cac_ten = sorted({luong.ten for luong in self.cac_luong.values() if luong.ten})
        bat = not all(cau_hinh.cua_nhan_vat(ten)["bat_auto"] for ten in cac_ten)
        if bat and self._chan_neu_chua_kich_hoat():
            return
        for ten in cac_ten:
            if cau_hinh.cua_nhan_vat(ten)["bat_auto"] != bat:
                self.dat_bat_auto(ten, bat)

    def an_hien_tat_ca(self):
        """Bấm tiêu đề Ẩn/Hiện: ẩn mọi cửa sổ game (auto vẫn chạy), bấm lần nữa thì hiện lại đúng chỗ cũ."""
        if cac_cua_so_da_an():
            self.in_log(f"Hiện lại {hien_cua_so()} cửa sổ game")
        else:
            self.in_log(f"Ẩn {an_cua_so(list(self.cac_luong))} cửa sổ game, auto vẫn chạy. "
                        "Bấm tiêu đề Hiện để hiện lại (tắt AutoHoc cũng tự hiện lại)")
        self.ve_lai_bang()

    def dat_bat_chuyen_sinh(self, ten, bat):
        cai_dat = cau_hinh.cua_nhan_vat(ten)
        cai_dat["bat_chuyen_sinh"] = bat
        cau_hinh.dat_nhan_vat(ten, cai_dat)
        if bat:
            for luong in self.cac_luong.values():
                if luong.ten == ten:
                    luong.chay_lai()
        self.in_log(f"{'BẬT' if bat else 'TẮT'} auto chuyển sinh cho {ten}"
                    + (" - cần tích cả ô Auto thì mới chạy" if bat and not cai_dat["bat_auto"] else ""))
        if ten == self.ten_dang_sua and self.bien_bat_chuyen_sinh_nv.get() != bat:
            self.bien_bat_chuyen_sinh_nv.set(bat)
        self.ve_lai_bang()

    def _doi_bat_chuyen_sinh_nv(self):
        if self.ten_dang_sua is None:
            self.bien_bat_chuyen_sinh_nv.set(False)
            messagebox.showinfo("Chuyển sinh", "Chọn một nhân vật trong danh sách trước")
            return
        self.dat_bat_chuyen_sinh(self.ten_dang_sua, self.bien_bat_chuyen_sinh_nv.get())

    def _chon_nhan_vat(self, _su_kien=None):
        chon = self.bang.selection()
        luong = self.cac_luong.get(int(chon[0])) if chon else None
        if luong is None or luong.ten is None:
            return
        if luong.ten != self.ten_dang_sua:
            self.nap_form(luong.ten)
        self.ve_lai_thong_tin()

    def luong_dang_chon(self):
        for luong in self.cac_luong.values():
            if luong.ten is not None and luong.ten == self.ten_dang_sua:
                return luong
        return None

    # ---------- Tab cài đặt ----------

    def _tao_cac_tab(self):
        self.cac_canvas_tab = set()
        self.cac_cap_nhat_tab = []
        self._canvas_theo_widget = {}
        self._cao_tab_toi_da = None
        self.root.bind("<Configure>", self._cua_so_doi_co, add="+")
        so_tay = self.so_tay = ttk.Notebook(self.root)
        so_tay.pack(fill="both", expand=True, padx=6, pady=6)
        self.root.bind_all("<MouseWheel>", self._lan_chuot)
        # Lăn chuột lướt qua ô chọn thì cuộn tab, không đổi giá trị ô đó.
        for lop in ("TCombobox", "TSpinbox"):
            self.root.bind_class(lop, "<MouseWheel>", self._lan_chuot)

    def _cac_buoc_tao_tab(self):
        """
        Dựng từng tab theo thứ tự. Tạo mỗi widget ttk tốn vài ms nên dựng xen giữa các lượt vòng sự kiện
        (_tao_tab_tiep): cửa sổ hiện ngay, không treo vài giây lúc mở.
        """
        so_tay = self.so_tay
        return [lambda: self._tao_tab_chuyen_sinh(so_tay),
                lambda: self._tao_tab_kich_hoat(so_tay),
                lambda: self._tao_tab_config(so_tay),
                lambda: self._tao_tab_chien_dau(so_tay),
                lambda: self._tao_tab_auto_click(so_tay),
                lambda: self._tao_tab_pho_ban(so_tay),
                lambda: self._tao_tab_chung(so_tay),
                lambda: self._tao_tab_tai_khoan(so_tay),
                lambda: self._tao_tab_nhom(so_tay),
                lambda: self._tao_tab_tien_ich(so_tay),
                lambda: self._tao_tab_tao_nhan_vat(so_tay),
                lambda: self._tao_tab_cai_dat(so_tay),
                lambda: self._cho_keo_tha_tab(so_tay),
                lambda: self._tao_o_an_hien_tab(so_tay)]

    def _tao_tab_tiep(self):
        if self._buoc_tao_tab:
            self._buoc_tao_tab.pop(0)()
            self.root.after(1, self._tao_tab_tiep)
            return
        self.dang_khoi_dong = False
        self._hoan_tat_khoi_dong()

    def _tao_tab_chuyen_sinh(self, so_tay):
        tab = self._tab_cuon(so_tay, "Chuyển sinh")
        self.nhan_dang_sua = ttk.Label(tab, text="Chọn một nhân vật trong danh sách để chỉnh cài đặt",
                                       font=("Segoe UI", 9, "bold"))
        self.nhan_dang_sua.pack(anchor="w")

        dong = ttk.Frame(tab)
        dong.pack(fill="x", pady=(4, 2))
        self.bien_bat_chuyen_sinh_tat_ca = tk.BooleanVar()
        self.bien_tat_chuyen_sinh_tat_ca = tk.BooleanVar()
        self.chuyen_sinh_truoc_khi_doi = {}
        ttk.Checkbutton(dong, text="Bật auto chuyển sinh cho tất cả nhân vật",
                        variable=self.bien_bat_chuyen_sinh_tat_ca,
                        command=lambda: self.doi_chuyen_sinh_tat_ca(self.bien_bat_chuyen_sinh_tat_ca, True)
                        ).pack(side="left")
        ttk.Checkbutton(dong, text="Tắt auto chuyển sinh cho tất cả nhân vật",
                        variable=self.bien_tat_chuyen_sinh_tat_ca,
                        command=lambda: self.doi_chuyen_sinh_tat_ca(self.bien_tat_chuyen_sinh_tat_ca, False)
                        ).pack(side="left", padx=(16, 0))
        self.bien_bat_chuyen_sinh_nv = tk.BooleanVar()
        ttk.Checkbutton(tab, text="Bật auto chuyển sinh cho nhân vật này",
                        variable=self.bien_bat_chuyen_sinh_nv,
                        command=self._doi_bat_chuyen_sinh_nv).pack(anchor="w", pady=(0, 6), after=dong)

        self.cac_o_chon_map = []
        khung_cs = ttk.LabelFrame(tab, text="Chuyển sinh", padding=6)
        khung_cs.pack(fill="x")
        self.bien_cs_level = tk.StringVar()
        self.bien_cs_dich_chuyen_truoc = tk.BooleanVar()
        self.bien_cs_map_truoc = tk.StringVar()
        self.bien_cs_hang_truoc = tk.StringVar()
        dong = ttk.Frame(khung_cs)
        dong.pack(fill="x")
        ttk.Label(dong, text="Khi đạt level").pack(side="left")
        ttk.Entry(dong, textvariable=self.bien_cs_level, width=6).pack(side="left", padx=4)
        ttk.Label(dong, text="dùng ngay vật phẩm ở ô 1,1 trong túi đồ").pack(side="left")
        ttk.Checkbutton(khung_cs, text="Dịch chuyển tới map trước, tới nơi rồi mới dùng vật phẩm chuyển sinh",
                        variable=self.bien_cs_dich_chuyen_truoc,
                        command=lambda: self._luu_ngay(self.bien_cs_dich_chuyen_truoc, self._sua_dich_chuyen_truoc,
                                                       "dịch chuyển tới map trước khi chuyển sinh")).pack(
            anchor="w", pady=(6, 0))
        dong = ttk.Frame(khung_cs)
        dong.pack(fill="x", padx=(self.px(20), 0), pady=(2, 0))
        ttk.Label(dong, text="Map").pack(side="left")
        self._o_chon_map(dong, self.bien_cs_map_truoc).pack(side="left", padx=4)
        ttk.Label(dong, text="dùng vật phẩm ở hàng").pack(side="left")
        ttk.Combobox(dong, textvariable=self.bien_cs_hang_truoc, values=CAC_HANG_TUI, state="readonly",
                     width=4).pack(side="left", padx=4)
        ttk.Label(dong, text="trong túi").pack(side="left")
        ttk.Label(khung_cs, text="Không tích thì đứng ở map nào cũng dùng ô 1,1 ngay. Các config level / map / hàng "
                                 "ở ngay bên dưới.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(6, 0))

        khung_moc = ttk.LabelFrame(tab, text="Config dịch chuyển theo level", padding=6)
        khung_moc.pack(fill="x", pady=(6, 0))
        self.khung_cac_moc = ttk.Frame(khung_moc)
        self.khung_cac_moc.pack(fill="x")
        self.cac_moc = []
        ttk.Button(khung_moc, text="+ Thêm config", command=lambda: self.them_moc(
            {"level": 1, "map": "", "hang_vat_pham_dich_chuyen": 5})).pack(anchor="w", pady=(4, 0))
        ttk.Label(khung_moc, text="Đúng level thì auto kiểm tra map của dòng đó. Nếu đang ở đúng map rồi thì "
                                  "không dùng vật phẩm; chưa ở map đó thì auto dùng vật phẩm lần lượt ở các ô cột "
                                  "1 tới 5 của hàng đã chọn. Dòng \"Bị PK\" giữ nguyên như trước.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(4, 0))

        khung_diem = ttk.LabelFrame(tab, text="Tự cộng điểm tiềm năng (bảng Alt+C)", padding=6)
        khung_diem.pack(fill="x", pady=(6, 0))
        self.bien_cong_diem = tk.BooleanVar()
        self.bien_chi_so = {khoa: tk.BooleanVar() for khoa, _ in CAC_CHI_SO}
        self.bien_dung_hop_point = tk.BooleanVar()
        dong = ttk.Frame(khung_diem)
        dong.pack(fill="x")
        ttk.Checkbutton(dong, text="Có điểm tiềm năng thì tự cộng vào:", variable=self.bien_cong_diem,
                        command=lambda: self._luu_ngay(self.bien_cong_diem, self._sua_cong_diem,
                                                       "tự cộng điểm tiềm năng")).pack(side="left")
        for khoa, ten_chi_so in CAC_CHI_SO:
            ttk.Checkbutton(dong, text=ten_chi_so, variable=self.bien_chi_so[khoa],
                            command=lambda khoa=khoa, ten_chi_so=ten_chi_so: self._luu_ngay(
                                self.bien_chi_so[khoa], self._sua_cong_diem, f"cộng điểm vào {ten_chi_so}")).pack(
                side="left", padx=(6, 0))
        ttk.Checkbutton(khung_diem, text="Tự dùng Hộp Point (500 / 800) nhặt được trong túi",
                        variable=self.bien_dung_hop_point,
                        command=lambda: self._luu_ngay(self.bien_dung_hop_point, self._sua_cong_diem,
                                                       "tự dùng Hộp Point")).pack(anchor="w", pady=(4, 0))
        ttk.Label(khung_diem, text="Tích nhiều chỉ số thì chia đều: mỗi 1000 điểm cho lần lượt từng chỉ số (giống bấm "
                                   "\"+\" ở bảng Alt+C), còn dưới 1000 điểm thì chờ đủ. Dùng Hộp Point xong auto cộng "
                                   "luôn điểm nhận được.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(4, 0))

        nut = ttk.Frame(tab)
        nut.pack(fill="x", pady=(8, 0))
        ttk.Button(nut, text="Lưu", command=self.luu_form).pack(side="left")
        ttk.Button(nut, text="Áp dụng cho tất cả", command=self.ap_dung_tat_ca).pack(side="left", padx=4)
        ttk.Button(nut, text="Kiểm tra túi", command=self.kiem_tra_tui).pack(side="left")
        ttk.Button(nut, text="Chạy lại", command=self.chay_lai).pack(side="left", padx=4)

    def _tao_tab_chung(self, so_tay):
        tab_chung = ttk.Frame(so_tay, padding=8)
        so_tay.add(tab_chung, text="Cài đặt chung")
        so_tay.hide(tab_chung)
        self.bien_chung = {}
        gia_tri = cau_hinh.chung()
        for dong_so, (khoa, nhan) in enumerate(CAI_DAT_CHUNG):
            ttk.Label(tab_chung, text=nhan).grid(row=dong_so, column=0, sticky="w", pady=2)
            self.bien_chung[khoa] = tk.StringVar(value=str(gia_tri[khoa]))
            ttk.Spinbox(tab_chung, from_=1, to=600, textvariable=self.bien_chung[khoa], width=6).grid(
                row=dong_so, column=1, sticky="w", padx=8)
        ttk.Button(tab_chung, text="Lưu", command=self.luu_chung).grid(
            row=len(CAI_DAT_CHUNG), column=0, sticky="w", pady=(8, 0))

    def _cho_keo_tha_tab(self, so_tay):
        """Giữ chuột vào tên tab rồi kéo sang trái / phải để đổi chỗ; thứ tự lưu ở "thu_tu_tab" (theo tên tab)."""
        theo_ten = {so_tay.tab(tab, "text"): tab for tab in so_tay.tabs()}
        for vi_tri, ten in enumerate(ten for ten in cau_hinh.chung()["thu_tu_tab"] if ten in theo_ten):
            so_tay.insert(vi_tri, theo_ten[ten])
        dang_keo = {"tab": None}

        def tab_o(su_kien):
            if not so_tay.identify(su_kien.x, su_kien.y):
                return None
            try:
                return so_tay.index(f"@{su_kien.x},{su_kien.y}")
            except tk.TclError:
                return None

        def bam(su_kien):
            chi_so = tab_o(su_kien)
            dang_keo["tab"] = None if chi_so is None else so_tay.tabs()[chi_so]

        def keo(su_kien):
            chi_so = tab_o(su_kien)
            if dang_keo["tab"] is not None and chi_so is not None and so_tay.tabs()[chi_so] != dang_keo["tab"]:
                so_tay.insert(chi_so, dang_keo["tab"])

        def tha(_su_kien):
            if dang_keo["tab"] is None:
                return
            dang_keo["tab"] = None
            thu_tu = [so_tay.tab(tab, "text") for tab in so_tay.tabs()]
            if thu_tu != cau_hinh.chung()["thu_tu_tab"]:
                cau_hinh.dat_chung({"thu_tu_tab": thu_tu})

        so_tay.bind("<ButtonPress-1>", bam, add="+")
        so_tay.bind("<B1-Motion>", keo, add="+")
        so_tay.bind("<ButtonRelease-1>", tha, add="+")

    def _tao_o_an_hien_tab(self, so_tay):
        """Tab Cài đặt: mỗi tab một ô tích hiện / ẩn, lưu tên tab đang ẩn ở "tab_an". Tab Cài đặt luôn hiện."""
        tab_an = set(cau_hinh.chung()["tab_an"])
        cac_tab = [(so_tay.tab(tab, "text"), tab) for tab in so_tay.tabs()]
        cac_tab = [(ten, tab) for ten, tab in cac_tab if ten not in TAB_LUON_HIEN]
        self.bien_hien_tab = {}

        def doi(ten, tab):
            if self.bien_hien_tab[ten].get():
                so_tay.add(tab)
            else:
                so_tay.hide(tab)
            an = [t for t, _ in cac_tab if not self.bien_hien_tab[t].get()]
            cau_hinh.dat_chung({"tab_an": an})
            self.in_log(f"{'Hiện' if self.bien_hien_tab[ten].get() else 'Ẩn'} tab {ten}")

        khung = ttk.LabelFrame(self.tab_cai_dat, text="Ẩn / hiện tab", padding=6)
        khung.pack(fill="x", pady=(8, 0))
        for so, (ten, tab) in enumerate(cac_tab):
            self.bien_hien_tab[ten] = tk.BooleanVar(value=ten not in tab_an)
            ttk.Checkbutton(khung, text=ten, variable=self.bien_hien_tab[ten],
                            command=lambda ten=ten, tab=tab: doi(ten, tab)).grid(
                row=so // 3, column=so % 3, sticky="w", padx=(0, 16), pady=1)
            if ten in tab_an:
                so_tay.hide(tab)
        ttk.Label(khung, text="Bỏ tích để ẩn tab khỏi thanh tab (auto vẫn chạy như cũ, chỉ ẩn giao diện). "
                              "Tab Cài đặt luôn hiện.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").grid(
            row=len(cac_tab) // 3 + 1, column=0, columnspan=3, sticky="w", pady=(4, 0))

    def _tao_tab_kich_hoat(self, so_tay):
        tab = self._tab_cuon(so_tay, "Kích hoạt")
        ttk.Label(tab, text="Mã máy (HWID) — gửi cho admin qua Zalo để nhận file license.dat:",
                  wraplength=self.px(DOAN_WRAP_GHI_CHU)).pack(anchor="w")
        dong = ttk.Frame(tab)
        dong.pack(fill="x", pady=(6, 4))
        self.bien_hwid_kich_hoat = tk.StringVar(value=kich_hoat.doc_hwid())
        ttk.Entry(dong, textvariable=self.bien_hwid_kich_hoat, width=42, state="readonly").pack(side="left")
        ttk.Button(dong, text="Sao chép HWID", command=self._sao_chep_hwid_kich_hoat).pack(side="left", padx=(8, 0))
        ttk.Button(dong, text="Làm mới mã máy", command=self._lam_moi_hwid_kich_hoat).pack(side="left", padx=(4, 0))

        self.nhan_trang_thai_kich_hoat = ttk.Label(tab, text="", wraplength=self.px(DOAN_WRAP_GHI_CHU))
        self.nhan_trang_thai_kich_hoat.pack(anchor="w", pady=(8, 4))

        nut = ttk.Frame(tab)
        nut.pack(fill="x", pady=(4, 8))
        ttk.Button(nut, text="Chọn file license.dat…", command=self._chon_license_kich_hoat).pack(side="left")
        ttk.Button(nut, text="Kiểm tra lại", command=self._cap_nhat_trang_thai_kich_hoat).pack(side="left", padx=(8, 0))

        ttk.Label(
            tab,
            text=f"Sau khi nhận license.dat, đặt file cạnh AutoHoc.exe hoặc bấm «Chọn file».\n"
                 f"Liên hệ Zalo {kich_hoat.LIEN_HE_ZALO} (cùng số hỗ trợ bản dùng thử).",
            foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w")
        if not kich_hoat.bat_buoc_kich_hoat():
            ttk.Label(tab, text="Bản đang chạy từ code / không bắt buộc kích hoạt — vẫn có thể thử license tại đây.",
                      foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU)).pack(anchor="w", pady=(8, 0))
        self._cap_nhat_trang_thai_kich_hoat()

    def _sao_chep_hwid_kich_hoat(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.bien_hwid_kich_hoat.get())
        self.in_log(f"Đã sao chép HWID: {self.bien_hwid_kich_hoat.get()}")

    def _lam_moi_hwid_kich_hoat(self):
        self.bien_hwid_kich_hoat.set(kich_hoat.doc_hwid())

    def _cap_nhat_trang_thai_kich_hoat(self):
        hop_le, mo_ta = kich_hoat.xac_thuc_license()
        mau = "green" if hop_le and kich_hoat.bat_buoc_kich_hoat() else ("orange" if hop_le else "red")
        if not kich_hoat.bat_buoc_kich_hoat():
            mo_ta = f"{mo_ta} (bản này không bắt buộc kích hoạt khi bật Auto.)"
        self.nhan_trang_thai_kich_hoat.configure(text=mo_ta, foreground=mau)

    def _chon_license_kich_hoat(self):
        duong_dan = filedialog.askopenfilename(
            title="Chọn license.dat",
            filetypes=[("License", "*.dat"), ("Tất cả", "*.*")],
        )
        if not duong_dan:
            return
        ok, mo_ta = kich_hoat.luu_license_tu_file(duong_dan)
        if ok:
            self.in_log(f"Kích hoạt: {mo_ta}")
            messagebox.showinfo("Kích hoạt", mo_ta)
        else:
            messagebox.showerror("Kích hoạt", mo_ta)
        self._cap_nhat_trang_thai_kich_hoat()

    def _tao_tab_config(self, so_tay):
        tab = self._tab_cuon(so_tay, "Config")
        khung_map = ttk.LabelFrame(tab, text="Danh sách map (dùng chung cho mọi nhân vật)", padding=6)
        khung_map.pack(fill="x")
        self.ds_map = tk.Listbox(khung_map, height=4, exportselection=False)
        self.ds_map.pack(side="left", fill="x", expand=True)
        cot = ttk.Frame(khung_map)
        cot.pack(side="left", anchor="n", padx=(6, 0))
        self.bien_map_moi = tk.StringVar()
        ttk.Entry(cot, textvariable=self.bien_map_moi, width=22).pack(anchor="w")
        ttk.Button(cot, text="Thêm map", command=self.them_map).pack(anchor="w", pady=(4, 0))
        ttk.Button(cot, text="Xóa map đang chọn", command=self.xoa_map).pack(anchor="w", pady=(4, 0))
        self._keo_dai_duoc(self.ds_map, "ds_map", cha=tab, after=khung_map)
        self.nap_ds_map()

        self.nhan_config = ttk.Label(tab, text="Danh sách này dùng cho các ô chọn map ở tab Chuyển sinh",
                                     font=("Segoe UI", 9, "bold"))
        self.nhan_config.pack(anchor="w", pady=(8, 0))
        ttk.Label(tab, text="Thêm / xóa map ở đây để các ô chọn map trong tab Chuyển sinh có sẵn danh sách. "
                            "Các config level nằm ngay trong tab Chuyển sinh.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(4, 0))

    def cac_map(self):
        return cau_hinh.chung()["danh_sach_map"]

    def _o_chon_map(self, cha, bien):
        """Ô chọn map trong danh sách, vẫn gõ tay được tên map khác."""
        o = ttk.Combobox(cha, textvariable=bien, values=self.cac_map(), width=20)
        self.cac_o_chon_map.append(o)
        return o

    def nap_ds_map(self):
        cac_map = self.cac_map()
        self.ds_map.delete(0, "end")
        for ten_map in cac_map:
            self.ds_map.insert("end", ten_map)
        self.cac_o_chon_map = [o for o in self.cac_o_chon_map if o.winfo_exists()]
        for o in self.cac_o_chon_map:
            o.configure(values=cac_map)

    def them_map(self):
        ten_map = self.bien_map_moi.get().strip()
        if not ten_map:
            return
        cac_map = self.cac_map()
        if any(chuan_hoa(m) == chuan_hoa(ten_map) for m in cac_map):
            messagebox.showinfo("Thêm map", f"Đã có map {ten_map}")
            return
        cau_hinh.dat_chung({"danh_sach_map": cac_map + [ten_map]})
        self.bien_map_moi.set("")
        self.nap_ds_map()
        self.in_log(f"Đã thêm map {ten_map} vào danh sách")

    def xoa_map(self):
        chon = self.ds_map.curselection()
        if not chon:
            return
        cac_map = self.cac_map()
        ten_map = cac_map.pop(chon[0])
        cau_hinh.dat_chung({"danh_sach_map": cac_map})
        self.nap_ds_map()
        self.in_log(f"Đã xóa map {ten_map} khỏi danh sách (các mốc đang dùng map này vẫn giữ nguyên)")

    def _tao_tab_cai_dat(self, so_tay):
        tab = self.tab_cai_dat = self._tab_cuon(so_tay, "Cài đặt")
        chung = cau_hinh.chung()
        self.bien_cai_dat_game = {}
        for khoa, nhan, _ in CAI_DAT_GAME:
            self.bien_cai_dat_game[khoa] = tk.BooleanVar(value=chung[khoa])
            ttk.Checkbutton(tab, text=nhan, variable=self.bien_cai_dat_game[khoa],
                            command=lambda khoa=khoa: self.doi_cai_dat_game(khoa)).pack(anchor="w")
        ttk.Label(tab, text="Âm thanh: như Duyệt Cài đặt âm thanh. Đồ họa: như Duyệt Thiết lập hiển thị (Thấp/Không, "
                            "tắt địa hình/nhân vật cao cấp, số mô hình) + các biến View_* (hiệu ứng, thời tiết…) "
                            "trong game và trong Bin/System.cfg, Accounts/*.pfc trước khi mở Game.exe. "
                            "Không đổi gamma, chất lượng màu 16 bit (yszl), đồng bộ dọc, FULLSCREEN / độ phân giải. "
                            "Tắt tùy chọn thì không tự bật lại đồ họa.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(4, 0))

    def doi_cai_dat_game(self, khoa):
        bat = self.bien_cai_dat_game[khoa].get()
        cau_hinh.dat_chung({khoa: bat})
        nhan = next(nhan for k, nhan, _ in CAI_DAT_GAME if k == khoa)
        self.in_log(f"{'BẬT' if bat else 'TẮT'}: {nhan}"
                    + (" (các game đang mở cũng làm ngay)" if bat else " (không tự bật lại những gì đã đổi)"))
        if bat:
            chung = cau_hinh.chung()
            for luong in self.cac_luong.values():
                luong.da_cai_dat_game.discard(khoa)
                if luong.ten and luong.dang_trong_game:
                    luong.cai_dat_game(chung)

    def _tao_tab_chien_dau(self, so_tay):
        tab = self._tab_cuon(so_tay, "Chiến đấu")
        self.nhan_chien_dau = ttk.Label(tab, text="Chọn một nhân vật trong danh sách để chỉnh cài đặt",
                                        font=("Segoe UI", 9, "bold"))
        self.nhan_chien_dau.pack(anchor="w")
        khung = ttk.LabelFrame(tab, text="Tự đánh", padding=8)
        khung.pack(fill="x", pady=(4, 0))
        self.bien_cd = {khoa: tk.BooleanVar() for khoa in CAC_O_TICH_CHIEN_DAU}
        self.bien_cd.update({khoa: tk.StringVar()
                             for khoa in ("ban_kinh", "x", "y", "so_quai_lua", "ten_key", "phan_tram_buff",
                                          "phan_tram_an_don", "hoan_hi_toi_thieu")})
        self.map_diem_dang_sua = ""

        def o_tich(dong, khoa, chu):
            ttk.Checkbutton(khung, text=chu, variable=self.bien_cd[khoa], command=self.luu_chien_dau).grid(
                row=dong, column=0, sticky="w", pady=2)
            phu = ttk.Frame(khung)
            phu.grid(row=dong, column=1, sticky="w", padx=(8, 0))
            return phu

        phu = o_tich(0, "bat", "Tự động đánh")
        ttk.Label(phu, text="Bán kính").pack(side="left")
        ttk.Spinbox(phu, from_=1, to=60, textvariable=self.bien_cd["ban_kinh"], width=4).pack(side="left", padx=4)
        phu = o_tich(1, "quanh_diem", "Quanh")
        ttk.Label(phu, text="[").pack(side="left")
        ttk.Entry(phu, textvariable=self.bien_cd["x"], width=5).pack(side="left")
        ttk.Label(phu, text=",").pack(side="left")
        ttk.Entry(phu, textvariable=self.bien_cd["y"], width=5).pack(side="left")
        ttk.Label(phu, text="]").pack(side="left")
        self.nhan_map_diem = ttk.Label(phu, text="", foreground="gray")
        self.nhan_map_diem.pack(side="left", padx=4)
        ttk.Button(phu, text="Lấy vị trí hiện tại", command=self.lay_vi_tri_chien_dau).pack(side="left", padx=4)
        o_tich(2, "dung_f1", "Dùng F1")
        phu = o_tich(3, "lua_quai", "Lùa Quái")
        ttk.Label(phu, text="Gom").pack(side="left")
        ttk.Spinbox(phu, from_=1, to=20, textvariable=self.bien_cd["so_quai_lua"], width=4).pack(side="left", padx=4)
        ttk.Label(phu, text="con rồi mới đánh").pack(side="left")
        phu = o_tich(4, "danh_theo_key", "Đánh theo Key")
        ttk.Label(phu, text="Key").pack(side="left")
        self.chon_key = ttk.Combobox(phu, textvariable=self.bien_cd["ten_key"], width=18, state="readonly",
                                     postcommand=self._nap_ds_key)
        self.chon_key.pack(side="left", padx=4)
        self.chon_key.bind("<<ComboboxSelected>>", lambda _: self.luu_chien_dau())
        ttk.Label(phu, text="để trống = trưởng nhóm ở tab Nhóm", foreground="gray").pack(side="left", padx=4)
        o_tich(5, "dung_skill_pet", "Dùng Skill Pet")
        phu = o_tich(6, "xuong_thu", "Xuống thú cưỡi")
        ttk.Label(phu, text="khi bắt đầu đánh (thành thị không có quái nên không xuống)",
                  foreground="gray").pack(side="left")
        phu = o_tich(7, "nhat_do", "Tự nhặt túi đồ")
        ttk.Label(phu, text="khi không có buff Càn Khôn Hồ: chạy tới túi đồ trong bán kính đánh rồi nhặt",
                  foreground="gray").pack(side="left")
        khung_tu_danh = khung

        self.khung_buff = khung = ttk.LabelFrame(tab, text="Nga My - Buff máu", padding=8)
        dong = ttk.Frame(khung)
        dong.pack(anchor="w")
        ttk.Checkbutton(dong, text="Buff máu khi đồng đội / mình còn dưới", variable=self.bien_cd["buff_mau"],
                        command=self.luu_chien_dau).pack(side="left")
        o = ttk.Spinbox(dong, from_=1, to=99, textvariable=self.bien_cd["phan_tram_buff"], width=4,
                        command=self.luu_chien_dau)
        o.pack(side="left", padx=4)
        o.bind("<Return>", lambda _: self.luu_chien_dau())
        ttk.Label(dong, text="% máu").pack(side="left")
        ttk.Label(khung, text=f"Chọn người máu thấp nhất (người cùng nhóm hoặc trong danh sách đồng minh đang thấy "
                              f"được, hoặc mình) rồi dùng thẳng "
                              f"kỹ năng {TEN_KY_NANG_BUFF_MAU}; không có kỹ năng này thì bấm F{PHIM_BUFF_DU_PHONG}. "
                              "Chạy cả khi không bật Tự động đánh.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(4, 0))
        self.khung_tu_danh = khung_tu_danh

        khung = ttk.LabelFrame(tab, text="Trân thú", padding=8)
        khung.pack(fill="x", pady=(6, 0))
        dong = ttk.Frame(khung)
        dong.pack(anchor="w")
        ttk.Checkbutton(dong, text="Tự xuất chiến trân thú, hoan hỉ dưới",
                        variable=self.bien_cd["xuat_chien_tran_thu"], command=self.luu_chien_dau).pack(side="left")
        o = ttk.Spinbox(dong, from_=1, to=100, textvariable=self.bien_cd["hoan_hi_toi_thieu"], width=4,
                        command=self.luu_chien_dau)
        o.pack(side="left", padx=4)
        o.bind("<Return>", lambda _: self.luu_chien_dau())
        ttk.Label(dong, text="thì bấm Ăn").pack(side="left")
        ttk.Label(khung, text="Trân thú chưa xuất chiến thì gọi ra (có nhiều con thì gọi con cấp cao nhất). Hoan hỉ "
                              "dưới mức đặt thì bấm Ăn tới khi đủ (cả khi trân thú đang xuất chiến). Chạy cả khi "
                              "không bật Tự động đánh.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(4, 0))

        khung = ttk.LabelFrame(tab, text="Tăng cấp", padding=8)
        khung.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(khung, text="Tự Động Tăng Cấp", variable=self.bien_cd["tu_tang_cap"],
                        command=self.luu_chien_dau).pack(anchor="w")
        ttk.Label(khung, text="Đủ kinh nghiệm thì tự bấm Thăng cấp (như nút ở bảng nhân vật Alt+C). Mặc định bật cho "
                              "mọi nhân vật; chạy cả khi không tích ô Auto / không bật Tự động đánh.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(4, 0))

        khung = ttk.LabelFrame(tab, text="Khi bật PK đội / PK cá nhân", padding=8)
        khung.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(khung, text="Bật PK: có người chơi thì đánh người trước quái, cả nhóm đánh theo trưởng nhóm",
                        variable=self.bien_cd["uu_tien_nguoi_choi"], command=self.luu_chien_dau).pack(anchor="w")
        dong = ttk.Frame(khung)
        dong.pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(dong, text="Bị người chơi đánh mà máu mình dưới", variable=self.bien_cd["an_don"],
                        command=self.luu_chien_dau).pack(side="left")
        o = ttk.Spinbox(dong, from_=1, to=99, textvariable=self.bien_cd["phan_tram_an_don"], width=4,
                        command=self.luu_chien_dau)
        o.pack(side="left", padx=4)
        o.bind("<Return>", lambda _: self.luu_chien_dau())
        ttk.Label(dong, text=f"% thì dùng {TEN_KY_NANG_AN_DON}").pack(side="left")
        ttk.Label(khung, text=f"Đang ẩn thân thì không đánh / buff (sẽ bị lộ), chờ máu hồi tới "
                              f"{MAU_HET_AN_THAN * 100:.0f}% hoặc hết ẩn thân rồi đánh tiếp.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w")

        khung = ttk.LabelFrame(tab, text="Đồng minh - không PK (dùng chung cho mọi nhân vật)", padding=8)
        khung.pack(fill="x", pady=(6, 0))
        self._tao_ds_ten(khung, "dong_minh", "Đồng minh (white list)", "danh sách đồng minh không PK")

        khung = ttk.LabelFrame(tab, text="Tự dùng kỹ năng (ô trên thanh kỹ năng)", padding=8)
        khung.pack(fill="x", pady=(6, 0))
        self.bien_phim_skill = {phim: tk.BooleanVar() for phim in CAC_PHIM_SKILL}
        for cot, phim in enumerate(CAC_PHIM_SKILL):
            ttk.Checkbutton(khung, text=f"F{phim}", variable=self.bien_phim_skill[phim],
                            command=self.luu_chien_dau).grid(row=0, column=cot, sticky="w", padx=(0, 6))

        nut = ttk.Frame(tab)
        nut.pack(fill="x", pady=(8, 0))
        ttk.Button(nut, text="Lưu", command=self.luu_chien_dau).pack(side="left")
        ttk.Button(nut, text="Áp dụng cho tất cả", command=self.ap_dung_chien_dau_tat_ca).pack(side="left", padx=4)
        ttk.Label(tab, text="Chỉ đánh khi nhân vật được tích ô Auto trong danh sách phía trên. "
                            "Tự động đánh: chọn quái gần nhất trong bán kính rồi đánh, chết thì sang con khác. "
                            "Quanh [x,y]: chỉ đánh quái quanh điểm đó (cùng map), hết quái thì chạy về điểm. "
                            "Dùng F1 / Tự dùng kỹ năng: khi đang đánh, mỗi giây bấm một ô, lần lượt F1 rồi các ô "
                            "F2-F10 đã tích (game không cho biết kỹ năng hồi chưa, ô chưa hồi thì bỏ qua lượt đó). "
                            "Đánh theo Key: đánh đúng con quái mà "
                            "nhân vật Key (trưởng nhóm) đang chọn, không xét bán kính; Key chưa chọn quái thì đánh "
                            "nốt con đang đánh rồi chờ; Key không có trong auto hoặc khác map thì tự đánh như "
                            "thường. Lùa Quái: đánh mỗi con một cái cho chúng đuổi theo, gom đủ số con rồi mới "
                            "đánh (nên để kỹ năng đánh lan ở F1). Dùng Skill Pet: dùng kỹ năng của trân thú đang "
                            "xuất chiến. NPC bị bỏ qua. Khi bật PK: thấy người chơi là đánh người, ưu tiên người "
                            "trưởng nhóm đang đánh, rồi kẻ đang đánh mình, rồi kẻ đang đánh người cùng nhóm, rồi "
                            "người chơi gần nhất; không đánh người cùng nhóm, nhân vật trong auto, danh sách đồng "
                            "minh ở trên và danh sách mời ở tab Nhóm; không còn người chơi thì đánh quái như thường. "
                            "Auto tạm ngừng đánh lúc dịch chuyển / chuyển sinh. Nếu "
                            "ChickenAuto cũng đang tự đánh nhân vật này thì tắt bên đó để hai auto không giành "
                            "mục tiêu.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(8, 0))

    def nap_form_chien_dau(self, ten):
        cd = cai_dat_chien_dau(cau_hinh.cua_nhan_vat(ten))
        self.nhan_chien_dau.configure(text=f"Cài đặt chiến đấu cho: {ten}")
        for khoa in CAC_O_TICH_CHIEN_DAU:
            self.bien_cd[khoa].set(cd[khoa])
        for khoa in ("ban_kinh", "so_quai_lua", "ten_key", "phan_tram_buff", "phan_tram_an_don", "hoan_hi_toi_thieu"):
            self.bien_cd[khoa].set(str(cd[khoa]))
        for phim, bien in self.bien_phim_skill.items():
            bien.set(phim in cd["cac_phim_skill"])
        self.bien_cd["x"].set(str(cd["diem"]["x"]))
        self.bien_cd["y"].set(str(cd["diem"]["y"]))
        self.map_diem_dang_sua = cd["diem"]["map"]
        self.nhan_map_diem.configure(text=self.map_diem_dang_sua)
        self.hien_khung_buff()

    def hien_khung_buff(self):
        """Khung Buff máu chỉ hiện khi nhân vật đang chọn là Nga My (hoặc đã bật buff, để còn tắt được)."""
        luong = self.luong_dang_chon()
        hien = (luong is not None and luong.mon_phai == MON_PHAI_NGA_MY) \
            or (self.ten_dang_sua is not None and self.bien_cd["buff_mau"].get())
        if hien and not self.khung_buff.winfo_manager():
            self.khung_buff.pack(fill="x", pady=(6, 0), after=self.khung_tu_danh)
        elif not hien and self.khung_buff.winfo_manager():
            self.khung_buff.pack_forget()

    def _nap_ds_key(self):
        ds = sorted({luong.ten for luong in self.cac_luong.values() if luong.ten and luong.ten != self.ten_dang_sua},
                    key=chuan_hoa)
        hien_tai = self.bien_cd["ten_key"].get()
        if hien_tai and hien_tai not in ds:
            ds.insert(0, hien_tai)
        self.chon_key.configure(values=[""] + ds)

    def lay_vi_tri_chien_dau(self):
        luong = self.luong_dang_chon()
        tt = self.thong_tin.get(luong.hwnd) if luong else None
        if tt is None:
            messagebox.showinfo("Lấy vị trí", "Chọn một nhân vật đang ở trong game")
            return
        self.bien_cd["x"].set(str(tt["x"]))
        self.bien_cd["y"].set(str(tt["y"]))
        self.map_diem_dang_sua = tt["map"]
        self.nhan_map_diem.configure(text=tt["map"])

    def doc_form_chien_dau(self):
        """Đọc tab Chiến đấu thành cài đặt chiến đấu. Sai dữ liệu thì báo ValueError."""
        cd = cai_dat_chien_dau(cau_hinh.cua_nhan_vat(self.ten_dang_sua))
        for khoa in CAC_O_TICH_CHIEN_DAU:
            cd[khoa] = self.bien_cd[khoa].get()
        cd["ban_kinh"] = so_nguyen(self.bien_cd["ban_kinh"].get(), "Bán kính")
        if not 1 <= cd["ban_kinh"] <= 60:
            raise ValueError("Bán kính phải từ 1 tới 60")
        cd["so_quai_lua"] = so_nguyen(self.bien_cd["so_quai_lua"].get(), "Số quái lùa")
        if not 1 <= cd["so_quai_lua"] <= 20:
            raise ValueError("Số quái lùa phải từ 1 tới 20")
        cd["ten_key"] = self.bien_cd["ten_key"].get().strip()
        cd["phan_tram_buff"] = so_nguyen(self.bien_cd["phan_tram_buff"].get(), "Phần trăm máu để buff")
        if not 1 <= cd["phan_tram_buff"] <= 99:
            raise ValueError("Phần trăm máu để buff phải từ 1 tới 99")
        cd["phan_tram_an_don"] = so_nguyen(self.bien_cd["phan_tram_an_don"].get(), "Phần trăm máu để ẩn độn")
        if not 1 <= cd["phan_tram_an_don"] <= 99:
            raise ValueError("Phần trăm máu để ẩn độn phải từ 1 tới 99")
        cd["hoan_hi_toi_thieu"] = so_nguyen(self.bien_cd["hoan_hi_toi_thieu"].get(), "Hoan hỉ tối thiểu của trân thú")
        if not 1 <= cd["hoan_hi_toi_thieu"] <= 100:
            raise ValueError("Hoan hỉ tối thiểu của trân thú phải từ 1 tới 100")
        cd["cac_phim_skill"] = [phim for phim, bien in self.bien_phim_skill.items() if bien.get()]
        diem = {"map": self.map_diem_dang_sua, "x": so_nguyen(self.bien_cd["x"].get(), "Tọa độ x"),
                "y": so_nguyen(self.bien_cd["y"].get(), "Tọa độ y")}
        if cd["quanh_diem"] and not diem["map"]:
            luong = self.luong_dang_chon()
            tt = self.thong_tin.get(luong.hwnd) if luong else None
            if tt is None:
                raise ValueError("Bấm \"Lấy vị trí hiện tại\" để chọn điểm đánh quanh")
            diem["map"] = tt["map"]
        cd["diem"] = diem
        return cd

    def luu_chien_dau(self):
        if self.ten_dang_sua is None:
            for bien in list(self.bien_cd.values()) + list(self.bien_phim_skill.values()):
                if isinstance(bien, tk.BooleanVar):
                    bien.set(False)
            messagebox.showinfo("Chiến đấu", "Chọn một nhân vật trong danh sách trước")
            return
        try:
            cd = self.doc_form_chien_dau()
        except ValueError as loi:
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        cai_dat = cau_hinh.cua_nhan_vat(self.ten_dang_sua)
        cu = cai_dat_chien_dau(cai_dat)
        cai_dat["chien_dau"] = cd
        cau_hinh.dat_nhan_vat(self.ten_dang_sua, cai_dat)
        self.nap_form_chien_dau(self.ten_dang_sua)
        if cd == cu:
            return
        if (cd["buff_mau"], cd["phan_tram_buff"]) != (cu["buff_mau"], cu["phan_tram_buff"]):
            self.in_log(f"{self.ten_dang_sua}: " + (f"BẬT buff máu khi đồng đội / mình dưới {cd['phan_tram_buff']}%"
                                                    if cd["buff_mau"] else "TẮT buff máu")
                        + (" - chưa tích ô Auto nên chưa buff" if cd["buff_mau"] and not cai_dat["bat_auto"] else ""))
        if (cd["an_don"], cd["phan_tram_an_don"]) != (cu["an_don"], cu["phan_tram_an_don"]):
            self.in_log(f"{self.ten_dang_sua}: " + (f"BẬT dùng {TEN_KY_NANG_AN_DON} khi bị PK mà máu dưới "
                                                    f"{cd['phan_tram_an_don']}%" if cd["an_don"]
                                                    else f"TẮT dùng {TEN_KY_NANG_AN_DON}"))
        if (cd["xuat_chien_tran_thu"], cd["hoan_hi_toi_thieu"]) != (cu["xuat_chien_tran_thu"], cu["hoan_hi_toi_thieu"]):
            self.in_log(f"{self.ten_dang_sua}: " + (f"BẬT tự xuất chiến trân thú, hoan hỉ dưới "
                                                    f"{cd['hoan_hi_toi_thieu']} thì cho ăn" if cd["xuat_chien_tran_thu"]
                                                    else "TẮT tự xuất chiến trân thú")
                        + (" - chưa tích ô Auto nên chưa chạy" if cd["xuat_chien_tran_thu"] and not cai_dat["bat_auto"]
                           else ""))
        if cd["tu_tang_cap"] != cu["tu_tang_cap"]:
            self.in_log(f"{self.ten_dang_sua}: {'BẬT' if cd['tu_tang_cap'] else 'TẮT'} tự động tăng cấp")
        rieng = ("buff_mau", "phan_tram_buff", "an_don", "phan_tram_an_don", "xuat_chien_tran_thu",
                 "hoan_hi_toi_thieu", "tu_tang_cap")
        if dict(cd, **{khoa: cu[khoa] for khoa in rieng}) == cu:
            return
        chi_tiet = [f"bán kính {cd['ban_kinh']}"]
        if cd["quanh_diem"]:
            chi_tiet.append(f"quanh [{cd['diem']['x']},{cd['diem']['y']}] ở {cd['diem']['map']}")
        if cd["dung_f1"]:
            chi_tiet.append("dùng F1")
        if cd["cac_phim_skill"]:
            chi_tiet.append("kỹ năng " + " ".join(f"F{phim}" for phim in cd["cac_phim_skill"]))
        if cd["lua_quai"]:
            chi_tiet.append(f"lùa {cd['so_quai_lua']} con")
        if cd["danh_theo_key"]:
            chi_tiet.append(f"đánh theo Key {cd['ten_key'] or '(trưởng nhóm)'}")
        if cd["dung_skill_pet"]:
            chi_tiet.append("dùng skill pet")
        if cd["uu_tien_nguoi_choi"]:
            chi_tiet.append("bật PK thì ưu tiên đánh người chơi")
        if cd["xuong_thu"]:
            chi_tiet.append("xuống thú cưỡi khi đánh")
        if cd["nhat_do"]:
            chi_tiet.append("tự nhặt túi đồ khi không có Càn Khôn Hồ")
        self.in_log(f"{self.ten_dang_sua}: {'BẬT' if cd['bat'] else 'TẮT'} tự đánh"
                    + (" (" + ", ".join(chi_tiet) + ")" if cd["bat"] else "")
                    + (" - chưa tích ô Auto nên chưa đánh" if cd["bat"] and not cai_dat["bat_auto"] else ""))

    def ap_dung_chien_dau_tat_ca(self):
        """Chép cách đánh (không gồm bật/tắt và điểm Quanh) cho mọi nhân vật và làm mặc định cho nhân vật mới."""
        if self.ten_dang_sua is None:
            return
        try:
            cd = self.doc_form_chien_dau()
        except ValueError as loi:
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        chung = {khoa: cd[khoa] for khoa in CAC_KHOA_CHIEN_DAU_CHUNG}
        cai_dat = cau_hinh.cua_nhan_vat(self.ten_dang_sua)
        cai_dat["chien_dau"] = cd
        cau_hinh.dat_nhan_vat(self.ten_dang_sua, cai_dat)
        def chep(_ten, cai_dat):
            cai_dat["chien_dau"] = dict(cai_dat_chien_dau(cai_dat), **chung)
            return cai_dat
        cau_hinh.thay_tat_ca_nhan_vat(chep)
        mac_dinh = cau_hinh.mac_dinh()
        mac_dinh["chien_dau"] = dict(cai_dat_chien_dau({}), **chung)
        cau_hinh.dat_mac_dinh(mac_dinh)
        self.in_log("Đã áp dụng cách đánh cho tất cả nhân vật và làm mặc định cho nhân vật mới")

    def _tao_tab_auto_click(self, so_tay):
        tab = self._tab_cuon(so_tay, "Auto click")
        self.nhan_auto_click = ttk.Label(tab, text="Chọn một nhân vật trong danh sách để chỉnh cài đặt",
                                         font=("Segoe UI", 9, "bold"))
        self.nhan_auto_click.pack(anchor="w")
        khung = ttk.LabelFrame(tab, text="Tự bấm phím (ô trên thanh kỹ năng)", padding=8)
        khung.pack(fill="x", pady=(4, 0))
        self.bien_ac_bat = tk.BooleanVar()
        self.bien_ac_giay = tk.StringVar()
        self.bien_ac_phim = {phim: tk.BooleanVar() for phim in auto_click.CAC_PHIM}
        ttk.Checkbutton(khung, text="Bật auto click", variable=self.bien_ac_bat,
                        command=self.luu_auto_click).grid(row=0, column=0, columnspan=len(auto_click.CAC_PHIM),
                                                          sticky="w")
        for cot, phim in enumerate(auto_click.CAC_PHIM):
            ttk.Checkbutton(khung, text=f"F{phim}", variable=self.bien_ac_phim[phim],
                            command=self.luu_auto_click).grid(row=1, column=cot, sticky="w", padx=(0, 6), pady=(6, 0))
        dong = ttk.Frame(khung)
        dong.grid(row=2, column=0, columnspan=len(auto_click.CAC_PHIM), sticky="w", pady=(6, 0))
        ttk.Label(dong, text="Bấm mỗi").pack(side="left")
        ttk.Spinbox(dong, from_=auto_click.GIAY_TOI_THIEU, to=auto_click.GIAY_TOI_DA, increment=0.1,
                    textvariable=self.bien_ac_giay, width=5).pack(side="left", padx=4)
        ttk.Label(dong, text="giây").pack(side="left")

        nut = ttk.Frame(tab)
        nut.pack(fill="x", pady=(8, 0))
        ttk.Button(nut, text="Lưu", command=self.luu_auto_click).pack(side="left")
        ttk.Button(nut, text="Áp dụng cho tất cả", command=self.ap_dung_auto_click_tat_ca).pack(side="left", padx=4)
        ttk.Label(tab, text="Chỉ bấm khi nhân vật được tích ô Auto trong danh sách phía trên. Mỗi lượt bấm tất cả "
                            "các ô đã tích, đứng yên hay đang đánh đều bấm; ô chưa hồi hoặc đang vận công thì game "
                            f"tự bỏ qua. Nhanh nhất {auto_click.GIAY_TOI_THIEU} giây một lượt. Tạm ngừng lúc dịch "
                            "chuyển / chuyển sinh / chết. Nếu tab Chiến đấu cũng tự dùng kỹ năng thì nên bỏ tích các "
                            "ô trùng ở một bên.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(8, 0))

    def _tao_tab_pho_ban(self, so_tay):
        tab = self._tab_cuon(so_tay, "Phó bản")
        self.nhan_pho_ban = ttk.Label(tab, text="Chọn một nhân vật trong danh sách để chỉnh cài đặt Phiêu Miễu Phong",
                                      font=("Segoe UI", 9, "bold"))
        self.nhan_pho_ban.pack(anchor="w")
        khung = ttk.LabelFrame(tab, text="Xoay vòng tài khoản & Phiêu Miễu Phong", padding=8)
        khung.pack(fill="x", pady=(4, 0))
        xv_chung = cau_hinh.chung()
        dong = ttk.Frame(khung)
        dong.pack(fill="x")
        ttk.Label(dong, text="Số người mỗi nhóm").pack(side="left")
        self.bien_xv_so_nguoi = tk.StringVar(value=str(xv_chung.get("so_nguoi_mot_nhom", 4)))
        ttk.Spinbox(dong, from_=1, to=SO_NGUOI_MOT_NHOM_TOI_DA, textvariable=self.bien_xv_so_nguoi, width=4,
                    state="readonly").pack(side="left", padx=4)
        ttk.Label(dong, text="Số round mỗi nhóm").pack(side="left", padx=(8, 0))
        self.bien_xv_so_round = tk.StringVar(value=str(xv_chung.get("xv_so_round", 3)))
        ttk.Spinbox(dong, from_=1, to=SO_ROUND_TOI_DA, textvariable=self.bien_xv_so_round, width=4,
                    state="readonly").pack(side="left", padx=4)
        ttk.Separator(khung, orient="horizontal").pack(fill="x", pady=(8, 6))
        ttk.Label(khung, text="Phiêu Miễu Phong (cài theo nhân vật đang chọn ở danh sách trên)",
                  font=("Segoe UI", 9, "bold")).pack(anchor="w")
        self.bien_pmp_bat = tk.BooleanVar()
        self.bien_pmp_so_vong = tk.StringVar()
        self.bien_pmp_sat_tinh = tk.BooleanVar()
        ttk.Checkbutton(khung, text="Đi Phiêu Miễu Phong khi xoay vòng (chỉ chạy sau khi bấm Bắt đầu bên dưới)",
                        variable=self.bien_pmp_bat, command=self.luu_pho_ban).pack(anchor="w", pady=(4, 0))
        ttk.Checkbutton(khung, text="Hết lượt Phiêu Miễu Phong thì đi Thập Nhị Sát Tinh (NPC SÁT TINH ở Lạc Dương)",
                        variable=self.bien_pmp_sat_tinh, command=self.luu_pho_ban).pack(anchor="w")
        dong = ttk.Frame(khung)
        dong.pack(fill="x", pady=(6, 0))
        ttk.Label(dong, text="Số vòng mỗi ngày").pack(side="left")
        ttk.Spinbox(dong, from_=0, to=99, textvariable=self.bien_pmp_so_vong, width=5).pack(side="left", padx=4)
        ttk.Label(dong, text="(0 = đi tới khi game báo hết lượt)").pack(side="left")
        self.bien_pmp_truong_khong_danh = tk.BooleanVar()
        ttk.Checkbutton(khung, text="Đi tổ đội: đội trưởng luôn cưỡi thú, không đánh ở Phiêu Miễu Phong "
                                    "(chỉ đội viên đánh, đi ải nhanh hơn)",
                        variable=self.bien_pmp_truong_khong_danh, command=self.luu_pho_ban).pack(anchor="w",
                                                                                                 pady=(6, 0))
        nen = ttk.Style().lookup("TFrame", "background") or "SystemButtonFace"
        self.nhan_pmp_hom_nay = tk.Text(khung, height=2, width=60, relief="flat", borderwidth=0,
                                        highlightthickness=0, background=nen, font=("Segoe UI", 9),
                                        cursor="arrow", state="disabled")
        self.nhan_pmp_hom_nay.tag_configure("so", foreground="green", font=("Segoe UI", 9, "bold"))
        self.nhan_pmp_hom_nay.pack(anchor="w", pady=(6, 0))
        nut_pmp = ttk.Frame(khung)
        nut_pmp.pack(fill="x", pady=(4, 0))
        ttk.Button(nut_pmp, text="Lưu PMP", command=self.luu_pho_ban).pack(side="left")
        ttk.Button(nut_pmp, text="Áp dụng PMP cho tất cả", command=self.ap_dung_pho_ban_tat_ca).pack(side="left", padx=4)
        ttk.Button(nut_pmp, text="Đặt lại lượt hôm nay", command=self.dat_lai_pho_ban).pack(side="left")
        ttk.Separator(khung, orient="horizontal").pack(fill="x", pady=(8, 6))
        self.bien_xv_chi_sat_tinh = tk.BooleanVar(value=bool(xv_chung.get("xv_chi_sat_tinh")))
        ttk.Checkbutton(khung, text="Chỉ đi Sát Tinh (bỏ qua Phiêu Miễu Phong, vẫn xoay vòng tài khoản)",
                        variable=self.bien_xv_chi_sat_tinh,
                        command=self.luu_cai_dat_xoay_vong).pack(anchor="w")
        self.bien_xv_test = tk.BooleanVar(value=bool(xv_chung.get("xv_test")))
        ttk.Checkbutton(khung, text="Chế độ test (1 round, 1 lượt PMP — hoặc 1 lượt Sát Tinh nếu chỉ Sát Tinh — "
                                    "giao dịch rồi dừng)",
                        variable=self.bien_xv_test, command=self.luu_cai_dat_xoay_vong).pack(anchor="w", pady=(4, 0))
        self.bien_xv_chuyen_do = tk.BooleanVar(value=bool(xv_chung.get("xv_chuyen_do", True)))
        ttk.Checkbutton(khung, text="Đội viên giao dịch đồ mới nhặt cho trưởng nhóm khi xong phó bản\n"
                                    "(xong Sát Tinh thì giao dịch ở Lạc Dương, không chuyển tiền)",
                        variable=self.bien_xv_chuyen_do, command=self.luu_cai_dat_xoay_vong).pack(anchor="w")
        self.bien_xv_ngay_moi = tk.BooleanVar(value=bool(xv_chung.get("xv_ngay_moi", True)))
        ttk.Checkbutton(khung, text="Qua 0h: làm mới danh sách và chạy lại từ nhóm 1 (hết danh sách thì chờ 0h);\n"
                                    "nhóm đang trong phó bản thì đi nốt vòng đó, ra khỏi phó bản mới quay lại",
                        variable=self.bien_xv_ngay_moi, command=self.luu_cai_dat_xoay_vong).pack(anchor="w")
        self.bien_xv_so_nguoi.trace_add("write", lambda *_: self.luu_cai_dat_xoay_vong())
        self.bien_xv_so_round.trace_add("write", lambda *_: self.luu_cai_dat_xoay_vong())
        dong = ttk.Frame(khung)
        dong.pack(fill="x", pady=(8, 0))
        self.nut_xoay_vong = ttk.Button(dong, text="Bắt đầu", command=self.bat_tat_xoay_vong)
        self.nut_xoay_vong.pack(side="left")
        ttk.Button(dong, text="Chạy lại từ đầu", command=self.chay_lai_xoay_vong).pack(side="left", padx=4)
        ttk.Button(dong, text="Làm mới danh sách", command=self.lam_moi_danh_sach_xoay_vong).pack(side="left")
        ttk.Button(dong, text="Giao dịch ngay", command=self.giao_dich_ngay_xoay_vong).pack(side="left", padx=4)
        ttk.Button(dong, text="Nhóm tiếp theo", command=self.nhom_tiep_theo_xoay_vong).pack(side="left")
        ttk.Button(dong, text="Test nhóm online", command=self.test_nhom_online_xoay_vong).pack(side="left", padx=4)
        self.nhan_xoay_vong = ttk.Label(dong, text="")
        self.nhan_xoay_vong.pack(side="left", padx=8)
        ttk.Label(khung, text="Tích XV ở tab Tài khoản, cấu hình PMP (nên «Áp dụng cho tất cả»), rồi bấm Bắt đầu — "
                              "PMP/Sát Tinh không tự chạy khi chỉ bật ô Auto train.\n"
                              "Xoay vòng: N tài khoản XV là một nhóm (acc đầu là trưởng), mỗi nhóm chạy số round đã chọn; "
                              "mỗi round dùng caychay10 / 100 / 1000. Mỗi round đi PMP (nếu bật) rồi Sát Tinh tới hết lượt, "
                              "giao dịch ở Lạc Dương, sang round tiếp. Acc train và acc chính online không bị tắt game.\n"
                              "PMP: về Đại Lý → Di Chuyển → Trình Thanh Sương, 4 ải + boss; đội trưởng dẫn đội viên đã tích "
                              "Auto + Đi PMP. Hết PMP thì Sát Tinh tại NPC SÁT TINH.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(6, 0))

        self._tao_khung_ac_tac(tab)

        cd = cai_dat_giao_acc_chinh()
        khung = ttk.LabelFrame(tab, text="Giao dịch cho acc chính", padding=8)
        khung.pack(fill="x", pady=(8, 0))
        self.bien_gac = {}
        for hang, (khoa, nhan, an) in enumerate((("tai_khoan", "Tài khoản", False), ("mat_khau", "Mật khẩu", True),
                                                 ("nhan_vat", "Tên nhân vật", False),
                                                 ("loai_tru", "Không giao (cách nhau dấu phẩy)", False))):
            ttk.Label(khung, text=nhan).grid(row=hang, column=0, sticky="w", pady=1)
            self.bien_gac[khoa] = tk.StringVar(value=cd[khoa])
            ttk.Entry(khung, textvariable=self.bien_gac[khoa], width=50 if khoa == "loai_tru" else 24,
                      show="*" if an else "").grid(row=hang, column=1, sticky="w", padx=4, pady=1)
        self.bien_gac_hom_nay = tk.BooleanVar(value=cd["chi_hom_nay"])
        ttk.Checkbutton(khung, text="Chỉ nhân vật đã đi phó bản hôm nay (bỏ tích: mọi nhân vật round đã tạo)",
                        variable=self.bien_gac_hom_nay).grid(row=4, column=0, columnspan=2, sticky="w", pady=(4, 0))
        self.bien_gac_tat_ca_pb = tk.BooleanVar(value=cd.get("tat_ca_pho_ban", False))
        ttk.Checkbutton(khung, text="Tất cả acc phó bản (mọi acc trong nhóm, từng nhân vật round;\n"
                                    "không có đồ thì thoát game, sang acc tiếp theo)",
                        variable=self.bien_gac_tat_ca_pb).grid(row=5, column=0, columnspan=2, sticky="w", pady=(2, 0))
        dong = ttk.Frame(khung)
        dong.grid(row=6, column=0, columnspan=2, sticky="w", pady=(6, 0))
        self.nut_giao_acc_chinh = ttk.Button(dong, text="Bắt đầu", command=self.bat_tat_giao_acc_chinh)
        self.nut_giao_acc_chinh.pack(side="left")
        ttk.Button(dong, text="Làm lại từ đầu", command=self.dat_lai_giao_acc_chinh).pack(side="left", padx=4)
        self.nhan_giao_acc_chinh = ttk.Label(dong, text=self._mo_ta_tien_trinh_gac())
        self.nhan_giao_acc_chinh.pack(side="left", padx=8)
        ttk.Label(khung, text="Bấm Bắt đầu: mọi client đang trong game về chọn máy chủ (giữ client, không mở game mới). "
                              "Đăng nhập acc chính (đứng ở NPC Tân Thủ, Đại Lý), rồi lần lượt đăng nhập acc phó bản "
                              "(mặc định: chỉ trưởng nhóm; tích «Tất cả acc phó bản»: mọi tài khoản trong nhóm xoay vòng, "
                              "từng nhân vật round 1-3). Kiểm tra túi Đạo cụ + Nguyên liệu: có đồ thì giao cho acc chính "
                              "(trừ ô Không giao, đồ khóa bỏ qua), không có đồ thì thoát game và sang acc tiếp (chế độ "
                              "tất cả acc). Túi acc chính còn dưới 5 ô trống thì cất vào Thiên Cơ Cẩm Nang / Thương khố. "
                              "Cả hai đầy thì dừng. Bấm Dừng rồi Bắt đầu đi tiếp nhân vật chưa xong (tiến trình theo ngày).",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").grid(row=7, column=0, columnspan=2,
                                                                                  sticky="w", pady=(6, 0))

    def _tao_khung_ac_tac(self, tab):
        khung = ttk.LabelFrame(tab, text="Sự kiện Ác Tặc (cài chung — chỉ đội trưởng trong nhóm game đi)", padding=8)
        khung.pack(fill="x", pady=(8, 0))
        self.bien_at_bat = tk.BooleanVar()
        self.bien_at_bo_02h = tk.BooleanVar()
        self.bien_at_route = tk.StringVar(value="moi")
        self.bien_at_ten_quai = tk.StringVar(value="Ác Tặc")
        self.bien_at_chay_pp = tk.BooleanVar(value=False)
        self.bien_at_cho_party = tk.BooleanVar(value=True)
        self.bien_at_tu_tim = tk.BooleanVar(value=True)
        self.bien_at_dung_gauto = tk.BooleanVar(value=False)
        self.bien_at_duong_dan_gauto = tk.StringVar(value="")
        self.bien_at_phut_gauto = tk.StringVar(value="30")
        self.at_thu_tu = list(cau_hinh.CAC_MAP_AC_TAC)
        self.at_da_chon = set(cau_hinh.CAC_MAP_AC_TAC)
        ttk.Checkbutton(khung, text="Đi Ác Tặc trong khung giờ (ưu tiên hơn PMP / Sát Tinh: tới giờ thì bỏ dở phó bản, "
                                    "về Đại Lý rồi đi Ác Tặc)",
                        variable=self.bien_at_bat, command=self.luu_ac_tac).pack(anchor="w")
        ttk.Checkbutton(khung, text="Bỏ khung 02:00-03:00 (chỉ đi các khung 13h, 15h, 17h, 19h, 21h)",
                        variable=self.bien_at_bo_02h, command=self.luu_ac_tac).pack(anchor="w")
        dong = ttk.Frame(khung)
        dong.pack(fill="x", pady=(4, 0))
        ttk.Label(dong, text="Đường tuần tra").pack(side="left")
        ttk.Radiobutton(dong, text="Mới", value="moi", variable=self.bien_at_route,
                        command=self.luu_ac_tac).pack(side="left", padx=(4, 0))
        ttk.Radiobutton(dong, text="Kiểu cũ", value="cu", variable=self.bien_at_route,
                        command=self.luu_ac_tac).pack(side="left", padx=(4, 0))
        dong2 = ttk.Frame(khung)
        dong2.pack(fill="x", pady=(4, 0))
        ttk.Label(dong2, text="Chạy tìm (mặc định, như GAuto)", foreground="gray").pack(side="left")
        ttk.Checkbutton(dong2, text="Chạy pathpoints (tắt = chạy tìm quanh mốc ACTAC)",
                        variable=self.bien_at_chay_pp, command=self.luu_ac_tac).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(dong2, text="Chờ party (chống kẹt)",
                        variable=self.bien_at_cho_party, command=self.luu_ac_tac).pack(side="left", padx=(8, 0))
        ttk.Checkbutton(dong2, text="Tự tìm (quét rộng hơn)",
                        variable=self.bien_at_tu_tim, command=self.luu_ac_tac).pack(side="left", padx=(8, 0))
        dong_g = ttk.Frame(khung)
        dong_g.pack(fill="x", pady=(6, 0))
        ttk.Checkbutton(dong_g, text="Đi Ác Tặc qua GAuto — tới giờ tự tích Ác Tặc trên cửa sổ GAuto, mỗi khung chạy",
                        variable=self.bien_at_dung_gauto, command=self.luu_ac_tac).pack(anchor="w")
        dong_g2 = ttk.Frame(khung)
        dong_g2.pack(fill="x", pady=(2, 0))
        ttk.Label(dong_g2, text="Đường dẫn GAuto (.exe)").pack(side="left")
        ttk.Entry(dong_g2, textvariable=self.bien_at_duong_dan_gauto, width=40).pack(side="left", padx=4)
        ttk.Button(dong_g2, text="Chọn...", command=self.chon_duong_dan_gauto).pack(side="left")
        ttk.Button(dong_g2, text="Test GAuto", command=self.test_gauto).pack(side="left", padx=(4, 0))
        ttk.Label(dong_g2, text="Phút / khung").pack(side="left", padx=(8, 0))
        ttk.Spinbox(dong_g2, from_=5, to=120, width=4, textvariable=self.bien_at_phut_gauto,
                    command=self.luu_ac_tac).pack(side="left", padx=4)
        ttk.Label(khung, text="GAuto: mở GAuto (GAuto_2025) và đăng nhập đội trưởng trước; GAuto tự chạy quyền Admin nên "
                              "AutoHoc cũng phải chạy quyền Admin. Tới giờ AutoHoc đưa đội tới map đầu danh sách ☑, chọn "
                              "map đó trên GAuto (bấm chuột thật ~1 giây) rồi tích Ác Tặc cho dòng đội trưởng; hết «Phút "
                              "/ khung» thì bỏ tích, đi tiếp phó bản. GAuto không có Tây Hồ. Bấm «Test GAuto» để thử.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(2, 0))
        ttk.Label(dong, text="Tên quái (cách nhau dấu phẩy)").pack(side="left", padx=(12, 0))
        ttk.Entry(dong, textvariable=self.bien_at_ten_quai, width=20).pack(side="left", padx=4)
        dong = ttk.Frame(khung)
        dong.pack(fill="x", pady=(6, 0))
        self.ds_at_map = tk.Listbox(dong, height=len(self.at_thu_tu), width=32, exportselection=False,
                                    activestyle="none")
        self.ds_at_map.pack(side="left")
        self.ds_at_map.bind("<Double-Button-1>", lambda _e: self.bat_tat_map_ac_tac())
        cot = ttk.Frame(dong)
        cot.pack(side="left", padx=6, anchor="n")
        ttk.Button(cot, text="Chọn / bỏ", command=self.bat_tat_map_ac_tac).pack(fill="x")
        ttk.Button(cot, text="Lên", command=lambda: self.doi_thu_tu_map_ac_tac(-1)).pack(fill="x", pady=(4, 0))
        ttk.Button(cot, text="Xuống", command=lambda: self.doi_thu_tu_map_ac_tac(1)).pack(fill="x", pady=(4, 0))
        self._ve_ds_map_ac_tac()
        nut = ttk.Frame(khung)
        nut.pack(fill="x", pady=(6, 0))
        ttk.Button(nut, text="Lưu Ác Tặc", command=self.luu_ac_tac).pack(side="left")
        ttk.Button(nut, text="Áp dụng Ác Tặc cho tất cả", command=self.ap_dung_ac_tac_tat_ca).pack(side="left", padx=4)
        ttk.Label(khung, text="Khung giờ: 02-03h, 13-14h, 15-16h, 17-18h, 19-20h, 21-22h. Đi các map đã tích (☑) theo "
                              "thứ tự trên xuống: về Đại Lý → NPC Di Chuyển (Tây Hồ, Thái Hồ qua Tô Châu; Đôn Hoàng, "
                              "Tung Sơn qua Lạc Dương, rồi chạy qua cổng map) → tuần tra theo điểm, gom Ác Tặc. Hết Ác Tặc thì sang map sau; "
                              "hết giờ hoặc đi hết map thì về thành, đi tiếp PMP / Sát Tinh. Đi tổ đội: đội trưởng dẫn "
                              "đường, đội viên chỉ cần bật Auto để theo và đánh. "
                              "3 phút không thấy NPC/quái trên một map thì tự sang map kế (thứ tự danh sách).",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(6, 0))
        self.nap_form_ac_tac()

    def _ve_ds_map_ac_tac(self, chon=None):
        ds = self.ds_at_map
        ds.delete(0, "end")
        for ten in self.at_thu_tu:
            hub = HUB_CUA_MAP_AC_TAC.get(ten) or MAP_DAI_LY
            ds.insert("end", f"{O_BAT if ten in self.at_da_chon else O_TAT} {ten} ({hub})")
        if chon is not None:
            ds.selection_set(chon)
            ds.see(chon)

    def bat_tat_map_ac_tac(self):
        chon = self.ds_at_map.curselection()
        if not chon:
            return
        ten = self.at_thu_tu[chon[0]]
        if ten in self.at_da_chon:
            self.at_da_chon.discard(ten)
        else:
            self.at_da_chon.add(ten)
        self._ve_ds_map_ac_tac(chon[0])
        self.luu_ac_tac()

    def doi_thu_tu_map_ac_tac(self, buoc):
        chon = self.ds_at_map.curselection()
        if not chon:
            return
        i, j = chon[0], chon[0] + buoc
        if not 0 <= j < len(self.at_thu_tu):
            return
        self.at_thu_tu[i], self.at_thu_tu[j] = self.at_thu_tu[j], self.at_thu_tu[i]
        self._ve_ds_map_ac_tac(j)
        self.luu_ac_tac()

    def nap_form_ac_tac(self, cai_dat=None):
        at = cai_dat_ac_tac()
        self.bien_at_bat.set(bool(at["bat"]))
        self.bien_at_bo_02h.set(bool(at["bo_khung_02h"]))
        self.bien_at_route.set("cu" if at.get("route") == "cu" else "moi")
        self.bien_at_ten_quai.set(at.get("ten_quai") or "Ác Tặc")
        self.bien_at_chay_pp.set(bool(at.get("chay_pathpoints", False)))
        self.bien_at_cho_party.set(bool(at.get("cho_party", True)))
        self.bien_at_tu_tim.set(bool(at.get("tu_tim", True)))
        self.bien_at_dung_gauto.set(bool(at.get("dung_gauto")))
        self.bien_at_duong_dan_gauto.set(at.get("duong_dan_gauto") or "")
        self.bien_at_phut_gauto.set(str(at.get("phut_gauto") or 30))
        thu_tu = [m for m in at.get("thu_tu_map") or () if m in cau_hinh.CAC_MAP_AC_TAC]
        self.at_thu_tu = list(dict.fromkeys(thu_tu + list(cau_hinh.CAC_MAP_AC_TAC)))
        self.at_da_chon = {m for m in at.get("map_uu_tien") or () if m in cau_hinh.CAC_MAP_AC_TAC}
        self._ve_ds_map_ac_tac()

    def doc_form_ac_tac(self):
        ten_quai = ", ".join(t.strip() for t in self.bien_at_ten_quai.get().split(",") if t.strip()) or "Ác Tặc"
        try:
            phut_g = int(self.bien_at_phut_gauto.get().strip() or "30")
        except ValueError:
            phut_g = 30
        phut_g = max(5, min(phut_g, 120))
        return {"bat": self.bien_at_bat.get(), "bo_khung_02h": self.bien_at_bo_02h.get(),
                "route": self.bien_at_route.get(), "ten_quai": ten_quai,
                "chay_pathpoints": self.bien_at_chay_pp.get(),
                "cho_party": self.bien_at_cho_party.get(),
                "tu_tim": self.bien_at_tu_tim.get(),
                "dung_gauto": self.bien_at_dung_gauto.get(),
                "duong_dan_gauto": self.bien_at_duong_dan_gauto.get().strip(),
                "phut_gauto": phut_g,
                "map_uu_tien": [m for m in self.at_thu_tu if m in self.at_da_chon],
                "thu_tu_map": list(self.at_thu_tu)}

    def luu_ac_tac(self):
        gia_tri = self.doc_form_ac_tac()
        cu = cai_dat_ac_tac()
        mac_dinh = cau_hinh.mac_dinh()
        mac_dinh["ac_tac"] = dict(cai_dat_ac_tac(), **gia_tri)
        cau_hinh.dat_mac_dinh(mac_dinh)
        if gia_tri["bat"] != cu["bat"]:
            self.in_log(f"{'BẬT' if gia_tri['bat'] else 'TẮT'} {MO_TA_AC_TAC} (đội trưởng trong nhóm game)"
                        + (f" ({mo_ta_lich(gia_tri)}; map: {', '.join(gia_tri['map_uu_tien']) or 'chưa chọn'})"
                           if gia_tri["bat"] else ""))
            if gia_tri["bat"] and not gia_tri["map_uu_tien"]:
                messagebox.showwarning("Ác Tặc", "Chưa tích map Ác Tặc nào")
            if gia_tri["bat"] and gia_tri["dung_gauto"] and not gia_tri["duong_dan_gauto"]:
                messagebox.showwarning("Ác Tặc", "Bật GAuto nhưng chưa nhập đường dẫn GAuto_2025.exe")

    def ap_dung_ac_tac_tat_ca(self):
        self.luu_ac_tac()
        self.in_log("Đã lưu cài đặt Ác Tặc chung (đội trưởng)")

    def _mo_ta_tien_trinh_gac(self):
        tt = cai_dat_giao_acc_chinh().get("tien_trinh") or {}
        if tt.get("ngay") != date.today().isoformat() or not tt.get("da_xong"):
            return ""
        return f"Hôm nay đã giao xong: {', '.join(tt['da_xong'])}"

    def _luu_giao_acc_chinh(self):
        luu_giao_acc_chinh(**{k: v.get().strip() for k, v in self.bien_gac.items()},
                           chi_hom_nay=self.bien_gac_hom_nay.get(),
                           tat_ca_pho_ban=self.bien_gac_tat_ca_pb.get())

    def dat_lai_giao_acc_chinh(self):
        if self.luong_giao_acc_chinh and self.luong_giao_acc_chinh.is_alive():
            messagebox.showinfo("Giao dịch cho acc chính", "Đang chạy, bấm Dừng trước")
            return
        if messagebox.askyesno("Giao dịch cho acc chính", "Xóa tiến trình hôm nay, lần sau bắt đầu lại từ trưởng "
                                                          "nhóm đầu tiên?"):
            luu_giao_acc_chinh(tien_trinh={})
            self.nhan_giao_acc_chinh.configure(text="")

    def bat_tat_giao_acc_chinh(self):
        if self.luong_giao_acc_chinh and self.luong_giao_acc_chinh.is_alive():
            self.luong_giao_acc_chinh.dung.set()
            self.nhan_giao_acc_chinh.configure(text="Đang dừng...")
            self.in_log("[Giao acc chính] Dừng theo yêu cầu")
            return
        self._luu_giao_acc_chinh()
        if not all(self.bien_gac[k].get().strip() for k in ("tai_khoan", "mat_khau", "nhan_vat")):
            messagebox.showinfo("Giao dịch cho acc chính", "Điền tài khoản, mật khẩu, tên nhân vật của acc chính")
            return
        if self.luong_xoay_vong and self.luong_xoay_vong.is_alive():
            messagebox.showinfo("Giao dịch cho acc chính", "Đang xoay vòng tài khoản, chờ xong hoặc dừng trước")
            return
        if self.luong_tao_nv and self.luong_tao_nv.is_alive():
            messagebox.showinfo("Giao dịch cho acc chính", "Đang tạo nhân vật ở tab Tạo nhân vật, chờ xong hoặc "
                                                            "dừng trước")
            return
        self.luong_giao_acc_chinh = LuongGiaoAccChinh(self.hang_doi)
        self.luong_giao_acc_chinh.start()
        cac_tk = self.luong_giao_acc_chinh.cac_tai_khoan()
        for ten, luong in self.cac_luong_dang_nhap.items():
            if ten.lower() in cac_tk:
                luong.dung.set()
        self.nut_giao_acc_chinh.configure(text="Dừng")

    def xoay_vong_sau_giao_acc_chinh(self):
        """Giao acc chính xong: chờ luồng giao thoát hẳn (trả client, bật lại phó bản) rồi tự bấm Bắt đầu xoay vòng."""
        if self.luong_giao_acc_chinh and self.luong_giao_acc_chinh.is_alive():
            self.root.after(500, self.xoay_vong_sau_giao_acc_chinh)
            return
        if self.luong_xoay_vong and self.luong_xoay_vong.is_alive():
            return
        if not cac_tai_khoan_dang_tich():
            self.in_log("[Giao acc chính] Xong — chưa tích XV tài khoản nào nên không tự xoay vòng phó bản")
            return
        self.in_log("[Giao acc chính] Xong — tự bắt đầu lại xoay vòng phó bản")
        self.bat_tat_xoay_vong()

    def luu_cai_dat_xoay_vong(self):
        """Ghi tab Xoay vòng vào cau_hinh.json (gọi khi đổi ô / checkbox và khi thoát AutoHoc)."""
        try:
            so_nguoi = int(self.bien_xv_so_nguoi.get().strip())
            so_round = int(self.bien_xv_so_round.get().strip())
            if not (1 <= so_nguoi <= SO_NGUOI_MOT_NHOM_TOI_DA and 1 <= so_round <= SO_ROUND_TOI_DA):
                return False
        except (ValueError, AttributeError):
            return False
        cau_hinh.dat_chung({"so_nguoi_mot_nhom": so_nguoi, "xv_so_round": so_round,
                            "xv_chi_sat_tinh": self.bien_xv_chi_sat_tinh.get(),
                            "xv_test": self.bien_xv_test.get(), "xv_chuyen_do": self.bien_xv_chuyen_do.get(),
                            "xv_ngay_moi": self.bien_xv_ngay_moi.get()})
        return True

    def chay_lai_xoay_vong(self):
        """Dừng xoay vòng đang chạy (nếu có), chờ dừng hẳn rồi bắt đầu lại từ tài khoản đầu tiên trong danh sách."""
        if not (self.luong_xoay_vong and self.luong_xoay_vong.is_alive()):
            xoa_xv_tien_trinh()
            self.in_log("[Xoay vòng] Chạy lại từ nhóm 1, tài khoản đầu tiên trong danh sách")
            self.bat_tat_xoay_vong(tu_nhom_1=True)
            return
        if not messagebox.askyesno("Xoay vòng", "Dừng xoay vòng đang chạy rồi bắt đầu lại từ nhóm 1, tài khoản đầu "
                                                "tiên trong danh sách? Nhân vật đã hết lượt hôm nay được bỏ qua."):
            return
        self.luong_xoay_vong.dung.set()
        self.luong_xoay_vong.tat_pho_ban_ngay()
        self.nhan_xoay_vong.configure(text="Đang dừng để chạy lại từ tài khoản đầu tiên...")
        self.in_log("[Xoay vòng] Chạy lại từ đầu: dừng luồng đang chạy, xong thì bắt đầu lại từ tài khoản đầu tiên")

        def cho_dung():
            if self.luong_xoay_vong and self.luong_xoay_vong.is_alive():
                self.root.after(500, cho_dung)
                return
            xoa_xv_tien_trinh()
            self.bat_tat_xoay_vong(tu_nhom_1=True)
        cho_dung()

    def lam_moi_danh_sach_xoay_vong(self):
        """Xóa bộ đếm phó bản hôm nay của mọi nhân vật (PMP, Sơ, Sát Tinh) rồi xoay vòng lại từ nhóm 1."""
        dang_chay = bool(self.luong_xoay_vong and self.luong_xoay_vong.is_alive())
        if not messagebox.askyesno("Xoay vòng", "Xóa toàn bộ lịch sử phó bản hôm nay (số vòng PMP, Sơ, Sát Tinh, "
                                                "hết lượt) của mọi nhân vật rồi bắt đầu lại từ nhóm 1?"
                                   + ("\nXoay vòng đang chạy sẽ dừng trước." if dang_chay else "")
                                   + "\nNhân vật thật sự đã hết lượt trong game thì NPC vẫn báo hết lượt."):
            return

        def xoa_va_chay():
            if self.luong_xoay_vong and self.luong_xoay_vong.is_alive():
                self.root.after(500, xoa_va_chay)
                return

            def xoa(cai_dat):
                pmp = cai_dat.get("pho_ban_pmp")
                if pmp:
                    pmp["hom_nay"] = {}
            ds = cau_hinh.cac_nhan_vat()
            cau_hinh.cap_nhat_tat_ca_nhan_vat(lambda cai_dat: xoa(cai_dat) or True)
            xoa_xv_tien_trinh()
            self.in_log(f"[Xoay vòng] Làm mới danh sách: đã xóa lịch sử phó bản hôm nay của {len(ds)} nhân vật, "
                        "bắt đầu lại từ nhóm 1")
            self.bat_tat_xoay_vong(tu_nhom_1=True)

        if dang_chay:
            self.luong_xoay_vong.dung.set()
            self.luong_xoay_vong.tat_pho_ban_ngay()
            self.nhan_xoay_vong.configure(text="Đang dừng để làm mới danh sách...")
            self.in_log("[Xoay vòng] Làm mới danh sách: dừng luồng đang chạy")
        xoa_va_chay()

    def nhom_tiep_theo_xoay_vong(self):
        """Round đang kẹt: đội viên giao đồ cho trưởng nhóm rồi xoay sang round / nhóm kế tiếp."""
        luong = self.luong_xoay_vong
        if not (luong and luong.is_alive()):
            messagebox.showinfo("Nhóm tiếp theo", "Xoay vòng chưa chạy")
            return
        if not messagebox.askyesno("Nhóm tiếp theo", "Kết thúc round đang đi: đội viên còn trong game giao đồ cho "
                                                     "trưởng nhóm, rồi xoay sang round / nhóm kế tiếp?"):
            return
        if not luong.nhom_tiep_theo():
            messagebox.showinfo("Nhóm tiếp theo", "Xoay vòng đang đăng nhập / tạo nhân vật / giao dịch cuối round, "
                                                  "bấm lại sau")
            return
        self.in_log("[Xoay vòng] Nhóm tiếp theo: kết thúc round đang đi, giao dịch cho trưởng nhóm rồi sang "
                    "round / nhóm kế tiếp")

    def giao_dich_ngay_xoay_vong(self):
        """
        Đội viên giao đồ mới nhặt cho trưởng nhóm ngay, không chờ xong phó bản. Xoay vòng đang chạy thì nhờ luồng xoay
        vòng làm (nó đang điều khiển nhóm); không thì tự tìm nhóm trong game của các nhân vật đang chạy trong auto.
        """
        luong = self.luong_xoay_vong
        if luong and luong.is_alive():
            if not luong.giao_dich_ngay():
                messagebox.showinfo("Giao dịch ngay", "Xoay vòng đang đăng nhập / lập nhóm / giao dịch cuối round, "
                                                      "bấm lại sau khi nhóm đã đi phó bản")
                return
            self.in_log("[Xoay vòng] Giao dịch ngay: nhóm đang đi phó bản sẽ tạm dừng, đội viên giao đồ cho trưởng "
                        "nhóm rồi đi tiếp")
            return
        if self.luong_giao_dich_ngay and self.luong_giao_dich_ngay.is_alive():
            messagebox.showinfo("Giao dịch ngay", "Đang giao dịch, chờ xong rồi bấm lại")
            return
        if self.luong_giao_acc_chinh and self.luong_giao_acc_chinh.is_alive():
            messagebox.showinfo("Giao dịch ngay", "Đang giao dịch cho acc chính, chờ xong hoặc dừng trước")
            return
        self.luong_giao_dich_ngay = LuongGiaoDichNgay(list(self.cac_luong.values()), self.hang_doi)
        self.luong_giao_dich_ngay.start()

    def test_nhom_online_xoay_vong(self):
        """Đi thử 1 lượt phó bản với các nhân vật đang trong game, không đăng xuất để ghép đúng nhóm xoay vòng."""
        if self.luong_xoay_vong and self.luong_xoay_vong.is_alive():
            messagebox.showinfo("Test nhóm online", "Xoay vòng đang chạy, bấm Dừng trước")
            return
        if self.luong_tao_nv and self.luong_tao_nv.is_alive():
            messagebox.showinfo("Test nhóm online", "Đang tạo nhân vật ở tab Tạo nhân vật, chờ xong hoặc dừng trước")
            return
        if self.luong_giao_acc_chinh and self.luong_giao_acc_chinh.is_alive():
            messagebox.showinfo("Test nhóm online", "Đang giao dịch cho acc chính, chờ xong hoặc dừng trước")
            return
        if self._chan_neu_chua_kich_hoat():
            return
        nhom = nhom_dang_online()
        if not nhom:
            messagebox.showinfo("Test nhóm online", "Không có nhân vật nào đang trong game (ngoài acc chính / acc train)")
            return
        chi_st = self.bien_xv_chi_sat_tinh.get()
        luot = "1 lượt Sát Tinh" if chi_st else "1 lượt PMP"
        if not messagebox.askyesno(
                "Test nhóm online",
                f"Đi thử {luot} với {len(nhom)} nhân vật đang trong game:\n{', '.join(tv.ten for tv in nhom)}\n\n"
                f"Trưởng nhóm: {nhom[0].ten}\n\nKhông đăng xuất / đăng nhập lại. Xong lượt thì về thành"
                f"{', đội viên giao đồ cho trưởng nhóm' if self.bien_xv_chuyen_do.get() else ''} rồi dừng."):
            return
        self.luong_xoay_vong = LuongXoayVong(self.hang_doi, 1, True, self.bien_xv_chuyen_do.get(), False, chi_st,
                                             nhom_online=nhom)
        dat_phien_xoay_vong(True)
        self.luong_xoay_vong.start()
        cac_tk = self.luong_xoay_vong.cac_tai_khoan()
        for ten, luong in self.cac_luong_dang_nhap.items():
            if ten.lower() in cac_tk:
                luong.dung.set()
        self.nut_xoay_vong.configure(text="Dừng")

    def bat_tat_xoay_vong(self, tu_nhom_1=False):
        if self.luong_xoay_vong and self.luong_xoay_vong.is_alive():
            dat_phien_xoay_vong(False)
            self.luong_xoay_vong.dung.set()
            self.luong_xoay_vong.tat_pho_ban_ngay()
            self.nhan_xoay_vong.configure(text="Đang dừng...")
            self.in_log("[Xoay vòng] Dừng theo yêu cầu (tắt Phó bản nhóm đang đi)")
            return
        if self.luong_tao_nv and self.luong_tao_nv.is_alive():
            messagebox.showinfo("Xoay vòng", "Đang tạo nhân vật ở tab Tạo nhân vật, chờ xong hoặc dừng trước")
            return
        if self.luong_giao_acc_chinh and self.luong_giao_acc_chinh.is_alive():
            messagebox.showinfo("Xoay vòng", "Đang giao dịch cho acc chính, chờ xong hoặc dừng trước")
            return
        if not cac_tai_khoan_dang_tich():
            messagebox.showinfo("Xoay vòng", "Chưa tích XV (xoay vòng) tài khoản phó bản nào ở tab Tài khoản")
            return
        if not self.luu_cai_dat_xoay_vong():
            messagebox.showerror("Xoay vòng",
                                 f"Số người mỗi nhóm (1–{SO_NGUOI_MOT_NHOM_TOI_DA}) và số round (1–{SO_ROUND_TOI_DA}) "
                                 "phải là số hợp lệ")
            return
        if self._chan_neu_chua_kich_hoat():
            return
        try:
            so_mot_nhom = int(self.bien_xv_so_nguoi.get())
        except (ValueError, tk.TclError):
            so_mot_nhom = 4
        gioi_ip = proxy_mang.so_ip_toi_da()
        if so_mot_nhom > gioi_ip:
            if not messagebox.askyesno(
                    "Xoay vòng — giới hạn server",
                    f"Server thường giới hạn khoảng {gioi_ip} tài khoản online theo proxy đã cấu hình "
                    f"(số proxy × acc/IP).\n\n"
                    f"Bạn đặt {so_mot_nhom} người/nhóm — acc vượt giới hạn hay bị «Đã ngắt kết nối».\n\n"
                    "Vẫn bắt đầu?"):
                return
        self.luong_xoay_vong = LuongXoayVong(self.hang_doi, int(self.bien_xv_so_round.get()),
                                             self.bien_xv_test.get(), self.bien_xv_chuyen_do.get(),
                                             self.bien_xv_ngay_moi.get(), self.bien_xv_chi_sat_tinh.get(),
                                             tu_nhom_1=tu_nhom_1)
        dat_phien_xoay_vong(True)
        self.luong_xoay_vong.start()
        cac_tk = self.luong_xoay_vong.cac_tai_khoan()
        for ten, luong in self.cac_luong_dang_nhap.items():
            if ten.lower() in cac_tk:
                luong.dung.set()
        self.nut_xoay_vong.configure(text="Dừng")

    def nap_form_pho_ban(self, ten):
        cai_dat = cau_hinh.cua_nhan_vat(ten)
        pmp = cai_dat_pmp(cai_dat)
        self.nhan_pho_ban.configure(text=f"Cài đặt phó bản cho: {ten}")
        self.bien_pmp_bat.set(pmp["bat"])
        self.bien_pmp_so_vong.set(str(pmp["so_vong"]))
        self.bien_pmp_sat_tinh.set(pmp["sat_tinh"])
        self.bien_pmp_truong_khong_danh.set(pmp["truong_khong_danh"])
        self.nap_form_ac_tac(cai_dat)
        self.hien_hom_nay(cai_dat)

    def hien_hom_nay(self, cai_dat):
        o = self.nhan_pmp_hom_nay
        o.configure(state="normal")
        o.delete("1.0", "end")
        for chu, la_so in cac_doan_hom_nay(cai_dat):
            o.insert("end", chu, ("so",) if la_so else ())
        o.configure(state="disabled")

    def doc_form_pho_ban(self):
        """Các ô của tab Phó bản (không gồm bộ đếm hôm nay), None nếu chưa chọn nhân vật / nhập sai."""
        if self.ten_dang_sua is None:
            self.bien_pmp_bat.set(False)
            messagebox.showinfo("Phó bản", "Chọn một nhân vật trong danh sách trước")
            return None
        try:
            so_vong = int(self.bien_pmp_so_vong.get().strip())
            if not 0 <= so_vong <= 99:
                raise ValueError
        except ValueError:
            messagebox.showerror("Cài đặt chưa đúng", "Số vòng mỗi ngày phải là số từ 0 tới 99")
            return None
        return {"bat": self.bien_pmp_bat.get(), "so_vong": so_vong, "sat_tinh": self.bien_pmp_sat_tinh.get(),
                "truong_khong_danh": self.bien_pmp_truong_khong_danh.get()}

    def ap_dung_pho_ban_tat_ca(self):
        gia_tri = self.doc_form_pho_ban()
        if gia_tri is None:
            return

        def sua(cai_dat):
            cai_dat["pho_ban_pmp"] = dict(cai_dat_pmp(cai_dat), **gia_tri)
            if gia_tri["bat"]:
                cai_dat["bat_chuyen_sinh"] = False
        cau_hinh.cap_nhat_tat_ca_nhan_vat(lambda cai_dat: sua(cai_dat) or True)
        if gia_tri["bat"]:
            self.ve_lai_bang()
            self.in_log("Bật phó bản cho tất cả nhân vật: đã TẮT auto chuyển sinh của mọi nhân vật")
        mac_dinh = cau_hinh.mac_dinh()
        mac_dinh["pho_ban_pmp"] = dict(cai_dat_pmp(mac_dinh), **gia_tri,
                                       hom_nay=dict(cau_hinh.MAC_DINH_PHO_BAN_PMP["hom_nay"]))
        cau_hinh.dat_mac_dinh(mac_dinh)
        self.nap_form_pho_ban(self.ten_dang_sua)
        self.in_log("Đã áp dụng cài đặt phó bản cho tất cả nhân vật và làm mặc định cho nhân vật mới")

    def luu_pho_ban(self):
        gia_tri = self.doc_form_pho_ban()
        if gia_tri is None:
            return
        bat = gia_tri["bat"]
        cu = cau_hinh.cua_nhan_vat(self.ten_dang_sua)
        tat_chuyen_sinh = bat and not cai_dat_pmp(cu)["bat"] and cu["bat_chuyen_sinh"]

        def sua(cai_dat):
            cai_dat["pho_ban_pmp"] = dict(cai_dat_pmp(cai_dat), **gia_tri)
            if tat_chuyen_sinh:
                cai_dat["bat_chuyen_sinh"] = False
        cau_hinh.sua_nhan_vat(self.ten_dang_sua, sua)
        moi = cau_hinh.cua_nhan_vat(self.ten_dang_sua)
        self.nap_form_pho_ban(self.ten_dang_sua)
        self.ve_lai_bang()
        if bat != cai_dat_pmp(cu)["bat"]:
            self.in_log(f"{'BẬT' if bat else 'TẮT'} tự đi Phiêu Miễu Phong cho {self.ten_dang_sua}"
                        + (", TẮT auto chuyển sinh" if tat_chuyen_sinh else "")
                        + (" - chạy khi bấm Bắt đầu xoay vòng (tab Phó bản)" if bat else ""))
        else:
            self.in_log(f"Đã lưu cài đặt phó bản của {self.ten_dang_sua}")

    def dat_lai_pho_ban(self):
        if self.ten_dang_sua is None:
            return

        def sua(cai_dat):
            cai_dat["pho_ban_pmp"] = dict(cai_dat_pmp(cai_dat), hom_nay=dict(cau_hinh.MAC_DINH_PHO_BAN_PMP["hom_nay"]))
        cau_hinh.sua_nhan_vat(self.ten_dang_sua, sua)
        for luong in self.cac_luong.values():
            if luong.ten == self.ten_dang_sua:
                luong.pho_ban.nghi_den = 0.0
        self.nap_form_pho_ban(self.ten_dang_sua)
        self.in_log(f"Đã đặt lại lượt Phiêu Miễu Phong và Sát Tinh hôm nay của {self.ten_dang_sua}")

    def nap_form_auto_click(self, ten):
        ac = auto_click.cai_dat_auto_click(cau_hinh.cua_nhan_vat(ten))
        self.nhan_auto_click.configure(text=f"Cài đặt auto click cho: {ten}")
        self.bien_ac_bat.set(ac["bat"])
        self.bien_ac_giay.set(f"{ac['giay']:g}")
        for phim, bien in self.bien_ac_phim.items():
            bien.set(phim in ac["cac_phim"])

    def doc_form_auto_click(self):
        """Đọc tab Auto click. Sai dữ liệu thì báo ValueError."""
        try:
            giay = float(self.bien_ac_giay.get().strip().replace(",", "."))
        except ValueError:
            raise ValueError("Số giây phải là số, vd. 0.5") from None
        if not auto_click.GIAY_TOI_THIEU <= giay <= auto_click.GIAY_TOI_DA:
            raise ValueError(f"Số giây phải từ {auto_click.GIAY_TOI_THIEU} tới {auto_click.GIAY_TOI_DA:g}")
        return {"bat": self.bien_ac_bat.get(), "giay": giay,
                "cac_phim": [phim for phim, bien in self.bien_ac_phim.items() if bien.get()]}

    def luu_auto_click(self):
        if self.ten_dang_sua is None:
            self.bien_ac_bat.set(False)
            for bien in self.bien_ac_phim.values():
                bien.set(False)
            messagebox.showinfo("Auto click", "Chọn một nhân vật trong danh sách trước")
            return
        try:
            ac = self.doc_form_auto_click()
        except ValueError as loi:
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        cai_dat = cau_hinh.cua_nhan_vat(self.ten_dang_sua)
        cu = auto_click.cai_dat_auto_click(cai_dat)
        cai_dat["auto_click"] = ac
        cau_hinh.dat_nhan_vat(self.ten_dang_sua, cai_dat)
        self.nap_form_auto_click(self.ten_dang_sua)
        if auto_click.cai_dat_auto_click(cai_dat) == cu:
            return
        phim = " ".join(f"F{p}" for p in ac["cac_phim"]) or "chưa tích phím nào"
        self.in_log(f"{self.ten_dang_sua}: {'BẬT' if ac['bat'] else 'TẮT'} auto click"
                    + (f" ({phim}, mỗi {ac['giay']:g} giây)" if ac["bat"] else "")
                    + (" - chưa tích ô Auto nên chưa bấm" if ac["bat"] and not cai_dat["bat_auto"] else ""))

    def ap_dung_auto_click_tat_ca(self):
        """Chép phím và số giây (không gồm bật/tắt) cho mọi nhân vật và làm mặc định cho nhân vật mới."""
        if self.ten_dang_sua is None:
            return
        try:
            ac = self.doc_form_auto_click()
        except ValueError as loi:
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        chung = {"cac_phim": ac["cac_phim"], "giay": ac["giay"]}
        cai_dat = cau_hinh.cua_nhan_vat(self.ten_dang_sua)
        cai_dat["auto_click"] = ac
        cau_hinh.dat_nhan_vat(self.ten_dang_sua, cai_dat)
        def chep(_ten, cai_dat):
            cai_dat["auto_click"] = dict(auto_click.cai_dat_auto_click(cai_dat), **chung)
            return cai_dat
        cau_hinh.thay_tat_ca_nhan_vat(chep)
        mac_dinh = cau_hinh.mac_dinh()
        mac_dinh["auto_click"] = dict(auto_click.cai_dat_auto_click({}), **chung)
        cau_hinh.dat_mac_dinh(mac_dinh)
        self.in_log("Đã áp dụng phím auto click cho tất cả nhân vật và làm mặc định cho nhân vật mới")

    def _tao_tab_tien_ich(self, so_tay):
        tab = self._tab_cuon(so_tay, "Tiện ích")
        khung = ttk.LabelFrame(tab, text="Vứt rác", padding=8)
        khung.pack(fill="x")
        chung = cau_hinh.chung()
        self.bien_vut_rac = tk.BooleanVar(value=chung["bat_vut_rac"])
        ttk.Checkbutton(khung, text="Tự vứt rác cho mọi nhân vật trong auto", variable=self.bien_vut_rac,
                        command=self.luu_vut_rac).grid(row=0, column=0, columnspan=3, sticky="w")
        dong = ttk.Frame(khung)
        dong.grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Label(dong, text="Kiểm tra túi mỗi (giây)").pack(side="left")
        self.bien_giay_vut_rac = tk.StringVar(value=str(chung["giay_giua_moi_lan_vut_rac"]))
        ttk.Spinbox(dong, from_=10, to=3600, textvariable=self.bien_giay_vut_rac, width=6).pack(side="left", padx=8)
        dong = ttk.Frame(khung)
        dong.grid(row=2, column=0, columnspan=3, sticky="w", pady=(4, 0))
        self.bien_vut_duoi_sao = tk.BooleanVar(value=chung["vut_trang_bi_duoi_sao"])
        ttk.Checkbutton(dong, text="Vứt cả trang bị dưới", variable=self.bien_vut_duoi_sao,
                        command=self.luu_vut_rac).pack(side="left")
        self.bien_so_sao = tk.StringVar(value=str(chung["so_sao_toi_thieu"]))
        ttk.Spinbox(dong, from_=1, to=9, textvariable=self.bien_so_sao, width=4).pack(side="left", padx=4)
        ttk.Label(dong, text="sao").pack(side="left")
        ttk.Button(dong, text="Lưu", command=self.luu_vut_rac).pack(side="left", padx=(8, 0))
        nut = ttk.Frame(khung)
        nut.grid(row=3, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Button(nut, text="Xem rác (ghi ra nhật ký)", command=lambda: self.gui_yeu_cau_rac("xem")).pack(side="left")
        ttk.Button(nut, text="Vứt rác ngay", command=lambda: self.gui_yeu_cau_rac("vut")).pack(side="left", padx=6)
        ttk.Label(khung, text="Rác là trang bị có dòng \"Chưa giám định\" khi rê chuột xem, và (nếu tích) trang bị "
                              "đã giám định có số sao ít hơn số đã chọn (vd. chọn 9 thì vứt 0-8 sao, giữ 9 sao). "
                              "Trang bị không có sao, Phi Hoàng Thạch và vật phẩm khác không bị đụng tới. "
                              "Vứt là tiêu hủy luôn, không lấy lại được - bấm \"Xem rác\" trước.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))

        khung = ttk.LabelFrame(tab, text="Auto duyệt", padding=8)
        khung.pack(fill="x", pady=(8, 0))
        self.bien_tu_duyet = tk.BooleanVar(value=chung["tu_duyet_popup"])
        ttk.Checkbutton(khung, text="Auto duyệt: popup cần xác nhận hiện lên thì tự bấm Duyệt",
                        variable=self.bien_tu_duyet, command=self.luu_tu_duyet).pack(anchor="w")
        self.bien_nhan_ty_thi = tk.BooleanVar(value=chung["tu_nhan_ty_thi"])
        ttk.Checkbutton(khung, text="Nhận cả lời mời tỷ thí (tỷ thí có thể bị giết)",
                        variable=self.bien_nhan_ty_thi, command=self.luu_tu_duyet).pack(anchor="w", padx=(20, 0))
        ttk.Label(khung, text="Áp dụng cho mọi cửa sổ game: mang trang bị sẽ bị khóa, tiêu hủy vật phẩm, lời mời "
                              "vào nhóm / Kéo / cưỡi chung / kết bạn, và mọi hộp hỏi khác - kể cả thoát game, mất "
                              "kết nối (đóng game), phóng sinh trân thú, bỏ nhiệm vụ, rời bang. Tự duyệt được ghi "
                              "vào nhật ký.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(6, 0))

        khung = ttk.LabelFrame(tab, text="Tự mua và dùng vật phẩm", padding=8)
        khung.pack(fill="x", pady=(8, 0))
        self.bien_tu_mua_dung = {}
        for khoa, lop in (("tu_dung_x2", TuDungX2), ("tu_dung_can_khon_ho", TuDungCanKhonHo)):
            self.bien_tu_mua_dung[khoa] = tk.BooleanVar(value=chung[khoa])
            ttk.Checkbutton(khung, text=f"Hết {lop.TEN_HIEU_UNG} thì tự dùng {lop.TEN_VAT_PHAM}, "
                                        f"túi hết thì tự mua {lop.SO_MUA_MOI_LAN} cái",
                            variable=self.bien_tu_mua_dung[khoa],
                            command=lambda khoa=khoa, lop=lop: self.luu_tu_mua_dung(khoa, lop)).pack(anchor="w")
        ttk.Label(khung, text="Áp dụng cho nhân vật đang bật Auto, kiểm tra mỗi 30 giây; hết hiệu ứng thì dùng 1 cái. "
                              "Thời gian x2 đọc ở dòng cuối bảng nhiệm vụ (Alt+Q), Càn Khôn Hồ đọc ở buff trên nhân "
                              "vật. Mua ở Tiệm KNB (nút Nguyên Bảo trên minimap) mục Nhiệt Mại Thương Phẩm, chỉ mua "
                              "khi giá 0 KNB và ô \"Xác nhận mua\" không tích.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(6, 0))

        khung = ttk.LabelFrame(tab, text="Auto chat Thế giới", padding=8)
        khung.pack(fill="x", pady=(8, 0))
        self.bien_chat = tk.BooleanVar(value=chung["chat_the_gioi"])
        ttk.Checkbutton(khung, text="Tự chat kênh Thế giới", variable=self.bien_chat,
                        command=self.luu_chat_the_gioi).pack(anchor="w")
        dong = ttk.Frame(khung)
        dong.pack(fill="x", pady=(4, 0))
        ttk.Label(dong, text="Nội dung").pack(side="left")
        self.bien_noi_dung_chat = tk.StringVar(value=chung["noi_dung_chat_the_gioi"])
        o_chat = ttk.Entry(dong, textvariable=self.bien_noi_dung_chat)
        o_chat.pack(side="left", fill="x", expand=True, padx=(8, 0))
        o_chat.bind("<Return>", lambda _su_kien: self.luu_chat_the_gioi())
        dong = ttk.Frame(khung)
        dong.pack(fill="x", pady=(4, 0))
        ttk.Label(dong, text="Chat mỗi (giây)").pack(side="left")
        self.bien_giay_chat = tk.StringVar(value=str(chung["giay_chat_the_gioi"]))
        ttk.Spinbox(dong, from_=GIAY_CHAT_TOI_THIEU, to=3600, textvariable=self.bien_giay_chat,
                    width=6).pack(side="left", padx=8)
        ttk.Label(dong, text="Nhân vật").pack(side="left")
        self.bien_nv_chat = tk.StringVar(value=chung["nhan_vat_chat_the_gioi"] or MOI_NHAN_VAT_CHAT)
        self.chon_nv_chat = ttk.Combobox(dong, textvariable=self.bien_nv_chat, width=28, state="readonly",
                                         postcommand=self._nap_ds_nv_chat)
        self.chon_nv_chat.pack(side="left", padx=6)
        ttk.Button(dong, text="Lưu", command=self.luu_chat_the_gioi).pack(side="left")
        ttk.Label(khung, text="Tích vào là gửi ngay một lần, sau đó cứ đủ số giây lại gửi lại. Chọn một nhân vật thì "
                              "chỉ nhân vật đó chat, không thì mọi nhân vật đang bật Auto cùng chat. Chat dồn quá "
                              "nhanh (vd. vừa chat tay) thì game báo \"không nên nói chuyện với tốc độ quá nhanh\" và "
                              "bỏ lượt đó.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(6, 0))

    def _nap_ds_nv_chat(self):
        ds = [luong.ten for luong in self.cac_luong.values() if luong.ten]
        hien_tai = self.bien_nv_chat.get()
        if hien_tai not in ds and hien_tai != MOI_NHAN_VAT_CHAT:
            ds.insert(0, hien_tai)
        self.chon_nv_chat.configure(values=[MOI_NHAN_VAT_CHAT] + ds)

    def luu_chat_the_gioi(self):
        chung = cau_hinh.chung()
        bat = self.bien_chat.get()
        noi_dung = self.bien_noi_dung_chat.get().strip()
        try:
            giay = so_nguyen(self.bien_giay_chat.get(), "Số giây giữa hai lần chat")
            if giay < GIAY_CHAT_TOI_THIEU:
                raise ValueError(f"Số giây giữa hai lần chat phải từ {GIAY_CHAT_TOI_THIEU} trở lên")
            if bat and not noi_dung:
                raise ValueError("Nhập nội dung chat trước khi bật")
            ma_lua_chat(noi_dung)
        except (ValueError, LoiChat) as loi:
            if bat and not chung["chat_the_gioi"]:
                self.bien_chat.set(False)
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        nhan_vat = "" if self.bien_nv_chat.get() == MOI_NHAN_VAT_CHAT else self.bien_nv_chat.get()
        cau_hinh.dat_chung({"chat_the_gioi": bat, "noi_dung_chat_the_gioi": noi_dung, "giay_chat_the_gioi": giay,
                            "nhan_vat_chat_the_gioi": nhan_vat})
        if bat and not chung["chat_the_gioi"]:
            for luong in self.cac_luong.values():
                luong.luc_chat_the_gioi = 0.0
        self.in_log(f"{'BẬT' if bat else 'TẮT'} auto chat Thế giới"
                    + (f" mỗi {giay} giây ({nhan_vat or MOI_NHAN_VAT_CHAT.lower()}): {noi_dung}" if bat else ""))

    def luu_tu_mua_dung(self, khoa, lop):
        bat = self.bien_tu_mua_dung[khoa].get()
        cau_hinh.dat_chung({khoa: bat})
        self.in_log(f"{'BẬT' if bat else 'TẮT'} tự dùng {lop.TEN_VAT_PHAM} khi hết {lop.TEN_HIEU_UNG}")

    def luu_tu_duyet_tu_tab_tai_khoan(self):
        bat = self.bien_tu_duyet_popup_tk.get()
        cau_hinh.dat_chung({"tu_duyet_popup": bat})
        if hasattr(self, "bien_tu_duyet"):
            self.bien_tu_duyet.set(bat)
        self.in_log(f"{'BẬT' if bat else 'TẮT'} tự duyệt popup (mọi cửa sổ game)")

    def luu_tu_duyet(self):
        bat, ty_thi = self.bien_tu_duyet.get(), self.bien_nhan_ty_thi.get()
        cau_hinh.dat_chung({"tu_duyet_popup": bat, "tu_nhan_ty_thi": ty_thi})
        if hasattr(self, "bien_tu_duyet_popup_tk"):
            self.bien_tu_duyet_popup_tk.set(bat)
        self.in_log(f"{'BẬT' if bat else 'TẮT'} auto duyệt popup"
                    + (", nhận cả lời mời tỷ thí" if bat and ty_thi else ""))

    def luu_vut_rac(self):
        try:
            giay = so_nguyen(self.bien_giay_vut_rac.get(), "Số giây kiểm tra túi")
            if giay < 10:
                raise ValueError("Số giây kiểm tra túi phải từ 10 trở lên")
            so_sao = so_nguyen(self.bien_so_sao.get(), "Số sao")
            if not 1 <= so_sao <= 9:
                raise ValueError("Số sao phải từ 1 tới 9")
        except ValueError as loi:
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        bat = self.bien_vut_rac.get()
        duoi_sao = self.bien_vut_duoi_sao.get()
        cau_hinh.dat_chung({"bat_vut_rac": bat, "giay_giua_moi_lan_vut_rac": giay,
                            "vut_trang_bi_duoi_sao": duoi_sao, "so_sao_toi_thieu": so_sao})
        self.in_log(f"{'BẬT' if bat else 'TẮT'} tự vứt rác" + (f", kiểm tra túi mỗi {giay} giây" if bat else "")
                    + (f", vứt cả trang bị dưới {so_sao} sao" if duoi_sao else ", chỉ vứt đồ Chưa giám định"))

    def gui_yeu_cau_rac(self, viec):
        cac_luong = [luong for luong in self.cac_luong.values() if luong.ten]
        if not cac_luong:
            messagebox.showinfo("Vứt rác", "Chưa có nhân vật nào trong game")
            return
        if viec == "vut" and not messagebox.askyesno(
                "Vứt rác", f"Tiêu hủy mọi trang bị Chưa giám định"
                           + (f" và trang bị dưới {cau_hinh.chung()['so_sao_toi_thieu']} sao"
                              if cau_hinh.chung()["vut_trang_bi_duoi_sao"] else "")
                           + f" trong túi của {len(cac_luong)} nhân vật?"):
            return
        for luong in cac_luong:
            luong.yeu_cau_rac = viec
        self.in_log(("Xem" if viec == "xem" else "Vứt") + " rác ở lượt kiểm tra tới của: "
                    + ", ".join(luong.ten for luong in cac_luong))

    def _tao_tab_tao_nhan_vat(self, so_tay):
        tab = self._tab_cuon(so_tay, "Tạo nhân vật")
        khung = ttk.LabelFrame(tab, text="Mã kiểm tra", padding=8)
        khung.pack(fill="x")
        self.bien_nhap_ma_tao_nv = tk.BooleanVar(value=cau_hinh.chung()["tu_nhap_ma_tao_nhan_vat"])
        ttk.Checkbutton(khung, text="Tự nhập mã kiểm tra khi bấm Tạo nhân vật", variable=self.bien_nhap_ma_tao_nv,
                        command=self.luu_nhap_ma_tao_nv).pack(anchor="w")
        ttk.Label(khung, text="Ở màn hình chọn nhân vật, bấm Tạo nhân vật trong game: hộp mã kiểm tra hiện lên thì "
                              "auto đọc 4 số trong ảnh và nhập giúp, đọc sai thì tự thử ảnh khác tới khi vào được "
                              "màn hình tạo nhân vật (thường 5-30 giây). Mã kiểm tra lúc đăng nhập chỉnh ở tab "
                              "Tài khoản.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(6, 0))

        tuy_chon = cau_hinh.doc_tai_khoan()["tao_nhan_vat_moi"]
        khung = ttk.LabelFrame(tab, text="Tài khoản mới: tạo nhân vật + nhận đồ tân thủ", padding=8)
        khung.pack(fill="x", pady=(8, 0))
        ttk.Label(khung, text="Mỗi dòng một tài khoản: tài_khoản mật_khẩu").pack(anchor="w")
        self.o_ds_tao_nv = tk.Text(khung, height=5, width=40, font=("Consolas", 9))
        self.o_ds_tao_nv.pack(fill="x", pady=(2, 0))
        self.o_ds_tao_nv.insert("1.0", tuy_chon["danh_sach"])

        dong = ttk.Frame(khung)
        dong.pack(fill="x", pady=(6, 0))
        ttk.Label(dong, text="Số nhân vật mỗi tài khoản").pack(side="left")
        self.bien_so_nv_moi = tk.StringVar(value=str(tuy_chon["so_nhan_vat"]))
        ttk.Spinbox(dong, from_=1, to=3, width=3, textvariable=self.bien_so_nv_moi).pack(side="left", padx=4)
        ttk.Label(dong, text="(vd. caychay10 -> caychay10, caychay100, caychay1000)",
                  foreground="gray").pack(side="left", padx=(8, 0))

        self.bien_nhan_do_tan_thu = tk.BooleanVar(value=tuy_chon["nhan_do_tan_thu"])
        ttk.Checkbutton(khung, text="Vào từng nhân vật nhận đồ tân thủ (Thiên Long, Vàng + ĐT, mang đồ, dùng Hộp "
                                    "Point, cộng Nội Lực)", variable=self.bien_nhan_do_tan_thu).pack(anchor="w",
                                                                                                    pady=(4, 0))
        dong = ttk.Frame(khung)
        dong.pack(fill="x", pady=(6, 0))
        self.nut_tao_nv = ttk.Button(dong, text="Bắt đầu", command=self.bat_tat_tao_nv)
        self.nut_tao_nv.pack(side="left")
        self.nut_nang_cap_online = ttk.Button(dong, text="Test nâng cấp NV", command=self.bat_tat_nang_cap_online)
        self.nut_nang_cap_online.pack(side="left", padx=(6, 0))
        self.nhan_tao_nv = ttk.Label(dong, text="", foreground="blue")
        self.nhan_tao_nv.pack(side="left", padx=8)
        ttk.Label(khung, text="Làm lần lượt từng tài khoản: mở game, đăng nhập (máy chủ, mã kiểm tra lấy ở tab Tài "
                              "khoản), tạo nhân vật nữ avatar đầu tiên. Nhân vật 1 tên là tên tài khoản, nhân vật 2 / 3 "
                              "lặp thêm 1 / 2 lần ký tự cuối của tên tài khoản; tên trùng thì thêm số ở cuối. Mỗi nhân vật: vào game nhận đồ "
                              "rồi về chọn máy chủ, tạo nhân vật tiếp theo; xong tài khoản thì tắt game. Nhân vật đã "
                              "nhận đồ được ghi lại, chạy lại không làm lại.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(6, 0))

    def luu_tao_nv(self):
        """Lưu các ô của khung tạo nhân vật mới. Trả về (danh sách tài khoản, tùy chọn); sai thì báo ValueError."""
        chu = self.o_ds_tao_nv.get("1.0", "end").strip()
        ds = doc_danh_sach(chu)
        so_nv = so_nguyen(self.bien_so_nv_moi.get(), "Số nhân vật mỗi tài khoản")
        if not 1 <= so_nv <= 3:
            raise ValueError("Số nhân vật mỗi tài khoản từ 1 tới 3")
        tuy_chon = {"danh_sach": chu, "so_nhan_vat": so_nv,
                    "nhan_do_tan_thu": self.bien_nhan_do_tan_thu.get()}
        self._sua_tai_khoan(lambda cai_dat: cai_dat["tao_nhan_vat_moi"].update(tuy_chon))
        return ds, tuy_chon

    def bat_tat_tao_nv(self):
        if self.luong_tao_nv and self.luong_tao_nv.is_alive():
            self.luong_tao_nv.dung.set()
            self.nhan_tao_nv.configure(text="Đang dừng...")
            self.in_log("[Tạo nhân vật] Dừng theo yêu cầu (game đang mở sẽ được tắt)")
            return
        try:
            ds, tuy_chon = self.luu_tao_nv()
        except ValueError as loi:
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        if not ds:
            messagebox.showinfo("Tạo nhân vật", "Nhập ít nhất một dòng: tài_khoản mật_khẩu")
            return
        cai_dat = cau_hinh.doc_tai_khoan()
        self.luong_tao_nv = LuongTaoNhanVat(ds, cai_dat, tuy_chon, self.hang_doi)
        self.luong_tao_nv.start()
        self.nut_tao_nv.configure(text="Dừng")
        self.in_log(f"[Tạo nhân vật] Bắt đầu {len(ds)} tài khoản ({', '.join(t['ten_dang_nhap'] for t in ds)}), "
                    f"mỗi tài khoản {tuy_chon['so_nhan_vat']} nhân vật"
                    + (", nhận đồ tân thủ" if tuy_chon["nhan_do_tan_thu"] else ""))

    def bat_tat_nang_cap_online(self):
        if self.luong_nang_cap_online and self.luong_nang_cap_online.is_alive():
            self.luong_nang_cap_online.dung.set()
            self.nhan_tao_nv.configure(text="Đang dừng...")
            self.in_log("[Nâng cấp NV] Dừng theo yêu cầu")
            return
        if not messagebox.askyesno("Test nâng cấp NV",
                                   "Nâng cấp ngay mọi nhân vật đang trong game chưa có trong danh sách đã nâng cấp "
                                   "(nang_cap_da_xong.json)?\n\nMỗi nhân vật: Bách Bảo 9 sao, mua Thần Khí + trứng "
                                   "trân thú, 4 giftcode, mang Hoàng Kim + vứt đồ cũ + dùng Hộp Point, rút 2 lần "
                                   "10.000.000 Nội Lực, cộng 10.000.000 Nội Lực (chưa max) rồi hết vào Thân Pháp.\n\n"
                                   "Bình thường auto tự nâng cấp mỗi khi đăng nhập nhân vật, nút này chỉ để test."):
            return
        self.luong_nang_cap_online = LuongNangCapOnline(self.hang_doi)
        self.luong_nang_cap_online.start()
        self.nut_nang_cap_online.configure(text="Dừng nâng cấp")
        self.in_log("[Nâng cấp NV] Bắt đầu nâng cấp các nhân vật đang online")

    def luu_nhap_ma_tao_nv(self):
        bat = self.bien_nhap_ma_tao_nv.get()
        cau_hinh.dat_chung({"tu_nhap_ma_tao_nhan_vat": bat})
        self.in_log(f"{'BẬT' if bat else 'TẮT'} tự nhập mã kiểm tra khi tạo nhân vật")

    def _tao_tab_nhom(self, so_tay):
        tab = self._tab_cuon(so_tay, "Nhóm")
        chung = cau_hinh.chung()
        self.bien_moi_nhom = tk.BooleanVar(value=chung["bat_moi_nhom"])
        ttk.Checkbutton(tab, text="Tự mời nhóm (ai đang làm trưởng nhóm thì mời, nhân vật trong auto tự đồng ý)",
                        variable=self.bien_moi_nhom, command=self.luu_nhom).pack(anchor="w")

        dong = ttk.Frame(tab)
        dong.pack(fill="x", pady=(6, 0))
        ttk.Label(dong, text="Trưởng nhóm").pack(side="left")
        self.bien_truong_nhom = tk.StringVar(value=chung["truong_nhom"])
        self.chon_truong_nhom = ttk.Combobox(dong, textvariable=self.bien_truong_nhom, width=20, state="readonly",
                                             postcommand=self._nap_ds_truong_nhom)
        self.chon_truong_nhom.pack(side="left", padx=6)
        ttk.Button(dong, text="Lưu", command=self.luu_nhom).pack(side="left")
        self.bien_moi_nhan_vat_auto = tk.BooleanVar(value=chung["bat_moi_nhan_vat_auto"])
        ttk.Checkbutton(tab, text="Mời mọi nhân vật đang chạy trong auto (bỏ tích thì chỉ mời người trong danh sách mời)",
                        variable=self.bien_moi_nhan_vat_auto, command=self.luu_nhom).pack(anchor="w", pady=(4, 0))

        khung = ttk.Frame(tab)
        khung.pack(fill="x", pady=(6, 0))
        self._tao_ds_ten(khung, "danh_sach_moi", "Danh sách mời (white list)", "danh sách mời nhóm")

        self.bang_nhom = ttk.Treeview(tab, columns=("nhan_vat", "trang_thai"), show="headings", height=4,
                                      selectmode="none")
        for cot, tieu_de, rong in (("nhan_vat", "Nhân vật", 130), ("trang_thai", "Trạng thái nhóm", 300)):
            self.bang_nhom.heading(cot, text=tieu_de)
            self.bang_nhom.column(cot, width=self.px(rong), anchor="w", stretch=cot == "trang_thai")
        self.bang_nhom.pack(fill="x", pady=(6, 0))
        self._keo_dai_duoc(self.bang_nhom, "nhom", cha=tab, after=self.bang_nhom)
        ttk.Label(tab, text=f"Nhóm tối đa {SO_NGUOI_TOI_DA} người. Ai đang làm trưởng nhóm trong game (kể cả khi trưởng "
                            "nhóm cũ bị diss và game chuyển quyền) sẽ mời nhân vật trong auto còn thiếu và người trong "
                            "danh sách mời đang ở gần. Trưởng nhóm chọn ở trên bị diss thì người khác làm trưởng tạm, "
                            "vào lại thì được mời và nhận lại quyền trưởng nhóm. Chưa ai có nhóm thì trưởng nhóm chọn "
                            "ở trên lập nhóm (để trống hoặc người đó không online thì nhân vật đầu tiên theo tên). "
                            "Có 2 nhóm thì nhóm nhỏ hơn tự nhập vào nhóm lớn.",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(4, 0))

    def _nap_ds_truong_nhom(self):
        ds = [luong.ten for luong in self.cac_luong.values() if luong.ten]
        hien_tai = self.bien_truong_nhom.get()
        if hien_tai and hien_tai not in ds:
            ds.insert(0, hien_tai)
        self.chon_truong_nhom.configure(values=[""] + ds)

    def luu_nhom(self):
        bat, truong = self.bien_moi_nhom.get(), self.bien_truong_nhom.get().strip()
        bat_nv_auto = self.bien_moi_nhan_vat_auto.get()
        if bat:
            trong_auto = {chuan_hoa(l.ten) for l in self.cac_luong.values() if l.ten}
            ds_moi = chung["danh_sach_moi"] if (chung := cau_hinh.chung()) else []
            if ds_moi and not any(chuan_hoa(t) in trong_auto for t in ds_moi) and not bat_nv_auto:
                bat_nv_auto = True
                self.bien_moi_nhan_vat_auto.set(True)
                self.in_log("Danh sách mời không khớp nhân vật đang online → bật «mời mọi nhân vật trong auto»")
        cau_hinh.dat_chung({"bat_moi_nhom": bat, "truong_nhom": truong, "bat_moi_nhan_vat_auto": bat_nv_auto})
        self.trang_thai_nhom.clear()
        self.cap_nhat_nhom()
        self.in_log(f"{'BẬT' if bat else 'TẮT'} tự mời nhóm" + (f", trưởng nhóm {truong}" if truong else ""))

    def _tao_ds_ten(self, khung, khoa, tieu_de, mo_ta):
        """
        Hai danh sách: người chơi xung quanh (trái) và danh sách tên lưu ở cài đặt chung khoa (phải), nút Thêm / Xóa
        và ô gõ tên. Dùng cho danh sách mời nhóm và danh sách đồng minh.
        """
        khung.columnconfigure(0, weight=1)
        khung.columnconfigure(2, weight=1)
        ttk.Label(khung, text="Người chơi xung quanh").grid(row=0, column=0, sticky="w")
        ttk.Label(khung, text=tieu_de).grid(row=0, column=2, sticky="w")
        xung_quanh = tk.Listbox(khung, height=5, selectmode="extended", exportselection=False)
        xung_quanh.grid(row=1, column=0, sticky="nsew")
        ds = tk.Listbox(khung, height=5, selectmode="extended", exportselection=False)
        ds.grid(row=1, column=2, sticky="nsew")
        bien_ten = tk.StringVar()

        def ve_lai():
            moi = list(cau_hinh.chung()[khoa])
            if list(ds.get(0, "end")) == moi:
                return
            ds.delete(0, "end")
            for ten in moi:
                ds.insert("end", ten)

        def them(cac_ten):
            hien_co = cau_hinh.chung()[khoa]
            da_co = {chuan_hoa(ten) for ten in hien_co}
            moi = []
            for ten in cac_ten:
                if ten and chuan_hoa(ten) not in da_co:
                    da_co.add(chuan_hoa(ten))
                    moi.append(ten)
            if moi:
                cau_hinh.dat_chung({khoa: hien_co + moi})
                ve_lai()
                self.in_log(f"Thêm vào {mo_ta}: {', '.join(moi)}")

        def them_go_tay():
            ten = bien_ten.get().strip()
            if not ten:
                return
            try:
                chuoi_lua(ten)
            except LoiDangNhap as loi:
                messagebox.showerror("Tên không hợp lệ", str(loi))
                return
            them([ten])
            bien_ten.set("")

        def xoa():
            bo = [ds.get(i) for i in ds.curselection()]
            if not bo:
                return
            khoa_bo = {chuan_hoa(ten) for ten in bo}
            cau_hinh.dat_chung({khoa: [ten for ten in cau_hinh.chung()[khoa] if chuan_hoa(ten) not in khoa_bo]})
            ve_lai()
            self.in_log(f"Xóa khỏi {mo_ta}: {', '.join(bo)}")

        nut_giua = ttk.Frame(khung)
        nut_giua.grid(row=1, column=1, padx=6)
        ttk.Button(nut_giua, text="Thêm >>",
                   command=lambda: them([xung_quanh.get(i) for i in xung_quanh.curselection()])).pack(pady=2)
        ttk.Button(nut_giua, text="<< Xóa", command=xoa).pack(pady=2)
        dong_nhap = ttk.Frame(khung)
        dong_nhap.grid(row=2, column=2, sticky="ew", pady=(4, 0))
        o_ten = ttk.Entry(dong_nhap, textvariable=bien_ten)
        o_ten.pack(side="left", fill="x", expand=True)
        o_ten.bind("<Return>", lambda _su_kien: them_go_tay())
        ttk.Button(dong_nhap, text="Thêm tên", command=them_go_tay).pack(side="left", padx=(4, 0))
        ve_lai()
        self.cac_ds_xung_quanh.append(xung_quanh)
        self.cac_ve_lai_ds.append(ve_lai)

    def ve_lai_xung_quanh(self):
        """Người chơi ở gần bất kỳ nhân vật nào trong auto, trừ chính các nhân vật trong auto."""
        trong_auto = {chuan_hoa(luong.ten) for luong in self.cac_luong.values() if luong.ten}
        cac_ten = sorted({ten for ds in self.xung_quanh.values() for ten in ds if chuan_hoa(ten) not in trong_auto})
        if cac_ten == self.ds_xung_quanh_dang_hien:
            return
        for o_ds in self.cac_ds_xung_quanh:
            dang_chon = {o_ds.get(i) for i in o_ds.curselection()}
            o_ds.delete(0, "end")
            for chi_so, ten in enumerate(cac_ten):
                o_ds.insert("end", ten)
                if ten in dang_chon:
                    o_ds.selection_set(chi_so)
        self.ds_xung_quanh_dang_hien = cac_ten

    def _acc_chinh_online(self):
        """Như ten_nhan_vat_acc_chinh_online nhưng đọc thông tin luồng game đã gửi lên, không gọi Lua từ giao diện."""
        cd = cai_dat_giao_acc_chinh()
        tk = (cd.get("tai_khoan") or "").strip().lower()
        ten = (cd.get("nhan_vat") or "").strip()
        if not tk or not ten:
            return None
        for tt in self.thong_tin.values():
            if (tt.get("tai_khoan") or "").lower() == tk and chuan_hoa(tt.get("ten") or "") == chuan_hoa(ten):
                return ten
        return None

    def cap_nhat_nhom(self):
        """Tính trên luồng giao diện; luồng game chỉ đọc self.nhom_hien_tai (thay cả dict, không sửa tại chỗ)."""
        chung = cau_hinh.chung()
        if not chung["bat_moi_nhom"]:
            self.nhom_hien_tai = None
            return
        khoa_uu_tien = chuan_hoa(chung["truong_nhom"])
        trong_auto = {chuan_hoa(luong.ten): luong.ten for luong in self.cac_luong.values() if luong.ten}
        khoa_ds_moi = {chuan_hoa(ten) for ten in chung["danh_sach_moi"]}
        moi_moi_nhan_vat_auto = chung["bat_moi_nhan_vat_auto"]
        # Xoay vòng tạm whitelist (round trước); không ai online trùng tên → mời mọi nhân vật đang auto.
        if not moi_moi_nhan_vat_auto and chung["danh_sach_moi"] \
                and not any(k in trong_auto for k in khoa_ds_moi):
            moi_moi_nhan_vat_auto = True
        if moi_moi_nhan_vat_auto:
            nhan_vat_auto = list(trong_auto.values())
        else:
            nhan_vat_auto = [ten for khoa, ten in trong_auto.items()
                             if khoa in khoa_ds_moi or khoa == khoa_uu_tien]
        acc_train = self._acc_chinh_online()
        if acc_train:
            khoa_train = chuan_hoa(acc_train)
            nhan_vat_auto = [ten for ten in nhan_vat_auto if chuan_hoa(ten) != khoa_train]
        khoa_nhan_vat = {chuan_hoa(ten) for ten in nhan_vat_auto}
        if khoa_uu_tien in khoa_nhan_vat:
            nguoi_lap = trong_auto[khoa_uu_tien]
        else:
            nguoi_lap = min(nhan_vat_auto, key=chuan_hoa, default="")
        cac_nhom = {chuan_hoa(ten): thanh_vien for ten, thanh_vien in self.doi_hinh_nhom.values()
                    if chuan_hoa(ten) in khoa_nhan_vat}
        nguoi_ngoai = [ten for ten in chung["danh_sach_moi"] if chuan_hoa(ten) not in trong_auto]
        if acc_train:
            nguoi_ngoai = [ten for ten in nguoi_ngoai if chuan_hoa(ten) != khoa_train]
        self.nhom_hien_tai = {"nhan_vat_auto": nhan_vat_auto, "nguoi_lap": nguoi_lap,
                              "truong_uu_tien": trong_auto[khoa_uu_tien] if khoa_uu_tien in khoa_nhan_vat else "",
                              "nguoi_ngoai": nguoi_ngoai,
                              "cac_nhom": cac_nhom}

    def ve_lai_bang_nhom(self):
        con = set()
        for hwnd, luong in self.cac_luong.items():
            if not luong.ten:
                continue
            iid = str(hwnd)
            con.add(iid)
            if self.nhom_hien_tai is None:
                mo_ta = "Tắt tự mời nhóm"
            else:
                mo_ta = self.trang_thai_nhom.get(hwnd, "Đang kiểm tra...")
            if self.bang_nhom.exists(iid):
                dat_dong_bang(self.bang_nhom, iid, (luong.ten, mo_ta))
            else:
                self.bang_nhom.insert("", "end", iid=iid, values=(luong.ten, mo_ta))
        for iid in self.bang_nhom.get_children():
            if iid not in con:
                self.bang_nhom.delete(iid)

    def _tao_tab_tai_khoan(self, so_tay):
        tab = self._tab_cuon(so_tay, "Tài khoản")
        cai_dat = cau_hinh.doc_tai_khoan()
        self.bien_mat_ket_noi = tk.BooleanVar(value=cau_hinh.chung()["tu_thoat_khi_mat_ket_noi"])
        ttk.Checkbutton(tab, text="Mất kết nối thì tự bấm Duyệt (kết nối lại), không được thì bấm Đóng cho game tắt",
                        variable=self.bien_mat_ket_noi, command=self.doi_mat_ket_noi).pack(anchor="w")
        self.bien_giai_ma_vao_game = tk.BooleanVar(value=cai_dat["giai_ma_kiem_tra"])
        ttk.Checkbutton(tab, text="Giải mã kiểm tra khi vào game (không nhập mã cố định ở ô Mã kiểm tra)",
                        variable=self.bien_giai_ma_vao_game, command=self.doi_giai_ma_vao_game).pack(anchor="w")

        khung = ttk.Frame(tab)
        khung.pack(fill="x", pady=(4, 0))
        self.bien_dang_nhap = {}
        for so, (khoa, nhan, rong) in enumerate(CAI_DAT_DANG_NHAP):
            dong, cot = (0, 0) if so == 0 else ((so + 1) // 2, (so + 1) % 2 * 2)
            ttk.Label(khung, text=nhan).grid(row=dong, column=cot, sticky="w", pady=1, padx=(12 if cot else 0, 4))
            self.bien_dang_nhap[khoa] = tk.StringVar(value=str(cai_dat[khoa]))
            ttk.Entry(khung, textvariable=self.bien_dang_nhap[khoa], width=rong).grid(
                row=dong, column=cot + 1, columnspan=3 if so == 0 else 1, sticky="w")
        ttk.Button(khung, text="Chọn...", command=self.chon_thu_muc_game).grid(row=0, column=4, sticky="w",
                                                                             padx=(4, 0))

        self.khoa_ds_tk_dang_chon = cau_hinh.KHOA_TK_PHO_BAN
        self.bang_tk = {}
        for khoa_ds, tieu_de_khung, cot_bat in (
                (cau_hinh.KHOA_TK_PHO_BAN, "Tài khoản phó bản (xoay vòng PMP / Sát Tinh)", "XV"),
                (cau_hinh.KHOA_TK_TRAIN, "Tài khoản train (chỉ train, không xoay vòng)", "Bật")):
            khung_tk = ttk.LabelFrame(tab, text=tieu_de_khung, padding=4)
            khung_tk.pack(fill="x", pady=(6, 0))
            bang = ttk.Treeview(khung_tk, columns=("bat", "ten_dang_nhap", "nhan_vat", "trang_thai"),
                                show="headings", height=4, selectmode="browse")
            for cot, tieu_de, rong in (("bat", cot_bat, 40), ("ten_dang_nhap", "Tài khoản", 110),
                                       ("nhan_vat", "Nhân vật", 110),
                                       ("trang_thai", "Trạng thái", 190)):
                bang.heading(cot, text=tieu_de)
                bang.column(cot, width=self.px(rong), anchor="center" if cot == "bat" else "w",
                            stretch=cot == "trang_thai")
            bang.heading("bat", command=lambda k=khoa_ds: self.bat_tat_ca_tai_khoan(k))
            bang.pack(fill="x")
            self._keo_dai_duoc(bang, f"tai_khoan_{khoa_ds}")
            bang.bind("<Button-1>", lambda e, k=khoa_ds: self._bam_vao_bang_tai_khoan(e, k))
            bang.bind("<Double-1>", lambda e, k=khoa_ds: self._double_click_bang_tai_khoan(e, k))
            bang.bind("<<TreeviewSelect>>", lambda e, k=khoa_ds: self._chon_tai_khoan(e, k))
            self.bang_tk[khoa_ds] = bang

        dong = ttk.Frame(tab)
        dong.pack(fill="x", pady=(4, 0))
        self.bien_tai_khoan = {khoa: tk.StringVar() for khoa in ("ten_dang_nhap", "mat_khau", "nhan_vat")}
        for khoa, nhan, rong, an in (("ten_dang_nhap", "Tài khoản", 14, ""), ("mat_khau", "Mật khẩu", 12, "●"),
                                     ("nhan_vat", "Nhân vật", 14, "")):
            ttk.Label(dong, text=nhan).pack(side="left", padx=(0 if khoa == "ten_dang_nhap" else 8, 2))
            ttk.Entry(dong, textvariable=self.bien_tai_khoan[khoa], width=rong, show=an).pack(side="left")
        dong = ttk.Frame(tab)
        dong.pack(fill="x", pady=(4, 0))
        self.bien_tu_dang_nhap_khi_diss = tk.BooleanVar(value=True)
        ttk.Checkbutton(dong, text="Tự mở lại khi diss",
                        variable=self.bien_tu_dang_nhap_khi_diss).pack(side="left")
        chung_tk = cau_hinh.chung()
        self.bien_tu_duyet_popup_tk = tk.BooleanVar(value=chung_tk.get("tu_duyet_popup", False))
        ttk.Checkbutton(dong, text="Tự duyệt popup",
                        variable=self.bien_tu_duyet_popup_tk,
                        command=self.luu_tu_duyet_tu_tab_tai_khoan).pack(side="left", padx=(8, 0))
        ttk.Label(dong, text="Thêm vào").pack(side="left", padx=(12, 2))
        self.bien_loai_tai_khoan = tk.StringVar(value="pho_ban")
        ttk.Radiobutton(dong, text="Phó bản", variable=self.bien_loai_tai_khoan, value="pho_ban").pack(side="left")
        ttk.Radiobutton(dong, text="Train", variable=self.bien_loai_tai_khoan, value="train").pack(side="left",
                                                                                                    padx=(4, 0))
        dong = ttk.Frame(tab)
        dong.pack(fill="x", pady=(4, 0))
        ttk.Label(dong, text="Đến TK").pack(side="left", padx=(0, 2))
        self.bien_tai_khoan_den = tk.StringVar()
        ttk.Entry(dong, textvariable=self.bien_tai_khoan_den, width=14).pack(side="left")
        ttk.Label(dong, text="(caychay10 → caychay100)", foreground="gray").pack(side="left", padx=(4, 8))

        nut = ttk.Frame(tab)
        nut.pack(fill="x", pady=(6, 0))
        ttk.Button(nut, text="Thêm / Sửa", command=self.them_sua_tai_khoan).pack(side="left")
        ttk.Button(nut, text="Thêm hàng loạt", command=self.them_tai_khoan_hang_loat).pack(side="left", padx=4)
        ttk.Button(nut, text="Xóa", command=self.xoa_tai_khoan).pack(side="left", padx=4)
        ttk.Button(nut, text="Xóa tất cả", command=self.xoa_tat_ca_tai_khoan).pack(side="left")
        ttk.Button(nut, text="Lưu cài đặt", command=self.luu_cai_dat_dang_nhap).pack(side="left", padx=4)

        ttk.Label(tab, text="Phó bản — cột XV: tham gia xoay vòng (chỉ mở game khi bấm Bắt đầu ở tab Phó bản). Train — "
                            "cột Bật: bật auto train. Double-click dòng tài khoản (không phải cột XV/Bật) để mở game và "
                            "đăng nhập ngay (mạng qua Proxifier + Proxy Broker bên dưới). Tự mở lại khi diss: bảng Train, "
                            "tích Bật + ô bên trên. Mỗi tài khoản chỉ nằm một bảng. Game train không bị tắt khi chạy xoay vòng "
                            "phó bản. Nhân vật để trống thì tới màn chọn nhân vật; vào game rồi thì tự ghi tên. Sửa tay "
                            "tai_khoan.json: tai_khoan_pho_ban / tai_khoan_train (mật khẩu chữ thường).",
                  foreground="gray", wraplength=self.px(DOAN_WRAP_GHI_CHU), justify="left").pack(anchor="w", pady=(4, 0))

        proxy_broker_ui.dam_bao_config()
        pb_cfg = proxy_broker_ui.doc_config()
        self.khung_pf = ttk.LabelFrame(tab, text="Proxifier + Proxy Broker", padding=4)
        self.khung_pf.pack(fill="x", pady=(8, 0))
        khung_pf = self.khung_pf
        self.bien_pf_exe = tk.StringVar(value=pb_cfg.get("proxifier_exe") or "")
        self.bien_pf_ppx = tk.StringVar(value=pb_cfg.get("profile_ppx") or "")
        self.bien_pf_log = tk.StringVar(value=pb_cfg.get("log_file") or "")
        if pb_cfg.get("proxifier_exe"):
            cap = proxy_broker_ui.phat_hien_tu_exe(pb_cfg["proxifier_exe"])
            if cap.get("profile_ppx") and not self.bien_pf_ppx.get().strip():
                self.bien_pf_ppx.set(cap["profile_ppx"])
            if cap.get("log_file") and not self.bien_pf_log.get().strip():
                self.bien_pf_log.set(cap["log_file"])
        proxy_broker_ui.dam_bao_log_broker()
        for hang, (nhan, bien, cmd) in enumerate((
                ("Proxifier.exe", self.bien_pf_exe, self.chon_pf_exe),
                ("Profile .ppx", self.bien_pf_ppx, self.chon_pf_ppx),
                ("Log Proxifier", self.bien_pf_log, self.chon_pf_log),
        )):
            ttk.Label(khung_pf, text=nhan).grid(row=hang, column=0, sticky="w", pady=1)
            ttk.Entry(khung_pf, textvariable=bien, width=58).grid(row=hang, column=1, sticky="ew", padx=4)
            ttk.Button(khung_pf, text="...", width=3, command=cmd).grid(row=hang, column=2)
        khung_pf.columnconfigure(1, weight=1)
        ttk.Label(
            khung_pf,
            text=f"Log Proxy Broker (tự tạo): {proxy_broker_ui.mo_ta_log_broker()} — "
                 "Log Proxifier: bật ghi log trong app Proxifier (Profile → Log), chọn file để broker đọc lỗi 10060…",
            foreground="gray",
            wraplength=self.px(520),
            justify="left",
        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(2, 0))
        dong_pf = ttk.Frame(khung_pf)
        dong_pf.grid(row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))
        ttk.Button(dong_pf, text="Lưu Proxifier", command=self.luu_proxy_broker).pack(side="left")
        ttk.Button(dong_pf, text="Chạy Proxy Broker", command=self.chay_proxy_broker).pack(side="left", padx=4)
        ttk.Button(dong_pf, text="Dừng Broker", command=self.dung_proxy_broker).pack(side="left", padx=4)
        self.nhan_pf_broker_led = ttk.Label(khung_pf, text="○ Broker: chưa chạy", font=("Segoe UI", 9, "bold"))
        self.nhan_pf_broker_led.grid(row=5, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self.nhan_pf_trang_thai = ttk.Label(khung_pf, text=proxy_broker_ui.mo_ta_state(), foreground="gray")
        self.nhan_pf_trang_thai.grid(row=6, column=0, columnspan=3, sticky="w", pady=(2, 0))
        self._proc_proxy_broker = None
        self._pf_broker_chay_truoc = False
        self._pf_health_truoc = None
        self._pf_gan_luc_da_login = None
        self._pf_failover_luc_truoc = None
        self.root.after(500, self.cap_nhat_trang_thai_proxy_broker)
        self.root.after(2000, self._lap_cap_nhat_proxy_broker)

        self.nap_bang_tai_khoan()

    def them_moc(self, moc):
        khung = ttk.Frame(self.khung_cac_moc)
        khung.pack(fill="x", pady=(1, 4))
        bien = {"level": tk.StringVar(value=str(moc["level"])), "map": tk.StringVar(value=moc["map"]),
                "hang_vat_pham_dich_chuyen": tk.StringVar(value=str(moc.get("hang_vat_pham_dich_chuyen", ""))),
                "map_khi_bi_pk": tk.StringVar(value=moc.get("map_khi_bi_pk", "")),
                "hang_vat_pham_khi_bi_pk": tk.StringVar(value=str(moc.get("hang_vat_pham_khi_bi_pk", ""))),
                "dang_dung_map_pk": tk.BooleanVar(value=moc.get("dang_dung_map_pk", False))}
        dong = ttk.Frame(khung)
        dong.pack(fill="x")
        ttk.Label(dong, text="Từ level").pack(side="left")
        ttk.Entry(dong, textvariable=bien["level"], width=5).pack(side="left", padx=4)
        ttk.Label(dong, text="tới map").pack(side="left")
        self._o_chon_map(dong, bien["map"]).pack(side="left", padx=4)
        ttk.Label(dong, text="dùng hàng").pack(side="left")
        ttk.Combobox(dong, textvariable=bien["hang_vat_pham_dich_chuyen"], values=CAC_HANG_TUI,
                     state="readonly", width=4).pack(side="left", padx=4)
        muc = (khung, bien)
        ttk.Button(dong, text="X", width=3, command=lambda: self.xoa_moc(muc)).pack(side="left", padx=(4, 0))

        dong = ttk.Frame(khung)
        dong.pack(fill="x", pady=(1, 0))
        ttk.Label(dong, text="Bị PK thì tới").pack(side="left", padx=(self.px(24), 0))
        self._o_chon_map(dong, bien["map_khi_bi_pk"]).pack(side="left", padx=4)
        ttk.Label(dong, text="dùng hàng").pack(side="left")
        ttk.Combobox(dong, textvariable=bien["hang_vat_pham_khi_bi_pk"], values=[""] + CAC_HANG_TUI,
                     state="readonly", width=4).pack(side="left", padx=4)
        ttk.Checkbutton(dong, text="Đang dùng", variable=bien["dang_dung_map_pk"],
                        command=lambda: self._luu_ngay(
                            bien["dang_dung_map_pk"], lambda cai_dat: self._sua_dang_dung_map_pk(bien, cai_dat),
                            f"đứng ở map Bị PK của mốc level {bien['level'].get()}")).pack(side="left", padx=(6, 0))
        self.cac_moc.append(muc)

    def xoa_moc(self, muc):
        muc[0].destroy()
        self.cac_moc.remove(muc)

    def nap_form(self, ten):
        """Hiện cài đặt đã lưu của nhân vật lên tab Chuyển sinh và Config."""
        cai_dat = cau_hinh.cua_nhan_vat(ten)
        self.ten_dang_sua = ten
        self.nhan_dang_sua.configure(text=f"Cài đặt riêng cho: {ten}")
        self.nhan_config.configure(text=f"Danh sách map đang dùng cho: {ten}")

        self.bien_bat_chuyen_sinh_nv.set(cai_dat["bat_chuyen_sinh"])
        cs = cai_dat["chuyen_sinh"]
        self.bien_cs_level.set(str(cs["level"]))
        self.bien_cs_dich_chuyen_truoc.set(cs.get("dich_chuyen_truoc_chuyen_sinh", False))
        self.bien_cs_map_truoc.set(cs.get("map_truoc_chuyen_sinh", ""))
        self.bien_cs_hang_truoc.set(str(cs.get("hang_vat_pham_truoc_chuyen_sinh", 5)))

        for khung, _ in self.cac_moc:
            khung.destroy()
        self.cac_moc = []
        for moc in cai_dat["moc_level"]:
            self.them_moc(moc)

        cd = cai_dat.get("auto_cong_diem") or cau_hinh.MAC_DINH_CONG_DIEM
        self.bien_cong_diem.set(cd["bat"])
        for khoa, bien in self.bien_chi_so.items():
            bien.set(khoa in cd["cac_chi_so"])
        self.bien_dung_hop_point.set(cd["tu_dung_hop_point"])
        self.nap_form_chien_dau(ten)
        self.nap_form_auto_click(ten)
        self.nap_form_pho_ban(ten)

    def doc_form(self):
        """Đọc tab Chuyển sinh thành dict cài đặt. Sai dữ liệu thì báo ValueError."""
        cai_dat = cau_hinh.cua_nhan_vat(self.ten_dang_sua)

        cs = {
            "level": so_nguyen(self.bien_cs_level.get(), "Level chuyển sinh"),
            "dich_chuyen_truoc_chuyen_sinh": self.bien_cs_dich_chuyen_truoc.get(),
            "map_truoc_chuyen_sinh": self.bien_cs_map_truoc.get().strip(),
            "hang_vat_pham_truoc_chuyen_sinh": doc_hang(self.bien_cs_hang_truoc.get(),
                                                        "dịch chuyển trước khi chuyển sinh"),
        }
        if cs["dich_chuyen_truoc_chuyen_sinh"] and not cs["map_truoc_chuyen_sinh"]:
            raise ValueError("Chưa chọn map dịch chuyển tới trước khi chuyển sinh")
        cai_dat["chuyen_sinh"] = cs

        cai_dat["moc_level"] = []
        for _, bien in self.cac_moc:
            level = so_nguyen(bien["level"].get(), "Level của mốc")
            noi = f"mốc level {level}"
            if level >= cs["level"]:
                raise ValueError(f"Mốc level {level} không bao giờ chạy vì tới level {cs['level']} là chuyển sinh. "
                                 "Muốn tới map trước khi chuyển sinh thì tích ô đó ở tab Chuyển sinh.")
            moc = {"level": level, "map": bien["map"].get().strip(),
                   "hang_vat_pham_dich_chuyen": doc_hang(bien["hang_vat_pham_dich_chuyen"].get(), noi)}
            if not moc["map"]:
                raise ValueError(f"Chưa nhập tên map ở {noi}")
            map_pk = bien["map_khi_bi_pk"].get().strip()
            hang_pk = bien["hang_vat_pham_khi_bi_pk"].get().strip()
            if map_pk or hang_pk:
                if not map_pk:
                    raise ValueError(f"Chưa nhập tên map ở dòng Bị PK của {noi}")
                moc.update({"map_khi_bi_pk": map_pk,
                            "hang_vat_pham_khi_bi_pk": doc_hang(hang_pk, f"dòng Bị PK của {noi}"),
                            "dang_dung_map_pk": bien["dang_dung_map_pk"].get()})
            cai_dat["moc_level"].append(moc)
        if not cai_dat["moc_level"]:
            raise ValueError("Cần ít nhất một mốc map train")
        cai_dat["moc_level"].sort(key=lambda m: m["level"], reverse=True)

        cd = {"bat": self.bien_cong_diem.get(),
              "cac_chi_so": [khoa for khoa, _ in CAC_CHI_SO if self.bien_chi_so[khoa].get()],
              "tu_dung_hop_point": self.bien_dung_hop_point.get()}
        if cd["bat"] and not cd["cac_chi_so"]:
            raise ValueError("Bật tự cộng điểm tiềm năng thì cần tích ít nhất một chỉ số")
        cai_dat["auto_cong_diem"] = cd
        return cai_dat

    def luu_form(self):
        if self.ten_dang_sua is None:
            return
        try:
            cai_dat = self.doc_form()
        except ValueError as loi:
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        cau_hinh.dat_nhan_vat(self.ten_dang_sua, cai_dat)
        self.nap_form(self.ten_dang_sua)
        self.in_log(f"Đã lưu cài đặt của {self.ten_dang_sua}")

    def _luu_ngay(self, bien, sua, mo_ta):
        """
        Tích / bỏ tích ô bien là lưu ngay vào cài đặt đã lưu của nhân vật đang sửa (không cần bấm Lưu, không đụng tới
        các ô khác đang sửa dở). sua(cai_dat) sửa cài đặt, báo ValueError thì trả ô về như cũ.
        """
        if self.ten_dang_sua is None:
            bien.set(not bien.get())
            messagebox.showinfo("Chuyển sinh", "Chọn một nhân vật trong danh sách trước")
            return
        cai_dat = cau_hinh.cua_nhan_vat(self.ten_dang_sua)
        try:
            sua(cai_dat)
        except ValueError as loi:
            bien.set(not bien.get())
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        cau_hinh.dat_nhan_vat(self.ten_dang_sua, cai_dat)
        self.in_log(f"{self.ten_dang_sua}: {'BẬT' if bien.get() else 'TẮT'} {mo_ta}")

    def _sua_dich_chuyen_truoc(self, cai_dat):
        bat = self.bien_cs_dich_chuyen_truoc.get()
        map_truoc = self.bien_cs_map_truoc.get().strip()
        if bat and not map_truoc:
            raise ValueError("Chọn map dịch chuyển tới trước khi chuyển sinh rồi mới tích ô này")
        cai_dat["chuyen_sinh"] = dict(cai_dat["chuyen_sinh"], dich_chuyen_truoc_chuyen_sinh=bat,
                                      map_truoc_chuyen_sinh=map_truoc,
                                      hang_vat_pham_truoc_chuyen_sinh=doc_hang(self.bien_cs_hang_truoc.get(),
                                                                               "dịch chuyển trước khi chuyển sinh"))

    def _sua_cong_diem(self, cai_dat):
        cd = {"bat": self.bien_cong_diem.get(),
              "cac_chi_so": [khoa for khoa, _ in CAC_CHI_SO if self.bien_chi_so[khoa].get()],
              "tu_dung_hop_point": self.bien_dung_hop_point.get()}
        if cd["bat"] and not cd["cac_chi_so"]:
            raise ValueError("Bật tự cộng điểm tiềm năng thì cần tích ít nhất một chỉ số")
        cai_dat["auto_cong_diem"] = cd

    def _sua_dang_dung_map_pk(self, bien_moc, cai_dat):
        try:
            level = int(bien_moc["level"].get())
        except ValueError:
            raise ValueError("Level của dòng này chưa đúng, sửa rồi bấm Lưu") from None
        moc = next((moc for moc in cai_dat["moc_level"] if moc["level"] == level and "map_khi_bi_pk" in moc), None)
        if moc is None:
            raise ValueError(f"Dòng Bị PK của mốc level {level} chưa được lưu, bấm Lưu trước")
        moc["dang_dung_map_pk"] = bien_moc["dang_dung_map_pk"].get()

    def cap_nhat_co_map_pk(self, ten):
        """Luồng auto vừa đổi "dang_dung_map_pk" đã lưu: cập nhật ô "Đang dùng" trên form mà không xóa chỗ đang sửa dở."""
        if ten != self.ten_dang_sua:
            return
        co_theo_level = {moc["level"]: moc["dang_dung_map_pk"] for moc in cau_hinh.cua_nhan_vat(ten)["moc_level"]
                         if "dang_dung_map_pk" in moc}
        for _, bien in self.cac_moc:
            try:
                level = int(bien["level"].get())
            except ValueError:
                continue
            if level in co_theo_level and bien["map_khi_bi_pk"].get().strip():
                bien["dang_dung_map_pk"].set(co_theo_level[level])

    def ap_dung_tat_ca(self):
        """Chép cài đặt đang sửa cho mọi nhân vật và làm mặc định cho nhân vật mới (giữ nguyên bật/tắt của từng người)."""
        if self.ten_dang_sua is None:
            return
        try:
            cai_dat = self.doc_form()
        except ValueError as loi:
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        cau_hinh.dat_nhan_vat(self.ten_dang_sua, cai_dat)
        cac_khoa_rieng = ("chien_dau", "auto_click", "pho_ban_pmp")
        cai_dat = {khoa: gia_tri for khoa, gia_tri in cai_dat.items() if khoa not in cac_khoa_rieng}
        def chep(_ten, cua_nguoi_do):
            moi = dict(cai_dat, bat_auto=cua_nguoi_do["bat_auto"], bat_chuyen_sinh=cua_nguoi_do["bat_chuyen_sinh"],
                       chi_in_khong_bam=cua_nguoi_do["chi_in_khong_bam"],
                       moc_level=giu_co_map_pk(cai_dat["moc_level"], cua_nguoi_do["moc_level"]))
            moi.update({khoa: cua_nguoi_do[khoa] for khoa in cac_khoa_rieng if khoa in cua_nguoi_do})
            return moi
        cau_hinh.thay_tat_ca_nhan_vat(chep)
        mac_dinh = dict(cai_dat, bat_auto=False, bat_chuyen_sinh=False, chi_in_khong_bam=False,
                        moc_level=giu_co_map_pk(cai_dat["moc_level"], []))
        mac_dinh_cu = cau_hinh.mac_dinh()
        mac_dinh.update({khoa: mac_dinh_cu[khoa] for khoa in cac_khoa_rieng if khoa in mac_dinh_cu})
        cau_hinh.dat_mac_dinh(mac_dinh)
        self.in_log("Đã áp dụng cài đặt cho tất cả nhân vật và làm mặc định cho nhân vật mới")

    def doi_chuyen_sinh_tat_ca(self, bien, bat):
        """
        Tích ô "Bật / Tắt auto chuyển sinh cho tất cả nhân vật": bật / tắt auto chuyển sinh của mọi nhân vật đang chạy.
        Bỏ tích: trả lại như lúc trước khi tích (không nhớ thì đổi ngược lại hết).
        """
        cac_ten = sorted({luong.ten for luong in self.cac_luong.values() if luong.ten})
        hien_tai = {ten: cau_hinh.cua_nhan_vat(ten)["bat_chuyen_sinh"] for ten in cac_ten}
        if bien.get():
            truoc = hien_tai
            moi = dict.fromkeys(cac_ten, bat)
        else:
            truoc = {}
            moi = {ten: self.chuyen_sinh_truoc_khi_doi.get(ten, not bat) for ten in cac_ten}
            if all(gia_tri == bat for gia_tri in moi.values()):
                moi = dict.fromkeys(cac_ten, not bat)
        self.dang_doi_tat_ca = True
        try:
            for ten in cac_ten:
                if moi[ten] != hien_tai[ten]:
                    self.dat_bat_chuyen_sinh(ten, moi[ten])
        finally:
            self.dang_doi_tat_ca = False
        self.chuyen_sinh_truoc_khi_doi = truoc
        self.ve_lai_bang()

    def kiem_tra_tui(self):
        luong = self.luong_dang_chon()
        if luong:
            luong.kiem_tra_tui()

    def chay_lai(self):
        luong = self.luong_dang_chon()
        if luong:
            luong.chay_lai()
            self.in_log(f"{luong.ten}: xóa đếm thất bại, auto sẽ thử lại")

    def luu_chung(self):
        try:
            gia_tri = {khoa: so_nguyen(self.bien_chung[khoa].get(), nhan) for khoa, nhan in CAI_DAT_CHUNG}
        except ValueError as loi:
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        cau_hinh.dat_chung(gia_tri)
        self.in_log("Đã lưu cài đặt chung")

    # ---------- Tab Tài khoản ----------

    @staticmethod
    def _tu_dang_nhap_khi_diss(tai_khoan):
        if "tu_dang_nhap_khi_diss" in tai_khoan:
            return bool(tai_khoan["tu_dang_nhap_khi_diss"])
        return bool(tai_khoan.get("bat"))

    @staticmethod
    def _tai_khoan_tu_mo_lai_khi_diss(cai_dat):
        """Train đã bật + tích Tự mở lại khi diss (không bắt buộc trùng tab Giao acc chính)."""
        ds, da_co = [], set()
        for tk in cai_dat.get(cau_hinh.KHOA_TK_TRAIN, []):
            ten = (tk.get("ten_dang_nhap") or "").strip()
            if not ten or ten in da_co or not tk.get("mat_khau"):
                continue
            if not tk.get("bat") or not UngDung._tu_dang_nhap_khi_diss(tk):
                continue
            ds.append(tk)
            da_co.add(ten)
        return ds

    def _tai_khoan_pho_ban_mat_cua_so(self, cai_dat):
        """Phó bản đang chạy auto nhưng mất cửa sổ (thường do proxy die) — chỉ khi broker Proxifier bật."""
        ds = []
        for tk in cai_dat.get(cau_hinh.KHOA_TK_PHO_BAN, []):
            ten = (tk.get("ten_dang_nhap") or "").strip()
            if not ten or not tk.get("mat_khau"):
                continue
            tt = self.trang_thai_tai_khoan.get(ten) or ""
            if "PMP" not in tt and "Phó bản" not in tt:
                continue
            if self._co_cua_so_hoac_dang_mo(tk):
                continue
            ds.append(tk)
        return ds

    @staticmethod
    def _khoa_ds_tu_loai(loai):
        return cau_hinh.KHOA_TK_PHO_BAN if loai == "pho_ban" else cau_hinh.KHOA_TK_TRAIN

    @staticmethod
    def _iid_tai_khoan(khoa_ds, ten):
        return f"{khoa_ds}:{ten}"

    @staticmethod
    def _phan_tich_iid_tai_khoan(iid):
        if ":" in iid:
            khoa_ds, ten = iid.split(":", 1)
            return khoa_ds, ten
        return None, iid

    def nap_bang_tai_khoan(self, cai_dat=None):
        cai_dat = cai_dat or cau_hinh.doc_tai_khoan()
        for khoa_ds, bang in self.bang_tk.items():
            bang.delete(*bang.get_children())
            for tai_khoan in cai_dat[khoa_ds]:
                ten = tai_khoan.get("ten_dang_nhap", "")
                if not ten:
                    continue
                iid = self._iid_tai_khoan(khoa_ds, ten)
                if bang.exists(iid):
                    continue
                bang.insert("", "end", iid=iid, values=(
                    O_BAT if tai_khoan.get("bat") else O_TAT, ten, tai_khoan.get("nhan_vat", ""), ""))
        self.ds_tai_khoan_dang_hien = [
            (t.get("ten_dang_nhap"), t.get("nhan_vat"), bool(t.get("bat")), khoa)
            for khoa in (cau_hinh.KHOA_TK_PHO_BAN, cau_hinh.KHOA_TK_TRAIN)
            for t in cai_dat[khoa]]
        self.ve_lai_bang_tai_khoan()

    def _doc_tai_khoan_nhanh(self):
        """tai_khoan.json chỉ đọc lại khi file đổi (vòng vẽ lại giao diện gọi liên tục)."""
        try:
            luc_sua = os.path.getmtime(cau_hinh.DUONG_DAN_TAI_KHOAN)
        except OSError:
            luc_sua = None
        if luc_sua is None or luc_sua != self._tai_khoan_luc_sua:
            self._tai_khoan_dem = cau_hinh.doc_tai_khoan()
            try:
                self._tai_khoan_luc_sua = os.path.getmtime(cau_hinh.DUONG_DAN_TAI_KHOAN)
            except OSError:
                self._tai_khoan_luc_sua = None
        return self._tai_khoan_dem

    def ve_lai_bang_tai_khoan(self):
        theo_ten = {t["ten_dang_nhap"]: t for t in cau_hinh.tat_ca_muc_tai_khoan(self._doc_tai_khoan_nhanh())}
        # Cùng thứ tự ưu tiên như cua_so_cua_tai_khoan, nhưng duyệt cửa sổ (và đọc tiêu đề) một lần cho cả bảng.
        luong_theo_tk, luong_theo_tieu_de = {}, {}
        for luong in self.cac_luong.values():
            if luong.tai_khoan:
                luong_theo_tk.setdefault(luong.tai_khoan.lower(), luong)
        for luong in self.cac_luong.values():
            if not luong.tai_khoan:
                ten_cua_so = luong.ten or ten_trong_tieu_de(luong.hwnd)
                if ten_cua_so:
                    luong_theo_tieu_de.setdefault(chuan_hoa(ten_cua_so), luong)
        for khoa_ds, bang in self.bang_tk.items():
            for iid in bang.get_children():
                _, ten = self._phan_tich_iid_tai_khoan(iid)
                nhan_vat = chuan_hoa(bang.set(iid, "nhan_vat") or "")
                luong = luong_theo_tk.get((ten or "").lower()) \
                    or (luong_theo_tieu_de.get(nhan_vat) if nhan_vat else None)
                if luong:
                    trang_thai = f"Đang online ({luong.ten or ten_trong_tieu_de(luong.hwnd)})"
                elif ten in self.cac_luong_dang_nhap:
                    trang_thai = self.trang_thai_tai_khoan.get(ten, "Đang mở game")
                elif ten in self.tai_khoan_tam_dung:
                    trang_thai = self.trang_thai_tai_khoan.get(ten, "Tạm dừng")
                elif not self._tu_dang_nhap_khi_diss(theo_ten.get(ten, {})):
                    trang_thai = "Không tự mở lại khi diss"
                else:
                    trang_thai = "Chờ mở game"
                dat_o_bang(bang, iid, "trang_thai", trang_thai)

    def _sua_tai_khoan(self, sua):
        """Đọc tai_khoan.json, gọi sua(cai_dat) để đổi, rồi lưu và vẽ lại bảng."""
        cai_dat = cau_hinh.doc_tai_khoan()
        sua(cai_dat)
        cau_hinh.luu_tai_khoan(cai_dat)
        self.nap_bang_tai_khoan(cai_dat)

    def _bam_vao_bang_tai_khoan(self, su_kien, khoa_ds):
        bang = self.bang_tk[khoa_ds]
        if (bang.identify_region(su_kien.x, su_kien.y) != "cell"
                or bang.identify_column(su_kien.x) != "#1"):
            return
        iid = bang.identify_row(su_kien.y)
        if not iid:
            return
        _, ten = self._phan_tich_iid_tai_khoan(iid)
        loai = "phó bản" if khoa_ds == cau_hinh.KHOA_TK_PHO_BAN else "train"
        cot = "XV" if khoa_ds == cau_hinh.KHOA_TK_PHO_BAN else "Bật"

        def sua(cai_dat):
            for tai_khoan in cai_dat[khoa_ds]:
                if tai_khoan["ten_dang_nhap"] == ten:
                    tai_khoan["bat"] = not tai_khoan.get("bat")
                    self.in_log(f"{'BẬT' if tai_khoan['bat'] else 'TẮT'} {cot} ({loai}) cho tài khoản {ten}")
        self.tai_khoan_tam_dung.discard(ten)
        self._sua_tai_khoan(sua)

    def _double_click_bang_tai_khoan(self, su_kien, khoa_ds):
        """Double-click dòng (trừ cột XV/Bật) → mở client và đăng nhập tài khoản đó."""
        bang = self.bang_tk[khoa_ds]
        if bang.identify_region(su_kien.x, su_kien.y) != "cell":
            return
        if bang.identify_column(su_kien.x) == "#1":
            return
        iid = bang.identify_row(su_kien.y)
        if not iid:
            return
        _, ten = self._phan_tich_iid_tai_khoan(iid)
        tai_khoan, _ = cau_hinh.muc_tai_khoan(ten)
        if not tai_khoan:
            return
        nhan_vat = f" ({tai_khoan['nhan_vat']})" if tai_khoan.get("nhan_vat") else ""
        self._khoi_dong_luong_dang_nhap(
            tai_khoan,
            ly_do_log=f"[Bấm tài khoản] Mở game và đăng nhập {ten}{nhan_vat}",
        )

    def _khoi_dong_luong_dang_nhap(self, tai_khoan, cai_dat=None, ly_do_log=None):
        """Một luồng LuongDangNhap (proxy qua dang_nhap.dieu_khien). Trả về True nếu đã start."""
        ten = (tai_khoan.get("ten_dang_nhap") or "").strip()
        if not ten:
            messagebox.showwarning("Đăng nhập", "Chưa có tên tài khoản")
            return False
        if not tai_khoan.get("mat_khau"):
            messagebox.showwarning("Đăng nhập", f"Tài khoản {ten} chưa có mật khẩu (Thêm / Sửa rồi Lưu)")
            return False
        if self._chan_neu_chua_kich_hoat():
            return False
        luong_cu = self.cac_luong_dang_nhap.get(ten)
        if luong_cu and luong_cu.is_alive():
            messagebox.showinfo("Đăng nhập", f"{ten} đang được mở game / đăng nhập")
            return False
        if self.cua_so_cua_tai_khoan(tai_khoan):
            messagebox.showinfo("Đăng nhập", f"{ten} đã có cửa sổ game (đang online hoặc đang auto)")
            return False
        cai_dat = cai_dat or cau_hinh.doc_tai_khoan()
        dang_mo = sum(1 for luong in self.cac_luong_dang_nhap.values() if luong.is_alive())
        if dang_mo >= cai_dat["so_game_mo_cung_luc"]:
            messagebox.showwarning(
                "Đăng nhập",
                f"Đã có {dang_mo} luồng mở game (giới hạn {cai_dat['so_game_mo_cung_luc']} — "
                "sửa ở ô Số game mở cùng lúc)",
            )
            return False
        self.tai_khoan_tam_dung.discard(ten)
        self.in_log(ly_do_log or f"Mở game và đăng nhập tài khoản {ten}")
        self.trang_thai_tai_khoan[ten] = "Đang mở game"
        self.cac_luong_dang_nhap[ten] = LuongDangNhap(tai_khoan, cai_dat, self.hang_doi)
        self.cac_luong_dang_nhap[ten].start()
        return True

    def _chon_tai_khoan(self, _su_kien=None, khoa_ds=None):
        if khoa_ds is None:
            return
        self.khoa_ds_tk_dang_chon = khoa_ds
        bang = self.bang_tk[khoa_ds]
        chon = bang.selection()
        if not chon:
            return
        _, ten = self._phan_tich_iid_tai_khoan(chon[0])
        tai_khoan, _ = cau_hinh.muc_tai_khoan(ten)
        if not tai_khoan:
            return
        for khoa, bien in self.bien_tai_khoan.items():
            bien.set(tai_khoan.get(khoa, ""))
        self.bien_tu_dang_nhap_khi_diss.set(self._tu_dang_nhap_khi_diss(tai_khoan))
        self.bien_loai_tai_khoan.set("pho_ban" if khoa_ds == cau_hinh.KHOA_TK_PHO_BAN else "train")

    def doc_o_tai_khoan(self):
        return {"ten_dang_nhap": self.bien_tai_khoan["ten_dang_nhap"].get().strip(),
                "mat_khau": self.bien_tai_khoan["mat_khau"].get(),
                "nhan_vat": self.bien_tai_khoan["nhan_vat"].get().strip(),
                "tu_dang_nhap_khi_diss": self.bien_tu_dang_nhap_khi_diss.get()}

    def luu_tai_khoan_dang_sua(self):
        """Các ô tài khoản đang sửa một tài khoản đã có trong bảng (và khác với đã lưu) thì lưu luôn."""
        moi = self.doc_o_tai_khoan()
        cu, _ = cau_hinh.muc_tai_khoan(moi["ten_dang_nhap"])
        if cu and moi["mat_khau"] and any(cu.get(khoa, "") != gia_tri for khoa, gia_tri in moi.items()):
            self.them_sua_tai_khoan()

    def _tk_trung_danh_sach_khac(self, ten, bo_qua_khoa):
        cai_dat = cau_hinh.doc_tai_khoan()
        for khoa in (cau_hinh.KHOA_TK_PHO_BAN, cau_hinh.KHOA_TK_TRAIN):
            if khoa == bo_qua_khoa:
                continue
            if any(t["ten_dang_nhap"] == ten for t in cai_dat[khoa]):
                return khoa
        return None

    @staticmethod
    def _danh_sach_tk_theo_khoang(dau, cuoi):
        """caychay10 + caychay100 → caychay10..caychay100 (cùng prefix)."""
        m1, m2 = re.match(r"^(.+?)(\d+)$", dau.strip()), re.match(r"^(.+?)(\d+)$", cuoi.strip())
        if not m1 or not m2 or m1.group(1) != m2.group(1):
            raise ValueError("Tài khoản và Đến TK phải cùng kiểu (vd. caychay10 và caychay100)")
        a, b = int(m1.group(2)), int(m2.group(2))
        if a > b:
            a, b = b, a
        pre = m1.group(1)
        return [f"{pre}{i}" for i in range(a, b + 1)]

    def them_tai_khoan_hang_loat(self):
        dau = self.bien_tai_khoan["ten_dang_nhap"].get().strip()
        cuoi = self.bien_tai_khoan_den.get().strip()
        mat_khau = self.bien_tai_khoan["mat_khau"].get()
        if not dau or not cuoi or not mat_khau:
            messagebox.showerror("Thiếu thông tin", "Cần Tài khoản (đầu), Đến TK (cuối) và Mật khẩu chung")
            return
        try:
            ds_ten = self._danh_sach_tk_theo_khoang(dau, cuoi)
        except ValueError as loi:
            messagebox.showerror("Sai định dạng", str(loi))
            return
        if len(ds_ten) > 500:
            messagebox.showerror("Quá nhiều", f"{len(ds_ten)} tài khoản — tối đa 500 mỗi lần")
            return
        if not messagebox.askyesno("Thêm hàng loạt",
                                   f"Thêm {len(ds_ten)} tài khoản ({ds_ten[0]} … {ds_ten[-1]}) "
                                   f"vào bảng {'phó bản' if self.bien_loai_tai_khoan.get() == 'pho_ban' else 'train'}?"):
            return
        mau = self.doc_o_tai_khoan()
        khoa_ds = self._khoa_ds_tu_loai(self.bien_loai_tai_khoan.get())
        them = 0

        def sua(cai_dat):
            nonlocal them
            for ten in ds_ten:
                if self._tk_trung_danh_sach_khac(ten, khoa_ds):
                    continue
                if any(t["ten_dang_nhap"] == ten for t in cai_dat[khoa_ds]):
                    continue
                muc = dict(mau, ten_dang_nhap=ten, mat_khau=mat_khau, nhan_vat="")
                cai_dat[khoa_ds].append(dict(muc, bat=True, tu_dang_nhap_khi_diss=muc["tu_dang_nhap_khi_diss"]))
                them += 1
        self.khoa_ds_tk_dang_chon = khoa_ds
        self._sua_tai_khoan(sua)
        self.in_log(f"Đã thêm hàng loạt {them}/{len(ds_ten)} tài khoản "
                    f"({'phó bản' if khoa_ds == cau_hinh.KHOA_TK_PHO_BAN else 'train'})")

    def them_sua_tai_khoan(self):
        moi = self.doc_o_tai_khoan()
        if not moi["ten_dang_nhap"] or not moi["mat_khau"]:
            messagebox.showerror("Thiếu thông tin", "Cần nhập tài khoản và mật khẩu (nhân vật có thể để trống)")
            return
        khoa_ds = self._khoa_ds_tu_loai(self.bien_loai_tai_khoan.get())
        khoa_khac = self._tk_trung_danh_sach_khac(moi["ten_dang_nhap"], khoa_ds)
        if khoa_khac:
            loai = "phó bản" if khoa_khac == cau_hinh.KHOA_TK_PHO_BAN else "train"
            messagebox.showerror("Trùng tài khoản",
                                 f"{moi['ten_dang_nhap']} đã có trong bảng {loai}. Xóa ở bảng kia trước khi chuyển.")
            return

        def sua(cai_dat):
            for tai_khoan in cai_dat[khoa_ds]:
                if tai_khoan["ten_dang_nhap"] == moi["ten_dang_nhap"]:
                    tai_khoan.update(moi)
                    self.in_log(f"Đã sửa tài khoản {moi['ten_dang_nhap']} ({'phó bản' if khoa_ds == cau_hinh.KHOA_TK_PHO_BAN else 'train'})")
                    return
            cai_dat[khoa_ds].append(dict(moi, bat=True, tu_dang_nhap_khi_diss=moi["tu_dang_nhap_khi_diss"]))
            self.in_log(f"Đã thêm tài khoản {moi['ten_dang_nhap']} ({'phó bản' if khoa_ds == cau_hinh.KHOA_TK_PHO_BAN else 'train'})")
        self.khoa_ds_tk_dang_chon = khoa_ds
        self.tai_khoan_tam_dung.discard(moi["ten_dang_nhap"])
        self._sua_tai_khoan(sua)

    def xoa_tai_khoan(self):
        """Xóa tài khoản đang chọn hoặc đang tích XV/Bật trong bảng đang thao tác."""
        xoa = set()
        for khoa_ds, bang in self.bang_tk.items():
            for iid in bang.selection():
                _, ten = self._phan_tich_iid_tai_khoan(iid)
                xoa.add(ten)
            for tai_khoan in cau_hinh.doc_tai_khoan()[khoa_ds]:
                if tai_khoan.get("bat"):
                    xoa.add(tai_khoan["ten_dang_nhap"])
        if not xoa or not messagebox.askyesno("Xóa tài khoản",
                                              f"Xóa {len(xoa)} tài khoản khỏi danh sách?\n" + ", ".join(sorted(xoa))):
            return

        def sua(cai_dat):
            for khoa in (cau_hinh.KHOA_TK_PHO_BAN, cau_hinh.KHOA_TK_TRAIN):
                cai_dat[khoa] = [t for t in cai_dat[khoa] if t["ten_dang_nhap"] not in xoa]
        self.tai_khoan_tam_dung.difference_update(xoa)
        self._sua_tai_khoan(sua)
        self.in_log(f"Đã xóa tài khoản {', '.join(sorted(xoa))}")

    def xoa_tat_ca_tai_khoan(self):
        cai_dat = cau_hinh.doc_tai_khoan()
        so = len(cai_dat[cau_hinh.KHOA_TK_PHO_BAN]) + len(cai_dat[cau_hinh.KHOA_TK_TRAIN])
        if not so or not messagebox.askyesno("Xóa tất cả tài khoản", f"Xóa cả {so} tài khoản (phó bản + train)?"):
            return

        def sua(cai_dat):
            cai_dat[cau_hinh.KHOA_TK_PHO_BAN] = []
            cai_dat[cau_hinh.KHOA_TK_TRAIN] = []
        self.tai_khoan_tam_dung.clear()
        self._sua_tai_khoan(sua)
        self.in_log(f"Đã xóa tất cả {so} tài khoản")

    def bat_tat_ca_tai_khoan(self, khoa_ds):
        """Bấm tiêu đề cột XV/Bật: còn tài khoản chưa bật thì bật hết, không thì tắt hết."""
        ket_qua = {}
        loai = "phó bản" if khoa_ds == cau_hinh.KHOA_TK_PHO_BAN else "train"
        cot = "XV" if khoa_ds == cau_hinh.KHOA_TK_PHO_BAN else "Bật"

        def sua(cai_dat):
            ds = cai_dat[khoa_ds]
            bat = not all(t.get("bat") for t in ds) if ds else False
            for tai_khoan in ds:
                tai_khoan["bat"] = bat
            ket_qua.update(bat=bat, so=len(ds))
        self._sua_tai_khoan(sua)
        if ket_qua.get("so"):
            if ket_qua["bat"]:
                self.tai_khoan_tam_dung.clear()
            self.in_log(f"{'BẬT' if ket_qua['bat'] else 'TẮT'} {cot} cho tất cả {ket_qua['so']} tài khoản {loai}")

    def doi_mat_ket_noi(self):
        bat = self.bien_mat_ket_noi.get()
        cau_hinh.dat_chung({"tu_thoat_khi_mat_ket_noi": bat})
        self.in_log(f"{'BẬT' if bat else 'TẮT'} tự xử lý hộp mất kết nối (Duyệt kết nối lại, không được thì Đóng game)"
                    + (" - tích \"Tự mở lại khi diss\" cho từng tài khoản ở tab Tài khoản để game tắt rồi được mở lại"
                       if bat else ""))

    def doi_giai_ma_vao_game(self):
        bat = self.bien_giai_ma_vao_game.get()

        def sua(cai_dat):
            cai_dat["giai_ma_kiem_tra"] = bat
        self._sua_tai_khoan(sua)
        self.in_log("Khi vào game: " + ("giải mã kiểm tra" if bat else "nhập mã kiểm tra cố định")
                    + " (áp dụng từ lần đăng nhập sau)")

    def chon_duong_dan_gauto(self):
        """Chọn thư mục GAuto (vd. AutoTLBB); tự điền ChickenAuto.exe nếu có trong thư mục."""
        hien_tai = self.bien_at_duong_dan_gauto.get().strip()
        if hien_tai and os.path.isfile(hien_tai):
            thu_muc = os.path.dirname(hien_tai)
        elif hien_tai and os.path.isdir(hien_tai):
            thu_muc = hien_tai
        else:
            thu_muc = None
        thu_muc = filedialog.askdirectory(
            parent=self.root,
            title="Chọn thư mục GAuto (ChickenAuto / AutoTLBB)",
            initialdir=thu_muc if thu_muc and os.path.isdir(thu_muc) else None,
        )
        if not thu_muc:
            return
        from gauto_ac_tac import CAC_TEN_EXE_GAUTO

        for ten_file in CAC_TEN_EXE_GAUTO:
            duong = os.path.join(thu_muc, ten_file)
            if os.path.isfile(duong):
                self.bien_at_duong_dan_gauto.set(duong)
                self.luu_ac_tac()
                return
        duong = filedialog.askopenfilename(
            parent=self.root,
            title="Không thấy GAuto_2025.exe / ChickenAuto.exe — chọn file",
            initialdir=thu_muc,
            filetypes=[("GAuto", "GAuto*.exe"), ("ChickenAuto", "ChickenAuto.exe"), ("File chạy", "*.exe"),
                       ("Tất cả", "*.*")],
        )
        if duong:
            self.bien_at_duong_dan_gauto.set(duong)
            self.luu_ac_tac()

    def test_gauto(self):
        """Chạy thử điều khiển GAuto từng bước (log ở khung Nhật ký), không cần tới giờ Ác Tặc."""
        duong = self.bien_at_duong_dan_gauto.get().strip()
        if not duong:
            messagebox.showwarning("Test GAuto", "Chọn đường dẫn GAuto_2025.exe trước (nút Chọn...)", parent=self.root)
            return
        ten = simpledialog.askstring("Test GAuto", "Tên nhân vật (đội trưởng) trong bảng GAuto để test\n"
                                                   "(để trống = dòng đang chọn trong GAuto)", parent=self.root)
        if ten is None:
            return
        cac_map = [m for m in self.at_thu_tu if m in self.at_da_chon]
        bat_thu = messagebox.askyesno(
            "Test GAuto", f"Chọn map «{cac_map[0] if cac_map else '?'}» (map đầu danh sách AutoHoc) trên GAuto bằng chuột, "
                          "tích thử ô «Ác Tặc» 3 giây rồi bỏ tích?\nTrong lúc chọn map (~1 giây) đừng động chuột.\n\n"
                          "Không = chỉ đọc, không bấm gì trên GAuto.", parent=self.root)

        def chay():
            log = lambda chu: self.hang_doi.put(("log", chu))  # noqa: E731
            try:
                gauto_ac_tac.test_gauto(duong, ten.strip(), log, bat_thu, cac_map_autohoc=cac_map)
            except gauto_ac_tac.LoiGautoAcTac as loi:
                log(f"Test GAuto: LỖI — {loi}")
                if str(loi) == gauto_ac_tac.THONG_BAO_CAN_ADMIN:
                    self.root.after(0, self.hoi_chay_lai_quyen_admin)
            except Exception:
                log(f"Test GAuto: lỗi không mong đợi\n{traceback.format_exc()}")

        threading.Thread(target=chay, daemon=True).start()

    def hoi_chay_lai_quyen_admin(self):
        if not messagebox.askyesno("Test GAuto", "GAuto chạy quyền Admin nên AutoHoc cũng phải chạy quyền Admin mới "
                                                 "điều khiển được.\n\nĐóng AutoHoc và mở lại bằng quyền Admin ngay "
                                                 "(Windows sẽ hỏi xác nhận)?", parent=self.root):
            return
        if not gauto_ac_tac.chay_lai_quyen_admin():
            messagebox.showerror("Test GAuto", "Không mở lại được AutoHoc quyền Admin (đã bấm No ở hộp Windows?) — "
                                               "chuột phải AutoHoc.exe → Run as administrator", parent=self.root)
            return
        self.thoat()

    def chon_thu_muc_game(self):
        """Chọn file Game.exe của máy đang dùng; thư mục game là thư mục chứa Bin."""
        hien_tai = self.bien_dang_nhap["thu_muc_game"].get().strip()
        thu_muc_bin = os.path.join(hien_tai, "Bin")
        duong_dan = filedialog.askopenfilename(
            parent=self.root, title="Chọn file Game.exe (trong thư mục Bin của game)",
            initialdir=thu_muc_bin if os.path.isdir(thu_muc_bin) else hien_tai or None,
            filetypes=[("Game.exe", "Game.exe"), ("File chạy", "*.exe")])
        if not duong_dan:
            return
        thu_muc = os.path.dirname(os.path.normpath(duong_dan))
        if os.path.basename(thu_muc).lower() == "bin":
            thu_muc = os.path.dirname(thu_muc)
        if not cau_hinh.la_thu_muc_game(thu_muc):
            messagebox.showerror("Chưa đúng file", "Hãy chọn file Game.exe nằm trong thư mục Bin của game")
            return
        self.bien_dang_nhap["thu_muc_game"].set(thu_muc)
        self.luu_cai_dat_dang_nhap()

    def chon_pf_exe(self):
        duong = filedialog.askopenfilename(
            parent=self.root, title="Chọn Proxifier.exe", filetypes=[("Proxifier", "Proxifier.exe"), ("exe", "*.exe")])
        if duong:
            self.bien_pf_exe.set(duong)
            self._ap_dung_phat_hien_proxifier()

    def _ap_dung_phat_hien_proxifier(self, ghi_log=True):
        exe = self.bien_pf_exe.get().strip()
        if not exe:
            return
        ph = proxy_broker_ui.phat_hien_tu_exe(exe)
        if ph.get("profile_ppx"):
            self.bien_pf_ppx.set(ph["profile_ppx"])
        if ph.get("log_file"):
            self.bien_pf_log.set(ph["log_file"])
        if ghi_log and ph:
            self.in_log(
                "[Proxifier] Tự nhận: "
                + (f"profile {ph.get('profile_ppx', '—')}" if ph.get("profile_ppx") else "")
                + (f", log {ph.get('log_file')}" if ph.get("log_file") else " (chưa thấy log — bật ghi log trong Proxifier)")
            )

    def chon_pf_ppx(self):
        duong = filedialog.askopenfilename(
            parent=self.root, title="Chọn profile Proxifier", filetypes=[("Profile", "*.ppx"), ("Tất cả", "*.*")])
        if duong:
            self.bien_pf_ppx.set(duong)

    def chon_pf_log(self):
        duong = filedialog.askopenfilename(
            parent=self.root,
            title="Chọn file log Proxifier (không phải proxy_broker.log)",
            filetypes=[("Log", "*.txt"), ("Tất cả", "*.*")])
        if duong:
            self.bien_pf_log.set(duong)

    def luu_proxy_broker(self):
        try:
            cfg = proxy_broker_ui.doc_config()
        except (OSError, json.JSONDecodeError):
            cfg = {}
        exe = self.bien_pf_exe.get().strip()
        cfg = proxy_broker_ui.ap_dung_phat_hien_len_config(exe, cfg)
        cfg["profile_ppx"] = self.bien_pf_ppx.get().strip() or cfg.get("profile_ppx") or ""
        cfg["log_file"] = self.bien_pf_log.get().strip() or cfg.get("log_file") or ""
        self.bien_pf_ppx.set(cfg.get("profile_ppx") or "")
        self.bien_pf_log.set(cfg.get("log_file") or "")
        proxy_broker_ui.ghi_config(cfg)
        self.in_log("Đã lưu cấu hình Proxifier (proxy_broker.json)")

    def chay_proxy_broker(self):
        self._ap_dung_phat_hien_proxifier(ghi_log=False)
        self.luu_proxy_broker()
        if self._proc_proxy_broker and self._proc_proxy_broker.poll() is None:
            messagebox.showinfo("Proxy Broker", "Broker đang chạy")
            return
        try:
            self._proc_proxy_broker = proxy_broker_ui.chay_broker_daemon()
        except (OSError, RuntimeError) as loi:
            messagebox.showerror("Proxy Broker", str(loi))
            self.in_log(f"[Proxy Broker] Lỗi khởi chạy: {loi}")
            return
        con_chay, loi = proxy_broker_ui.kiem_tra_vua_chay(self._proc_proxy_broker)
        if not con_chay:
            self._proc_proxy_broker = None
            messagebox.showerror("Proxy Broker", loi)
            self.in_log(f"[Proxy Broker] Không chạy được — xem proxy_broker.log")
            for dong in loi.splitlines()[-5:]:
                if dong.strip():
                    self.in_log(f"  {dong}")
            return
        chay, pid = proxy_broker_ui.broker_dang_chay(self._proc_proxy_broker)
        self.in_log(
            f"[Proxy Broker] Đã khởi chạy nền (PID {pid}). "
            f"Theo dõi: dòng trạng thái xanh/vàng bên dưới + file proxy_broker.log"
        )
        self.cap_nhat_trang_thai_proxy_broker()

    def dung_proxy_broker(self):
        if proxy_broker_ui.dung_broker(self._proc_proxy_broker):
            self._proc_proxy_broker = None
            self.in_log("[Proxy Broker] Đã dừng")
            self.cap_nhat_trang_thai_proxy_broker()
            return
        self._proc_proxy_broker = None
        self.in_log("[Proxy Broker] Không thấy process đang chạy")
        self.cap_nhat_trang_thai_proxy_broker()

    def _lap_cap_nhat_proxy_broker(self):
        self.cap_nhat_trang_thai_proxy_broker()
        self.root.after(2000, self._lap_cap_nhat_proxy_broker)

    def cap_nhat_trang_thai_proxy_broker(self):
        if not getattr(self, "nhan_pf_trang_thai", None):
            return
        try:
            chuoi, mau, chay = proxy_broker_ui.mo_ta_hien_thi(self._proc_proxy_broker)
            dong = chuoi.split("\n", 1)
            self.nhan_pf_broker_led.config(text=dong[0], foreground=mau)
            self.nhan_pf_trang_thai.config(text=dong[1] if len(dong) > 1 else "")
            if getattr(self, "khung_pf", None):
                phu = " — broker đang chạy" if chay else ""
                self.khung_pf.config(text=f"Proxifier + Proxy Broker{phu}")
        except tk.TclError:
            pass
        st = proxy_broker_ui.doc_state()
        health = st.get("health")
        if chay and not self._pf_broker_chay_truoc:
            self.in_log(f"[Proxy Broker] Đang chạy — health={health or '—'}")
        if self._pf_broker_chay_truoc and not chay:
            self.in_log("[Proxy Broker] Đã tắt (process không còn). Xem proxy_broker.log nếu lỗi.")
        if health != self._pf_health_truoc and health and self._pf_health_truoc:
            tb = (st.get("thong_bao") or "").strip()
            self.in_log(f"[Proxy Broker] Health → {health}" + (f" — {tb}" if tb else ""))
        fo = st.get("failover_luc")
        if chay and fo and fo != self._pf_failover_luc_truoc:
            tb = (st.get("thong_bao") or "").strip()
            self.in_log(
                "[Proxy Broker] Đã đổi proxy khi game đang chạy — "
                + (tb if tb else "auto phó bản / train tiếp tục sau khi game nối lại mạng.")
            )
            self._pf_failover_luc_truoc = fo
        px = st.get("proxy_active") or {}
        gan_luc = px.get("gan_luc")
        if (
            chay
            and health == "healthy"
            and gan_luc
            and gan_luc != self._pf_gan_luc_da_login
            and proxy_broker_ui.doc_config().get("auto_login_sau_gan", True)
        ):
            self._proxy_broker_tu_dang_nhap(px, st)
            self._pf_gan_luc_da_login = gan_luc
        self._pf_broker_chay_truoc = chay
        self._pf_health_truoc = health
        if self._proc_proxy_broker and self._proc_proxy_broker.poll() is not None:
            self._proc_proxy_broker = None

    def _proxy_broker_tu_dang_nhap(self, proxy_active, state_broker):
        """Sau khi broker gắn proxy healthy — mở game tài khoản đầu tiên trong danh sách."""
        if not state_broker.get("cho_phep_login_them", True):
            self.in_log(
                "[Proxy Broker] Đã 4 game/IP — chờ slot trước khi tự đăng nhập thêm."
            )
            return False
        ip = proxy_active.get("host", "?")
        ms = proxy_active.get("latency_ms")
        phu = f"IP {ip}"
        if ms is not None:
            phu += f", ~{ms}ms"
        cai_dat = cau_hinh.doc_tai_khoan()
        for khoa in (cau_hinh.KHOA_TK_PHO_BAN, cau_hinh.KHOA_TK_TRAIN):
            for tk in cai_dat.get(khoa, []):
                if not (tk.get("ten_dang_nhap") or "").strip():
                    continue
                if not tk.get("mat_khau"):
                    continue
                ten = tk["ten_dang_nhap"].strip()
                ly_do = f"[Proxy Broker] Proxy đã gắn ({phu}) — tự mở game đăng nhập {ten}"
                if self._khoi_dong_luong_dang_nhap(tk, cai_dat, ly_do_log=ly_do):
                    return True
        self.in_log("[Proxy Broker] Không có tài khoản (có mật khẩu) để tự đăng nhập.")
        return False

    def luu_cai_dat_dang_nhap(self):
        self.luu_tai_khoan_dang_sua()
        try:
            gia_tri = {}
            for khoa, nhan, _ in CAI_DAT_DANG_NHAP:
                chu = self.bien_dang_nhap[khoa].get().strip()
                if khoa in CAC_O_SO_DANG_NHAP:
                    gia_tri[khoa] = so_nguyen(chu, nhan)
                    if gia_tri[khoa] < 1:
                        raise ValueError(f"{nhan} phải lớn hơn 0")
                elif not chu:
                    raise ValueError(f"Chưa nhập {nhan}")
                else:
                    gia_tri[khoa] = chu
            if not os.path.isfile(os.path.join(gia_tri["thu_muc_game"], "Bin", "Game.exe")):
                raise ValueError("Thư mục game phải chứa Bin\\Game.exe")
        except ValueError as loi:
            messagebox.showerror("Cài đặt chưa đúng", str(loi))
            return
        self._sua_tai_khoan(lambda cai_dat: cai_dat.update(gia_tri))
        px_cu = dict(cau_hinh.chung().get("proxy") or {})
        px_cu["bat"] = False
        cau_hinh.dat_chung({"proxy": px_cu})
        self.tai_khoan_tam_dung.clear()
        self.in_log("Đã lưu cài đặt tự đăng nhập")

    # ---------- Tự mở game và đăng nhập ----------

    def _co_cua_so_hoac_dang_mo(self, tai_khoan):
        if self.cua_so_cua_tai_khoan(tai_khoan):
            return True
        ten = tai_khoan.get("ten_dang_nhap")
        luong = self.cac_luong_dang_nhap.get(ten)
        if luong and luong.is_alive():
            return True
        from xoay_vong import tim_hwnd_cua_tai_khoan
        return bool(tim_hwnd_cua_tai_khoan(ten))

    def cua_so_cua_tai_khoan(self, tai_khoan):
        """
        Luồng của cửa sổ game đang dùng tài khoản này, None nếu không có. So theo tên tài khoản đọc trong game;
        cửa sổ chưa đọc được tài khoản thì so tên nhân vật (trên tiêu đề cửa sổ) với nhân vật ghi trong tài khoản.
        """
        ten = tai_khoan.get("ten_dang_nhap", "").lower()
        nhan_vat = chuan_hoa(tai_khoan.get("nhan_vat") or "")
        for luong in self.cac_luong.values():
            if luong.tai_khoan and luong.tai_khoan.lower() == ten:
                return luong
        for luong in self.cac_luong.values():
            ten_cua_so = luong.ten or ten_trong_tieu_de(luong.hwnd)
            if nhan_vat and not luong.tai_khoan and ten_cua_so and chuan_hoa(ten_cua_so) == nhan_vat:
                return luong
        return None

    def hoc_nhan_vat(self, tt):
        """Tài khoản chưa ghi tên nhân vật thì ghi tên nhân vật đang chơi, lần sau bị diss sẽ tự vào lại nhân vật đó."""
        tai_khoan = tt["tai_khoan"].lower()
        if not tai_khoan or not any(ten and ten.lower() == tai_khoan and not nhan_vat
                                    for ten, nhan_vat, _, _ in self.ds_tai_khoan_dang_hien or ()):
            return

        def sua(cai_dat):
            for khoa in (cau_hinh.KHOA_TK_PHO_BAN, cau_hinh.KHOA_TK_TRAIN):
                for muc in cai_dat[khoa]:
                    if muc.get("ten_dang_nhap", "").lower() == tai_khoan and not muc.get("nhan_vat"):
                        muc["nhan_vat"] = tt["ten"]
        self._sua_tai_khoan(sua)
        self.in_log(f"Tài khoản {tai_khoan} đang chơi nhân vật {tt['ten']}, đã ghi vào tai_khoan.json "
                    "(bị diss sẽ tự đăng nhập lại nhân vật này)")

    def da_nhan_ra_moi_cua_so(self):
        """
        Cửa sổ chưa đọc được tài khoản (mới mở auto, game mới mở, đang kết nối...) có thể chính là tài khoản cần
        tìm, nên chờ; quá lâu vẫn chưa đọc được mới coi như không phải, để không đăng nhập đè (đá nhân vật đang chơi).
        """
        giay_cho = cau_hinh.chung()["giay_cho_game_khoi_dong"] + GIAY_CHO_SAU_KHI_VAO_GAME
        game_dang_dang_nhap = {luong.pid for luong in self.cac_luong_dang_nhap.values()}
        if self.luong_tao_nv and self.luong_tao_nv.is_alive():
            game_dang_dang_nhap.add(self.luong_tao_nv.pid)
        for luong in self.cac_luong.values():
            if luong.tai_khoan or luong.game.lua.pid in game_dang_dang_nhap:
                continue
            if ten_trong_tieu_de(luong.hwnd) and time.time() - luong.luc_tao < GIAY_CHO_SAU_KHI_VAO_GAME:
                return False
            try:
                if time.time() - psutil.Process(luong.game.lua.pid).create_time() < giay_cho:
                    return False
            except psutil.Error:
                pass
        return True

    def dang_giao_acc_chinh(self):
        return self.luong_giao_acc_chinh is not None and self.luong_giao_acc_chinh.is_alive()

    def dang_tu_dang_nhap(self, pid):
        """
        Game này đang có luồng tự đăng nhập / tạo nhân vật mới / xoay vòng (lúc đăng nhập, giao dịch) điều khiển
        (gọi từ luồng của cửa sổ game).
        """
        if client_dang_dang_nhap(pid):
            return True
        if self.luong_xoay_vong and self.luong_xoay_vong.dang_dieu_khien(pid):
            return True
        if self.luong_giao_acc_chinh and self.luong_giao_acc_chinh.dang_dieu_khien(pid):
            return True
        if self.luong_giao_dich_ngay and self.luong_giao_dich_ngay.dang_dieu_khien(pid):
            return True
        return any(luong.pid == pid and luong.is_alive()
                   for luong in list(self.cac_luong_dang_nhap.values()) + [self.luong_tao_nv] if luong)

    def giam_sat_dang_nhap(self):
        """Mỗi 3 giây xem có nhân vật nào trong tab Tài khoản bị diss không, có thì mở game đăng nhập lại."""
        try:
            self._giam_sat_dang_nhap()
            self.loi_giam_sat = None
        except Exception as loi:
            if str(loi) != self.loi_giam_sat:
                self.loi_giam_sat = str(loi)
                self.in_log(f"Lỗi tự đăng nhập (kiểm tra tai_khoan.json):\n{traceback.format_exc()}")
        self.root.after(3000, self.giam_sat_dang_nhap)

    def _giam_sat_dang_nhap(self):
        for ten, luong in list(self.cac_luong_dang_nhap.items()):
            if luong.is_alive():
                continue
            if luong.thanh_cong:
                self.luc_vao_game[ten] = time.time()
            elif not luong.dung.is_set():
                self.tai_khoan_tam_dung.add(ten)
                self.in_log(f"Tạm dừng tự đăng nhập tài khoản {ten} (lý do ở dòng log phía trên). "
                            "Sửa xong thì bấm Thêm / Sửa, Lưu cài đặt, hoặc tắt bật lại tài khoản để thử lại.")
            del self.cac_luong_dang_nhap[ten]

        cai_dat = cau_hinh.doc_tai_khoan()
        ds = [(t.get("ten_dang_nhap"), t.get("nhan_vat"), bool(t.get("bat")), khoa)
              for khoa in (cau_hinh.KHOA_TK_PHO_BAN, cau_hinh.KHOA_TK_TRAIN)
              for t in cai_dat[khoa]]
        if ds != self.ds_tai_khoan_dang_hien:
            self.nap_bang_tai_khoan(cai_dat)
        if not self.da_nhan_ra_moi_cua_so():
            return

        xoay_vong = self.luong_xoay_vong.cac_tai_khoan() if self.luong_xoay_vong else set()
        if self.luong_giao_acc_chinh:
            xoay_vong |= self.luong_giao_acc_chinh.cac_tai_khoan()
        broker_chay, _ = proxy_broker_ui.broker_dang_chay(self._proc_proxy_broker)
        for tai_khoan in self._tai_khoan_tu_mo_lai_khi_diss(cai_dat):
            if (tai_khoan.get("ten_dang_nhap") or "").lower() in xoay_vong:
                continue
            if (sum(not luong.cho_nguoi_choi for luong in self.cac_luong_dang_nhap.values())
                    >= cai_dat["so_game_mo_cung_luc"]):
                break
            ten = tai_khoan.get("ten_dang_nhap")
            if (not ten or not tai_khoan.get("mat_khau")
                    or ten in self.cac_luong_dang_nhap
                    or ten in self.tai_khoan_tam_dung or self._co_cua_so_hoac_dang_mo(tai_khoan)
                    or time.time() - self.luc_vao_game.get(ten, 0) < GIAY_CHO_SAU_KHI_VAO_GAME):
                continue
            nhan_vat = f" ({tai_khoan['nhan_vat']})" if tai_khoan.get("nhan_vat") else ""
            self._khoi_dong_luong_dang_nhap(
                tai_khoan,
                cai_dat=cai_dat,
                ly_do_log=f"Tài khoản {ten}{nhan_vat} không có cửa sổ game nào, tự mở game và đăng nhập",
            )

        if broker_chay:
            for tai_khoan in self._tai_khoan_pho_ban_mat_cua_so(cai_dat):
                ten = (tai_khoan.get("ten_dang_nhap") or "").strip()
                if (ten in self.cac_luong_dang_nhap or ten in self.tai_khoan_tam_dung
                        or time.time() - self.luc_vao_game.get(ten, 0) < GIAY_CHO_SAU_KHI_VAO_GAME):
                    continue
                if sum(not luong.cho_nguoi_choi for luong in self.cac_luong_dang_nhap.values()
                       ) >= cai_dat["so_game_mo_cung_luc"]:
                    break
                nhan_vat = f" ({tai_khoan['nhan_vat']})" if tai_khoan.get("nhan_vat") else ""
                self._khoi_dong_luong_dang_nhap(
                    tai_khoan,
                    cai_dat=cai_dat,
                    ly_do_log=(
                        f"[Proxy Broker] {ten}{nhan_vat} mất cửa sổ khi đang phó bản — "
                        "tự mở game đăng nhập lại (auto PMP tiếp tục sau vào game)"
                    ),
                )

    # ---------- Log ----------

    def _tao_log(self):
        khung = ttk.Frame(self.root, padding=(6, 0, 6, 6))
        # Xếp trước khung tab: cửa sổ thấp thì khung tab co lại (lăn chuột để xem), ô log vẫn hiện đủ.
        khung.pack(side="bottom", fill="both", expand=True, before=self.so_tay)
        self.o_log = tk.Text(khung, height=10, width=70, wrap="word", state="disabled", font=("Segoe UI", 9))
        thanh_cuon = ttk.Scrollbar(khung, command=self.o_log.yview)
        self.o_log.configure(yscrollcommand=thanh_cuon.set)
        thanh_cuon.pack(side="right", fill="y")
        self.o_log.pack(side="left", fill="both", expand=True)

    def _them_dong_log_ui(self, dong):
        self.o_log.configure(state="normal")
        self.o_log.insert("end", dong)
        so_dong = int(self.o_log.index("end-1c").split(".")[0])
        if so_dong > SO_DONG_LOG_TOI_DA:
            self.o_log.delete("1.0", f"{so_dong - SO_DONG_LOG_TOI_DA}.0")
        self.o_log.see("end")
        self.o_log.configure(state="disabled")

    def in_log(self, chu):
        dong_ui = f"[{time.strftime('%H:%M:%S')}] {chu}\n"
        hom_nay = time.strftime("%Y-%m-%d")
        if hom_nay != self._nhat_ky_hom_nay:
            self._nhat_ky_hom_nay = hom_nay
            if don_nhat_ky_sang_ngay_moi(self._duong_dan_nhat_ky):
                self._them_dong_log_ui(f"[{time.strftime('%H:%M:%S')}] Đã xóa nhật ký file (sang ngày mới).\n")
        if not self._nhat_ky_file_loi:
            try:
                with open(self._duong_dan_nhat_ky, "a", encoding="utf-8") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {chu}\n")
            except OSError as loi:
                if self._duong_dan_nhat_ky == NHAT_KY_CANH_EXE:
                    moi = _chon_duong_dan_nhat_ky()
                    if moi != NHAT_KY_CANH_EXE:
                        self._duong_dan_nhat_ky = moi
                        don_nhat_ky_sang_ngay_moi(self._duong_dan_nhat_ky)
                        try:
                            with open(self._duong_dan_nhat_ky, "a", encoding="utf-8") as f:
                                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {chu}\n")
                            self._them_dong_log_ui(
                                f"[{time.strftime('%H:%M:%S')}] Nhật ký file chuyển sang {self._duong_dan_nhat_ky} "
                                f"(thư mục exe không ghi được — thường gặp trên máy ảo).\n")
                            self._them_dong_log_ui(dong_ui)
                            return
                        except OSError:
                            pass
                self._nhat_ky_file_loi = True
                canh_bao = (f"[{time.strftime('%H:%M:%S')}] Không ghi được nhật ký file ({loi}) — "
                            "chỉ hiện trên giao diện. Đặt AutoHoc vào ổ C: trong VM hoặc tắt chia sẻ thư mục từ host.\n")
                self._them_dong_log_ui(canh_bao)
        self._them_dong_log_ui(dong_ui)

    # ---------- Vòng cập nhật ----------

    def quet_cua_so(self):
        """Mỗi 2 giây tìm cửa sổ game mới và tạo luồng cho nó."""
        try:
            for cua_so in tim_cua_so_game():
                hwnd = cua_so["hwnd"]
                if hwnd in self.cac_luong:
                    continue
                try:
                    luong = LuongNhanVat(hwnd, self.hang_doi, lambda: self.nhom_hien_tai, self.dang_tu_dang_nhap,
                                         self.dang_giao_acc_chinh, lambda: list(self.cac_luong.values()))
                except LoiLua:
                    continue
                self.cac_luong[hwnd] = luong
                self.bang.insert("", "end", iid=str(hwnd),
                                 values=(O_TAT, "", cua_so["tieu_de"].split(" - ")[0], "", "Đang kết nối..."))
                luong.start()
        except Exception:
            self.in_log(f"Lỗi khi tìm cửa sổ game:\n{traceback.format_exc()}")
        try:
            self._dong_bo_o_tich()
        except Exception:
            self.in_log(f"Lỗi khi cập nhật ô tích:\n{traceback.format_exc()}")
        self.root.after(2000, self.quet_cua_so)

    def _dong_bo_o_tich(self):
        """Cài đặt bị luồng khác đổi (vd. xoay vòng bật Tự mời nhóm / Tự động đánh) thì cho ô tích hiện theo."""
        chung = cau_hinh.chung()
        for bien, khoa in ((self.bien_moi_nhom, "bat_moi_nhom"), (self.bien_moi_nhan_vat_auto, "bat_moi_nhan_vat_auto")):
            if bien.get() != chung[khoa]:
                bien.set(chung[khoa])
        if self.root.focus_get() is not self.chon_truong_nhom and self.bien_truong_nhom.get() != chung["truong_nhom"]:
            self.bien_truong_nhom.set(chung["truong_nhom"])
        for ve_lai in self.cac_ve_lai_ds:
            ve_lai()
        if self.ten_dang_sua is not None:
            bat = cai_dat_chien_dau(cau_hinh.cua_nhan_vat(self.ten_dang_sua))["bat"]
            if self.bien_cd["bat"].get() != bat:
                self.bien_cd["bat"].set(bat)

    def xu_ly_hang_doi(self):
        co_tin = False
        while True:
            try:
                tin = self.hang_doi.get_nowait()
            except queue.Empty:
                break
            co_tin = True
            loai, *noi_dung = tin
            if loai == "log":
                self.in_log(noi_dung[0])
            elif loai == "cap_nhat":
                hwnd, tt = noi_dung
                self.thong_tin[hwnd] = tt
                self.loi.pop(hwnd, None)
                self.hoc_nhan_vat(tt)
            elif loai == "chua_vao_game":
                self.thong_tin.pop(noi_dung[0], None)
                self.doi_hinh_nhom.pop(noi_dung[0], None)
                self.loi.pop(noi_dung[0], None)
            elif loai == "loi":
                hwnd, chu = noi_dung
                self.loi[hwnd] = chu
            elif loai == "mat":
                self.xoa_cua_so(noi_dung[0])
            elif loai == "trang_thai_tai_khoan":
                ten, mo_ta = noi_dung
                self.trang_thai_tai_khoan[ten] = mo_ta
            elif loai == "nap_bang_tai_khoan":
                self.nap_bang_tai_khoan()
            elif loai == "trang_thai_xoay_vong":
                self.nhan_xoay_vong.configure(text=noi_dung[0])
                if not (self.luong_xoay_vong and self.luong_xoay_vong.is_alive()) \
                        or noi_dung[0] in ("Xong", "Đã dừng", "Lỗi, xem log"):
                    self.nut_xoay_vong.configure(text="Bắt đầu")
            elif loai == "trang_thai_giao_acc_chinh":
                self.nhan_giao_acc_chinh.configure(text=noi_dung[0])
                if not (self.luong_giao_acc_chinh and self.luong_giao_acc_chinh.is_alive()) \
                        or noi_dung[0].startswith(("Xong", "Đã dừng", "Dừng:", "Lỗi")):
                    self.nut_giao_acc_chinh.configure(text="Bắt đầu")
                if noi_dung[0].startswith("Xong"):
                    self.xoay_vong_sau_giao_acc_chinh()
            elif loai == "trang_thai_tao_nv":
                self.nhan_tao_nv.configure(text=noi_dung[0])
                if not (self.luong_tao_nv and self.luong_tao_nv.is_alive()) or noi_dung[0] in ("Xong", "Đã dừng"):
                    self.nut_tao_nv.configure(text="Bắt đầu")
            elif loai == "trang_thai_nang_cap":
                self.nhan_tao_nv.configure(text=noi_dung[0])
                if noi_dung[0] in ("Xong", "Đã dừng"):
                    self.nut_nang_cap_online.configure(text="Test nâng cấp NV")
            elif loai == "nhom":
                hwnd, ten, mo_ta, thanh_vien = noi_dung
                self.trang_thai_nhom[hwnd] = mo_ta
                self.doi_hinh_nhom[hwnd] = (ten, thanh_vien)
            elif loai == "xung_quanh":
                hwnd, cac_ten = noi_dung
                self.xung_quanh[hwnd] = cac_ten
            elif loai == "cai_dat_doi":
                self.cap_nhat_co_map_pk(noi_dung[0])
                if self.ten_dang_sua:
                    # Luồng auto có thể đã đổi cả đội (hết lượt: tắt phó bản, bật chuyển sinh).
                    cai_dat = cau_hinh.cua_nhan_vat(self.ten_dang_sua)
                    self.hien_hom_nay(cai_dat)
                    self.bien_pmp_bat.set(cai_dat_pmp(cai_dat)["bat"])
        # Vẽ lại cả giao diện tốn thời gian (Treeview, đọc cấu hình): có tin mới thì tối đa ~2 lần/giây,
        # không có tin thì 1 lần/giây cho cột trạng thái do luồng game tự đổi.
        bay_gio = time.monotonic()
        cach = bay_gio - self._luc_ve_lai
        if cach >= GIAY_VE_LAI_TOI_DA or (co_tin and cach >= GIAY_VE_LAI_KHI_CO_TIN):
            self._luc_ve_lai = bay_gio
            try:
                self.cap_nhat_nhom()
            except OSError:
                pass
            self.ve_lai_bang()
            self.ve_lai_thong_tin()
            self.ve_lai_bang_tai_khoan()
            self.ve_lai_bang_nhom()
            self.ve_lai_xung_quanh()
            self.hien_khung_buff()
        self.root.after(300, self.xu_ly_hang_doi)

    def xoa_cua_so(self, hwnd):
        luong = self.cac_luong.pop(hwnd, None)
        self.thong_tin.pop(hwnd, None)
        self.loi.pop(hwnd, None)
        self.trang_thai_nhom.pop(hwnd, None)
        self.doi_hinh_nhom.pop(hwnd, None)
        self.xung_quanh.pop(hwnd, None)
        if self.bang.exists(str(hwnd)):
            self.bang.delete(str(hwnd))
        if luong and luong.ten:
            self.in_log(f"Cửa sổ game của {luong.ten} đã đóng")

    def ve_lai_bang(self):
        so_bat = so_chuyen_sinh = 0
        da_an = cac_cua_so_da_an()
        tieu_de_an = "Hiện" if da_an else "Ẩn"
        if self.bang.heading("an", "text") != tieu_de_an:
            self.bang.heading("an", text=tieu_de_an)
        for hwnd, luong in self.cac_luong.items():
            dat_o_bang(self.bang, str(hwnd), "an", "ẩn" if hwnd in da_an else "")
            tt = self.thong_tin.get(hwnd)
            if luong.ten is None or tt is None:
                trang_thai = "Chưa đọc được game" if hwnd in self.loi else luong.trang_thai.get("mo_ta", "Đang kết nối...")
                dat_o_bang(self.bang, str(hwnd), "trang_thai", trang_thai)
                continue
            cai_dat = cau_hinh.cua_nhan_vat(luong.ten)
            bat = cai_dat["bat_auto"]
            so_bat += bat
            so_chuyen_sinh += bat and cai_dat["bat_chuyen_sinh"]
            trang_thai = "Chưa đọc được game" if hwnd in self.loi else " | ".join(
                chu for chu in (luong.trang_thai.get("mo_ta", ""), luong.mo_ta_chien_dau, luong.mo_ta_auto_click)
                if chu) \
                or ("Đang auto" if bat else "")
            dat_dong_bang(self.bang, str(hwnd), (O_BAT if bat else O_TAT, "ẩn" if hwnd in da_an else "",
                                                 f"{tt['ten']} ({tt['level']})", tt["tai_khoan"], trang_thai))
        self.sap_xep_bang()
        if not self.dang_doi_tat_ca:
            cac_ten = {luong.ten for luong in self.cac_luong.values() if luong.ten}
            cac_bat = [cau_hinh.cua_nhan_vat(ten)["bat_chuyen_sinh"] for ten in cac_ten]
            bat_het = bool(cac_bat) and all(cac_bat)
            tat_het = bool(cac_bat) and not any(cac_bat)
            if not (bat_het or tat_het):
                self.chuyen_sinh_truoc_khi_doi = {}
            for bien, gia_tri in ((self.bien_bat_chuyen_sinh_tat_ca, bat_het),
                                  (self.bien_tat_chuyen_sinh_tat_ca, tat_het)):
                if bien.get() != gia_tri:
                    bien.set(gia_tri)
            if self.ten_dang_sua in cac_ten:
                cs_nv = cau_hinh.cua_nhan_vat(self.ten_dang_sua)["bat_chuyen_sinh"]
                if self.bien_bat_chuyen_sinh_nv.get() != cs_nv:
                    self.bien_bat_chuyen_sinh_nv.set(cs_nv)
        self.bien_thanh_trang_thai.set(
            f"Đang theo dõi {len(self.cac_luong)} cửa sổ game - {so_bat} nhân vật bật auto, "
            f"{so_chuyen_sinh} bật chuyển sinh" + (f" - đang ẩn {len(da_an)} cửa sổ game" if da_an else ""))

    def ve_lai_thong_tin(self):
        luong = self.luong_dang_chon()
        tt = self.thong_tin.get(luong.hwnd) if luong else None
        if tt is None:
            for bien in self.bien_thong_tin.values():
                bien.set("-")
            return

        def phan_tram(hien_tai, toi_da):
            return f"{hien_tai * 100 // toi_da}%" if toi_da else "-"

        self.bien_thong_tin["level"].set(str(tt["level"]))
        self.bien_thong_tin["hp"].set(phan_tram(tt["hp"], tt["hp_toi_da"]))
        self.bien_thong_tin["mp"].set(phan_tram(tt["mp"], tt["mp_toi_da"]))
        self.bien_thong_tin["map"].set(tt["map"])
        self.bien_thong_tin["toa_do"].set(f"[{tt['x']},{tt['y']}]")
        self.bien_thong_tin["chuyen_sinh"].set(f"{luong.trang_thai.get('so_lan_chuyen_sinh', 0)} lần")

    def thoat(self):
        hien_cua_so()
        if not self.dang_khoi_dong:
            self.luu_cai_dat_xoay_vong()
        for luong in self.cac_luong.values():
            luong.dung.set()
        for luong in self.cac_luong_dang_nhap.values():
            luong.dung.set()
        if self.luong_tao_nv:
            self.luong_tao_nv.dung.set()
        if self.luong_nang_cap_online:
            self.luong_nang_cap_online.dung.set()
        if self.luong_xoay_vong:
            self.luong_xoay_vong.luu_tien_trinh_ngay()
            self.luong_xoay_vong.dung.set()
        if self.luong_giao_acc_chinh:
            self.luong_giao_acc_chinh.dung.set()
        if self.luong_giao_dich_ngay and self.luong_giao_dich_ngay.is_alive():
            # Chờ luồng bật lại auto đã tạm tắt, kẻo cau_hinh.json lưu nhân vật ở trạng thái tắt auto.
            self.luong_giao_dich_ngay.dung.set()
            self.luong_giao_dich_ngay.join(10)
        self.root.destroy()


def main():
    bat_dpi_awareness()
    root = tk.Tk()
    icon = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "icon.ico")
    if os.path.exists(icon):
        root.iconbitmap(default=icon)
    if han_dung.co_han_dung():
        han_dung.dong_bo_gio_mang()
        if han_dung.giay_con_lai() <= 0:
            root.withdraw()
            messagebox.showerror("Hết hạn dùng thử", han_dung.THONG_BAO_HET_HAN)
            root.destroy()
            return
    UngDung(root)
    root.mainloop()


if __name__ == "__main__":
    main()
