"""
SỰ KIỆN ÁC TẶC (tab "Phó bản", khung "Sự kiện Ác Tặc", cài riêng từng nhân vật).

Lịch: mỗi ngày 6 khung, mỗi khung 1 giờ (KHUNG_GIO). Trong khung giờ, nhân vật bật Ác Tặc bỏ dở PMP / Sát Tinh (kể
cả đang ở trong phó bản), về Đại Lý rồi lần lượt đi các map đã chọn, tuần tra theo điểm như "Phụ Bản Tùy Chọn"
[ACTAC] / [ACTACKIEUCU] của GAuto: tới điểm, thấy Ác Tặc thì đánh, dọn xong đi điểm sau. Một vòng tuần tra không
thấy con nào thì map đó coi như hết: về Đại Lý, sang map tiếp theo. 3 phút liên tục không thấy NPC/quái cũng
đổi sang map kế theo thứ tự đã chọn. Đi hết các map hoặc hết giờ thì về Đại Lý,
luồng nhân vật quay lại PMP / Sát Tinh như cũ.

Đường đi: từ Đại Lý, NPC "Di Chuyển" (165, 156); đang đứng sẵn ở Lạc Dương / Tô Châu mà map nằm sau thành đó thì đi thẳng
ra cổng, không về Đại Lý:
    Vô Lượng Sơn, Kiếm Các : Bản Đồ Luyện Cấp ở NPC Di Chuyển Đại Lý (dò dòng theo tên map).
    Tây Hồ, Thái Hồ        : Bản Đồ Thành Thị (111116, 8888) -> Tô Châu (111116, 1002), rồi chạy tới cổng map.
    Đôn Hoàng, Tung Sơn    : Bản Đồ Thành Thị (111116, 8888) -> Lạc Dương (111116, 1001), rồi chạy tới cổng map.
Cổng map lấy từ "Tiên Nhân Chỉ Lộ" của game (DataPool:GetAutoSearch, loại 99 "Vận chuyển"): chạy tới tọa độ cổng như
khi nhấp đúp dòng "Bản đồ: ..." (AutoRunToTarget + SetAutoRunTargetNPCName). Ghi tay được trong cau_hinh.json,
khóa "ac_tac_map" (xem tests/AC_TAC.md): {"Tung Sơn": {"cong": [x, y]} hoặc {"buoc": [[script, extra], ...],
"npc": {"ten": "...", "xy": [x, y]}}, "diem": [[x, y, lên_ngựa, theo_đội], ...]}.

Tổ đội: đội trưởng (người đầu nhóm trong game) dẫn đường và tuần tra. Đội viên trong auto đã bật Ác Tặc: Theo đội khi
đội trưởng mời, bỏ theo để đánh trong vùng đội trưởng ghi, bị bỏ lại thì tự đi tới map đội trưởng đang tuần tra.
"""
import random
import re
import threading
import time
from collections import namedtuple
from datetime import datetime, timedelta

import cau_hinh
from auto_chuyen_sinh import chuan_hoa
from bang_ma_viscii import giai_ma
from chien_dau import KY_NANG_VE_THANH, khoang_cach, ma_dung_ky_nang_theo_dinh_nghia
from dang_nhap import bo_dau, chuoi_lua
from lua_game import LoiLua
from pho_ban_pmp import (GIAY_CHO_BO_THEO, GIAY_CHO_DOI_MAP, GIAY_CHO_QUAI_XUAT_HIEN, GIAY_CHO_VE_THANH,
                         GIAY_GIUA_HAI_LAN_TRIEU_TAP, GIAY_MO_HOI_THOAI, GIAY_SAU_CON_CUOI, GIAY_TOI_DA_CHO_THEO,
                         KHOANG_CACH_LEN_THU, KHOANG_TOI_DIEM, MA_BO_THEO_DOI, MA_DANG_CUOI,
                         MA_DANG_THEO_DOI, MA_THEO_DOI, MAP_DAI_LY, MAP_LAC_DUONG, SO_LAN_THU,
                         LoiPhoBan, PhoBanPMP, _doc_dang_theo_doi, _Dung, bo_theo_doi, chuan_bi_ve_thanh,
                         dong_y_theo_doi_popup, la_dai_ly, xuong_thu)

MO_TA = "Ác Tặc"
KHUNG_GIO = (2, 13, 15, 17, 19, 21)
KHUNG_SANG = 2
PHUT_DI_TRUOC = 2
PHUT_KHUNG_MAC_DINH = 30
MAP_TO_CHAU = "Tô Châu"
CAC_MAP = tuple(cau_hinh.CAC_MAP_AC_TAC)
HUB_CUA_MAP = {"Vô Lượng Sơn": None, "Kiếm Các": None, "Tây Hồ": MAP_TO_CHAU, "Thái Hồ": MAP_TO_CHAU,
               "Đôn Hoàng": MAP_LAC_DUONG, "Tung Sơn": MAP_LAC_DUONG}
# Cổng map trong thành trung chuyển (Tiên Nhân Chỉ Lộ: Lạc Dương scene 0, Tô Châu scene 1).
CONG_TOI_MAP = {"Tây Hồ": (182, 287), "Thái Hồ": (181, 33), "Đôn Hoàng": (33, 130), "Tung Sơn": (159, 287)}
NPC_DI_CHUYEN = "Di Chuyển"
XY_DI_CHUYEN_DAI_LY = (165, 156)
BUOC_THANH_THI = (111116, 8888)
BUOC_TOI_HUB = {MAP_LAC_DUONG: (BUOC_THANH_THI, (111116, 1001)), MAP_TO_CHAU: (BUOC_THANH_THI, (111116, 1002))}
# Menu con của NPC Di Chuyển nên thử trước khi tìm dòng tới map dã ngoại; menu "Phụ Bản" không có map dã ngoại.
UU_TIEN_MENU = ("luyen cap", "da ngoai")
BO_QUA_MENU = ("phu ban",)

# (x, y, lên ngựa, gọi theo đội) — "Phụ Bản Tùy Chọn" của GAuto (pathpoints.txt).
ROUTE_MOI = ((98, 78, 1, 1), (108, 35, 0, 0), (98, 17, 1, 1), (56, 23, 0, 0), (40, 18, 0, 0), (28, 23, 1, 1),
             (41, 80, 0, 0), (23, 98, 0, 0), (21, 105, 0, 0))
ROUTE_CU = ((98, 78, 0, 0), (105, 54, 0, 0), (105, 24, 0, 0), (79, 22, 0, 0), (55, 22, 0, 0), (24, 23, 1, 1),
            (42, 40, 0, 0), (41, 71, 0, 0), (40, 86, 0, 0), (23, 98, 0, 0), (21, 105, 1, 1))

KHOANG_PHAT_HIEN = 30
BAN_KINH_DANH = 12
# Ác Tặc chạy quanh: tâm vùng đánh lệch quá chừng này so với con gần nhất thì dời theo.
KHOANG_DOI_TAM = 5
GIAY_DANH_NHOM_TOI_DA = 180
GIAY_TOI_DA_MOT_DIEM = 60
GIAY_KET_O_DIEM = 6
GIAY_CHO_HIEN_QUAI = 1.5
SO_VONG_TUAN_TRA_TOI_DA = 6
SO_LAN_ROI_MAP = 3
GIAY_NGHI_KHI_LOI = 60
GIAY_CHO_DOI_VIEN_VE = 40
GIAY_TOI_DA_MOI_THEO = 10
GIAY_GIUA_HAI_LAN_MOI_THEO = 3
# Đội viên cùng map mà đứng xa đội trưởng (không theo đội) thì tự chạy tới.
KHOANG_GAN_TRUONG = 10
GIAY_GIUA_HAI_LAN_CHAY = 3
GIAY_GIUA_HAI_LAN_DI_RIENG = 30
GIAY_GIUA_HAI_LAN_VE_THANH = 5
# Chọn dòng dịch chuyển xong mà chừng này giây chưa đổi map: hội thoại có thể đang hỏi xác nhận.
GIAY_CHO_XAC_NHAN = 3
# Tên map đổi trước khi cảnh mới nạp xong: chờ thêm rồi mới chạy / dùng kỹ năng.
GIAY_SAU_DOI_MAP = 3
GIAY_CHO_KY_NANG = 8
# Chạy bộ tới cổng map: tối đa chừng này giây; đứng yên quá GIAY_KET_O_DIEM thì bấm chạy lại.
GIAY_TOI_DA_TOI_CONG = 120
# GAuto cboxChoParty: đội trưởng chờ đồng đội trong auto tới gần rồi mới đi điểm kế.
GIAY_CHO_DONG_DOI_GAN = 90
GIAY_TIM_NPC_KHONG_CO = 180  # 3 phút không thấy NPC/quái Ác Tặc → sang map tiếp theo (map_uu_tien)

MA_DONG_HOI_THOAI = 'if IsWindowShow("Quest") then CloseWindow("Quest", true) end'

Chang = namedtuple("Chang", "map_tu ten_npc xy cac_buoc map_toi")


class _HetKhung(Exception):
    """Hết khung giờ Ác Tặc."""


class _RoiMap(Exception):
    """Đang tuần tra mà nhân vật không còn ở map Ác Tặc (chết về thành, bị kéo đi...)."""


