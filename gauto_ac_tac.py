"""
Điều khiển Ác Tặc trên cửa sổ GAuto TLBB 2.5 (GAuto_2025.exe, ứng dụng WinForms 32-bit). Bấm bằng chuột ảo (gửi
WM_LBUTTONDOWN / WM_LBUTTONUP thẳng vào ô, GAuto nổi lên trên cùng không lấy focus, con trỏ thật không động); ô nào
không ăn chuột ảo thì tự dùng chuột thật (mượn chuột ~1 giây):
    Bảng nhân vật   : SysListView32 con trực tiếp của cửa sổ chính; MSAA: phần tử con 1..n tên "caychay10 (TL/123)",
                      accSelect chọn dòng (GAuto đổi cả tab cài đặt sang nhân vật đó).
    Tab cài đặt     : SysTabControl32; tab chỉ tạo control khi mở lần đầu. Chuyển tab bằng phím mũi tên gửi thẳng vào
                      thanh tab (MSAA "Switch" và lệnh TCM_SETCURSEL không làm GAuto đổi trang).
    Khung Ác Tặc    : trong trang "Nhiệm vụ", các ô tích cùng một khung với ô "Ác Tặc": "Chạy tìm", "Tự tìm",
                      "Chờ party (chống kẹt)", "Chạy pathpoints"; ô tích WinForms tự vẽ nên BM_GETCHECK luôn 0,
                      đọc / bấm bằng MSAA (trạng thái CHECKED, hành động mặc định Check / Uncheck).
    Map             : ô COMBOBOX trong khung, GAuto lưu riêng từng nhân vật. CB_SETCURSEL và phím gửi thẳng
                      (không focus) thì GAuto trả map cũ. Bấm dòng list trên máy ảo lệch lên 1 dòng (Tung Sơn thành
                      Thái Hồ). Focus ô Map, F4 mở danh sách, mũi tên tới đúng dòng, Enter.
GAuto tự nâng quyền Admin khi mở, Windows chặn app thường điều khiển app Admin: AutoHoc phải chạy quyền Admin.
"""
import contextlib
import ctypes
import os
import re
import sys
import threading
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
# GAuto 2.x (gameautopro): «GAuto TLBB-2.5.3.3 | …» hoặc «GAuto_2025». Không trùng tiêu đề game «… - ChickenAuto».
MAU_CUA_SO_GAUTO = re.compile(r"^GAuto", re.I)
# Cửa sổ hệ thống không được đẩy xuống đáy khi đang tìm chỗ bấm.
LOP_KHONG_DAY_XUONG = {"Shell_TrayWnd", "Progman", "WorkerW", "Button"}
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
LB_SETTOPINDEX = 0x0197
LB_GETITEMRECT = 0x0198
LB_GETITEMHEIGHT = 0x01A1
LVM_FIRST = 0x1000
LVM_GETITEMRECT = LVM_FIRST + 14
LVM_ENSUREVISIBLE = LVM_FIRST + 19
LVM_GETTOPINDEX = LVM_FIRST + 39
LVM_GETCOUNTPERPAGE = LVM_FIRST + 40
LVM_GETITEMSTATE = LVM_FIRST + 44
LVM_GETITEMSPACING = LVM_FIRST + 51
LVIR_BOUNDS = 0
LVIS_STATEIMAGEMASK = 0xF000
GIAY_CHO_DOI_NHAN_VAT = 1.5
# Ngay sau khi đổi map GAuto bận lưu cài đặt, chọn dòng có lúc vài giây mới ăn.
GIAY_CHO_CHON_DONG = 6
GIAY_CHO_CHON_MSAA = 1.5
GIAY_CHO_THA_XUONG = 1.5
GIAY_GIUA_PHIM_TAB = 0.8
GIAY_CHO_O_TICH = 3.0
# Tích ô đầu dòng (bật auto) thì GAuto nạp lại cài đặt nhân vật vài giây sau, xóa ô tích đặt trước lúc đó.
GIAY_CHO_GAUTO_NAP = 5
# Sau khi tích «Ác Tặc», canh thêm chừng này giây phòng GAuto nạp lại muộn xóa mất ô vừa tích.
GIAY_CANH_NAP_LAI = 8
# Bấm GAuto bằng chuột ảo (PostMessage, không di con trỏ / không lấy focus); không ăn thì tự dùng chuột thật.
CHUOT_AO = True
# GAuto có lúc trả lại map cũ ngay sau khi đổi: chờ chừng này giây rồi đọc lại.
GIAY_GIU_MAP = 2.5
# Máy yếu: nghỉ sau mỗi cú bấm (tích ô, chọn map, chọn dòng) để GAuto kịp ăn trước thao tác kế.
GIAY_NGHI_SAU_THAO_TAC = 1.0
# Giữ nút chuột xuống một chút — bấm xuống/nhả liền trên máy chậm hay không ăn.
GIAY_GIU_NUT_CHUOT = 0.25
# Máy ảo / màn nhỏ: cửa sổ game hay đè GAuto — thử lại vài lần, đẩy cửa sổ che xuống dưới.
SO_LAN_THU_CHE = 4
GIAY_GIUA_THU_CHE = 0.6
# GAuto nạp lại bảng sau khi chọn dòng: MSAA accLocation hay chết (0x800706be). Thử lại vài lần.
SO_LAN_THU_DAU_DONG = 3
GIAY_GIUA_THU_DAU_DONG = 0.9
_KHOA_CHUOT_AO = threading.Lock()
_DA_BAO_CHUOT_THAT = set()
_CHO_BAO = []


class LoiGautoAcTac(Exception):
    pass


def _gui_con_tro_toi_gauto():
    """
    GAuto là process 32-bit. AutoHoc 64-bit mà SendMessage lParam = con trỏ RECT/buffer thì GAuto ghi vào địa chỉ
    cắt còn 32-bit → AccessViolation, hộp .NET «Attempted to read or write protected memory».
    Chỉ bản AutoHoc 32-bit mới gửi được LVM_GETITEMRECT / LB_GETITEMRECT / CB_GETLBTEXT.
    """
    return ctypes.sizeof(ctypes.c_void_p) == 4


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


def _la_tieu_de_quan_ly(tieu_de, muon_gauto):
    if muon_gauto:
        return bool(MAU_CUA_SO_GAUTO.match(tieu_de) and " - ChickenAuto" not in tieu_de)
    return bool(MAU_CUA_SO_CHICKEN.match(tieu_de))


def _chon_hwnd_gauto(khop_duong, cung_loai):
    """Ưu tiên cửa sổ đúng đường dẫn exe, rồi cửa sổ cùng họ tên file (máy cài GAuto ở thư mục khác)."""
    for nhom in (khop_duong, cung_loai):
        if not nhom:
            continue
        co_bang = [h for h in nhom if _bang_nhan_vat(h, bat_buoc=False)]
        return (co_bang or nhom)[0]
    return None


