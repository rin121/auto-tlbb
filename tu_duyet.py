"""
TỰ DUYỆT POPUP: hộp hỏi xác nhận hiện lên thì tự bấm nút Duyệt, bằng chính hàm của nút đó trong giao diện game
(Data\\Interface.axp), không click chuột:
    MessageBox_Self   : MessageBox_Self_OK_Clicked()     mang trang bị sẽ khóa, tiêu hủy vật phẩm, thoát game, mất kết nối,
                                                         phóng sinh, bỏ nhiệm vụ, bang hội, PK, mua bán, hỏi từ script server...
    MessageBox_Other  : MessageBox_Other_OK_Clicked()    mời vào nhóm, xin vào nhóm, Kéo, mời cưỡi chung
    TeamMessageBox1-5 : TeamMessageBoxN_OK_Clicked()     đội viên mời người khác vào nhóm, hỏi đội trưởng
    MessageBoxCommon  : MessageBoxCommon_Ok_Clicked()    hộp hỏi chung (bày bán, tìm bạn...)
    MessageBox_Friend : MessageBox_Friend_Ok_Clicked()   người khác xin kết bạn
    AcceptBox         : AcceptBox_OK_Clicked()           mời tỷ thí - chỉ duyệt khi bật riêng (tỷ thí có thể chết)

Hàm của nút dùng "this" (cửa sổ đang chạy script) để tự đóng hộp; game để "this" trong bảng riêng của cửa sổ
(<Tên>_Env), trong_cua_so() trỏ vào bảng đó nên "this" đúng cửa sổ. Bảng riêng không có "this" thì không bấm.
TeamMessageBox1 luôn hiện (chứa 5 khung hỏi), nên xét từng khung TeamMessageBoxN_Frame có đang hiện không.
"""
import time

from bang_ma_viscii import giai_ma
from dang_nhap import bo_dau, bo_ma_mau, trong_cua_so

# (cửa sổ, hàm nút Duyệt, nút Duyệt, ô nội dung)
CAC_HOP = (
    ("MessageBox_Self", "MessageBox_Self_OK_Clicked", "MessageBox_Self_OK_Button", "MessageBox_Self_Text"),
    ("MessageBox_Other", "MessageBox_Other_OK_Clicked", "MessageBox_Other_OK_Button", "MessageBox_Other_Text"),
    ("MessageBoxCommon", "MessageBoxCommon_Ok_Clicked", "MessageBoxCommon_OK_Button", "MessageBoxCommon_Text"),
    ("MessageBox_Friend", "MessageBox_Friend_Ok_Clicked", "MessageBox_Friend_OK_Button", "MessageBox_Friend_Text"),
)
HOP_TY_THI = ("AcceptBox", "AcceptBox_OK_Clicked", "AcceptBox_OK_Button", "AcceptBox_Text")
CUA_SO_HOI_NHOM = "TeamMessageBox1"
SO_KHUNG_HOI_NHOM = 5
# Bấm Duyệt mà hộp không đóng thì chờ chừng này giây mới bấm lại, để không bấm liên tục vào một hộp bấm không ăn.
GIAY_TRUOC_KHI_BAM_LAI = 3
# Hộp hỏi thoát game (bấm X / Alt+F4 cửa sổ game): Duyệt là game tự tắt, không bao giờ tự bấm.
CAC_CHU_KHONG_DUYET = ("roi bo the gioi",)
MA_CON_HIEN = 'local con = "0" if {dieu_kien} then con = "1" end '

MA_DOC_NOI_DUNG = 'local ok, chu = pcall(function() return {o}:GetText() end) if not ok or chu == nil then chu = "" end '
# Không đọc được trạng thái nút (hàm IsVisible không có) thì coi như nút đang hiện.
MA_NUT_HIEN = ('local ok, hien = pcall(function() return {nut}:IsVisible() end) '
               'if ok and (hien == false or hien == 0) then return "" end ')


def ma_hop_dang_hien(cho_ty_thi):
    """Lua trả về tên các hộp đang hiện, mỗi dòng một tên (khung hỏi nhóm ghi "TeamMessageBoxN")."""
    cac_hop = CAC_HOP + ((HOP_TY_THI,) if cho_ty_thi else ())
    ma = 'local s = "" '
    ma += " ".join(f'if IsWindowShow("{hop[0]}") then s = s .. "{hop[0]}\\n" end' for hop in cac_hop)
    ma += (f' if IsWindowShow("{CUA_SO_HOI_NHOM}") then '
           f'local e = rawget(getfenv(0), "{CUA_SO_HOI_NHOM}_Env") '
           f'if type(e) == "table" then for i = 1, {SO_KHUNG_HOI_NHOM} do '
           'local khung = rawget(e, "TeamMessageBox" .. i .. "_Frame") '
           'local ok, hien = pcall(function() return khung:IsVisible() end) '
           'if ok and hien and hien ~= 0 then s = s .. "TeamMessageBox" .. i .. "\\n" end '
           'end end end')
    return ma + " return s"


