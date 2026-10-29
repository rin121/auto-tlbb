"""
MSAA (IAccessible, oleacc.dll) qua ctypes: đọc tên / trạng thái control, chọn dòng ListView, chuyển tab, bấm ô tích
của ứng dụng khác mà không bấm chuột thật (cửa sổ bị che / ẩn sau vẫn được). Không cần comtypes.
Ứng dụng đích chạy quyền Admin thì tiến trình gọi cũng phải chạy Admin (Windows chặn, lỗi E_ACCESSDENIED).
"""
import ctypes
from ctypes import POINTER, WINFUNCTYPE, byref, c_long, c_ushort, c_void_p, c_wchar_p, c_int64

OBJID_CLIENT = -4
CHILDID_SELF = 0
VT_I4 = 3
STATE_SYSTEM_UNAVAILABLE = 0x1
STATE_SYSTEM_SELECTED = 0x2
STATE_SYSTEM_CHECKED = 0x10
STATE_SYSTEM_INVISIBLE = 0x8000
SELFLAG_TAKEFOCUS = 0x1
SELFLAG_TAKESELECTION = 0x2

HRESULT = c_long


class VARIANT(ctypes.Structure):
    _fields_ = [("vt", c_ushort), ("r1", c_ushort), ("r2", c_ushort), ("r3", c_ushort),
                ("val", c_int64), ("pad", c_int64)]


class GUID(ctypes.Structure):
    _fields_ = [("d1", ctypes.c_uint32), ("d2", ctypes.c_uint16), ("d3", ctypes.c_uint16),
                ("d4", ctypes.c_ubyte * 8)]


IID_IACCESSIBLE = GUID(0x618736E0, 0x3C3D, 0x11CF, (ctypes.c_ubyte * 8)(0x81, 0x0C, 0x00, 0xAA, 0x00, 0x38, 0x9B, 0x71))

# Thứ tự hàm trong vtable IAccessible (IUnknown 0-2, IDispatch 3-6).
_RELEASE = 2
_CHILD_COUNT = 8
_NAME = 10
_ROLE = 13
_STATE = 14
_DEFAULT_ACTION = 20
_SELECT = 21
_LOCATION = 22
_DO_DEFAULT_ACTION = 25

_oleacc = ctypes.windll.oleacc
_oleaut32 = ctypes.windll.oleaut32
_ole32 = ctypes.windll.ole32
_oleaut32.SysFreeString.argtypes = [c_void_p]


class LoiMsaa(Exception):
    pass


def khoi_tao_com():
    _ole32.CoInitialize(None)


def _con(id_con):
    return VARIANT(VT_I4, 0, 0, 0, int(id_con), 0)


class DoiTuong:
    """IAccessible của một cửa sổ (OBJID_CLIENT); id_con = 0 là chính nó, 1..n là phần tử con (dòng, tab...)."""

    def __init__(self, hwnd):
        khoi_tao_com()
        self.hwnd = hwnd
        self.ptr = c_void_p()
        hr = _oleacc.AccessibleObjectFromWindow(hwnd, ctypes.c_uint32(OBJID_CLIENT & 0xFFFFFFFF),
                                                byref(IID_IACCESSIBLE), byref(self.ptr))
        if hr != 0 or not self.ptr:
            raise LoiMsaa(f"không đọc được control (hwnd {hwnd}, mã {hr & 0xFFFFFFFF:#x}) — "
                          "ứng dụng chạy Admin thì AutoHoc cũng phải chạy Admin")

    def _ham(self, chi_so, *argtypes):
        vtbl = ctypes.cast(self.ptr, POINTER(POINTER(c_void_p))).contents
        return WINFUNCTYPE(HRESULT, c_void_p, *argtypes)(vtbl[chi_so])

    def _goi(self, chi_so, argtypes, *args):
        hr = self._ham(chi_so, *argtypes)(self.ptr, *args)
        if hr < 0:
            raise LoiMsaa(f"lỗi MSAA {hr & 0xFFFFFFFF:#x} (hwnd {self.hwnd})")
        return hr

    def dong(self):
        if self.ptr:
            self._ham(_RELEASE)(self.ptr)
            self.ptr = c_void_p()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.dong()

    def so_con(self):
        n = c_long()
        self._goi(_CHILD_COUNT, (POINTER(c_long),), byref(n))
        return n.value

    def _chuoi(self, chi_so, id_con):
        bstr = c_void_p()
        hr = self._goi(chi_so, (VARIANT, POINTER(c_void_p)), _con(id_con), byref(bstr))
        if hr != 0 or not bstr:
            return ""
        try:
            return ctypes.wstring_at(bstr.value)
        finally:
            _oleaut32.SysFreeString(bstr)

    def ten(self, id_con=CHILDID_SELF):
        return self._chuoi(_NAME, id_con)

    def hanh_dong(self, id_con=CHILDID_SELF):
        return self._chuoi(_DEFAULT_ACTION, id_con)

    def _so(self, chi_so, id_con):
        kq = VARIANT()
        self._goi(chi_so, (VARIANT, POINTER(VARIANT)), _con(id_con), byref(kq))
        return int(kq.val & 0xFFFFFFFF) if kq.vt == VT_I4 else 0

    def vai_tro(self, id_con=CHILDID_SELF):
        return self._so(_ROLE, id_con)

    def trang_thai(self, id_con=CHILDID_SELF):
        return self._so(_STATE, id_con)

    def da_tich(self, id_con=CHILDID_SELF):
        return bool(self.trang_thai(id_con) & STATE_SYSTEM_CHECKED)

    def dang_chon(self, id_con=CHILDID_SELF):
        return bool(self.trang_thai(id_con) & STATE_SYSTEM_SELECTED)

    def chon(self, id_con):
        self._goi(_SELECT, (c_long, VARIANT), SELFLAG_TAKEFOCUS | SELFLAG_TAKESELECTION, _con(id_con))

    def bam(self, id_con=CHILDID_SELF):
        self._goi(_DO_DEFAULT_ACTION, (VARIANT,), _con(id_con))

    def vi_tri(self, id_con=CHILDID_SELF):
        l, t, w, h = c_long(), c_long(), c_long(), c_long()
        self._goi(_LOCATION, (POINTER(c_long),) * 4 + (VARIANT,), byref(l), byref(t), byref(w), byref(h),
                  _con(id_con))
        return l.value, t.value, w.value, h.value

    def cac_ten_con(self):
        return [self.ten(i) for i in range(1, self.so_con() + 1)]