def tim_cua_so_quan_ly(duong_dan_gauto):
    """HWND cửa sổ quản lý — khớp exe cấu hình; không khớp thư mục thì vẫn nhận cửa sổ GAuto cùng loại đang mở."""
    muc_tieu = _chuan_hoa_duong_dan(duong_dan_gauto)
    muon_gauto = _cau_hinh_muon_gauto_tlbb(duong_dan_gauto)
    ten_mong_doi = {t.lower() for t in _danh_sach_exe_tim(duong_dan_gauto)}
    khop, cung_loai = [], []

    def duyet(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True
        tieu_de = (win32gui.GetWindowText(hwnd) or "").strip()
        if not _la_tieu_de_quan_ly(tieu_de, muon_gauto):
            return True
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        exe = _exe_cua_pid(pid)
        if _khop_duong_dan_gauto(muc_tieu, exe):
            khop.append(hwnd)
        elif exe and os.path.basename(exe).lower() in ten_mong_doi:
            cung_loai.append(hwnd)
        return True

    win32gui.EnumWindows(duyet, None)
    hwnd = _chon_hwnd_gauto(khop, cung_loai)
    if hwnd:
        return hwnd
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
    q = _tien_trinh_admin(os.getpid())
    if q is not None:
        return q
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def gauto_la_admin(hwnd):
    """
    True nếu GAuto đang elevated. Không đọc được token (OpenProcess bị từ chối) thì coi là Admin:
    app thường không mở được tiến trình quyền cao, và nếu vẫn bấm thì Windows nuốt chuột ảo.
    """
    q = _tien_trinh_admin(win32process.GetWindowThreadProcessId(hwnd)[1])
    if q is None:
        return True
    return q


THONG_BAO_CAN_ADMIN = ("GAuto đang chạy quyền Admin (GAuto tự nâng quyền khi mở) còn AutoHoc thì không — Windows chặn "
                       "AutoHoc điều khiển GAuto. Tắt AutoHoc, chuột phải AutoHoc.exe → Run as administrator")


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


def _con_lop(hwnd, lop):
    """Control lớp lop: con trực tiếp trước, không có thì bất kỳ con cháu (bản GAuto bọc bảng trong panel)."""
    truc = _con_truc_tiep(hwnd, lop)
    if truc:
        return truc
    return [c for c in _cac_con(hwnd) if lop in (win32gui.GetClassName(c) or "")]


def _bang_nhan_vat(hwnd, bat_buoc=True):
    ds = _con_lop(hwnd, "SysListView32")
    if not ds and bat_buoc:
        raise LoiGautoAcTac("không thấy bảng nhân vật trên cửa sổ GAuto")
    return ds[0] if ds else None


def _thanh_tab(hwnd):
    ds = _con_lop(hwnd, "SysTabControl32")
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
                _bam_dong_chuot(hwnd, o.vi_tri(id_dong), xong, id_dong)
                if cho_xong(0.5):
                    break
        if not xong():
            raise LoiGautoAcTac(f"không chọn được dòng «{ten_nv}» trong bảng GAuto (GAuto đang cài cho "
                                f"«{nhan_vat_dang_cai(hwnd) or '?'}»)")
        time.sleep(GIAY_CHO_DOI_NHAN_VAT)
        _nghi_sau_thao_tac()


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


def dat_o_chuot(hwnd, hwnd_o, bat, ten):
    """
    Tích / bỏ tích ô hwnd_o trong khung Ác Tặc bằng chuột (ảo, không ăn thì thật): tích qua MSAA thì ô hiện ☑ nhưng
    GAuto không chạy Ác Tặc (phải bấm tay lại mới chạy). Trả về "ảo" / "thật" nếu đã bấm, False nếu ô đã đúng.
    """
    if da_tich(hwnd_o) == bat:
        return False
    l, t, r, b = win32gui.GetWindowRect(hwnd_o)
    rong, cao = max(1, r - l), max(1, b - t)
    # Ô tích WinForms: hộp nằm sát mép trái. 8px cố định lệch trên màn 150%.
    le = min(rong // 3, max(8, cao // 2))
    cach = _bam_ao_hoac_that(hwnd, hwnd_o, (l + le, t + cao // 2), f"ô «{ten}»",
                             lambda: da_tich(hwnd_o) == bat)
    if da_tich(hwnd_o) != bat:
        raise LoiGautoAcTac(f"không {'tích' if bat else 'bỏ tích'} được ô «{ten}» trên GAuto")
    _nghi_sau_thao_tac()
    return cach


def _chu_combo_theo_lenh(hwnd_combo, chi_so):
    if not _gui_con_tro_toi_gauto():
        return ""
    user32 = ctypes.windll.user32
    buf = ctypes.create_unicode_buffer(256)
    n = user32.SendMessageW(hwnd_combo, win32con.CB_GETLBTEXT, chi_so, buf)
    if n is None or n < 0:
        return ""
    return buf.value[:n]


def _ten_map_msaa(hwnd_combo):
    """Đọc tên map qua MSAA khi lệnh combo không trả chữ (GAuto 32-bit, AutoHoc 64-bit)."""
    try:
        with _msaa(hwnd_combo) as o:
            ds = []
            for i in range(1, o.so_con() + 1):
                try:
                    ten = (o.ten(i) or "").strip()
                except msaa.LoiMsaa:
                    break
                if ten:
                    ds.append(ten)
            dang_chon = (o.ten(0) or "").strip()
            return dang_chon, ds
    except LoiGautoAcTac:
        return "", []


# MSAA trên HWND combo đôi khi trả nhãn kiểu đường, không phải tên map trong list thả xuống.
_NHAN_KIEU_DUONG = frozenset({"đường đi", "open"})


def _la_nhan_kieu_duong(ten):
    return (ten or "").strip().casefold() in _NHAN_KIEU_DUONG


def doc_map(hwnd_combo):
    """Tên map đang chọn trong ô Map của GAuto, "" nếu chưa chọn.

    Tên đọc được bằng lệnh (32-bit) hoặc MSAA là map thật thì trả ngay. MSAA ra «Đường đi» / «Open»
    thì lấy tên theo CB_GETCURSEL trong hwndList — cùng list chon_map dùng.
    """
    i = win32gui.SendMessage(hwnd_combo, win32con.CB_GETCURSEL, 0, 0)
    if i >= 0:
        chu = _chu_combo_theo_lenh(hwnd_combo, i)
        if chu:
            return chu
    dang_chon, _ = _ten_map_msaa(hwnd_combo)
    if i >= 0 and _la_nhan_kieu_duong(dang_chon):
        ds = _doc_ds_list_combo(hwnd_combo)
        if 0 <= i < len(ds) and ds[i] and not _la_nhan_kieu_duong(ds[i]):
            return ds[i]
    return dang_chon


def _info_combo(hwnd_combo):
    """COMBOBOXINFO — cùng API chon_map dùng để lấy hwndList."""
    info = _ComboInfo(cbSize=ctypes.sizeof(_ComboInfo))
    if not ctypes.windll.user32.GetComboBoxInfo(hwnd_combo, ctypes.byref(info)):
        return None
    return info


def _doc_ds_list_combo(hwnd_combo):
    """Tên từng dòng trong list thả xuống (hwndList). AutoHoc 64-bit không dùng CB_GETLBTEXT."""
    def doc(info):
        h = int(info.hwndList or 0) if info else 0
        if not h:
            return []
        _, ds = _ten_map_msaa(h)
        return [m for m in ds if m]

    ds = doc(_info_combo(hwnd_combo))
    if ds:
        return ds
    da_mo = _dang_tha_xuong(hwnd_combo)
    try:
        if not da_mo:
            win32gui.SendMessage(hwnd_combo, win32con.CB_SHOWDROPDOWN, 1, 0)
            if not _cho_dk(lambda: _dang_tha_xuong(hwnd_combo), GIAY_CHO_THA_XUONG):
                return []
        return doc(_info_combo(hwnd_combo))
    finally:
        if not da_mo and _dang_tha_xuong(hwnd_combo):
            win32gui.SendMessage(hwnd_combo, win32con.CB_SHOWDROPDOWN, 0, 0)


def cac_map(hwnd_combo):
    """Danh sách map ô Map: GETLBTEXT (32-bit) hoặc hwndList của chon_map (64-bit)."""
    if _gui_con_tro_toi_gauto():
        ds = [_chu_combo_theo_lenh(hwnd_combo, i)
              for i in range(max(0, win32gui.SendMessage(hwnd_combo, win32con.CB_GETCOUNT, 0, 0)))]
        if any(ds):
            return ds
    ds = _doc_ds_list_combo(hwnd_combo)
    if ds:
        return ds
    _, tu_msaa = _ten_map_msaa(hwnd_combo)
    return [m for m in tu_msaa if m]


def vi_tri_map(cac, ten_map):
    """Chỉ số map ten_map trong danh sách GAuto (so không dấu), None nếu GAuto không có."""
    from dang_nhap import bo_dau
    khoa = bo_dau(ten_map or "")
    return next((i for i, m in enumerate(cac) if bo_dau(m) == khoa), None)


class _ComboInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint32), ("rcItem", ctypes.c_long * 4), ("rcButton", ctypes.c_long * 4),
                ("stateButton", ctypes.c_uint32), ("hwndCombo", ctypes.c_void_p), ("hwndItem", ctypes.c_void_p),
                ("hwndList", ctypes.c_void_p)]


def _la_cua_so_autohoc(hwnd):
    """Cửa sổ thuộc chính tiến trình AutoHoc (UI Tk). Đưa nó lên trước giữa các lần bấm GAuto thì hai cửa sổ giành focus."""
    if not hwnd:
        return False
    try:
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
    except (win32gui.error, OSError):
        return False
    return pid == os.getpid()


def _hien_cua_so_gauto(hwnd):
    """
    Mở GAuto trước khi bấm: đang thu nhỏ thì khôi phục, đang ẩn thì hiện, nằm ngoài màn thì kéo vào.
    Trả về lý do vừa phải mở, hoặc None nếu cửa sổ đã nằm trên màn.
    """
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return "đang thu nhỏ"
        if not win32gui.IsWindowVisible(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
            return "đang ẩn"
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        vx = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
        vy = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
        vw = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
        vh = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
        if r <= vx or b <= vy or l >= vx + vw or t >= vy + vh:
            win32gui.SetWindowPos(
                hwnd, 0, vx + 40, vy + 40, 0, 0,
                win32con.SWP_NOSIZE | win32con.SWP_NOZORDER | win32con.SWP_NOACTIVATE)
            return "đang nằm ngoài màn hình"
    except (win32gui.error, win32api.error, AttributeError, OSError):
        return None
    return None


@contextlib.contextmanager
def _noi_len(hwnd):
    """Đưa GAuto lên trên cùng mà không lấy focus (chuột ảo cần ô không bị che); xong trả về dưới cửa sổ đang dùng."""
    co = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
    _hien_cua_so_gauto(hwnd)
    da_tren_cung = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST
    thu_nho = win32gui.IsIconic(hwnd)
    dang_dung = win32gui.GetForegroundWindow()
    if thu_nho:
        win32gui.ShowWindow(hwnd, win32con.SW_SHOWNOACTIVATE)
    if not da_tren_cung:
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, co)
    try:
        yield
    finally:
        try:
            if not da_tren_cung:
                win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, co)
                # Không nhét GAuto xuống dưới cửa sổ AutoHoc — laptop hay để AutoHoc focus, mỗi ô lại nhảy qua lại.
                if dang_dung and dang_dung != hwnd and win32gui.IsWindow(dang_dung) \
                        and not _la_cua_so_autohoc(dang_dung):
                    win32gui.SetWindowPos(hwnd, dang_dung, 0, 0, 0, 0, co)
            if thu_nho:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOWMINNOACTIVE)
        except win32gui.error:
            pass


