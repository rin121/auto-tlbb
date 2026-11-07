"""Inline keyboard hai tầng: danh sách máy → thao tác đọc snapshot."""
import hashlib
import time

from bot_quan_ly.lenh import (
    _online_offline,
    _so_cua_so,
    tin_acc,
    tin_loi,
    tin_nhom,
    tin_ping,
    tin_status,
)

_SO_COT = 2
_GIOI_HAN_TELEGRAM = 64
_HANH_DONG = frozenset(("ping", "status", "nhom", "acc", "loi"))


def id_may_tu_ban(may):
    snap = may.get("snapshot") if isinstance(may.get("snapshot"), dict) else may
    if not isinstance(snap, dict):
        snap = {}
    return str(
        snap.get("id_may")
        or may.get("id")
        or may.get("ten")
        or snap.get("ten_may")
        or ""
    ).strip()


def slug_tu_may(may):
    chu = id_may_tu_ban(may).casefold()
    if not chu:
        chu = (may.get("ten") or "").casefold()
    return hashlib.sha256(chu.encode("utf-8")).hexdigest()[:8]


def may_tu_slug(kho, slug, bay_gio=None):
    if not slug:
        return None
    slug = slug.casefold()
    for may in kho.danh_sach_gom_ten(bay_gio):
        if slug_tu_may(may) == slug:
            return may
    return None


def _nut(text, callback_data):
    return {"text": text, "callback_data": callback_data}


def _hang_2(nut):
    hang = []
    for i in range(0, len(nut), _SO_COT):
        hang.append(nut[i : i + _SO_COT])
    return hang


def _hang_1(nut):
    return [[b] for b in nut]


def _markup(hang):
    return {"inline_keyboard": hang}


def _nhan_may(kho, may, bay_gio=None):
    tt = _online_offline(kho, may, bay_gio)
    ten = may["ten"]
    so = _so_cua_so(may.get("snapshot") or {})
    duoi = f" - {tt} - {so} người"
    nhan = f"{ten}{duoi}"
    if len(nhan) <= _GIOI_HAN_TELEGRAM:
        return nhan
    gon = duoi if len(duoi) < _GIOI_HAN_TELEGRAM else f" - {tt} - {so}"
    con = _GIOI_HAN_TELEGRAM - len(gon) - 1
    if con < 4:
        return (ten[: _GIOI_HAN_TELEGRAM - 1] + "…")[:_GIOI_HAN_TELEGRAM]
    return ten[:con] + "…" + gon


def keyboard_danh_sach(kho, bay_gio=None):
    bay_gio = time.time() if bay_gio is None else bay_gio
    ds = kho.danh_sach_gom_ten(bay_gio)
    if not ds:
        text = "Chưa có máy nào báo cáo."
        mk = _markup([[_nut("Làm mới", "ds")]])
        return {"text": text, "reply_markup": mk}
    nut = [_nut(_nhan_may(kho, may, bay_gio), f"m:{slug_tu_may(may)}") for may in ds]
    hang = _hang_1(nut)
    hang.append([_nut("Làm mới", "ds")])
    text = f"Chọn máy ({len(ds)}):"
    return {"text": text, "reply_markup": _markup(hang)}


def keyboard_may(kho, may, bay_gio=None):
    bay_gio = time.time() if bay_gio is None else bay_gio
    slug = slug_tu_may(may)
    tt = _online_offline(kho, may, bay_gio)
    text = f"{may['ten']}: {tt}"
    hang = [
        [
            _nut("Status", f"x:{slug}:status"),
            _nut("Ping", f"x:{slug}:ping"),
        ],
        [
            _nut("Nhóm", f"x:{slug}:nhom"),
            _nut("Acc", f"x:{slug}:acc"),
        ],
        [_nut("Lỗi", f"x:{slug}:loi")],
        [
            _nut("Quay lại", "ds"),
            _nut("Làm mới", f"m:{slug}"),
        ],
    ]
    return {"text": text, "reply_markup": _markup(hang)}


def _noi_dung_hanh_dong(kho, may, act, bay_gio):
    act = (act or "").lower()
    if act == "ping":
        return tin_ping(kho, may, bay_gio)
    if act == "status":
        return tin_status(kho, may, bay_gio)
    if act == "nhom":
        return tin_nhom(may)
    if act == "acc":
        return tin_acc(may)
    if act == "loi":
        return tin_loi(may)
    return None


def xuly_callback(kho, data, bay_gio=None):
    """
    Trả dict:
      loai: 'edit' | 'send'
      text, reply_markup (edit)
      noi_dung_gui (send — tin riêng, giữ menu)
    """
    bay_gio = time.time() if bay_gio is None else bay_gio
    raw = (data or "").strip()
    if not raw or raw == "ds":
        ban = keyboard_danh_sach(kho, bay_gio)
        return {"loai": "edit", **ban}

    if raw.startswith("m:"):
        slug = raw[2:].strip()
        may = may_tu_slug(kho, slug, bay_gio)
        if may is None:
            ban = keyboard_danh_sach(kho, bay_gio)
            ban["text"] = "Không thấy máy — danh sách đã cập nhật."
            return {"loai": "edit", **ban}
        ban = keyboard_may(kho, may, bay_gio)
        return {"loai": "edit", **ban}

    if raw.startswith("x:"):
        phan = raw[2:].split(":", 1)
        if len(phan) != 2:
            return {"loai": "edit", **keyboard_danh_sach(kho, bay_gio)}
        slug, act = phan[0].strip(), phan[1].strip().lower()
        may = may_tu_slug(kho, slug, bay_gio)
        if may is None:
            ban = keyboard_danh_sach(kho, bay_gio)
            return {
                "loai": "send",
                "noi_dung_gui": "Không thấy máy (đã đổi id hoặc tắt). Chọn máy bên dưới.",
                "reply_markup": ban["reply_markup"],
            }
        if act not in _HANH_DONG:
            sub = keyboard_may(kho, may, bay_gio)
            return {
                "loai": "send",
                "noi_dung_gui": f"Hành động «{act}» không hợp lệ.",
                "reply_markup": sub["reply_markup"],
            }
        noi = _noi_dung_hanh_dong(kho, may, act, bay_gio)
        if not noi:
            sub = keyboard_may(kho, may, bay_gio)
            return {
                "loai": "send",
                "noi_dung_gui": "Không có dữ liệu.",
                "reply_markup": sub["reply_markup"],
            }
        sub = keyboard_may(kho, may, bay_gio)
        return {
            "loai": "send",
            "noi_dung_gui": noi,
            "reply_markup": sub["reply_markup"],
        }

    if raw.startswith("bk:sub:"):
        return {"loai": "edit", **keyboard_danh_sach(kho, bay_gio)}

    return {"loai": "edit", **keyboard_danh_sach(kho, bay_gio)}
