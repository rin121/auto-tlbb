"""
Điều khiển Ác Tặc trên cửa sổ GAuto TLBB 2.5 (GAuto_2025.exe, ứng dụng WinForms 32-bit) — không bấm chuột thật:
    Bảng nhân vật   : SysListView32 con trực tiếp của cửa sổ chính; MSAA: phần tử con 1..n tên "caychay10 (TL/123)",
                      accSelect chọn dòng (GAuto đổi cả tab cài đặt sang nhân vật đó).
    Tab cài đặt     : SysTabControl32; tab chỉ tạo control khi mở lần đầu. Chuyển tab bằng phím mũi tên gửi thẳng vào
                      thanh tab (MSAA "Switch" và lệnh TCM_SETCURSEL không làm GAuto đổi trang).
    Khung Ác Tặc    : trong trang "Nhiệm vụ", các ô tích cùng một khung với ô "Ác Tặc": "Chạy tìm", "Tự tìm",
                      "Chờ party (chống kẹt)", "Chạy pathpoints"; ô tích WinForms tự vẽ nên BM_GETCHECK luôn 0,
                      đọc / bấm bằng MSAA (trạng thái CHECKED, hành động mặc định Check / Uncheck).
    Map             : ô COMBOBOX trong khung, GAuto lưu riêng từng nhân vật. Đổi bằng lệnh (CB_SETCURSEL, phím gửi
                      thẳng) thì GAuto trả lại map cũ, nên chọn bằng chuột thật: đưa GAuto lên trước, bấm nút thả
                      xuống, bấm dòng map (~1 giây, người dùng đừng động chuột), đọc lại CB_GETCURSEL / CB_GETLBTEXT.
GAuto tự nâng quyền Admin khi mở, Windows chặn app thường điều khiển app Admin: AutoHoc phải chạy quyền Admin.
"""
import contextlib
import ctypes
import os
import re
import sys
import time

import psutil
import win32api
import win32con
import win32gui
import win32process

import msaa
from keo_tha import KHOA_CHUOT, LoiKeoTha, _len_truoc

PHUT_MAC_DINH = 30
MAU_CUA_SO_CHICKEN = re.compile(r"^ChickenAuto \(ver\.\d+\)$")
# GAuto 2.x (gameautopro): «GAuto TLBB-2.5.3.3 | …» — không trùng tiêu đề game «… - ChickenAuto».
MAU_CUA_SO_GAUTO = re.compile(r"^GAuto\b", re.I)
CAC_TEN_EXE_GAUTO = ("GAuto_2025.exe", "GAuto.exe", "GAuto.bin", "ChickenAuto.exe", "ChickenAuto.bin")
CAC_TEN_EXE_GAUTO_TLBB = ("GAuto_2025.exe", "GAuto.exe", "GAuto.bin")
CAC_TEN_EXE_CHICKEN = ("ChickenAuto.exe", "ChickenAuto.bin")

TAB_NHIEM_VU = "Nhiệm vụ"
O_AC_TAC = "Ác Tặc"
O_CHAY_TIM = "Chạy tìm"
O_TU_TIM = "Tự tìm"
O_CHO_PARTY = "Chờ party (chống kẹt)"
O_CHAY_PATHPOINTS = "Chạy pathpoints"
CAC_O_KHUNG_AC_TAC = (O_AC_TAC, O_CHAY_TIM, O_TU_TIM, O_CHO_PARTY, O_CHAY_PATHPOINTS)
TCM_GETCURSEL = 0x130B
LB_GETTOPINDEX = 0x018E
GIAY_CHO_DOI_NHAN_VAT = 0.8
# Ngay sau khi đổi map GAuto bận lưu cài đặt, chọn dòng có lúc vài giây mới ăn.
GIAY_CHO_CHON_DONG = 6
GIAY_CHO_CHON_MSAA = 1.5
GIAY_CHO_THA_XUONG = 1.5
GIAY_GIUA_PHIM_TAB = 0.35
GIAY_CHO_O_TICH = 2.0


class LoiGautoAcTac(Exception):
    pass