def _he_so_logic_cua_so(hwnd):
    """
    Cửa sổ đích không DPI-aware thì WM_LBUTTON* dùng pixel logic (96 DPI), còn AutoHoc đọc pixel vật lý.
    None nếu không cần đổi (cùng hệ tọa độ, hoặc không đọc được).
    """
    user32 = ctypes.windll.user32
    try:
        user32.GetWindowDpiAwarenessContext.restype = ctypes.c_void_p
        user32.GetWindowDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
        user32.GetAwarenessFromDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.GetDpiForWindow.restype = ctypes.c_uint
        user32.GetDpiForWindow.argtypes = [ctypes.c_void_p]
        ctx = user32.GetWindowDpiAwarenessContext(hwnd)
        if user32.GetAwarenessFromDpiAwarenessContext(ctx) != 0:
            return None
        dpi = user32.GetDpiForWindow(hwnd) or 96
    except (AttributeError, OSError, ValueError):
        return None
    if dpi == 96:
        return None
    return 96 / dpi


def _lp_chuot(x, y, he_so=None):
    if he_so:
        x, y = int(round(x * he_so)), int(round(y * he_so))
    return win32api.MAKELONG(int(x) & 0xFFFF, int(y) & 0xFFFF)


def _nghi_sau_thao_tac():
    if GIAY_NGHI_SAU_THAO_TAC:
        time.sleep(GIAY_NGHI_SAU_THAO_TAC)


def _gui_click_ao(hwnd_dich, lp):
    win32gui.PostMessage(hwnd_dich, win32con.WM_MOUSEMOVE, 0, lp)
    win32gui.PostMessage(hwnd_dich, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lp)
    time.sleep(GIAY_GIU_NUT_CHUOT)
    win32gui.PostMessage(hwnd_dich, win32con.WM_LBUTTONUP, 0, lp)


def _sua_diem_man_hinh(hwnd, diem):
    """
    MSAA accLocation trên GAuto không DPI-aware trả pixel logic, trong khi màn 125/150% dùng pixel vật lý.
    Điểm nằm ngoài cửa sổ thì nhân / chia theo DPI cho tới khi rơi vào cửa sổ. Không sửa được thì giữ nguyên.
    """
    try:
        if _diem_trong_cua_so(hwnd, diem):
            return diem
        dpi = ctypes.windll.user32.GetDpiForWindow(int(hwnd)) or 96
    except (AttributeError, OSError, ValueError, win32gui.error):
        return diem
    if dpi == 96:
        return diem
    for he in (dpi / 96, 96 / dpi):
        thu = (int(round(diem[0] * he)), int(round(diem[1] * he)))
        if _diem_trong_cua_so(hwnd, thu):
            return thu
    return diem


def _bam_ao(hwnd_dich, diem, he_so=0):
    """Một cú chuột ảo tại điểm màn hình. he_so=None thì tự scale khi GAuto không DPI-aware; 0 thì giữ nguyên."""
    x, y = win32gui.ScreenToClient(hwnd_dich, diem)
    if he_so is None:
        he_so = _he_so_logic_cua_so(hwnd_dich)
    _gui_click_ao(hwnd_dich, _lp_chuot(x, y, he_so or None))


def _bam_client(hwnd_dich, xy, he_so=0):
    """Một cú chuột ảo theo toạ độ client của hwnd_dich (cùng hệ với LVM_GETITEMRECT)."""
    x, y = xy
    if he_so is None:
        he_so = _he_so_logic_cua_so(hwnd_dich)
    _gui_click_ao(hwnd_dich, _lp_chuot(x, y, he_so or None))


def _cho_dk(dk, giay):
    het = time.time() + giay
    while not dk() and time.time() < het:
        time.sleep(0.1)
    return dk()


def _bao_chuot_that(cho):
    if cho not in _DA_BAO_CHUOT_THAT:
        _DA_BAO_CHUOT_THAT.add(cho)
        _CHO_BAO.append(f"GAuto không nhận chuột ảo ở {cho}, dùng chuột thật")


def rut_bao_chuot(in_log):
    """Ghi các lần phải chuyển sang chuột thật (mỗi loại ô báo một lần mỗi phiên)."""
    while _CHO_BAO:
        chu = _CHO_BAO.pop(0)
        if in_log:
            in_log(chu)


