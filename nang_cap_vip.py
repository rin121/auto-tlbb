"""
NÂNG CẤP VIP (level 3), ba bước chạy riêng. Mỗi bước acc chính chỉ rút và giao một loại mảnh,
acc đã xong level 2 đổi tại NPC Trao Đổi, mang món mới và chỉ vứt món vừa tháo.

    Kim Vương     — 5000 Mảnh Vỡ Trang Bị, dòng Đổi Trang Bị VIP
    Thú cưỡi VIP  — 500 Mảnh Vỡ Thú Cưỡi, dòng Đổi Thú Cưỡi VIP
    Thời trang VIP — 500 Mảnh Vỡ Thời Trang, dòng Đổi Thời Trang VIP

Khóa từ ghi tay 2026-11-18:
    ghi_20261118_154125 GaoDẻLâu — rút Packet_Temporary_Select, 250 / lần, cách 3 giây;
        giao PlayerList + ContexMenu_Exchange, 5 ô, Exchange_Lock, ExchangeSafe_Confirm("HH:MM"), Trade_Accept.
    ghi_20261118_155538 cosato777 — NPC Trao Đổi, QuestFrameOptionClicked(-1, 0, dòng),
        XiaoXiang_DuiHuanUI2_Clicked(ô) rồi OK. Thành công = túi có đúng mã món.

Thiếu mảnh: không rút, không giao, đăng xuất phiên này rồi xoay vòng.
Đủ và đổi xong: không xoay vòng. Chưa làm bước tẩy điểm.
"""
import json
import math
import os
import re
import threading
import time
import traceback
from datetime import datetime

from auto_chuyen_sinh import chuan_hoa
from cua_so_game import tim_cua_so_game
from dang_nhap import bo_dau, dang_hien, trong_cua_so
from giao_acc_chinh import (GIAY_CHAY_TOI, GIAY_CHO_CUA_SO, GIAY_GIUA_RUT_TCCN, KHOANG_CACH_DUNG_CHO,
                            MA_DONG_CUA_SO, MA_LIET_KE_TCCN, NPC_TRAO_DOI, SO_LAN_DANG_NHAP_LAI,
                            GiaoAccChinhEngine, LoiGiaoAccChinh, _Dung, ma_bam_o_doi, ma_xac_nhan_doi)
from giao_dich import GiaoDich, LoiGiaoDich, doc_tui
from lua_game import LoiLua
from nang_cap_nhan_vat import MA_TRANG_BI, da_lam, doc_bang
from nhan_vat_moi import NhanDoTanThu
from pho_ban_pmp import MA_CHUOT_PHAI, LoiPhoBan
from pho_ban_pmp import _Dung as DungPhoBan
from rut_ngoc_tccn import SO_RUT_TCCN, ma_rut_tccn
from thu_muc import THU_MUC_APP
from vut_rac import LoiVutRac, vut_theo_ma
from xoay_vong import (SO_ROUND_TOI_DA, cac_tai_khoan_dang_tich, ten_round,
                       tim_game_cua_tai_khoan, tim_hwnd_theo_nhan_vat)

DUONG_DAN = os.path.join(THU_MUC_APP, "nang_cap_vip_da_xong.json")
CUA_SO_DOI = "XiaoXiang_DuiHuanUI2"
CHONG_TUI = 200
# Mỗi lần giao tối đa 5 ô (ghi_20261118_154125: 31 ô = 7 lần).
SO_O_MOT_LAN = 5

# (khóa, mã, tên, số lượng một acc). Ô Thiên Cơ đọc lúc chạy, không khóa số ô.
MANH = (
    {"khoa": "trang bi", "ma": 30503234, "ten": "Mảnh Vỡ Trang Bị", "so": 5000},
    {"khoa": "thu cuoi", "ma": 30503264, "ten": "Mảnh Vỡ Thú Cưỡi", "so": 500},
    {"khoa": "thoi trang", "ma": 30503263, "ten": "Mảnh Vỡ Thời Trang", "so": 500},
)
_TEN_MANH = {
    "manh vo trang bi": "trang bi",
    "manh vo thu cuoi": "thu cuoi",
    "manh vo thoi trang": "thoi trang",
}
_MA_MANH = {m["ma"]: m["khoa"] for m in MANH}

# Ba bước độc lập. dong = extra của QuestFrameOptionClicked(-1, 0, extra).
BUOC = (
    {"khoa": "trang bi", "ten": "Kim Vương", "dong": 1},
    {"khoa": "thu cuoi", "ten": "Thú cưỡi VIP", "dong": 4},
    {"khoa": "thoi trang", "ten": "Thời trang VIP", "dong": 3},
)
_BUOC = {b["khoa"]: b for b in BUOC}
KHOA_BUOC = tuple(b["khoa"] for b in BUOC)

# (dòng hội thoại extra, ô Clicked, mã, tên). Dòng = QuestFrameOptionClicked(-1, 0, extra).
# 1 Đổi Trang Bị VIP, 3 Đổi Thời Trang VIP, 4 Đổi Thú Cưỡi VIP.
MON = (
    (1, 1, 10162460, "Kim Vương - Khôi"),
    (1, 2, 10162461, "Kim Vương - Ngoa"),
    (1, 3, 10162462, "Kim Vương - Thủ"),
    (1, 4, 10162463, "Kim Vương - Giáp"),
    (1, 5, 10162464, "Kim Vương - Kiên"),
    (1, 6, 10162465, "Kim Vương - Liên"),
    (1, 7, 10162466, "Kim Vương - Đái"),
    (1, 8, 10162467, "Kim Vương - Giới"),
    (1, 9, 10162468, "Kim Vương - Ngọc"),
    (1, 10, 10162469, "Kim Vương - Uyển"),
    (3, 35, 10163082, "Áo Tắm - VIP2"),
    (4, 35, 10165078, "Toạ Kỵ: Ngọc Đoàn Đoàn - VIP2"),
)
DONG_MENU = {1: (0, 1), 3: (0, 3), 4: (0, 4)}
MA_MOI = {ma for _, _, ma, _ in MON}

_khoa = threading.Lock()


class ThieuManh(LoiGiaoAccChinh):
    """Túi + Thiên Cơ không đủ một acc. Không rút."""

    def __init__(self, thieu):
        self.thieu = dict(thieu)
        super().__init__(mo_ta_thieu(thieu))


def _ten_sach(ten):
    return re.sub(r"#[-0-9a-fA-F]*", "", ten or "").strip()


