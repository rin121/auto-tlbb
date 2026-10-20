"""
TỰ GIẢI MÃ KIỂM TRA (4 chữ số, hộp TextValidate): lúc tạo nhân vật (tao_nhan_vat.py), và lúc đăng nhập nếu
bật "Giải mã kiểm tra khi vào game" ở tab Tài khoản (dang_nhap.py; tắt thì nhập mã cố định trong cài đặt).

Server không gửi đáp án xuống client, chỉ gửi ảnh. Mọi loại mã kiểm tra (đăng nhập, tạo nhân vật, giao dịch,
lên cấp) đều được hàm 0x498070 chép vào DataPool (con trỏ ở 0x645AE0) + 0x4A5E8: 576 byte = ảnh 128x36,
mỗi điểm 1 bit, hàng 16 byte, bit cao bên trái. Ảnh gồm một dải nhiễu đen lớn, 4 chữ số vẽ đảo màu (XOR)
đè lên và các chấm nhiễu.

Cách đọc: lọc trung vị cỡ lớn xóa nét chữ (nét chỉ dày 1-2 điểm) để còn lại dải nhiễu -> XOR với ảnh gốc
còn nét chữ số -> bỏ các đốm nhỏ -> ddddocr đọc. ddddocr hay bỏ sót chữ số bị nhiễu đè, nên với mỗi cỡ lọc
đọc cả ảnh (vài độ phóng, chỉ lấy lần ra đủ 4 số) và đọc riêng từng ô 32 điểm (mỗi chữ số nằm trong một ô),
rồi bỏ phiếu theo từng vị trí. Vị trí nào không có phiếu thì coi như ảnh khó đọc (nên đổi ảnh khác).
"""
import io
import os
import platform
import struct
import subprocess
import sys
import threading
import types
from collections import Counter

from PIL import Image, ImageChops, ImageFilter

from lua_game import doc_bo_nho, kernel32, mo_tien_trinh

CON_TRO_DATAPOOL = 0x645AE0
LECH_ANH = 0x4A5E8
RONG, CAO = 128, 36
SO_BYTE_ANH = RONG * CAO // 8
HAM_CHEP_ANH = 0x498070
MAU_HAM_CHEP_ANH = bytes.fromhex("558bec83ec14a1044964008945fc33c08945ee538945f2568b75088bd98945f657668945fa8b450c"
                                 "8dbbe8a50400b990000000f3a5")
SO_CHU_SO = 4
RONG_O = RONG // SO_CHU_SO
LE_O = 4
VIEN_O = 8
DO_PHONG_O = 3
CAC_CO_LOC = (7, 9, 11)
CAC_DO_PHONG = (2, 3)
DOM_NHO_NHAT = 6
# ddddocr đọc không giới hạn ký tự, hay nhầm chữ số thành chữ cái trông giống.
DOI_KY_TU = str.maketrans({"O": "0", "o": "0", "D": "0", "Q": "0", "U": "0", "u": "0",
                           "I": "1", "l": "1", "i": "1", "J": "1", "j": "1", "|": "1", "L": "1",
                           "Z": "2", "z": "2", "A": "4", "y": "4", "S": "5", "s": "5",
                           "b": "6", "G": "6", "T": "7", "B": "8", "g": "9", "q": "9"})

_khoa = threading.Lock()
_ocr = None


def _dam_bao_cv2_gia():
    """ddddocr import cv2 ở đầu module; exe không đóng gói OpenCV."""
    if "cv2" in sys.modules:
        return
    try:
        import cv2  # noqa: F401
    except ImportError:
        sys.modules["cv2"] = types.ModuleType("cv2")


class LoiGiaiCaptcha(Exception):
    pass


_dam_bao_cv2_gia()