def _bam_ao_hoac_that(hwnd, hwnd_dich, diem, cho, da_xong, giay=GIAY_CHO_O_TICH):
    """
    Bấm chuột ảo vào hwnd_dich; da_xong() không thành True trong giay giây thì bấm chuột thật như cũ.
    Trả về "ảo" / "thật" (cách đã ăn).
    """
    diem = _sua_diem_man_hinh(hwnd_dich, diem)
    if hwnd != hwnd_dich and not _diem_trong_cua_so(hwnd_dich, diem):
        diem = _sua_diem_man_hinh(hwnd, diem)
    return _bam_roi_that(hwnd, hwnd_dich, cho, da_xong, giay, lambda he_so: _bam_ao(hwnd_dich, diem, he_so), diem)


def _bam_client_hoac_that(hwnd, hwnd_dich, xy, cho, da_xong, giay=GIAY_CHO_O_TICH):
    """Như _bam_ao_hoac_that nhưng xy là toạ độ client của hwnd_dich (ô tích bảng nhân vật)."""
    try:
        diem = win32gui.ClientToScreen(hwnd_dich, (int(xy[0]), int(xy[1])))
    except win32gui.error:
        diem = xy
    return _bam_roi_that(hwnd, hwnd_dich, cho, da_xong, giay, lambda he_so: _bam_client(hwnd_dich, xy, he_so), diem)


def _bam_roi_that(hwnd, hwnd_dich, cho, da_xong, giay, bam_ao, diem):
    if CHUOT_AO:
        with _KHOA_CHUOT_AO, _noi_len(hwnd):
            bam_ao(0)
            if not _cho_dk(da_xong, giay) and _he_so_logic_cua_so(hwnd_dich):
                # Màn 125/150%: cú đầu không ăn thì thử hệ pixel kia, không bấm cả hai cùng lúc
                # (cú sau lệch lên một dòng / bỏ tích ô vừa bật).
                bam_ao(None)
            if _cho_dk(da_xong, giay):
                return "ảo"
        if da_xong():
            return "ảo"
        _bao_chuot_that(cho)
    with _muon_chuot(hwnd, cho):
        _bam_chuot(hwnd, diem, cho)
        _cho_dk(da_xong, giay)
    return "thật"


def _thuoc_gauto(hwnd_goc, diem):
    """True nếu điểm màn hình đang nằm trên cửa sổ GAuto (kể cả control con)."""
    try:
        duoi = win32gui.WindowFromPoint(diem)
    except win32gui.error:
        return False
    if not duoi:
        return False
    try:
        goc = win32gui.GetAncestor(duoi, win32con.GA_ROOT)
        chu = win32gui.GetWindow(duoi, win32con.GW_OWNER)
    except win32gui.error:
        return False
    return hwnd_goc in (duoi, goc, chu)


def _ten_lop(hwnd):
    try:
        return win32gui.GetClassName(hwnd) or ""
    except win32gui.error:
        return ""


def _diem_trong_cua_so(hwnd, diem):
    try:
        l, t, r, b = win32gui.GetWindowRect(hwnd)
    except win32gui.error:
        return False
    x, y = diem
    return l <= x < r and t <= y < b


def _mo_ta_cua_so_tai(diem):
    try:
        duoi = win32gui.WindowFromPoint(diem)
        goc = win32gui.GetAncestor(duoi, win32con.GA_ROOT) if duoi else 0
    except win32gui.error:
        return ""
    if not goc:
        return ""
    return f"«{tom_tat_cua_so(goc)}» ({_ten_lop(goc)})"


def _ha_cua_so_che(hwnd_goc, diem):
    """Đẩy cửa sổ đang đè điểm bấm xuống dưới (không ẩn), để chuột thật bấm được GAuto trên VM/màn nhỏ."""
    try:
        duoi = win32gui.WindowFromPoint(diem)
    except win32gui.error:
        return None
    if not duoi:
        return None
    try:
        goc = win32gui.GetAncestor(duoi, win32con.GA_ROOT)
    except win32gui.error:
        return None
    if not goc or goc == hwnd_goc or not win32gui.IsWindow(goc):
        return None
    if _ten_lop(goc) in LOP_KHONG_DAY_XUONG:
        return None
    co = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
    try:
        # Cửa sổ game hay gắn TOPMOST: HWND_BOTTOM không gỡ được cờ đó, GAuto vẫn nằm dưới.
        if win32gui.GetWindowLong(goc, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST:
            win32gui.SetWindowPos(goc, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, co)
        win32gui.SetWindowPos(goc, win32con.HWND_BOTTOM, 0, 0, 0, 0, co)
    except win32gui.error:
        return None
    return goc


def _san_sang_bam(hwnd_goc, diem):
    """Chỉ bấm khi điểm đang thuộc GAuto. Nằm trong khung GAuto nhưng game đè lên thì chưa được — phải gạt game ra."""
    return _thuoc_gauto(hwnd_goc, diem)


def _bam_chuot(hwnd_goc, diem, cho="ô Map"):
    co = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
    for lan in range(SO_LAN_THU_CHE):
        if _san_sang_bam(hwnd_goc, diem):
            break
        try:
            win32gui.SetWindowPos(hwnd_goc, win32con.HWND_TOPMOST, 0, 0, 0, 0, co | win32con.SWP_SHOWWINDOW)
            win32gui.BringWindowToTop(hwnd_goc)
        except win32gui.error:
            pass
        _ha_cua_so_che(hwnd_goc, diem)
        time.sleep(GIAY_GIUA_THU_CHE)
    else:
        dang_che = _mo_ta_cua_so_tai(diem)
        raise LoiGautoAcTac(f"cửa sổ GAuto đang bị cửa sổ khác che chỗ {cho}"
                            + (f" ({dang_che})" if dang_che else ""))
    win32api.SetCursorPos(diem)
    time.sleep(GIAY_GIU_NUT_CHUOT)
    if not _san_sang_bam(hwnd_goc, diem):
        _ha_cua_so_che(hwnd_goc, diem)
        time.sleep(GIAY_GIUA_THU_CHE)
        if not _san_sang_bam(hwnd_goc, diem):
            dang_che = _mo_ta_cua_so_tai(diem)
            raise LoiGautoAcTac(f"cửa sổ GAuto đang bị cửa sổ khác che chỗ {cho}"
                                + (f" ({dang_che})" if dang_che else ""))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(GIAY_GIU_NUT_CHUOT)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


@contextlib.contextmanager
def _muon_chuot(hwnd, viec):
    """Đưa GAuto lên trước + TOPMOST để bấm chuột thật; xong trả chuột và z-order như cũ."""
    with KHOA_CHUOT:
        cu_truoc, cu_chuot = win32gui.GetForegroundWindow(), win32api.GetCursorPos()
        co = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_NOACTIVATE
        try:
            da_tren_cung = bool(win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) & win32con.WS_EX_TOPMOST)
        except win32gui.error:
            da_tren_cung = False
        try:
            try:
                ctypes.windll.user32.AllowSetForegroundWindow(0xFFFFFFFF)
            except (AttributeError, OSError):
                pass
            _hien_cua_so_gauto(hwnd)
            try:
                _len_truoc(hwnd)
            except LoiKeoTha as loi:
                raise LoiGautoAcTac(f"không đưa được cửa sổ GAuto lên trước để {viec}") from loi
            if not da_tren_cung:
                try:
                    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, co)
                except win32gui.error:
                    pass
            yield
        finally:
            tra_focus = cu_truoc and cu_truoc != hwnd and win32gui.IsWindow(cu_truoc) \
                and not _la_cua_so_autohoc(cu_truoc)
            try:
                if not da_tren_cung:
                    win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0, co)
                    if tra_focus:
                        win32gui.SetWindowPos(hwnd, cu_truoc, 0, 0, 0, 0, co)
            except win32gui.error:
                pass
            try:
                win32api.SetCursorPos(cu_chuot)
            except win32api.error:
                pass
            if tra_focus:
                try:
                    _len_truoc(cu_truoc)
                except (LoiKeoTha, win32gui.error):
                    pass