def la_cua_so_quan_ly_gauto(tieu_de):
    tieu_de = (tieu_de or "").strip()
    if not tieu_de:
        return False
    if MAU_CUA_SO_CHICKEN.match(tieu_de):
        return True
    return bool(MAU_CUA_SO_GAUTO.match(tieu_de) and " - ChickenAuto" not in tieu_de)


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
    if os.path.isdir(os.path.abspath(raw)):
        return any(os.path.isfile(os.path.join(os.path.abspath(raw), t)) for t in CAC_TEN_EXE_GAUTO_TLBB)
    return False


def _danh_sach_exe_tim(duong_dan):
    if _cau_hinh_muon_gauto_tlbb(duong_dan):
        return CAC_TEN_EXE_GAUTO_TLBB
    if "chickenauto" in os.path.basename((duong_dan or "").strip().lower()):
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
            if os.path.isfile(os.path.join(p, ten)):
                return os.path.join(p, ten)
    for hau in (".exe", ".bin"):
        if not p.lower().endswith(hau) and os.path.isfile(p + hau):
            return p + hau
    raise LoiGautoAcTac(f"không tìm thấy file GAuto: {duong_dan}")


def _khop_duong_dan_gauto(duong_cau_hinh, exe_chay):
    if not exe_chay:
        return False
    cau = os.path.normcase(os.path.abspath(duong_cau_hinh))
    chay = os.path.normcase(exe_chay)
    if chay in (cau, cau.replace(".exe", ".bin")) or cau == chay.replace(".exe", ".bin"):
        return True
    if os.path.dirname(cau) and os.path.dirname(cau) == os.path.dirname(chay):
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
    """HWND cửa sổ quản lý — khớp exe cấu hình; GAuto_2025.exe chỉ nhận cửa sổ «GAuto TLBB…», không ChickenAuto."""
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
        if _khop_duong_dan_gauto(muc_tieu, _exe_cua_pid(pid)):
            ket_qua.append(hwnd)
        return True

    win32gui.EnumWindows(duyet, None)
    if ket_qua:
        # Cửa sổ chính có bảng nhân vật (cửa sổ phụ «GAuto TLBB - 2.5…» ẩn thì không có).
        return next((h for h in ket_qua if _bang_nhan_vat(h, bat_buoc=False)), ket_qua[0])
    if muon_gauto:
        raise LoiGautoAcTac("chưa thấy cửa sổ GAuto TLBB (tiêu đề «GAuto …») — mở GAuto_2025, kiểm tra đường dẫn .exe "
                            "trong cài Ác Tặc")
    raise LoiGautoAcTac("chưa thấy cửa sổ ChickenAuto quản lý (kiểm tra đường dẫn .exe trong cài Ác Tặc)")


# ---------- quyền ----------

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


def autohoc_la_admin():
    return bool(_tien_trinh_admin(os.getpid()))


def gauto_la_admin(hwnd):
    return bool(_tien_trinh_admin(win32process.GetWindowThreadProcessId(hwnd)[1]))


THONG_BAO_CAN_ADMIN = ("GAuto đang chạy quyền Admin (GAuto tự nâng quyền khi mở) còn AutoHoc thì không — Windows chặn "
                       "AutoHoc điều khiển GAuto. Tắt AutoHoc, chuột phải AutoHoc.exe → Run as administrator "
                       "(hoặc bấm «Test GAuto» → Có để mở lại AutoHoc quyền Admin)")


def kiem_tra_quyen(hwnd):
    if gauto_la_admin(hwnd) and not autohoc_la_admin():
        raise LoiGautoAcTac(THONG_BAO_CAN_ADMIN)


def chay_lai_quyen_admin():
    """Mở lại AutoHoc quyền Admin (hộp UAC). True nếu đã mở, người gọi tự đóng bản đang chạy."""
    if getattr(sys, "frozen", False):
        exe, tham_so = sys.executable, ""
    else:
        exe, tham_so = sys.executable, " ".join(f'"{a}"' for a in [os.path.abspath(sys.argv[0])] + sys.argv[1:])
    kq = ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, tham_so, os.getcwd(), 1)
    return kq > 32


