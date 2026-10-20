"""
MẤT KẾT NỐI: game mất kết nối với server thì không tự tắt mà hiện hộp hỏi, nên auto tự đăng nhập (dang_nhap.py) không
biết để mở lại. Auto bấm giống người chơi, bằng chính hàm của nút trong giao diện game (Data\\Interface.axp):
    QuitRelative           : "Mất kết nối với server, có kết nối lại không?" (Duyệt / Hủy)       (QuitRelative.lua)
                             Duyệt = QuitRelative_OK_Clicked() -> EnterReconnect(true), thử kết nối lại.
                             Kết nối thất bại thì nút Duyệt bị khóa, Hủy = QuitRelative_Cancel_Clicked() -> thoát game.
                             Nút không có IsEnabled, nên mỗi lần mất kết nối chỉ Duyệt một lần, hộp còn hỏi thì Hủy.
    LoginSelectServerQuest : "Xin kiểm tra lại đường mạng và đăng nhập lại..." (Đóng)            (SelectServerQuest.lua)
                             Đóng = SelectServerQuest_Bn1Click() -> đóng kết nối / thoát game.
    MessageBox_Self        : hộp NET_CLOSE, Duyệt = MessageBox_Self_OK_Clicked() -> QuitApplication("quit").
Game đóng rồi thì auto tự đăng nhập mở lại (nếu bật ở tab Tài khoản). Kẹt quá GIAY_TOI_DA_TRUOC_KHI_THOAT giây
(vd. đang kết nối lại mãi) thì gọi thẳng QuitApplication("quit").
Ở màn hình đăng nhập: client không có luồng đăng nhập nào điều khiển (luồng đó tự đọc hộp rồi bấm) mà còn hộp
LoginSelectServerQuest một nút (lỗi mạng, máy chủ bận...) thì bấm nút đó để client sẵn sàng đăng nhập tiếp.
"""
import time

from bang_ma_viscii import giai_ma
from dang_nhap import CHU_DANG_ONLINE, GIAY_DONG_THONG_BAO_DANG_ONLINE, bo_dau, trong_cua_so

GIAY_GIUA_HAI_LAN_BAM = 5
GIAY_CHO_DONG_HOP_DANG_NHAP = 2
GIAY_TOI_DA_TRUOC_KHI_THOAT = 120
# Hộp "Đóng" / MessageBox_Self chỉ bấm khi nội dung nói về mạng, hoặc vừa thấy hộp QuitRelative.
CAC_CHU_VE_MANG = ("duong mang", "mat ket noi", "ngat ket noi", "bi dut", "ket noi voi may chu", "ket noi voi server")
GIAY_NHO_QUIT_RELATIVE = 300

_MA_HAM = (r'local function hien(o) local ok, v = pcall(function() return o:IsVisible() end) '
           r'if not ok then return "1" end if v and v ~= 0 then return "1" end return "0" end '
           r'local function bat(o) local ok, v = pcall(function() return o:IsEnabled() end) '
           r'if not ok then return "1" end if v and v ~= 0 then return "1" end return "0" end '
           r'local function chu(o) local ok, v = pcall(function() return o:GetText() end) '
           r'if not ok or v == nil then return "" end return (string.gsub(tostring(v), "[\r\n\t]", " ")) end ')


def _doc_hop(cua_so, ma_dong):
    """Đoạn Lua thêm một dòng (các cột cách nhau bằng tab) vào s nếu hộp cua_so đang hiện."""
    return (f'if IsWindowShow("{cua_so}") then s = s .. (function() '
            + trong_cua_so(cua_so, _MA_HAM + f'return {ma_dong} .. "\\n"') + ' end)() end ')


MA_DOC = ('local s = "" '
          'if IsWindowShow("PlayerFrame") then s = s .. "trong_game\\n" end '
          + _doc_hop("QuitRelative", '"qr\\t" .. hien(QuitRelative_OK_Button) .. "\\t" .. bat(QuitRelative_OK_Button) '
                                     '.. "\\t" .. hien(QuitRelative_Cancel_Button) .. "\\t" .. chu(QuitRelative_Text)')
          + _doc_hop("LoginSelectServerQuest",
                     '"ssq\\t" .. hien(SelectServerQuest_Button1) .. "\\t" .. hien(SelectServerQuest_Button2) '
                     '.. "\\t" .. chu(SelectServerQuest_Button1) .. "\\t" .. chu(SelectServerQuest_InfoWindow)')
          + _doc_hop("MessageBox_Self", '"mbs\\t" .. hien(MessageBox_Self_OK_Button) .. "\\t" .. chu(MessageBox_Self_Text)')
          + 'return s')
MA_DUYET_KET_NOI_LAI = trong_cua_so("QuitRelative", "QuitRelative_OK_Clicked()")
MA_HUY_KET_NOI_LAI = trong_cua_so("QuitRelative", "QuitRelative_Cancel_Clicked()")
MA_DONG_THONG_BAO = trong_cua_so("LoginSelectServerQuest", "SelectServerQuest_Bn1Click()")
MA_DUYET_MESSAGE_BOX = trong_cua_so("MessageBox_Self", "MessageBox_Self_OK_Clicked()")
MA_THOAT_GAME = 'QuitApplication("quit")'


