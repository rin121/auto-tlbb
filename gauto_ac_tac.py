"""
Điều khiển tab Nhiệm vụ / Ác Tặc trên cửa sổ ChickenAuto (GAuto) quản lý.

ChickenAuto / GAuto 2.x dùng Qt một HWND — không có UIA/child window. Bấm chuột thật theo toạ độ client
(tỉ lệ % kích thước cửa sổ). Có hai profile: ChickenAuto ver.116 vs GAuto TLBB-2.5 (tab Nhiệm vụ giữa pane).
"""
import ctypes
import os
import re
import time

import psutil

from cua_so_game import bat_dpi_awareness, chup_cua_so

bat_dpi_awareness()
import win32api
import win32con
import win32gui
import win32process

from keo_tha import KHOA_CHUOT, LoiKeoTha, _len_truoc

PHUT_MAC_DINH = 30
MAU_CUA_SO_CHICKEN = re.compile(r"^ChickenAuto \(ver\.\d+\)$")
# GAuto 2.x (gameautopro): «GAuto TLBB-2.5.3.3 | …» — không trùng tiêu đề game «… - ChickenAuto».
MAU_CUA_SO_GAUTO = re.compile(r"^GAuto\b", re.I)
CAC_TEN_EXE_GAUTO = ("GAuto_2025.exe", "GAuto.exe", "GAuto.bin", "ChickenAuto.exe", "ChickenAuto.bin")
CAC_TEN_EXE_GAUTO_TLBB = ("GAuto_2025.exe", "GAuto.exe", "GAuto.bin")
CAC_TEN_EXE_CHICKEN = ("ChickenAuto.exe", "ChickenAuto.bin")

# Toạ độ client (x%, y%) — calibrate theo HWND (xem TOA_DO_CHICKEN / TOA_DO_GAUTO25).
KICH_THUOC_CHICKEN = (360, 700)
KICH_THUOC_GAUTO25 = (380, 640)

TOA_DO_CHICKEN = {
    # ~360x700 — tab Nhiệm vụ ở thanh dưới.
    "tab_nhiem_vu": (0.76, 0.955),
    "dong_nhan_vat_y0": 0.10,
    "buoc_dong": 0.038,
    "cot_dong": 0.22,
    "check_ac_tac": (0.06, 0.54),
    "check_chay_pathpoints": (0.06, 0.60),
    "check_cho_party": (0.50, 0.60),
    "check_tu_tim": (0.06, 0.66),
    "combo_map": (0.62, 0.54),
}

# GAuto TLBB-2.5.x (~365x611): bảng nhân vật trên, tab Nhiệm vụ giữa (calibrate từ UI thật).
TOA_DO_GAUTO25 = {
    "tab_nhiem_vu": (0.60, 0.38),
    "dong_nhan_vat_y0": 0.126,
    "buoc_dong": 0.036,
    "cot_dong": 0.22,
    "check_ac_tac": (0.04, 0.50),
    "check_chay_pathpoints": (0.04, 0.57),
    "check_chay_tim": (0.60, 0.55),
    "check_tu_tim": (0.55, 0.565),
    "check_cho_party": (0.50, 0.525),
    "combo_map": (0.32, 0.54),
}

TOA_DO = TOA_DO_CHICKEN  # giữ tên cũ cho import/tests


def _la_gauto_25(hwnd):
    try:
        tieu_de = win32gui.GetWindowText(hwnd) or ""
    except win32gui.error:
        return False
    return bool(MAU_CUA_SO_GAUTO.match(tieu_de) and " - ChickenAuto" not in tieu_de)


def _toa_do(hwnd):
    return TOA_DO_GAUTO25 if _la_gauto_25(hwnd) else TOA_DO_CHICKEN


def _kich_thuoc_chuan_bi(hwnd):
    return KICH_THUOC_GAUTO25 if _la_gauto_25(hwnd) else KICH_THUOC_CHICKEN


class LoiGautoAcTac(Exception):
    pass


def la_cua_so_quan_ly_gauto(tieu_de):
    tieu_de = (tieu_de or "").strip()
    if not tieu_de:
        return False
    if MAU_CUA_SO_CHICKEN.match(tieu_de):
        return True
    if MAU_CUA_SO_GAUTO.match(tieu_de) and " - ChickenAuto" not in tieu_de:
        return True
    return False


