"""
Báo cáo giao dịch đội viên → trưởng nhóm: mỗi lần giao xong ghi một dòng vào bao_cao_giao_dich.csv cạnh AutoHoc.exe
(mở bằng Excel): ngày, giờ, nhóm, người giao, người nhận, số ô, tổng số lượng, chi tiết từng món.
"""
import csv
import os
import threading
from datetime import datetime

from thu_muc import THU_MUC_APP

DUONG_DAN = os.path.join(THU_MUC_APP, "bao_cao_giao_dich.csv")
CAC_COT = ["Ngày", "Giờ", "Nhóm", "Người giao", "Người nhận", "Số ô", "Số lượng", "Chi tiết"]

_khoa = threading.Lock()
# Dòng chưa ghi được (file đang mở trong Excel bị khóa): ghi bù ở lần sau.
_cho_ghi = []


def tom_tat(chi_tiet):
    """[(tên, số lượng)] -> "Tên A x3, Tên B x10" (gộp cùng tên, giữ thứ tự gặp đầu tiên)."""
    tong = {}
    for ten, so in chi_tiet:
        tong[ten] = tong.get(ten, 0) + so
    return ", ".join(f"{ten} x{so}" for ten, so in tong.items())


def tao_dong(nhom, nguoi_giao, nguoi_nhan, chi_tiet, luc=None):
    luc = luc or datetime.now()
    return [luc.strftime("%Y-%m-%d"), luc.strftime("%H:%M:%S"), nhom, nguoi_giao, nguoi_nhan,
            len(chi_tiet), sum(so for _, so in chi_tiet), tom_tat(chi_tiet)]


def ghi(nhom, nguoi_giao, nguoi_nhan, chi_tiet, luc=None, duong_dan=None):
    """
    Ghi một dòng (bỏ qua nếu không giao được món nào). Trả về None nếu đã ghi, chuỗi lỗi nếu chưa ghi được
    (dòng được giữ lại để ghi bù lần sau).
    """
    if not chi_tiet:
        return None
    duong_dan = duong_dan or DUONG_DAN
    with _khoa:
        _cho_ghi.append(tao_dong(nhom, nguoi_giao, nguoi_nhan, chi_tiet, luc))
        try:
            moi = not os.path.isfile(duong_dan) or os.path.getsize(duong_dan) == 0
            # utf-8-sig cho file mới để Excel nhận đúng tiếng Việt; ghi tiếp thì không thêm BOM giữa file.
            with open(duong_dan, "a", encoding="utf-8-sig" if moi else "utf-8", newline="") as f:
                viet = csv.writer(f)
                if moi:
                    viet.writerow(CAC_COT)
                viet.writerows(_cho_ghi)
        except OSError as loi:
            return f"chưa ghi được {os.path.basename(duong_dan)} ({loi}), sẽ ghi bù lần sau — đóng file nếu đang mở"
        _cho_ghi.clear()
    return None


def ghi_va_bao(in_log, nhom, nguoi_giao, nguoi_nhan, chi_tiet):
    loi = ghi(nhom, nguoi_giao, nguoi_nhan, chi_tiet)
    if loi:
        in_log(f"Báo cáo giao dịch: {loi}")
