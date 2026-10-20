"""
XOAY VÒNG PHÓ BẢN: các tài khoản đang tích "Bật" ở tab Tài khoản, cứ SO_TAI_KHOAN_MOT_NHOM tài khoản liền nhau
là một nhóm (tài khoản đầu là trưởng nhóm). Mỗi nhóm chạy so_round round; round r dùng nhân vật thứ r theo quy tắc
tên (caychay10 -> caychay10, caychay100, caychay1000).

Một round:
    0. Tài khoản chưa có nhân vật của round thì tạo + nhận đồ tân thủ ngay trong game của nó (cả nhóm cùng lúc).
    1. Đăng nhập cả nhóm vào nhân vật của round (game đang mở thì về chọn máy chủ rồi vào nhân vật mới). Server chỉ
       cho 4 tài khoản online cùng lúc nên game ngoài nhóm bị tắt trước.
    2. Chụp túi đồ, hồi máu ở NPC Di Chuyển, bật tự mời nhóm (trưởng nhóm = nhân vật của tài khoản đầu), chờ cả đội vào nhóm.
    3. Bật Auto + Phó bản cho cả đội; luồng của từng cửa sổ game (LuongNhanVat) tự đi PMP rồi Sát Tinh.
    4. Chờ trưởng nhóm xong (test: 1 lượt PMP; chỉ Sát Tinh: tới khi NPC báo hết lượt Sát Tinh;
       đủ PMP+ST: hết lượt PMP và Sát Tinh trong ngày trên nhân vật round đó).
    5. Tắt auto, cả đội về Đại Lý (ô về thành), đội viên giao dịch đồ mới nhặt cho trưởng nhóm.
Lúc đăng nhập / chụp túi / về thành / giao dịch, các game của nhóm do luồng này điều khiển (dang_dieu_khien),
LuongNhanVat không chen vào. Cửa sổ game giữ qua các round và dùng lại cho nhóm sau; hết danh sách thì tắt game.
Chạy lại ngày mới: qua 0h thì làm mới danh sách tài khoản và chạy lại từ nhóm 1 (bộ đếm phó bản tự về 0 khi sang
ngày); nhóm đang ở trong phó bản lúc 0h thì đi nốt vòng đó (không vào vòng mới), ra khỏi phó bản mới quay lại.
Hết danh sách trong ngày thì chờ qua 0h rồi đi lại.
"""
import math
import re
import threading
import time
import traceback
from datetime import date

import win32gui
import win32process

import cau_hinh
from auto_chuyen_sinh import chuan_hoa
from cua_so_game import tim_cua_so_game
from chien_dau import KY_NANG_VE_THANH, ma_dung_ky_nang_theo_dinh_nghia
from dang_nhap import (LoiDangNhap, LoiSaiRuleNhanVat, LuongDangNhap, _gan_pid_dang_nhap, con_chay, giu_client,
                       man_hinh_hien_tai, tai_khoan_cua_pid, tat_game, trong_cua_so,
                       thoat_ve_chon_may_chu)
from game_api import Game
from giao_dich import GIAY_GUI_LAI_VI_TRI, KHOANG_CACH_GIAO_DICH, GiaoDich, LoiGiaoDich, chup_tui, o_do_moi
from lua_game import LoiLua
from moi_nhom import doc_nhom
from nhan_vat_moi import LuongTaoNhanVat, NhanDoTanThu, cac_ten_nhan_vat, da_xong, ten_sai_rule, ten_thuc
from pho_ban_pmp import (GIAY_MOT_VONG, MAP_DAI_LY, MAP_LAC_DUONG, cai_dat_pmp, chuan_bi_ve_thanh, dang_chay_vong,
                         dat_chan_vong_moi, dat_phien_xoay_vong, hom_nay, la_dai_ly, la_lac_duong,
                         la_map_trong_pho_ban)

SO_TAI_KHOAN_MOT_NHOM = 4  # mặc định; số thật lấy từ cau_hinh.chung()["so_nguoi_mot_nhom"]
SO_NGUOI_MOT_NHOM_TOI_DA = 6
SO_ROUND_TOI_DA = 3
GIAY_CHO_VAO_NHOM = 5
GIAY_CHO_VE_DAI_LY = 20
GIAY_GIUA_HAI_LAN_VE_THANH = 15
GIAY_TAP_TRUNG = 5
# Tên map đổi sang Đại Lý trước khi nhân vật load xong: giao dịch ngay thì chưa thấy nhau trong danh sách quanh mình.
GIAY_CHO_LOAD_TRUOC_GIAO_DICH = 6
GIAY_CHO_RA_LAC_DUONG = 15
SO_LAN_THU_GIAO_DICH = 3
GIAY_GIUA_HAI_LAN_GIAO_DICH = 4
GIAY_KIEM_TRA = 3
# Server reset lượt phó bản lúc 0h; chờ thêm chút phòng giờ máy lệch với server.
GIAY_CHO_SAU_NUA_DEM = 60
KHOA_CHUNG_NHOM = ("bat_moi_nhom", "truong_nhom", "bat_moi_nhan_vat_auto", "danh_sach_moi")


class _Dung(Exception):
    pass


def khoa_sap_xep_tai_khoan(ten):
    """caychay9 < caychay10 < caychay24: so phần chữ rồi tới phần số."""
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", ten.lower())]


def cac_tai_khoan_dang_tich():
    ds = [tk for tk in cau_hinh.tai_khoan_pho_ban()
          if tk.get("bat") and tk.get("ten_dang_nhap") and tk.get("mat_khau")]
    return sorted(ds, key=lambda tk: khoa_sap_xep_tai_khoan(tk["ten_dang_nhap"]))


def bo_tich_tai_khoan(ten_dang_nhap):
    cai_dat = cau_hinh.doc_tai_khoan()
    for tk in cai_dat[cau_hinh.KHOA_TK_PHO_BAN]:
        if (tk.get("ten_dang_nhap") or "").lower() == ten_dang_nhap.lower():
            tk["bat"] = False
    cau_hinh.luu_tai_khoan(cai_dat)


def so_nguoi_mot_nhom():
    try:
        n = int(cau_hinh.chung().get("so_nguoi_mot_nhom", SO_TAI_KHOAN_MOT_NHOM))
    except (TypeError, ValueError):
        n = SO_TAI_KHOAN_MOT_NHOM
    return max(1, min(SO_NGUOI_MOT_NHOM_TOI_DA, n))


def chia_nhom(ds):
    n = so_nguoi_mot_nhom()
    return [ds[i:i + n] for i in range(0, len(ds), n)]


def hwnd_giu_khi_xoay_vong():
    """Cửa sổ train / acc chính không thuộc nhóm phó bản — giữ khi tắt game thừa (kể cả đang đăng nhập)."""
    from giao_acc_chinh import cai_dat as cd_giao_acc_chinh
    giu = set()
    tk_chinh = (cd_giao_acc_chinh().get("tai_khoan") or "").strip()
    if tk_chinh:
        hwnd = tim_hwnd_cua_tai_khoan(tk_chinh)
        if hwnd:
            giu.add(hwnd)
    for tk in cau_hinh.tai_khoan_train():
        ten = (tk.get("ten_dang_nhap") or "").strip()
        if not ten:
            continue
        hwnd = tim_hwnd_cua_tai_khoan(ten)
        if hwnd:
            giu.add(hwnd)
    return giu