def _cau_hinh_muon_gauto_tlbb(duong_dan):
    """Đường dẫn cấu hình trỏ GAuto TLBB 2.x — không dùng cửa sổ ChickenAuto."""
    raw = (duong_dan or "").strip()
    if not raw:
        return False
    ten = os.path.basename(os.path.abspath(raw)).lower()
    if ten.startswith("gauto"):
        return True
    if "chickenauto" in ten:
        return False
    # Thư mục GAuto_2025, AutoTLBB có GAuto_2025.exe — ưu tiên GAuto khi quét thư mục.
    if os.path.isdir(os.path.abspath(raw)):
        for ten_exe in CAC_TEN_EXE_GAUTO_TLBB:
            if os.path.isfile(os.path.join(os.path.abspath(raw), ten_exe)):
                return True
    return False


def _danh_sach_exe_tim(duong_dan):
    if _cau_hinh_muon_gauto_tlbb(duong_dan):
        return CAC_TEN_EXE_GAUTO_TLBB
    raw = (duong_dan or "").strip().lower()
    if "chickenauto" in os.path.basename(raw):
        return CAC_TEN_EXE_CHICKEN
    return CAC_TEN_EXE_GAUTO


def tom_tat_cua_so(hwnd):
    try:
        return (win32gui.GetWindowText(hwnd) or "").strip() or f"hwnd {hwnd}"
    except win32gui.error:
        return f"hwnd {hwnd}"


def _chuan_hoa_duong_dan(duong_dan):
    if not (duong_dan or "").strip():
        return ""
    p = os.path.abspath(duong_dan.strip())
    if os.path.isfile(p):
        return p
    if os.path.isdir(p):
        for ten in _danh_sach_exe_tim(duong_dan):
            duong = os.path.join(p, ten)
            if os.path.isfile(duong):
                return duong
    for hau in (".exe", ".bin"):
        if not p.lower().endswith(hau):
            thu = p + hau
            if os.path.isfile(thu):
                return thu
    raise LoiGautoAcTac(f"không tìm thấy file GAuto: {duong_dan}")


def _khop_duong_dan_gauto(duong_cau_hinh, exe_chay):
    if not exe_chay:
        return False
    cau = os.path.normcase(os.path.abspath(duong_cau_hinh))
    chay = os.path.normcase(exe_chay)
    if cau == chay:
        return True
    for a, b in ((cau, chay), (cau.replace(".exe", ".bin"), chay), (cau, chay.replace(".exe", ".bin"))):
        if a == b:
            return True
    thu_muc = os.path.dirname(cau)
    if thu_muc and thu_muc == os.path.dirname(chay):
        ten_cau, ten_chay = os.path.basename(cau).lower(), os.path.basename(chay).lower()
        if ten_cau.startswith("gauto") and ten_chay.startswith("gauto"):
            return True
        if "chickenauto" in ten_cau and "chickenauto" in ten_chay:
            return True
    return False


def _exe_cua_pid(pid):
    try:
        return os.path.normcase(psutil.Process(pid).exe())
    except (psutil.Error, OSError):
        return None


