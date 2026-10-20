"""
TỰ NHẶT TÚI ĐỒ (tab "Chiến đấu"): không có buff Càn Khôn Hồ thì chạy tới túi đồ quái rớt rồi nhặt.

Túi đồ  : đối tượng lớp CTripperObject_ItemBox (hàm lấy lớp "mov eax, 0x63e214 / ret"), cùng danh sách đối tượng
          với quái (xem chien_dau.py); id server +0x34, tọa độ x +0x44, y +0x4C.
Mở túi  : không có hàm Lua nào, nên dùng dll\\autohoc_nhat.dll qua loadlib có sẵn trong Lua của game: DLL gọi
          Tripper_Active của túi (như bấm chuột vào túi), game gửi gói tin mở túi; máy chủ chỉ cho mở khi đứng sát
          túi (khoảng 2 ô), mở được thì cửa sổ LootPacket hiện danh sách đồ.
Nhặt    : LootPacket_Collect_Clicked() (nút "Nhặt hết" của cửa sổ LootPacket).
"""
import os
import struct
import time

from chien_dau import (CON_TRO_QUAN_LY_DOI_TUONG, LECH_CAY_DOI_TUONG, LECH_HAM_LAY_LOP, LECH_ID,
                       LECH_NHAN_VAT_CUA_MINH, LECH_X, LECH_Y, SO_NUT_TOI_DA, LoiChienDau, khoang_cach)
from dang_nhap import trong_cua_so
from thu_muc import THU_MUC_APP
from tu_dung_vat_pham import TuDungCanKhonHo

HAM_LOP_TUI_DO = bytes.fromhex("b814e26300c3")  # mov eax, CTripperObject_ItemBox / ret
DUONG_DAN_DLL_NHAT = os.path.join(THU_MUC_APP, "dll", "autohoc_nhat.dll")
KHOANG_CACH_MO_TUI = 1.5
GIAY_TOI_DA_MOT_TUI = 12.0
GIAY_GIUA_HAI_LAN_CHAY = 1.0
GIAY_GIUA_HAI_LAN_MO = 1.5
GIAY_GIUA_HAI_LAN_BAM_NHAT = 1.0
GIAY_XEM_CAN_KHON_HO = 30.0
GIAY_BO_QUA_TUI_KHONG_NHAT_DUOC = 120.0
GIAY_BO_QUA_TUI_NGUOI_KHAC = 3600.0
SO_TUI_XEM_QUYEN_MOI_LUOT = 5

MA_CUA_SO_NHAT_DANG_MO = 'return tostring(IsWindowShow("LootPacket"))'
MA_BAM_NHAT_HET = trong_cua_so("LootPacket", 'if IsWindowShow("LootPacket") then LootPacket_Collect_Clicked() end')


def chuoi_lua_ansi(chu):
    """Chuỗi Lua theo bảng mã ANSI của Windows (đường dẫn file cho LoadLibraryA)."""
    return '"' + "".join(chr(b) if 32 <= b < 127 and b not in (34, 92) else f"\\{b:03d}"
                         for b in chu.encode("mbcs")) + '"'


def ma_mo_tui(id_tui, chi_xem=False):
    """Lua mở túi id_tui (chi_xem=True: chỉ xem còn túi và có quyền nhặt). Kết quả xem dll\\autohoc_nhat.c."""
    tham_so = f'"{int(id_tui)}", "xem"' if chi_xem else f'"{int(id_tui)}"'
    return (f'AutoHoc_MoTui = AutoHoc_MoTui or loadlib({chuoi_lua_ansi(DUONG_DAN_DLL_NHAT)}, "autohoc_mo_tui") '
            'if not AutoHoc_MoTui then return "dll" end '
            f"return AutoHoc_MoTui({tham_so})")