# ---------- control ----------

def _cac_con(hwnd):
    ds = []
    try:
        win32gui.EnumChildWindows(hwnd, lambda c, _: ds.append(c) or True, None)
    except win32gui.error:
        pass
    return ds


def _con_truc_tiep(hwnd, lop):
    return [c for c in _cac_con(hwnd) if win32gui.GetParent(c) == hwnd and lop in win32gui.GetClassName(c)]


def _bang_nhan_vat(hwnd, bat_buoc=True):
    ds = _con_truc_tiep(hwnd, "SysListView32")
    if not ds and bat_buoc:
        raise LoiGautoAcTac("không thấy bảng nhân vật trên cửa sổ GAuto")
    return ds[0] if ds else None


def _thanh_tab(hwnd):
    ds = _con_truc_tiep(hwnd, "SysTabControl32")
    if not ds:
        raise LoiGautoAcTac("không thấy thanh tab cài đặt trên cửa sổ GAuto")
    return ds[0]


def _msaa(hwnd):
    try:
        return msaa.DoiTuong(hwnd)
    except msaa.LoiMsaa as loi:
        raise LoiGautoAcTac(str(loi)) from loi


def ten_tu_dong_gauto(chu):
    """«caychay10 (TL/123)» -> «caychay10»."""
    chu = (chu or "").strip()
    return re.sub(r"\s*\([^()]*\)\s*$", "", chu) or chu


def _khop_ten(a, b):
    from auto_chuyen_sinh import chuan_hoa
    return bool(a) and bool(b) and chuan_hoa(a) == chuan_hoa(b)


def danh_sach_nhan_vat(hwnd):
    """[(id MSAA, tên, đang chọn, ô đầu dòng tích)] các dòng bảng nhân vật GAuto."""
    kq = []
    with _msaa(_bang_nhan_vat(hwnd)) as o:
        for i in range(1, o.so_con() + 1):
            try:
                ten, tt = o.ten(i), o.trang_thai(i)
            except msaa.LoiMsaa:
                continue
            if ten:
                kq.append((i, ten_tu_dong_gauto(ten), bool(tt & msaa.STATE_SYSTEM_SELECTED),
                           bool(tt & msaa.STATE_SYSTEM_CHECKED)))
    return kq


def tim_chi_so_dong_theo_ten(hwnd, ten_nv, cache=None):
    """id MSAA của dòng nhân vật ten_nv trong bảng GAuto (cache không dùng nữa, giữ tham số cho bên gọi)."""
    kiem_tra_quyen(hwnd)
    ds = danh_sach_nhan_vat(hwnd)
    for i, ten, _, _ in ds:
        if _khop_ten(ten, ten_nv):
            return i
    raise LoiGautoAcTac(f"bảng GAuto không có nhân vật «{ten_nv}» (đang có: {', '.join(t for _, t, _, _ in ds) or 'trống'})"
                        " — đăng nhập nhân vật đó trong GAuto")


def nhan_vat_dang_cai(hwnd):
    """Tên nhân vật GAuto đang hiện cài đặt (tab đầu của thanh tab mang tên nhân vật)."""
    ten_tab = _cac_ten_tab(_thanh_tab(hwnd))
    return ten_tab[0] if ten_tab else ""