def khoa_tu_ten(ten):
    """Khóa mảnh từ tên hoặc từ mã (chuỗi số) trong danh sách Thiên Cơ."""
    chu = _ten_sach(ten)
    thuong = bo_dau(chu).strip()
    khoa = _TEN_MANH.get(thuong)
    if khoa:
        return khoa
    # «Mảnh Vỡ Trang Bị (Khóa)» vẫn là mảnh. Bản VIP là món khác, không tính.
    if "vip" not in thuong:
        for ten_khoa, khoa_khoa in _TEN_MANH.items():
            if thuong.startswith(ten_khoa):
                return khoa_khoa
    try:
        return _MA_MANH.get(int(float(chu)))
    except (TypeError, ValueError):
        return None


def o_manh_tccn(bang, khoa, so_rut=250):
    """
    (ô, số trong ô) của chồng lớn nhất đúng loại.
    Ô có món nhưng số đọc được là 0 (máy ảo hay trả 0) thì vẫn rút `so_rut`.
    """
    if not isinstance(bang, list):
        return None
    duong = []
    for o, ten, so in bang:
        if khoa_tu_ten(ten) != khoa:
            continue
        try:
            n = int(so)
        except (TypeError, ValueError):
            n = 0
        duong.append((int(o), n))
    if not duong:
        return None
    co = [x for x in duong if x[1] > 0]
    o, n = max(co or duong, key=lambda x: x[1])
    if n < 1:
        n = so_rut
    return o, n


def tong_ma(tui, ma):
    return sum(so for (_, _), (m, so, _) in tui.items() if m == ma)


def ton_theo_khoa(tui):
    return {m["khoa"]: tong_ma(tui, m["ma"]) for m in MANH}


def ton_tccn(bang):
    """{khóa: tổng số} từ danh sách ô Thiên Cơ [(ô, tên, số)]."""
    tong = {m["khoa"]: 0 for m in MANH}
    if not isinstance(bang, list):
        return tong
    for _, ten, so in bang:
        khoa = khoa_tu_ten(ten)
        if khoa:
            tong[khoa] += int(so)
    return tong


def phan_manh(trong_tui, trong_tccn, khoa=None):
    """
    (cần rút, thiếu). Cần rút = phần chưa có trong túi. Thiếu = Thiên Cơ không đủ phần đó.
    Có thiếu thì không rút loại nào. `khoa` giới hạn một bước (trang bi / thu cuoi / thoi trang).
    """
    rut, thieu = {}, {}
    for m in MANH:
        if khoa is not None and m["khoa"] != khoa:
            continue
        can = max(0, m["so"] - int(trong_tui.get(m["khoa"], 0)))
        co = int(trong_tccn.get(m["khoa"], 0))
        if can > co:
            thieu[m["khoa"]] = can - co
        elif can:
            rut[m["khoa"]] = can
    return rut, thieu


def mo_ta_thieu(thieu):
    ten = {m["khoa"]: m["ten"] for m in MANH}
    return "Thiên Cơ thiếu " + ", ".join(f"{ten[k]} {so}" for k, so in thieu.items())


def so_o_can(so_manh, chong=CHONG_TUI):
    """Số ô túi một loại mảnh chiếm khi chồng `chong` (ghi: 200)."""
    if so_manh <= 0:
        return 0
    return (int(so_manh) + chong - 1) // chong


def ket_luan_rut(tui_truoc, tui_sau, tccn_truoc, tccn_sau):
    """
    Sau một lần bấm rút.
    'xong' túi đã tăng.
    'cho' Thiên Cơ đã giảm hoặc chưa đọc được: server lag, không bấm rút lại.
    'rut_lai' túi và Thiên Cơ đều chưa đổi: bấm rút lại.
    """
    if tui_sau > tui_truoc:
        return "xong"
    if tccn_truoc is None or tccn_sau is None or tccn_sau < tccn_truoc:
        return "cho"
    return "rut_lai"


def nen_rut_tiep(loi):
    """Lỗi lúc rút Thiên Cơ thì rút tiếp. Hết mảnh hoặc túi không còn chỗ thì dừng."""
    if isinstance(loi, (LoiLua, OSError)):
        return True
    chu = bo_dau(str(loi))
    if "o trong" in chu or " het " in chu:
        return False
    return True


def la_loi_diss(loi):
    """Game treo, cửa sổ đóng, hoặc không còn process — acc chính bị ngắt."""
    chu = str(loi).lower()
    return any(mau in chu for mau in (
        "đã đóng", "đã tắt", "invalid window", "không nạp được dll", "không phản hồi"))


def can_mo_lai_client(loi, cua_so_con, da_thoat):
    """Đóng hẳn hoặc đã bấm Hủy thoát game thì mở client mới. Treo mà cửa sổ còn thì bấm Duyệt trước."""
    if da_thoat or not cua_so_con:
        return True
    chu = str(loi).lower()
    return any(mau in chu for mau in ("đã đóng", "đã tắt", "invalid window", "không nạp được dll"))


def ket_luan_giao(loi):
    """Sau một lần chuyển đồ. None là xong. Lỗi giao dịch thì giao lại phần còn thiếu. Dừng của user thì dừng."""
    if loi is None:
        return "xong"
    if str(loi) == "đã dừng":
        return "dung"
    return "giao_lai"


def ket_luan_doi(co_mon, manh_truoc, manh_sau):
    """
    Sau một lần bấm đổi.
    'xong' túi hoặc người đã có món.
    'cho' mảnh đã giảm hoặc chưa đọc được: server đã nhận, không bấm đổi lại.
    'doi_lai' món và mảnh đều chưa đổi: bấm đổi lại.
    """
    if co_mon:
        return "xong"
    if manh_truoc is None or manh_sau is None or manh_sau < manh_truoc:
        return "cho"
    return "doi_lai"


def so_lan_giao(so_o, moi_lan=SO_O_MOT_LAN):
    if so_o <= 0:
        return 0
    return (int(so_o) + moi_lan - 1) // moi_lan


def o_can_giao(tui, can_theo_ma):
    """Các ô (túi, ô) đưa đủ `can_theo_ma` {mã: số}, không lấy dư chồng sau khi đã đủ."""
    con = {int(ma): int(so) for ma, so in can_theo_ma.items() if int(so) > 0}
    kq = []
    for khoa in sorted(tui):
        ma, so, _ = tui[khoa]
        if con.get(ma, 0) <= 0:
            continue
        kq.append(khoa)
        con[ma] -= so
    return kq


def mon_chua_co(cac_ma, khoa=None):
    """Món VIP chưa nằm trong túi hoặc trên người. `khoa` chỉ lấy món của một bước."""
    co = set(cac_ma)
    dong = None if khoa is None else _BUOC[khoa]["dong"]
    return [m for m in MON if m[2] not in co and (dong is None or m[0] == dong)]


def ma_vua_thao(truoc, sau, ma_moi=None):
    """Mã từng nằm trên người, giờ không còn, và không phải món VIP mới."""
    moi = MA_MOI if ma_moi is None else set(ma_moi)
    return set(truoc.values()) - set(sau.values()) - moi


