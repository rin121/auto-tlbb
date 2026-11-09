"""Gửi snapshot AutoHoc tới bot quản lý. Không gọi Telegram, không gửi mật khẩu."""
import json
import os
import secrets
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from thu_muc import THU_MUC_APP

_THU_MUC_NGUON = os.path.dirname(os.path.abspath(__file__))

PHIEN_BAN = 1
CHU_KY_GUI = 20
CONG_HUB_MAC_DINH = 8787
DUONG_DAN = os.path.join(THU_MUC_APP, "ket_noi_telegram.json")
MAC_DINH = {"bat": False, "ten_may": "", "dia_chi": "", "ma_ket_noi": "", "id_may": ""}


def dam_bao_id_may(gia):
    """ID cố định mỗi máy (lần đầu: mã ngẫu nhiên, không dùng tên PC — tránh clone VM trùng)."""
    gia["id_may"] = str(gia.get("id_may") or "").strip()
    if not gia["id_may"]:
        gia["id_may"] = secrets.token_hex(8)
    if len(gia["id_may"]) > 40:
        gia["id_may"] = gia["id_may"][:40]
    return gia


def lam_moi_id_may(duong_dan=None):
    """Clone VM / copy ket_noi_telegram.json: bấm để hub nhận là máy mới (giữ tên hiển thị)."""
    cau = doc(duong_dan)
    cau["id_may"] = ""
    cau = dam_bao_id_may(cau)
    luu(cau, duong_dan)
    return cau["id_may"]


class LoiGui(Exception):
    pass


def tim_chay_bot_quan_ly():
    """Đường dẫn ChayBotQuanLy.bat nếu máy này có cài bot quản lý (máy chủ)."""
    for thu_muc in (
            THU_MUC_APP,
            os.path.dirname(THU_MUC_APP),
            os.path.normpath(os.path.join(THU_MUC_APP, "..", "..")),
            _THU_MUC_NGUON,
            os.path.dirname(_THU_MUC_NGUON),
    ):
        if not thu_muc:
            continue
        bat = os.path.join(thu_muc, "bot_quan_ly", "ChayBotQuanLy.bat")
        if os.path.isfile(bat):
            return bat
    bat = os.path.join(THU_MUC_APP, "ChayBotQuanLy.bat")
    return bat if os.path.isfile(bat) else None


def _phan_dia_chi_ket_noi(dia_chi):
    chu = chuan_hoa_dia_chi(dia_chi or "")
    if not chu:
        return "127.0.0.1", CONG_HUB_MAC_DINH
    phan = urllib.parse.urlsplit(chu)
    host = phan.hostname or "127.0.0.1"
    cong = phan.port if phan.port is not None else (
        443 if phan.scheme == "https" else CONG_HUB_MAC_DINH)
    return host, cong


def hub_dang_nghe(dia_chi, timeout=0.35):
    """POST /bao-cao có nhận TCP không (không gửi body thật)."""
    host, cong = _phan_dia_chi_ket_noi(dia_chi)
    if host in ("127.0.0.1", "localhost", "::1"):
        try:
            with socket.create_connection((host, cong), timeout=timeout):
                return True
        except OSError:
            return False
    return None