def tim_cua_so_quan_ly(duong_dan_gauto):
    """HWND cửa sổ quản lý — khớp exe cấu hình; GAuto_2025.exe chỉ bấm cửa sổ «GAuto TLBB…», không ChickenAuto."""
    muc_tieu = _chuan_hoa_duong_dan(duong_dan_gauto)
    muon_gauto = _cau_hinh_muon_gauto_tlbb(duong_dan_gauto)
    ket_qua = []

    def duyet(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        tieu_de = (win32gui.GetWindowText(hwnd) or "").strip()
        if muon_gauto:
            if not MAU_CUA_SO_GAUTO.match(tieu_de) or " - ChickenAuto" in tieu_de:
                return True
        elif not MAU_CUA_SO_CHICKEN.match(tieu_de):
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        exe = _exe_cua_pid(pid)
        if _khop_duong_dan_gauto(muc_tieu, exe):
            ket_qua.append(hwnd)
        return True

    win32gui.EnumWindows(duyet, None)
    if ket_qua:
        if muon_gauto:
            uu_tien = [h for h in ket_qua if _la_gauto_25(h)]
            return (uu_tien or ket_qua)[0]
        return ket_qua[0]
    if muon_gauto:
        raise LoiGautoAcTac(
            "chưa thấy cửa sổ GAuto TLBB (tiêu đề «GAuto …») — mở GAuto_2025, kiểm tra đường dẫn .exe trong cài Ác Tặc; "
            "không dùng ChickenAuto"
        )
    raise LoiGautoAcTac(
        "chưa thấy cửa sổ ChickenAuto quản lý (kiểm tra đường dẫn .exe trong cài Ác Tặc)"
    )


def _kich_thuoc_client(hwnd):
    l, t, r, b = win32gui.GetClientRect(hwnd)
    return r - l, b - t


def _vung_man_hinh_ao():
    user32 = ctypes.windll.user32
    return (
        user32.GetSystemMetrics(76),
        user32.GetSystemMetrics(77),
        user32.GetSystemMetrics(78),
        user32.GetSystemMetrics(79),
    )


def _ep_toa_do_man_hinh(sx, sy):
    vx, vy, vw, vh = _vung_man_hinh_ao()
    x1 = vx + max(vw, 1) - 1
    y1 = vy + max(vh, 1) - 1
    return max(vx, min(x1, int(sx))), max(vy, min(y1, int(sy)))


def _dat_con_tro_man_hinh(sx, sy):
    sx, sy = _ep_toa_do_man_hinh(sx, sy)
    for _ in range(4):
        try:
            win32api.SetCursorPos((sx, sy))
            return True
        except win32api.error:
            time.sleep(0.06)
    return False


def _bam_sendmessage(hwnd, x, y):
    """GAuto/ChickenAuto Qt — bấm qua message khi SetCursorPos bị Windows chặn."""
    lparam = win32api.MAKELONG(int(x) & 0xFFFF, int(y) & 0xFFFF)
    win32gui.SendMessage(hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    win32gui.SendMessage(hwnd, win32con.WM_LBUTTONUP, 0, lparam)


def _dua_cua_so_vao_man_hinh(hwnd, rong, cao):
    vx, vy, vw, vh = _vung_man_hinh_ao()
    x1 = vx + max(vw, 1) - 1
    y1 = vy + max(vh, 1) - 1
    l, t, _, _ = win32gui.GetWindowRect(hwnd)
    r = l + rong
    b = t + cao
    if r < vx or b < vy or l > x1 or t > y1:
        l, t = vx + 20, vy + 20
    l = max(vx, min(l, max(vx, x1 - rong + 1)))
    t = max(vy, min(t, max(vy, y1 - cao + 1)))
    win32gui.MoveWindow(hwnd, l, t, rong, cao, True)


def _tien_trinh_admin(pid):
    """True/False theo token elevated; None nếu không đọc được."""
    import ctypes.wintypes as wt

    k32, adv = ctypes.windll.kernel32, ctypes.windll.advapi32
    handle = k32.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    token = wt.HANDLE()
    try:
        if not adv.OpenProcessToken(handle, 0x0008, ctypes.byref(token)):
            return None
        try:
            gia_tri, can = wt.DWORD(), wt.DWORD()
            if not adv.GetTokenInformation(token, 20, ctypes.byref(gia_tri), 4, ctypes.byref(can)):
                return None
            return bool(gia_tri.value)
        finally:
            k32.CloseHandle(token)
    finally:
        k32.CloseHandle(handle)


def kiem_tra_quyen(hwnd):
    """Windows chặn chuột / tin nhắn từ app thường vào app chạy Admin (UIPI)."""
    pid_gauto = win32process.GetWindowThreadProcessId(hwnd)[1]
    if _tien_trinh_admin(pid_gauto) and not _tien_trinh_admin(os.getpid()):
        raise LoiGautoAcTac(
            "GAuto đang chạy quyền Admin còn AutoHoc thì không — Windows chặn AutoHoc bấm vào GAuto. "
            "Tắt AutoHoc, chuột phải AutoHoc.exe → Run as administrator (hoặc chạy GAuto không Admin)"
        )


def _diem(hwnd, xy):
    if isinstance(xy[0], float):
        w, h = _kich_thuoc_client(hwnd)
        return int(xy[0] * w), int(xy[1] * h)
    return xy


def bam_client(hwnd, xy):
    """Bấm chuột trái (client) — không dùng keo_tha.bam vì cửa sổ GAuto có thể bị che một phần."""
    if not (hwnd and win32gui.IsWindow(hwnd)):
        raise LoiGautoAcTac("cửa sổ GAuto không còn mở")
    x, y = _diem(hwnd, xy)
    with KHOA_CHUOT:
        cu_truoc, cu_chuot = win32gui.GetForegroundWindow(), win32api.GetCursorPos()
        try:
            try:
                _len_truoc(hwnd)
            except LoiKeoTha:
                pass
            a = win32gui.ClientToScreen(hwnd, (x, y))
            if _dat_con_tro_man_hinh(a[0], a[1]):
                time.sleep(0.12)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                time.sleep(0.12)
            else:
                _bam_sendmessage(hwnd, x, y)
                time.sleep(0.12)
        except win32api.error as loi:
            try:
                _bam_sendmessage(hwnd, x, y)
                time.sleep(0.12)
            except win32gui.error:
                raise LoiGautoAcTac(
                    f"không bấm được cửa sổ GAuto (chuột / cửa sổ: {loi})"
                ) from loi
        finally:
            try:
                win32api.SetCursorPos(cu_chuot)
            except win32api.error:
                pass
            if cu_truoc and cu_truoc != hwnd and win32gui.IsWindow(cu_truoc):
                try:
                    _len_truoc(cu_truoc)
                except Exception:
                    pass


def _trang_thai_check(hwnd, xy):
    """Đoán checkbox đang bật: lấy mẫu vùng nhỏ quanh toạ độ (màu xanh GAuto)."""
    from PIL import ImageGrab

    x, y = _diem(hwnd, xy)
    sx, sy = win32gui.ClientToScreen(hwnd, (x, y))
    anh = ImageGrab.grab(bbox=(sx - 4, sy - 4, sx + 12, sy + 12))
    pixels = list(anh.getdata())
    # Checkbox bật thường có pixel xanh dương đậm (#2d6 / tương tự).
    xanh = sum(1 for r, g, b in pixels if b > 120 and g > 80 and r < 100)
    return xanh >= 3


def _dat_check(hwnd, xy, bat):
    dang_bat = _trang_thai_check(hwnd, xy)
    if dang_bat != bat:
        bam_client(hwnd, xy)
        time.sleep(0.15)


def chon_dong_nhan_vat(hwnd, chi_so=0):
    """Chọn dòng trong bảng nhân vật (0 = dòng đầu)."""
    td = _toa_do(hwnd)
    x = td["cot_dong"]
    y = td["dong_nhan_vat_y0"] + chi_so * td["buoc_dong"]
    bam_client(hwnd, (x, y))
    time.sleep(0.2)


def _dong_dang_chon(hwnd, chi_so):
    """Dòng chi_so có nền xanh (đang chọn) trong bảng nhân vật."""
    td = _toa_do(hwnd)
    img = chup_cua_so(hwnd)
    w, h = img.size
    y = int((td["dong_nhan_vat_y0"] + chi_so * td["buoc_dong"]) * h) + 4
    x = max(4, int(w * 0.04))
    r, g, b = img.getpixel((x, y))[:3]
    return b > 130 and g > 70 and r < 110


def _ocr_crop_ten(crop):
    import io

    from giai_captcha import _lay_ocr

    ocr = _lay_ocr()
    buf = io.BytesIO()
    crop.convert("RGB").save(buf, format="PNG")
    return (ocr.classification(buf.getvalue()) or "").strip()


def _ten_khop_doc(ocr_chu, ten_nv):
    from auto_chuyen_sinh import chuan_hoa
    from dang_nhap import bo_dau

    a = bo_dau(chuan_hoa(ten_nv))
    b = bo_dau(chuan_hoa(ocr_chu))
    if not a or not b:
        return False
    return a in b or b in a or a[:4] in b or b[:4] in a


def tim_chi_so_dong_theo_ten(hwnd, ten_nv, cache=None):
    """Tìm dòng bảng GAuto có tên nhân vật (đội trưởng), cache dict ten->chi_so."""
    from auto_chuyen_sinh import chuan_hoa

    khoa = chuan_hoa(ten_nv)
    if cache is not None and khoa in cache:
        return cache[khoa]
    kiem_tra_quyen(hwnd)
    _chuan_bi_cua_so(hwnd)
    for i in range(24):
        chon_dong_nhan_vat(hwnd, i)
        time.sleep(0.22)
        if not _dong_dang_chon(hwnd, i):
            continue
        td = _toa_do(hwnd)
        img = chup_cua_so(hwnd)
        w, h = img.size
        y0 = int(td["dong_nhan_vat_y0"] * h) + i * int(td["buoc_dong"] * h)
        dy = int(td["buoc_dong"] * h) + 2
        crop = img.crop((0, max(0, y0 - 1), int(w * 0.58), min(h, y0 + dy)))
        try:
            chu = _ocr_crop_ten(crop)
        except Exception:
            chu = ""
        if _ten_khop_doc(chu, ten_nv):
            if cache is not None:
                cache[khoa] = i
            return i
    raise LoiGautoAcTac(f"không tìm dòng GAuto cho nhân vật «{ten_nv}» (kiểm tra bảng quản lý GAuto)")


def _chuan_bi_cua_so(hwnd):
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        rong, cao = _kich_thuoc_chuan_bi(hwnd)
        _dua_cua_so_vao_man_hinh(hwnd, rong, cao)
        time.sleep(0.2)
    except win32gui.error:
        pass


def chon_tab_nhiem_vu(hwnd):
    _chuan_bi_cua_so(hwnd)
    td = _toa_do(hwnd)
    bam_client(hwnd, td["tab_nhiem_vu"])
    time.sleep(0.2)
    if not _la_gauto_25(hwnd):
        bam_client(hwnd, (0.88, 0.40))
        time.sleep(0.2)


def _dan_ten_vao_clipboard(chuoi):
    import win32clipboard

    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, chuoi)
    finally:
        win32clipboard.CloseClipboard()


def _go_phim(*ma_phim):
    for vk, up in ma_phim:
        win32api.keybd_event(vk, 0, 0 if not up else win32con.KEYEVENTF_KEYUP, 0)


def _chon_map_combo(hwnd, ten_map):
    """Chọn map trong combobox (bấm combo, dán tên map)."""
    bam_client(hwnd, _toa_do(hwnd)["combo_map"])
    time.sleep(0.2)
    _dan_ten_vao_clipboard(ten_map)
    _go_phim((win32con.VK_CONTROL, False), (ord("V"), False), (ord("V"), True),
             (win32con.VK_CONTROL, True))
    time.sleep(0.15)
    _go_phim((win32con.VK_RETURN, False), (win32con.VK_RETURN, True))
    time.sleep(0.2)


def dat_cai_dat_ac_tac(hwnd, at, ten_nv, chi_so_dong=None, cache=None):
    """
    Bật Ác Tặc trên GAuto: chọn dòng ten_nv (đội trưởng), tab Nhiệm vụ, map đầu trong map_uu_tien.
    """
    kiem_tra_quyen(hwnd)
    _chuan_bi_cua_so(hwnd)
    if chi_so_dong is None:
        chi_so_dong = tim_chi_so_dong_theo_ten(hwnd, ten_nv, cache)
    chon_dong_nhan_vat(hwnd, chi_so_dong)
    chon_tab_nhiem_vu(hwnd)
    td = _toa_do(hwnd)
    maps = at.get("map_uu_tien") or []
    if maps:
        _chon_map_combo(hwnd, maps[0])
    chay_pp = bool(at.get("chay_pathpoints"))
    _dat_check(hwnd, td["check_chay_pathpoints"], chay_pp)
    if "check_chay_tim" in td:
        _dat_check(hwnd, td["check_chay_tim"], not chay_pp)
    _dat_check(hwnd, td["check_cho_party"], bool(at.get("cho_party", True)))
    _dat_check(hwnd, td["check_tu_tim"], bool(at.get("tu_tim", True)))
    _dat_check(hwnd, td["check_ac_tac"], True)


def tat_ac_tac(hwnd, ten_nv, chi_so_dong=None, cache=None):
    kiem_tra_quyen(hwnd)
    _chuan_bi_cua_so(hwnd)
    if chi_so_dong is None:
        chi_so_dong = tim_chi_so_dong_theo_ten(hwnd, ten_nv, cache)
    chon_dong_nhan_vat(hwnd, chi_so_dong)
    chon_tab_nhiem_vu(hwnd)
    _dat_check(hwnd, _toa_do(hwnd)["check_ac_tac"], False)


def phut_gauto(at):
    gia_tri = at.get("phut_gauto")
    if gia_tri is None or gia_tri == "":
        gia_tri = PHUT_MAC_DINH
    try:
        p = int(gia_tri)
    except (TypeError, ValueError):
        p = PHUT_MAC_DINH
    return max(1, min(p, 120))
