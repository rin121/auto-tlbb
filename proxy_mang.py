"""
Gán proxy SOCKS5 / HTTP CONNECT cho từng Game.exe qua autohoc_proxy.dll (vùng nhớ chung theo pid).
"""
import ctypes
import hashlib
import mmap
import re
import socket
import struct
import threading
import time
from urllib.parse import urlparse

import psutil

import cau_hinh
from cua_so_game import tim_cua_so_game
from lua_game import FILE_MAP_ALL_ACCESS, nap_dll_duong_dan, kernel32
from thu_muc import THU_MUC_APP

import os

DUONG_DAN_DLL_PROXY = os.path.join(THU_MUC_APP, "dll", "autohoc_proxy.dll")
TEN_DLL_PROXY = "autohoc_proxy.dll"
TEN_DLL_PROXY_MOI = "autohoc_proxy_moi.dll"
AUTOHOC_PROXY_BUILD_ID = 2025102122
PHIEN_DAY_HOOK_LOGIN = 3
_khoa = threading.Lock()
_gan = {}
_cho_bat_proxy = {}
_da_nap_dll = set()
_proxy_da_kich_hoat = set()


def _hash_file(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _nguon_dll_proxy():
    return os.path.normpath(os.path.join(THU_MUC_APP, "..", "..", "dll", TEN_DLL_PROXY))


def chon_dll_proxy_nap():
    """
    Trả về (đường_dan, tên_module) để LoadLibrary — luôn khớp nội dung deploy (tránh moi*.dll cũ).
    """
    import shutil
    thu_muc = os.path.join(THU_MUC_APP, "dll")
    deploy = DUONG_DAN_DLL_PROXY
    nguon = _nguon_dll_proxy()
    if os.path.isfile(nguon) and (not os.path.isfile(deploy)
                                  or os.path.getmtime(nguon) > os.path.getmtime(deploy) + 0.5):
        os.makedirs(thu_muc, exist_ok=True)
        try:
            shutil.copy2(nguon, deploy)
        except OSError:
            pass
    if not os.path.isfile(deploy):
        return deploy, TEN_DLL_PROXY
    return deploy, TEN_DLL_PROXY


def mo_ta_dll_vua_chon():
    dll, ten = chon_dll_proxy_nap()
    if not os.path.isfile(dll):
        return f"{ten} (không thấy file)"
    return f"{ten} (build {AUTOHOC_PROXY_BUILD_ID}, md5 {_hash_file(dll)[:8]}…)"


LOAI_SOCKS5 = 1
LOAI_HTTP = 2


class VungProxy(ctypes.Structure):
    _fields_ = [
        ("phien", ctypes.c_long),
        ("bat", ctypes.c_long),
        ("loai", ctypes.c_long),
        ("port", ctypes.c_long),
        ("host", ctypes.c_char * 256),
        ("user", ctypes.c_char * 128),
        ("mat_khau", ctypes.c_char * 128),
        ("so_lan_ok", ctypes.c_long),
        ("ma_loi", ctypes.c_long),
        ("dich_ip", ctypes.c_long),
        ("dich_port", ctypes.c_long),
        ("cach_hook", ctypes.c_long),
        ("phien_dll", ctypes.c_long),
        ("debug_iat", ctypes.c_long),
        ("debug_hook", ctypes.c_long),
        ("so_lan_thu", ctypes.c_long),
    ]


def ten_vung_chung(pid):
    return f"Local\\AutoHoc_Proxy2_{pid}"


def _cau_hinh_proxy():
    px = cau_hinh.chung().get("proxy") or {}
    return {"bat": bool(px.get("bat")),
            "so_acc_moi_ip": max(1, int(px.get("so_acc_moi_ip") or 4)),
            "danh_sach": px.get("danh_sach") or ""}


def da_bat():
    return _cau_hinh_proxy()["bat"] and bool(doc_ds_proxy(_cau_hinh_proxy()["danh_sach"]))


def doc_ds_proxy(chuoi):
    """Mỗi dòng một proxy. Trả về list dict host, port, loai, user, mat_khau."""
    ket_qua = []
    if not chuoi:
        return ket_qua
    for dong in chuoi.replace("\r", "").split("\n"):
        dong = dong.strip()
        if not dong or dong.startswith("#"):
            continue
        muc = _phan_tich_mot_proxy(dong)
        if muc:
            ket_qua.append(muc)
    return ket_qua


def _phan_tich_mot_proxy(dong):
    loai = LOAI_SOCKS5
    user = mat_khau = ""
    if "://" in dong:
        u = urlparse(dong)
        scheme = (u.scheme or "").lower()
        if scheme in ("http", "https"):
            loai = LOAI_HTTP
        elif scheme.startswith("socks"):
            loai = LOAI_SOCKS5
        host = u.hostname
        port = u.port
        if u.username:
            user = u.username
        if u.password:
            mat_khau = u.password
        if not (host and port):
            return None
        return {"loai": loai, "host": host, "port": int(port), "user": user, "mat_khau": mat_khau}
    phan = dong.split(":")
    if len(phan) == 2:
        host, port = phan[0].strip(), phan[1].strip()
        if not (host and port.isdigit()):
            return None
        return {"loai": loai, "host": host, "port": int(port), "user": "", "mat_khau": ""}
    if len(phan) >= 4:
        host, port, user = phan[0].strip(), phan[1].strip(), phan[2].strip()
        mat_khau = ":".join(phan[3:]).strip()
        if not (host and port.isdigit()):
            return None
        return {"loai": loai, "host": host, "port": int(port), "user": user, "mat_khau": mat_khau}
    return None


def _con_chay(pid):
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


def _loi_dang_nhap(chu):
    from dang_nhap import LoiDangNhap
    return LoiDangNhap(chu)


def _cac_pid_game():
    pid = set()
    for cua_so in tim_cua_so_game():
        if _con_chay(cua_so["pid"]):
            pid.add(cua_so["pid"])
    return pid


def se_gan_proxy_tiep_theo():
    """Bật Nhiều IP: luôn mở game mới (không dùng client rảnh)."""
    return da_bat()


def so_ip_toi_da():
    """Số acc online tối đa theo cấu hình (mỗi proxy × số acc/IP)."""
    cfg = _cau_hinh_proxy()
    so_acc = max(1, cfg["so_acc_moi_ip"])
    if not cfg["bat"]:
        return so_acc
    ds = doc_ds_proxy(cfg["danh_sach"])
    if not ds:
        return so_acc
    return len(ds) * so_acc


def _dem_slot(so_acc, ds_proxy):
    """
    Chỉ đếm client đã gán trong _gan (không đếm Game.exe đang mở song song chưa gán).
    """
    theo_proxy = [0] * len(ds_proxy)
    for p in list(_gan.keys()):
        if not _con_chay(p):
            del _gan[p]
            _cho_bat_proxy.pop(p, None)
            _da_nap_dll.discard(p)
            _proxy_da_kich_hoat.discard(p)
            continue
        kenh = _gan.get(p)
        if isinstance(kenh, int) and 0 <= kenh < len(theo_proxy):
            theo_proxy[kenh] += 1
    return theo_proxy


def _gan_chuoi(buf, ten_truong, data, kich_thuoc):
    """Gán chuỗi vào field c_char_Array của VungProxy (truy cập .host trả về bytes, không gán từng byte)."""
    data = (data or b"")[:kich_thuoc - 1]
    setattr(buf, ten_truong, data + b"\x00" * (kich_thuoc - len(data)))


def _mo_vung(pid, giay_cho=8):
    ten = ten_vung_chung(pid)
    het_han = time.time() + giay_cho
    while time.time() < het_han:
        handle = kernel32.OpenFileMappingW(FILE_MAP_ALL_ACCESS, False, ten)
        if handle:
            kernel32.CloseHandle(handle)
            return mmap.mmap(-1, ctypes.sizeof(VungProxy), tagname=ten)
        time.sleep(0.15)
    return None


def _tao_buf_vung(proxy_bat, muc=None, phien_cu=0):
    """Struct cục bộ — ghi vào mmap bằng copy bytes (tránh from_buffer + close mmap)."""
    buf = VungProxy()
    buf.phien = int(phien_cu) + 1
    buf.phien_dll = AUTOHOC_PROXY_BUILD_ID
    if not (proxy_bat and muc):
        buf.bat = 0
        _gan_chuoi(buf, "host", b"", 256)
        buf.port = 0
        _gan_chuoi(buf, "user", b"", 128)
        _gan_chuoi(buf, "mat_khau", b"", 128)
        buf.loai = LOAI_SOCKS5
    else:
        buf.bat = 1
        buf.loai = int(muc["loai"])
        buf.port = int(muc["port"])
        _gan_chuoi(buf, "host", muc["host"].encode("ascii", "ignore"), 256)
        _gan_chuoi(buf, "user", (muc.get("user") or "").encode("utf-8", "ignore"), 128)
        _gan_chuoi(buf, "mat_khau", (muc.get("mat_khau") or "").encode("utf-8", "ignore"), 128)
    return buf


def _ghi_bytes_vao_mmap(vung, buf):
    raw = ctypes.string_at(ctypes.byref(buf), ctypes.sizeof(buf))
    vung.seek(0)
    vung.write(raw)
    vung.flush()


def _ghi_vung(pid, proxy_bat, muc=None):
    vung = _mo_vung(pid, giay_cho=12)
    if not vung:
        if not _con_chay(pid):
            raise _loi_dang_nhap("Game đã tắt trước khi bật proxy DLL")
        raise _loi_dang_nhap("DLL proxy chưa sẵn sàng (inject thất bại hoặc autohoc_proxy.dll không chạy trong game)")
    try:
        raw_cu = vung.read(ctypes.sizeof(VungProxy))
        phien_cu = struct.unpack_from("l", raw_cu, 0)[0] if len(raw_cu) >= 4 else 0
        buf = _tao_buf_vung(proxy_bat, muc, phien_cu)
        if len(raw_cu) >= 4:
            buf.phien = phien_cu
        if len(raw_cu) >= ctypes.sizeof(VungProxy):
            old = VungProxy.from_buffer_copy(raw_cu)
            buf.so_lan_ok = old.so_lan_ok
            buf.ma_loi = old.ma_loi
            buf.dich_ip = old.dich_ip
            buf.dich_port = old.dich_port
            buf.cach_hook = old.cach_hook
            buf.debug_iat = old.debug_iat
            buf.debug_hook = old.debug_hook
            buf.so_lan_thu = old.so_lan_thu
            if int(old.phien_dll) > 0:
                buf.phien_dll = old.phien_dll
        _ghi_bytes_vao_mmap(vung, buf)
    finally:
        vung.close()


def cho_hook_san_sang(pid, giay_cho=25, in_log=None, yeu_cau_iat=False):
    if not pid or not da_bat():
        return 0
    het_han = time.time() + max(3, giay_cho)
    lan_cuoi = 0
    luc_log = time.time()
    bat_dau = time.time()
    while time.time() < het_han:
        tr = doc_vung_proxy(pid)
        if not tr:
            time.sleep(0.25)
            continue
        hook = int(tr.get("cach_hook") or 0)
        lan_cuoi = hook
        iat = int(tr.get("debug_iat") or 0)
        if int(tr.get("so_lan_ok") or 0) > 0:
            return hook
        bat = int(tr.get("bat") or 0)
        bay_gio = time.time()
        if yeu_cau_iat and not bat:
            if hook >= 2:
                return hook
            if iat >= 1:
                return hook
            if hook >= 3:
                return hook
        elif hook >= 2:
            if bat and hook >= 5 and iat < 1:
                time.sleep(0.35)
                continue
            return hook
        if in_log and bay_gio - luc_log >= (3 if yeu_cau_iat else 10):
            luc_log = bay_gio
            in_log(
                f"Proxy DLL: vẫn chờ hook… cach_hook={hook}, IAT={tr.get('debug_iat', 0)}, "
                f"debug_hook={tr.get('debug_hook', 0)}, phien={tr.get('phien', 0)}, bat={bat}, "
                f"{int(bay_gio - bat_dau)}s")
        time.sleep(0.35)
    return lan_cuoi


def dang_di_proxy(pid):
    kenh = _gan.get(pid)
    return isinstance(kenh, int)


def chuan_bi_proxy_truoc_mang(pid, in_log=None):
    """
    Chỉ nạp DLL + phien=1 (chưa hook). Gắn hook chỉ khi vào màn đăng nhập (_bat_dau_hook_tai_login).
    """
    if not (pid and dang_di_proxy(pid)):
        return
    if not _cho_bat_proxy.get(pid):
        return
    if pid in _da_nap_dll:
        return
    nap_dll_proxy(pid)
    _da_nap_dll.add(pid)
    _ghi_vung(pid, False)
    if in_log:
        in_log(f"DLL proxy: {mo_ta_dll_vua_chon()}")


def bat_proxy_khi_san_sang(pid):
    """Bật SOCKS trong DLL sau khi hook đã sẵn sàng."""
    muc = _cho_bat_proxy.get(pid)
    if not muc:
        return False
    _ghi_vung(pid, True, muc)
    return True


def _nhich_phien_hook(pid):
    vung = _mo_vung(pid, giay_cho=0.3)
    if not vung:
        return
    try:
        raw = bytearray(vung.read(ctypes.sizeof(VungProxy)))
        if len(raw) < 4:
            return
        phien = struct.unpack_from("l", raw, 0)[0]
        struct.pack_into("l", raw, 0, phien + 1)
        vung.seek(0)
        vung.write(bytes(raw))
        vung.flush()
    finally:
        vung.close()


def _tang_phien_mmap(pid, toi_thieu=PHIEN_DAY_HOOK_LOGIN):
    vung = _mo_vung(pid, giay_cho=5)
    if not vung:
        return
    try:
        raw = bytearray(vung.read(ctypes.sizeof(VungProxy)))
        if len(raw) < 4:
            return
        phien = struct.unpack_from("l", raw, 0)[0]
        if phien >= toi_thieu:
            return
        struct.pack_into("l", raw, 0, toi_thieu)
        vung.seek(0)
        vung.write(bytes(raw))
        vung.flush()
    finally:
        vung.close()


def _bat_dau_hook_tai_login(pid):
    """Tăng phien mmap lên >=3 — DLL mới được patch IAT (tránh diss sau chọn máy chủ)."""
    _tang_phien_mmap(pid, PHIEN_DAY_HOOK_LOGIN)


def da_kich_hoat_proxy(pid):
    return pid in _proxy_da_kich_hoat


def chuan_bi_dang_nhap_qua_proxy(pid, giay_cho=50, in_log=None, som=False, sau_splash=False):
    """
    Chờ hook, bật proxy, trả về cach_hook. Raise LoiDangNhap nếu không hook được.
    som=True: legacy — kích hoạt ngay sau mở game (tránh: dễ crash splash).
    sau_splash=True: sau chờ cửa sổ splash — bật hook + SOCKS trước đăng nhập.
    """
    if pid in _proxy_da_kich_hoat:
        tr = doc_vung_proxy(pid) or {}
        return int(tr.get("cach_hook") or 0)
    if pid not in _da_nap_dll:
        chuan_bi_proxy_truoc_mang(pid, in_log=in_log)
    if sau_splash:
        time.sleep(2)
    else:
        time.sleep(1 if som else 5)
    _bat_dau_hook_tai_login(pid)
    if in_log:
        tr = doc_vung_proxy(pid) or {}
        in_log(f"Proxy DLL: chờ hook (phien={tr.get('phien', 0)}, cach_hook={tr.get('cach_hook', 0)}, "
               f"build={tr.get('phien_dll', 0)})")
    cho_hook_san_sang(pid, 6 if sau_splash else 8, in_log=None, yeu_cau_iat=True)
    _tang_phien_mmap(pid, PHIEN_DAY_HOOK_LOGIN + 1)
    if not _con_chay(pid):
        raise _loi_dang_nhap("Game đã tắt trước khi bật proxy")
    if not bat_proxy_khi_san_sang(pid):
        raise _loi_dang_nhap("Chưa gán proxy cho client này")
    time.sleep(4 if sau_splash else 2)
    hook = cho_hook_san_sang(pid, giay_cho, in_log=in_log, yeu_cau_iat=False)
    if hook < 2:
        hook = cho_hook_san_sang(pid, min(20, giay_cho), in_log=in_log, yeu_cau_iat=False)
    if not sau_splash:
        time.sleep(0.5)
    hook = max(hook, int((doc_vung_proxy(pid) or {}).get("cach_hook") or 0))
    if in_log and hook >= 2:
        in_log(f"Proxy DLL: hook sẵn sàng (cach_hook={hook})")
    tr_ok = doc_vung_proxy(pid) or {}
    hook_mmap = int(tr_ok.get("cach_hook") or 0)
    hook = max(hook, hook_mmap)
    if hook < 2 and int(tr_ok.get("bat") or 0):
        if hook_mmap >= 3:
            hook = hook_mmap
    if hook < 2 and not tr_ok.get("so_lan_ok"):
        tr = doc_vung_proxy(pid) or {}
        dbg = tr.get("debug_iat", 0)
        build = tr.get("phien_dll", 0)
        raise _loi_dang_nhap(
            f"Proxy chưa gắn hook (cach_hook={hook}, debug_iat={dbg}, phien={tr.get('phien', 0)}, "
            f"debug_hook={tr.get('debug_hook', 0)}, build_dll={build}). "
            "Xóa dong_goi\\AutoHoc\\dll\\autohoc_proxy_moi*.dll rồi chạy lại AutoHoc.")
    _proxy_da_kich_hoat.add(pid)
    if in_log:
        if sau_splash:
            nhan = "Proxy sau splash"
        elif som:
            nhan = "Proxy sớm (trước splash)"
        else:
            nhan = "Proxy sau bật"
        in_log(f"{nhan}: {tom_tat_proxy(pid)}")
    return hook


def kich_hoat_proxy_sau_splash(pid, giay_cho=40, in_log=None):
    """Sau splash: phien hook + bat=1 — mọi TCP đăng nhập qua SOCKS, không patch WS2 lúc tải game."""
    if not (pid and dang_di_proxy(pid)):
        return 0
    if in_log:
        in_log("Chờ hook proxy (sau splash, trước đăng nhập)…")
    return chuan_bi_dang_nhap_qua_proxy(pid, giay_cho=giay_cho, in_log=in_log, sau_splash=True)


def kich_hoat_proxy_som(pid, giay_cho=40, in_log=None):
    """Client đã qua splash — bật proxy ngay (dùng lại game / client rảnh)."""
    if not (pid and dang_di_proxy(pid)):
        return 0
    if in_log:
        in_log("Chờ hook proxy…")
    return chuan_bi_dang_nhap_qua_proxy(pid, giay_cho=giay_cho, in_log=in_log, som=False)


def mo_ta_trang_thai_hook(pid):
    """Dòng log khi game báo lỗi mạng nhưng hook chưa thấy kết nối qua proxy."""
    tr = doc_vung_proxy(pid)
    if not (tr and tr.get("bat")):
        return ""
    if tr.get("so_lan_ok", 0) > 0:
        return ""
    ma = tr.get("ma_loi", 0)
    hook = tr.get("cach_hook", 0)
    if ma:
        return f"Proxy DLL: lỗi handshake mã {ma} (hook={hook})"
    if hook == 0:
        return "Proxy DLL: hook chưa sẵn sàng (game có thể đăng nhập quá sớm sau inject)"
    if hook >= 3:
        return ""
    if hook == 1:
        return "Proxy DLL: bản cũ (hot-patch connect) — đóng game, cập nhật autohoc_proxy.dll rồi thử lại"
    return f"Proxy DLL: hook IAT={hook}, so_lan_ok=0 — game chưa đi SOCKS (ma_loi={ma}); thử acc khác hoặc proxy khác"


def doc_vung_proxy(pid):
    vung = _mo_vung(pid, giay_cho=0.3)
    if not vung:
        return None
    try:
        raw = vung.read(ctypes.sizeof(VungProxy))
        if len(raw) < ctypes.sizeof(VungProxy):
            return None
        buf = VungProxy.from_buffer_copy(raw)
        host = bytes(buf.host).split(b"\x00")[0].decode("ascii", "replace")
        return {
            "bat": int(buf.bat),
            "loai": int(buf.loai),
            "host": host,
            "port": int(buf.port),
            "phien": int(buf.phien),
            "ma_loi": int(buf.ma_loi),
            "so_lan_ok": int(buf.so_lan_ok),
            "cach_hook": int(buf.cach_hook),
            "phien_dll": int(buf.phien_dll),
            "debug_iat": int(buf.debug_iat),
            "debug_hook": int(buf.debug_hook),
            "so_lan_thu": int(buf.so_lan_thu),
            "dich_ip": int(buf.dich_ip),
            "dich_port": int(buf.dich_port),
        }
    finally:
        vung.close()


def tom_tat_proxy(pid):
    tr = doc_vung_proxy(pid)
    if not tr:
        return "Proxy mmap: không đọc được (game đã thoát?)"
    dich = ""
    dip = int(tr.get("dich_ip") or 0)
    if dip:
        try:
            dich = f", dich_cuoi={socket.inet_ntoa(struct.pack('!I', dip & 4294967295))}:{tr.get('dich_port', 0)}"
        except OSError:
            dich = f", dich_cuoi=0x{dip:x}:{tr.get('dich_port', 0)}"
    return (f"bat={tr.get('bat', 0)}, hook={tr.get('cach_hook', 0)}, IAT={tr.get('debug_iat', 0)}, "
            f"thử_SOCKS={tr.get('so_lan_thu', 0)}, ok={tr.get('so_lan_ok', 0)}, ma_loi={tr.get('ma_loi', 0)}{dich}")


def cho_ket_noi_socks(pid, giay=20, in_log=None):
    """Chờ DLL báo đã gọi connect qua hook (so_lan_thu hoặc so_lan_ok > 0)."""
    if not (pid and dang_di_proxy(pid)):
        return False
    het = time.time() + max(3, giay)
    while time.time() < het:
        tr = doc_vung_proxy(pid) or {}
        if int(tr.get("so_lan_ok") or 0) > 0 or int(tr.get("so_lan_thu") or 0) > 0:
            return True
        time.sleep(0.35)
    if in_log:
        in_log(f"Chưa thấy kết nối SOCKS sau {giay}s — {tom_tat_proxy(pid)}")
    return False


def nap_dll_proxy(pid):
    if not da_bat():
        return False
    dll, ten_dll = chon_dll_proxy_nap()
    if not os.path.isfile(dll):
        raise _loi_dang_nhap(f"Không thấy {dll}")
    for _ in range(12):
        try:
            nap_dll_duong_dan(pid, dll, ten_dll)
        except Exception:
            pass
        if _mo_vung(pid, giay_cho=0.5):
            return True
        time.sleep(0.3)
    raise _loi_dang_nhap("Không nạp được autohoc_proxy.dll vào game (quá lâu chờ vùng nhớ chung)")


def gan_cho(pid):
    """
    Gán proxy còn slot (mọi acc đi SOCKS/HTTP). Nạp DLL + bat=0, bật SOCKS trước đăng nhập server.
    """
    if not da_bat():
        return None
    cfg = _cau_hinh_proxy()
    ds = doc_ds_proxy(cfg["danh_sach"])
    if not ds:
        return None
    so_acc = cfg["so_acc_moi_ip"]
    with _khoa:
        theo_proxy = _dem_slot(so_acc, ds)
        kenh_cu = _gan.get(pid)
        if isinstance(kenh_cu, int) and 0 <= kenh_cu < len(theo_proxy):
            theo_proxy[kenh_cu] -= 1
        muc_proxy = None
        chi_so_proxy = None
        slot_proxy = 0
        for i, muc in enumerate(ds):
            if theo_proxy[i] < so_acc:
                _gan[pid] = i
                chi_so_proxy = i
                muc_proxy = muc
                slot_proxy = theo_proxy[i] + 1
                break
        if muc_proxy is None:
            raise _loi_dang_nhap(f"Hết slot proxy ({len(ds)} proxy × {so_acc} acc/IP), thêm proxy ở tab Tài khoản")
    _cho_bat_proxy[pid] = muc_proxy
    return f"đi qua proxy {chi_so_proxy + 1} ({muc_proxy['host']}:{muc_proxy['port']}), IP này {slot_proxy}/{so_acc} acc"


def nha(pid):
    if not pid:
        return
    with _khoa:
        if pid in _gan:
            del _gan[pid]
        _cho_bat_proxy.pop(pid, None)
        _da_nap_dll.discard(pid)
        _proxy_da_kich_hoat.discard(pid)
    try:
        _ghi_vung(pid, False)
    except Exception:
        pass


def mo_ta_kenh(pid):
    with _khoa:
        kenh = _gan.get(pid)
    if kenh is None:
        return ""
    cfg = _cau_hinh_proxy()
    ds = doc_ds_proxy(cfg["danh_sach"])
    if isinstance(kenh, int) and 0 <= kenh < len(ds):
        p = ds[kenh]
        return f"Proxy {kenh + 1} ({p['host']}:{p['port']})"
    return ""


def _gui_het(sock, data):
    view = memoryview(data)
    da = 0
    while da < len(view):
        n = sock.send(view[da:])
        if n <= 0:
            raise OSError("send")
        da += n


def _nhan_het(sock, n):
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise OSError("recv")
        buf += chunk
    return buf


def _socks5_ket_noi(sock, dich_host, dich_port, user="", mat_khau=""):
    if user:
        sock.sendall(b"\x05\x01\x02")
    else:
        sock.sendall(b"\x05\x01\x00")
    rep = _nhan_het(sock, 2)
    if rep[0] != 5:
        raise OSError("SOCKS5 không hỗ trợ")
    if rep[1] == 2:
        u = user.encode("utf-8")
        p = mat_khau.encode("utf-8")
        sock.sendall(b"\x01" + bytes([len(u)]) + u + bytes([len(p)]) + p)
        rep2 = _nhan_het(sock, 2)
        if rep2[1] != 0:
            raise OSError("SOCKS5 xác thực thất bại")
    elif rep[1] != 0:
        raise OSError(f"SOCKS5 từ chối ({rep[1]})")
    try:
        dip = socket.inet_aton(dich_host)
        atyp = b"\x01"
        dia_chi = dip
    except OSError:
        h = dich_host.encode("idna")
        atyp = b"\x03"
        dia_chi = bytes([len(h)]) + h
    req = b"\x05\x01\x00" + atyp + dia_chi + struct.pack("!H", int(dich_port))
    sock.sendall(req)
    rep3 = _nhan_het(sock, 10)
    if rep3[1] != 0:
        raise OSError(f"SOCKS5 CONNECT thất bại ({rep3[1]})")


def kiem_tra_proxy(muc, giay_cho=12, dich_host=None, dich_port=80):
    host = muc["host"]
    port = int(muc["port"])
    loai = muc.get("loai", LOAI_SOCKS5)
    user = muc.get("user") or ""
    mat_khau = muc.get("mat_khau") or ""
    dich_host = dich_host or "api.ipify.org"
    dich_port = int(dich_port)
    bat_dau = time.time()
    sock = socket.create_connection((host, port), timeout=giay_cho)
    try:
        if loai == LOAI_HTTP:
            yeu_cau = f"CONNECT {dich_host}:{dich_port} HTTP/1.0\r\n"
            if user:
                import base64
                tok = base64.b64encode(f"{user}:{mat_khau}".encode()).decode()
                yeu_cau += f"Proxy-Authorization: Basic {tok}\r\n"
            yeu_cau += "\r\n"
            sock.sendall(yeu_cau.encode())
            phan_hoi = b""
            while b"\r\n\r\n" not in phan_hoi and len(phan_hoi) < 4096:
                phan_hoi += sock.recv(256)
            dong1 = phan_hoi.split(b"\r\n", 1)[0]
            if b"200" not in dong1:
                raise OSError("HTTP CONNECT thất bại")
        else:
            _socks5_ket_noi(sock, dich_host, dich_port, user, mat_khau)
        sock.sendall(
            f"GET / HTTP/1.0\r\nHost: {dich_host}\r\nConnection: close\r\n\r\n".encode())
        data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
        body = data.split(b"\r\n\r\n", 1)[-1].strip()
        chuoi = body.decode("ascii", "replace").strip()
        ip = chuoi.split()[0] if chuoi else "?"
        ms = int((time.time() - bat_dau) * 1000)
        return ip, ms
    finally:
        sock.close()