def nhan_vat_cua_tk(tk):
    """Tên nhân vật trên dòng tài khoản. Trống thì ba tên round."""
    ten = (tk.get("nhan_vat") or "").strip()
    if ten:
        return [ten]
    login = tk.get("ten_dang_nhap") or ""
    return [ten_round(login, r) for r in range(SO_ROUND_TOI_DA)]


def ba_nhan_vat(tk):
    """Ba nhân vật của một tài khoản. Ô tên trên bảng tài khoản chỉ ghi nhân vật đầu."""
    login = (tk.get("ten_dang_nhap") or "").strip()
    if not login:
        ten = (tk.get("nhan_vat") or "").strip()
        return [ten] if ten else []
    return list(dict.fromkeys(ten_round(login, r) for r in range(SO_ROUND_TOI_DA)))


def _bo_acc_chinh(tk, ten, ten_chinh, tk_chinh):
    if (tk.get("ten_dang_nhap") or "").lower() == (tk_chinh or "").lower():
        return True
    return not ten or chuan_hoa(ten) == chuan_hoa(ten_chinh)


def ung_vien(cac_tk, ten_chinh, tk_chinh, da_lv2, da_vip):
    """[(tài khoản, tên)] đã xong level 2, chưa VIP, không phải acc chính."""
    kq = []
    for tk in cac_tk:
        for ten in nhan_vat_cua_tk(tk):
            if _bo_acc_chinh(tk, ten, ten_chinh, tk_chinh):
                continue
            if not da_lv2(ten) or da_vip(ten):
                continue
            kq.append((tk, ten))
    return kq


def dong_bang(cac_tk, ten_chinh, tk_chinh, da_lv2, da_vip, buoc_xong=None):
    """
    [(tài khoản, tên, 'level2'|'vip', frozenset khóa đã xong)] để bấm chọn.
    Mỗi tài khoản có ba nhân vật round. Chưa xong level 2 thì không hiện.
    `buoc_xong(tên)` trả các bước đã xong; không truyền thì `da_vip` True nghĩa là đủ ba bước.
    """
    kq = []
    for tk in cac_tk:
        for ten in ba_nhan_vat(tk):
            if _bo_acc_chinh(tk, ten, ten_chinh, tk_chinh):
                continue
            if buoc_xong:
                xong = frozenset(k for k in buoc_xong(ten) if k in _BUOC)
            elif da_vip(ten):
                xong = frozenset(KHOA_BUOC)
            else:
                xong = frozenset()
            if len(xong) == len(KHOA_BUOC):
                kq.append((tk, ten, "vip", xong))
            elif da_lv2(ten):
                kq.append((tk, ten, "level2", xong))
    return kq


def buoc_chon(cac_khoa):
    """Các bước được tick, luôn theo thứ tự Kim Vương → thú cưỡi → thời trang."""
    hop = set(cac_khoa or ())
    return [k for k in KHOA_BUOC if k in hop]


def sap_uu_tien_dang_online(con, dang_online):
    """Giữ thứ tự bảng. `dang_online` không kéo nhân vật đang mở lên trước người đứng đầu."""
    del dang_online
    return list(con)


def mo_ta_bang(xong):
    """Cột trạng thái: Level 2, các bước đã xong, hoặc Đã VIP."""
    xong = set(xong or ())
    if set(KHOA_BUOC) <= xong:
        return "Đã VIP"
    if not xong:
        return "Level 2"
    ngan = {"trang bi": "Kim Vương", "thu cuoi": "thú", "thoi trang": "áo"}
    return "Level 2 · " + ", ".join(ngan[k] for k in KHOA_BUOC if k in xong)


def doc(duong_dan=None):
    duong_dan = duong_dan or DUONG_DAN
    try:
        with open(duong_dan, encoding="utf-8") as f:
            du_lieu = json.load(f)
    except (OSError, ValueError):
        return {}
    return du_lieu if isinstance(du_lieu, dict) else {}


def _ghi(du_lieu, duong_dan):
    tam = f"{duong_dan}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=1)
    os.replace(tam, duong_dan)


def _muc(ten, duong_dan):
    muc = doc(duong_dan).get(chuan_hoa(ten)) if ten else None
    return muc if isinstance(muc, dict) else None


def _tap_buoc(muc):
    """Khóa bước đã đổi xong. Cờ xong cũ = đủ cả ba bước."""
    if not muc:
        return set()
    if muc.get("xong") is True:
        return set(KHOA_BUOC)
    return {k for k in (muc.get("buoc_xong") or []) if k in _BUOC}


def buoc_da_xong(ten, duong_dan=None):
    return _tap_buoc(_muc(ten, duong_dan))


def da_xong_buoc(ten, khoa, duong_dan=None):
    return khoa in _tap_buoc(_muc(ten, duong_dan))


def da_xong(ten, duong_dan=None):
    return set(KHOA_BUOC) <= _tap_buoc(_muc(ten, duong_dan))


def da_nhan_buoc(ten, khoa, duong_dan=None):
    """Đã giao mảnh của bước này (đổi dở thì không rút lại). Cờ «nhan» cũ = đã giao cả ba loại."""
    muc = _muc(ten, duong_dan)
    if not muc:
        return False
    if khoa in _tap_buoc(muc):
        return True
    if khoa in (muc.get("nhan_buoc") or []):
        return True
    return "nhan" in (muc.get("buoc") or [])


def da_nhan_manh(ten, duong_dan=None):
    muc = _muc(ten, duong_dan)
    if not muc:
        return False
    return muc.get("xong") is True or "nhan" in muc.get("buoc", [])


def ma_thao_da_ghi(ten, duong_dan=None):
    muc = _muc(ten, duong_dan)
    if not muc:
        return set()
    return {int(m) for m in muc.get("thao", [])}