def doc(duong_dan=None):
    duong_dan = duong_dan or DUONG_DAN
    gia = dict(MAC_DINH)
    try:
        with open(duong_dan, encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        return gia
    if not isinstance(raw, dict):
        return gia
    for khoa in MAC_DINH:
        if khoa in raw and raw[khoa] is not None:
            gia[khoa] = raw[khoa]
    gia["bat"] = bool(gia["bat"])
    gia["ten_may"] = str(gia["ten_may"]).strip()
    gia["dia_chi"] = chuan_hoa_dia_chi(gia["dia_chi"])
    gia["ma_ket_noi"] = str(gia["ma_ket_noi"])
    return dam_bao_id_may(gia)


def luu(du_lieu, duong_dan=None):
    duong_dan = duong_dan or DUONG_DAN
    ban = doc_tu_dict(du_lieu)
    with open(duong_dan, "w", encoding="utf-8") as f:
        json.dump(ban, f, ensure_ascii=False, indent=2)


def doc_tu_dict(du_lieu):
    gia = dict(MAC_DINH)
    if isinstance(du_lieu, dict):
        for khoa in MAC_DINH:
            if khoa in du_lieu and du_lieu[khoa] is not None:
                gia[khoa] = du_lieu[khoa]
    gia["bat"] = bool(gia["bat"])
    gia["ten_may"] = str(gia["ten_may"]).strip()
    gia["dia_chi"] = chuan_hoa_dia_chi(gia["dia_chi"])
    gia["ma_ket_noi"] = str(gia["ma_ket_noi"])
    return dam_bao_id_may(gia)


def chuan_hoa_dia_chi(dia_chi):
    """IP/host không kèm http:// hoặc thiếu cổng http → thêm :8787 (cổng bot quản lý)."""
    chu = (dia_chi or "").strip().rstrip("/")
    if not chu:
        return ""
    neu = chu.lower()
    if neu.startswith(("http://", "https://")):
        phan = urllib.parse.urlsplit(chu)
    else:
        phan = urllib.parse.urlsplit(f"http://{chu}")
    if phan.scheme not in ("http", "https") or not phan.hostname:
        return chu
    if phan.path not in ("", "/"):
        return chu
    cong = phan.port
    if cong is None and phan.scheme == "http":
        cong = CONG_HUB_MAC_DINH
    host = phan.hostname
    netloc = host if cong is None else f"{host}:{cong}"
    if phan.username:
        phan_thong_tin = phan.username
        if phan.password:
            phan_thong_tin += f":{phan.password}"
        netloc = f"{phan_thong_tin}@{netloc}"
    chu = urllib.parse.urlunsplit((phan.scheme, netloc, "", "", ""))
    return chu.rstrip("/")


def dia_chi_hop_le(dia_chi):
    dia_chi = chuan_hoa_dia_chi(dia_chi)
    phan = urllib.parse.urlparse(dia_chi or "")
    if phan.scheme not in ("http", "https") or not phan.netloc:
        return False
    if phan.path not in ("", "/"):
        return False
    return not (phan.params or phan.query or phan.fragment)


def ten_hop_le(ten):
    ten = (ten or "").strip()
    if not ten or len(ten) > 40:
        return False
    return not any(ord(c) < 32 for c in ten)


def kiem_tra(cau, bat_buoc=False):
    """ValueError với câu tiếng Việt nếu bật (hoặc bat_buoc) mà thiếu / sai."""
    cau = doc_tu_dict(cau)
    if not cau["bat"] and not bat_buoc:
        return cau
    if not ten_hop_le(cau["ten_may"]):
        raise ValueError("Tên máy trống hoặc dài quá 40 ký tự.")
    if not dia_chi_hop_le(cau["dia_chi"]):
        raise ValueError(
            "Địa chỉ không hợp lệ (vd IP 113.22.183.60, https://….trycloudflare.com). "
            "Không gõ /bao-cao — http tự thêm cổng 8787 nếu thiếu.")
    if not str(cau["ma_ket_noi"]).strip():
        raise ValueError("Chưa nhập mã bí mật.")
    return cau


def mo_ta_auto(co_loi, co_thong_tin, mo_ta_luong, mo_ta_chien_dau, mo_ta_auto_click, bat_auto):
    """Cùng cách ghép cột trạng thái trên bảng nhân vật."""
    if not co_thong_tin:
        if co_loi:
            return "Chưa đọc được game"
        return mo_ta_luong or "Đang kết nối..."
    if co_loi:
        return "Chưa đọc được game"
    ghep = " | ".join(chu for chu in (mo_ta_luong, mo_ta_chien_dau, mo_ta_auto_click) if chu)
    return ghep or ("Đang auto" if bat_auto else "")


def trang_thai_acc(dang_online, ten_online, dang_mo, mo_ta_mo, tam_dung, mo_ta_tam, tu_mo_lai):
    """Cùng nghĩa cột trạng thái bảng tài khoản."""
    if dang_online:
        return f"Đang online ({ten_online})"
    if dang_mo:
        return mo_ta_mo or "Đang mở game"
    if tam_dung:
        return mo_ta_tam or "Tạm dừng"
    if not tu_mo_lai:
        return "Không tự mở lại khi diss"
    return "Chờ mở game"


def cua_so_bao_cao(ten, tai_khoan, map, hp, level, mon_phai, trong_game, mo_ta, loi, nhom, mo_ta_nhom,
                   luot_hom_nay=None):
    """luot_hom_nay: {"pmp", "sat_tinh", "ac_tac"} — số lượt đội trưởng đã đi hôm nay."""
    luot = luot_hom_nay or {}
    return {
        "ten": ten or "",
        "tai_khoan": tai_khoan or "",
        "map": map or "",
        "hp": hp,
        "level": level,
        "mon_phai": mon_phai or "",
        "trong_game": bool(trong_game),
        "mo_ta": mo_ta or "",
        "loi": loi or "",
        "nhom": [str(x) for x in (nhom or []) if x],
        "mo_ta_nhom": mo_ta_nhom or "",
        "luot_hom_nay": {khoa: int(luot.get(khoa) or 0) for khoa in ("pmp", "sat_tinh", "ac_tac")},
    }


def acc_bao_cao(ten, loai, nhan_vat, bat, trang_thai):
    return {
        "ten": ten or "",
        "loai": loai or "",
        "nhan_vat": nhan_vat or "",
        "bat": bool(bat),
        "trang_thai": trang_thai or "",
    }


def hop_snapshot(ten_may, uptime_giay, cua_so, acc, xoay_vong="", tat=False, luc=None, id_may=None, ten_may_cu=None):
    return {
        "phien_ban": PHIEN_BAN,
        "ten_may": ten_may,
        "id_may": id_may or ten_may,
        "ten_may_cu": ten_may_cu or "",
        "luc": time.time() if luc is None else luc,
        "uptime_giay": max(0, int(uptime_giay or 0)),
        "so_cua_so": len(cua_so or []),
        "tat": bool(tat),
        "cua_so": list(cua_so or []),
        "acc": list(acc or []),
        "xoay_vong": xoay_vong or "",
    }


def gui_bao_cao(dia_chi, ma, snapshot, timeout=10):
    url = dia_chi.rstrip("/") + "/bao-cao"
    data = json.dumps(snapshot, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-Ma-Ket-Noi": ma,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status not in (200, 204):
                raise LoiGui(f"HTTP {resp.status}")
    except urllib.error.HTTPError as loi:
        raise LoiGui(f"HTTP {loi.code}") from loi
    except urllib.error.URLError as loi:
        raise LoiGui(str(loi.reason)) from loi


class LuongBaoCao:
    """Thread nền chỉ POST bản snapshot luồng UI đã ghi. Không đọc Tk."""

    def __init__(self, lay_cau_hinh, bao_log):
        self._lay_cau_hinh = lay_cau_hinh
        self._bao_log = bao_log
        self._khoa = threading.Lock()
        self._khoa_gui = threading.Lock()
        self._snapshot = None
        self._dung = threading.Event()
        self._thread = None
        self._the_he = 0
        self._ngung = True
        self._loi_dang_bao = False

    def dang_chay(self):
        return not self._ngung and self._thread is not None and self._thread.is_alive()

    def cap_nhat_snapshot(self, snapshot):
        with self._khoa:
            self._snapshot = snapshot

    def bat(self):
        self._ngung = False
        self._loi_dang_bao = False
        self._the_he += 1
        the = self._the_he
        if self._thread and self._thread.is_alive():
            self._dung.set()
        self._dung = threading.Event()
        self._thread = threading.Thread(
            target=self._chay, args=(the, self._dung), name="bao-cao-telegram", daemon=True)
        self._thread.start()

    def dung(self):
        self._ngung = True
        self._dung.set()

    def gui_tat(self, snapshot, timeout=5):
        """Gọi trên luồng UI lúc thoát, sau dung(). Chờ lượt gửi đang chạy rồi báo tắt."""
        self.dung()
        cau = self._lay_cau_hinh()
        if not cau.get("bat"):
            return
        snap = dict(snapshot)
        snap["tat"] = True
        with self._khoa_gui:
            try:
                gui_bao_cao(cau["dia_chi"], cau["ma_ket_noi"], snap, timeout=timeout)
            except LoiGui as loi:
                self._bao_log(f"Không báo được lúc tắt: {loi}")

    def _chay(self, the, dung):
        while not dung.is_set() and the == self._the_he and not self._ngung:
            self._gui_mot_lan()
            dung.wait(CHU_KY_GUI)

    def _gui_mot_lan(self):
        if self._ngung:
            return
        cau = self._lay_cau_hinh()
        if not cau.get("bat"):
            return
        with self._khoa:
            snap = self._snapshot
        if not snap:
            return
        with self._khoa_gui:
            if self._ngung:
                return
            try:
                gui_bao_cao(cau["dia_chi"], cau["ma_ket_noi"], snap, timeout=10)
            except LoiGui as loi:
                if not self._loi_dang_bao:
                    self._loi_dang_bao = True
                    self._bao_log(f"Báo cáo Telegram lỗi: {loi}")
                return
        if self._loi_dang_bao:
            self._loi_dang_bao = False
            self._bao_log("Báo cáo Telegram đã gửi lại được.")
