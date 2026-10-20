"""
TỰ MUA VÀ DÙNG VẬT PHẨM (tab "Tiện ích"): hết hiệu ứng thì dùng 1 cái trong túi; túi hết thì mở Tiệm KNB mua rồi dùng.
    TuDungX2        : Thiên Linh Đan, khi hết x2 kinh nghiệm.
    TuDungCanKhonHo : Càn Khôn Hồ, khi hết buff Càn Khôn Hồ (tự nhặt đồ quái rớt).

Thời gian x2 : dòng cuối bảng nhiệm vụ (Alt+Q) QuestLog_Time, game tự cập nhật khi server báo (UPDATE_DOUBLE_EXP):
               "Kinh nghiệm x 2: 19H" / "...: 1D" khi còn trên 1 giờ; còn dưới 1 giờ thì chỉ ghi "Kinh nghiệm x 2"
               và đồng hồ QuestLog_Watch đếm ngược (thuộc tính "Timer" = số giây lúc server báo); hết x2 thì
               server báo -1. SystemSetup:GetDoubleExp("remaintime") chỉ đúng lúc đang xử lý sự kiện đó.
Buff         : Player:GetBuffToolTipsByIndex(i) bắt đầu bằng tên buff ("Càn Khôn Hồ: Tự động thu thập..."),
               Player:GetBuffTimeTextByIndex(i) là số giây còn lại (PlayerImpactFrame.lua).
Tiệm KNB     : cửa sổ ShopCustom của server (không phải YuanbaoShop gốc). Gọi đúng các hàm giao diện như người bấm,
               không tự gửi XSCRIPT: server đổi script (950070 -> 45060) thì gói tin cũ bị ngắt kết nối.
               Mở   : MiniMap_YuanBaoFunc() (nút Nguyên Bảo), mở ở tiệm đầu, nhóm đầu.
               Tiệm : ShopCustom_ButtonNN (Nhiệt Mại Thương Phẩm, ..., Nam Bắc Kỳ Hóa, Quảng Trường Hình Tượng...),
                      bấm = ShopCustom_KeySelected(NN).
               Nhóm : ShopCustom_DetailNN (vd. Tiên Đan Linh Dược, Thú Cưỡi Tân Thủ, Kỵ Thuật),
                      bấm = ShopCustom_DetailSelected(NN).
               Món  : ShopCustom_ItemInfoNN_Text (tên) / _GB ("Điểm Tặng: giá"), NN = 01..20 (trang 1).
                      ShopCustom_Item_Clicked(NN) mua 1 cái.
Dùng         : PlayerPackage:UseItem(ô), như chuột phải vào món trong túi.
"""
import re
import time

from auto_chuyen_sinh import chuan_hoa
from bang_ma_viscii import giai_ma
from dang_nhap import bo_dau, bo_ma_mau, trong_cua_so

SO_O_SHOP = 20
GIAY_GIUA_MOI_LAN_XEM = 30
GIAY_CHO_SHOP = 6
GIAY_CHO_DOI_TUI = 2
GIAY_GIUA_MOI_LAN_MUA = 0.3
# Không mua / dùng được thì chờ lâu mới thử lại, để không mở shop liên tục.
GIAY_NGHI_KHI_LOI = 300

MAU_THOI_GIAN = re.compile(r"(\d+)\s*([DH])\s*$")

MA_DOC_X2 = trong_cua_so("QuestLog", (
    'local ok, chu = pcall(function() return QuestLog_Time:GetText() end) '
    'local ok2, hien = pcall(function() return QuestLog_Watch:IsVisible() end) '
    'local ok3, giay = pcall(function() return QuestLog_Watch:GetProperty("Timer") end) '
    'return tostring(ok and chu or "") .. "\\t" .. tostring(ok2 and hien) .. "\\t" .. tostring(ok3 and giay)'))

MA_DS_BUFF = ('local s = "" for i = 0, Player:GetBuffNumber() - 1 do '
              's = s .. tostring(Player:GetBuffTimeTextByIndex(i)) .. "\\t" '
              '.. tostring(Player:GetBuffToolTipsByIndex(i)) .. "\\n" end return s')

MA_MO_SHOP = trong_cua_so("MiniMap", "MiniMap_YuanBaoFunc()")
MA_SHOP_DANG_MO = 'return tostring(IsWindowShow("ShopCustom"))'