def chon_dong(hwnd, id_dong, ten_nv=None):
    """
    Chọn dòng (GAuto đổi tab cài đặt sang nhân vật đó). Biết ten_nv thì chờ tới khi tab cài đặt đúng tên nhân vật đó
    (dòng hiện "đang chọn" chưa chắc GAuto đã đổi cài đặt sang nhân vật đó).
    """
    with _msaa(_bang_nhan_vat(hwnd)) as o:
        ten_dong = ten_tu_dong_gauto(o.ten(id_dong))
        if ten_nv and not _khop_ten(ten_dong, ten_nv):
            raise LoiGautoAcTac(f"dòng GAuto đã đổi, không còn là «{ten_nv}»")
        ten_nv = ten_nv or ten_dong

        def xong():
            return o.dang_chon(id_dong) and _khop_ten(nhan_vat_dang_cai(hwnd), ten_nv)

        def cho_xong(giay):
            het = time.time() + giay
            while not xong() and time.time() < het:
                time.sleep(0.1)
            return xong()
        if xong():
            return
        o.chon(id_dong)
        # Chọn bằng MSAA có lúc chỉ đổi dòng sáng mà GAuto vẫn giữ cài đặt nhân vật cũ: bấm chuột thật vào dòng.
        if not cho_xong(GIAY_CHO_CHON_MSAA):
            for _ in range(2):
                _bam_dong_chuot(hwnd, o.vi_tri(id_dong))
                if cho_xong(GIAY_CHO_CHON_DONG / 2):
                    break
        if not xong():
            raise LoiGautoAcTac(f"không chọn được dòng «{ten_nv}» trong bảng GAuto (GAuto đang cài cho "
                                f"«{nhan_vat_dang_cai(hwnd) or '?'}»)")
        time.sleep(GIAY_CHO_DOI_NHAN_VAT)


def _dam_bao_dang_cai(hwnd, ten_nv):
    dang = nhan_vat_dang_cai(hwnd)
    if not _khop_ten(dang, ten_nv):
        raise LoiGautoAcTac(f"GAuto đổi sang cài cho «{dang or '?'}» giữa chừng (cần «{ten_nv}»), không tích")


def _trang_tab(tab, ten):
    for c in _cac_con(tab):
        if win32gui.GetParent(c) == tab and win32gui.GetWindowText(c) == ten:
            return c
    return None


def _cac_ten_tab(tab):
    ds = []
    with _msaa(tab) as o:
        for i in range(1, o.so_con() + 1):
            try:
                ds.append(o.ten(i))
            except msaa.LoiMsaa:
                break
    return ds


def mo_tab(hwnd, ten):
    """Chuyển thanh tab sang trang ten (phím mũi tên gửi thẳng vào thanh tab), trả về HWND trang."""
    tab = _thanh_tab(hwnd)
    ten_tab = _cac_ten_tab(tab)
    if ten not in ten_tab:
        raise LoiGautoAcTac(f"GAuto không có tab «{ten}» (có: {', '.join(ten_tab)})")
    dich = ten_tab.index(ten)
    for _ in range(len(ten_tab) * 2):
        trang = _trang_tab(tab, ten)
        hien_tai = win32gui.SendMessage(tab, TCM_GETCURSEL, 0, 0)
        if trang and hien_tai == dich and win32gui.IsWindowVisible(trang):
            return trang
        phim = win32con.VK_RIGHT if hien_tai < dich else win32con.VK_LEFT
        win32gui.PostMessage(tab, win32con.WM_KEYDOWN, phim, 0)
        win32gui.PostMessage(tab, win32con.WM_KEYUP, phim, 0xC0000000)
        time.sleep(GIAY_GIUA_PHIM_TAB)
    raise LoiGautoAcTac(f"không mở được tab «{ten}» trên GAuto")


def khung_ac_tac(hwnd):
    """{tên ô: HWND} các ô tích khung Ác Tặc và "map": HWND ô chọn map (mở tab Nhiệm vụ nếu chưa mở)."""
    trang = _trang_tab(_thanh_tab(hwnd), TAB_NHIEM_VU) or mo_tab(hwnd, TAB_NHIEM_VU)
    con = _cac_con(trang)
    o_ac_tac = next((c for c in con if win32gui.GetWindowText(c) == O_AC_TAC and "BUTTON" in win32gui.GetClassName(c)),
                    None)
    if o_ac_tac is None:
        trang = mo_tab(hwnd, TAB_NHIEM_VU)
        con = _cac_con(trang)
        o_ac_tac = next((c for c in con if win32gui.GetWindowText(c) == O_AC_TAC), None)
    if o_ac_tac is None:
        raise LoiGautoAcTac("không thấy ô «Ác Tặc» trong tab Nhiệm vụ của GAuto")
    khung = win32gui.GetParent(o_ac_tac)
    kq = _cac_o_trong_khung(khung)
    if "map" not in kq:
        # Khung thu gọn (chỉ hiện hàng đầu) thì GAuto chưa tạo ô Map / «Tự tìm»: bấm nút mở rộng không chữ đầu khung.
        nut = next((c for c in _cac_con(khung) if win32gui.GetParent(c) == khung and not win32gui.GetWindowText(c)
                    and "BUTTON" in win32gui.GetClassName(c)), None)
        if nut:
            with _msaa(nut) as o:
                o.bam(0)
            het = time.time() + GIAY_CHO_O_TICH
            while "map" not in kq and time.time() < het:
                time.sleep(0.1)
                kq = _cac_o_trong_khung(khung)
    return kq


