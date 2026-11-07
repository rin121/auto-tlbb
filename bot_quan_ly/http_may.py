"""POST /bao-cao từ AutoHoc. Không đọc Telegram."""
import hmac
import json

GIOI_HAN_BODY = 200_000


def ma_khop(gui, dung):
    a = (gui or "").encode("utf-8")
    b = (dung or "").encode("utf-8")
    if not b or len(a) != len(b):
        return False
    return hmac.compare_digest(a, b)


def ten_hop_le(ten):
    ten = (ten or "").strip()
    if not ten or len(ten) > 40:
        return False
    return not any(ord(c) < 32 for c in ten)


def nhan_bao_cao(ma_gui, body, ma_dung, kho, bay_gio=None):
    """(mã HTTP, các câu cần nhắn). Sai mã thì 403, không ghi snapshot."""
    if not ma_khop(ma_gui, ma_dung):
        return 403, []
    if body is None or len(body) > GIOI_HAN_BODY:
        return 413, []
    try:
        data = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 400, []
    if not isinstance(data, dict) or not ten_hop_le(data.get("ten_may")):
        return 400, []
    data["ten_may"] = str(data["ten_may"]).strip()
    if data.get("id_may") is not None:
        chu = str(data.get("id_may") or "").strip()
        if chu and not ten_hop_le(chu):
            return 400, []
        if chu:
            data["id_may"] = chu
    if data.get("ten_may_cu"):
        data["ten_may_cu"] = str(data["ten_may_cu"]).strip()
    return 204, kho.nap(data, bay_gio)