def doc_cac_hop(lua):
    """{"trong_game": bool, "qr": [ok_hien, ok_bat, huy_hien, chu] | None, "ssq": [...] | None, "mbs": [...] | None}"""
    ket_qua = {"trong_game": False, "qr": None, "ssq": None, "mbs": None}
    for dong in giai_ma(lua.chay(MA_DOC, so_lan_thu=1)).split("\n"):
        cot = dong.split("\t")
        if cot[0] == "trong_game":
            ket_qua["trong_game"] = True
        elif cot[0] in ("qr", "ssq", "mbs"):
            ket_qua[cot[0]] = cot[1:]
    return ket_qua


def noi_ve_mang(chu):
    chu = bo_dau(chu)
    return any(tu in chu for tu in CAC_CHU_VE_MANG)


class XuLyMatKetNoi:
    """Mỗi cửa sổ game một đối tượng; gọi kiem_tra() định kỳ (luồng phụ, không chờ vòng auto chính)."""

    def __init__(self, lua, in_log):
        self.lua = lua
        self.in_log = in_log
        self.luc_thay_mat_ket_noi = None
        self.luc_thay_quit_relative = 0.0
        self.luc_bam = 0.0
        self.da_thoat = False
        self.da_duyet = False
        self.luc_thay_hop_dang_nhap = None

    def _bam(self, ma, log):
        self.luc_bam = time.time()
        self.in_log(log)
        self.lua.chay(ma, so_lan_thu=1)

    def _dong_hop_dang_nhap(self, ssq, bay_gio):
        if not ssq or ssq[0] != "1" or ssq[1] != "0":
            self.luc_thay_hop_dang_nhap = None
            return
        if self.luc_thay_hop_dang_nhap is None:
            self.luc_thay_hop_dang_nhap = bay_gio
        # "Nhân vật đang online": game khóa nút Đóng 20 giây.
        cho = GIAY_DONG_THONG_BAO_DANG_ONLINE if CHU_DANG_ONLINE in bo_dau(ssq[3]) else GIAY_CHO_DONG_HOP_DANG_NHAP
        if bay_gio - self.luc_thay_hop_dang_nhap < cho or bay_gio - self.luc_bam < GIAY_GIUA_HAI_LAN_BAM:
            return
        self._bam(MA_DONG_THONG_BAO, f"Màn hình đăng nhập: bấm {ssq[2].strip() or 'Đóng'} ở hộp \"{ssq[3].strip()}\" "
                                     "để đăng nhập tiếp")

    def kiem_tra(self, xu_ly_trong_game=True):
        """Lỗi Lua thì ném LoiLua. xu_ly_trong_game=False: chỉ đóng hộp thông báo ở màn hình đăng nhập."""
        hop = doc_cac_hop(self.lua)
        bay_gio = time.time()
        if not hop["trong_game"]:
            self.luc_thay_mat_ket_noi = None
            self._dong_hop_dang_nhap(hop["ssq"], bay_gio)
            return
        self.luc_thay_hop_dang_nhap = None
        if not xu_ly_trong_game:
            return
        if hop["qr"]:
            self.luc_thay_quit_relative = bay_gio
        vua_thay_qr = bay_gio - self.luc_thay_quit_relative < GIAY_NHO_QUIT_RELATIVE
        ssq_mang = bool(hop["ssq"]) and hop["ssq"][0] == "1" and hop["ssq"][1] == "0" \
            and bo_dau(hop["ssq"][2]) == "dong" and (vua_thay_qr or noi_ve_mang(hop["ssq"][3]))
        mbs_mang = bool(hop["mbs"]) and hop["mbs"][0] == "1" and noi_ve_mang(hop["mbs"][1])
        if not (hop["qr"] or ssq_mang or mbs_mang):
            self.luc_thay_mat_ket_noi = None
            self.da_thoat = self.da_duyet = False
            return
        if self.luc_thay_mat_ket_noi is None:
            self.luc_thay_mat_ket_noi = bay_gio
        if bay_gio - self.luc_bam < GIAY_GIUA_HAI_LAN_BAM:
            return

        if bay_gio - self.luc_thay_mat_ket_noi >= GIAY_TOI_DA_TRUOC_KHI_THOAT and not self.da_thoat:
            self.da_thoat = True
            self._bam(MA_THOAT_GAME, f"Mất kết nối đã {GIAY_TOI_DA_TRUOC_KHI_THOAT} giây mà game vẫn chưa đóng, "
                                     "thoát game để tự đăng nhập lại")
        elif ssq_mang:
            self._bam(MA_DONG_THONG_BAO, f"Mất kết nối: bấm Đóng ở hộp \"{hop['ssq'][3]}\" để thoát game")
        elif mbs_mang:
            self._bam(MA_DUYET_MESSAGE_BOX, f"Mất kết nối: bấm Duyệt ở hộp \"{hop['mbs'][1]}\" để thoát game")
        elif hop["qr"][0] == "1" and hop["qr"][1] == "1" and not self.da_duyet \
                and "that bai" not in bo_dau(hop["qr"][3]):
            self.da_duyet = True
            self._bam(MA_DUYET_KET_NOI_LAI, f"Mất kết nối: bấm Duyệt ở hộp \"{hop['qr'][3]}\" để kết nối lại")
        elif hop["qr"][0] == "1" and hop["qr"][2] == "1":
            # Game không có IsEnabled nên không biết Duyệt đã bị khóa chưa: đã Duyệt mà hộp vẫn hỏi là kết nối lại hỏng.
            self._bam(MA_HUY_KET_NOI_LAI, f"Mất kết nối: kết nối lại thất bại (\"{hop['qr'][3]}\"), bấm Hủy để thoát game")
