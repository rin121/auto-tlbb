"""
VỨT RÁC: tiêu hủy trang bị "Chưa giám định" và (nếu bật) trang bị dưới N sao trong túi.

Game không có hàm Lua nào cho biết đồ đã giám định chưa hay hủy đồ theo ô, nên phần này đọc/ghi thẳng bộ nhớ
Game.exe (địa chỉ tìm bằng cách dịch ngược, chỉ đúng với bản Game.exe này) rồi gọi hàm Lua có sẵn của game:

    Túi đồ         : DataPool (con trỏ ở 0x645AE0) + 0x37C -> mảng 100 con trỏ món đồ, chỉ số trùng với
                     PlayerPackage:EnumItem("base", ô)                                  (UserBag_GetItem, 0x49D170)
    Chưa giám định : đúng điều kiện tooltip hiện dòng "Chưa giám định" (hàm 0x421000):
                     là trang bị (hàm ảo +0x0C trả về 1), vị trí mặc (món+0x28 -> +0x14) khác 8/9/10,
                     loại đồ phải giám định (món+0x1C -> +0x28 khác 0), có thuộc tính (món+0x14 -> byte +0x5E > 0)
                     và chưa có cờ đã giám định (món+0x14 -> byte +0x0D, bit 2)
    Số sao         : như hàm 0x421340 (tooltip lấy qua SuperTooltips:GetEquipQual): món+0x14 -> byte +0x6A.
                     Không có sao nếu chưa giám định, mẫu đồ không có sao (món+0x28 -> +0x64 <= 0),
                     vị trí mặc 17 tính sao kiểu khác (auto bỏ qua). Trước khi server gửi thuộc tính thì byte này
                     là 0, nên chỉ tin số sao khi món đã có thuộc tính (+0x5E > 0).
    Thuộc tính     : client chỉ có sau khi hỏi server. Tooltip hỏi bằng SuperTooltips:SendAskItemInfoMsg() cho món
                     có ActionID ghi ở SuperTooltips (đối tượng tĩnh 0x6449D0) + 4                      (0x41E7F0)
    Hủy            : DiscardItem() (nút đồng ý của hộp "tiêu hủy vật phẩm") hủy món ở DataPool+0x47C30 (2 = túi đồ),
                     DataPool+0x47C34 (ô), gửi lên server rồi tự trả hai ô nhớ đó về 0 / -1              (0x44F730)

Trước khi làm gì cũng so các đoạn code trên với bản đã dịch ngược; khác một byte là báo lỗi, không ghi gì.
"""
import ctypes
import struct
import time

from bang_ma_viscii import giai_ma
from lua_game import kernel32

MAU_CODE = {
    0x421000: "8b41288b401483f808743083f809742b83f80a74268b511c8b422885c074198b49148a415e84c0760fe8e20a1700"
              "85c07506b801000000c333c0c332c0c3",
    0x44F74E: "a1044964008b0de05a6400538b99347c04008945f08b81307c040083e80256570f8442010000480f854d0200",
    0x49D170: "558bec8b450885c07c1483f8647d0f8b897c0300008d04818b005dc20400",
    0x41E7F0: "8b4904a1046364008b1056518bc8ff52388bf085f6744f8b168bceff521883f80375438b068bceff50288bf085f674"
              "368b168bceff522883f802752a8b068bceff908400000085c0741c8b1653578b3de05a64008b1f8bceff5230508bcf"
              "ff939c0000005f5b33c05ec20400",
    0x44F9C2: "8b0de05a6400c781307c0400000000008b0de05a6400c781347c0400ffffffff",
    0x421340: "568bf18b46288b401483f808742c83f809742783f80a74228b4e1c8b412885c074188b4e148a415e84c0760ee89f07"
              "170085c0750583c8ff5ec38b46288b486485c97ef18378141174098b56140fb6426a5ec3",
}
CON_TRO_DATAPOOL = 0x645AE0
SUPER_TOOLTIPS = 0x6449D0
VTABLE_SUPER_TOOLTIPS = 0x5EEAA4
LECH_TUI = 0x37C
LECH_HUY_NOI_CHUA, LECH_HUY_O = 0x47C30, 0x47C34
NOI_CHUA_TUI_DO = 2
HAM_LA_TRANG_BI = bytes.fromhex("b801000000c3")  # mov eax, 1 / ret
VI_TRI_KHONG_GIAM_DINH = (8, 9, 10)
VI_TRI_SAO_KIEU_KHAC = 0x11
GIAY_CHO_THUOC_TINH = 1.5
GIAY_CHO_HUY = 2

