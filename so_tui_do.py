"""
SỔ TÚI ĐỒ: số ô đồ giao được cho acc chính của từng nhân vật phó bản, lưu mãi ở DUONG_DAN (không xóa theo ngày).

Xoay vòng ghi sổ:
    đầu round  -> "chua_ro" (đang đi, chưa biết còn gì; round dừng giữa chừng thì vẫn là chưa rõ)
    cuối round -> "da_ghi" + số ô (sau khi đội viên giao cho trưởng nhóm; giao lỗi thì đồ còn trong túi, số ô > 0)
Giao dịch cho acc chính đọc sổ: còn đồ / chưa rõ thì đăng nhập để giao (kể cả không phải trưởng nhóm), đã ghi 0 ô thì
bỏ qua; giao xong thì ghi 0 ô + đã giao cho acc chính, mã đồ không giao được (đồ khóa) để lần sau không đếm nữa.
Số ô giao được = ô túi Đạo cụ + Nguyên liệu, trừ đồ loại trừ (tab Giao dịch cho acc chính) và mã không giao được.
"""
import json
import os
import threading
from datetime import datetime

import cau_hinh
from auto_chuyen_sinh import chuan_hoa
from dang_nhap import bo_dau
from thu_muc import THU_MUC_APP

DUONG_DAN = os.path.join(THU_MUC_APP, "so_tui_do.json")
LOAI_TRU_MAC_DINH = ("Càn Khôn Hồ, Bách Bảo Nang, Bách Bảo Rương, Tân Thủ, Thanh Đồng Đao, Long Văn, Ám Khí, "
                     "Chuyển Sinh Tại Chỗ, Hộp Point")
CHUA_RO = "chua_ro"
DA_GHI = "da_ghi"

_khoa = threading.Lock()


def cac_tu_loai_tru(chu):
    # So không dấu: game ghi «Mãnh Vỡ» trong khi người chơi gõ «Mảnh Vỡ».
    return [bo_dau(t) for t in chu.replace("\n", ",").split(",") if t.strip()]


def bi_loai_tru(ten, cac_tu):
    khoa = bo_dau(ten)
    return any(t in khoa for t in cac_tu)


def loai_tru_hien_tai():
    cd = cau_hinh.chung().get("giao_acc_chinh") or {}
    return cac_tu_loai_tru(cd.get("loai_tru") or LOAI_TRU_MAC_DINH)


def dem_o(tui, cac_tu, ma_khong_giao=()):
    """Số ô đồ giao được trong tui ({(túi, ô): (mã, số, tên)} của giao_dich.doc_tui)."""
    bo = set(ma_khong_giao)
    return sum(1 for ma, _, ten in tui.values() if ma not in bo and not bi_loai_tru(ten, cac_tu))


def _bay_gio():
    return datetime.now().isoformat(timespec="seconds")


def doc(duong_dan=None):
    try:
        with open(duong_dan or DUONG_DAN, encoding="utf-8") as f:
            du_lieu = json.load(f)
    except (OSError, ValueError):
        return {}
    return du_lieu if isinstance(du_lieu, dict) else {}


def _ghi_file(du_lieu, duong_dan):
    tam = f"{duong_dan}.{os.getpid()}.tmp"
    try:
        with open(tam, "w", encoding="utf-8") as f:
            json.dump(du_lieu, f, ensure_ascii=False, indent=1)
        os.replace(tam, duong_dan)
    except OSError:
        pass


def _sua(tk, ten, sua, duong_dan=None):
    duong_dan = duong_dan or DUONG_DAN
    with _khoa:
        du_lieu = doc(duong_dan)
        muc = dict(du_lieu.get(chuan_hoa(ten)) or {})
        muc.update(tk=tk, ten=ten)
        sua(muc)
        du_lieu[chuan_hoa(ten)] = muc
        _ghi_file(du_lieu, duong_dan)
        return muc


def ghi_chua_ro(tk, ten, duong_dan=None):
    def sua(muc):
        muc.update(trang_thai=CHUA_RO, luc=_bay_gio())
    return _sua(tk, ten, sua, duong_dan)


def ghi_so_o(tk, ten, tui, cac_tu=None, duong_dan=None):
    """Ghi số ô giao được hiện có trong túi; có đồ thì bỏ dấu đã giao cho acc chính."""
    cac_tu = loai_tru_hien_tai() if cac_tu is None else cac_tu

    def sua(muc):
        so = dem_o(tui, cac_tu, muc.get("ma_khong_giao") or ())
        muc.update(trang_thai=DA_GHI, so_o=so, luc=_bay_gio())
        if so:
            muc["da_giao_acc_chinh"] = False
    return _sua(tk, ten, sua, duong_dan)


def ghi_da_giao(tk, ten, ma_khong_giao=(), duong_dan=None):
    """Giao cho acc chính xong (hoặc không có đồ): 0 ô, nhớ mã không giao được."""
    def sua(muc):
        muc.update(trang_thai=DA_GHI, so_o=0, luc=_bay_gio(), da_giao_acc_chinh=True,
                   luc_giao_acc_chinh=_bay_gio(),
                   ma_khong_giao=sorted(set(muc.get("ma_khong_giao") or ()) | set(ma_khong_giao)))
    return _sua(tk, ten, sua, duong_dan)


def muc_cua(so, ten):
    return so.get(chuan_hoa(ten))


def can_giao(muc):
    """Sổ ghi còn đồ hoặc chưa rõ (round dừng giữa chừng) -> phải đăng nhập kiểm tra."""
    return bool(muc) and (muc.get("trang_thai") == CHUA_RO or (muc.get("so_o") or 0) > 0)


def chac_khong_co_do(muc):
    return bool(muc) and muc.get("trang_thai") == DA_GHI and not muc.get("so_o")


def mo_ta(muc):
    if not muc:
        return "chưa có trong sổ"
    if muc.get("trang_thai") == CHUA_RO:
        return f"chưa rõ (đi phó bản lúc {muc.get('luc', '?')}, chưa ghi cuối round)"
    return f"{muc.get('so_o') or 0} ô đồ (ghi lúc {muc.get('luc', '?')})"