def ma_duyet_hop(cua_so, ham, nut, o_noi_dung):
    """
    Lua bấm Duyệt ở một hộp. Trả về "da_duyet\\t<1 nếu bấm xong hộp vẫn hiện, 0 nếu đã đóng>\\t<nội dung>",
    "" nếu hộp đã đóng / không có nút, "khong_this".
    """
    return trong_cua_so(cua_so, (
        f'if not IsWindowShow("{cua_so}") then return "" end '
        f'if rawget(rawget(getfenv(0), "{cua_so}_Env") or {{}}, "this") == nil then return "khong_this" end '
        + MA_NUT_HIEN.format(nut=nut) + MA_DOC_NOI_DUNG.format(o=o_noi_dung)
        + f'{ham}() ' + MA_CON_HIEN.format(dieu_kien=f'IsWindowShow("{cua_so}")')
        + 'return "da_duyet\\t" .. con .. "\\t" .. chu'))


def ma_doc_hop(cua_so, o_noi_dung):
    """Lua trả về nội dung hộp đang hiện (không bấm gì), "" nếu hộp đã đóng."""
    return trong_cua_so(cua_so, (
        f'if not IsWindowShow("{cua_so}") then return "" end '
        + MA_DOC_NOI_DUNG.format(o=o_noi_dung) + 'return chu'))


def khong_duoc_duyet(noi_dung):
    chu = bo_dau(noi_dung)
    return any(tu in chu for tu in CAC_CHU_KHONG_DUYET)


def ma_duyet_khung_hoi_nhom(so):
    kiem_tra_hien = f'pcall(function() return TeamMessageBox{so}_Frame:IsVisible() end)'
    return trong_cua_so(CUA_SO_HOI_NHOM, (
        f'local ok, hien = {kiem_tra_hien} '
        'if not ok or not hien or hien == 0 then return "" end '
        + MA_DOC_NOI_DUNG.format(o=f"TeamMessageBox{so}_Text")
        + f'TeamMessageBox{so}_OK_Clicked() '
        + f'local ok2, hien2 = {kiem_tra_hien} '
        + MA_CON_HIEN.format(dieu_kien="ok2 and hien2 and hien2 ~= 0")
        + 'return "da_duyet\\t" .. con .. "\\t" .. chu'))


class LoiTuDuyet(Exception):
    pass


class TuDuyet:
    """Mỗi cửa sổ game một đối tượng; gọi kiem_tra() định kỳ."""

    def __init__(self, lua, in_log):
        self.lua = lua
        self.in_log = in_log
        self.da_bam = {}
        self.da_bao_bo_qua = set()

    def kiem_tra(self, cho_ty_thi):
        """Duyệt mọi hộp đang hiện. Lỗi Lua thì ném LoiLua."""
        dang_hien = self.lua.chay(ma_hop_dang_hien(cho_ty_thi), so_lan_thu=1).decode("latin-1").split()
        self.da_bam = {ten: luc for ten, luc in self.da_bam.items() if ten in dang_hien}
        self.da_bao_bo_qua &= set(dang_hien)
        theo_ten = {hop[0]: hop for hop in CAC_HOP + (HOP_TY_THI,)}
        for ten in dang_hien:
            if ten in theo_ten:
                cua_so, _, _, o_noi_dung = theo_ten[ten]
                noi_dung = bo_ma_mau(giai_ma(self.lua.chay(ma_doc_hop(cua_so, o_noi_dung), so_lan_thu=1)))
                if khong_duoc_duyet(noi_dung):
                    if ten not in self.da_bao_bo_qua:
                        self.da_bao_bo_qua.add(ten)
                        self.in_log(f"Không tự duyệt [{ten}] (hộp thoát game): {noi_dung.replace(chr(10), ' ')}")
                    continue
                ma = ma_duyet_hop(*theo_ten[ten])
            else:
                ma = ma_duyet_khung_hoi_nhom(int(ten[len("TeamMessageBox"):]))
            self.duyet(ten, ma)

    def duyet(self, ten, ma):
        bay_gio = time.time()
        truoc = self.da_bam.get(ten)
        if truoc and bay_gio - truoc < GIAY_TRUOC_KHI_BAM_LAI:
            return
        ket_qua = self.lua.chay(ma, so_lan_thu=1)
        if ket_qua == b"khong_this":
            raise LoiTuDuyet(f"hộp {ten} không có biến this trong bảng riêng, không bấm được")
        if not ket_qua.startswith(b"da_duyet\t"):
            return
        _, con_hien, noi_dung = ket_qua.split(b"\t", 2)
        if con_hien == b"1":
            self.da_bam[ten] = bay_gio
        else:
            self.da_bam.pop(ten, None)
        noi_dung = bo_ma_mau(giai_ma(noi_dung)).replace("\n", " ")
        self.in_log(f"Tự duyệt [{ten}]" + (f": {noi_dung}" if noi_dung else ""))