def _cap_nhat(ten, duong_dan, sua):
    duong_dan = duong_dan or DUONG_DAN
    with _khoa:
        du_lieu = doc(duong_dan)
        muc = du_lieu.get(chuan_hoa(ten))
        if not isinstance(muc, dict):
            muc = {"ten": ten, "xong": False, "buoc": [], "thao": []}
        sua(muc)
        muc["ten"] = ten
        muc["luc"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        du_lieu[chuan_hoa(ten)] = muc
        _ghi(du_lieu, duong_dan)


def danh_dau_nhan(ten, duong_dan=None):
    def sua(muc):
        muc["buoc"] = sorted(set(muc.get("buoc", [])) | {"nhan"})
        muc["xong"] = False
    _cap_nhat(ten, duong_dan, sua)


def danh_dau_nhan_buoc(ten, khoa, duong_dan=None):
    def sua(muc):
        muc["nhan_buoc"] = sorted(set(muc.get("nhan_buoc") or []) | {khoa})
    _cap_nhat(ten, duong_dan, sua)


def danh_dau_buoc(ten, khoa, duong_dan=None):
    """Đánh dấu một bước đã đổi xong. Đủ ba bước thì xong VIP."""
    def sua(muc):
        xong = set(muc.get("buoc_xong") or []) | {khoa}
        if muc.get("xong") is True:
            xong |= set(KHOA_BUOC)
        muc["buoc_xong"] = [k for k in KHOA_BUOC if k in xong]
        muc["nhan_buoc"] = sorted(set(muc.get("nhan_buoc") or []) | {khoa})
        muc["xong"] = set(KHOA_BUOC) <= set(muc["buoc_xong"])
    _cap_nhat(ten, duong_dan, sua)


def danh_dau_thao(ten, cac_ma, duong_dan=None):
    def sua(muc):
        muc["thao"] = sorted(set(muc.get("thao", [])) | {int(m) for m in cac_ma})
    _cap_nhat(ten, duong_dan, sua)


def danh_dau_xong(ten, duong_dan=None):
    def sua(muc):
        muc["xong"] = True
        muc["buoc"] = sorted(set(muc.get("buoc", [])) | {"nhan"})
    _cap_nhat(ten, duong_dan, sua)


class LuongNangCapVip(threading.Thread, GiaoAccChinhEngine):
    """Đăng nhập acc chính rồi từng acc đã xong level 2. Không kiểm tra quy tắc tên caychay10."""

    kiem_tra_rule_ten = False
    ghi_so_tui = False
    thoat_sau_giao = False

    def __init__(self, hang_doi, tk_chinh, cac_tk=None, duong_dan=None, buoc="trang bi", cac_buoc=None):
        super().__init__(daemon=True)
        chon = buoc_chon(cac_buoc if cac_buoc is not None else [buoc])
        if not chon:
            raise ValueError(buoc)
        self.hang_doi = hang_doi
        self.dung = threading.Event()
        self.cac_buoc = chon
        self.buoc = chon[0]
        self.tk_chinh = tk_chinh
        self.cac_tk = list(cac_tai_khoan_dang_tich() if cac_tk is None else cac_tk)
        self.duong_dan = duong_dan or DUONG_DAN
        self.chinh = None
        self.phu = None
        self.ten_phu = ""
        self.hwnd_truong = None
        self.pid_dieu_khien = set()
        self.cac_luong_con = []
        self.tk_da_thoat = set()
        self.tien_trinh = {}
        self.ds_truong = []
        self.loai_tru = []

    def dang_dieu_khien(self, pid):
        if not self.is_alive():
            return False
        return pid in self.pid_dieu_khien or any(l.pid == pid and l.is_alive() for l in list(self.cac_luong_con))

    def cac_tai_khoan(self):
        if not self.is_alive():
            return set()
        return {self.tk_chinh["ten_dang_nhap"].lower()} | {
            (tk.get("ten_dang_nhap") or "").lower() for tk, _ in self._danh_sach()}

    def _ten_buoc(self):
        return _BUOC[self.buoc]["ten"]

    def _manh(self):
        return next(m for m in MANH if m["khoa"] == self.buoc)

    def in_log(self, chu):
        self.hang_doi.put(("log", f"[Nâng cấp VIP] {chu}"))

    def bao_trang_thai(self, chu):
        self.hang_doi.put(("trang_thai_nang_cap_vip", chu))

    def _danh_sach(self):
        return ung_vien(
            self.cac_tk, self.tk_chinh.get("nhan_vat"), self.tk_chinh.get("ten_dang_nhap"),
            lambda ten: da_lam(ten),
            lambda ten: all(da_xong_buoc(ten, k, self.duong_dan) for k in self.cac_buoc))

    def run(self):
        try:
            self._chay()
        except ThieuManh as loi:
            self.in_log(f"{loi}. Không rút, không giao. Đăng xuất và xoay vòng.")
            self._dang_xuat_phien()
            self.bao_trang_thai("Thiếu mảnh — xoay vòng")
        except _Dung:
            self.in_log("Đã dừng")
            self.bao_trang_thai("Đã dừng")
        except LoiGiaoAccChinh as loi:
            self.in_log(f"Dừng: {loi}")
            self.bao_trang_thai(f"Dừng: {loi}")
        except Exception:
            self.in_log(f"Lỗi không mong đợi\n{traceback.format_exc()}")
            self.bao_trang_thai("Lỗi, xem log")
        finally:
            for game in (self.phu, self.chinh):
                if not game:
                    continue
                try:
                    game.lua.chay(MA_DONG_CUA_SO)
                except (LoiLua, OSError, AttributeError):
                    pass

    def _chay(self):
        con = self._danh_sach()
        ten_chinh = self.tk_chinh.get("nhan_vat") or ""
        ten_buoc = ", ".join(_BUOC[k]["ten"] for k in self.cac_buoc)
        if not con:
            self.in_log(f"{ten_buoc}: không còn nhân vật chưa xong (trừ {ten_chinh})")
            self.bao_trang_thai(f"Xong {ten_buoc} (không còn nhân vật)")
            return
        self.in_log(f"{ten_buoc} — acc chính {ten_chinh}, {len(con)} nhân vật: "
                    + ", ".join(ten for _, ten in con))
        self.ten_giu_online = {chuan_hoa(ten_chinh)}
        self.tk_giu_online = {(self.tk_chinh.get("ten_dang_nhap") or "").lower()}
        dang_online = self._giu_nhan_vat_dang_online(con)
        for ten_on in dang_online:
            self.in_log(f"{ten_on} đang đăng nhập, không đăng xuất")
        con = sap_uu_tien_dang_online(con, dang_online)
        self.bao_trang_thai(f"Vào acc chính {ten_chinh}")
        self._vao_acc_chinh()
        for so, (tk, ten) in enumerate(con, 1):
            self._kiem_tra_dung()
            self.bao_trang_thai(f"{so}/{len(con)}: {ten}")
            self._mot_acc(tk, ten)
        ten_buoc_xong = ", ".join(_BUOC[k]["ten"] for k in self.cac_buoc)
        self.in_log(f"Xong {ten_buoc_xong}, kể cả tài khoản tích cuối. Đăng xuất và xoay vòng.")
        self._dang_xuat_phien()
        self.bao_trang_thai("Xong — xoay vòng")

    def _dang_xuat_phien(self):
        if self.phu:
            self._thoat_game_pho_ban(self.phu, self.ten_phu or "acc phụ")
            self.phu = None
        if self.chinh:
            self._thoat_game_pho_ban(self.chinh, self.tk_chinh.get("nhan_vat") or "acc chính")
            self.chinh = None

    def _tui(self, game):
        return doc_tui(game.lua)

    def _trang_bi(self, game):
        """{ô: mã} đang mang."""
        return {o: ma for o, (ma, _) in doc_bang(game.lua.chay(MA_TRANG_BI)).items()}

    def _cac_ma_co(self, game):
        tui = self._tui(game)
        return {ma for (_, _), (ma, _, _) in tui.items()} | set(self._trang_bi(game).values())

    def _mot_acc(self, tk, ten):
        con = [k for k in self.cac_buoc if not da_xong_buoc(ten, k, self.duong_dan)]
        if not con:
            self.in_log(f"{ten}: các bước đang chọn đã xong")
            return
        da_vao = False
        for khoa in con:
            self._kiem_tra_dung()
            self.buoc = khoa
            manh = self._manh()
            self.bao_trang_thai(f"{ten}: {self._ten_buoc()}")
            if not da_nhan_buoc(ten, khoa, self.duong_dan):
                self._rut_tiep(ten)
                if not da_vao:
                    self._vao_phu(tk, ten)
                    da_vao = True
                self._giao(ten)
                while not self._du_manh(self.phu):
                    self._kiem_tra_dung()
                    self.in_log(f"{ten}: túi chưa đủ {manh['ten']}, giao tiếp")
                    self._giao(ten)
                danh_dau_nhan_buoc(ten, khoa, self.duong_dan)
                self.in_log(f"{ten}: đã nhận đủ {manh['ten']}, bắt đầu đổi")
            else:
                self.in_log(f"{ten}: đã nhận {manh['ten']} lần trước, đổi tiếp không rút lại")
                if not da_vao:
                    self._vao_phu(tk, ten)
                    da_vao = True
            self._doi(ten)
            self._mang_va_vut(ten)
            danh_dau_buoc(ten, khoa, self.duong_dan)
            self.in_log(f"{ten}: xong {self._ten_buoc()}")
        self.ten_giu_online.discard(chuan_hoa(ten))
        self._thoat_game_pho_ban(self.phu, ten)
        self.phu = None

    def _ten_dang_trong_game(self, cac_ten):
        """Tên trong danh sách đang mở game."""
        thay, da = [], set()
        for ten in cac_ten:
            khoa = chuan_hoa(ten)
            if not khoa or khoa in da:
                continue
            if tim_hwnd_theo_nhan_vat(ten):
                da.add(khoa)
                thay.append(ten)
        return thay

    def _giu_nhan_vat_dang_online(self, con):
        dang = self._ten_dang_trong_game([ten for _, ten in con])
        for ten in dang:
            self.ten_giu_online.add(chuan_hoa(ten))
        return dang

    def _du_manh(self, game):
        ton = ton_theo_khoa(self._tui(game))
        manh = self._manh()
        return ton[manh["khoa"]] >= manh["so"]

    def _cua_so_song(self, game):
        hwnd = self._hwnd_dang_giu(game)
        if not hwnd:
            return False
        try:
            import win32gui
            return bool(win32gui.IsWindow(hwnd))
        except (OSError, ValueError):
            return False

    def _bam_duyet_mat_ket_noi(self):
        """Bấm Duyệt hộp mất kết nối nếu cửa sổ acc chính còn. True khi đã bấm Duyệt hoặc Hủy."""
        from mat_ket_noi import XuLyMatKetNoi
        game = self.chinh
        if not game or not getattr(game, "lua", None):
            return False
        xl = getattr(self, "_xu_ly_mat_ket_noi", None)
        if xl is None or getattr(xl, "lua", None) is not game.lua:
            xl = XuLyMatKetNoi(game.lua, self.in_log)
            self._xu_ly_mat_ket_noi = xl
        try:
            xl.kiem_tra(True)
        except (LoiLua, OSError):
            return False
        return bool(xl.da_duyet or xl.da_thoat)

    def _mo_lai_acc_chinh(self):
        ten = self.tk_chinh.get("nhan_vat") or "acc chính"
        self._lan_mo_lai_diss = getattr(self, "_lan_mo_lai_diss", 0) + 1
        if self._lan_mo_lai_diss > SO_LAN_DANG_NHAP_LAI:
            raise LoiGiaoAccChinh(f"{ten}: ngắt kết nối quá {SO_LAN_DANG_NHAP_LAI} lần, dừng nâng cấp VIP")
        self.in_log(f"{ten}: mở lại client và đăng nhập ({self._lan_mo_lai_diss}/{SO_LAN_DANG_NHAP_LAI})")
        self._xu_ly_mat_ket_noi = None
        self.chinh = self._dang_nhap_lai_mot(
            self.tk_chinh, self.chinh, ten, self._hwnd_dang_giu(self.phu))

    def _tat_client_treo(self):
        game = self.chinh
        pid = getattr(getattr(game, "lua", None), "pid", None)
        if not pid:
            return
        from dang_nhap import tat_game
        ten = self.tk_chinh.get("nhan_vat") or "acc chính"
        self.in_log(f"{ten}: game không phản hồi, tắt client để mở lại")
        tat_game(pid)

    def _phuc_hoi_diss_acc_chinh(self, loi):
        """Bấm Duyệt lúc cửa sổ còn. Cửa sổ đóng, đã thoát, hoặc treo vài lần thì mở client đăng nhập lại."""
        if "không phản hồi" in str(loi).lower() and self._cua_so_song(self.chinh):
            self._lan_treo = getattr(self, "_lan_treo", 0) + 1
        else:
            self._lan_treo = 0
        if self._cua_so_song(self.chinh):
            self._bam_duyet_mat_ket_noi()
        xl = getattr(self, "_xu_ly_mat_ket_noi", None)
        da_thoat = bool(xl and xl.da_thoat)
        treo_lau = getattr(self, "_lan_treo", 0) >= 3
        if not can_mo_lai_client(loi, self._cua_so_song(self.chinh), da_thoat) and not treo_lau:
            ten = self.tk_chinh.get("nhan_vat") or "acc chính"
            self.in_log(f"{ten}: mất kết nối ({loi}), đã thử Duyệt, rút tiếp")
            self.dung.wait(3)
            return True
        if treo_lau and self._cua_so_song(self.chinh):
            self._tat_client_treo()
        self._lan_treo = 0
        self._mo_lai_acc_chinh()
        return True

    def _rut_tiep(self, ten):
        """Lỗi ở bước rút Thiên Cơ: mở lại và rút phần còn thiếu, không dừng cả phiên."""
        while True:
            self._kiem_tra_dung()
            try:
                self._chuan_bi_manh(ten)
                return
            except ThieuManh:
                raise
            except _Dung:
                raise
            except (LoiGiaoAccChinh, LoiLua, OSError) as loi:
                if not nen_rut_tiep(loi):
                    raise
                if la_loi_diss(loi) and self._phuc_hoi_diss_acc_chinh(loi):
                    continue
                self.in_log(f"{ten}: lỗi rút Thiên Cơ ({loi}), rút tiếp từ Thiên Cơ")
                self.dung.wait(2)

    def _chuan_bi_manh(self, ten):
        """Kiểm tra đủ trước. Thiếu thì không rút. Đủ thì rút phần túi còn thiếu."""
        game = self.chinh
        if not self._mo_tccn(game):
            raise LoiGiaoAccChinh("không mở được Thiên Cơ Cẩm Nang")
        bang = self._liet_ke_vat(game, MA_LIET_KE_TCCN)
        if bang in ("dong", "khong"):
            raise LoiGiaoAccChinh("không liệt kê được Thiên Cơ Cẩm Nang")
        trong_tui = ton_theo_khoa(self._tui(game))
        trong_tccn = ton_tccn(bang)
        self.in_log("Thiên Cơ: " + ", ".join(
            f"{m['ten']} {trong_tccn[m['khoa']]}" for m in MANH)
            + " — túi acc chính: " + ", ".join(f"{m['ten']} {trong_tui[m['khoa']]}" for m in MANH))
        rut, thieu = phan_manh(trong_tui, trong_tccn, self.buoc)
        if thieu:
            game.lua.chay(MA_DONG_CUA_SO)
            raise ThieuManh(thieu)
        can_o = sum(so_o_can(so) for so in rut.values())
        trong = self._o_trong_dao_cu(game)
        if can_o and trong < can_o:
            game.lua.chay(MA_DONG_CUA_SO)
            raise LoiGiaoAccChinh(
                f"túi acc chính còn {trong} ô trống, cần {can_o} ô để rút {self._manh()['ten']} cho {ten}")
        for m in MANH:
            if m["khoa"] != self.buoc:
                continue
            so = rut.get(m["khoa"], 0)
            if so:
                self._rut_loai(m, so)
        game.lua.chay(MA_DONG_CUA_SO)
        if not self._du_manh(game):
            raise LoiGiaoAccChinh(f"đã rút mà túi acc chính chưa đủ {self._manh()['ten']} cho {ten}")

    def _o_dau_tccn(self, khoa):
        """Ô mảnh còn hàng. Đọc hụt (máy ảo, hộp nhập số đang mở) thì đóng/mở lại rồi đọc tiếp."""
        mau = None
        for lan in range(4):
            self._kiem_tra_dung()
            if lan:
                self.dung.wait(0.8)
                try:
                    self.chinh.lua.chay(MA_DONG_CUA_SO)
                except (LoiLua, OSError):
                    pass
                if not self._mo_tccn(self.chinh):
                    continue
            bang = self._liet_ke_vat(self.chinh, MA_LIET_KE_TCCN)
            chon = o_manh_tccn(bang, khoa, SO_RUT_TCCN)
            if chon:
                return chon
            mau = bang
        if isinstance(mau, list) and mau:
            xem = ", ".join(f"ô {o} {ten} x{so}" for o, ten, so in mau[:6])
            ten_manh = next(m["ten"] for m in MANH if m["khoa"] == khoa)
            self.in_log(f"Thiên Cơ còn {len(mau)} ô, không thấy {ten_manh}: {xem}")
        elif mau in ("dong", "khong"):
            self.in_log(f"Thiên Cơ chưa đọc được danh sách ({mau})")
        else:
            self.in_log("Thiên Cơ liệt kê rỗng")
        return None, 0

    def _ton_tccn(self, khoa):
        bang = self._liet_ke_vat(self.chinh, MA_LIET_KE_TCCN)
        if not isinstance(bang, list):
            return None
        tong, thay = 0, False
        for _, ten, so in bang:
            if khoa_tu_ten(ten) != khoa:
                continue
            thay = True
            try:
                n = int(so)
            except (TypeError, ValueError):
                n = 0
            if n > 0:
                tong += n
        if not thay:
            return 0
        # Có ô đúng món mà số đang là 0: chưa đọc được, đừng coi là đã hết.
        return tong or None

    def _rut_loai(self, manh, so):
        """Rút đúng `so` mảnh. Mỗi lần tối đa 250, cách 3 giây. Túi chưa kịp tăng vì lag thì chờ, không dừng."""
        game, da = self.chinh, 0
        while da < so:
            self._kiem_tra_dung()
            o, trong_o = self._o_dau_tccn(manh["khoa"])
            if o is None:
                raise LoiGiaoAccChinh(f"Thiên Cơ hết {manh['ten']} khi còn thiếu {so - da}")
            lan = min(SO_RUT_TCCN, so - da, trong_o)
            truoc = tong_ma(self._tui(game), manh["ma"])
            ton_truoc = self._ton_tccn(manh["khoa"])
            kq = game.lua.chay(ma_rut_tccn(o, lan))
            if kq in (b"dong", b"khong"):
                raise LoiGiaoAccChinh(f"không rút được {manh['ten']} ({kq.decode()})")
            lan_cho = 0
            lan_khong_doi = 0
            while True:
                self._kiem_tra_dung()
                self.dung.wait(GIAY_GIUA_RUT_TCCN)
                sau = self._cho_tui_ma(game, manh["ma"], truoc)
                ton_sau = self._ton_tccn(manh["khoa"])
                quyet = ket_luan_rut(truoc, sau, ton_truoc, ton_sau)
                if quyet == "xong":
                    break
                lan_cho += 1
                if quyet == "cho":
                    lan_khong_doi = 0
                    self.in_log(f"Rút {manh['ten']} server lag, túi chưa kịp tăng, chờ tiếp ({lan_cho})")
                    continue
                lan_khong_doi += 1
                if lan_khong_doi < 3:
                    self.in_log(f"Rút {manh['ten']} túi chưa tăng, chờ thêm ({lan_cho})")
                    continue
                self.in_log(f"Rút {manh['ten']} túi chưa tăng, bấm rút lại (ô {o}, nhập {lan})")
                break
            if sau <= truoc:
                continue
            da += sau - truoc
            self.in_log(f"Rút {sau - truoc} {manh['ten']} (ô {o}, nhập {lan}), túi {truoc + (sau - truoc)}")

    def _cho_tui_ma(self, game, ma, truoc, lan=24):
        sau = tong_ma(self._tui(game), ma)
        for _ in range(lan):
            if sau > truoc:
                return sau
            self.dung.wait(0.15)
            self._kiem_tra_dung()
            sau = tong_ma(self._tui(game), ma)
        return sau

    def _chon_game_truong(self, tk, ten=None):
        """Đúng nhân vật đang trong game thì dùng client đó. Không lấy client của nhân vật khác đang giữ."""
        hwnd_chinh = self.chinh.lua.hwnd
        hwnd_ten = tim_hwnd_theo_nhan_vat(ten, gan_tk=tk.get("ten_dang_nhap")) if ten else None
        if hwnd_ten and hwnd_ten != hwnd_chinh:
            self.ten_giu_online.add(chuan_hoa(ten))
            self._thoat_cac_client(giu=self._cac_hwnd_giu(hwnd_chinh, hwnd_ten))
            return hwnd_ten
        giu_xv = self._hwnd_giu_xoay_vong()
        dang_giu = self._cac_hwnd_giu(hwnd_chinh)
        hwnd = self._hwnd_dll_san(tim_game_cua_tai_khoan(tk["ten_dang_nhap"]))
        if hwnd in giu_xv or hwnd in dang_giu:
            hwnd = None
        cac_cua_so = [c["hwnd"] for c in tim_cua_so_game()
                      if c["hwnd"] != hwnd_chinh and c["hwnd"] not in giu_xv and c["hwnd"] not in dang_giu]
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

    def _vao_phu(self, tk, ten):
        if tim_hwnd_theo_nhan_vat(ten, gan_tk=tk.get("ten_dang_nhap")):
            self.in_log(f"{ten} đang đăng nhập, giữ nguyên")
        else:
            self.in_log(f"{ten}: đăng nhập")
        game = self._dang_nhap(dict(tk, nhan_vat=ten), self._chon_game_truong(tk, ten))
        if game is None:
            raise LoiGiaoAccChinh(f"không đăng nhập được {ten}")
        self.phu = game
        self.ten_phu = ten
        self.hwnd_truong = game.lua.hwnd
        self._cho(lambda: self._doc(game), 60)
        xy = NPC_TRAO_DOI[1]
        for g, ten_g in ((self.chinh, self.tk_chinh.get("nhan_vat") or "acc chính"), (game, ten)):
            self._ve_dai_ly(g, ten_g)
            self._chay_toi(g, ten_g, xy)

    def _giao(self, ten):
        manh = self._manh()
        ma, can = manh["ma"], manh["so"]
        da_bao = False
        while True:
            self._kiem_tra_dung()
            try:
                con = max(0, can - tong_ma(self._tui(self.phu), ma))
            except (LoiLua, OSError):
                self.in_log(f"{ten}: chưa đọc được túi người nhận, chờ rồi giao tiếp")
                self.dung.wait(2)
                continue
            if con <= 0:
                return
            try:
                cac_o = o_can_giao(self._tui(self.chinh), {ma: con})
            except (LoiLua, OSError):
                self.in_log(f"{ten}: chưa đọc được túi acc chính, chờ rồi giao tiếp")
                self.dung.wait(2)
                continue
            if not cac_o:
                self.in_log(f"{ten}: túi chưa thấy đủ {manh['ten']} để giao nốt, chờ rồi giao tiếp")
                self.dung.wait(2)
                continue
            if not da_bao:
                self.in_log(f"Giao {manh['so']} {manh['ten']} cho {ten} "
                            f"({len(cac_o)} ô, {so_lan_giao(len(cac_o))} lần, mỗi lần {SO_O_MOT_LAN} ô)")
                da_bao = True
            try:
                GiaoDich(self.chinh, self.phu, self.tk_chinh.get("nhan_vat") or "acc chính", ten,
                         self.in_log, self.dung.is_set).chuyen(cac_o)
            except (LoiGiaoDich, LoiLua, OSError) as loi:
                ket = ket_luan_giao(loi)
                if ket == "dung":
                    raise _Dung() from loi
                if la_loi_diss(loi):
                    self._phuc_hoi_diss_acc_chinh(loi)
                    continue
                self.in_log(f"{ten}: lỗi giao dịch ({loi})")
                self._chay_lai_gan_acc_chinh(ten)

    def _chay_lai_gan_acc_chinh(self, ten):
        """Acc phụ chạy sát acc chính, rồi vòng giao dịch gọi lại."""
        self.in_log(f"{ten}: chạy lại gần acc chính rồi giao dịch lại")
        chinh, phu = self.chinh, self.phu
        try:
            a, b = self._doc(chinh), self._doc(phu)
            if not a or not b or a.get("map") != b.get("map"):
                xy = NPC_TRAO_DOI[1]
                for g, ten_g in ((chinh, self.tk_chinh.get("nhan_vat") or "acc chính"), (phu, ten)):
                    self._ve_dai_ly(g, ten_g)
                    self._chay_toi(g, ten_g, xy)
                return

            def toi():
                aa, bb = self._doc(chinh), self._doc(phu)
                if not aa or not bb or aa.get("map") != bb.get("map"):
                    return False
                if math.hypot(aa["x"] - bb["x"], aa["y"] - bb["y"]) <= KHOANG_CACH_DUNG_CHO:
                    return True
                phu.lua.chay(f"AutoRunToTarget({int(aa['x']) + 1}, {int(aa['y'])})")
                return False

            if not self._cho(toi, GIAY_CHAY_TOI):
                self.in_log(f"{ten}: chưa chạy sát acc chính, vẫn giao dịch lại")
        except _Dung:
            raise
        except (LoiGiaoAccChinh, LoiLua, OSError) as loi:
            self.in_log(f"{ten}: chạy gần acc chính chưa xong ({loi}), vẫn giao dịch lại")

    def _cua_doi_mo(self, game):
        try:
            return game.lua.chay(f'return tostring(IsWindowShow("{CUA_SO_DOI}"))') == b"true"
        except (LoiLua, OSError):
            return False

    def _mo_menu(self, ten, dong_menu):
        game = self.phu
        while True:
            self._kiem_tra_dung()
            try:
                game.lua.chay(f'if IsWindowShow("{CUA_SO_DOI}") then CloseWindow("{CUA_SO_DOI}", true) end '
                              'if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
            except (LoiLua, OSError):
                pass
            try:
                NhanDoTanThu(game, ten, self.in_log, self.dung.is_set, self.bao_trang_thai)._noi_chuyen(
                    NPC_TRAO_DOI, (DONG_MENU[dong_menu],))
            except DungPhoBan:
                raise _Dung()
            except (LoiPhoBan, LoiLua, OSError) as loi:
                self.in_log(f"{ten}: {loi}, nói chuyện NPC lại")
                self.dung.wait(2)
                continue
            if self._cho(lambda: self._cua_doi_mo(game), GIAY_CHO_CUA_SO):
                return
            self.in_log(f"{ten}: chưa mở được cửa sổ đổi, nói chuyện lại")

    def _co_mon(self, game, ma):
        try:
            return ma in self._cac_ma_co(game)
        except (LoiLua, OSError):
            return False

    def _so_manh_tui(self, game):
        try:
            return tong_ma(self._tui(game), self._manh()["ma"])
        except (LoiLua, OSError):
            return None

    def _xep_roi_mo_doi(self, ten):
        """Đổi không vào túi: tắt cửa sổ đổi, mở túi, bấm Xếp, rồi mở lại giao diện đổi."""
        game = self.phu
        self.in_log(f"{ten}: đổi không được, tắt giao diện đổi, xếp túi rồi mở lại")
        try:
            game.lua.chay(f'if IsWindowShow("{CUA_SO_DOI}") then CloseWindow("{CUA_SO_DOI}", true) end '
                          'if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
        except (LoiLua, OSError) as loi:
            self.in_log(f"{ten}: không đóng được cửa sổ đổi ({loi})")
        self._xep_tui(game, ten)
        self._mo_menu(ten, _BUOC[self.buoc]["dong"])

    def _doi_mot(self, ten, o, ma, ten_mon):
        """Bấm chọn ô rồi OK. Túi chưa kịp có món vì lag thì chờ. Đổi không được thì xếp túi và mở lại."""
        game = self.phu
        lan_bam = 0
        while True:
            self._kiem_tra_dung()
            if self._co_mon(game, ma):
                self.in_log(f"{ten}: đổi được {ten_mon}")
                return True
            if not self._cua_doi_mo(game):
                self._mo_menu(ten, _BUOC[self.buoc]["dong"])
            truoc = self._so_manh_tui(game)
            game.lua.chay(ma_bam_o_doi(CUA_SO_DOI, o))
            self.dung.wait(0.3)
            game.lua.chay(ma_xac_nhan_doi(CUA_SO_DOI))
            lan_bam += 1
            lan_cho = 0
            lan_khong_doi = 0
            while True:
                self._kiem_tra_dung()
                self.dung.wait(2)
                quyet = ket_luan_doi(self._co_mon(game, ma), truoc, self._so_manh_tui(game))
                if quyet == "xong":
                    self.in_log(f"{ten}: đổi được {ten_mon}")
                    return True
                lan_cho += 1
                if quyet == "cho":
                    lan_khong_doi = 0
                    self.in_log(f"{ten}: chọn ô {o} server lag, chưa thấy {ten_mon}, chờ tiếp ({lan_cho})")
                    continue
                lan_khong_doi += 1
                if lan_khong_doi < 6:
                    self.in_log(f"{ten}: chọn ô {o} chưa thấy {ten_mon}, chờ thêm ({lan_cho})")
                    continue
                self.in_log(f"{ten}: chọn ô {o} chưa thấy {ten_mon}, xếp túi rồi đổi lại (lần {lan_bam})")
                self._xep_roi_mo_doi(ten)
                break

    def _doi(self, ten):
        dong = _BUOC[self.buoc]["dong"]
        con = mon_chua_co(self._cac_ma_co(self.phu), self.buoc)
        if not con:
            self.in_log(f"{ten}: đã có đủ món {self._ten_buoc()}")
            return
        for dong in (dong,):
            nhom = [m for m in con if m[0] == dong]
            if not nhom:
                continue
            for _, o, ma, ten_mon in nhom:
                if not self._cua_doi_mo(self.phu):
                    self._mo_menu(ten, dong)
                if not self._doi_mot(ten, o, ma, ten_mon):
                    raise LoiGiaoAccChinh(f"{ten}: không đổi được {ten_mon}")
        try:
            self.phu.lua.chay(MA_DONG_CUA_SO)
            self.phu.lua.chay(f'if IsWindowShow("{CUA_SO_DOI}") then CloseWindow("{CUA_SO_DOI}", true) end')
        except (LoiLua, OSError):
            pass

    def _mang_mot(self, game, ten, ma, ten_mon):
        lan = 0
        while True:
            self._kiem_tra_dung()
            if ma in self._trang_bi(game).values():
                return True
            try:
                tui = self._tui(game)
            except (LoiLua, OSError):
                self.in_log(f"{ten}: chưa đọc được túi để mang {ten_mon}, thử lại")
                self.dung.wait(2)
                continue
            o = next((slot for (loai, slot), (m, _, _) in tui.items() if loai == "base" and m == ma), None)
            if o is None:
                if ma in self._trang_bi(game).values():
                    return True
                self.in_log(f"{ten}: chưa thấy {ten_mon} trong túi, chờ rồi mang lại")
                self.dung.wait(2)
                continue
            try:
                game.lua.chay('if not IsWindowShow("Packet") then OpenWindow("Packet") end')
                game.lua.chay(MA_CHUOT_PHAI.replace("{o}", str(o)))
            except (LoiLua, OSError) as loi:
                self.in_log(f"{ten}: {loi}, mang {ten_mon} lại")
                self.dung.wait(2)
                continue
            het = time.time() + 8
            while time.time() < het:
                self._kiem_tra_dung()
                if ma in self._trang_bi(game).values():
                    self.in_log(f"{ten}: đã mang {ten_mon}")
                    return True
                if dang_hien(game.lua, "MessageBox_Self"):
                    game.lua.chay(trong_cua_so(
                        "MessageBox_Self",
                        'if IsWindowShow("MessageBox_Self") then MessageBox_Self_OK_Clicked() end'))
                self.dung.wait(0.3)
            lan += 1
            self.in_log(f"{ten}: chưa mang được {ten_mon}, mang lại (lần {lan})")

    def _mang_va_vut(self, ten):
        game = self.phu
        truoc = self._trang_bi(game)
        mon = [m for m in MON if m[0] == _BUOC[self.buoc]["dong"]]
        for _, _, ma, ten_mon in mon:
            if ma in truoc.values():
                continue
            self._mang_mot(game, ten, ma, ten_mon)
        sau = self._trang_bi(game)
        thao = ma_vua_thao(truoc, sau) | ma_thao_da_ghi(ten, self.duong_dan)
        danh_dau_thao(ten, thao, self.duong_dan)
        if thao:
            self.in_log(f"{ten}: vứt {len(thao)} món vừa tháo")
            while True:
                self._kiem_tra_dung()
                try:
                    vut_theo_ma(game.lua, ten, thao, self.in_log, self.dung.is_set)
                    break
                except (LoiVutRac, LoiLua, OSError) as loi:
                    self.in_log(f"{ten}: chưa vứt được đồ vừa tháo ({loi}), vứt lại")
                    self.dung.wait(2)
        con = [ten_mon for _, _, ma, ten_mon in mon if ma not in self._trang_bi(game).values()]
        if con:
            self.in_log(f"{ten}: chưa mang {', '.join(con)}, mang lại")
            for _, _, ma, ten_mon in mon:
                if ma not in self._trang_bi(game).values():
                    self._mang_mot(game, ten, ma, ten_mon)
