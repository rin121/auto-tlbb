"""Ghép câu trả lời Telegram từ snapshot máy. Không gọi mạng."""
import re
import time

GIOI_HAN_TIN = 4000
_LENH = re.compile(r"^/([A-Za-z0-9_]+)(?:@[A-Za-z0-9_]+)?(?:\s+(.*))?$", re.DOTALL)
_CAN_TEN = frozenset(("ping", "status", "nhom", "acc", "loi"))
_NHAN_TRANG = {"online": "online", "im": "im", "tat": "đã tắt"}
_NHAN_LOAI = {"pho_ban": "phó bản", "train": "train"}


def phan_lenh(text):
    """('/status', 'PhongKhach') hoặc (None, '')."""
    khoa = _LENH.match((text or "").strip())
    if not khoa:
        return None, ""
    return khoa.group(1).lower(), (khoa.group(2) or "").strip()


def cat_tin(chu, gioi_han=GIOI_HAN_TIN):
    chu = chu or ""
    if not chu:
        return []
    if len(chu) <= gioi_han:
        return [chu]
    doan = []
    while chu:
        if len(chu) <= gioi_han:
            doan.append(chu)
            break
        cat = chu.rfind("\n", 0, gioi_han)
        if cat < gioi_han // 2:
            cat = gioi_han
        doan.append(chu[:cat].rstrip("\n"))
        chu = chu[cat:].lstrip("\n")
    return [d for d in doan if d]


def mo_ta_uptime(giay):
    giay = max(0, int(giay or 0))
    gio, phut = divmod(giay // 60, 60)
    if gio:
        return f"{gio} giờ {phut} phút"
    return f"{phut} phút"


def _luc(rec, mau="%H:%M:%S"):
    return time.strftime(mau, time.localtime(rec["luc_thay"]))


def _so_cua_so(snap):
    if snap.get("so_cua_so") is not None:
        return snap["so_cua_so"]
    return len(snap.get("cua_so") or [])


def tin_ds(kho, bay_gio=None):
    ds = kho.danh_sach()
    if not ds:
        return "Chưa có máy nào báo cáo."
    dong = [f"Máy ({len(ds)})"]
    for may in ds:
        trang = _NHAN_TRANG[kho.trang_thai_luc(may, bay_gio)]
        so = _so_cua_so(may["snapshot"])
        dong.append(f"- {may['ten']}: {trang}, {so} cửa sổ, lần cuối {_luc(may)}")
    return "\n".join(dong)


def _chon(kho, ten, bay_gio):
    if ten:
        may = kho.tim(ten)
        if may is None:
            return None, f"Không thấy máy «{ten}».\n" + tin_ds(kho, bay_gio)
        return may, None
    ds = kho.danh_sach()
    if len(ds) == 1:
        return ds[0], None
    if not ds:
        return None, "Chưa có máy nào báo cáo."
    return None, "Có nhiều máy, ghi thêm tên.\n" + tin_ds(kho, bay_gio)


def _tieu_de(kho, may, bay_gio):
    trang = _NHAN_TRANG[kho.trang_thai_luc(may, bay_gio)]
    return f"{may['ten']}: {trang}"


def tin_ping(kho, may, bay_gio=None):
    snap = may["snapshot"]
    dong = [
        _tieu_de(kho, may, bay_gio),
        f"Uptime: {mo_ta_uptime(snap.get('uptime_giay'))}",
        f"Cửa sổ: {_so_cua_so(snap)}",
        f"Lần báo cáo: {_luc(may, '%Y-%m-%d %H:%M:%S')}",
    ]
    if snap.get("xoay_vong"):
        dong.append(f"Xoay vòng: {snap['xoay_vong']}")
    return "\n".join(dong)


def _dong_cua_so(cs, so):
    ten = cs.get("ten") or "(chưa có tên)"
    level = cs.get("level")
    lv = f" (lv {level})" if level not in (None, "") else ""
    tk = f" — {cs['tai_khoan']}" if cs.get("tai_khoan") else ""
    phan = " | ".join(
        p for p in (
            cs.get("map") or "",
            f"HP {cs['hp']}" if cs.get("hp") not in (None, "") else "",
            cs.get("mo_ta") or "",
        ) if p
    )
    dong = f"{so}. {ten}{lv}{tk}"
    if phan:
        dong += "\n   " + phan
    if cs.get("loi"):
        dong += "\n   Lỗi: " + str(cs["loi"])
    return dong


def tin_status(kho, may, bay_gio=None):
    cua = may["snapshot"].get("cua_so") or []
    dong = [f"{_tieu_de(kho, may, bay_gio)} — {len(cua)} cửa sổ"]
    if not cua:
        dong.append("Chưa có cửa sổ game.")
    for so, cs in enumerate(cua, 1):
        dong.append(_dong_cua_so(cs, so))
    return "\n".join(dong)


def tin_nhom(may):
    cua = may["snapshot"].get("cua_so") or []
    dong = [f"{may['ten']} — nhóm"]
    if not cua:
        dong.append("Chưa có cửa sổ game.")
        return "\n".join(dong)
    for cs in cua:
        ten = cs.get("ten") or "(chưa có tên)"
        tv = [str(x) for x in (cs.get("nhom") or []) if x]
        mo = cs.get("mo_ta_nhom") or ""
        if not tv and not mo:
            dong.append(f"- {ten}: chưa có nhóm")
            continue
        dong.append(f"- {ten}: {mo or 'có nhóm'}")
        if tv:
            dong.append("  " + ", ".join(tv))
    return "\n".join(dong)


def tin_acc(may):
    acc = may["snapshot"].get("acc") or []
    dong = [f"{may['ten']} — {len(acc)} tài khoản"]
    if not acc:
        dong.append("Chưa có tài khoản.")
        return "\n".join(dong)
    for muc in acc:
        loai = _NHAN_LOAI.get(muc.get("loai"), muc.get("loai") or "")
        nv = f" ({muc['nhan_vat']})" if muc.get("nhan_vat") else ""
        bat = "bật" if muc.get("bat") else "tắt"
        dong.append(f"- [{loai}] {muc.get('ten')}{nv} — {bat} — {muc.get('trang_thai') or ''}")
    return "\n".join(dong)


def tin_loi(may):
    loi = [cs for cs in (may["snapshot"].get("cua_so") or []) if cs.get("loi")]
    if not loi:
        return f"{may['ten']}: không có lỗi."
    dong = [f"{may['ten']} — lỗi"]
    for cs in loi:
        dong.append(f"- {cs.get('ten') or 'cửa sổ'}: {cs['loi']}")
    return "\n".join(dong)


def tin_help():
    return (
        "/ds — danh sách máy\n"
        "/ping [tên] — còn báo cáo không\n"
        "/status [tên] — nhân vật đang chạy\n"
        "/nhom [tên] — đội hình\n"
        "/acc [tên] — tài khoản\n"
        "/loi [tên] — lỗi cửa sổ"
    )


def tra_loi(kho, lenh, ten="", bay_gio=None):
    lenh = (lenh or "").lower()
    if lenh in ("help", "start"):
        return tin_help()
    if lenh == "ds":
        return tin_ds(kho, bay_gio)
    if lenh not in _CAN_TEN:
        return "Lệnh không rõ.\n" + tin_help()
    may, loi = _chon(kho, ten, bay_gio)
    if loi:
        return loi
    if lenh == "ping":
        return tin_ping(kho, may, bay_gio)
    if lenh == "status":
        return tin_status(kho, may, bay_gio)
    if lenh == "nhom":
        return tin_nhom(may)
    if lenh == "acc":
        return tin_acc(may)
    return tin_loi(may)
