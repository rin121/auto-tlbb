"""
Chạy lệnh Lua bên trong Game.exe, thông qua dll\\autohoc_lua.dll.

Ví dụ:
    lua = LuaGame(hwnd)
    lua.chay('return Player:GetData("LEVEL")')          -> b"30"
    lua.chay('return PlayerPackage:EnumItem("base", 20):GetName()')

Nạp DLL: Python mở tiến trình game, ghi đường dẫn DLL vào bộ nhớ của game, rồi tạo một luồng
trong game chạy LoadLibraryA(đường_dẫn). Game.exe là 32-bit còn Python là 64-bit, nên địa chỉ
LoadLibraryA phải tính từ kernel32.dll bản 32-bit (thư mục SysWOW64).
"""
import ctypes
import ctypes.wintypes as wt
import mmap
import os
import struct
import time

import pefile
import pywintypes
import win32api
import win32event
import win32process

from thu_muc import THU_MUC_APP

DUONG_DAN_DLL = os.path.join(THU_MUC_APP, "dll", "autohoc_lua.dll")
TEN_DLL = "autohoc_lua.dll"

# Phải khớp với autohoc_lua.c
KICH_THUOC_CHUOI = 65536
TIN_NHAN_AUTOHOC = 0x8000 + 0x2B1  # WM_APP + 0x2B1
VI_TRI_SAN_SANG, VI_TRI_TRANG_THAI, VI_TRI_MA_LOI = 0, 4, 8
VI_TRI_LENH = 12
VI_TRI_KET_QUA = VI_TRI_LENH + KICH_THUOC_CHUOI
KICH_THUOC_VUNG_CHUNG = VI_TRI_KET_QUA + KICH_THUOC_CHUOI
RANH, CO_LENH, XONG = 0, 1, 2
THONG_BAO_LOI = {
    1: "chưa bắt được lua_State của game",
    2: "lỗi cú pháp Lua",
    3: "lỗi khi chạy Lua",
}

PROCESS_QUYEN_NAP_DLL = 0x0002 | 0x0008 | 0x0010 | 0x0020 | 0x0400
MEM_COMMIT_RESERVE, MEM_RELEASE, PAGE_READWRITE = 0x3000, 0x8000, 0x04
LIST_MODULES_32BIT = 0x01
FILE_MAP_ALL_ACCESS = 0xF001F

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

kernel32.OpenProcess.restype = wt.HANDLE
kernel32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
kernel32.VirtualAllocEx.restype = ctypes.c_void_p
kernel32.VirtualAllocEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD, wt.DWORD]
kernel32.VirtualFreeEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, wt.DWORD]
kernel32.WriteProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                        ctypes.POINTER(ctypes.c_size_t)]
kernel32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                       ctypes.POINTER(ctypes.c_size_t)]
kernel32.CreateRemoteThread.restype = wt.HANDLE
kernel32.CreateRemoteThread.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_void_p,
                                        ctypes.c_void_p, wt.DWORD, ctypes.POINTER(wt.DWORD)]
kernel32.WaitForSingleObject.argtypes = [wt.HANDLE, wt.DWORD]
kernel32.GetExitCodeThread.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]
kernel32.CloseHandle.argtypes = [wt.HANDLE]
kernel32.OpenFileMappingW.restype = wt.HANDLE
kernel32.OpenFileMappingW.argtypes = [wt.DWORD, wt.BOOL, wt.LPCWSTR]
psapi.EnumProcessModulesEx.argtypes = [wt.HANDLE, ctypes.POINTER(ctypes.c_void_p), wt.DWORD,
                                       ctypes.POINTER(wt.DWORD), wt.DWORD]
psapi.GetModuleBaseNameW.argtypes = [wt.HANDLE, ctypes.c_void_p, wt.LPWSTR, wt.DWORD]


class LoiLua(Exception):
    pass


def ten_vung_chung(pid):
    return f"Local\\AutoHoc_Lua_{pid}"