def _rect_dong_bang(hwnd_list, chi_so_msaa):
    """
    Hình chữ nhật dòng trong bảng nhân vật, toạ độ client.
    MSAA con 1 là dòng listview 0. None nếu không phải listview hoặc dòng không có.
    AutoHoc 64-bit gửi LVM_GETITEMRECT sang GAuto 32-bit không marshal RECT: lúc đó dùng chiều cao dòng
    (LVM_GETCOUNTPERPAGE / LVM_GETITEMSPACING, số nguyên, chạy xuyên process).
    """
    i = int(chi_so_msaa) - 1
    if i < 0:
        return None
    try:
        hwnd_list = int(hwnd_list)
    except (TypeError, ValueError):
        return None
    if not hwnd_list:
        return None
    try:
        ctypes.windll.user32.SendMessageW(hwnd_list, LVM_ENSUREVISIBLE, i, 0)
        if _gui_con_tro_toi_gauto():
            rc = _RECT()
            rc.left = LVIR_BOUNDS
            ok = ctypes.windll.user32.SendMessageW(hwnd_list, LVM_GETITEMRECT, i, ctypes.byref(rc))
            if ok and rc.bottom > rc.top and rc.right > rc.left:
                return rc.left, rc.top, rc.right, rc.bottom
    except (OSError, ValueError):
        pass
    return _rect_dong_bang_theo_cao(hwnd_list, i)


def _dpi_cua_so(hwnd):
    """DPI cửa sổ. 0 nếu không đọc được — không coi 0 là 96."""
    try:
        dpi = int(ctypes.windll.user32.GetDpiForWindow(int(hwnd)))
    except (AttributeError, OSError, ValueError, TypeError):
        return 0
    return dpi if dpi > 0 else 0


def _y_duoi_header(hwnd_list):
    """Client Y mép dưới SysHeader32. 0 nếu không thấy header (giữ công thức không trừ header)."""
    thay = []

    def thay_header(con, _):
        try:
            if win32gui.GetClassName(con) == "SysHeader32":
                thay.append(con)
                return False
        except win32gui.error:
            pass
        return True

    try:
        win32gui.EnumChildWindows(int(hwnd_list), thay_header, None)
        if not thay:
            return 0
        trai, _tren, _phai, duoi = win32gui.GetWindowRect(thay[0])
        _x, y = win32gui.ScreenToClient(int(hwnd_list), (trai, duoi))
    except (win32gui.error, TypeError, ValueError):
        return 0
    return y if y > 0 else 0


