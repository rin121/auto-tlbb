"""Đăng ký tài khoản trên trang web Thiên Long Nhất Kiếm (chỉ stdlib)."""
from __future__ import annotations

import http.cookiejar
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

REGISTER_URL = "https://tlbbnhatkiem.online/register.php"
MAT_KHAU_MAC_DINH = "123123"
GIAY_GIUA_LAN = 20.0

SUCCESS_MARKERS = ("đăng ký thành công", "thanh cong")
EXISTS_MARKERS = ("đã được sử dụng", "da duoc su dung", "đã tồn tại")
RATE_LIMIT_MARKERS = ("20 giây", "20 giay", "quá nhanh", "qua nhanh", "thử lại sau", "thu lai sau")


@dataclass
class KetQuaDangKy:
    account: str
    ok: bool
    message: str
    skipped_exists: bool = False


def danh_sach_tai_khoan(tien_to: str, tu: int, den: int) -> list[str]:
    """sonoko + 1..3 → sonoko1, sonoko2, sonoko3."""
    return [f"{tien_to}{i}" for i in range(tu, den + 1)]


def mo_trinh_duyet() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    opener.addheaders = [
        (
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ),
        ("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        ("Accept-Language", "vi-VN,vi;q=0.9,en;q=0.8"),
    ]
    return opener


def _extract_csrf(html: str) -> str:
    m = re.search(r'name="csrf"\s+value="([^"]+)"', html)
    if not m:
        raise ValueError("Không tìm thấy CSRF token trên trang đăng ký.")
    return m.group(1)


def _extract_message(html: str) -> str:
    m = re.search(r'class="form-message[^"]*">\s*([^<]+?)\s*</div>', html, re.I)
    if m:
        return m.group(1).strip()
    return ""


def phan_loai_thong_bao(message: str) -> tuple[bool, bool, bool]:
    """(thành công, đã tồn tại, bị giới hạn tốc độ)."""
    low = message.lower()
    is_success = any(x in low for x in SUCCESS_MARKERS)
    is_exists = any(x in low for x in EXISTS_MARKERS)
    is_rate = any(x in low for x in RATE_LIMIT_MARKERS)
    return is_success, is_exists, is_rate


def dang_ky_mot(opener: urllib.request.OpenerDirector, account: str, password: str) -> KetQuaDangKy:
    try:
        with opener.open(REGISTER_URL, timeout=45) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        return KetQuaDangKy(account, False, f"Lỗi mạng (GET): {e}")

    try:
        csrf = _extract_csrf(html)
    except ValueError as e:
        return KetQuaDangKy(account, False, str(e))

    payload = urllib.parse.urlencode(
        {
            "csrf": csrf,
            "website": "",
            "account": account,
            "email": "",
            "password": password,
            "confirm": password,
        }
    ).encode("utf-8")

    req = urllib.request.Request(REGISTER_URL, data=payload, method="POST")
    try:
        with opener.open(req, timeout=45) as resp:
            html2 = resp.read().decode("utf-8", errors="replace")
    except urllib.error.URLError as e:
        return KetQuaDangKy(account, False, f"Lỗi mạng (POST): {e}")

    message = _extract_message(html2) or "(Không có thông báo từ server)"
    is_success, is_exists, _ = phan_loai_thong_bao(message)
    if is_success:
        return KetQuaDangKy(account, True, message)
    if is_exists:
        return KetQuaDangKy(account, False, message, skipped_exists=True)
    return KetQuaDangKy(account, False, message)


def cho_giay(giay: float, nen_dung) -> bool:
    """Chờ từng giây. True nếu bị yêu cầu dừng giữa chừng."""
    if giay <= 0:
        return False
    end = time.monotonic() + giay
    while True:
        if nen_dung():
            return True
        left = end - time.monotonic()
        if left <= 0:
            return False
        time.sleep(min(1.0, left))
