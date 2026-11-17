"""
Boss thế giới (tab Boss), gắn vào xoay vòng phó bản.

Mỗi 4 giờ (00, 04, 08, 12, 16, 20): trước 3 phút cả đội về Đại Lý. Đội trưởng bấm Theo đội,
nói chuyện NPC Di Chuyển, chọn «Bản Đồ BOOS VIP» rồi map người dùng chọn
(Ngân Ngai Tuyết Nguyên hoặc Yến Vương Cổ Mộ). Chết thì Đầu thai, Mạnh Bà, về Đại Lý, ra map lại.
Boss chết hoặc tới phút thứ 5 (vd 4:05) thì về Đại Lý và xoay vòng đi tiếp.
"""
from datetime import datetime, timedelta

from dang_nhap import bo_dau


class LoiBoss(Exception):
    pass

GIO_BOSS = (0, 4, 8, 12, 16, 20)
PHUT_VAO_TRUOC = 3
PHUT_ROI = 5
MAP_BOSS = ("Ngân Ngai Tuyết Nguyên", "Yến Vương Cổ Mộ")
DONG_BOOS_VIP = ("boos vip", "boss vip")
TU_BOSS_CHET = ("tieu diet", "da bi ha", "da chet", "bi giet", "danh bai")


def khoa_moc_boss(moc):
    return moc.strftime("%Y-%m-%dT%H")


def khung_boss(bay_gio):
    """(mốc giờ boss, lúc bắt đầu, lúc phải về) nếu đang trong cửa sổ, không thì None.

    Cửa sổ là [giờ boss − 3 phút, giờ boss + 5 phút). 23:57 thuộc mốc 00:00 hôm sau. 04:05 thì đã hết.
    """
    gio = bay_gio.replace(minute=0, second=0, microsecond=0)
    for lech in (-1, 0, 1):
        moc = gio + timedelta(hours=lech)
        if moc.hour not in GIO_BOSS:
            continue
        bat = moc - timedelta(minutes=PHUT_VAO_TRUOC)
        ket = moc + timedelta(minutes=PHUT_ROI)
        if bat <= bay_gio < ket:
            return moc, bat, ket
    return None


def den_luc_roi_boss(bay_gio, moc):
    return bay_gio >= moc + timedelta(minutes=PHUT_ROI)


def nen_di_boss(bay_gio, moc_da_xong, bat=True):
    """True khi tab Boss đang bật, đang trong cửa sổ, và mốc này chưa đi xong."""
    if not bat:
        return False
    khung = khung_boss(bay_gio)
    if khung is None:
        return False
    return khoa_moc_boss(khung[0]) != (moc_da_xong or "")


def cai_dat_boss(chung):
    ten = chung.get("map_boss") or MAP_BOSS[0]
    if ten not in MAP_BOSS:
        ten = MAP_BOSS[0]
    return {"bat": bool(chung.get("bat_boss")), "map": ten,
            "moc_da_xong": chung.get("moc_boss_da_xong") or ""}


def _dong_id(cac_dong, mau):
    khoa = bo_dau(mau)
    for loai, s, e, chu in cac_dong:
        if loai == "id" and s >= 0 and khoa in bo_dau(chu or ""):
            return s, e
    return None


def dong_menu_boss(cac_dong):
    """(script, extra) của dòng Bản Đồ BOOS VIP / Boss Vip."""
    for mau in DONG_BOOS_VIP:
        dong = _dong_id(cac_dong, mau)
        if dong:
            return dong
    return None


def dong_map_boss(cac_dong, ten_map):
    return _dong_id(cac_dong, ten_map)


def dong_tiep(cac_dong):
    return _dong_id(cac_dong, "tiep")


def cung_ten_map(dang_o, mong):
    if not dang_o or not mong:
        return False
    a, b = bo_dau(dang_o), bo_dau(mong)
    return a == b or b in a or a in b


def _cum_boss(ten_map):
    return " ".join(bo_dau(ten_map).split()[:2])


def khop_ten_boss(ten, ten_map):
    """Tên quái chứa hai chữ đầu của map (Yến Vương / Ngân Ngai)."""
    if not ten:
        return False
    return _cum_boss(ten_map) in bo_dau(ten)


def thong_bao_boss_chet(cac_dong, ten_map):
    cum = _cum_boss(ten_map)
    for chu in cac_dong:
        b = bo_dau(chu or "")
        if cum in b and any(tu in b for tu in TU_BOSS_CHET):
            return True
    return False


def boss_bien_mat(da_thay, cac_ten_hp, ten_map):
    """(đã chết, đang thấy boss). Chết khi boss trong tầm có máu 0. Khuất tầm không tính là chết."""
    song = chet = False
    for ten, hp in cac_ten_hp:
        if not khop_ten_boss(ten, ten_map):
            continue
        if hp > 0:
            song = True
        else:
            chet = True
    if chet and not song:
        return True, True
    if song:
        return False, True
    return False, da_thay
