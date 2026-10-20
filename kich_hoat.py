"""
Kích hoạt AutoHoc theo máy (HWID + license.dat ký Ed25519).

- Bản exe cộng đồng: build gắn module _kich_hoat_bat (BAT_BUOC = True) → bắt buộc license hợp lệ.
- Chạy từ code (python giao_dien.py) không có _kich_hoat_bat → không bắt buộc (dev).
- User gửi HWID qua Zalo; admin chạy dong_goi/tao_license.py để tạo license.dat.
"""
import base64
import ctypes
import hashlib
import json
import os
import re
import winreg

from thu_muc import THU_MUC_APP

try:
    import _kich_hoat_bat as _bat_build
except ImportError:
    _bat_build = None

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:
    Ed25519PublicKey = None

from kich_hoat_khoa_cong import KHOA_CONG_B64

TEN_FILE_LICENSE = "license.dat"
PHIEN_BAN = 1
LIEN_HE_ZALO = "0928462386"


def bat_buoc_kich_hoat():
    return _bat_build is not None and getattr(_bat_build, "BAT_BUOC", True)


def duong_dan_license():
    return os.path.join(THU_MUC_APP, TEN_FILE_LICENSE)


def _volume_serial_o_c():
    serial = ctypes.c_uint32()
    if not ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p("C:\\"), None, 0, ctypes.byref(serial), None, None, None, 0):
        return "0"
    return str(serial.value)


def _machine_guid():
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as khoa:
            return str(winreg.QueryValueEx(khoa, "MachineGuid")[0])
    except OSError:
        return ""


def doc_hwid():
    """Mã máy ổn định (hash MachineGuid + serial ổ C:)."""
    raw = f"{_machine_guid()}|{_volume_serial_o_c()}"
    digest = hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest().upper()
    return "-".join(digest[i:i + 4] for i in range(0, 16, 4))


def _chuan_hoa_hwid(chu):
    return re.sub(r"[^0-9A-F]", "", (chu or "").upper())


def _noi_dung_ky(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _doc_ban_license(duong_dan=None):
    duong_dan = duong_dan or duong_dan_license()
    if not os.path.isfile(duong_dan):
        return None
    try:
        with open(duong_dan, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, TypeError):
        return None


def _khoa_cong():
    if not KHOA_CONG_B64 or Ed25519PublicKey is None:
        return None
    try:
        raw = base64.b64decode(KHOA_CONG_B64)
        return Ed25519PublicKey.from_public_bytes(raw)
    except Exception:
        return None


def xac_thuc_license(duong_dan=None):
    """
    Trả về (hop_le: bool, mo_ta: str).
    hop_le False: mo_ta là lý do (tiếng Việt).
    """
    if not bat_buoc_kich_hoat():
        return True, "Không yêu cầu kích hoạt (chạy từ code hoặc bản nội bộ)."

    if Ed25519PublicKey is None:
        return False, "Thiếu thư viện cryptography trong bản cài — liên hệ người phát hành."

    khoa = _khoa_cong()
    if khoa is None:
        return False, "Bản auto chưa có khóa công kích hoạt — liên hệ người phát hành."

    ban = _doc_ban_license(duong_dan)
    if not ban:
        return False, f"Chưa có file {TEN_FILE_LICENSE} cạnh AutoHoc.exe."

    chu_ky = ban.get("chu_ky")
    payload = ban.get("payload")
    if not chu_ky or not isinstance(payload, dict):
        return False, "File license không đúng định dạng."

    if payload.get("v") != PHIEN_BAN:
        return False, "License phiên bản không tương thích."

    hwid_license = _chuan_hoa_hwid(payload.get("hwid", ""))
    hwid_may = _chuan_hoa_hwid(doc_hwid())
    if hwid_license != hwid_may:
        return False, "License không khớp máy này (HWID khác)."

    try:
        khoa.verify(base64.b64decode(chu_ky), _noi_dung_ky(payload))
    except Exception:
        return False, "Chữ ký license không hợp lệ (file bị sửa hoặc giả)."

    het = payload.get("het_han")
    thoi_han = ""
    if het is not None:
        try:
            import time
            from datetime import datetime
            ts = float(het)
            if time.time() > ts:
                return False, "License đã hết hạn."
            thoi_han = f", hết hạn lúc {datetime.fromtimestamp(ts).strftime('%H:%M %d/%m/%Y')}"
        except (TypeError, ValueError):
            pass

    ghi = payload.get("ghi_chu") or ""
    if ghi:
        return True, f"Đã kích hoạt ({ghi}{thoi_han})."
    return True, f"Đã kích hoạt{thoi_han or ' (không giới hạn thời gian)'}."


def da_kich_hoat(duong_dan=None):
    return xac_thuc_license(duong_dan)[0]


def luu_license_tu_file(nguon):
    """Copy license user chọn vào thư mục app. Trả về (ok, mo_ta)."""
    ban = _doc_ban_license(nguon)
    if not ban:
        return False, "Không đọc được file license."
    hop_le, mo_ta = xac_thuc_license(nguon)
    if not hop_le:
        return False, mo_ta
    dich = duong_dan_license()
    try:
        with open(nguon, encoding="utf-8") as f:
            noi_dung = f.read()
        with open(dich, "w", encoding="utf-8") as f:
            f.write(noi_dung)
    except OSError as loi:
        return False, f"Không ghi được license: {loi}"
    return True, mo_ta