class _HetTimNpc(Exception):
    """Hết thời gian tìm NPC/quái Ác Tặc trên map hiện tại — đổi sang map kế trong danh sách."""

    def __init__(self, ten_map):
        self.ten_map = ten_map


class LoiAcTac(LoiPhoBan):
    pass


class _Chet(LoiPhoBan):
    """Nhân vật chết: thôi lượt này, luồng nhân vật tự Đầu thai rồi đi tiếp (không tính map lỗi)."""


# ---------- cài đặt / lịch ----------

def cai_dat_ac_tac(cai_dat_nhan_vat=None):
    """Cài Ác Tặc chung (mac_dinh): chỉ đội trưởng trong game chạy; đội viên theo đội."""
    gia_tri = dict(cau_hinh.MAC_DINH_AC_TAC)
    gia_tri.update(cau_hinh.mac_dinh().get("ac_tac") or {})
    return gia_tri


def cac_khung(at):
    return tuple(gio for gio in KHUNG_GIO if not (gio == KHUNG_SANG and at.get("bo_khung_02h")))


def phut_khung(at):
    """Số phút đi Ác Tặc mỗi khung, tính từ giờ bắt đầu (ô «phút GAuto»)."""
    try:
        p = int(at.get("phut_gauto") or PHUT_KHUNG_MAC_DINH)
    except (TypeError, ValueError):
        p = PHUT_KHUNG_MAC_DINH
    return max(1, min(p, 120))


def khung_hien_tai(at, bay_gio=None):
    """
    (ngày, giờ bắt đầu) của khung Ác Tặc đang chạy, None nếu ngoài giờ. Khung 21h chạy từ 20:58 (ra map trước
    PHUT_DI_TRUOC phút) tới 21:00 + phut_khung (vd 21:20).
    """
    bay_gio = bay_gio or datetime.now()
    sau = (bay_gio + timedelta(minutes=PHUT_DI_TRUOC)).replace(minute=0, second=0, microsecond=0)
    for bat_dau in (sau, sau - timedelta(hours=1), sau - timedelta(hours=2)):
        if bat_dau.hour in cac_khung(at) and bay_gio < bat_dau + timedelta(minutes=phut_khung(at)):
            return bat_dau.date().isoformat(), bat_dau.hour
    return None


def dang_khung_ac_tac(at, bay_gio=None):
    return khung_hien_tai(at, bay_gio) is not None


def luc_bat_dau_khung(khung):
    """Thời điểm (time.time()) giờ bắt đầu khung (vd 21:00) — lúc bật GAuto."""
    ngay, gio = khung
    return (datetime.fromisoformat(ngay) + timedelta(hours=gio)).timestamp()


def luc_het_khung(khung, at=None):
    """Thời điểm (time.time()) kết thúc khung: giờ bắt đầu + phut_khung (vd 21:20)."""
    return luc_bat_dau_khung(khung) + phut_khung(at or {}) * 60


def mo_ta_khung(khung, at=None):
    bat_dau = datetime.fromtimestamp(luc_bat_dau_khung(khung))
    return f"{bat_dau:%H:%M}-{datetime.fromtimestamp(luc_het_khung(khung, at)):%H:%M}"


def mo_ta_lich(at):
    p = phut_khung(at)
    return ", ".join(f"{g:02d}:00-{(datetime(2000, 1, 1, g) + timedelta(minutes=p)):%H:%M}" for g in cac_khung(at))


# Mỗi khung chỉ một nhóm (trưởng nhóm nhận khung đầu tiên) đi Ác Tặc; nhóm khác login vào giữa khung thì không đi.
_NHAN_KHUNG = {}
_KHOA_NHAN_KHUNG = threading.Lock()


def nhan_khung(khung, ten_truong):
    """Trưởng nhóm ten_truong nhận đi khung này. False nếu nhóm khác đã nhận."""
    with _KHOA_NHAN_KHUNG:
        da = _NHAN_KHUNG.setdefault(tuple(khung), ten_truong)
    return chuan_hoa(da) == chuan_hoa(ten_truong)


def nguoi_nhan_khung(khung):
    with _KHOA_NHAN_KHUNG:
        return _NHAN_KHUNG.get(tuple(khung))


# ---------- map / đường đi ----------

def cung_ten_map(a, b):
    return bool(a) and bool(b) and bo_dau(a) == bo_dau(b)


def ten_map_chuan(ten_map):
    """Tên map Ác Tặc như trong CAC_MAP (gõ không dấu / khác hoa thường vẫn nhận), None nếu không phải map Ác Tặc."""
    return next((m for m in CAC_MAP if cung_ten_map(m, ten_map)), None)


def la_map_ac_tac(ten_map):
    return ten_map_chuan(ten_map) is not None


# GAuto gặp Ác Tặc, khiêu chiến xong thì cả đội vào phó bản riêng này (tên khác map dã ngoại).
CAC_MAP_PHO_BAN_AC_TAC = ("Tặc Khấu doanh địa",)


def la_pho_ban_ac_tac(ten_map):
    return any(cung_ten_map(m, ten_map) for m in CAC_MAP_PHO_BAN_AC_TAC)


def nen_bao_roi_map_ac_tac(map_hien, map_tuan_tra):
    """
    Đang tuần tra map_tuan_tra: chỉ coi là «rời map» khi về thành / hub hoặc nhảy sang map Ác Tặc khác.
    Map ải sau NPC khiêu chiến (tên khác map dã ngoại) không báo rời — tránh tự Về thành Đại Lý.
    """
    if not map_hien or cung_ten_map(map_hien, map_tuan_tra):
        return False
    if o_thanh_trung_chuyen_ac_tac(map_hien) or la_dai_ly(map_hien):
        return True
    return la_map_ac_tac(map_hien)


def o_thanh_trung_chuyen_ac_tac(ten_map):
    """Đại Lý / Lạc Dương / Tô Châu — chỉ từ đây mới tự về thành rồi đi NPC (đội viên bị bỏ ở thành)."""
    b = bo_dau(ten_map or "")
    return b in {bo_dau(MAP_DAI_LY), bo_dau(MAP_LAC_DUONG), bo_dau(MAP_TO_CHAU)}


def cac_map_da_chon(at):
    """Các map đã chọn theo thứ tự đi (bỏ tên lạ, bỏ trùng)."""
    ds = []
    for ten in at.get("map_uu_tien") or ():
        chuan = ten_map_chuan(ten)
        if chuan and chuan not in ds:
            ds.append(chuan)
    return ds


def map_tiep_theo(at, bo_qua=()):
    """Map đầu tiên trong danh sách đã chọn chưa nằm trong bo_qua (đã hết Ác Tặc / lỗi), None nếu không còn."""
    bo = {bo_dau(m) for m in bo_qua}
    return next((m for m in cac_map_da_chon(at) if bo_dau(m) not in bo), None)


def hub_cua_map(ten_map):
    """Thành trung chuyển trước khi ra map Ác Tặc (Lạc Dương: Tung Sơn / Đôn Hoàng), None nếu đi từ Đại Lý."""
    chuan = ten_map_chuan(ten_map)
    return HUB_CUA_MAP.get(chuan) if chuan else None


def tuy_chinh_map():
    """Đường đi / điểm tuần tra ghi tay trong cau_hinh.json (khóa "ac_tac_map")."""
    return cau_hinh.chung().get("ac_tac_map") or {}


def _tuy_chinh_cua(ten_map, tuy_chinh):
    return next((v for k, v in (tuy_chinh or {}).items() if cung_ten_map(k, ten_map)), None) or {}


def chuoi_buoc_toi(ten_map, tuy_chinh=None):
    """Các chặng từ Đại Lý tới ten_map: [Chang(map_tu, NPC, tọa độ NPC hoặc None, dòng chọn hoặc None, map_toi)]."""
    chuan = ten_map_chuan(ten_map)
    if chuan is None:
        raise LoiAcTac(f"{ten_map} không phải map Ác Tặc")
    tc = _tuy_chinh_cua(chuan, tuy_chinh)
    hub = HUB_CUA_MAP[chuan]
    chang = []
    tu = MAP_DAI_LY
    if hub:
        chang.append(Chang(MAP_DAI_LY, NPC_DI_CHUYEN, XY_DI_CHUYEN_DAI_LY, BUOC_TOI_HUB[hub], hub))
        tu = hub
    npc = tc.get("npc") or {}
    cac_buoc = tuple(tuple(int(v) for v in b) for b in tc.get("buoc") or ()) or None
    cong = tc.get("cong") or (None if npc or cac_buoc else CONG_TOI_MAP.get(chuan))
    if cong:
        # ten_npc None: chạy bộ qua cổng map tại xy.
        chang.append(Chang(tu, None, (int(cong[0]), int(cong[1])), None, chuan))
        return chang
    xy = tuple(npc["xy"]) if npc.get("xy") else (XY_DI_CHUYEN_DAI_LY if tu == MAP_DAI_LY else None)
    chang.append(Chang(tu, npc.get("ten") or NPC_DI_CHUYEN, xy, cac_buoc, chuan))
    return chang