class _OcrSubprocess:
    """Win7: OCR qua tiến trình python.exe thường trực trong ocr_py\\ (onnx không chạy được trong exe PyInstaller).
    Giao thức xem dong_goi\\ocr_py_win7\\giai_ocr.py."""

    def __init__(self, python_exe, script):
        self._lenh = [python_exe, script]
        self._tien_trinh = None

    def _doc_tra_loi(self):
        dau = self._tien_trinh.stdout.read(4)
        if len(dau) < 4:
            loi = self._tien_trinh.stderr.read().decode("utf-8", "replace").strip()
            self._tat()
            raise LoiGiaiCaptcha(f"ocr_py dừng đột ngột: {loi[-300:] or 'không có thông báo lỗi'}")
        n = struct.unpack("<I", dau)[0]
        return self._tien_trinh.stdout.read(n).decode("utf-8", "replace")

    def _khoi_dong(self):
        self._tien_trinh = subprocess.Popen(
            self._lenh, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if self._doc_tra_loi() != "OK":
            self._tat()
            raise LoiGiaiCaptcha("ocr_py khởi động không đúng giao thức")

    def _tat(self):
        if self._tien_trinh:
            try:
                self._tien_trinh.kill()
            except OSError:
                pass
            self._tien_trinh = None

    def classification(self, img_bytes, png_fix=False):  # noqa: ARG002
        if self._tien_trinh is None or self._tien_trinh.poll() is not None:
            self._khoi_dong()
        try:
            self._tien_trinh.stdin.write(struct.pack("<I", len(img_bytes)) + img_bytes)
            self._tien_trinh.stdin.flush()
        except OSError as loi:
            self._tat()
            raise LoiGiaiCaptcha(f"ocr_py không nhận ảnh ({loi})") from None
        return self._doc_tra_loi()


def _thu_muc_auto_chay():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _duong_ocr_py():
    thu_muc = os.path.join(_thu_muc_auto_chay(), "ocr_py")
    return thu_muc, os.path.join(thu_muc, "python.exe"), os.path.join(thu_muc, "giai_ocr.py")


def _nen_dung_ocr_subprocess():
    if os.environ.get("AUTOHOC_OCR_SUBPROCESS") == "1":
        return True
    if platform.system() == "Windows" and platform.release() == "7":
        return True
    return os.path.isfile(_duong_ocr_py()[1])


def kiem_tra_ocr_win7():
    """Chuỗi cảnh báo nếu máy cần bộ OCR Win7 mà thiếu file; None nếu ổn hoặc không cần."""
    if not _nen_dung_ocr_subprocess():
        return None
    thu_muc, py, script = _duong_ocr_py()
    thieu = [os.path.relpath(p, _thu_muc_auto_chay()) for p in (py, script) if not os.path.isfile(p)]
    if thieu:
        return (f"Win7: thiếu {', '.join(thieu)} cạnh AutoHoc.exe nên không tự giải được mã kiểm tra. "
                f"Copy CẢ thư mục win7 (có ocr_py\\) từ bản build — "
                f"không chỉ copy mỗi AutoHoc.exe. (Đang tìm ở {thu_muc})")
    # vcomp140.dll chỉ có từ bản ocr_py kèm runtime VC++ 14.29; bản cũ dùng msvcp140 Win8+ -> lỗi get_all_providers.
    if not os.path.isfile(os.path.join(thu_muc, "vcomp140.dll")):
        return (f"Win7: thư mục ocr_py đang là bản CŨ (thiếu vcomp140.dll) nên không giải được mã kiểm tra. "
                f"Xóa hẳn {thu_muc} rồi copy lại thư mục ocr_py từ bản build win7 mới nhất.")
    return None


def _lay_ocr_subprocess():
    canh_bao = kiem_tra_ocr_win7()
    if canh_bao:
        raise LoiGiaiCaptcha(canh_bao)
    _, py, script = _duong_ocr_py()
    return _OcrSubprocess(py, script)


def doc_anh(pid):
    """576 byte ảnh mã kiểm tra đang lưu trong game."""
    handle = mo_tien_trinh(pid)
    try:
        if doc_bo_nho(handle, HAM_CHEP_ANH, len(MAU_HAM_CHEP_ANH)) != MAU_HAM_CHEP_ANH:
            raise LoiGiaiCaptcha(f"bản Game.exe này khác bản đã dịch ngược (code ở {HAM_CHEP_ANH:#x})")
        datapool = struct.unpack("<I", doc_bo_nho(handle, CON_TRO_DATAPOOL, 4))[0]
        anh = doc_bo_nho(handle, datapool + LECH_ANH, SO_BYTE_ANH)
    finally:
        kernel32.CloseHandle(handle)
    if len(anh) != SO_BYTE_ANH:
        raise LoiGiaiCaptcha("không đọc được ảnh mã kiểm tra")
    return anh


def _lay_ocr():
    global _ocr
    if _ocr is None:
        if _nen_dung_ocr_subprocess():
            _ocr = _lay_ocr_subprocess()
            return _ocr
        _dam_bao_cv2_gia()
        try:
            import onnxruntime  # noqa: F401 — ddddocr import onnx ở đầu __init__
        except ImportError as loi:
            raise LoiGiaiCaptcha(
                f"onnxruntime không chạy được ({loi}). "
                "Win7: dùng win7\\AutoHoc.exe bản mới, cài VC++ 2015–2022 x64."
            ) from None
        try:
            import ddddocr
        except ImportError as loi:
            raise LoiGiaiCaptcha(f"thiếu thư viện ddddocr ({loi})") from None
        try:
            _ocr = ddddocr.DdddOcr(show_ad=False)
        except Exception as loi:
            raise LoiGiaiCaptcha(f"không khởi tạo ddddocr/onnx ({loi})") from None
    return _ocr


def _bo_dom_nho(anh):
    """Giữ lại các cụm điểm trắng (liền nhau theo 8 hướng) có từ DOM_NHO_NHAT điểm trở lên."""
    diem = anh.load()
    ket_qua = Image.new("L", anh.size, 0)
    diem_ra = ket_qua.load()
    da_xet = set()
    for y in range(CAO):
        for x in range(RONG):
            if not diem[x, y] or (x, y) in da_xet:
                continue
            cum = [(x, y)]
            da_xet.add((x, y))
            i = 0
            while i < len(cum):
                cx, cy = cum[i]
                i += 1
                for nx in (cx - 1, cx, cx + 1):
                    for ny in (cy - 1, cy, cy + 1):
                        if 0 <= nx < RONG and 0 <= ny < CAO and diem[nx, ny] and (nx, ny) not in da_xet:
                            da_xet.add((nx, ny))
                            cum.append((nx, ny))
            if len(cum) >= DOM_NHO_NHAT:
                for p in cum:
                    diem_ra[p] = 255
    return ket_qua


def _net_chu_so(anh_goc, co_loc):
    """Ảnh nét chữ số màu đen trên nền trắng."""
    dai_nhieu = anh_goc.filter(ImageFilter.MedianFilter(co_loc))
    return ImageChops.invert(_bo_dom_nho(ImageChops.difference(anh_goc, dai_nhieu)))


def _doc_so(ocr, anh, do_phong):
    bo_dem = io.BytesIO()
    anh.resize((anh.width * do_phong, anh.height * do_phong), Image.BILINEAR).convert("RGB").save(bo_dem, "PNG")
    return "".join(c for c in ocr.classification(bo_dem.getvalue()).translate(DOI_KY_TU) if c in "0123456789")


def giai(anh):
    """Trả về mã 4 chữ số đọc được từ 576 byte ảnh, None nếu ảnh khó đọc."""
    anh_goc = Image.frombytes("1", (RONG, CAO), anh).convert("L")
    phieu = [Counter() for _ in range(SO_CHU_SO)]
    with _khoa:
        ocr = _lay_ocr()
        for co_loc in CAC_CO_LOC:
            net = _net_chu_so(anh_goc, co_loc)
            for do_phong in CAC_DO_PHONG:
                so = _doc_so(ocr, net, do_phong)
                if len(so) == SO_CHU_SO:
                    for vi_tri, chu_so in enumerate(so):
                        phieu[vi_tri][chu_so] += 1
            for vi_tri in range(SO_CHU_SO):
                trai = max(0, vi_tri * RONG_O - LE_O)
                phai = min(RONG, (vi_tri + 1) * RONG_O + LE_O)
                o = Image.new("L", (phai - trai + 2 * VIEN_O, CAO + 2 * VIEN_O), 255)
                o.paste(net.crop((trai, 0, phai, CAO)), (VIEN_O, VIEN_O))
                so = _doc_so(ocr, o, DO_PHONG_O)
                if len(so) == 1:
                    phieu[vi_tri][so] += 1
    if not all(phieu):
        return None
    return "".join(p.most_common(1)[0][0] for p in phieu)