def _cac_o_trong_khung(khung):
    kq = {}
    for c in _cac_con(khung):
        if win32gui.GetParent(c) != khung:
            continue
        lop, chu = win32gui.GetClassName(c), win32gui.GetWindowText(c)
        if "BUTTON" in lop and chu in CAC_O_KHUNG_AC_TAC:
            kq[chu] = c
        elif "COMBOBOX" in lop:
            kq.setdefault("map", c)
    return kq


def da_tich(hwnd_o):
    with _msaa(hwnd_o) as o:
        return o.da_tich()


def dat_o(hwnd_o, bat, ten):
    with _msaa(hwnd_o) as o:
        if o.da_tich() == bat:
            return False
        o.bam()
        het = time.time() + GIAY_CHO_O_TICH
        while o.da_tich() != bat and time.time() < het:
            time.sleep(0.1)
        if o.da_tich() != bat:
            raise LoiGautoAcTac(f"không {'tích' if bat else 'bỏ tích'} được ô «{ten}» trên GAuto")
    return True


def doc_map(hwnd_combo):
    """Tên map đang chọn trong ô Map của GAuto, "" nếu chưa chọn."""
    user32 = ctypes.windll.user32
    i = win32gui.SendMessage(hwnd_combo, win32con.CB_GETCURSEL, 0, 0)
    if i < 0:
        return ""
    buf = ctypes.create_unicode_buffer(256)
    n = user32.SendMessageW(hwnd_combo, win32con.CB_GETLBTEXT, i, buf)
    return buf.value[:max(n, 0)]


def cac_map(hwnd_combo):
    user32 = ctypes.windll.user32
    ds = []
    for i in range(max(0, win32gui.SendMessage(hwnd_combo, win32con.CB_GETCOUNT, 0, 0))):
        buf = ctypes.create_unicode_buffer(256)
        user32.SendMessageW(hwnd_combo, win32con.CB_GETLBTEXT, i, buf)
        ds.append(buf.value)
    return ds


def vi_tri_map(cac, ten_map):
    """Chỉ số map ten_map trong danh sách GAuto (so không dấu), None nếu GAuto không có."""
    from dang_nhap import bo_dau
    khoa = bo_dau(ten_map or "")
    return next((i for i, m in enumerate(cac) if bo_dau(m) == khoa), None)


class _ComboInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("rcItem", ctypes.c_long * 4), ("rcButton", ctypes.c_long * 4),
                ("stateButton", ctypes.c_uint32), ("hwndCombo", ctypes.c_void_p), ("hwndItem", ctypes.c_void_p),
                ("hwndList", ctypes.c_void_p)]


def _bam_chuot(hwnd_goc, diem, cho="ô Map"):
    duoi = win32gui.WindowFromPoint(diem)
    if hwnd_goc not in (duoi, win32gui.GetAncestor(duoi, win32con.GA_ROOT), win32gui.GetWindow(duoi, win32con.GW_OWNER)):
        raise LoiGautoAcTac(f"cửa sổ GAuto đang bị cửa sổ khác che chỗ {cho}")
    win32api.SetCursorPos(diem)
    time.sleep(0.15)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