def diem_tuan_tra(ten_map, at, tuy_chinh=None):
    """Các điểm tuần tra của map: ghi tay trong "ac_tac_map" nếu có, không thì route GAuto đã chọn."""
    diem = _tuy_chinh_cua(ten_map, tuy_chinh).get("diem")
    if diem:
        return tuple((int(d[0]), int(d[1]), int(d[2]) if len(d) > 2 else 0, int(d[3]) if len(d) > 3 else 0)
                     for d in diem)
    return ROUTE_CU if at.get("route") == "cu" else ROUTE_MOI


def tim_dong_toi_map(cac_dong, ten_map):
    """(script, extra) của dòng hội thoại (loại id) có tên ten_map, None nếu không có."""
    khoa = bo_dau(ten_map)
    for loai, s, e, chu in cac_dong:
        if loai == "id" and khoa in bo_dau(chu):
            return s, e
    return None


def cac_dong_menu_con(cac_dong):
    """Các dòng "Bản Đồ ..." (mở danh sách map, không dịch chuyển ngay) nên thử, Luyện Cấp / Dã Ngoại trước."""
    menu = []
    for loai, s, e, chu in cac_dong:
        b = bo_dau(chu)
        if loai != "id" or "ban do" not in b or any(k in b for k in BO_QUA_MENU):
            continue
        hang = next((i for i, k in enumerate(UU_TIEN_MENU) if k in b), len(UU_TIEN_MENU))
        menu.append((hang, s, e, chu))
    return [(s, e, chu) for _, s, e, chu in sorted(menu, key=lambda m: m[0])]


def cac_mau_ten(at):
    """Tên quái Ác Tặc (không dấu) để khớp, từ ô "Tên quái" (cách nhau dấu phẩy)."""
    return [bo_dau(t) for t in (at.get("ten_quai") or "").split(",") if bo_dau(t)]


def khop_ten_ac_tac(ten, cac_mau):
    """Tên có chứa một mẫu đứng riêng thành chữ ("Ác Tặc" khớp "ác tặc đầu lĩnh" nhưng không khớp "Hắc Tặc")."""
    b = bo_dau(ten)
    return any(re.search(rf"(?<!\w){re.escape(m)}(?!\w)", b) for m in cac_mau)


def la_npc_khieu_chien_ac_tac(ten_chuan, ten_npc_cfg=None):
    """NPC cần mở hội thoại khiêu chiến (vd. Ác Tặc Tạo Phản), không đánh trực tiếp như quái."""
    b = bo_dau(ten_chuan)
    if ten_npc_cfg and bo_dau(ten_npc_cfg) in b:
        return True
    return "tao phan" in b and "ac tac" in b


def dong_khieu_chien_ac_tac(cac_dong):
    """(script, extra) của dòng khiêu chiến trong Quest, None nếu chỉ có Tạm biệt."""
    uu_tien = []
    for loai, s, e, chu in cac_dong:
        if loai != "id" or not chu:
            continue
        b = bo_dau(chu)
        if "tam biet" in b and len(b) < 24:
            continue
        hang = 9
        if "khieu chien" in b:
            hang = 0
        elif "chang le" in b and ("so" in b or "nguoi" in b or "ta" in b):
            hang = 1
        elif "chang le" in b:
            hang = 2
        uu_tien.append((hang, s, e, chu))
    if not uu_tien:
        return None
    uu_tien.sort(key=lambda x: x[0])
    _, s, e, _ = uu_tien[0]
    return (s, e)


# ---------- tổ đội ----------

class DoiAcTac:
    """Đội đi Ác Tặc: đội trưởng ghi vị trí / vùng đánh / map đang tới, luồng của đội viên đọc."""

    def __init__(self, truong, cac_doi_vien=None, doc_lai=None):
        self.truong = truong
        self.cac_doi_vien = dict(cac_doi_vien or {})
        self.doc_lai = doc_lai
        self.vung = None
        self.map_vung = None
        self.quai_danh = ()
        self.vi_tri = None      # (x, y, map) của đội trưởng
        self.map_dich = None    # map Ác Tặc đội trưởng đang tới / đang tuần tra

    def lam_moi(self):
        moi = self.doc_lai() if self.doc_lai else None
        if moi is None or list(moi) == list(self.cac_doi_vien):
            return False
        self.cac_doi_vien = moi
        return True

    def map_doi_vien(self):
        kq = {}
        for ten, luong in self.cac_doi_vien.items():
            try:
                tt = luong.game.thong_tin()
                kq[ten] = tt["map"] if tt else luong.map_hien_tai
            except (LoiLua, OSError, AttributeError):
                kq[ten] = luong.map_hien_tai
        return kq

    def chua_theo(self):
        return [ten for ten, luong in self.cac_doi_vien.items() if not _doc_dang_theo_doi(luong)]

    def can_trieu_tap(self, game_truong):
        """Đội viên chưa Theo đội — cần triệu tập (giống DoiPMP / GAuto «pt theo sau»)."""
        try:
            tt_tr = game_truong.thong_tin()
        except LoiLua:
            return []
        if not tt_tr:
            return []
        can = []
        for ten, luong in self.cac_doi_vien.items():
            if _doc_dang_theo_doi(luong):
                luong.trieu_tap_den = None
                continue
            can.append((ten, luong))
        return can

    def gui_trieu_tap(self, game_truong, het_han, in_log, ten_truong, luc_bao):
        can = self.can_trieu_tap(game_truong)
        if not can:
            return
        try:
            tt_tr = game_truong.thong_tin()
        except LoiLua:
            return
        if not tt_tr:
            return
        xy = (tt_tr["x"], tt_tr["y"])
        map_tr = tt_tr["map"]
        khoa_tr = chuan_hoa(map_tr)
        ten_ds = []
        for ten, luong in can:
            try:
                tt = luong.game.thong_tin()
            except (LoiLua, OSError, AttributeError):
                continue
            if not tt or chuan_hoa(tt["map"]) != khoa_tr:
                continue
            luong.trieu_tap_den = (xy[0], xy[1], map_tr, het_han)
            ten_ds.append(ten)
        if not ten_ds:
            return
        bay_gio = time.time()
        if bay_gio - luc_bao.get("luc", 0) >= GIAY_GIUA_HAI_LAN_TRIEU_TAP:
            luc_bao["luc"] = bay_gio
            in_log(f"{ten_truong}: {MO_TA} triệu tập {', '.join(ten_ds)} tới ({int(xy[0])}, {int(xy[1])}) [{map_tr}]")

    def dat_vung(self, vung, quai=(), ten_map=None):
        # Ghi tên quái trước vùng (và xóa vùng trước tên) để luồng chiến đấu không đánh nhầm quái thường.
        if vung:
            self.quai_danh = tuple(quai)
            self.map_vung = ten_map
            self.vung = vung
        else:
            self.vung = None
            self.quai_danh = ()

    def vung_cho(self, ten_map):
        vung = self.vung
        return vung if vung and cung_ten_map(self.map_vung, ten_map) else None


def buoc_doi_vien(game, doi, tt, state, bay_gio=None, at=None):
    """
    Một bước của đội viên (gọi lặp từ luồng đội viên, không chặn). Trả về ("mo_ta", chữ) hoặc ("di", map) khi phải tự
    đi tới map đội trưởng đang tuần tra (luồng đội viên tự chạy AcTacRunner.di_rieng).
    """
    bay_gio = bay_gio or time.time()
    dong_y_theo_doi_popup(game)
    map_dv = tt["map"]
    vt = doi.vi_tri
    if not vt:
        if doi.map_dich and at and cung_ten_map(map_dv, doi.map_dich) \
                and bay_gio - state.get("luc_chay", 0) >= GIAY_GIUA_HAI_LAN_CHAY:
            diem = diem_tuan_tra(doi.map_dich, at, tuy_chinh_map())
            if diem:
                state["luc_chay"] = bay_gio
                game.lua.chay(f"AutoRunToTarget({int(diem[0][0])}, {int(diem[0][1])})")
                return "mo_ta", f"tự chạy tuần tra {doi.map_dich} (chờ tín hiệu {doi.truong})"
        return "mo_ta", f"chờ đội trưởng {doi.truong}"
    try:
        dang_theo = game.lua.chay(MA_DANG_THEO_DOI) == b"1"
    except LoiLua:
        dang_theo = False
    if cung_ten_map(map_dv, vt[2]):
        if doi.vung_cho(map_dv):
            if dang_theo and bay_gio - state.get("luc_bo_theo", 0) >= GIAY_GIUA_HAI_LAN_CHAY:
                state["luc_bo_theo"] = bay_gio
                game.lua.chay(MA_BO_THEO_DOI)
            return "mo_ta", f"đánh Ác Tặc cùng {doi.truong}"
        if not dang_theo and khoang_cach((tt["x"], tt["y"]), vt[:2]) > KHOANG_GAN_TRUONG \
                and bay_gio - state.get("luc_chay", 0) >= GIAY_GIUA_HAI_LAN_CHAY:
            state["luc_chay"] = bay_gio
            game.lua.chay(f"AutoRunToTarget({int(vt[0])}, {int(vt[1])})")
            return "mo_ta", f"chạy tới đội trưởng {doi.truong}"
        return "mo_ta", f"theo đội trưởng {doi.truong}"
    if dang_theo:
        return "mo_ta", f"theo đội trưởng {doi.truong} sang [{vt[2]}]"
    if vt and not cung_ten_map(map_dv, vt[2]) and not o_thanh_trung_chuyen_ac_tac(map_dv):
        if bay_gio - state.get("luc_moi_theo", 0) >= GIAY_GIUA_HAI_LAN_MOI_THEO:
            state["luc_moi_theo"] = bay_gio
            game.lua.chay(MA_THEO_DOI)
        if la_map_ac_tac(map_dv) or (doi.map_dich and la_map_ac_tac(doi.map_dich)):
            return "mo_ta", f"mời theo đội trưởng sang [{vt[2]}] (không tự về {MAP_DAI_LY})"
    if doi.map_dich and cung_ten_map(vt[2], doi.map_dich) and not cung_ten_map(map_dv, doi.map_dich):
        if o_thanh_trung_chuyen_ac_tac(map_dv):
            if bay_gio - state.get("luc_di_rieng", 0) >= GIAY_GIUA_HAI_LAN_DI_RIENG:
                state["luc_di_rieng"] = bay_gio
                return "di", doi.map_dich
            return "mo_ta", f"chờ thử lại đường tới {doi.map_dich}"
        if bay_gio - state.get("luc_moi_theo", 0) >= GIAY_GIUA_HAI_LAN_MOI_THEO:
            state["luc_moi_theo"] = bay_gio
            game.lua.chay(MA_THEO_DOI)
        return "mo_ta", f"mời theo đội trưởng vào {doi.map_dich} (đang ở [{map_dv}])"
    return "mo_ta", f"chờ đội trưởng {doi.truong} ([{vt[2]}])"