# Dòng "tiem|nhom|mon \t số \t tên [\t giá]" cho các nút / món đang hiện.
MA_DS_SHOP = trong_cua_so("ShopCustom", (
    'if not IsWindowShow("ShopCustom") then return "" end '
    'local function chu(o) if o == nil then return "" end '
    'local ok, t = pcall(function() return o:GetText() end) return ok and tostring(t) or "" end '
    'local function hien(o) if o == nil then return false end '
    'local ok, t = pcall(function() return o:IsVisible() end) return ok and t end '
    'local E, s = ShopCustom_Env, "" '
    'for i = 1, 12 do local k = string.format("%02d", i) '
    'if hien(E["ShopCustom_Button" .. k]) then s = s .. "tiem\\t" .. i .. "\\t" .. chu(E["ShopCustom_Button" .. k]) .. "\\n" end '
    'if hien(E["ShopCustom_Detail" .. k]) then s = s .. "nhom\\t" .. i .. "\\t" .. chu(E["ShopCustom_Detail" .. k]) .. "\\n" end end '
    f'for i = 1, {SO_O_SHOP} do local k = string.format("%02d", i) '
    'if hien(E["ShopCustom_ItemInfo" .. k]) then '
    's = s .. "mon\\t" .. i .. "\\t" .. chu(E["ShopCustom_ItemInfo" .. k .. "_Text"]) .. "\\t" '
    '.. chu(E["ShopCustom_ItemInfo" .. k .. "_GB"]) .. "\\n" end end return s'))

MA_DS_TUI = ('local s = "" for i = 0, 99 do local a = PlayerPackage:EnumItem("base", i) '
             'if a and a:GetID() ~= 0 then s = s .. i .. "\\t" .. a:GetNum() .. "\\t" .. a:GetName() .. "\\n" end end '
             'return s')


class LoiVatPham(Exception):
    pass


def doc_giay_x2(chu, dong_ho_hien, giay_dong_ho):
    """
    Số giây x2 còn lại theo bảng nhiệm vụ: con số của dòng chữ (giờ / ngày, làm tròn xuống) hoặc của đồng hồ.
    0 nếu đã hết x2.
    """
    khop = MAU_THOI_GIAN.search(bo_ma_mau(chu))
    if khop:
        return int(khop.group(1)) * (86400 if khop.group(2) == "D" else 3600)
    if dong_ho_hien == "true":
        try:
            return max(int(float(giay_dong_ho)), 0)
        except ValueError:
            return 0
    return 0


def mo_ta_thoi_gian(giay):
    return f"{giay // 3600} giờ" if giay >= 3600 else f"{giay // 60} phút"


def _ten_shop(chu):
    """Tên nút / món trong shop để so sánh: bỏ mã màu và ký tự lạ còn sót ở đầu ("?Kỵ Thuật" -> "kỵ thuật")."""
    return chuan_hoa(bo_ma_mau(chu)).lstrip("?\ufffd ").strip()