QUYEN_DOC_GHI = 0x0008 | 0x0010 | 0x0020 | 0x0400
MA_DS_TUI = ('local s = "" for i = 0, 99 do local a = PlayerPackage:EnumItem("base", i) '
             'if a and a:GetID() ~= 0 then s = s .. i .. "|" .. a:GetID() .. "|" .. a:GetName() .. "\\n" end end '
             'return s')


class LoiVutRac(Exception):
    pass


class BoNho:
    def __init__(self, pid):
        self.tay_cam = kernel32.OpenProcess(QUYEN_DOC_GHI, False, pid)
        if not self.tay_cam:
            raise LoiVutRac(f"không mở được tiến trình game {pid} (lỗi {ctypes.get_last_error()})")

    def dong(self):
        kernel32.CloseHandle(self.tay_cam)

    def doc(self, dia_chi, so_byte):
        dem = ctypes.create_string_buffer(so_byte)
        da_doc = ctypes.c_size_t()
        if not kernel32.ReadProcessMemory(self.tay_cam, dia_chi, dem, so_byte, ctypes.byref(da_doc)) \
                or da_doc.value != so_byte:
            raise LoiVutRac(f"không đọc được bộ nhớ game ở {dia_chi:#x}")
        return dem.raw

    def so(self, dia_chi):
        return struct.unpack("<I", self.doc(dia_chi, 4))[0]

    def byte(self, dia_chi):
        return self.doc(dia_chi, 1)[0]

    def ghi(self, dia_chi, gia_tri):
        du_lieu = struct.pack("<I", gia_tri & 0xFFFFFFFF)
        da_ghi = ctypes.c_size_t()
        if not kernel32.WriteProcessMemory(self.tay_cam, dia_chi, du_lieu, 4, ctypes.byref(da_ghi)):
            raise LoiVutRac(f"không ghi được bộ nhớ game ở {dia_chi:#x}")


