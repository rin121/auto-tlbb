"""Inline keyboard hai tầng: danh sách máy → thao tác đọc snapshot."""
import hashlib
import re
import time

from bot_quan_ly.lenh import (
    GIOI_HAN_TIN,
    _luc,
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
CALLBACK_KHONG_LAM_GI = "_"
_ICON = ("🖥", "🌸", "⭐", "🍀", "💜", "☀️", "🎮", "💎")
_HANH_DONG = frozenset(("ping", "status", "nhom", "acc", "loi"))
_VONG = re.compile(r"(?:round|vòng)\s*(\d+)", re.IGNORECASE)
_TIEN_TO_HOAT_DONG = (
    ("Phó bản PMP: Sát Tinh: ", "Phó bản Sát Tinh: "),
    ("Phó bản PMP: Sát Tinh", "Phó bản Sát Tinh"),
)


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
    snap = may.get("snapshot") or {}
    so = _so_cua_so(snap)
    vong = vong_tu_snapshot(snap) if tt == "online" else ""
    duoi = f" - {tt}" + (f" - {vong}" if vong else "") + f" - {so} người"
    nhan = f"{ten}{duoi}"
    if len(nhan) <= _GIOI_HAN_TELEGRAM:
        return nhan
    gon = duoi if len(duoi) < _GIOI_HAN_TELEGRAM else f" - {tt} - {so}"
    con = _GIOI_HAN_TELEGRAM - len(gon) - 1
    if con < 4:
        return (ten[: _GIOI_HAN_TELEGRAM - 1] + "…")[:_GIOI_HAN_TELEGRAM]
    return ten[:con] + "…" + gon


def vong_tu_snapshot(snap):
    """'Nhóm 1 round 2: …' → 'Vòng 2'."""
    khop = _VONG.search(str((snap or {}).get("xoay_vong") or ""))
    return f"Vòng {khop.group(1)}" if khop else ""


def hoat_dong_nhan_vat(cs):
    """Phần luồng chính của cột trạng thái (bỏ phần chiến đấu / auto click sau « | »)."""
    chu = str(cs.get("mo_ta") or "").split(" | ", 1)[0].strip()
    for cu, moi in _TIEN_TO_HOAT_DONG:
        if chu.startswith(cu):
            chu = moi + chu[len(cu):]
            break
    return chu or "chưa có hoạt động"


def luot_nhan_vat(cs):
    """'Hôm nay: Sát Tinh 8 vòng, PMP 0 vòng, Ác Tặc 1 lần' — rỗng khi chưa đi lượt nào (đội viên)."""
    luot = cs.get("luot_hom_nay") or {}
    st, pmp, at = (int(luot.get(k) or 0) for k in ("sat_tinh", "pmp", "ac_tac"))
    if not (st or pmp or at):
        return ""
    return f"Hôm nay: Sát Tinh {st} vòng, PMP {pmp} vòng, Ác Tặc {at} lần"


def khoi_may(kho, may, bay_gio=None):
    """Tiêu đề máy + một dòng / nhân vật (chỉ khi online — offline thì snapshot đã cũ)."""
    snap = may.get("snapshot") or {}
    tt = _online_offline(kho, may, bay_gio)
    if tt != "online":
        return [f"{may['ten']} - offline - lần cuối {_luc(may, '%H:%M %d/%m')}"]
    tieu_de = " - ".join(p for p in (may["ten"], tt, vong_tu_snapshot(snap)) if p)
    dong = [tieu_de]
    cua = snap.get("cua_so") or []
    if not cua:
        dong.append("• chưa có cửa sổ game")
    for cs in cua:
        ten = cs.get("ten") or "(chưa có tên)"
        dong.append(f"• {ten} - {hoat_dong_nhan_vat(cs)}")
        luot = luot_nhan_vat(cs)
        if luot:
            dong.append(f"   {luot}")
    return dong


def _cat_text(text):
    if len(text) <= GIOI_HAN_TIN:
        return text
    return text[: GIOI_HAN_TIN - 1] + "…"


def _html(chu):
    return str(chu).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def icon_may(may):
    return _ICON[int(slug_tu_may(may), 16) % len(_ICON)]


def _viec_ngan(cs):
    viec = hoat_dong_nhan_vat(cs)
    if viec.startswith("Phó bản "):
        viec = viec[len("Phó bản "):]
    return viec


def _the_may(kho, may, bay_gio):
    """Một khối chữ / máy (HTML). Telegram không vẽ được thẻ màu như web."""
    snap = may.get("snapshot") or {}
    icon = icon_may(may)
    tt = _online_offline(kho, may, bay_gio)
    cham = "🟢" if tt == "online" else "⚪"
    so = f"{_so_cua_so(snap)} người"
    if tt == "online":
        phu = " · ".join(p for p in ("Online", vong_tu_snapshot(snap), so) if p)
    else:
        phu = f"Offline · {so} · lần cuối {_luc(may, '%H:%M %d/%m')}"
    dong = [f"{icon} <b>{_html(may['ten'])}</b>  {cham} {_html(phu)}"]
    if tt != "online":
        return "\n".join(dong)
    cua = snap.get("cua_so") or []
    if not cua:
        dong.append("• chưa có cửa sổ game")
    for cs in cua:
        ten = cs.get("ten") or "(chưa có tên)"
        dong.append(f"• {_html(ten)} — {_html(_viec_ngan(cs))}")
        luot = luot_nhan_vat(cs)
        if luot:
            dong.append(f"ℹ️ {_html(luot)}")
    return "\n".join(dong)


def _cat_nut(chu):
    if len(chu) <= _GIOI_HAN_TELEGRAM:
        return chu
    return chu[: _GIOI_HAN_TELEGRAM - 1] + "…"


def _nhan_nut(may):
    return _cat_nut(f"{icon_may(may)} {may['ten']}")


def keyboard_danh_sach(kho, bay_gio=None):
    bay_gio = time.time() if bay_gio is None else bay_gio
    ds = kho.danh_sach_gom_ten(bay_gio)
    if not ds:
        return {
            "text": "Chưa có máy nào báo cáo.",
            "parse_mode": "HTML",
            "reply_markup": _markup([[_nut("🔄 Làm mới", "ds")]]),
        }
    the = [_the_may(kho, may, bay_gio) for may in ds]
    text = "✨ <b>Danh sách máy</b>\n\n" + "\n\n".join(the)
    nut = [_nut(_nhan_nut(may), f"m:{slug_tu_may(may)}") for may in ds]
    hang = _hang_2(nut)
    hang.append([_nut("🔄 Làm mới", "ds")])
    return {"text": _cat_text(text), "parse_mode": "HTML", "reply_markup": _markup(hang)}


def keyboard_may(kho, may, bay_gio=None):
    bay_gio = time.time() if bay_gio is None else bay_gio
    slug = slug_tu_may(may)
    text = _cat_text("\n".join(_html(d) for d in khoi_may(kho, may, bay_gio)))
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
    return {"text": text, "parse_mode": "HTML", "reply_markup": _markup(hang)}


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
      loai: 'edit' | 'send' | 'bo_qua'
      text, reply_markup (edit)
      noi_dung_gui (send — tin riêng, giữ menu)
    """
    bay_gio = time.time() if bay_gio is None else bay_gio
    raw = (data or "").strip()
    if raw == CALLBACK_KHONG_LAM_GI:
        return {"loai": "bo_qua"}
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