class TiemKNB:
    """Điều khiển cửa sổ Tiệm KNB (ShopCustom) bằng các hàm giao diện như người bấm."""

    def __init__(self, lua):
        self.lua = lua

    def doc(self):
        """{"tiem": {số: tên}, "nhom": {số: tên}, "mon": {số: (tên, chữ giá)}} của những gì đang hiện."""
        ds = {"tiem": {}, "nhom": {}, "mon": {}}
        for dong in giai_ma(self.lua.chay(MA_DS_SHOP)).split("\n"):
            phan = dong.split("\t")
            if len(phan) >= 3 and phan[0] in ds and phan[1].isdigit():
                ds[phan[0]][int(phan[1])] = (bo_ma_mau(phan[2]), bo_ma_mau(phan[3]) if len(phan) > 3 else "") \
                    if phan[0] == "mon" else bo_ma_mau(phan[2])
        return ds

    def _cho_doi(self, cu):
        """Chờ danh sách món khác cu (server gửi về chậm); hết giờ thì thôi, có thể đang ở đúng chỗ rồi."""
        het_han = time.time() + GIAY_CHO_DOI_TUI
        ds = self.doc()
        while ds["mon"] == cu and time.time() < het_han:
            time.sleep(0.2)
            ds = self.doc()
        return ds

    def mo(self):
        if self.lua.chay(MA_SHOP_DANG_MO) != b"true":
            self.lua.chay(MA_MO_SHOP)
        het_han = time.time() + GIAY_CHO_SHOP
        while time.time() < het_han:
            time.sleep(0.3)
            ds = self.doc()
            if ds["tiem"] and ds["mon"]:
                return ds
        raise LoiVatPham("bấm nút Nguyên Bảo mà Tiệm KNB không mở")

    def _bam(self, loai, ten, ham):
        ds = self.doc()
        so = next((so for so, chu in ds[loai].items() if _ten_shop(chu) == chuan_hoa(ten)), None)
        if so is None:
            raise LoiVatPham(f"Tiệm KNB không có {'tiệm' if loai == 'tiem' else 'nhóm'} {ten} "
                             f"(đang có: {', '.join(ds[loai].values())})")
        self._goi(f"{ham}({so})")
        return self._cho_doi(ds["mon"])

    def _goi(self, ma):
        # Bấm vào shop đã bị đóng (vd. người chơi / script khác đóng giữa chừng) có thể làm game văng.
        if self.lua.chay(trong_cua_so("ShopCustom", f'if not IsWindowShow("ShopCustom") then return "dong" end '
                                                    f'{ma} return ""')) == b"dong":
            raise LoiVatPham("Tiệm KNB bị đóng giữa chừng")

    def chon(self, tiem, nhom=None):
        """Mở shop, chọn tiệm rồi nhóm (nhom=None: nhóm đầu, game tự chọn khi đổi tiệm)."""
        self.mo()
        self._bam("tiem", tiem, "ShopCustom_KeySelected")
        if nhom:
            self._bam("nhom", nhom, "ShopCustom_DetailSelected")

    def tim(self, ten):
        """(số ô, giá Điểm Tặng) của món ten ở trang đang hiện. Món bán bằng KNB thì báo lỗi, auto không tiêu KNB."""
        for so, (chu, gia) in self.doc()["mon"].items():
            if _ten_shop(chu) == chuan_hoa(ten):
                if "diem tang" not in bo_dau(gia):
                    raise LoiVatPham(f"{ten} đang bán \"{gia}\", auto chỉ mua món trả bằng Điểm Tặng")
                so_gia = re.search(r"\d+", gia)
                return so, int(so_gia.group()) if so_gia else None
        raise LoiVatPham(f"Tiệm KNB không thấy {ten} ở nhóm đang chọn")

    def bam_mua(self, so):
        self._goi(f"ShopCustom_Item_Clicked({so})")

    def dong(self):
        self.lua.chay('if IsWindowShow("ShopCustom") then CloseWindow("ShopCustom", true) end')