def tat_game_khac(giu_hwnd, in_log):
    """Tắt mọi game không nằm trong giu_hwnd (+ acc train / acc chính)."""
    giu = {h for h in giu_hwnd if h} | hwnd_giu_khi_xoay_vong()
    for cua_so in tim_cua_so_game():
        if cua_so["hwnd"] in giu:
            continue
        in_log(f"Tắt game ngoài nhóm: {cua_so['tieu_de'].split(' - ')[0]} (pid {cua_so['pid']})")
        tat_game(cua_so["pid"])


def game_ranh(giu_hwnd):
    """Cửa sổ game không thuộc nhóm (và không phải acc train / acc chính): dùng lại cho thành viên chưa có game."""
    giu = {h for h in giu_hwnd if h} | hwnd_giu_khi_xoay_vong()
    return [c["hwnd"] for c in tim_cua_so_game() if c["hwnd"] not in giu]


def thoat_game_khac(giu_hwnd, in_log, nen_dung=None):
    """
    Server giới hạn số tài khoản online cùng lúc: game ngoài nhóm đang trong game thì về chọn máy chủ (giữ client
    để nhóm sau dùng lại, khỏi mở game mới). Không về được thì mới tắt.
    """
    giu = {h for h in giu_hwnd if h} | hwnd_giu_khi_xoay_vong()
    for cua_so in tim_cua_so_game():
        if cua_so["hwnd"] in giu:
            continue
        try:
            game = Game(cua_so["hwnd"])
            dang_choi = bool(game.thong_tin()) or man_hinh_hien_tai(game.lua) == "vao_game"
        except (LoiLua, OSError):
            continue
        if not dang_choi:
            continue
        in_log(f"Game ngoài nhóm: {cua_so['tieu_de'].split(' - ')[0]} về chọn máy chủ (giữ client)")
        thoat_ve_chon_may_chu(cua_so["pid"], in_log, nen_dung)


def ten_round(tk, r):
    """Nhân vật chơi round r của tài khoản tk (tên theo quy tắc, hoặc tên đã tạo thay khi trùng tên)."""
    return ten_thuc(tk, cac_ten_nhan_vat(tk, SO_ROUND_TOI_DA)[r])


def da_xong_hom_nay(ten):
    """
    Nhân vật đã đi hết phó bản hôm nay. Sát Tinh đi sau PMP và khi hết lượt thì ghi st_het cho cả đội (đội viên không
    có het_luot PMP đáng tin), nên chỉ xét st_het.
    """
    return hom_nay(cai_dat_pmp(cau_hinh.cua_nhan_vat(ten)))["st_het"]


MAU_TIEU_DE_DA_VAO_GAME = re.compile(r"^(.*) \(\d+\) \[.*\] - ChickenAuto")


def ten_trong_tieu_de(hwnd):
    khop = MAU_TIEU_DE_DA_VAO_GAME.search(win32gui.GetWindowText(hwnd))
    return khop.group(1) if khop else None


def tim_hwnd_theo_nhan_vat(ten_nhan_vat, gan_tk=None):
    """Cửa sổ đang chơi nhân vật này (đọc trong game hoặc tiêu đề), None nếu không thấy."""
    khoa = chuan_hoa(ten_nhan_vat or "")
    if not khoa:
        return None
    for cua_so in tim_cua_so_game():
        hwnd = cua_so["hwnd"]
        try:
            tt = Game(cua_so["hwnd"]).thong_tin()
        except (LoiLua, OSError):
            tt = None
        except Exception:
            tt = None
        if tt and chuan_hoa(tt["ten"]) == khoa:
            tk = (tt.get("tai_khoan") or "").strip()
            if tk:
                _gan_pid_dang_nhap(tk, cua_so["pid"])
            elif gan_tk:
                _gan_pid_dang_nhap(gan_tk, cua_so["pid"])
            return hwnd
        ten_td = ten_trong_tieu_de(hwnd)
        if ten_td and chuan_hoa(ten_td) == khoa:
            if gan_tk:
                _gan_pid_dang_nhap(gan_tk, cua_so["pid"])
            return hwnd
    return None


def tim_hwnd_cho_thanh_vien(tk, ten_nhan_vat=None):
    """Game của tài khoản hoặc nhân vật round (khi ACCOUNTNAME trong game chưa đọc được)."""
    hwnd = tim_hwnd_cua_tai_khoan(tk)
    if hwnd:
        return hwnd
    return tim_hwnd_theo_nhan_vat(ten_nhan_vat, gan_tk=tk)


def tim_hwnd_cua_tai_khoan(ten_dang_nhap):
    """hwnd game của tài khoản: đã vào game hoặc đang mở/đăng nhập."""
    from dang_nhap import hwnd_dang_dang_nhap
    return tim_game_cua_tai_khoan(ten_dang_nhap) or hwnd_dang_dang_nhap(ten_dang_nhap)


def tim_game_cua_tai_khoan(ten_dang_nhap):
    """hwnd của game đang trong game bằng tài khoản này, None nếu không thấy."""
    for cua_so in tim_cua_so_game():
        try:
            tt = Game(cua_so["hwnd"]).thong_tin()
        except (LoiLua, OSError):
            continue
        except Exception:
            continue
        if tt and (tt["tai_khoan"] or "").lower() == ten_dang_nhap.lower():
            return cua_so["hwnd"]
    return None


class LuongVaoNhanVat(LuongDangNhap):
    """
    Đăng nhập tài khoản vào nhân vật tai_khoan["nhan_vat"]. Có hwnd (game của round / nhóm trước) thì dùng lại game
    đó: đang trong game bằng nhân vật khác thì về chọn máy chủ rồi đăng nhập lại; game đã tắt thì mở game mới.
    """
    ve_chon_may_chu = LuongTaoNhanVat.ve_chon_may_chu

    def __init__(self, tai_khoan, cai_dat, hang_doi, hwnd=None, kiem_tra_rule_ten=True):
        super().__init__(tai_khoan, cai_dat, hang_doi)
        self.chi_co_mot_may_chu_thi_chon = True
        self.hwnd = hwnd
        self.game = None
        if hwnd:
            try:
                if not giu_client(win32process.GetWindowThreadProcessId(hwnd)[1], self):
                    self.hwnd = None
            except OSError:
                pass
        # Quy tắc tên (caychay10 -> caychay100...) chỉ áp cho acc phó bản, không áp cho acc chính.
        self.kiem_tra_rule_ten = kiem_tra_rule_ten

    def kiem_tra_ds_nhan_vat(self, cac_ten):
        if not self.kiem_tra_rule_ten:
            return
        sai = ten_sai_rule(self.tai_khoan["ten_dang_nhap"], cac_ten)
        if sai:
            raise LoiSaiRuleNhanVat(sai)

    def dang_nhap_mot_lan(self, lan, so_lan):
        hwnd, self.hwnd = self.hwnd, None
        if hwnd is None:
            hwnd = tim_hwnd_theo_nhan_vat(self.tai_khoan.get("nhan_vat"),
                                          gan_tk=self.tai_khoan["ten_dang_nhap"])
        try:
            game = Game(hwnd) if hwnd else None
        except (LoiLua, OSError):
            game = None
        if game is None or not con_chay(game.lua.pid):
            super().dang_nhap_mot_lan(lan, so_lan)
            self.game = Game(next(c["hwnd"] for c in tim_cua_so_game() if c["pid"] == self.pid))
            return
        self.pid, self.game = game.lua.pid, game
        giu_client(self.pid, self)
        cua_toi = tai_khoan_cua_pid(self.pid) == self.tai_khoan["ten_dang_nhap"].lower()
        _gan_pid_dang_nhap(self.tai_khoan["ten_dang_nhap"], self.pid)
        tt = game.thong_tin()
        if tt and chuan_hoa(tt["ten"]) == chuan_hoa(self.tai_khoan["nhan_vat"]):
            self.in_log(f"Đã vào game nhân vật {tt['ten']}, bỏ qua đăng nhập")
            return
        man = man_hinh_hien_tai(game.lua)
        if tt or man in ("vao_game", ""):
            self.ve_chon_may_chu(game)
        elif man == "chon_nhan_vat" and not cua_toi:
            # Client dùng lại còn ở màn chọn nhân vật của tài khoản khác: phải về đăng nhập, kẻo đọc nhầm danh sách.
            self.in_log("Game đang ở màn chọn nhân vật của tài khoản khác, quay lại đăng nhập")
            game.lua.chay(trong_cua_so("LoginSelectRole", "SelectRole_Return()"))
            het_han = time.time() + 15
            while time.time() < het_han and man_hinh_hien_tai(game.lua) == "chon_nhan_vat":
                time.sleep(0.5)
        if self.dieu_khien(game) != "vao_game":
            raise LoiDangNhap(f"chưa vào được game bằng {self.tai_khoan['nhan_vat']}")