def cac_module_32bit(handle_tien_trinh):
    """Trả về dict {tên module viết thường: địa chỉ nạp} của tiến trình 32-bit."""
    mang = (ctypes.c_void_p * 1024)()
    can = wt.DWORD()
    if not psapi.EnumProcessModulesEx(handle_tien_trinh, mang, ctypes.sizeof(mang), ctypes.byref(can),
                                      LIST_MODULES_32BIT):
        raise ctypes.WinError(ctypes.get_last_error())
    ket_qua = {}
    ten = ctypes.create_unicode_buffer(260)
    for i in range(can.value // ctypes.sizeof(ctypes.c_void_p)):
        psapi.GetModuleBaseNameW(handle_tien_trinh, mang[i], ten, 260)
        ket_qua[ten.value.lower()] = mang[i]
    return ket_qua


def _cho_module_trong_tien_trinh(handle_tien_trinh, ten_module, lan_thu=200, giay_buoc=0.05):
    """
    Game mở CREATE_SUSPENDED chưa nạp kernel32 — chờ trước khi inject DLL.
    """
    khoa = (ten_module or "").lower()
    for _ in range(lan_thu):
        try:
            cac_module = cac_module_32bit(handle_tien_trinh)
        except OSError:
            time.sleep(giay_buoc)
            continue
        if khoa in cac_module:
            return cac_module[khoa]
        time.sleep(giay_buoc)
    raise LoiLua(f"tiến trình game chưa nạp {ten_module} (chờ inject DLL quá lâu)")


def rva_ham_xuat(duong_dan_dll, ten_ham):
    pe = pefile.PE(duong_dan_dll, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    for ham in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        if ham.name == ten_ham.encode():
            return ham.address
    raise LookupError(f"Không thấy hàm {ten_ham} trong {duong_dan_dll}")


def doc_bo_nho(handle_tien_trinh, dia_chi, so_byte):
    bo_dem = ctypes.create_string_buffer(so_byte)
    da_doc = ctypes.c_size_t()
    if not kernel32.ReadProcessMemory(handle_tien_trinh, dia_chi, bo_dem, so_byte, ctypes.byref(da_doc)):
        raise ctypes.WinError(ctypes.get_last_error())
    return bo_dem.raw[:da_doc.value]


def mo_tien_trinh(pid):
    handle = kernel32.OpenProcess(PROCESS_QUYEN_NAP_DLL, False, pid)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    return handle


def da_nap_dll(pid):
    handle = mo_tien_trinh(pid)
    try:
        return TEN_DLL in cac_module_32bit(handle)
    finally:
        kernel32.CloseHandle(handle)


def nap_dll(pid):
    """Nạp autohoc_lua.dll vào tiến trình game (nếu chưa nạp). Trả về True nếu vừa nạp."""
    return nap_dll_duong_dan(pid, DUONG_DAN_DLL, TEN_DLL)


def nap_dll_duong_dan(pid, duong_dan_dll, ten_dll, cho_kernel_lan_thu=200, cho_kernel_giay_buoc=0.05):
    """Nạp một DLL 32-bit vào tiến trình game (nếu chưa nạp). Trả về True nếu vừa nạp."""
    handle = mo_tien_trinh(pid)
    try:
        cac_module = cac_module_32bit(handle)
        if ten_dll in cac_module:
            return False

        dia_chi_kernel = _cho_module_trong_tien_trinh(
            handle, "kernel32.dll", lan_thu=cho_kernel_lan_thu, giay_buoc=cho_kernel_giay_buoc)
        dia_chi_loadlibrary = dia_chi_kernel + rva_ham_xuat(
            r"C:\Windows\SysWOW64\kernel32.dll", "LoadLibraryA")

        duong_dan = duong_dan_dll.encode("mbcs") + b"\0"
        vung_nho = kernel32.VirtualAllocEx(handle, None, len(duong_dan), MEM_COMMIT_RESERVE, PAGE_READWRITE)
        if not vung_nho:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            kernel32.WriteProcessMemory(handle, vung_nho, duong_dan, len(duong_dan), None)
            luong = kernel32.CreateRemoteThread(handle, None, 0, dia_chi_loadlibrary, vung_nho, 0, None)
            if not luong:
                raise ctypes.WinError(ctypes.get_last_error())
            kernel32.WaitForSingleObject(luong, 10000)
            ma_thoat = wt.DWORD()
            kernel32.GetExitCodeThread(luong, ctypes.byref(ma_thoat))
            kernel32.CloseHandle(luong)
            if ma_thoat.value == 0:
                raise LoiLua("LoadLibraryA trong game thất bại (DLL không nạp được)")
        finally:
            kernel32.VirtualFreeEx(handle, vung_nho, 0, MEM_RELEASE)
        return True
    finally:
        kernel32.CloseHandle(handle)


class LuaGame:
    def __init__(self, hwnd):
        self.hwnd = hwnd
        try:
            luong, self.pid = win32process.GetWindowThreadProcessId(hwnd)
        except pywintypes.error as loi:
            raise LoiLua(f"cửa sổ game đã đóng ({loi.strerror})") from loi
        if not luong:
            raise LoiLua("cửa sổ game đã đóng")
        self._vung = None
        # Mỗi lúc chỉ một script được gửi lệnh vào game (vd. auto đang chạy và mở thêm thu_lua.py).
        self._khoa = win32event.CreateMutex(None, False, f"Local\\AutoHoc_Lua_Khoa_{self.pid}")

    def _mo_vung_chung(self, giay_cho=5):
        if self._vung is not None:
            return
        ten = ten_vung_chung(self.pid)
        het_han = time.time() + giay_cho
        while True:
            handle = kernel32.OpenFileMappingW(FILE_MAP_ALL_ACCESS, False, ten)
            if handle:
                kernel32.CloseHandle(handle)
                self._vung = mmap.mmap(-1, KICH_THUOC_VUNG_CHUNG, tagname=ten)
                break
            if time.time() > het_han:
                raise LoiLua("DLL đã nạp nhưng chưa tạo vùng nhớ chung")
            time.sleep(0.1)
        while self._doc_so(VI_TRI_SAN_SANG) != 1:
            if time.time() > het_han:
                raise LoiLua("DLL chưa sẵn sàng (không tìm thấy cửa sổ game?)")
            time.sleep(0.1)

    def _doc_so(self, vi_tri):
        return struct.unpack_from("<i", self._vung, vi_tri)[0]

    def _ghi_so(self, vi_tri, gia_tri):
        struct.pack_into("<i", self._vung, vi_tri, gia_tri)

    def ket_noi(self):
        # DLL không bao giờ gỡ khỏi game và mỗi LuaGame gắn với một pid: đã mở vùng nhớ chung thì khỏi duyệt lại
        # danh sách module của game (vài trăm lời gọi Win32) ở mỗi lệnh Lua.
        if self._vung is not None:
            return
        try:
            nap_dll(self.pid)
        except LoiLua:
            raise
        except (OSError, LookupError, pywintypes.error) as loi:
            # Game vừa tắt (mất kết nối): tiến trình không còn module / không mở được.
            raise LoiLua(f"không nạp được DLL vào game (game đã tắt?): {loi!r}") from loi
        self._mo_vung_chung()

    def chay(self, ma_lua, giay_cho=3, so_lan_thu=5):
        """
        Chạy đoạn Lua trong game, trả về kết quả dạng bytes (chuỗi gốc của game, chưa đổi bảng mã).
        Đoạn Lua nên có "return ..." nếu muốn lấy kết quả.
        """
        self.ket_noi()
        # Lua 5.0: tostring() báo lỗi nếu không nhận được giá trị nào (vd. lệnh UseItem không trả về gì),
        # nên gán vào biến trước; không có kết quả thì trả về chuỗi rỗng.
        ma = ("local ket_qua = (function()\n" + ma_lua + "\nend)()\n"
              "if ket_qua == nil then return \"\" end\n"
              "return tostring(ket_qua)").encode("latin-1")
        if len(ma) >= KICH_THUOC_CHUOI:
            raise LoiLua("Đoạn Lua quá dài")

        if win32event.WaitForSingleObject(self._khoa, 15000) == win32event.WAIT_TIMEOUT:
            raise LoiLua("Script khác đang gửi lệnh vào game quá lâu")
        try:
            for lan in range(so_lan_thu):
                self._vung[VI_TRI_LENH:VI_TRI_LENH + len(ma) + 1] = ma + b"\0"
                self._ghi_so(VI_TRI_TRANG_THAI, CO_LENH)
                try:
                    win32api.PostMessage(self.hwnd, TIN_NHAN_AUTOHOC, 0, 0)
                except pywintypes.error as loi:
                    self._ghi_so(VI_TRI_TRANG_THAI, RANH)
                    raise LoiLua(f"cửa sổ game đã đóng ({loi.strerror})") from loi

                het_han = time.time() + giay_cho
                while self._doc_so(VI_TRI_TRANG_THAI) != XONG:
                    if time.time() > het_han:
                        self._ghi_so(VI_TRI_TRANG_THAI, RANH)
                        raise LoiLua("Game không phản hồi (đang loading hoặc bị treo?)")
                    time.sleep(0.01)

                ma_loi = self._doc_so(VI_TRI_MA_LOI)
                ket_thuc = self._vung.find(b"\0", VI_TRI_KET_QUA, VI_TRI_KET_QUA + KICH_THUOC_CHUOI)
                if ket_thuc < 0:
                    ket_thuc = VI_TRI_KET_QUA + KICH_THUOC_CHUOI
                ket_qua = self._vung[VI_TRI_KET_QUA:ket_thuc]
                self._ghi_so(VI_TRI_TRANG_THAI, RANH)

                if ma_loi == 0:
                    return ket_qua
                if ma_loi == 1 and lan < so_lan_thu - 1:
                    time.sleep(1)
                    continue
                raise LoiLua(f"{THONG_BAO_LOI.get(ma_loi, ma_loi)}: {ket_qua.decode('latin-1')}")
        finally:
            win32event.ReleaseMutex(self._khoa)