def _cao_dong_listview(hwnd_list, tru_header=0):
    """Chiều cao một dòng report-view. tru_header > 0 thì trừ phần header khỏi client. 0 nếu không đọc được."""
    try:
        hwnd_list = int(hwnd_list)
        if not hwnd_list:
            return 0
        so = int(ctypes.windll.user32.SendMessageW(hwnd_list, LVM_GETCOUNTPERPAGE, 0, 0))
        _l, _t, _r, b = win32gui.GetClientRect(hwnd_list)
        vung = b - tru_header if 0 < tru_header < b else b
        if so > 0 and vung > 0:
            return max(1, vung // so)
        spacing = int(ctypes.windll.user32.SendMessageW(hwnd_list, LVM_GETITEMSPACING, 1, 0))
        cao = (spacing >> 16) & 0xFFFF
        return cao if cao > 0 else 0
    except (OSError, ValueError, win32gui.error, TypeError):
        return 0


def _rect_dong_bang_theo_cao(hwnd_list, i):
    """Client rect dòng i (0-based) từ top-index × chiều cao — không cần con trỏ RECT sang process 32-bit.

    DPI khác 96 (laptop 125/150%) hoặc không đọc được DPI: công thức cũ, không trừ header.
    DPI đúng 96 và đo được SysHeader32: dòng 0 bắt đầu dưới header.
    """
    try:
        hwnd_list = int(hwnd_list)
        if not hwnd_list or i < 0:
            return None
        ctypes.windll.user32.SendMessageW(hwnd_list, LVM_ENSUREVISIBLE, i, 0)
        dau = int(ctypes.windll.user32.SendMessageW(hwnd_list, LVM_GETTOPINDEX, 0, 0))
        le_header = _y_duoi_header(hwnd_list) if _dpi_cua_so(hwnd_list) == 96 else 0
        cao = _cao_dong_listview(hwnd_list, le_header)
        l, _t, r, _b = win32gui.GetClientRect(hwnd_list)
    except (OSError, ValueError, win32gui.error, TypeError):
        return None
    if cao <= 0:
        return None
    top = le_header + (i - dau) * cao
    return l, top, r, top + cao


def _dong_dang_tich(hwnd_list, chi_so_msaa, o=None):
    """
    Ô đầu dòng đang ☑. Ưu tiên LVM_GETITEMSTATE (số nguyên, 64-bit → GAuto 32-bit được).
    None nếu không đọc được.
    """
    i = int(chi_so_msaa) - 1
    try:
        hwnd_list = int(hwnd_list)
    except (TypeError, ValueError):
        hwnd_list = 0
    if hwnd_list and i >= 0:
        try:
            st = int(ctypes.windll.user32.SendMessageW(hwnd_list, LVM_GETITEMSTATE, i, LVIS_STATEIMAGEMASK))
            anh = (st >> 12) & 0xF
            if anh:
                return anh >= 2
        except (OSError, ValueError):
            pass
    if o is not None:
        try:
            return o.da_tich(chi_so_msaa)
        except msaa.LoiMsaa:
            return None
    return None


def _diem_o_tich_client(left, top, right, bottom):
    """Tâm ô tích đầu dòng. Listview không DPI-aware vẽ ô này khoảng 16 pixel logic, sát mép trái."""
    cao = bottom - top
    return left + max(4, min(cao // 2, 12)), (top + bottom) // 2


def _diem_ten_dong_client(left, top, right, bottom):
    """Điểm trên chữ tên, tránh ô tích đầu dòng."""
    return left + max(30, min((right - left) // 2, 80)), (top + bottom) // 2


def _bam_dong_chuot(hwnd, vi_tri, da_xong, chi_so_msaa=None):
    """Bấm chuột (ảo, không ăn thì thật) vào chữ tên nhân vật của dòng (tránh ô tích đầu dòng) trong bảng GAuto."""
    bang = _bang_nhan_vat(hwnd)
    rc = _rect_dong_bang(bang, chi_so_msaa) if chi_so_msaa else None
    if rc:
        return _bam_client_hoac_that(hwnd, bang, _diem_ten_dong_client(*rc), "dòng nhân vật", da_xong,
                                     GIAY_CHO_CHON_DONG / 2)
    l, t, w, h = vi_tri
    diem = (l + max(30, min(w // 2, 80)), t + h // 2)
    return _bam_ao_hoac_that(hwnd, bang, diem, "dòng nhân vật", da_xong, GIAY_CHO_CHON_DONG / 2)


def _diem_o_dau_dong(vi_tri):
    """Tâm ô tích đầu dòng (bật / tắt auto GAuto cho nhân vật) trong khung dòng của bảng nhân vật."""
    l, t, _, h = vi_tri
    return l + max(8, h // 2), t + h // 2


def bat_lai_auto_neu_tat(hwnd, ten_nv):
    """Ô đầu dòng (bật auto GAuto) đang tắt thì tích lại. Đang bật thì không bấm. Trả về True nếu vừa tích."""
    return bool(dat_dau_dong(hwnd, (ten_nv,), True))


def dat_dau_dong(hwnd, cac_ten, bat):
    """
    Tích / bỏ tích ô đầu dòng của các nhân vật cac_ten có trong bảng GAuto, bằng chuột (ảo, không ăn thì thật; MSAA
    không đổi được ô này). Trả về tên các dòng đã đổi.
    """
    can = [(i, ten) for i, ten, _, tich in danh_sach_nhan_vat(hwnd)
           if tich != bat and any(_khop_ten(ten, t) for t in cac_ten)]
    if not can:
        return []
    _hien_cua_so_gauto(hwnd)
    loi_cuoi = None
    for lan in range(SO_LAN_THU_DAU_DONG):
        try:
            return _dat_dau_dong_lan(hwnd, can, bat)
        except msaa.LoiMsaa as loi:
            loi_cuoi = loi
            time.sleep(GIAY_GIUA_THU_DAU_DONG)
            bang = _bang_nhan_vat(hwnd, bat_buoc=False)
            can = [(i, ten) for i, ten, _, tich in danh_sach_nhan_vat(hwnd)
                   if tich != bat and any(_khop_ten(ten, t) for t in cac_ten)] or can
            if not bang:
                continue
    viec = "tích" if bat else "bỏ tích"
    raise LoiGautoAcTac(f"không {viec} được ô đầu dòng trên GAuto ({loi_cuoi})") from loi_cuoi


def _dat_dau_dong_lan(hwnd, can, bat):
    da_doi = []
    bang = _bang_nhan_vat(hwnd)
    with _msaa(bang) as o:
        for i, ten in can:
            da_xong = lambda i=i, o=o, bang=bang: _dong_dang_tich(bang, i, o) == bat
            rc = _rect_dong_bang(bang, i)
            if rc:
                _bam_client_hoac_that(hwnd, bang, _diem_o_tich_client(*rc), "ô đầu dòng nhân vật", da_xong)
            else:
                try:
                    diem = _diem_o_dau_dong(o.vi_tri(i))
                except msaa.LoiMsaa:
                    raise
                _bam_ao_hoac_that(hwnd, bang, diem, "ô đầu dòng nhân vật", da_xong)
            if _dong_dang_tich(bang, i, o) != bat:
                raise LoiGautoAcTac(f"không {'tích' if bat else 'bỏ tích'} được ô đầu dòng «{ten}» trên GAuto")
            da_doi.append(ten)
    return da_doi


def _dang_tha_xuong(hwnd_combo):
    return bool(win32gui.SendMessage(hwnd_combo, win32con.CB_GETDROPPEDSTATE, 0, 0))


class _RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


def _tam_rect(left, top, right, bottom):
    return (left + right) // 2, (top + bottom) // 2


def _rect_dong_list(hwnd_list, chi_so):
    """Hình chữ nhật dòng chi_so trong list (client). None nếu không đọc được / AutoHoc 64-bit."""
    if not _gui_con_tro_toi_gauto():
        return None
    rc = _RECT()
    ok = ctypes.windll.user32.SendMessageW(int(hwnd_list), LB_GETITEMRECT, int(chi_so), ctypes.byref(rc))
    if not ok or rc.bottom <= rc.top:
        return None
    return rc.left, rc.top, rc.right, rc.bottom


def _diem_dong_map(hwnd_combo, hwnd_list, dich):
    """
    Tâm dòng dich. AutoHoc 32-bit: LB_GETITEMRECT. AutoHoc 64-bit: LB_GETITEMHEIGHT (số nguyên, không crash GAuto).
    Không dùng CB_GETITEMHEIGHT làm nguồn chính — màn 125/150% thấp hơn dòng thật, Vô Lượng Sơn thành Tung Sơn.
    """
    win32gui.SendMessage(hwnd_list, LB_SETTOPINDEX, dich, 0)
    win32gui.SendMessage(hwnd_combo, win32con.CB_SETTOPINDEX, dich, 0)
    rc = _rect_dong_list(hwnd_list, dich)
    if rc and rc[1] >= 0:
        return _tam_rect(*rc)
    dau = win32gui.SendMessage(hwnd_list, LB_GETTOPINDEX, 0, 0)
    cao = win32gui.SendMessage(hwnd_list, LB_GETITEMHEIGHT, 0, 0) \
        or win32gui.SendMessage(hwnd_combo, win32con.CB_GETITEMHEIGHT, 0, 0)
    l, _, r, _ = win32gui.GetClientRect(hwnd_list)
    return (l + r) // 2, (dich - dau) * cao + cao // 2


def _chon_dong_map(hwnd_combo, info, dich, bam):
    """Mở danh sách ô Map, bấm dòng dich; bam(hwnd_dich, diem) là chuột ảo hoặc thật. False nếu danh sách không mở."""
    try:
        bl, bt, br, bb = info.rcButton
        bam(hwnd_combo, win32gui.ClientToScreen(hwnd_combo, ((bl + br) // 2, (bt + bb) // 2)))
        if not _cho_dk(lambda: _dang_tha_xuong(hwnd_combo), GIAY_CHO_THA_XUONG):
            return False
        ds = info.hwndList
        x, y = _diem_dong_map(hwnd_combo, ds, dich)
        bam(ds, win32gui.ClientToScreen(ds, (x, y)))
        time.sleep(GIAY_NGHI_SAU_THAO_TAC or 0.5)
        return True
    finally:
        if _dang_tha_xuong(hwnd_combo):
            win32gui.SendMessage(hwnd_combo, win32con.CB_SHOWDROPDOWN, 0, 0)


def _chi_so_combo(hwnd_combo):
    """CB_GETCURSEL, -1 nếu chưa chọn. pywin32 đôi khi trả 4294967295 thay vì -1."""
    try:
        i = int(win32gui.SendMessage(hwnd_combo, win32con.CB_GETCURSEL, 0, 0))
    except (TypeError, ValueError, win32gui.error):
        return -1
    if i < 0 or i > 1000:
        return -1
    return i


def _giu_map(hwnd_combo, dich):
    """Đã đúng map dich và GAuto không trả lại map cũ sau GIAY_GIU_MAP giây."""
    if _chi_so_combo(hwnd_combo) != dich:
        return False
    time.sleep(GIAY_GIU_MAP)
    return _chi_so_combo(hwnd_combo) == dich


def _phim(vk):
    win32api.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)


def _focus_cua_so_gauto(hwnd):
    """Đưa GAuto lên trước để nhận phím. Trả về cửa sổ đang dùng trước đó."""
    cu = win32gui.GetForegroundWindow()
    _hien_cua_so_gauto(hwnd)
    if win32gui.GetForegroundWindow() != hwnd:
        try:
            win32gui.SetForegroundWindow(hwnd)
        except win32gui.error:
            pass
        time.sleep(0.15)
    if win32gui.GetForegroundWindow() != hwnd:
        try:
            _len_truoc(hwnd)
        except LoiKeoTha as loi:
            raise LoiGautoAcTac("không đưa được cửa sổ GAuto lên trước để chọn map") from loi
    return cu


def _tra_focus_gauto(cu, hwnd):
    if not cu or cu == hwnd or not win32gui.IsWindow(cu) or _la_cua_so_autohoc(cu):
        return
    try:
        _len_truoc(cu)
    except (LoiKeoTha, win32gui.error):
        pass


def _dat_focus_combo(hwnd_combo):
    """Focus ô Map. Combo có ô gõ thì Windows chuyển focus sang Edit con — mũi tên vẫn đổi dòng khi list đang mở."""
    user32 = ctypes.windll.user32
    tid_me = ctypes.windll.kernel32.GetCurrentThreadId()
    tid = user32.GetWindowThreadProcessId(int(hwnd_combo), None)
    user32.AttachThreadInput(tid_me, tid, True)
    try:
        user32.SetFocus(int(hwnd_combo))
    finally:
        user32.AttachThreadInput(tid_me, tid, False)


def _mo_danh_sach_map(hwnd_combo):
    """F4 mở list ô Map. List đóng thì mũi tên chỉ chạy trong chữ, không đổi map."""
    if _dang_tha_xuong(hwnd_combo):
        return True
    _phim(win32con.VK_F4)
    return _cho_dk(lambda: _dang_tha_xuong(hwnd_combo), GIAY_CHO_THA_XUONG)


def _buoc_mui_ten(hwnd, hwnd_combo, dich):
    """Đang mở list: bấm lên/xuống từng dòng tới dich. Dừng nếu một phím không đổi dòng."""
    hien = _chi_so_combo(hwnd_combo)
    if hien < 0:
        _phim(win32con.VK_HOME)
        time.sleep(0.08)
        hien = _chi_so_combo(hwnd_combo)
    if hien < 0:
        hien = 0
    huong = 1 if dich > hien else -1
    phim = win32con.VK_DOWN if huong > 0 else win32con.VK_UP
    for _ in range(abs(dich - hien)):
        if win32gui.GetForegroundWindow() != hwnd:
            raise LoiGautoAcTac("GAuto mất focus khi đang chọn map bằng phím")
        truoc = _chi_so_combo(hwnd_combo)
        _phim(phim)
        time.sleep(0.08)
        if _chi_so_combo(hwnd_combo) == truoc:
            _phim(phim)
            time.sleep(0.08)
        if _chi_so_combo(hwnd_combo) != truoc + huong:
            return False
    return _chi_so_combo(hwnd_combo) == dich


def _chon_map_bang_phim(hwnd, hwnd_combo, dich):
    """Focus ô Map, mở danh sách, mũi tên tới dich, Enter. Không bấm dòng (DPI lệch 1 dòng)."""
    if _dang_tha_xuong(hwnd_combo):
        win32gui.SendMessage(hwnd_combo, win32con.CB_SHOWDROPDOWN, 0, 0)
        time.sleep(0.1)
    with KHOA_CHUOT:
        cu = _focus_cua_so_gauto(hwnd)
        try:
            _dat_focus_combo(hwnd_combo)
            time.sleep(0.1)
            if not _mo_danh_sach_map(hwnd_combo):
                raise LoiGautoAcTac("không mở được danh sách ô Map trên GAuto")
            if not _buoc_mui_ten(hwnd, hwnd_combo, dich):
                if _dang_tha_xuong(hwnd_combo):
                    _phim(win32con.VK_ESCAPE)
                return False
            _phim(win32con.VK_RETURN)
            time.sleep(0.15)
        finally:
            _tra_focus_gauto(cu, hwnd)
    return _chi_so_combo(hwnd_combo) == dich


def chon_map(hwnd, hwnd_combo, ten_map):
    """
    Chọn map ten_map trong ô Map GAuto bằng phím (focus ô, F4, mũi tên, Enter).
    Trả về "phím" nếu đã đổi, False nếu đang đúng map.
    """
    cac = cac_map(hwnd_combo)
    dich = vi_tri_map(cac, ten_map)
    if dich is None:
        raise LoiGautoAcTac(f"GAuto không có map «{ten_map}» (có: {', '.join(cac)}) — chọn map khác trong AutoHoc")
    if _chi_so_combo(hwnd_combo) == dich:
        return False
    if not _chon_map_bang_phim(hwnd, hwnd_combo, dich) or not _giu_map(hwnd_combo, dich):
        raise LoiGautoAcTac(f"chọn map «{ten_map}» trên GAuto không ăn (đang «{doc_map(hwnd_combo)}»)")
    _nghi_sau_thao_tac()
    return "phím"


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


def _doi_dau_dong(hwnd, ten_nv, bat, in_log):
    """Tích / bỏ tích ô đầu dòng của đội trưởng; có đổi thì chờ GAuto nạp xong cài đặt (nạp lại xóa ô vừa tích)."""
    if not dat_dau_dong(hwnd, (ten_nv,), bat):
        return False
    if in_log:
        in_log(f"{'tích' if bat else 'bỏ tích'} ô đầu dòng «{ten_nv}» ({'bật' if bat else 'tắt'} auto GAuto)")
    time.sleep(GIAY_CHO_GAUTO_NAP)
    return True


def dat_cai_dat_ac_tac(hwnd, at, ten_nv, chi_so_dong=None, cache=None, ten_map=None, in_log=None):
    """
    Bật Ác Tặc GAuto cho đúng dòng ten_nv (trưởng nhóm đang login), không đụng dòng khác: tích ô đầu dòng (bật auto
    GAuto, chờ GAuto nạp cài đặt), chọn dòng, chọn map ten_map, các ô phụ, tích «Ác Tặc» một lần sau cùng.
    Ô đầu dòng AutoHoc tự tích ghi vào cache["dau_dong"] để tat_ac_tac bỏ tích lại. Trả về map GAuto đang chọn.
    Lỗi sau khi đã bấm vào GAuto: LoiGautoAcTac có da_thao_tac=True (bên gọi không thử lại cả chuỗi).
    """
    kiem_tra_quyen(hwnd)
    ly_do = _hien_cua_so_gauto(hwnd)
    if ly_do and in_log:
        in_log(f"mở cửa sổ GAuto ({ly_do})")
    # Chỉ đánh dấu đã thao tác sau khi tích ô đầu dòng xong — lỗi che cửa sổ lúc đầu vẫn cho thử lại khung.
    da_thao_tac = False
    try:
        nap_lai = _doi_dau_dong(hwnd, ten_nv, True, in_log)
        da_thao_tac = True
        if nap_lai and cache is not None:
            cache["dau_dong"] = ten_nv
        o = _chon_nhan_vat(hwnd, ten_nv, chi_so_dong)
        if ten_map:
            if "map" not in o:
                raise LoiGautoAcTac("không thấy ô Map trong khung Ác Tặc của GAuto")
            _dam_bao_dang_cai(hwnd, ten_nv)
            chon_map(hwnd, o["map"], ten_map)
        if O_AC_TAC not in o:
            raise LoiGautoAcTac("không thấy ô «Ác Tặc» trên GAuto")
        chay_pp = bool(at.get("chay_pathpoints"))
        for ten, bat in ((O_CHAY_PATHPOINTS, chay_pp), (O_CHAY_TIM, not chay_pp),
                         (O_CHO_PARTY, bool(at.get("cho_party", True))), (O_TU_TIM, bool(at.get("tu_tim", True))),
                         (O_AC_TAC, True)):
            if ten in o:
                _dam_bao_dang_cai(hwnd, ten_nv)
                dat_o_chuot(hwnd, o[ten], bat, ten)
        if nap_lai:
            _canh_gauto_nap_lai(hwnd, o, ten_nv, in_log)
        return doc_map(o["map"]) if "map" in o else ""
    except LoiGautoAcTac as loi:
        if da_thao_tac:
            loi.da_thao_tac = True
        raise
    finally:
        rut_bao_chuot(in_log)


def _canh_gauto_nap_lai(hwnd, o, ten_nv, in_log):
    """GAuto nạp lại cài đặt muộn hơn GIAY_CHO_GAUTO_NAP thì xóa ô «Ác Tặc» vừa tích: canh thêm, mất thì tích lại 1 lần."""
    for _ in range(int(GIAY_CANH_NAP_LAI * 2)):
        time.sleep(0.5)
        if not da_tich(o[O_AC_TAC]):
            _dam_bao_dang_cai(hwnd, ten_nv)
            dat_o_chuot(hwnd, o[O_AC_TAC], True, O_AC_TAC)
            if in_log:
                in_log("GAuto nạp lại cài đặt xóa ô «Ác Tặc», tích lại")
            return


def tat_ac_tac(hwnd, ten_nv, chi_so_dong=None, cache=None, in_log=None):
    """Bỏ tích «Ác Tặc» của ten_nv một lần; ô đầu dòng AutoHoc đã tự tích (cache["dau_dong"]) thì bỏ tích lại."""
    try:
        if cache is not None and cache.get("dau_dong"):
            _doi_dau_dong(hwnd, cache.pop("dau_dong"), False, in_log)
        o = _chon_nhan_vat(hwnd, ten_nv, chi_so_dong)
        _dam_bao_dang_cai(hwnd, ten_nv)
        dat_o_chuot(hwnd, o[O_AC_TAC], False, O_AC_TAC)
    finally:
        rut_bao_chuot(in_log)


def _tieu_test_gauto(bat):
    return "Test GAuto bật" if bat else "Test GAuto tắt"


def _mo_ta_o(bat):
    return "☑" if bat else "☐"


def _doc_lai_gauto(hwnd, ten_nv):
    """Đọc lại ô đầu dòng, các ô khung Ác Tặc và map đang chọn sau khi bấm."""
    ds = danh_sach_nhan_vat(hwnd)
    dong = next(((i, ten, chon, tich) for i, ten, chon, tich in ds if _khop_ten(ten, ten_nv)), None)
    if dong is None:
        raise LoiGautoAcTac(f"bảng GAuto không còn dòng «{ten_nv}»")
    o = khung_ac_tac(hwnd)
    cac_o = {ten: da_tich(hwnd_o) for ten, hwnd_o in ((ten, o[ten]) for ten in CAC_O_KHUNG_AC_TAC if ten in o)}
    map_dang = doc_map(o["map"]) if "map" in o else ""
    cac = cac_map(o["map"]) if "map" in o else []
    return dong, cac_o, map_dang, cac


def _dong_trang_thai(dong, cac_o, map_dang):
    _, ten, _, tich = dong
    o_chu = ", ".join(f"{ten_o} {_mo_ta_o(cac_o[ten_o])}" for ten_o in CAC_O_KHUNG_AC_TAC if ten_o in cac_o)
    return (f"ô đầu dòng «{ten}» {_mo_ta_o(tich)}, map «{map_dang or 'chưa chọn'}»"
            + (f", {o_chu}" if o_chu else ""))


def test_gauto(duong_dan, ten_nv, in_log, bat=True, cac_map_autohoc=(), at=None):
    """
    Nút «Test GAuto bật» / «Test GAuto tắt». Cùng đường với lúc tới khung: bật thì tích ô đầu dòng, chọn map, tích
    Ác Tặc và để nguyên; tắt thì bỏ tích cả hai. Dòng OK chỉ ghi sau khi đọc lại ô trên GAuto, không ghi theo cú bấm.
    ten_nv rỗng thì dùng dòng đang chọn. LoiGautoAcTac khi hỏng hoặc đọc lại không đúng.
    """
    tieu = _tieu_test_gauto(bat)

    def log(chu):
        in_log(f"{tieu}: {chu}")

    log(f"1) tìm cửa sổ GAuto ({duong_dan or 'chưa nhập đường dẫn'})")
    hwnd = tim_cua_so_quan_ly(duong_dan)
    log(f"   thấy «{tom_tat_cua_so(hwnd)}»")
    ly = _hien_cua_so_gauto(hwnd)
    log(f"   cửa sổ {'vừa mở (' + ly + ')' if ly else 'đang hiện'}")
    q_gauto, q_auto = gauto_la_admin(hwnd), autohoc_la_admin()
    log(f"2) quyền: GAuto {'Admin' if q_gauto else 'thường'}, AutoHoc {'Admin' if q_auto else 'thường'}")
    kiem_tra_quyen(hwnd)
    ds = danh_sach_nhan_vat(hwnd)
    log("3) bảng nhân vật: " + ("; ".join(
        f"{ten}{' [đang chọn]' if chon else ''}{' [ô đầu dòng ☑]' if tich else ' [ô đầu dòng ☐]'}"
        for _, ten, chon, tich in ds) or "trống"))
    if not ds:
        raise LoiGautoAcTac("bảng nhân vật GAuto trống — đăng nhập nhân vật trong GAuto trước")
    if ten_nv:
        id_dong = tim_chi_so_dong_theo_ten(hwnd, ten_nv)
    else:
        id_dong = next((i for i, _, chon, _ in ds if chon), ds[0][0])
        ten_nv = next(t for i, t, _, _ in ds if i == id_dong)
    log(f"4) chọn dòng «{ten_nv}»")
    chon_dong(hwnd, id_dong, ten_nv)
    log(f"   tab cài đặt đang «{nhan_vat_dang_cai(hwnd) or '?'}»")
    log("5) đọc khung Ác Tặc trước khi bấm")
    dong, cac_o, map_dang, cac = _doc_lai_gauto(hwnd, ten_nv)
    log(f"   {_dong_trang_thai(dong, cac_o, map_dang)}")
    if cac:
        log(f"   GAuto có map: {', '.join(cac)}")
    thieu_map = [m for m in cac_map_autohoc if vi_tri_map(cac, m) is None]
    if thieu_map:
        log(f"   GAuto không có map {', '.join(thieu_map)} (đang tích trong AutoHoc)")
    map_dau = next((m for m in cac_map_autohoc if vi_tri_map(cac, m) is not None), None)
    try:
        if bat:
            if not map_dau:
                raise LoiGautoAcTac("AutoHoc chưa tích map nào mà GAuto có — tích map trong danh sách Ác Tặc")
            if cac_map_autohoc and cac_map_autohoc[0] != map_dau:
                log(f"   map đầu AutoHoc «{cac_map_autohoc[0]}» không có trên GAuto, dùng «{map_dau}»")
            log(f"6) bật như lúc tới khung: ô đầu dòng, map «{map_dau}», ô Ác Tặc — xong để nguyên, không tắt lại")
            dat_cai_dat_ac_tac(hwnd, at or {}, ten_nv, id_dong, ten_map=map_dau, in_log=log)
        else:
            log("6) tắt: bỏ tích ô đầu dòng, rồi bỏ tích ô Ác Tặc")
            if not _doi_dau_dong(hwnd, ten_nv, False, log):
                log(f"   ô đầu dòng «{ten_nv}» đang tắt sẵn, không bấm")
            o = _chon_nhan_vat(hwnd, ten_nv, id_dong)
            if O_AC_TAC not in o:
                raise LoiGautoAcTac("không thấy ô «Ác Tặc» trên GAuto")
            cach = dat_o_chuot(hwnd, o[O_AC_TAC], False, O_AC_TAC)
            if cach is False:
                log("   ô «Ác Tặc» đang tắt sẵn, không bấm")
            else:
                log(f"   bỏ tích ô «Ác Tặc» bằng chuột {cach}")
        log("7) đọc lại trên GAuto")
        dong, cac_o, map_dang, _ = _doc_lai_gauto(hwnd, ten_nv)
        log(f"   {_dong_trang_thai(dong, cac_o, map_dang)}")
        _, _, _, tich_dau = dong
        ac_bat = bool(cac_o.get(O_AC_TAC))
        if bat:
            lech = []
            if not tich_dau:
                lech.append("ô đầu dòng vẫn ☐")
            if not ac_bat:
                lech.append("ô Ác Tặc vẫn ☐")
            if map_dau and vi_tri_map([map_dang], map_dau) is None:
                lech.append(f"map đang «{map_dang or 'chưa chọn'}», cần «{map_dau}»")
            if lech:
                raise LoiGautoAcTac("bật không ăn — " + "; ".join(lech))
            log(f"OK — đã bật, để nguyên: ô đầu dòng ☑, Ác Tặc ☑, map «{map_dang}»")
        else:
            lech = []
            if tich_dau:
                lech.append("ô đầu dòng vẫn ☑")
            if ac_bat:
                lech.append("ô Ác Tặc vẫn ☑")
            if lech:
                raise LoiGautoAcTac("tắt không ăn — " + "; ".join(lech))
            log("OK — đã tắt: ô đầu dòng ☐, Ác Tặc ☐")
    finally:
        rut_bao_chuot(log)
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