class TuMuaDung:
    """Lớp chung; lớp con đặt TEN_VAT_PHAM, TEN_HIEU_UNG, SO_MUA_MOI_LAN và viết con_hieu_ung()."""
    TEN_VAT_PHAM = ""
    TEN_HIEU_UNG = ""
    SO_MUA_MOI_LAN = 1
    TIEM = "Nam Bắc Kỳ Hóa"
    NHOM = "Tiên Đan Linh Dược"

    def __init__(self, lua, in_log):
        self.lua = lua
        self.in_log = in_log
        self.luc_xem = 0.0
        self.nghi_den = 0.0

    def con_hieu_ung(self):
        """Số giây hiệu ứng còn lại (ước lượng), 0 nếu đã hết."""
        raise NotImplementedError

    def so_trong_tui(self):
        """{ô: số lượng} của vật phẩm trong túi."""
        cac_o = {}
        for dong in self.lua.chay(MA_DS_TUI).split(b"\n"):
            if dong:
                o, so, ten = dong.split(b"\t", 2)
                if chuan_hoa(giai_ma(ten)) == chuan_hoa(self.TEN_VAT_PHAM):
                    cac_o[int(o)] = int(so)
        return cac_o

    def _cho_tui_doi(self, tong_cu):
        het_han = time.time() + GIAY_CHO_DOI_TUI
        while time.time() < het_han:
            time.sleep(0.2)
            tong = sum(self.so_trong_tui().values())
            if tong != tong_cu:
                return tong
        return tong_cu

    def mua(self, so_luong=None):
        """
        Mua tối đa so_luong cái (mặc định SO_MUA_MOI_LAN) ở tiệm TIEM, nhóm NHOM; chỉ mua món trả bằng Điểm Tặng.
        Trả về số cái đã mua.
        """
        so_luong = so_luong or self.SO_MUA_MOI_LAN
        tiem = TiemKNB(self.lua)
        try:
            tiem.chon(self.TIEM, self.NHOM)
            o, _ = tiem.tim(self.TEN_VAT_PHAM)
            tong_dau = sum(self.so_trong_tui().values())
            tiem.bam_mua(o)
            if self._cho_tui_doi(tong_dau) == tong_dau:
                raise LoiVatPham(f"bấm mua {self.TEN_VAT_PHAM} không được (hết Điểm Tặng / túi đầy / "
                                 f"ô \"Xác nhận mua\" đang tích?)")
            for _ in range(so_luong - 1):
                time.sleep(GIAY_GIUA_MOI_LAN_MUA)
                tiem.bam_mua(o)
            time.sleep(GIAY_CHO_DOI_TUI)
            return sum(self.so_trong_tui().values()) - tong_dau
        finally:
            tiem.dong()

    def dung_mot(self):
        """Dùng 1 cái, chờ hiệu ứng hiện lại. Trả về số giây hiệu ứng sau khi dùng."""
        cac_o = self.so_trong_tui()
        tong = sum(cac_o.values())
        self.lua.chay(f"PlayerPackage:UseItem({min(cac_o)})")
        if self._cho_tui_doi(tong) == tong:
            raise LoiVatPham(f"dùng {self.TEN_VAT_PHAM} không được")
        het_han = time.time() + GIAY_CHO_DOI_TUI
        con = self.con_hieu_ung()
        while con <= 0 and time.time() < het_han:
            time.sleep(0.2)
            con = self.con_hieu_ung()
        return con

    def kiem_tra(self, ten, nen_dung=lambda: False):
        """
        Gọi mỗi lượt của vòng auto; tự giãn cách GIAY_GIUA_MOI_LAN_XEM giây. Hết hiệu ứng thì dùng 1 cái,
        túi không còn cái nào thì mua SO_MUA_MOI_LAN cái trước.
        """
        bay_gio = time.time()
        if bay_gio - self.luc_xem < GIAY_GIUA_MOI_LAN_XEM or bay_gio < self.nghi_den:
            return
        self.luc_xem = bay_gio
        if self.con_hieu_ung() > 0:
            return
        try:
            if not self.so_trong_tui():
                if nen_dung():
                    return
                da_mua = self.mua()
                self.in_log(f"{ten}: hết {self.TEN_HIEU_UNG}, đã mua {da_mua} {self.TEN_VAT_PHAM} ở Tiệm KNB")
            if nen_dung():
                return
            con = self.dung_mot()
            self.in_log(f"{ten}: đã dùng 1 {self.TEN_VAT_PHAM}, {self.TEN_HIEU_UNG} còn {mo_ta_thoi_gian(con)}, "
                        f"còn {sum(self.so_trong_tui().values())} cái trong túi")
        except LoiVatPham as loi:
            self.nghi_den = time.time() + GIAY_NGHI_KHI_LOI
            self.in_log(f"{ten}: không tự dùng {self.TEN_VAT_PHAM} được: {loi}. "
                        f"Thử lại sau {GIAY_NGHI_KHI_LOI // 60} phút")


class TuDungX2(TuMuaDung):
    TEN_VAT_PHAM = "Thiên Linh Đan"
    TEN_HIEU_UNG = "x2 kinh nghiệm"
    SO_MUA_MOI_LAN = 20

    def __init__(self, lua, in_log):
        super().__init__(lua, in_log)
        # Đồng hồ dưới 1 giờ: (số giây server báo, lúc thấy lần đầu). Server không báo lại thì tự trừ theo giờ máy.
        self.dong_ho = None

    def con_hieu_ung(self):
        phan = giai_ma(self.lua.chay(MA_DOC_X2)).split("\t")
        if len(phan) != 3:
            return 1  # không đọc được bảng nhiệm vụ thì coi như còn x2, không mua bừa
        chu, hien, giay = phan
        con = doc_giay_x2(chu, hien, giay)
        if MAU_THOI_GIAN.search(bo_ma_mau(chu)) or con <= 0:
            self.dong_ho = None
            return con
        if self.dong_ho is None or self.dong_ho[0] != con:
            self.dong_ho = (con, time.time())
        return max(con - (time.time() - self.dong_ho[1]), 0)


class TuDungCanKhonHo(TuMuaDung):
    TEN_VAT_PHAM = "Càn Khôn Hồ"
    TEN_HIEU_UNG = "buff Càn Khôn Hồ"
    SO_MUA_MOI_LAN = 2  # không chồng được, mỗi cái chiếm 1 ô túi

    def con_hieu_ung(self):
        for dong in giai_ma(self.lua.chay(MA_DS_BUFF)).split("\n"):
            giay, _, chu = dong.partition("\t")
            if chuan_hoa(bo_ma_mau(chu)).startswith(chuan_hoa(self.TEN_VAT_PHAM)):
                try:
                    return max(int(float(giay)), 1)
                except ValueError:
                    return 1
        return 0