def ve_thanh_neu_o_map_ac_tac(game, tt, state, in_log, ten):
    """Hết khung / đội trưởng thôi đi Ác Tặc mà đội viên còn ở map Ác Tặc: dùng kỹ năng về Đại Lý (cách nhau vài giây)."""
    if not tt or not la_map_ac_tac(tt["map"]):
        return False
    bay_gio = time.time()
    if bay_gio - state.get("luc_ve_thanh", 0) < GIAY_GIUA_HAI_LAN_VE_THANH:
        return True
    state["luc_ve_thanh"] = bay_gio
    in_log(f"{ten}: {MO_TA} — xong, về {MAP_DAI_LY}")
    chuan_bi_ve_thanh(game, in_log, ten)
    game.lua.chay(ma_dung_ky_nang_theo_dinh_nghia(KY_NANG_VE_THANH))
    return True


# ---------- luồng đi Ác Tặc ----------

class AcTacRunner(PhoBanPMP):
    """Đi Ác Tặc trong khung giờ (đội trưởng / một mình), hoặc tự đi tới map đội trưởng (đội viên bị bỏ lại)."""

    # (map đi, map tới) -> các dòng đã chọn được (dò theo chữ), dùng chung mọi cửa sổ game.
    duong_da_tim = {}

    def __init__(self, game, in_log):
        super().__init__(game, in_log)
        self.che_do = "ac_tac"
        self.ten = None
        self.trang_thai = {}
        self.nen_dung = lambda: False
        self.doi_at = None
        self.la_truong = False
        self.khung = None
        self.khung_xong = None
        self.map_da_het = set()
        self.map_loi = {}
        self.lan_roi_map = {}
        self.da_bo_qua = set()
        self.het_khung = float("inf")
        self.dang_ket_thuc = False
        self.dat_vung_rieng = lambda vung: None
        self._luc_gap_ac_tac = 0.0
        self._trieu_at_state = {}
        self.gauto_khung = None
        self.gauto_het_luc = 0.0
        self.gauto_loi_cuoi = None
        self.gauto_chi_so = None
        self.gauto_dong_cache = {}

    # ---------- trạng thái ----------

    def can_chen(self, at, bay_gio=None):
        """Đang trong khung Ác Tặc chưa đi xong: bỏ PMP / Sát Tinh để đi Ác Tặc."""
        khung = khung_hien_tai(at, bay_gio)
        return khung is not None and khung != self.khung_xong

    def _kiem_tra(self):
        if self.nen_dung():
            raise _Dung()
        if not self.dang_ket_thuc and time.time() >= self.het_khung:
            raise _HetKhung()

    def _tt(self):
        try:
            tt = self.game.thong_tin()
        except LoiLua:
            return None
        if tt and tt["hp"] <= 0 < tt["hp_toi_da"]:
            raise _Chet("nhân vật đã chết")
        if tt and self.la_truong and self.doi_at is not None:
            self.doi_at.vi_tri = (tt["x"], tt["y"], tt["map"])
        return tt

    def _mo_ta(self, chu):
        self.trang_thai["mo_ta"] = f"{MO_TA}: {chu}"

    def _log(self, chu):
        self.in_log(f"{self.ten}: {MO_TA} — {chu}")

    def _bat_dau_tim_tren_map(self):
        self._luc_gap_ac_tac = time.time()

    def _ghi_gap_ac_tac(self):
        self._luc_gap_ac_tac = time.time()

    def _kiem_tra_het_thoi_gian_tim(self, ten_map):
        if time.time() - self._luc_gap_ac_tac >= GIAY_TIM_NPC_KHONG_CO:
            raise _HetTimNpc(ten_map)

    def _bat_dau(self, ten, cai_dat_nhan_vat, trang_thai, nen_dung):
        self.ten, self.trang_thai, self.nen_dung = ten, trang_thai, nen_dung
        self.doi = None
        self.thong_bao = []
        self.dang_ket_thuc = False
        at = cai_dat_ac_tac()
        khung = khung_hien_tai(at)
        if khung is None:
            return None, None
        if khung != self.khung:
            self.khung = khung
            self.map_da_het, self.map_loi, self.lan_roi_map = set(), {}, {}
            self.da_bo_qua = set()
        self.het_khung = luc_het_khung(khung, at)
        self.het_han_vong = self.het_khung + 600
        return at, khung

    # ---------- về thành / tổ đội ----------

    def _ve_thanh_at(self):
        if la_dai_ly(self._map()):
            self._hoi_mau_dai_ly_neu_can()
            return
        self._dat_vung(None)
        self._mo_ta(f"về {MAP_DAI_LY}")
        map_dau = self._map()
        for _ in range(SO_LAN_THU):
            chuan_bi_ve_thanh(self.game, self.in_log, self.ten)
            # Vừa sang map, bảng kỹ năng có thể chưa nạp xong: thử lại vài giây rồi mới coi là không có kỹ năng.
            if not self._cho(lambda: self.game.lua.chay(ma_dung_ky_nang_theo_dinh_nghia(KY_NANG_VE_THANH)),
                             GIAY_CHO_KY_NANG, buoc=1):
                raise LoiAcTac("nhân vật không có kỹ năng Quay về Đại Lý thành")
            moi = self._cho(lambda: (lambda m: m if m and m != map_dau else None)(self._map()), GIAY_CHO_VE_THANH)
            if moi:
                if not la_dai_ly(moi):
                    raise LoiAcTac(f"kỹ năng Về thành đưa tới [{moi}], không phải {MAP_DAI_LY}")
                time.sleep(GIAY_SAU_DOI_MAP)
                self._log(f"đã về {MAP_DAI_LY}")
                self._hoi_mau_dai_ly_neu_can()
                return
        raise LoiAcTac(f"dùng kỹ năng Về thành {SO_LAN_THU} lần mà vẫn chưa về {MAP_DAI_LY}")

    def _goi_doi_vien_ve_thanh(self, bat_buoc=False):
        """Bấm kỹ năng Về thành cho các đội viên trong auto đang ở map khác Đại Lý (không chờ)."""
        if not self.doi_at:
            return []
        self.doi_at.lam_moi()
        map_truong = self._map()
        chua = []
        for ten, m in self.doi_at.map_doi_vien().items():
            if la_dai_ly(m):
                continue
            if not bat_buoc and map_truong and cung_ten_map(m, map_truong):
                continue
            chua.append(ten)
        for ten in chua:
            luong = self.doi_at.cac_doi_vien.get(ten)
            if luong is not None and luong.game:
                self._thu_ve_thanh_mot(luong.game, ten)
        return chua

    def _gom_doi_dai_ly(self):
        """Đội trưởng ở Đại Lý: gọi đội viên về Đại Lý, chờ một lúc, rồi mời Theo đội để NPC đưa cả đội đi."""
        if not self.doi_at or not self.doi_at.cac_doi_vien:
            return
        chua = self._goi_doi_vien_ve_thanh(bat_buoc=True)
        het_han = time.time() + GIAY_CHO_DOI_VIEN_VE
        luc_goi = time.time()
        while chua and time.time() < het_han:
            self._kiem_tra()
            self._mo_ta(f"chờ {', '.join(chua)} về {MAP_DAI_LY}")
            time.sleep(1)
            if time.time() - luc_goi >= GIAY_GIUA_HAI_LAN_VE_THANH:
                luc_goi = time.time()
                chua = self._goi_doi_vien_ve_thanh(bat_buoc=True)
            else:
                chua = [ten for ten, m in self.doi_at.map_doi_vien().items() if not la_dai_ly(m)]
        if chua:
            self._log(f"{', '.join(chua)} chưa về {MAP_DAI_LY}, vẫn đi (đội viên tự tới sau)")
        xy = self._vi_tri()
        self._goi_party_theo(xy or (0, 0), True, cho=True)

    def _gom_doi_tai_cho(self):
        """Đội trưởng đứng sẵn ở thành trung chuyển của map (vd Lạc Dương đi Tung Sơn): triệu tập đội viên tại chỗ."""
        if not self.doi_at or not self.doi_at.cac_doi_vien:
            return
        self.doi_at.lam_moi()
        map_truong = self._map()
        khac = [ten for ten, m in self.doi_at.map_doi_vien().items() if not cung_ten_map(m, map_truong)]
        if khac:
            self._log(f"{', '.join(khac)} không ở [{map_truong}], tự tới sau")
        self._moi_theo_doi(cho=True)

    def _len_thu_neu_xa(self, xy):
        tt = self._tt()
        if not tt or self._lua_dung(MA_DANG_CUOI) or not self._co_thu():
            return False
        if khoang_cach((tt["x"], tt["y"]), xy) <= KHOANG_CACH_LEN_THU:
            return False
        if self._len_thu():
            time.sleep(0.35)
            return True
        self._log("không lên được thú, chạy bộ")
        return False

    def _goi_party_theo(self, xy, goi_theo, cho=False):
        """
        GAuto pathpoints cột «pt theo sau»: lên thú nếu xa, bấm Theo đội, triệu tập đội viên chưa theo (như PMP).
        """
        if not self.la_truong or not self.doi_at or not self.doi_at.cac_doi_vien:
            return
        if not goi_theo:
            if cho:
                self._moi_theo_doi(cho=True)
            return
        self._len_thu_neu_xa(xy)
        self.game.lua.chay(MA_THEO_DOI)
        self.doi_at.gui_trieu_tap(self.game, time.time() + GIAY_TOI_DA_CHO_THEO, self.in_log, self.ten,
                                  self._trieu_at_state)
        if not cho:
            return
        het_han = time.time() + GIAY_TOI_DA_MOI_THEO
        luc_bam = time.time()
        while self.doi_at.chua_theo() and time.time() < het_han:
            self._kiem_tra()
            if time.time() - luc_bam >= GIAY_GIUA_HAI_LAN_MOI_THEO:
                luc_bam = time.time()
                self.game.lua.chay(MA_THEO_DOI)
                self.doi_at.gui_trieu_tap(self.game, time.time() + GIAY_TOI_DA_CHO_THEO, self.in_log, self.ten,
                                          self._trieu_at_state)
            time.sleep(0.5)

    def _moi_theo_doi(self, cho=False):
        if not self.doi_at or not self.doi_at.cac_doi_vien:
            return
        xy = self._vi_tri() or (0, 0)
        self._goi_party_theo(xy, True, cho=cho)

    # ---------- dịch chuyển ----------

    def _dong_hoi_thoai(self):
        try:
            self.game.lua.chay(MA_DONG_HOI_THOAI)
        except LoiLua:
            pass

    def _mo_npc(self, ten_npc, xy):
        """Mở hội thoại NPC; xy None: NPC phải thấy được quanh chỗ đang đứng. Trả về các dòng hội thoại."""
        self._dong_hoi_thoai()
        if xy is None:
            khoa = bo_dau(ten_npc)
            tt = self._tt()
            cac = [d for ten, d in self._quanh() if bo_dau(ten) == khoa]
            if not cac or not tt:
                gan = sorted({ten for ten, _ in self._quanh()})[:12]
                raise LoiAcTac(f"không thấy NPC {ten_npc} quanh ({tt and tt['x']}, {tt and tt['y']}) "
                               f"[{tt and tt['map']}] — NPC gần: {', '.join(gan) or 'không có'}; "
                               "ghi tọa độ NPC trong ac_tac_map (tests/AC_TAC.md)")
            npc = min(cac, key=lambda d: khoang_cach((tt["x"], tt["y"]), (d.x, d.y)))
            xy = (int(npc.x), int(npc.y))
        self._mo_hoi_thoai(ten_npc, xy, (-1, -1), bo_qua_neu_khong_co=True, dan_doi=False, giu_theo=True)
        ht = self._cho(self._hoi_thoai, GIAY_MO_HOI_THOAI)
        if not ht:
            raise LoiAcTac(f"không mở được hội thoại {ten_npc}")
        return ht[1]

    def _cho_dong(self, dong):
        """Chờ hội thoại có dòng (script, extra) rồi chọn."""
        if not self._cho(lambda: (lambda ht: ht and any((s, e) == tuple(dong) for _, s, e, _ in ht[1]))(
                self._hoi_thoai()), GIAY_MO_HOI_THOAI):
            raise LoiAcTac(f"hội thoại không có dòng {dong}")
        self._chon(dong)

    def _cho_dong_moi(self, cu):
        """Chờ hội thoại đổi sang danh sách khác cu (sau khi chọn menu con), trả về các dòng mới hoặc None."""
        ht = self._cho(lambda: (lambda h: h if h and h[1] != cu else None)(self._hoi_thoai()), GIAY_MO_HOI_THOAI)
        return ht[1] if ht else None

    def _do_duong(self, chang, cac_dong):
        """Chưa biết dòng tới map: tìm theo tên trong hội thoại, không có thì thử các menu "Bản Đồ ..."."""
        dong = tim_dong_toi_map(cac_dong, chang.map_toi)
        if dong:
            self._chon(dong)
            return [dong]
        menu = cac_dong_menu_con(cac_dong)
        da_xem = []
        for i, (s, e, chu) in enumerate(menu):
            if i:
                cac_dong = self._mo_npc(chang.ten_npc, chang.xy)
            self._chon((s, e))
            moi = self._cho_dong_moi(cac_dong)
            if moi:
                dong = tim_dong_toi_map(moi, chang.map_toi)
                if dong:
                    self._chon(dong)
                    return [(s, e), dong]
                da_xem.append(bo_dau(chu))
        self._dong_hoi_thoai()
        ds = "; ".join(bo_dau(c[3]) for c in cac_dong if c[3])
        raise LoiAcTac(f"NPC {chang.ten_npc} ở {chang.map_tu} không có dòng tới {chang.map_toi} "
                       f"(hội thoại: {ds}; đã xem menu: {', '.join(da_xem) or 'không có'})")

    def _cho_sang_map(self, map_tu, map_toi):
        """Chờ đổi map sau khi chọn dòng dịch chuyển; hội thoại hỏi xác nhận thì chọn dòng có tên map."""
        da_xac_nhan = False
        luc_chon = time.time()

        def da_doi():
            nonlocal da_xac_nhan
            m = self._map()
            if m and not cung_ten_map(m, map_tu):
                return m
            if not da_xac_nhan and time.time() - luc_chon >= GIAY_CHO_XAC_NHAN:
                ht = self._hoi_thoai()
                dong = tim_dong_toi_map(ht[1], map_toi) if ht else None
                if dong is None and ht:
                    dong = next(((s, e) for loai, s, e, chu in ht[1] if loai == "id"
                                 and any(k in bo_dau(chu) for k in ("dong y", "xac nhan"))), None)
                if dong:
                    da_xac_nhan = True
                    self._chon(dong)
            return None
        return self._cho(da_doi, GIAY_CHO_DOI_MAP)

    def _qua_cong(self, chang):
        """Chạy bộ tới cổng map chang.xy (như nhấp đúp "Bản đồ: ..." ở Tiên Nhân Chỉ Lộ) tới khi sang map khác."""
        x, y = chang.xy
        ma_chay = f"AutoRunToTarget({x}, {y}) SetAutoRunTargetNPCName({chuoi_lua('Bản đồ: ' + chang.map_toi)})"
        self._dong_hoi_thoai()
        if not self._lua_dung(MA_DANG_CUOI) and self._co_thu():
            self._len_thu()
        if self.la_truong:
            self._moi_theo_doi()
        self.game.lua.chay(ma_chay)
        het_han = time.time() + GIAY_TOI_DA_TOI_CONG
        vi_tri_cu, luc_di = None, time.time()
        while time.time() < het_han:
            self._kiem_tra()
            tt = self._tt()
            if tt and not cung_ten_map(tt["map"], chang.map_tu):
                return tt["map"]
            if tt:
                vi_tri = (tt["x"], tt["y"])
                if vi_tri_cu is None or khoang_cach(vi_tri, vi_tri_cu) >= 1:
                    vi_tri_cu, luc_di = vi_tri, time.time()
                elif time.time() - luc_di >= GIAY_KET_O_DIEM:
                    self.game.lua.chay(ma_chay)
                    luc_di = time.time()
            time.sleep(0.5)
        return None

    def _qua_chang(self, chang):
        khoa = (bo_dau(chang.map_tu), bo_dau(chang.map_toi))
        if chang.ten_npc is None:
            for lan in range(1, SO_LAN_THU + 1):
                self._mo_ta(f"chạy tới cổng {chang.map_toi} ({chang.xy[0]}, {chang.xy[1]}) ở {chang.map_tu}")
                moi = self._qua_cong(chang)
                if moi and cung_ten_map(moi, chang.map_toi):
                    time.sleep(GIAY_SAU_DOI_MAP)
                    return
                if moi:
                    raise LoiAcTac(f"cổng ({chang.xy[0]}, {chang.xy[1]}) ở {chang.map_tu} đưa tới [{moi}], "
                                   f"không phải {chang.map_toi}")
                self._log(f"chạy {GIAY_TOI_DA_TOI_CONG} giây chưa qua cổng {chang.map_toi} (lần {lan}/{SO_LAN_THU})")
            raise LoiAcTac(f"không qua được cổng {chang.map_toi} ở {chang.map_tu}")
        loi_cuoi = None
        for lan in range(1, SO_LAN_THU + 1):
            self._mo_ta(f"{chang.ten_npc} ({chang.map_tu}) → {chang.map_toi}")
            if self.la_truong:
                self._moi_theo_doi()
            try:
                cac_dong = self._mo_npc(chang.ten_npc, chang.xy)
                cac_buoc = chang.cac_buoc or self.duong_da_tim.get(khoa)
                if cac_buoc:
                    for i, dong in enumerate(cac_buoc):
                        if i:
                            self._cho_dong(dong)
                        else:
                            self._chon(dong)
                        time.sleep(0.5)
                else:
                    cac_buoc = self._do_duong(chang, cac_dong)
                moi = self._cho_sang_map(chang.map_tu, chang.map_toi)
            except _Chet:
                raise
            except LoiPhoBan as loi:
                loi_cuoi = LoiAcTac(str(loi))
                self._log(f"{loi} (lần {lan}/{SO_LAN_THU})")
                self._dong_hoi_thoai()
                continue
            if moi and cung_ten_map(moi, chang.map_toi):
                time.sleep(GIAY_SAU_DOI_MAP)
                if not chang.cac_buoc and khoa not in self.duong_da_tim:
                    self.duong_da_tim[khoa] = tuple(cac_buoc)
                    self._log(f"tìm được đường {chang.map_tu} → {chang.map_toi}: {list(cac_buoc)}")
                return
            if moi:
                raise LoiAcTac(f"NPC {chang.ten_npc} đưa tới [{moi}], không phải {chang.map_toi}")
            self.duong_da_tim.pop(khoa, None)
            loi_cuoi = LoiAcTac(f"chọn đường {list(cac_buoc)} mà chưa sang {chang.map_toi}")
            self._log(f"{loi_cuoi} (lần {lan}/{SO_LAN_THU})")
        raise loi_cuoi or LoiAcTac(f"không đi được {chang.map_tu} → {chang.map_toi}")

    def _di_toi_map(self, ten_map, ve_thanh_truoc=True, gom_doi=False):
        """Đi tới ten_map; mặc định về Đại Lý + gom đội (đội trưởng). Đội viên đang ở map dã ngoại không về thành."""
        if cung_ten_map(self._map(), ten_map):
            if self.la_truong and self.doi_at is not None:
                self.doi_at.map_dich = ten_map
            return
        if self.la_truong and self.doi_at is not None:
            self.doi_at.map_dich = ten_map
        hub = hub_cua_map(ten_map)
        o_hub = bool(hub) and cung_ten_map(self._map(), hub)
        if o_hub and (ve_thanh_truoc or gom_doi):
            self._log(f"đang ở {hub}, đi thẳng {ten_map} (không về {MAP_DAI_LY})")
        elif ve_thanh_truoc:
            self._ve_thanh_at()
        if gom_doi and self.la_truong:
            if o_hub:
                self._gom_doi_tai_cho()
            else:
                self._gom_doi_dai_ly()
        for chang in chuoi_buoc_toi(ten_map, tuy_chinh_map()):
            m = self._map()
            if cung_ten_map(m, chang.map_toi):
                continue
            if not cung_ten_map(m, chang.map_tu):
                raise LoiAcTac(f"đang ở [{m}], không phải {chang.map_tu} để đi {chang.map_toi}")
            self._qua_chang(chang)
        self._log(f"đã tới {ten_map}")

    # ---------- tuần tra / đánh ----------

    def _dat_vung(self, vung, quai=()):
        if self.doi_at is not None:
            self.doi_at.dat_vung(vung, quai, (self.doi_at.vi_tri or (0, 0, None))[2])
        self.dat_vung_rieng(vung)

    def _ac_tac_quanh(self, cac_mau, tam=None, ban_kinh=KHOANG_PHAT_HIEN, ten_npc_cfg=None):
        kq = []
        for ten, d in self._quanh():
            if d.hp <= 0 or d.id in self.da_bo_qua or not khop_ten_ac_tac(ten, cac_mau):
                continue
            if la_npc_khieu_chien_ac_tac(ten, ten_npc_cfg):
                continue
            if tam is not None and khoang_cach(tam, (d.x, d.y)) > ban_kinh:
                continue
            kq.append((ten, d))
        return kq

    def _npc_khieu_chien_gan(self, cac_mau, at, tam=None, ban_kinh=KHOANG_PHAT_HIEN):
        """NPC Ác Tặc cần chọn khiêu chiến trước khi ra quái."""
        ten_npc_cfg = (at.get("ten_npc") or "").strip()
        khoa_cfg = bo_dau(ten_npc_cfg) if ten_npc_cfg else ""
        gan = None
        gan_kc = None
        for ten, d in self._quanh():
            if d.hp <= 0 or d.id in self.da_bo_qua:
                continue
            if not la_npc_khieu_chien_ac_tac(ten, ten_npc_cfg) and not (
                    khoa_cfg and khoa_cfg in bo_dau(ten)):
                continue
            kc = khoang_cach(tam, (d.x, d.y)) if tam else 0
            if tam is not None and kc > ban_kinh:
                continue
            if gan is None or kc < gan_kc:
                gan, gan_kc = d, kc
        if gan is None:
            return None
        return giai_ma(gan.ten), gan

    def _chon_khieu_chien_hoi_thoai(self, at):
        ht = self._hoi_thoai()
        if not ht:
            return False
        goi = (at.get("dong_khieu") or "chẳng lẽ").strip()
        dong = dong_khieu_chien_ac_tac(ht[1])
        if dong is None and goi:
            for _, s, e, chu in ht[1]:
                if goi in chuan_hoa(chu):
                    dong = (s, e)
                    break
        if dong is None:
            return False
        self._chon(dong)
        return True

    def _lap_chon_khieu_chien_ac_tac(self, at, het_han=None):
        """Chọn lần lượt các dòng hội thoại (khiêu chiến / chẳng lẽ…) cho tới khi hội thoại đóng hoặc hết giờ."""
        het_han = het_han or time.time() + GIAY_CHO_XAC_NHAN + 22
        goi = (at.get("dong_khieu") or "chẳng lẽ").strip()
        while time.time() < het_han:
            self._kiem_tra()
            if self._chon_khieu_chien_hoi_thoai(at):
                return True
            ht = self._hoi_thoai()
            if not ht:
                return True
            dong = dong_khieu_chien_ac_tac(ht[1])
            if dong is not None:
                self._chon(dong)
                time.sleep(0.45)
                continue
            if goi:
                for _, s, e, chu in ht[1]:
                    if goi in chuan_hoa(chu):
                        self._chon((s, e))
                        time.sleep(0.45)
                        break
                else:
                    ds = [c[3] for c in ht[1] if c[3]]
                    self._log(f"hội thoại NPC, chưa có dòng «{goi}»: {'; '.join(ds[:5])}")
                    return False
                continue
            ds = [c[3] for c in ht[1] if c[3]]
            self._log(f"hội thoại NPC không chọn được dòng: {'; '.join(ds[:5])}")
            return False
        self._log("hết thời gian chọn dòng khiêu chiến NPC")
        return False

    def _thu_khieu_chien_npc(self, cac_mau, ten_map, at):
        """
        Mở NPC Ác Tặc / chọn dòng khiêu chiến rồi đánh. Trả về True nếu đã xử lý một nhóm.
        """
        ten_npc_cfg = (at.get("ten_npc") or "").strip()
        vi_tri = self._vi_tri()
        if self._chon_khieu_chien_hoi_thoai(at):
            self._ghi_gap_ac_tac()
            self._log("đã chọn khiêu chiến (hội thoại đang mở)")
            time.sleep(GIAY_CHO_BO_THEO + GIAY_CHO_QUAI_XUAT_HIEN)
            return self._danh_nhom(cac_mau, ten_map, at)
        npc = self._npc_khieu_chien_gan(cac_mau, at, vi_tri)
        if npc is None:
            return False
        self._ghi_gap_ac_tac()
        ten_hien, ent = npc
        goi = (at.get("dong_khieu") or "chẳng lẽ").strip()
        if self._lua_dung(MA_DANG_CUOI):
            xuong_thu(self.game)
        xy = (int(ent.x), int(ent.y))
        dong_mo = (goi,) if goi else ("khiêu chiến",)
        if not self._mo_hoi_thoai(ten_hien, xy, dong_mo, bo_qua_neu_khong_co=True, dan_doi=False, giu_theo=True):
            return False
        if not self._lap_chon_khieu_chien_ac_tac(at):
            return False
        self._log(f"{ten_hien} ({xy[0]}, {xy[1]}): đã chọn khiêu chiến")
        time.sleep(GIAY_CHO_BO_THEO + GIAY_CHO_QUAI_XUAT_HIEN)
        return self._danh_nhom(cac_mau, ten_map, at)

    def _vi_tri(self):
        tt = self._tt()
        return (tt["x"], tt["y"]) if tt else None

    def _dam_bao_dung_map(self, ten_map):
        m = self._map()
        if nen_bao_roi_map_ac_tac(m, ten_map):
            raise _RoiMap(m)

    def _danh_nhom(self, cac_mau, ten_map, at=None):
        """Đánh các Ác Tặc quanh mình tới khi không còn con nào. Trả về True nếu đã đánh."""
        ten_npc_cfg = (at or {}).get("ten_npc") if at else None
        bo_theo_doi(self.game)
        if self._lua_dung(MA_DANG_CUOI):
            xuong_thu(self.game)
        bat_dau = time.time()
        luc_het = None
        tam = None
        cac_ten = set()
        da_danh = False
        con = []
        try:
            while True:
                self._kiem_tra()
                self._dam_bao_dung_map(ten_map)
                bay_gio = time.time()
                vi_tri = self._vi_tri()
                con = self._ac_tac_quanh(cac_mau, vi_tri, ten_npc_cfg=ten_npc_cfg) if vi_tri else []
                if not con:
                    luc_het = luc_het or bay_gio
                    if bay_gio - luc_het >= GIAY_SAU_CON_CUOI:
                        return da_danh
                else:
                    luc_het = None
                    da_danh = True
                    self._ghi_gap_ac_tac()
                    cac_ten |= {ten for ten, _ in con}
                    gan = min((d for _, d in con), key=lambda d: khoang_cach(vi_tri, (d.x, d.y)))
                    if tam is None or khoang_cach(tam, (gan.x, gan.y)) > KHOANG_DOI_TAM:
                        tam = (int(gan.x), int(gan.y))
                        self._dat_vung((*tam, BAN_KINH_DANH), cac_ten)
                    self._mo_ta(f"{ten_map}: đánh {len(con)} Ác Tặc")
                if bay_gio - bat_dau >= GIAY_DANH_NHOM_TOI_DA:
                    self.da_bo_qua |= {d.id for _, d in con}
                    self._log(f"đánh {GIAY_DANH_NHOM_TOI_DA} giây chưa xong {len(con)} con, bỏ qua")
                    return da_danh
                time.sleep(0.4)
        finally:
            self._dat_vung(None)

    def _cho_dong_doi_gan(self, at):
        """GAuto «Đợi đồng đội đến gần mới đi tiếp được» (cboxChoParty)."""
        if not at.get("cho_party", True) or not self.la_truong or not self.doi_at or not self.doi_at.cac_doi_vien:
            return
        het_han = time.time() + GIAY_CHO_DONG_DOI_GAN

        def chua_gan():
            vt = self._vi_tri()
            map_hien = self._map()
            if not vt or not map_hien:
                return ["?"]
            chua = []
            for ten, luong in self.doi_at.cac_doi_vien.items():
                try:
                    tt = luong.game.thong_tin()
                except (LoiLua, OSError, AttributeError):
                    chua.append(ten)
                    continue
                if not tt or not cung_ten_map(tt["map"], map_hien):
                    chua.append(ten)
                elif khoang_cach(vt, (tt["x"], tt["y"])) > KHOANG_GAN_TRUONG:
                    chua.append(ten)
            return chua

        chua = chua_gan()
        if not chua:
            return
        self._log(f"chờ đồng đội tới gần: {', '.join(chua)}")
        while chua and time.time() < het_han:
            self._kiem_tra()
            self._mo_ta(f"chờ đồng đội ({', '.join(chua)})")
            if self.la_truong:
                self._moi_theo_doi()
            time.sleep(0.5)
            chua = chua_gan()
        if chua:
            self._log(f"đồng đội chưa tới hết ({', '.join(chua)}), vẫn đi tiếp")

    def _ban_kinh_tim(self, at):
        return KHOANG_PHAT_HIEN * (2 if at.get("tu_tim", True) else 1)

    def _chay_toi_diem(self, diem, cac_mau, ten_map, at, goi_theo=False, len_ngua_truoc=False):
        """Chạy tới diem; gặp Ác Tặc dọc đường thì dừng lại đánh. Trả về số nhóm đã đánh."""
        self._cho_dong_doi_gan(at)
        so_nhom = 0
        ten_npc_cfg = at.get("ten_npc")
        ban_tim = self._ban_kinh_tim(at)
        ma_chay = f"AutoRunToTarget({diem[0]}, {diem[1]})"
        if len_ngua_truoc and not self._lua_dung(MA_DANG_CUOI) and self._co_thu():
            self._len_thu()
            time.sleep(0.35)
        else:
            self._len_thu_neu_xa(diem)
        self._goi_party_theo(diem, goi_theo)
        self.game.lua.chay(ma_chay)
        het_han = time.time() + GIAY_TOI_DA_MOT_DIEM
        vi_tri_cu, luc_di = self._vi_tri(), time.time()
        lan_ket = 0
        while True:
            self._kiem_tra()
            self._kiem_tra_het_thoi_gian_tim(ten_map)
            self._dam_bao_dung_map(ten_map)
            vi_tri = self._vi_tri()
            bay_gio = time.time()
            if vi_tri and self._thu_khieu_chien_npc(cac_mau, ten_map, at):
                so_nhom += 1
                self._goi_party_theo(vi_tri, goi_theo)
                self.game.lua.chay(ma_chay)
                het_han = time.time() + GIAY_TOI_DA_MOT_DIEM
                vi_tri_cu, luc_di = self._vi_tri(), time.time()
                lan_ket = 0
                continue
            if vi_tri and self._ac_tac_quanh(cac_mau, vi_tri, ban_kinh=ban_tim, ten_npc_cfg=ten_npc_cfg):
                self._ghi_gap_ac_tac()
                so_nhom += self._danh_nhom(cac_mau, ten_map, at)
                vt = self._vi_tri()
                self._goi_party_theo(vt or diem, goi_theo)
                self.game.lua.chay(ma_chay)
                het_han = time.time() + GIAY_TOI_DA_MOT_DIEM
                vi_tri_cu, luc_di = self._vi_tri(), time.time()
                lan_ket = 0
                continue
            if vi_tri:
                if khoang_cach(vi_tri, diem) <= KHOANG_TOI_DIEM:
                    return so_nhom
                if vi_tri_cu is None or khoang_cach(vi_tri, vi_tri_cu) >= 1:
                    vi_tri_cu, luc_di = vi_tri, bay_gio
                    lan_ket = 0
                elif bay_gio - luc_di >= GIAY_KET_O_DIEM:
                    lan_ket += 1
                    if lan_ket >= 3:
                        return so_nhom
                    self._goi_party_theo(vi_tri, goi_theo)
                    self.game.lua.chay(ma_chay)
                    luc_di = bay_gio
            if bay_gio >= het_han:
                return so_nhom
            time.sleep(0.3)

    def _sau_diem(self, len_ngua, goi_theo):
        if len_ngua and not self._lua_dung(MA_DANG_CUOI) and self._co_thu():
            self._len_thu()
            time.sleep(0.35)
        vt = self._vi_tri()
        self._goi_party_theo(vt or (0, 0), goi_theo, cho=bool(goi_theo))

    def _tim_tren_map(self, ten_map, at):
        """GAuto tắt «Chạy pathpoints», bật «Chạy tìm»: lượt quét lỏng quanh các điểm mẫu ACTAC, không bám thứ tự cố định."""
        cac_diem = list(diem_tuan_tra(ten_map, at, tuy_chinh_map()))
        cac_mau = cac_mau_ten(at)
        if not cac_mau:
            raise LoiAcTac("chưa nhập tên quái Ác Tặc")
        if not cac_diem:
            raise LoiAcTac(f"chưa có điểm tuần tra cho {ten_map}")
        self._bat_dau_tim_tren_map()
        bo_theo_doi(self.game)
        self._dong_hoi_thoai()
        if self.la_truong and self.doi_at is not None:
            self.doi_at.map_dich = ten_map
            if self.doi_at.cac_doi_vien:
                self._moi_theo_doi(cho=True)
        self._log(f"chạy tìm {ten_map} ({len(cac_diem)} mốc, tên quái: {at.get('ten_quai', '')})")
        ban_tim = self._ban_kinh_tim(at)
        len_ngua_truoc = goi_theo_truoc = False
        for vong in range(1, SO_VONG_TUAN_TRA_TOI_DA + 1):
            so_nhom = 0
            thu_tu = list(cac_diem)
            random.shuffle(thu_tu)
            for i, (x, y, len_ngua, goi_theo) in enumerate(thu_tu, 1):
                self._kiem_tra_het_thoi_gian_tim(ten_map)
                dx, dy = x + random.randint(-12, 12), y + random.randint(-12, 12)
                self._mo_ta(f"{ten_map}: tìm vòng {vong}, mốc {i}/{len(thu_tu)} ({dx}, {dy})")
                so_nhom += self._chay_toi_diem((dx, dy), cac_mau, ten_map, at,
                                               goi_theo=goi_theo_truoc, len_ngua_truoc=len_ngua_truoc)
                time.sleep(GIAY_CHO_HIEN_QUAI)
                vi_tri = self._vi_tri()
                if vi_tri and self._thu_khieu_chien_npc(cac_mau, ten_map, at):
                    so_nhom += 1
                elif vi_tri and self._ac_tac_quanh(cac_mau, vi_tri, ban_kinh=ban_tim, ten_npc_cfg=at.get("ten_npc")):
                    self._ghi_gap_ac_tac()
                    so_nhom += self._danh_nhom(cac_mau, ten_map, at)
                self._sau_diem(len_ngua, goi_theo)
                len_ngua_truoc, goi_theo_truoc = len_ngua, goi_theo
            if not so_nhom:
                return
            self._log(f"{ten_map} vòng tìm {vong}: đánh {so_nhom} nhóm, quét lại")
            len_ngua_truoc = goi_theo_truoc = False

    def _tuan_tra(self, ten_map, at):
        """Đi hết các điểm, đánh Ác Tặc gặp được; lặp tới khi một vòng không gặp con nào (map đã hết)."""
        if not at.get("chay_pathpoints", False):
            return self._tim_tren_map(ten_map, at)
        cac_diem = diem_tuan_tra(ten_map, at, tuy_chinh_map())
        cac_mau = cac_mau_ten(at)
        if not cac_mau:
            raise LoiAcTac("chưa nhập tên quái Ác Tặc")
        self._bat_dau_tim_tren_map()
        bo_theo_doi(self.game)
        self._dong_hoi_thoai()
        if self.la_truong and self.doi_at is not None:
            self.doi_at.map_dich = ten_map
            if self.doi_at.cac_doi_vien:
                self._moi_theo_doi(cho=True)
        ban_tim = self._ban_kinh_tim(at)
        self._log(f"tuần tra {ten_map} ({len(cac_diem)} điểm, tên quái: {at.get('ten_quai', '')})")
        len_ngua_truoc = goi_theo_truoc = False
        for vong in range(1, SO_VONG_TUAN_TRA_TOI_DA + 1):
            so_nhom = 0
            for i, (x, y, len_ngua, goi_theo) in enumerate(cac_diem, 1):
                self._kiem_tra_het_thoi_gian_tim(ten_map)
                self._mo_ta(f"{ten_map}: vòng {vong}, điểm {i}/{len(cac_diem)} ({x}, {y})")
                so_nhom += self._chay_toi_diem((x, y), cac_mau, ten_map, at,
                                               goi_theo=goi_theo_truoc, len_ngua_truoc=len_ngua_truoc)
                time.sleep(GIAY_CHO_HIEN_QUAI)
                vi_tri = self._vi_tri()
                if vi_tri and self._thu_khieu_chien_npc(cac_mau, ten_map, at):
                    so_nhom += 1
                elif vi_tri and self._ac_tac_quanh(cac_mau, vi_tri, ban_kinh=ban_tim, ten_npc_cfg=at.get("ten_npc")):
                    self._ghi_gap_ac_tac()
                    so_nhom += self._danh_nhom(cac_mau, ten_map, at)
                self._sau_diem(len_ngua, goi_theo)
                len_ngua_truoc, goi_theo_truoc = len_ngua, goi_theo
            if not so_nhom:
                return
            self._log(f"{ten_map} vòng {vong}: đánh {so_nhom} nhóm, tuần tra lại")
            len_ngua_truoc = goi_theo_truoc = False

    # ---------- một khung giờ ----------

    def di_den_map_gauto(self, ten, cai_dat_nhan_vat, trang_thai, nen_dung, ten_map, doi_at=None):
        """Chỉ di chuyển tới map Ác Tặc (NPC / cổng), không tuần tra — dùng trước khi bật GAuto."""
        at, khung = self._bat_dau(ten, cai_dat_nhan_vat, trang_thai, nen_dung)
        if khung is None or not ten_map:
            return
        if nen_dung():
            return
        self.doi_at, self.la_truong = doi_at, True
        bo_theo_doi(self.game)
        self._dong_hoi_thoai()
        try:
            self._di_toi_map(ten_map, ve_thanh_truoc=True, gom_doi=True)
        except _Dung:
            pass
        except _Chet:
            self._log("nhân vật chết khi đi tới map")
        except LoiPhoBan as loi:
            self.nghi_den = time.time() + GIAY_NGHI_KHI_LOI
            self._log(f"đi {ten_map}: {loi}. Nghỉ {GIAY_NGHI_KHI_LOI} giây rồi thử lại")
        finally:
            if doi_at is not None:
                doi_at.map_dich = ten_map
            self.doi_at, self.la_truong = None, False

    def chay(self, ten, cai_dat_nhan_vat, trang_thai, nen_dung, dat_vung_danh, doi_at=None):
        """
        Đi Ác Tặc tới khi hết khung giờ / đi hết các map / bị tắt (chặn tới lúc đó). doi_at: DoiAcTac khi nhân vật
        này dẫn các đội viên trong auto (không có đội viên thì vẫn truyền để ghi vùng đánh cho luồng chiến đấu).
        """
        at, khung = self._bat_dau(ten, cai_dat_nhan_vat, trang_thai, nen_dung)
        if khung is None:
            return
        if nen_dung():
            return
        if time.time() < self.nghi_den:
            self._log(f"nghỉ sau lỗi, thử lại sau {int(self.nghi_den - time.time())} giây")
            return
        self.doi_at, self.la_truong = doi_at, True
        bo_theo_doi(self.game)
        self._dong_hoi_thoai()
        self.dat_vung_rieng = dat_vung_danh
        if not self.map_da_het and not self.map_loi:
            self._log(f"khung {mo_ta_khung(khung, at)}, đi: {', '.join(cac_map_da_chon(at)) or '(chưa chọn map)'}")
        try:
            self._doc_thong_bao()
            while True:
                self._kiem_tra()
                ten_map = map_tiep_theo(at, self.map_da_het | set(self.map_loi))
                if ten_map is None:
                    self.khung_xong = khung
                    self._log(f"đã đi hết các map khung {mo_ta_khung(khung, at)}, quay lại PMP / Sát Tinh")
                    self.dang_ket_thuc = True
                    self._ve_thanh_at()
                    self._goi_doi_vien_ve_thanh()
                    return
                try:
                    self._di_toi_map(ten_map, ve_thanh_truoc=True, gom_doi=True)
                    self._tuan_tra(ten_map, at)
                    self.map_da_het.add(ten_map)
                    self._log(f"{ten_map} hết Ác Tặc")
                except _HetTimNpc as het_tim:
                    ten_map = het_tim.ten_map
                    self._log(f"{ten_map}: {GIAY_TIM_NPC_KHONG_CO // 60} phút không thấy NPC/quái, đổi map kế")
                    self.map_da_het.add(ten_map)
                except _RoiMap as roi:
                    lan = self.lan_roi_map.get(ten_map, 0) + 1
                    self.lan_roi_map[ten_map] = lan
                    self._log(f"rời {ten_map} (đang ở [{roi}]) lần {lan}/{SO_LAN_ROI_MAP}")
                    if lan >= SO_LAN_ROI_MAP:
                        self.map_loi[ten_map] = f"rời map {lan} lần"
                except _Chet:
                    raise
                except LoiPhoBan as loi:
                    self.map_loi[ten_map] = str(loi)
                    self._log(f"bỏ qua {ten_map}: {loi}")
                self._ve_thanh_at()
        except _HetKhung:
            self._log(f"hết giờ khung {mo_ta_khung(khung, at)}, về {MAP_DAI_LY}")
            self.khung_xong = khung
            self.dang_ket_thuc = True
            try:
                self._ve_thanh_at()
            except LoiPhoBan as loi:
                self._log(f"chưa về được {MAP_DAI_LY}: {loi}")
            self._goi_doi_vien_ve_thanh()
        except _Dung:
            pass
        except _Chet:
            self._log("nhân vật chết, Đầu thai rồi đi tiếp")
        except LoiPhoBan as loi:
            self.nghi_den = time.time() + GIAY_NGHI_KHI_LOI
            self._log(f"lỗi: {loi}. Nghỉ {GIAY_NGHI_KHI_LOI} giây rồi thử lại")
        finally:
            self._dat_vung(None)
            if doi_at is not None:
                doi_at.map_dich = None
            self.doi_at, self.la_truong = None, False
            self.dat_vung_rieng = lambda vung: None
            self.dang_ket_thuc = False
            trang_thai["mo_ta"] = ""

    def di_rieng(self, ten, cai_dat_nhan_vat, trang_thai, nen_dung, ten_map):
        """Đội viên bị bỏ lại ở thành: về Đại Lý rồi đi NPC. Đang ở map Ác Tặc thì không tự về thành (theo đội trưởng)."""
        _, khung = self._bat_dau(ten, cai_dat_nhan_vat, trang_thai, nen_dung)
        if khung is None or nen_dung():
            return
        self.doi_at, self.la_truong = None, False
        tt = self._tt()
        map_hien = (tt or {}).get("map")
        ve_truoc = o_thanh_trung_chuyen_ac_tac(map_hien)
        self._log(f"tự đi tới {ten_map} theo đội trưởng"
                  + ("" if ve_truoc else f" (giữ [{map_hien}], không về {MAP_DAI_LY})"))
        try:
            self._di_toi_map(ten_map, ve_thanh_truoc=ve_truoc, gom_doi=False)
        except (_HetKhung, _Dung, _RoiMap, _Chet):
            pass
        except LoiPhoBan as loi:
            self._log(f"tự đi tới {ten_map} lỗi: {loi}")
        finally:
            trang_thai["mo_ta"] = ""
