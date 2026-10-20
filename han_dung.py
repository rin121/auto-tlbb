"""
Hạn dùng của bản dùng thử.

Bản build bằng dong_goi\\build_dung_thu.ps1 có thêm module _han_dung, một trong hai kiểu:
  - HET_HAN: hết hạn vào thời điểm cố định (giây kể từ 1970, giờ UTC), tính từ lúc build.
  - THOI_HAN_GIAY + MA_BAN: dùng được THOI_HAN_GIAY giây kể từ lần đầu mở bản build MA_BAN trên máy này
    (bản test vài phút, build xong lúc nào mở thử cũng được).
Không có module đó (chạy từ code, bản đóng gói thường) thì dùng không giới hạn.

Giờ hiện tại lấy từ internet (header Date của vài trang lớn) để chỉnh đồng hồ máy không có tác dụng.
Không vào được mạng thì dùng đồng hồ máy, nhưng không bao giờ lùi quá thời điểm lớn nhất đã thấy
(ghi trong registry HKCU\\Software\\AutoHoc), nên vặn lùi đồng hồ cũng không gia hạn được.
"""
import time
import urllib.request
import winreg
from email.utils import parsedate_to_datetime

try:
    import _han_dung as _ban_build
except ImportError:
    _ban_build = None

CAC_TRANG_LAY_GIO = ("https://www.google.com", "https://www.cloudflare.com", "https://www.microsoft.com")
GIAY_CHO_MOI_TRANG = 3
KHOA_REGISTRY = r"Software\AutoHoc"
TEN_LAN_CUOI = "lan_cuoi"
THONG_BAO_HET_HAN = "Đã hết hạn dùng thử, liên hệ 0928462386 zalo để gia hạn bạn nhé"

_lech_so_voi_may = 0.0
_het_han = getattr(_ban_build, "HET_HAN", None)


def co_han_dung():
    return _ban_build is not None


def _gio_tren_mang():
    for trang in CAC_TRANG_LAY_GIO:
        try:
            yeu_cau = urllib.request.Request(trang, method="HEAD", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(yeu_cau, timeout=GIAY_CHO_MOI_TRANG) as phan_hoi:
                ngay = phan_hoi.headers.get("Date")
            if ngay:
                return parsedate_to_datetime(ngay).timestamp()
        except Exception:
            continue
    return None


def _doc_registry(ten):
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KHOA_REGISTRY) as khoa:
            return float(winreg.QueryValueEx(khoa, ten)[0])
    except (OSError, ValueError):
        return None


def _ghi_registry(ten, gio):
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, KHOA_REGISTRY) as khoa:
            winreg.SetValueEx(khoa, ten, 0, winreg.REG_SZ, str(int(gio)))
    except OSError:
        pass


def dong_bo_gio_mang():
    """Gọi lúc mở auto (mất tối đa vài giây nếu không có mạng). Sau đó gio_hien_tai() không cần mạng nữa."""
    global _lech_so_voi_may
    gio_mang = _gio_tren_mang()
    if gio_mang is not None:
        _lech_so_voi_may = gio_mang - time.time()


def gio_hien_tai():
    gio = max(time.time() + _lech_so_voi_may, _doc_registry(TEN_LAN_CUOI) or 0)
    _ghi_registry(TEN_LAN_CUOI, gio)
    return gio


def het_han():
    """Thời điểm hết hạn. Bản tính từ lần đầu mở thì lần gọi đầu tiên ghi lại lúc bắt đầu vào registry."""
    global _het_han
    if _het_han is None and _ban_build is not None:
        ten = f"bat_dau_{_ban_build.MA_BAN}"
        bat_dau = _doc_registry(ten)
        if bat_dau is None:
            bat_dau = gio_hien_tai()
            _ghi_registry(ten, bat_dau)
        _het_han = bat_dau + _ban_build.THOI_HAN_GIAY
    return _het_han


def giay_con_lai():
    """Số giây còn dùng được (<= 0 là hết hạn). Không có hạn dùng thì trả về None."""
    if _ban_build is None:
        return None
    return het_han() - gio_hien_tai()


def mo_ta_con_lai(giay):
    if giay <= 0:
        return "đã hết hạn"
    ngay, du = divmod(int(giay), 86400)
    gio, du = divmod(du, 3600)
    phut = du // 60
    if ngay:
        return f"còn {ngay} ngày {gio} giờ"
    if gio:
        return f"còn {gio} giờ {phut} phút"
    if phut:
        return f"còn {phut} phút"
    return f"còn {du} giây"


def ngay_het_han():
    return time.strftime("%H:%M:%S %d/%m/%Y", time.localtime(het_han()))