class ThanhVien:
    """Một tài khoản trong nhóm và game / nhân vật của nó ở round đang chạy."""

    def __init__(self, tai_khoan):
        self.tai_khoan = tai_khoan
        self.tk = tai_khoan["ten_dang_nhap"]
        self.hwnd = None
        self.game = None
        self.ten = None
        self.anh_tui = None

    @property
    def pid(self):
        return self.game.lua.pid if self.game else None


class LuongXoayVong(threading.Thread):
    def __init__(self, hang_doi, so_round, che_do_test, chuyen_do, chay_lai_ngay_moi=True, chi_sat_tinh=False):
        super().__init__(daemon=True)
        self.hang_doi = hang_doi
        self.so_round = max(1, min(SO_ROUND_TOI_DA, so_round))
        self.che_do_test = che_do_test
        self.chuyen_do = chuyen_do
        self.chay_lai_ngay_moi = chay_lai_ngay_moi
        self.chi_sat_tinh = chi_sat_tinh
        self.dung = threading.Event()
        self.ds_tai_khoan = cac_tai_khoan_dang_tich()
        self.pid_dieu_khien = set()
        self.cac_luong_con = []
        self.cac_hwnd = []  # game của nhóm trước, dùng lại cho nhóm sau
        self.chung_cu = None
        self.so_round_da_chay = 0
        self.tk_sai_rule = set()
        self._tv_theo_tk = {}
        self._ngay_luot = date.today()
        # Nhóm đang bật Auto + Phó bản (để tắt ngay khi bấm Dừng xoay vòng).
        self.thanh_vien_dang_pb = None

    def tat_pho_ban_ngay(self):
        """Tắt Auto + Phó bản cho nhóm đang đi — luồng nhân vật sẽ dừng pho_ban.chay() sau vài giây."""
        if self.thanh_vien_dang_pb:
            self._tat_auto(self.thanh_vien_dang_pb)

    # ---------- dùng từ giao diện ----------

    def cac_tai_khoan(self):
        """Tên đăng nhập (chữ thường) các tài khoản luồng này điều khiển, luồng tự đăng nhập bỏ qua."""
        return {tk["ten_dang_nhap"].lower() for tk in self.ds_tai_khoan} if self.is_alive() else set()

    def dang_dieu_khien(self, pid):
        if not self.is_alive():
            return False
        return pid in self.pid_dieu_khien or any(l.pid == pid and l.is_alive() for l in list(self.cac_luong_con))

    # ---------- chung ----------

    def in_log(self, chu):
        self.hang_doi.put(("log", f"[Xoay vòng] {chu}"))

    def bao_trang_thai(self, chu):
        self.hang_doi.put(("trang_thai_xoay_vong", chu))

    def _kiem_tra_dung(self):
        if self.dung.is_set():
            raise _Dung()

    def _cho(self, dieu_kien, giay, buoc=1.0):
        het_han = time.time() + giay
        while True:
            self._kiem_tra_dung()
            ket_qua = dieu_kien()
            if ket_qua or time.time() > het_han:
                return ket_qua
            self.dung.wait(buoc)

    def run(self):
        try:
            self._chay()
            self.bao_trang_thai("Xong")
        except _Dung:
            self.tat_pho_ban_ngay()
            self.in_log("Đã dừng")
            self.bao_trang_thai("Đã dừng")
        except Exception:
            self.in_log(f"Lỗi không mong đợi\n{traceback.format_exc()}")
            self.bao_trang_thai("Lỗi, xem log")
        finally:
            dat_phien_xoay_vong(False)
            dat_chan_vong_moi(False)
            self.tat_pho_ban_ngay()
            self.thanh_vien_dang_pb = None
            for luong in self.cac_luong_con:
                luong.dung.set()
            self.pid_dieu_khien.clear()
            if self.chung_cu is not None:
                cau_hinh.dat_chung(self.chung_cu)
                self.chung_cu = None

    def _chay(self):
        if not self.ds_tai_khoan:
            self.in_log("Không có tài khoản nào đang tích Bật ở tab Tài khoản")
            return
        self.chung_cu = {k: cau_hinh.chung()[k] for k in KHOA_CHUNG_NHOM}
        while True:
            ngay = date.today()
            self.so_round_da_chay = 0
            qua_ngay = self._mot_luot(ngay)
            if not qua_ngay and self._con_luot_sat_tinh() and self.so_round_da_chay:
                self.ds_tai_khoan = cac_tai_khoan_dang_tich()
                if self.ds_tai_khoan:
                    self.in_log("Hết danh sách, còn nhân vật chưa hết lượt Sát Tinh: quay lại nhóm 1")
                    continue
            if self.che_do_test or not self.chay_lai_ngay_moi:
                break
            if not qua_ngay:
                self._tat_cac_game()
                self._cho_ngay_moi(ngay)
            self.ds_tai_khoan = cac_tai_khoan_dang_tich()
            if not self.ds_tai_khoan:
                self.in_log("Ngày mới: không còn tài khoản nào đang tích Bật ở tab Tài khoản, dừng")
                break
            self.in_log("Ngày mới: số lượt phó bản đã reset, quay lại nhóm 1")
        self._tat_cac_game()

    def _con_luot_sat_tinh(self):
        """Chế độ chỉ Sát Tinh: còn nhân vật round nào chưa hết lượt hôm nay thì đi lại từ nhóm 1 trong ngày."""
        if not self.chi_sat_tinh or self.che_do_test:
            return False
        return any(not da_xong_hom_nay(ten_round(tk["ten_dang_nhap"], r))
                   for tk in self.ds_tai_khoan for r in range(self.so_round))

    def _cho_ngay_moi(self, ngay):
        self.in_log(f"Hết danh sách tài khoản, chờ qua 0h (thêm {GIAY_CHO_SAU_NUA_DEM} giây) để đi lại từ nhóm 1")
        self.bao_trang_thai("Chờ qua 0h để đi lại từ nhóm 1")
        self._cho(lambda: date.today() != ngay, 2 * 86400, 10)
        self._xu_ly_qua_ngay(ngay)

    def _xu_ly_qua_ngay(self, ngay_cu):
        self.bao_trang_thai(f"Qua 0h, chờ {GIAY_CHO_SAU_NUA_DEM} giây cho server reset lượt")
        self._cho(lambda: False, GIAY_CHO_SAU_NUA_DEM)
        self.ds_tai_khoan = cac_tai_khoan_dang_tich()
        self.in_log(f"Qua 0h: làm mới danh sách ({len(self.ds_tai_khoan)} tài khoản phó bản), chạy lại từ nhóm 1")

    def _neu_qua_ngay(self, ngay):
        """True nếu đã sang ngày mới — dừng lượt hiện tại để quay lại nhóm 1."""
        if date.today() == ngay:
            return False
        if self.chay_lai_ngay_moi and not self.che_do_test:
            self._xu_ly_qua_ngay(ngay)
            return True
        return False

    def _tat_cac_game(self):
        for hwnd in self.cac_hwnd:
            try:
                tat_game(Game(hwnd).lua.pid)
            except (LoiLua, OSError):
                pass
        self.cac_hwnd = []

    def _mot_luot(self, ngay):
        """
        Đi lần lượt theo số tài khoản tăng dần; mỗi nhóm đi round 1, 2, 3, mỗi round ghép N acc đầu tiên còn phải đi
        round đó (bỏ nhân vật đã xong hôm nay / tài khoản sai rule) nên nhóm luôn đủ N người. Qua 0h thì làm mới
        danh sách và quay lại nhóm 1; hết danh sách trong ngày thì False.
        """
        # Tới lúc cả đội vào game mới bật lại, kẻo nhóm cũ (có người ngoài đội) mời nhân vật của đội vào.
        cau_hinh.dat_chung({"bat_moi_nhom": False})
        self._ngay_luot = ngay
        ds = self.ds_tai_khoan
        n_mot_nhom = so_nguoi_mot_nhom()
        luot_test = "1 lượt Sát Tinh" if self.chi_sat_tinh else "1 lượt PMP"
        che_do = f"TEST (1 round, {luot_test}, giao dịch rồi dừng)" if self.che_do_test else f"{self.so_round} round"
        if self.chi_sat_tinh and not self.che_do_test:
            che_do += ", chỉ Sát Tinh"
        self.in_log(f"Bắt đầu từ tài khoản đầu tiên: {len(ds)} tài khoản (mỗi nhóm {n_mot_nhom} acc theo số tăng "
                    f"dần, ghép lại đủ người mỗi round), {che_do}. Nhân vật đã hết lượt Sát Tinh hôm nay được bỏ "
                    "qua, không đăng nhập. " + ", ".join(tk["ten_dang_nhap"] for tk in ds))
        so_round = 1 if self.che_do_test else self.so_round
        if not self.che_do_test:
            for r in range(so_round):
                het = [ten_round(tk["ten_dang_nhap"], r) for tk in ds if da_xong_hom_nay(ten_round(tk["ten_dang_nhap"], r))]
                if het:
                    self.in_log(f"Round {r + 1} bỏ qua {len(het)} nhân vật đã hết lượt hôm nay: {', '.join(het)}")
        # Mỗi round một hàng chờ tài khoản theo số tăng dần; mỗi nhóm lấy N acc đầu hàng còn phải đi round đó, nên
        # acc đã xong / bị loại (sai rule) không chiếm chỗ, nhóm luôn ghép đủ N người.
        hang_cho = [list(ds) for _ in range(so_round)]
        tv_theo_tk = self._tv_theo_tk = {}
        so = 0
        while any(hang_cho):
            if self._neu_qua_ngay(ngay):
                return True
            so += 1
            ca_nhom = []
            for r in range(so_round):
                if self._neu_qua_ngay(ngay):
                    return True
                choi = []
                while hang_cho[r] and len(choi) < n_mot_nhom:
                    tk = hang_cho[r].pop(0)
                    ten = tk["ten_dang_nhap"]
                    if ten.lower() in self.tk_sai_rule:
                        continue
                    if not self.che_do_test and da_xong_hom_nay(ten_round(ten, r)):
                        continue
                    choi.append(tv_theo_tk.setdefault(ten.lower(), ThanhVien(tk)))
                if not choi:
                    continue
                ca_nhom += [tv for tv in choi if tv not in ca_nhom]
                self.in_log(f"Nhóm {so} round {r + 1}: ghép {', '.join(ten_round(tv.tk, r) for tv in choi)}")
                self._chuan_bi(so, r, choi)
                choi = self._bo_sai_rule(choi)
                if self._neu_qua_ngay(ngay):
                    return True
                con = self._round(so, r, choi) if choi else []
                if con:
                    self.so_round_da_chay += 1
                if self._neu_qua_ngay(ngay):
                    return True
                if self.che_do_test:
                    self.in_log("Chế độ test: xong 1 round, dừng để kiểm tra (game vẫn mở)")
                    self.cac_hwnd = []
                    return False
            cu = [h for h in self.cac_hwnd if h and win32gui.IsWindow(h)]
            moi = list(dict.fromkeys(tv.hwnd for tv in ca_nhom if tv.hwnd and win32gui.IsWindow(tv.hwnd)))
            self.cac_hwnd = moi + [h for h in dict.fromkeys(cu) if h not in moi]
        if self._neu_qua_ngay(ngay):
            return True
        if not self.chay_lai_ngay_moi:
            self.in_log("Hết danh sách tài khoản, tắt game")
        return False

    # ---------- chuẩn bị nhân vật ----------

    @staticmethod
    def _hwnd_cua(tv, hwnd):
        """hwnd còn mở và không phải client đang đăng nhập tài khoản khác."""
        if not (hwnd and win32gui.IsWindow(hwnd)):
            return False
        chu = tai_khoan_cua_pid(win32process.GetWindowThreadProcessId(hwnd)[1])
        return chu in (None, tv.tk.lower())

    def _gan_game(self, thanh_vien, r=None):
        """
        Chọn game cho từng thành viên (tv.hwnd): game đang dùng của chính tài khoản, không có thì game của nhóm trước
        (hoặc client rảnh bất kỳ) chưa ai dùng, không nữa thì None (mở game mới). Không tắt client: game được dùng lại
        tự về chọn máy chủ rồi đăng nhập tài khoản mới; game dư ngoài nhóm cũng chỉ về chọn máy chủ.
        """
        da_gan = set()
        for tv in thanh_vien:
            ten_nv = tv.ten or (ten_round(tv.tk, r) if r is not None else None)
            if not self._hwnd_cua(tv, tv.hwnd):
                tv.hwnd = tim_hwnd_cho_thanh_vien(tv.tk, ten_nv)
                if tv.hwnd and ten_nv:
                    try:
                        pid = win32process.GetWindowThreadProcessId(tv.hwnd)[1]
                        _gan_pid_dang_nhap(tv.tk, pid)
                    except OSError:
                        pass
            # Hai thành viên chung một client thì đăng nhập đè nhau, đọc nhầm danh sách nhân vật của nhau.
            if tv.hwnd in da_gan:
                tv.hwnd = None
            if tv.hwnd:
                da_gan.add(tv.hwnd)
        con_trong = []
        for h in self.cac_hwnd + game_ranh(da_gan):
            if h and h not in da_gan and h not in con_trong and win32gui.IsWindow(h):
                con_trong.append(h)
        for tv in thanh_vien:
            if tv.hwnd is None and con_trong:
                tv.hwnd = con_trong.pop(0)
        for tv in thanh_vien:
            if tv.hwnd:
                for khac in self._tv_theo_tk.values():
                    if khac is not tv and khac.hwnd == tv.hwnd:
                        khac.hwnd = None
        giu = {tv.hwnd for tv in thanh_vien} - {None}
        thoat_game_khac(giu, self.in_log, self.dung.is_set)

    def _chuan_bi(self, so_nhom, r, thanh_vien):
        """
        Tài khoản chưa có nhân vật của round r (đã nhận đồ tân thủ) thì tạo + nhận đồ ngay trong game của nó, cả nhóm
        cùng lúc; xong để game ở màn hình chọn nhân vật cho bước đăng nhập round vào luôn. Tài khoản đã có nhân vật
        thì vào game luôn trong lúc chờ, để cả nhóm mở game cùng lúc.
        """
        self._gan_game(thanh_vien, r)
        thieu = [tv for tv in thanh_vien
                 if not any(chuan_hoa(ten_round(tv.tk, r)) == chuan_hoa(x) for x in da_xong(tv.tk))]
        if not thieu:
            return
        ds = ", ".join(cac_ten_nhan_vat(tv.tk, SO_ROUND_TOI_DA)[r] for tv in thieu)
        self.bao_trang_thai(f"Nhóm {so_nhom} round {r + 1}: tạo nhân vật {ds}")
        self.in_log(f"Nhóm {so_nhom} round {r + 1}: tạo + nhận đồ tân thủ cho {ds}")
        cai_dat = cau_hinh.doc_tai_khoan()
        cac_luong = [(tv, LuongTaoNhanVat([tv.tai_khoan], cai_dat, {"so_nhan_vat": r + 1, "nhan_do_tan_thu": True, "dung_ten": True},
                                          self.hang_doi, hwnd=tv.hwnd, giu_game=True)) for tv in thieu]
        cac_luong += [(tv, LuongVaoNhanVat(dict(tv.tai_khoan, nhan_vat=ten_round(tv.tk, r)), cai_dat, self.hang_doi,
                                           tv.hwnd)) for tv in thanh_vien if tv not in thieu]
        for _, luong in cac_luong:
            self.cac_luong_con.append(luong)
            luong.start()
        while any(l.is_alive() for _, l in cac_luong):
            if self.dung.is_set():
                for _, l in cac_luong:
                    l.dung.set()
            # Game đã vào xong vẫn giữ lại (không cho luồng auto chạy) tới lúc round bắt đầu.
            self.pid_dieu_khien |= {l.pid for _, l in cac_luong if l.pid}
            time.sleep(1)
        for tv, luong in cac_luong:
            self.cac_luong_con.remove(luong)
            tv.hwnd = luong.game.lua.hwnd if luong.pid and luong.game and con_chay(luong.pid) else None
            if luong.sai_rule:
                self._danh_dau_sai_rule(tv.tk, luong.sai_rule)
                self._nha_client(tv, tv.hwnd)
            elif luong.sai_tai_khoan:
                self._loai_tai_khoan(tv.tk, "game báo sai tài khoản/mật khẩu")
                self._nha_client(tv, tv.hwnd)
        self._kiem_tra_dung()

    def _danh_dau_sai_rule(self, tk, cac_ten):
        self._loai_tai_khoan(tk, f"có nhân vật sai rule ({', '.join(cac_ten)})")

    def _loai_tai_khoan(self, tk, ly_do):
        """Tài khoản không dùng được (sai rule tên / sai mật khẩu): bỏ tích XV, không đi xoay vòng nữa."""
        khoa = tk.lower()
        if khoa in self.tk_sai_rule:
            return
        self.tk_sai_rule.add(khoa)
        bo_tich_tai_khoan(tk)
        self.ds_tai_khoan = [t for t in self.ds_tai_khoan if t["ten_dang_nhap"].lower() != khoa]
        self.in_log(f"{tk}: {ly_do}, bỏ tích khỏi danh sách phó bản")
        self.hang_doi.put(("nap_bang_tai_khoan",))

    def _bo_sai_rule(self, thanh_vien):
        return [tv for tv in thanh_vien if tv.tk.lower() not in self.tk_sai_rule]

    # ---------- một round ----------

    def _bo_acc_chinh_train(self, thanh_vien):
        """Tách acc chính đang online train ra khỏi nhóm đi phó bản."""
        from giao_acc_chinh import ten_nhan_vat_acc_chinh_online, tk_acc_chinh_bo_pho_ban
        khoa_tk = tk_acc_chinh_bo_pho_ban()
        if not khoa_tk:
            return thanh_vien
        pb = [tv for tv in thanh_vien if tv.tk.lower() != khoa_tk]
        if len(pb) < len(thanh_vien):
            self.in_log(f"Acc chính {ten_nhan_vat_acc_chinh_online()} đang online, không đưa vào nhóm phó bản")
        return pb

    def _danh_sach_moi_nhom(self, thanh_vien):
        from giao_acc_chinh import ten_nhan_vat_acc_chinh_online
        acc = ten_nhan_vat_acc_chinh_online()
        khoa_acc = chuan_hoa(acc) if acc else ""
        return [tv.ten for tv in thanh_vien if chuan_hoa(tv.ten) != khoa_acc]

    def _round(self, so_nhom, r, thanh_vien):
        """Trả về các thành viên còn dùng được (bỏ tài khoản đăng nhập thất bại)."""
        mo_ta = f"Nhóm {so_nhom} round {r + 1}"
        for tv in thanh_vien:
            tv.ten = ten_round(tv.tk, r)
        thanh_vien = self._bo_acc_chinh_train(thanh_vien)
        if not thanh_vien:
            self.in_log(f"{mo_ta}: không còn ai đi phó bản (acc chính đang train)")
            return []
        self.bao_trang_thai(f"{mo_ta}: đăng nhập {', '.join(tv.ten for tv in thanh_vien)}")
        self.in_log(f"{mo_ta}: đăng nhập {', '.join(tv.ten for tv in thanh_vien)}")
        thanh_vien = self._dang_nhap(thanh_vien)
        if not thanh_vien:
            return []
        truong, doi_vien = thanh_vien[0], thanh_vien[1:]
        self._ghi_truong_nhom(truong)
        self.pid_dieu_khien = {tv.pid for tv in thanh_vien}
        khoa_doi = [chuan_hoa(tv.ten) for tv in thanh_vien]
        for tv in thanh_vien:
            self._cho(lambda: self._doc(tv), 60)
            tv.anh_tui = chup_tui(tv.game.lua)
            self._roi_nhom_neu_sai(tv, khoa_doi, self.in_log)
            if la_dai_ly((self._doc(tv) or {}).get("map")):
                NhanDoTanThu(tv.game, tv.ten, self.in_log, self.dung.is_set, lambda _: None).hoi_mau()
        self._tat_auto(thanh_vien)
        self._lam_moi_cau_hinh_moi_nhom(truong, thanh_vien)
        self.pid_dieu_khien = set()

        self.bao_trang_thai(f"{mo_ta}: chờ {truong.ten} mời nhóm")
        if not self._cho_du_nhom_truoc_pb(mo_ta, truong, thanh_vien, khoa_doi):
            self.in_log(f"{mo_ta}: chưa lập được nhóm {len(thanh_vien)} người, bỏ qua round")
            return [tv for tv in thanh_vien if tv.game]

        dich = self._bat_pho_ban(thanh_vien, truong)
        self.thanh_vien_dang_pb = thanh_vien
        self.bao_trang_thai(f"{mo_ta}: đang đi phó bản (trưởng nhóm {truong.ten})")
        if self.che_do_test:
            che_do_pb = f"chờ xong lượt {'Sát Tinh' if self.chi_sat_tinh else 'PMP'} thứ {dich}"
        elif self.chi_sat_tinh:
            che_do_pb = "đi Sát Tinh tới khi NPC báo hết lượt rồi sang round tiếp"
        else:
            che_do_pb = "chờ hết lượt PMP và Sát Tinh"
        self.in_log(f"{mo_ta}: bật Auto + Phó bản, trưởng nhóm {truong.ten}, {che_do_pb}")
        try:
            self._cho_xong_pho_ban(thanh_vien, truong, dich, mo_ta)
        finally:
            self.thanh_vien_dang_pb = None

        self.pid_dieu_khien = {tv.pid for tv in thanh_vien if tv.pid}
        self._tat_auto(thanh_vien)
        dat_chan_vong_moi(False)
        co_sat_tinh = self.chi_sat_tinh or not self.che_do_test
        if co_sat_tinh and self._o_lac_duong(thanh_vien):
            # Round kết thúc bằng Sát Tinh: game trả cả đội ra Lạc Dương cạnh NPC, giao dịch luôn ở đó, khỏi về thành.
            self.in_log(f"{mo_ta}: cả đội đang ở {MAP_LAC_DUONG}, không về {MAP_DAI_LY}")
        else:
            self.bao_trang_thai(f"{mo_ta}: về {MAP_DAI_LY}")
            self._ve_dai_ly(thanh_vien)
        if self.chuyen_do and doi_vien:
            self.bao_trang_thai(f"{mo_ta}: chuyển đồ cho {truong.ten}")
            self.dung.wait(GIAY_CHO_LOAD_TRUOC_GIAO_DICH)
            self._kiem_tra_dung()
            self._tap_trung(doi_vien, truong, mo_ta)
            for tv in doi_vien:
                self._chuyen_do(tv, truong, mo_ta)
        self.in_log(f"{mo_ta}: xong")
        return thanh_vien

    @staticmethod
    def _ghi_truong_nhom(truong):
        """Nhóm có người bù vào thì trưởng nhóm không cố định: ghi lại để Giao dịch cho acc chính tìm đến."""
        ds = cau_hinh.chung()["xv_truong_nhom"]
        if [truong.tk, truong.ten] not in ds:
            cau_hinh.dat_chung({"xv_truong_nhom": ds + [[truong.tk, truong.ten]]})

    def _doc(self, tv):
        try:
            return tv.game.thong_tin()
        except (LoiLua, OSError):
            return None

    def _dang_nhap(self, thanh_vien):
        cai_dat = cau_hinh.doc_tai_khoan()
        self._gan_game(thanh_vien)
        for tv in thanh_vien:
            if tv.hwnd and tv.ten:
                try:
                    tt = Game(tv.hwnd).thong_tin()
                except (LoiLua, OSError):
                    tt = None
                if tt and chuan_hoa(tt["ten"]) == chuan_hoa(tv.ten):
                    self.in_log(f"{tv.ten}: dùng lại client đang online, không đăng nhập lại")
        cac_luong = []
        for tv in thanh_vien:
            luong = LuongVaoNhanVat(dict(tv.tai_khoan, nhan_vat=tv.ten), cai_dat, self.hang_doi, tv.hwnd)
            cac_luong.append((tv, luong))
            self.cac_luong_con.append(luong)
            luong.start()
        while any(l.is_alive() for _, l in cac_luong):
            if self.dung.is_set():
                for _, l in cac_luong:
                    l.dung.set()
            time.sleep(1)
        self._kiem_tra_dung()
        con = []
        for tv, luong in cac_luong:
            self.cac_luong_con.remove(luong)
            if luong.thanh_cong and luong.game:
                tv.game, tv.hwnd = luong.game, luong.game.lua.hwnd
                con.append(tv)
            else:
                if luong.sai_rule:
                    self._danh_dau_sai_rule(tv.tk, luong.sai_rule)
                elif luong.sai_tai_khoan:
                    self._loai_tai_khoan(tv.tk, "game báo sai tài khoản/mật khẩu")
                else:
                    self.in_log(f"Bỏ tài khoản {tv.tk}: đăng nhập {tv.ten} thất bại nhiều lần (xem log Đăng nhập)")
                    if luong.pid:
                        thoat_ve_chon_may_chu(luong.pid, self.in_log, self.dung.is_set)
                tv.game = None
                # Client vẫn mở (đã về chọn máy chủ) thì giữ hwnd để tài khoản khác dùng lại.
                self._nha_client(tv, next((c["hwnd"] for c in tim_cua_so_game()
                                           if luong.pid and c["pid"] == luong.pid), None))
        return con

    def _nha_client(self, tv, hwnd):
        """Thành viên bị bỏ: client (nếu còn) đưa vào danh sách dùng lại, thành viên không giữ nó nữa."""
        tv.hwnd = None
        if hwnd and hwnd not in self.cac_hwnd:
            self.cac_hwnd.append(hwnd)

    def _tat_auto(self, thanh_vien):
        def sua(cai_dat):
            cai_dat["bat_auto"] = False
            cai_dat["bat_chuyen_sinh"] = False
            cai_dat["pho_ban_pmp"] = dict(cai_dat_pmp(cai_dat), bat=False, xoay_vong=False)
        for tv in thanh_vien:
            cau_hinh.sua_nhan_vat(tv.ten, sua)

    def _du_nhom(self, truong, thanh_vien):
        try:
            trong = [chuan_hoa(t) for t in doc_nhom(truong.game.lua)["thanh_vien"]]
        except (LoiLua, OSError, ValueError):
            return False
        return bool(trong) and trong[0] == chuan_hoa(truong.ten) \
            and all(chuan_hoa(tv.ten) in trong for tv in thanh_vien)

    @staticmethod
    def _roi_nhom_neu_sai(tv, khoa_doi, in_log=None):
        """Rời nhóm cũ / nhóm một mình không phải đội round này."""
        try:
            nhom_cu = [chuan_hoa(t) for t in doc_nhom(tv.game.lua)["thanh_vien"]]
        except (LoiLua, OSError, ValueError):
            return
        if not nhom_cu:
            return
        if nhom_cu[0] != khoa_doi[0] or any(t not in khoa_doi for t in nhom_cu):
            if in_log:
                in_log(f"{tv.ten}: rời nhóm cũ ({', '.join(nhom_cu)})")
            tv.game.lua.chay("Player:LeaveTeam()")

    def _thieu_nhom(self, truong, thanh_vien):
        try:
            da_pt = {chuan_hoa(t) for t in doc_nhom(truong.game.lua)["thanh_vien"]}
        except (LoiLua, OSError, ValueError):
            return list(thanh_vien)
        return [tv for tv in thanh_vien if chuan_hoa(tv.ten) not in da_pt]

    def _lam_moi_cau_hinh_moi_nhom(self, truong, thanh_vien):
        cau_hinh.dat_chung({"bat_moi_nhom": True, "truong_nhom": truong.ten, "bat_moi_nhan_vat_auto": False,
                            "danh_sach_moi": self._danh_sach_moi_nhom(thanh_vien)})

    def _dam_bao_nhom_pb(self, mo_ta, truong, thanh_vien, khoa_doi):
        """Giữa chừng phó bản: acc diss / vào lại thì ghép lại PT với trưởng nhóm round."""
        if len(thanh_vien) <= 1 or not self._tv_dang_choi(truong):
            return
        if self._du_nhom(truong, thanh_vien):
            return
        thieu = self._thieu_nhom(truong, thanh_vien)
        bay_gio = time.time()
        if bay_gio - getattr(self, "_luc_log_thieu_nhom", 0) >= 30:
            self._luc_log_thieu_nhom = bay_gio
            if thieu:
                ten_thieu = ", ".join(tv.ten for tv in thieu)
                self.in_log(f"{mo_ta}: nhóm chưa đủ, thiếu {ten_thieu} — bật mời lại")
            else:
                try:
                    ds = doc_nhom(truong.game.lua)["thanh_vien"]
                    tr_pt = ds[0] if ds else "?"
                except (LoiLua, OSError, ValueError):
                    tr_pt = "?"
                self.in_log(f"{mo_ta}: nhóm chưa đúng (trưởng PT {tr_pt}, cần {truong.ten}) — rời PT để ghép lại")
        for tv in thanh_vien:
            if self._tv_dang_choi(tv):
                self._roi_nhom_neu_sai(tv, khoa_doi, self.in_log)
        self._lam_moi_cau_hinh_moi_nhom(truong, thanh_vien)

    def _tv_dang_choi(self, tv):
        if not (tv.pid and con_chay(tv.pid) and tv.hwnd and win32gui.IsWindow(tv.hwnd)):
            return False
        try:
            return bool(self._doc(tv))
        except (LoiLua, OSError):
            return False

    def _cho_du_nhom_truoc_pb(self, mo_ta, truong, thanh_vien, khoa_doi):
        """Chờ đủ N người trong nhóm trước khi bật phó bản; acc diss thì đăng nhập lại."""
        can = len(thanh_vien)
        if can <= 1:
            return True
        self.in_log(f"{mo_ta}: cần {can} người trong nhóm trước khi đi phó bản")
        lan_dn = 0
        while not self.dung.is_set():
            if self._du_nhom(truong, thanh_vien):
                try:
                    ds = doc_nhom(truong.game.lua)["thanh_vien"]
                    self.in_log(f"{mo_ta}: nhóm đủ {len(ds)} người ({', '.join(ds)})")
                except (LoiLua, OSError, ValueError):
                    self.in_log(f"{mo_ta}: nhóm đủ {len(thanh_vien)} người")
                return True
            offline = [tv for tv in thanh_vien if not self._tv_dang_choi(tv)]
            if offline and lan_dn % 4 == 0:
                self.in_log(f"{mo_ta}: thiếu {len(offline)}/{can} trong game "
                            f"({', '.join(tv.ten for tv in offline)}), đăng nhập lại")
                con = self._dang_nhap(offline)
                for tv in con:
                    self._cho(lambda t=tv: self._doc(t), 60)
                    tv.anh_tui = chup_tui(tv.game.lua)
                    self._roi_nhom_neu_sai(tv, khoa_doi, self.in_log)
                if con:
                    self._lam_moi_cau_hinh_moi_nhom(truong, thanh_vien)
                if con:
                    truong = next((tv for tv in thanh_vien if tv in con), truong)
            lan_dn += 1
            self.dung.wait(GIAY_KIEM_TRA)
        return False

    def _bat_pho_ban(self, thanh_vien, truong):
        """Bật Auto + Phó bản cho cả đội. Trả về số lượt PMP của trưởng nhóm cần đạt (chế độ test), None nếu chờ hết lượt."""
        dich = None
        dem_truong = hom_nay(cai_dat_pmp(cau_hinh.cua_nhan_vat(truong.ten)))
        if self.che_do_test:
            # Test + chỉ Sát Tinh: 1 vòng Sát Tinh; test thường: 1 vòng PMP.
            dich = dem_truong["st_vong" if self.chi_sat_tinh else "so_vong"] + 1
        chi_st = self.chi_sat_tinh
        sat_tinh = self.chi_sat_tinh or not self.che_do_test
        for tv in thanh_vien:
            def sua(cai_dat, la_truong=tv is truong):
                # xoay_vong: hết lượt thì luồng PMP không bật chuyển sinh (kẻo dịch chuyển đi trước khi giao dịch).
                pmp = dict(cai_dat_pmp(cai_dat), bat=True, sat_tinh=sat_tinh, chi_sat_tinh=chi_st, xoay_vong=True)
                if not chi_st and not self.che_do_test:
                    dem = hom_nay(pmp)
                    if dem["het_luot"] and dem.get("st_vong", 0) > 0 and not dem.get("st_het"):
                        hn = dict(pmp.get("hom_nay") or dem)
                        hn["het_luot"] = False
                        pmp["hom_nay"] = hn
                        if la_truong:
                            self.in_log(
                                f"[Xoay vòng] {tv.ten}: bỏ cờ hết lượt PMP thường ({dem['so_vong']} vòng PMP, "
                                f"{dem['st_vong']} vòng ST) — ưu tiên PMP trước Sát Tinh"
                            )
                pmp["so_vong"] = dich if (la_truong and dich and not chi_st) else 0
                cai_dat["pho_ban_pmp"] = pmp
                cai_dat["bat_auto"] = True
                cai_dat["bat_chuyen_sinh"] = False
                cai_dat["chien_dau"] = dict(cai_dat.get("chien_dau") or {}, bat=True)
            cau_hinh.sua_nhan_vat(tv.ten, sua)
        return dich

    def _xong_pho_ban(self, truong, dich):
        pmp = cai_dat_pmp(cau_hinh.cua_nhan_vat(truong.ten))
        dem = hom_nay(pmp)
        if dich and self.chi_sat_tinh:
            return dem["st_vong"] >= dich or dem["st_het"]
        if dich:
            return dem["so_vong"] >= dich or dem["het_luot"]
        if self.chi_sat_tinh:
            # Chỉ sang round tiếp khi NPC báo hết lượt Sát Tinh hôm nay (đủ 20 vòng).
            return dem["st_het"]
        # Hết lượt PMP/Sát Tinh thì luồng PMP tự tắt Phó bản (_xong_pho_ban_hom_nay).
        return not pmp["bat"] and (dem["st_het"] or dem["het_luot"])

    def _cho_xong_pho_ban(self, thanh_vien, truong, dich, mo_ta):
        dang_vao_lai = {}
        khoa_doi = [chuan_hoa(tv.ten) for tv in thanh_vien]
        qua_ngay = {}
        while not self._xong_pho_ban(truong, dich):
            self._kiem_tra_dung()
            if self._dung_pb_vi_qua_ngay(mo_ta, truong, qua_ngay):
                break
            self._dam_bao_nhom_pb(mo_ta, truong, thanh_vien, khoa_doi)
            # Game bị tắt / diss giữa chừng: luồng tự đăng nhập bỏ qua tài khoản xoay vòng, nên tự vào lại ở đây.
            for tv in thanh_vien:
                luong = dang_vao_lai.get(tv.tk)
                if luong is not None:
                    if luong.is_alive():
                        continue
                    del dang_vao_lai[tv.tk]
                    self.cac_luong_con.remove(luong)
                    if luong.thanh_cong and luong.game:
                        tv.game, tv.hwnd = luong.game, luong.game.lua.hwnd
                        self.in_log(f"{mo_ta}: {tv.ten} đã vào lại game")
                        self._roi_nhom_neu_sai(tv, khoa_doi, self.in_log)
                        self._lam_moi_cau_hinh_moi_nhom(truong, thanh_vien)
                    continue
                if tv.pid and con_chay(tv.pid) and tv.hwnd and win32gui.IsWindow(tv.hwnd):
                    continue
                self.in_log(f"{mo_ta}: game của {tv.ten} đã tắt, đăng nhập lại")
                luong = LuongVaoNhanVat(dict(tv.tai_khoan, nhan_vat=tv.ten), cau_hinh.doc_tai_khoan(), self.hang_doi)
                dang_vao_lai[tv.tk] = luong
                self.cac_luong_con.append(luong)
                luong.start()
            self.dung.wait(GIAY_KIEM_TRA)
        for luong in dang_vao_lai.values():
            luong.dung.set()

    def _dung_pb_vi_qua_ngay(self, mo_ta, truong, qua_ngay):
        """
        Qua 0h: trưởng nhóm đang trong phó bản thì chặn vòng mới, đi nốt vòng đang dở; không ở trong phó bản / đi
        xong vòng thì True để tắt auto, giao dịch rồi làm mới danh sách và chạy lại từ nhóm 1.
        """
        if not self.chay_lai_ngay_moi or self.che_do_test or date.today() == self._ngay_luot:
            return False
        if "luc" not in qua_ngay:
            qua_ngay["luc"] = time.time()
            dat_chan_vong_moi(True)
            if dang_chay_vong(truong.ten) and la_map_trong_pho_ban((self._doc(truong) or {}).get("map")):
                self.in_log(f"{mo_ta}: qua 0h, nhóm đang trong phó bản — đi nốt vòng này rồi làm mới danh sách, "
                            "chạy lại từ nhóm 1")
                self.bao_trang_thai(f"{mo_ta}: qua 0h, đi nốt vòng phó bản đang dở")
                return False
            self.in_log(f"{mo_ta}: qua 0h, nhóm không ở trong phó bản — dừng, làm mới danh sách, chạy lại từ nhóm 1")
            return True
        if dang_chay_vong(truong.ten) and time.time() - qua_ngay["luc"] < GIAY_MOT_VONG + 60:
            return False
        self.in_log(f"{mo_ta}: đã ra khỏi phó bản sau 0h — làm mới danh sách, chạy lại từ nhóm 1")
        return True

    def _o_lac_duong(self, thanh_vien):
        """Chờ tối đa GIAY_CHO_RA_LAC_DUONG cho cả đội ra Lạc Dương (vừa xong Sát Tinh). True nếu cả đội đã ở đó."""
        het_han = time.time() + GIAY_CHO_RA_LAC_DUONG
        while True:
            self._kiem_tra_dung()
            if all(la_lac_duong((self._doc(tv) or {}).get("map")) for tv in thanh_vien):
                return True
            if time.time() >= het_han:
                return False
            self.dung.wait(1)

    def _ve_dai_ly(self, thanh_vien):
        luc_ve = {}
        het_han = time.time() + GIAY_CHO_VE_DAI_LY
        while time.time() < het_han:
            self._kiem_tra_dung()
            chua = []
            for tv in thanh_vien:
                tt = self._doc(tv)
                if tt and la_dai_ly(tt["map"]):
                    continue
                chua.append(tv)
                if tt and time.time() - luc_ve.get(tv.tk, 0) >= GIAY_GIUA_HAI_LAN_VE_THANH:
                    luc_ve[tv.tk] = time.time()
                    try:
                        chuan_bi_ve_thanh(tv.game)
                        tv.game.lua.chay(ma_dung_ky_nang_theo_dinh_nghia(KY_NANG_VE_THANH))
                    except LoiLua:
                        pass
            if not chua:
                return
            self.dung.wait(1)
        self.in_log(f"Sau {GIAY_CHO_VE_DAI_LY} giây vẫn chưa về {MAP_DAI_LY}: "
                    + ", ".join(tv.ten for tv in thanh_vien if not la_dai_ly((self._doc(tv) or {}).get("map"))))

    def _tap_trung(self, doi_vien, truong, mo_ta):
        """Trưởng nhóm gửi vị trí cho cả đội; đội viên ở xa cùng lúc tự chạy tới (gửi lại định kỳ) để giao dịch."""
        het_han = time.time() + GIAY_TAP_TRUNG
        da_bao = False
        o_xa = []
        while time.time() < het_han:
            self._kiem_tra_dung()
            vt = self._doc(truong)
            if not vt:
                self.dung.wait(1)
                continue
            o_xa = []
            for tv in doi_vien:
                tt = self._doc(tv) if tv.game else None
                if not tt or tt["map"] != vt["map"]:
                    continue
                if math.hypot(tt["x"] - vt["x"], tt["y"] - vt["y"]) <= KHOANG_CACH_GIAO_DICH:
                    continue
                o_xa.append(tv)
                try:
                    tv.game.lua.chay(f"AutoRunToTarget({int(vt['x']) + 1}, {int(vt['y'])})")
                except (LoiLua, OSError):
                    pass
            if not o_xa:
                return
            if not da_bao:
                da_bao = True
                self.in_log(f"{mo_ta}: {truong.ten} gửi vị trí ({int(vt['x'])}, {int(vt['y'])}), "
                            f"{', '.join(tv.ten for tv in o_xa)} chạy tới để giao dịch")
            self.dung.wait(GIAY_GUI_LAI_VI_TRI)
        self.in_log(f"{mo_ta}: sau {GIAY_TAP_TRUNG} giây {', '.join(tv.ten for tv in o_xa)} vẫn chưa tới gần "
                    f"{truong.ten}")

    def _chuyen_do(self, tv, truong, mo_ta):
        for lan in range(1, SO_LAN_THU_GIAO_DICH + 1):
            try:
                cac_o = o_do_moi(tv.game.lua, tv.anh_tui)
                if not cac_o:
                    if lan == 1:
                        self.in_log(f"{tv.ten}: không nhặt được đồ mới, khỏi giao dịch")
                    return
                self.in_log(f"{tv.ten}: có {len(cac_o)} ô đồ mới, giao dịch cho {truong.ten}")
                GiaoDich(tv.game, truong.game, tv.ten, truong.ten, self.in_log, self.dung.is_set).chuyen(cac_o)
                return
            except (LoiGiaoDich, LoiLua, OSError) as loi:
                self._kiem_tra_dung()
                if lan >= SO_LAN_THU_GIAO_DICH:
                    self.in_log(f"{tv.ten}: giao dịch cho {truong.ten} thất bại: {loi}")
                    return
                self.in_log(f"{tv.ten}: giao dịch cho {truong.ten} lỗi ({loi}), thử lại lần {lan + 1}")
            self.dung.wait(GIAY_GIUA_HAI_LAN_GIAO_DICH)
            self._kiem_tra_dung()
            self._tap_trung([tv], truong, mo_ta)