def doc_tui_do(bo_nho, la_tui_theo_vtable):
    """(vị trí của mình, {id server: (x, y)} các túi đồ quanh mình). la_tui_theo_vtable: bộ nhớ đệm {vtable: bool}."""
    quan_ly = bo_nho.so(CON_TRO_QUAN_LY_DOI_TUONG)
    minh = bo_nho.so(quan_ly + LECH_NHAN_VAT_CUA_MINH)
    if not minh:
        raise LoiChienDau("chưa có nhân vật trong game")
    vi_tri = struct.unpack("<ff", bo_nho.doc(minh + LECH_X, 4) + bo_nho.doc(minh + LECH_Y, 4))
    dau = bo_nho.so(quan_ly + LECH_CAY_DOI_TUONG)
    cac_tui, can_xem, so_nut = {}, [bo_nho.so(dau + 4)], 0
    while can_xem and so_nut < SO_NUT_TOI_DA:
        so_nut += 1
        nut = can_xem.pop()
        try:
            khoi = bo_nho.doc(nut, 0x16)
            if khoi[0x15]:
                continue
            trai, _, phai, _, doi_tuong = struct.unpack_from("<5I", khoi)
            can_xem += [trai, phai]
            if not doi_tuong:
                continue
            vtable = bo_nho.so(doi_tuong)
            if vtable not in la_tui_theo_vtable:
                ham = bo_nho.doc(bo_nho.so(vtable + LECH_HAM_LAY_LOP), len(HAM_LOP_TUI_DO))
                la_tui_theo_vtable[vtable] = ham == HAM_LOP_TUI_DO
            if not la_tui_theo_vtable[vtable]:
                continue
            khoi = bo_nho.doc(doi_tuong + LECH_ID, LECH_Y + 4 - LECH_ID)
            ma_id = struct.unpack_from("<i", khoi, 0)[0]
            x = struct.unpack_from("<f", khoi, LECH_X - LECH_ID)[0]
            y = struct.unpack_from("<f", khoi, LECH_Y - LECH_ID)[0]
        except LoiChienDau:
            continue  # game vừa xóa đối tượng này trong lúc đọc
        cac_tui[ma_id] = (x, y)
    return vi_tri, cac_tui