def kiem_tra_ban_game(bo_nho, lua):
    for dia_chi, mau in MAU_CODE.items():
        if bo_nho.doc(dia_chi, len(mau) // 2) != bytes.fromhex(mau):
            raise LoiVutRac(f"bản Game.exe này khác bản đã dịch ngược (code ở {dia_chi:#x}), chưa hỗ trợ vứt rác")
    dia_chi_lua = int(lua.chay("return tostring(SuperTooltips)").split(b": ")[1], 16)
    if bo_nho.so(dia_chi_lua) != SUPER_TOOLTIPS or bo_nho.so(SUPER_TOOLTIPS) != VTABLE_SUPER_TOOLTIPS:
        raise LoiVutRac("không tìm thấy SuperTooltips ở địa chỉ đã biết, chưa hỗ trợ vứt rác")


def _ds_tui(lua):
    """{ô: (ActionID, tên)}."""
    ket_qua = {}
    for dong in lua.chay(MA_DS_TUI).split(b"\n"):
        if dong:
            o, ma, ten = dong.split(b"|", 2)
            ket_qua[int(o)] = (int(ma), giai_ma(ten))
    return ket_qua


def _trang_thai_giam_dinh(bo_nho, mon):
    """None nếu không phải trang bị phải giám định, ngược lại (số thuộc tính đã biết, đã giám định chưa)."""
    if bo_nho.doc(bo_nho.so(bo_nho.so(mon) + 0x0C), len(HAM_LA_TRANG_BI)) != HAM_LA_TRANG_BI:
        return None
    if bo_nho.so(bo_nho.so(mon + 0x28) + 0x14) in VI_TRI_KHONG_GIAM_DINH:
        return None
    if bo_nho.so(bo_nho.so(mon + 0x1C) + 0x28) == 0:
        return None
    chi_tiet = bo_nho.so(mon + 0x14)
    return bo_nho.byte(chi_tiet + 0x5E), bool(bo_nho.byte(chi_tiet + 0x0D) & 2)


def _la_trang_bi(bo_nho, mon):
    return bo_nho.doc(bo_nho.so(bo_nho.so(mon) + 0x0C), len(HAM_LA_TRANG_BI)) == HAM_LA_TRANG_BI


def _so_sao(bo_nho, mon):
    """Số sao của trang bị đã giám định, None nếu không có sao hoặc chưa biết chắc."""
    chi_tiet = bo_nho.so(mon + 0x14)
    if bo_nho.byte(chi_tiet + 0x5E) == 0:
        return None
    giam_dinh = _trang_thai_giam_dinh(bo_nho, mon)
    if giam_dinh is not None and not giam_dinh[1]:
        return None
    mau = bo_nho.so(mon + 0x28)
    if struct.unpack("<i", bo_nho.doc(mau + 0x64, 4))[0] <= 0 or bo_nho.so(mau + 0x14) == VI_TRI_SAO_KIEU_KHAC:
        return None
    return bo_nho.byte(chi_tiet + 0x6A)


def _hoi_thuoc_tinh(bo_nho, lua, cac_action_id):
    """Như rê chuột lên từng món: trỏ SuperTooltips vào món đó rồi hỏi server, xong trả lại món cũ."""
    action_cu = bo_nho.so(SUPER_TOOLTIPS + 4)
    try:
        for action_id in cac_action_id:
            bo_nho.ghi(SUPER_TOOLTIPS + 4, action_id)
            lua.chay("SuperTooltips:SendAskItemInfoMsg()")
    finally:
        bo_nho.ghi(SUPER_TOOLTIPS + 4, action_cu)


def _mang_tui(bo_nho):
    return bo_nho.so(bo_nho.so(CON_TRO_DATAPOOL) + LECH_TUI)


def tim_rac(bo_nho, lua, sao_toi_thieu=0):
    """
    [(ô, tên, con trỏ món, lý do)]: trang bị Chưa giám định, và trang bị dưới sao_toi_thieu sao (0 = không xét sao).
    """
    ds = _ds_tui(lua)
    mang = _mang_tui(bo_nho)
    trang_bi = {}
    for o in ds:
        mon = bo_nho.so(mang + 4 * o)
        if mon and _la_trang_bi(bo_nho, mon) and (sao_toi_thieu or _trang_thai_giam_dinh(bo_nho, mon) is not None):
            trang_bi[o] = mon
    chua_co_thuoc_tinh = [ds[o][0] for o, mon in trang_bi.items()
                          if bo_nho.byte(bo_nho.so(mon + 0x14) + 0x5E) == 0]
    if chua_co_thuoc_tinh:
        _hoi_thuoc_tinh(bo_nho, lua, chua_co_thuoc_tinh)
        time.sleep(GIAY_CHO_THUOC_TINH)

    rac = []
    for o in trang_bi:
        mon = bo_nho.so(mang + 4 * o)
        if not mon or not _la_trang_bi(bo_nho, mon):
            continue
        trang_thai = _trang_thai_giam_dinh(bo_nho, mon)
        if trang_thai and trang_thai[0] > 0 and not trang_thai[1]:
            rac.append((o, ds[o][1], mon, "Chưa giám định"))
        elif sao_toi_thieu:
            so_sao = _so_sao(bo_nho, mon)
            if so_sao is not None and so_sao < sao_toi_thieu:
                rac.append((o, ds[o][1], mon, f"{so_sao} sao"))
    return rac


def _huy(bo_nho, lua, o):
    dp = bo_nho.so(CON_TRO_DATAPOOL)
    bo_nho.ghi(dp + LECH_HUY_NOI_CHUA, NOI_CHUA_TUI_DO)
    bo_nho.ghi(dp + LECH_HUY_O, o)
    try:
        lua.chay("DiscardItem()")
    except Exception:
        bo_nho.ghi(dp + LECH_HUY_NOI_CHUA, 0)
        bo_nho.ghi(dp + LECH_HUY_O, -1)
        raise


def vut_rac(lua, ten, in_log, chi_xem=False, nen_dung=lambda: False, sao_toi_thieu=0):
    """
    Tìm (và vứt, nếu chi_xem=False) rác của nhân vật ten: trang bị Chưa giám định, và trang bị dưới
    sao_toi_thieu sao nếu sao_toi_thieu > 0. Trả về danh sách (ô, tên món, lý do).
    """
    bo_nho = BoNho(lua.pid)
    try:
        kiem_tra_ban_game(bo_nho, lua)
        rac = tim_rac(bo_nho, lua, sao_toi_thieu)
        if chi_xem:
            return [(o, ten_mon, ly_do) for o, ten_mon, _, ly_do in rac]
        mang = _mang_tui(bo_nho)
        da_vut = []
        for o, ten_mon, mon, ly_do in rac:
            if nen_dung():
                break
            if bo_nho.so(mang + 4 * o) != mon:
                continue
            _huy(bo_nho, lua, o)
            het_han = time.time() + GIAY_CHO_HUY
            while bo_nho.so(mang + 4 * o) == mon and time.time() < het_han:
                time.sleep(0.1)
            if bo_nho.so(mang + 4 * o) == mon:
                in_log(f"{ten}: không vứt được {ten_mon} (ô {o + 1}), có thể món đang bị khóa")
                continue
            in_log(f"{ten}: đã vứt {ten_mon} (ô {o + 1}, {ly_do})")
            da_vut.append((o, ten_mon, ly_do))
        return da_vut
    finally:
        bo_nho.dong()