@contextlib.contextmanager
def _muon_chuot(hwnd, viec):
    """Đưa GAuto lên trước để bấm chuột thật; xong trả chuột và cửa sổ trên cùng như cũ."""
    with KHOA_CHUOT:
        cu_truoc, cu_chuot = win32gui.GetForegroundWindow(), win32api.GetCursorPos()
        try:
            try:
                _len_truoc(hwnd)
            except LoiKeoTha as loi:
                raise LoiGautoAcTac(f"không đưa được cửa sổ GAuto lên trước để {viec}") from loi
            yield
        finally:
            win32api.SetCursorPos(cu_chuot)
            if cu_truoc and cu_truoc != hwnd and win32gui.IsWindow(cu_truoc):
                try:
                    _len_truoc(cu_truoc)
                except (LoiKeoTha, win32gui.error):
                    pass


def _bam_dong_chuot(hwnd, vi_tri):
    """Bấm chuột thật vào chữ tên nhân vật của dòng (tránh ô tích đầu dòng) trong bảng nhân vật GAuto."""
    l, t, w, h = vi_tri
    diem = (l + max(30, min(w // 2, 80)), t + h // 2)
    with _muon_chuot(hwnd, "chọn nhân vật"):
        _bam_chuot(hwnd, diem, "bảng nhân vật")
        time.sleep(0.3)


def chon_map(hwnd, hwnd_combo, ten_map):
    """Chọn map ten_map trong ô Map GAuto bằng chuột thật. True nếu đã đổi, False nếu đang đúng map."""
    cac = cac_map(hwnd_combo)
    dich = vi_tri_map(cac, ten_map)
    if dich is None:
        raise LoiGautoAcTac(f"GAuto không có map «{ten_map}» (có: {', '.join(cac)}) — chọn map khác trong AutoHoc")
    if win32gui.SendMessage(hwnd_combo, win32con.CB_GETCURSEL, 0, 0) == dich:
        return False
    info = _ComboInfo(cbSize=ctypes.sizeof(_ComboInfo))
    if not ctypes.windll.user32.GetComboBoxInfo(hwnd_combo, ctypes.byref(info)):
        raise LoiGautoAcTac("không đọc được ô Map của GAuto")
    with _muon_chuot(hwnd, "chọn map"):
        try:
            bl, bt, br, bb = info.rcButton
            _bam_chuot(hwnd, win32gui.ClientToScreen(hwnd_combo, ((bl + br) // 2, (bt + bb) // 2)))
            het = time.time() + GIAY_CHO_THA_XUONG
            while not win32gui.SendMessage(hwnd_combo, win32con.CB_GETDROPPEDSTATE, 0, 0) and time.time() < het:
                time.sleep(0.05)
            if not win32gui.SendMessage(hwnd_combo, win32con.CB_GETDROPPEDSTATE, 0, 0):
                raise LoiGautoAcTac("bấm ô Map GAuto mà danh sách map không mở")
            win32gui.SendMessage(hwnd_combo, win32con.CB_SETTOPINDEX, dich, 0)
            ds = info.hwndList
            dau = win32gui.SendMessage(ds, LB_GETTOPINDEX, 0, 0)
            cao = win32gui.SendMessage(hwnd_combo, win32con.CB_GETITEMHEIGHT, 0, 0)
            l, _, r, _ = win32gui.GetClientRect(ds)
            _bam_chuot(ds, win32gui.ClientToScreen(ds, ((l + r) // 2, (dich - dau) * cao + cao // 2)))
            time.sleep(0.5)
        finally:
            if win32gui.SendMessage(hwnd_combo, win32con.CB_GETDROPPEDSTATE, 0, 0):
                win32gui.SendMessage(hwnd_combo, win32con.CB_SHOWDROPDOWN, 0, 0)
    if win32gui.SendMessage(hwnd_combo, win32con.CB_GETCURSEL, 0, 0) != dich:
        raise LoiGautoAcTac(f"chọn map «{ten_map}» trên GAuto không ăn (đang «{doc_map(hwnd_combo)}»)")
    return True


def _chon_nhan_vat(hwnd, ten_nv, chi_so_dong):
    kiem_tra_quyen(hwnd)
    if chi_so_dong is None:
        chi_so_dong = tim_chi_so_dong_theo_ten(hwnd, ten_nv)
    try:
        chon_dong(hwnd, chi_so_dong, ten_nv)
    except LoiGautoAcTac:
        chi_so_dong = tim_chi_so_dong_theo_ten(hwnd, ten_nv)
        chon_dong(hwnd, chi_so_dong, ten_nv)
    return khung_ac_tac(hwnd)


def bo_tich_dong_khac(hwnd, ten_nv):
    """Bỏ tích «Ác Tặc» mọi dòng GAuto khác ten_nv (đội viên, nhân vật round trước). Trả về tên các dòng đã bỏ tích."""
    da_bo = []
    for id_dong, ten, _, _ in danh_sach_nhan_vat(hwnd):
        if _khop_ten(ten, ten_nv):
            continue
        chon_dong(hwnd, id_dong, ten)
        o = khung_ac_tac(hwnd)
        if O_AC_TAC in o and da_tich(o[O_AC_TAC]):
            _dam_bao_dang_cai(hwnd, ten)
            dat_o(o[O_AC_TAC], False, O_AC_TAC)
            da_bo.append(ten)
    return da_bo


def dat_cai_dat_ac_tac(hwnd, at, ten_nv, chi_so_dong=None, cache=None, ten_map=None, in_log=None):
    """
    Bật Ác Tặc GAuto chỉ cho dòng ten_nv (đội trưởng đang login) theo tùy chọn Ác Tặc của AutoHoc: bỏ tích Ác Tặc các
    dòng khác, chọn dòng đội trưởng, chọn map ten_map (map AutoHoc đã đưa đội tới), các ô phụ, tích «Ác Tặc» sau cùng.
    Trả về map GAuto đang chọn.
    """
    kiem_tra_quyen(hwnd)
    da_bo = bo_tich_dong_khac(hwnd, ten_nv)
    if da_bo and in_log:
        in_log(f"bỏ tích Ác Tặc GAuto ở dòng khác: {', '.join(da_bo)}")
    o = _chon_nhan_vat(hwnd, ten_nv, None)
    if ten_map:
        if "map" not in o:
            raise LoiGautoAcTac("không thấy ô Map trong khung Ác Tặc của GAuto")
        _dam_bao_dang_cai(hwnd, ten_nv)
        chon_map(hwnd, o["map"], ten_map)
    chay_pp = bool(at.get("chay_pathpoints"))
    for ten, bat in ((O_CHAY_PATHPOINTS, chay_pp), (O_CHAY_TIM, not chay_pp),
                     (O_CHO_PARTY, bool(at.get("cho_party", True))), (O_TU_TIM, bool(at.get("tu_tim", True))),
                     (O_AC_TAC, True)):
        if ten in o:
            _dam_bao_dang_cai(hwnd, ten_nv)
            dat_o(o[ten], bat, ten)
        elif ten == O_AC_TAC:
            raise LoiGautoAcTac("không thấy ô «Ác Tặc» trên GAuto")
    return doc_map(o["map"]) if "map" in o else ""


def tat_ac_tac(hwnd, ten_nv, chi_so_dong=None, cache=None):
    o = _chon_nhan_vat(hwnd, ten_nv, chi_so_dong)
    _dam_bao_dang_cai(hwnd, ten_nv)
    dat_o(o[O_AC_TAC], False, O_AC_TAC)


def test_gauto(duong_dan, ten_nv, in_log, bat_thu=False, giay_bat_thu=3, cac_map_autohoc=()):
    """
    Nút «Test GAuto»: chạy từng bước, ghi log từng bước. ten_nv rỗng thì dùng dòng đang chọn. bat_thu: chọn map đầu
    của cac_map_autohoc trên GAuto, tích Ác Tặc rồi bỏ tích lại sau giay_bat_thu giây (map giữ theo AutoHoc).
    Trả về True nếu mọi bước được; LoiGautoAcTac khi hỏng ở bước nào.
    """
    in_log(f"Test GAuto: 1) tìm cửa sổ GAuto ({duong_dan or 'chưa nhập đường dẫn'})")
    hwnd = tim_cua_so_quan_ly(duong_dan)
    in_log(f"Test GAuto:    thấy «{tom_tat_cua_so(hwnd)}»")
    q_gauto, q_auto = gauto_la_admin(hwnd), autohoc_la_admin()
    in_log(f"Test GAuto: 2) quyền: GAuto {'Admin' if q_gauto else 'thường'}, AutoHoc {'Admin' if q_auto else 'thường'}")
    kiem_tra_quyen(hwnd)
    ds = danh_sach_nhan_vat(hwnd)
    in_log("Test GAuto: 3) bảng nhân vật: " + ("; ".join(
        f"{ten}{' [đang chọn]' if chon else ''}{' [ô đầu dòng tích]' if tich else ''}" for _, ten, chon, tich in ds)
        or "trống"))
    if not ds:
        raise LoiGautoAcTac("bảng nhân vật GAuto trống — đăng nhập nhân vật trong GAuto trước")
    if ten_nv:
        id_dong = tim_chi_so_dong_theo_ten(hwnd, ten_nv)
    else:
        id_dong = next((i for i, _, chon, _ in ds if chon), ds[0][0])
        ten_nv = next(t for i, t, _, _ in ds if i == id_dong)
    in_log(f"Test GAuto: 4) chọn dòng «{ten_nv}»")
    chon_dong(hwnd, id_dong, ten_nv)
    in_log(f"Test GAuto: 5) mở tab «{TAB_NHIEM_VU}», tìm khung Ác Tặc")
    o = khung_ac_tac(hwnd)
    trang_thai = ", ".join(f"{ten} {'☑' if da_tich(o[ten]) else '☐'}" for ten in CAC_O_KHUNG_AC_TAC if ten in o)
    thieu = [ten for ten in CAC_O_KHUNG_AC_TAC if ten not in o]
    in_log(f"Test GAuto:    {trang_thai}" + (f"; không thấy ô: {', '.join(thieu)}" if thieu else ""))
    if "map" in o:
        cac = cac_map(o["map"])
        in_log(f"Test GAuto:    map GAuto chọn: «{doc_map(o['map']) or 'chưa chọn'}» (có: {', '.join(cac)})")
        thieu_map = [m for m in cac_map_autohoc if vi_tri_map(cac, m) is None]
        if thieu_map:
            in_log(f"Test GAuto:    GAuto không có map {', '.join(thieu_map)} (đang tích trong AutoHoc) — đưa map GAuto "
                   "có lên đầu danh sách AutoHoc")
    if bat_thu:
        map_dau = next((m for m in cac_map_autohoc if "map" in o and vi_tri_map(cac_map(o["map"]), m) is not None),
                       None)
        if map_dau:
            in_log(f"Test GAuto: 6) chọn map «{map_dau}» (map đầu AutoHoc) trên GAuto bằng chuột — đừng động chuột")
            chon_map(hwnd, o["map"], map_dau)
            in_log(f"Test GAuto:    map GAuto giờ là «{doc_map(o['map'])}»")
        da_bat = da_tich(o[O_AC_TAC])
        in_log(f"Test GAuto: 7) {'bỏ tích' if da_bat else 'tích'} thử ô «{O_AC_TAC}» {giay_bat_thu} giây rồi trả lại")
        dat_o(o[O_AC_TAC], not da_bat, O_AC_TAC)
        time.sleep(giay_bat_thu)
        dat_o(o[O_AC_TAC], da_bat, O_AC_TAC)
        in_log(f"Test GAuto:    đổi được, đã trả ô «{O_AC_TAC}» về {'☑' if da_bat else '☐'}")
    in_log("Test GAuto: OK — AutoHoc điều khiển được GAuto")
    return True


def phut_gauto(at):
    gia_tri = at.get("phut_gauto")
    if gia_tri is None or gia_tri == "":
        gia_tri = PHUT_MAC_DINH
    try:
        p = int(gia_tri)
    except (TypeError, ValueError):
        p = PHUT_MAC_DINH
    return max(1, min(p, 120))