class NhatDo:
    """Trạng thái tự nhặt túi đồ của một cửa sổ game; buoc() gọi ở luồng chiến đấu, trước lượt đánh."""

    def __init__(self, lua, in_log):
        self.lua = lua
        self.in_log = in_log
        self.can_khon_ho = TuDungCanKhonHo(lua, in_log)
        self.luc_xem_can_khon_ho = 0.0
        self.co_can_khon_ho = False
        self.tui = None
        self.luc_bat_dau = 0.0
        self.luc_chay = 0.0
        self.luc_mo = 0.0
        self.luc_bam_nhat = 0.0
        self.bo_qua_den = {}
        self.tat_vi_loi = None
        self.la_tui_theo_vtable = {}

    def bo_tui(self):
        self.tui = None

    def _co_can_khon_ho(self, bay_gio):
        if bay_gio - self.luc_xem_can_khon_ho >= GIAY_XEM_CAN_KHON_HO:
            self.luc_xem_can_khon_ho = bay_gio
            self.co_can_khon_ho = self.can_khon_ho.con_hieu_ung() > 0
        return self.co_can_khon_ho

    def _bao_loi_dll(self, ket_qua):
        self.tat_vi_loi = {b"dll": f"không nạp được {DUONG_DAN_DLL_NHAT}",
                           b"-2": "bản Game.exe này khác bản đã dịch ngược"}.get(ket_qua, f"DLL trả về {ket_qua!r}")
        self.bo_tui()
        self.in_log(f"Tự nhặt túi đồ: tắt vì {self.tat_vi_loi}")

    def _chon_tui(self, vi_tri, cac_tui, tam, ban_kinh, bay_gio):
        gan = sorted((khoang_cach(vi_tri, xy), ma_id) for ma_id, xy in cac_tui.items()
                     if khoang_cach(tam, xy) <= ban_kinh and self.bo_qua_den.get(ma_id, 0) <= bay_gio)
        for _, ma_id in gan[:SO_TUI_XEM_QUYEN_MOI_LUOT]:
            ket_qua = self.lua.chay(ma_mo_tui(ma_id, chi_xem=True))
            if ket_qua == b"1":
                return ma_id
            if ket_qua in (b"0", b"-1"):
                self.bo_qua_den[ma_id] = bay_gio + GIAY_BO_QUA_TUI_NGUOI_KHAC
            else:
                self._bao_loi_dll(ket_qua)
                return None
        return None

    def buoc(self, bo_nho, tam, ban_kinh):
        """
        Một lượt tự nhặt: túi đồ cách tam (None = vị trí của mình) không quá ban_kinh. Trả về mô tả nếu đang nhặt
        (lượt này không đánh), None nếu không có túi để nhặt / đang có Càn Khôn Hồ.
        """
        bay_gio = time.time()
        if self.tat_vi_loi or self._co_can_khon_ho(bay_gio):
            self.bo_tui()
            return None
        vi_tri, cac_tui = doc_tui_do(bo_nho, self.la_tui_theo_vtable)
        if not cac_tui:
            self.bo_tui()
            return None
        tam = tam or vi_tri
        self.bo_qua_den = {ma_id: den for ma_id, den in self.bo_qua_den.items() if ma_id in cac_tui and den > bay_gio}

        if self.tui is not None and self.tui not in cac_tui:
            self.bo_tui()  # đã nhặt hết (túi biến mất)
        if self.tui is None:
            self.tui = self._chon_tui(vi_tri, cac_tui, tam, ban_kinh, bay_gio)
            if self.tui is None:
                return None
            self.luc_bat_dau, self.luc_chay, self.luc_mo, self.luc_bam_nhat = bay_gio, 0.0, 0.0, 0.0

        x, y = cac_tui[self.tui]
        if bay_gio - self.luc_bat_dau > GIAY_TOI_DA_MOT_TUI:
            self.bo_qua_den[self.tui] = bay_gio + GIAY_BO_QUA_TUI_KHONG_NHAT_DUOC
            self.in_log(f"Tự nhặt túi đồ: {GIAY_TOI_DA_MOT_TUI:.0f} giây chưa nhặt xong túi ở [{x:.0f},{y:.0f}] "
                        f"(túi đầy / không tới được?), bỏ qua")
            self.bo_tui()
            return None

        if khoang_cach(vi_tri, (x, y)) > KHOANG_CACH_MO_TUI:
            if bay_gio - self.luc_chay >= GIAY_GIUA_HAI_LAN_CHAY:
                self.luc_chay = bay_gio
                self.lua.chay(f"AutoRunToTarget({x:.1f}, {y:.1f})")
            return f"Chạy tới nhặt túi đồ [{x:.0f},{y:.0f}]"

        if self.lua.chay(MA_CUA_SO_NHAT_DANG_MO) == b"true":
            if bay_gio - self.luc_bam_nhat >= GIAY_GIUA_HAI_LAN_BAM_NHAT:
                self.luc_bam_nhat = bay_gio
                self.lua.chay(MA_BAM_NHAT_HET)
        elif bay_gio - self.luc_mo >= GIAY_GIUA_HAI_LAN_MO:
            self.luc_mo = bay_gio
            ket_qua = self.lua.chay(ma_mo_tui(self.tui))
            if ket_qua == b"0":
                self.bo_tui()
                return None
            if ket_qua == b"-1":
                self.bo_qua_den[self.tui] = bay_gio + GIAY_BO_QUA_TUI_NGUOI_KHAC
                self.bo_tui()
                return None
            if ket_qua != b"1":
                self._bao_loi_dll(ket_qua)
                return None
        return f"Nhặt túi đồ [{x:.0f},{y:.0f}]"
