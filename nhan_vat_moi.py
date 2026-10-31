"""
TẠO NHÂN VẬT MỚI VÀ NHẬN ĐỒ TÂN THỦ CHO TÀI KHOẢN HOÀN TOÀN MỚI (tab "Tạo nhân vật").

Kịch bản ghi từ một lần chơi tay tài khoản caychay9 (ban_ghi/ghi_20261011_220455.txt):
    Chọn nhân vật : SelectRole_CreateRole() -> mã kiểm tra (tao_nhan_vat.giai_ma_kiem_tra) -> cửa sổ LoginCreateRole.
    Tạo           : CreateRole_SelectGirl() (chọn luôn avatar nữ đầu tiên), CreateRole_Name:SetText(tên),
                    CreateRole_BnClickCreateRole() -> GameProduceLogin:CreateRole(tên, 0).
    Vào game      : GameProduceLogin:SendEnterGameMsg(i) -> mã kiểm tra -> Đại Lý (160, 168).
    NPC Tân Thủ   : (111111, 9996) Gia Nhập Môn Phái -> (0, 324) Thiên Long; (111111, 6666) Vàng + ĐT.
    Túi           : mang Bách Bảo Nang, Bách Bảo Rương (chuột phải = nút ô túi :DoAction(), hộp "trang bị sẽ bị
                    khóa" bấm OK -> EquipItem).
    NPC Tân Thủ   : (111111, 1200) Nhận Trang Bị Tân Thủ (cần 16 ô trống nên phải mang túi trước), mang hết đồ.
    Túi           : dùng 3 Hộp Point Tân Thủ Lễ Bao (mỗi hộp 10.000.000 điểm tiềm năng).
    NPC Cộng Point: (111114, 7111) Cộng 10.000.000 -> (111114, 7121) Nội Lực, tới khi còn dưới 10.000.000 điểm.
Theo nhân vật mẫu caychay999:
    Tiệm KNB      : Nam Bắc Kỳ Hóa -> Tiên Đan Linh Dược: mua, dùng Càn Khôn Hồ.
                    Quảng Trường Hình Tượng -> Thú Cưỡi Tân Thủ: mua Đà Điểu; -> Kỵ Thuật: mua Kỵ Thuật: Đà Điểu.
                    Đóng shop, mang Đà Điểu (ô trang bị 8), dùng Kỵ Thuật.
Không xếp thanh phím tắt: phó bản dùng thẳng kỹ năng Kỵ thuật / Quay về Đại Lý thành (không cần ô F, không chiếm chuột).
    Hồi máu       : Hộp Point tăng máu tối đa mà máu hiện tại không đầy; mở hội thoại NPC Di Chuyển (Đại Lý) là hồi đầy
                    máu + nội lực, không cần chọn dòng nào.
    Xong          : EnterQuitWait(1) (Hệ thống -> Về chọn máy chủ), đăng nhập lại để tạo / nhận đồ nhân vật sau.
Tên nhân vật: tên tài khoản, rồi lặp thêm ký tự cuối (caychay10 -> caychay10, caychay100, caychay1000).
Tên bị trùng thì thử thêm số 1, 2... ở cuối.

Mỗi bước xem trạng thái trong game trước khi làm (đã vào phái, túi còn Bách Bảo Nang, còn Hộp Point...), nên chạy
lại trên nhân vật đã làm dở / đã xong cũng không nhận trùng.
"""
import threading
import time
import traceback

import psutil

import cau_hinh
import nang_cap_nhan_vat
from bang_ma_viscii import giai_ma
from dang_nhap import (CONG_MO_GAME, LoiDangNhap, LoiSaiRuleNhanVat, LoiSaiTaiKhoan, LuongDangNhap, bo_dau, cho_cua_so, chuoi_lua,
                       con_chay, dang_hien, dong_thong_bao, giu_client, lay_client_ranh, man_hinh_hien_tai,
                       mo_game, nha_cac_client,
                       noi_dung_thong_bao, tai_khoan_cua_pid, tat_game, thoat_ve_chon_may_chu,
                       trong_cua_so,
                       ve_chon_may_chu as ve_chon_may_chu_game)
from game_api import Game
from giai_captcha import LoiGiaiCaptcha
from lua_game import LoiLua
from pho_ban_pmp import (GIAY_CHO_GAME_TRA_LOI, GIAY_CHO_LAG, MA_DA_MANG, MAP_DAI_LY, SO_LAN_DUNG_TOI_DA,
                         SO_LAN_THU_MANG, LoiPhoBan, PhoBanPMP)
from tao_nhan_vat import giai_ma_kiem_tra
from tu_dung_vat_pham import LoiVatPham, TuDungCanKhonHo

MON_PHAI_THIEN_LONG = 6
CHUA_VAO_PHAI = 9

NPC_TAN_THU = ("Tân Thủ", (160, 166))
NPC_CONG_POINT = ("Cộng Point", (168, 142))
NPC_HOI_MAU = ("Di Chuyển", (165, 156))
DONG_VAO_PHAI = (111111, 9996)
DONG_THIEN_LONG = (0, 324)
DONG_VANG = (111111, 6666)
DONG_NHAN_TRANG_BI = (111111, 1200)
DONG_CONG_10_TRIEU = (111114, 7111)
DONG_NOI_LUC = (111114, 7121)
DIEM_MOI_LAN_CONG = 10_000_000
TIEN_VANG_TAN_THU = 100_000_000

MA_TUI_BACH_BAO = {10141030: "Bách Bảo Nang", 10141040: "Bách Bảo Rương"}
MA_TRANG_BI_TAN_THU = {
    10100000: "Thanh Đồng Đao", 10162420: "Tân Thủ - Khôi", 10162421: "Tân Thủ - Ngoa", 10162422: "Tân Thủ - Thủ",
    10162423: "Tân Thủ - Giáp", 10162424: "Tân Thủ - Kiên", 10162425: "Tân Thủ - Liên", 10162426: "Tân Thủ - Đái",
    10162427: "Tân Thủ - Giới", 10162428: "Tân Thủ - Ngọc", 10162429: "Tân Thủ - Uyển", 10163500: "Long Văn",
    10163518: "Ám Khí",
}
# Gói "Nhận Trang Bị Tân Thủ" có thêm một bộ Bách Bảo Nang / Rương không mang được (đã mang bộ ban đầu), nằm lại
# trong túi: còn thấy là đã nhận gói rồi.
MA_GOI_TAN_THU = set(MA_TRANG_BI_TAN_THU) - {10100000} | {10163506, 10163512}
MA_HOP_POINT = 30004622
O_TRANG_BI_KHOI = 1

GIAY_MOT_NHAN_VAT = 15 * 60
GIAY_CHO_HOP_MA = 15
GIAY_CHO_TAO_XONG = 25
GIAY_DONG_THONG_BAO_TAO = 5
GIAY_CHO_DANH_SACH_NHAN_VAT = 3
GIAY_CHO_VE_CHON_MAY_CHU = 40
SO_TEN_THU = 6
SO_ROUND_GHI_TEN = 3  # số tên theo quy tắc xét khi nhận nhân vật bị thêm số (bằng số round xoay vòng tối đa)
SO_LAN_TAO_MOT_TEN = 3
GIAY_CHO_MAY_CHU_BAN = 3
KHOA_TAO = threading.Lock()
SO_LAN_CONG_TOI_DA = 10

MA_DA_MANG_KHOI = MA_DA_MANG.replace("{o}", str(O_TRANG_BI_KHOI))
MA_TIEN = 'return tostring(Player:GetData("MONEY"))'
MA_DS_NHAN_VAT = ('local s = "" for i = 0, GameProduceLogin:GetRoleCount() - 1 do '
                  's = s .. GameProduceLogin:GetRoleInfo(i) .. "\\n" end return s')


def cac_ten_nhan_vat(tai_khoan, so_nhan_vat):
    """
    Tên định đặt cho nhân vật 1..so_nhan_vat: tên tài khoản, rồi lặp thêm ký tự cuối của nó.
    caychay10 -> caychay10, caychay100, caychay1000; caychay9 -> caychay9, caychay99, caychay999.
    """
    return [tai_khoan + tai_khoan[-1] * i for i in range(so_nhan_vat)]


def cung_ten(a, b):
    return a.casefold() == b.casefold()


def ten_sai_rule(tai_khoan, cac_ten):
    """Các nhân vật của tài khoản không theo quy tắc tên (xoay vòng nhận round theo tên)."""
    dung = cac_ten_nhan_vat(tai_khoan, SO_ROUND_GHI_TEN)
    return [ten for ten in cac_ten if not any(cung_ten(ten, t) for t in dung)]


def la_loi_ma_kiem_tra(chu):
    """"Kiểm tra chưa được duyệt, tạo nhân vật thất bại." - chưa qua mã kiểm tra tạo nhân vật."""
    chu = bo_dau(chu)
    return "kiem tra" in chu and "duyet" in chu


def ds_nhan_vat(lua):
    return [giai_ma(ten) for ten in lua.chay(MA_DS_NHAN_VAT).split(b"\n")[:-1]]


def da_xong(tai_khoan):
    return cau_hinh.doc_tai_khoan()["tao_nhan_vat_moi"]["da_xong"].get(tai_khoan.lower(), [])


def ghi_da_xong(tai_khoan, ten):
    cai_dat = cau_hinh.doc_tai_khoan()
    ds = cai_dat["tao_nhan_vat_moi"]["da_xong"].setdefault(tai_khoan.lower(), [])
    if not any(cung_ten(ten, t) for t in ds):
        ds.append(ten)
        cau_hinh.luu_tai_khoan(cai_dat)


def dong_bo_da_xong(tai_khoan, cac_ten):
    """
    Sổ «đã tạo + nhận đồ» và tên thay thế ghi nhân vật mà tài khoản không còn (bị xóa / server reset): bỏ đi để tạo lại
    và nhận đồ tân thủ cho nhân vật mới. Trả về các tên đã bỏ.
    """
    cai_dat = cau_hinh.doc_tai_khoan()
    tao = cai_dat["tao_nhan_vat_moi"]
    khoa = tai_khoan.lower()
    con = lambda ten: any(cung_ten(ten, c) for c in cac_ten)  # noqa: E731
    cu = tao["da_xong"].get(khoa, [])
    bo = [t for t in cu if not con(t)]
    thuc = tao["ten_thuc"].get(khoa, {})
    bo_thuc = [k for k, v in thuc.items() if not con(v)]
    if not bo and not bo_thuc:
        return []
    tao["da_xong"][khoa] = [t for t in cu if con(t)]
    for k in bo_thuc:
        del thuc[k]
    cau_hinh.luu_tai_khoan(cai_dat)
    return bo


def ten_thuc(tai_khoan, ten):
    """Tên nhân vật đã tạo thay cho tên định đặt ten (trùng tên phải thêm số), chưa ghi thì là chính ten."""
    ds = cau_hinh.doc_tai_khoan()["tao_nhan_vat_moi"]["ten_thuc"].get(tai_khoan.lower(), {})
    return ds.get(ten.lower(), ten)


def ghi_ten_thuc(tai_khoan, ten, thuc):
    cai_dat = cau_hinh.doc_tai_khoan()
    cai_dat["tao_nhan_vat_moi"]["ten_thuc"].setdefault(tai_khoan.lower(), {})[ten.lower()] = thuc
    cau_hinh.luu_tai_khoan(cai_dat)


def la_loi_may_chu_ban(chu):
    """Server bận (nhiều game bấm tạo cùng lúc): không phải lỗi tên, thử lại đúng tên đó."""
    chu = bo_dau(chu)
    return any(c in chu for c in ("dang thao tac", "dang ban", "loi noi bo"))


def doc_danh_sach(chu):
    """Mỗi dòng "tài_khoản mật_khẩu" (cách nhau bởi dấu cách, tab, dấu phẩy hoặc |). Sai dòng nào thì báo ValueError."""
    ds = []
    for so, dong in enumerate(chu.splitlines(), 1):
        phan = dong.replace(",", " ").replace("|", " ").split()
        if not phan:
            continue
        if len(phan) != 2:
            raise ValueError(f"Dòng {so} \"{dong.strip()}\" cần đúng 2 phần: tài khoản và mật khẩu")
        ds.append({"ten_dang_nhap": phan[0], "mat_khau": phan[1]})
    return ds


class NhanDoTanThu(PhoBanPMP):
    """Các bước làm trong game cho một nhân vật mới. Mượn phần chạy tới NPC / mở hội thoại của PhoBanPMP."""

    def __init__(self, game, ten, in_log, nen_dung, bao_trang_thai):
        super().__init__(game, in_log)
        self.ten, self.nen_dung, self.bao_trang_thai = ten, nen_dung, bao_trang_thai
        self.trang_thai = {}
        self.che_do = "tan_thu"
        self.het_han_vong = time.time() + GIAY_MOT_NHAN_VAT
        self.da_toi_cong_point = False

    def _mo_ta(self, chu):
        self.bao_trang_thai(f"{self.ten}: {chu}")

    def _tien(self):
        return int(float(self.game.lua.chay(MA_TIEN)))

    def _noi_chuyen(self, npc, cac_dong):
        """Mở hội thoại NPC rồi chọn lần lượt các dòng (dòng sau phải hiện ra mới chọn)."""
        ten_npc, xy = npc
        self._mo_ta(f"tới NPC {ten_npc}")
        if npc == NPC_CONG_POINT:
            self.da_toi_cong_point = True
        self._mo_hoi_thoai(ten_npc, xy, cac_dong[0], dan_doi=False)
        for i, dong in enumerate(cac_dong):
            if i and not self._cho(lambda: (lambda ht: ht and any((s, e) == dong for _, s, e, _ in ht[1]))(
                    self._hoi_thoai()), GIAY_CHO_GAME_TRA_LOI * 2):
                raise LoiPhoBan(f"NPC {ten_npc} không hiện dòng {dong} ({self._chu_hoi_thoai()})")
            self._chon(dong)
            time.sleep(0.5)

    def chay(self):
        tt = self._tt()
        if tt is None:
            raise LoiPhoBan("chưa vào game")
        self.in_log(f"{self.ten}: bắt đầu nhận đồ tân thủ [{tt['map']} ({tt['x']}, {tt['y']})]")
        self._vao_thien_long(tt)
        self._nhan_vang()
        self._mang(MA_TUI_BACH_BAO)
        self._nhan_trang_bi()
        self._mang(MA_TRANG_BI_TAN_THU)
        self._dung_hop_point()
        self._cong_noi_luc()
        self.roi_cong_point()
        self._can_khon_ho()
        self._thu_cuoi()
        self.hoi_mau()
        con_lai = {
            "chưa vào Thiên Long": (self._tt() or {}).get("mon_phai") != MON_PHAI_THIEN_LONG,
            "chưa mang trang bị tân thủ": self.game.lua.chay(MA_DA_MANG_KHOI) != b"1",
            "còn Hộp Point": self._so_luong({MA_HOP_POINT}) > 0,
            "còn trên 10.000.000 điểm tiềm năng": self.game.diem_tiem_nang() >= DIEM_MOI_LAN_CONG,
        }
        loi = [mo_ta for mo_ta, con in con_lai.items() if con]
        if loi:
            raise LoiPhoBan("chưa xong: " + ", ".join(loi))
        self.in_log(f"{self.ten}: đã nhận xong đồ tân thủ")

    def roi_cong_point(self):
        """
        Đứng ở NPC Cộng Point có góc lag, chạy đi là bị giật về: tăng point xong thì dùng Về thành Đại Lý (thử lại
        tới khi thấy đổi chỗ). Không ghé NPC Cộng Point thì thôi.
        """
        if not self.da_toi_cong_point:
            return
        self.game.lua.chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
        for lan in range(1, SO_LAN_THU_MANG + 1):
            self._kiem_tra()
            self._mo_ta(f"tăng point xong, Về thành {MAP_DAI_LY}" + (f" (lần {lan})" if lan > 1 else ""))
            try:
                if self._ve_thanh_tai_dai_ly():
                    self.da_toi_cong_point = False
                    return
            except LoiPhoBan as loi:
                self.in_log(f"{self.ten}: tăng point xong mà không Về thành được: {loi}")
                return
        self.in_log(f"{self.ten}: dùng Về thành {SO_LAN_THU_MANG} lần vẫn chưa rời NPC Cộng Point")

    def hoi_mau(self):
        """Máu / nội lực chưa đầy thì tới NPC Di Chuyển mở hội thoại (game hồi đầy), rồi đóng hội thoại."""
        def day():
            tt = self._tt()
            return tt and tt["hp"] >= tt["hp_toi_da"] and tt["mp"] >= tt["mp_toi_da"]
        if day():
            return
        try:
            self._mo_hoi_thoai(*NPC_HOI_MAU, (-1, -1), bo_qua_neu_khong_co=True, dan_doi=False)
            if self._cho(day, GIAY_CHO_GAME_TRA_LOI):
                self.in_log(f"{self.ten}: đã hồi đầy máu ở NPC {NPC_HOI_MAU[0]}")
            else:
                self.in_log(f"{self.ten}: nói chuyện NPC {NPC_HOI_MAU[0]} mà máu chưa đầy")
        except LoiPhoBan as loi:
            self.in_log(f"{self.ten}: chưa hồi máu được: {loi}")
        finally:
            self.game.lua.chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')

    def _vao_thien_long(self, tt):
        if tt["mon_phai"] == MON_PHAI_THIEN_LONG:
            return
        if tt["mon_phai"] != CHUA_VAO_PHAI:
            self.in_log(f"{self.ten}: đã ở môn phái khác (mã {tt['mon_phai']}), không vào Thiên Long")
            return
        self._noi_chuyen(NPC_TAN_THU, (DONG_VAO_PHAI, DONG_THIEN_LONG))
        if not self._cho(lambda: (self._tt() or {}).get("mon_phai") == MON_PHAI_THIEN_LONG,
                         GIAY_CHO_GAME_TRA_LOI + GIAY_CHO_LAG):
            raise LoiPhoBan(f"chọn Thiên Long mà chưa vào phái ({self._chu_hoi_thoai()})")
        self.in_log(f"{self.ten}: đã gia nhập Thiên Long")

    def _nhan_vang(self):
        tien = self._tien()
        if tien >= TIEN_VANG_TAN_THU:
            return
        self._noi_chuyen(NPC_TAN_THU, (DONG_VANG,))
        if self._cho(lambda: self._tien() > tien, GIAY_CHO_GAME_TRA_LOI + GIAY_CHO_LAG):
            self.in_log(f"{self.ten}: đã nhận Vàng + ĐT, tiền {tien} -> {self._tien()}")
        else:
            self.in_log(f"{self.ten}: chọn \"Tôi muốn nhận Vàng + ĐT\" mà tiền không đổi ({self._chu_hoi_thoai()})")

    def _nhan_trang_bi(self):
        if self.game.lua.chay(MA_DA_MANG_KHOI) == b"1" or self._so_luong(MA_GOI_TAN_THU):
            return
        self._noi_chuyen(NPC_TAN_THU, (DONG_NHAN_TRANG_BI,))
        if not self._cho(lambda: self._so_luong(MA_GOI_TAN_THU), GIAY_CHO_GAME_TRA_LOI * 2 + GIAY_CHO_LAG):
            raise LoiPhoBan(f"chọn \"Nhận Trang Bị Tân Thủ\" mà không nhận được đồ ({self._chu_hoi_thoai()})")
        self.in_log(f"{self.ten}: đã nhận trang bị tân thủ")

    def _dung_hop_point(self):
        """Dùng hết Hộp Point; game chậm thì chờ thêm GIAY_CHO_LAG, thử lại SO_LAN_THU_MANG lần mới báo lỗi."""
        that_bai = 0
        for _ in range(SO_LAN_DUNG_TOI_DA):
            self._kiem_tra()
            tui = self._tui()
            cac_o = sorted(o for o, (ma, _) in tui.items() if ma == MA_HOP_POINT)
            if not cac_o:
                return
            con = self._so_luong({MA_HOP_POINT})
            diem = self.game.diem_tiem_nang()
            self._mo_ta(f"dùng Hộp Point Tân Thủ Lễ Bao (còn {con})")
            self._chuot_phai(cac_o[0])
            if not (self._cho(lambda: self._so_luong({MA_HOP_POINT}) < con, GIAY_CHO_GAME_TRA_LOI)
                    or self._cho(lambda: self._so_luong({MA_HOP_POINT}) < con, GIAY_CHO_LAG)):
                that_bai += 1
                if that_bai >= SO_LAN_THU_MANG:
                    raise LoiPhoBan(f"dùng Hộp Point Tân Thủ Lễ Bao {that_bai} lần không được "
                                    f"({self._chu_hoi_thoai()})")
                self.in_log(f"{self.ten}: dùng Hộp Point chưa thấy mất hộp (lần {that_bai}/{SO_LAN_THU_MANG}), thử lại")
                continue
            that_bai = 0
            self._cho(lambda: self.game.diem_tiem_nang() > diem, GIAY_CHO_LAG)
            self.in_log(f"{self.ten}: đã dùng 1 Hộp Point Tân Thủ Lễ Bao, điểm tiềm năng {diem} -> "
                        f"{self.game.diem_tiem_nang()}")

    def _cong_noi_luc(self):
        that_bai = 0
        for _ in range(SO_LAN_CONG_TOI_DA + SO_LAN_THU_MANG):
            diem = self.game.diem_tiem_nang()
            if diem < DIEM_MOI_LAN_CONG:
                return
            self._noi_chuyen(NPC_CONG_POINT, (DONG_CONG_10_TRIEU, DONG_NOI_LUC))
            if not (self._cho(lambda: self.game.diem_tiem_nang() <= diem - DIEM_MOI_LAN_CONG, GIAY_CHO_GAME_TRA_LOI)
                    or self._cho(lambda: self.game.diem_tiem_nang() <= diem - DIEM_MOI_LAN_CONG, GIAY_CHO_LAG)):
                that_bai += 1
                if that_bai >= SO_LAN_THU_MANG:
                    raise LoiPhoBan(f"cộng 10.000.000 Nội Lực {that_bai} lần không được ({self._chu_hoi_thoai()})")
                self.in_log(f"{self.ten}: cộng Nội Lực chưa thấy trừ điểm (lần {that_bai}/{SO_LAN_THU_MANG}), thử lại")
                continue
            that_bai = 0
            self.in_log(f"{self.ten}: đã cộng 10.000.000 điểm Nội Lực, còn {self.game.diem_tiem_nang()} điểm")

    def _can_khon_ho(self):
        """Tiệm KNB -> Nam Bắc Kỳ Hóa -> Tiên Đan Linh Dược: mua 1 Càn Khôn Hồ rồi dùng (đang có buff thì thôi)."""
        ckh = TuDungCanKhonHo(self.game.lua, self.in_log)
        if ckh.con_hieu_ung() > 0:
            return
        try:
            if not ckh.so_trong_tui():
                self._mo_ta("mua Càn Khôn Hồ")
                ckh.mua(1)
                self.in_log(f"{self.ten}: đã mua Càn Khôn Hồ")
            self._mo_ta("dùng Càn Khôn Hồ")
            ckh.dung_mot()
            self.in_log(f"{self.ten}: đã dùng Càn Khôn Hồ")
        except LoiVatPham as loi:
            self.in_log(f"{self.ten}: không mua / dùng Càn Khôn Hồ được: {loi}")


class LuongTaoNhanVat(LuongDangNhap):
    """
    Lần lượt từng tài khoản: mở game, đăng nhập, tạo đủ so_nhan_vat nhân vật, vào từng nhân vật nhận đồ tân thủ,
    xong tài khoản thì tắt game.
    """

    def __init__(self, ds_tai_khoan, cai_dat, tuy_chon, hang_doi, hwnd=None, giu_game=False):
        """hwnd: dùng game đang mở này cho tài khoản đầu; giu_game: xong thì để game ở màn hình chọn nhân vật."""
        super().__init__({"ten_dang_nhap": "", "mat_khau": ""}, dict(cai_dat, giai_ma_kiem_tra=True), hang_doi)
        self.chi_co_mot_may_chu_thi_chon = True
        self.ds_tai_khoan = ds_tai_khoan
        self.tuy_chon = tuy_chon
        self.giu_game = giu_game
        self.game = None
        if hwnd:
            try:
                self.game = Game(hwnd)
                self.pid = self.game.lua.pid
                giu_client(self.pid, self)
            except (LoiLua, OSError):
                self.game = None
        self.ket_qua = {}
        self.da_qua_ma = False

    def in_log(self, chu):
        self.hang_doi.put(("log", f"[Tạo nhân vật {self.tai_khoan['ten_dang_nhap']}] {chu}"))

    def bao_trang_thai(self, mo_ta):
        self.hang_doi.put(("trang_thai_tao_nv", f"{self.tai_khoan['ten_dang_nhap']}: {mo_ta}"))

    def run(self):
        try:
            for tai_khoan in self.ds_tai_khoan:
                if self.dung.is_set():
                    break
                self.tai_khoan = dict(tai_khoan, nhan_vat="")
                self.ket_qua[tai_khoan["ten_dang_nhap"]] = self.lam_tai_khoan()
        finally:
            nha_cac_client(self)
        tom_tat = ", ".join(f"{tk}: {kq}" for tk, kq in self.ket_qua.items())
        self.hang_doi.put(("log", f"[Tạo nhân vật] {'Đã dừng' if self.dung.is_set() else 'Xong'}. {tom_tat}"))
        self.hang_doi.put(("trang_thai_tao_nv", "Đã dừng" if self.dung.is_set() else "Xong"))

    def lam_tai_khoan(self):
        so_lan = self.cai_dat["so_lan_thu_toi_da"]
        xong = False
        try:
            for lan in range(1, so_lan + 1):
                try:
                    if not (self.pid and con_chay(self.pid)):
                        self.mo_game_moi(lan, so_lan)
                    self.xu_ly(self.game)
                    xong = True
                    return "xong"
                except LoiSaiTaiKhoan as loi:
                    self.sai_tai_khoan = True
                    self.in_log(f"Dừng: {loi}")
                    return "sai tài khoản/mật khẩu"
                except LoiSaiRuleNhanVat as loi:
                    self.sai_rule = loi.cac_ten
                    self.in_log(f"Dừng: {loi}")
                    return "tên nhân vật sai rule"
                except LoiPhoBan as loi:
                    if self.dung.is_set():
                        return "đã dừng"
                    # Lỗi ở một bước nhận đồ: game vẫn chạy thì làm lại ngay trong game này. Tắt game thì server còn
                    # giữ nhân vật online, đăng nhập lại phải chờ thêm.
                    self.in_log(f"Lần {lan}/{so_lan} thất bại: {loi}"
                                + (", làm lại trong game đang mở" if self.pid and con_chay(self.pid) else ""))
                    if self.pid and con_chay(self.pid):
                        self.dung.wait(5)
                        continue
                except (LoiDangNhap, LoiGiaiCaptcha, LoiLua, OSError, psutil.Error) as loi:
                    if self.dung.is_set():
                        return "đã dừng"
                    self.in_log(f"Lần {lan}/{so_lan} thất bại: {loi}")
                except Exception:
                    if self.dung.is_set():
                        return "đã dừng"
                    self.in_log(f"Lần {lan}/{so_lan} lỗi không mong đợi\n{traceback.format_exc()}")
                if self.pid:
                    thoat_ve_chon_may_chu(self.pid, self.in_log, self.dung.is_set)
                    if not con_chay(self.pid):
                        self.pid = None
                self.dung.wait(5)
            return "thất bại"
        finally:
            if self.pid and not self.dung.is_set() and not (self.giu_game and xong):
                thoat_ve_chon_may_chu(self.pid, self.in_log, self.dung.is_set)
                self.pid = None
                nha_cac_client(self)

    def mo_game_moi(self, lan, so_lan):
        cd = self.cai_dat
        if self._dung_client_ranh():
            return
        self.bao_trang_thai(f"Chờ lượt mở game (lần {lan}/{so_lan})")
        CONG_MO_GAME.cho_luot(cd["so_game_moi_dot"], cd["giay_giua_moi_dot"], self.dung.is_set)
        if self._dung_client_ranh():
            return
        self.bao_trang_thai(f"Mở game (lần {lan}/{so_lan})")
        tk = self.tai_khoan["ten_dang_nhap"]
        self.pid = mo_game(cd["thu_muc_game"], tk)
        giu_client(self.pid, self)
        self.in_log(f"Đã mở game (pid {self.pid}), "
                    f"chờ {cd['giay_cho_truoc_khi_nap_dll']} giây cho game tải xong")
        self.game = Game(cho_cua_so(self.pid, cd["giay_cho_truoc_khi_nap_dll"], self.dung.is_set))

    def _dung_client_ranh(self):
        hwnd = lay_client_ranh(self)
        if not hwnd:
            return False
        self.game = Game(hwnd)
        self.pid = self.game.lua.pid
        self.in_log(f"Dùng client đang rảnh (pid {self.pid}), không mở game mới")
        return True

    def xu_ly(self, game):
        tk = self.tai_khoan["ten_dang_nhap"]
        so_nhan_vat = self.tuy_chon["so_nhan_vat"]
        while True:
            self.tai_khoan["nhan_vat"] = ""
            self.toi_chon_nhan_vat(game)
            cac_ten = ds_nhan_vat(game.lua)
            if self.tuy_chon.get("dung_ten"):
                self.kiem_tra_ds_nhan_vat(cac_ten)
                bo = dong_bo_da_xong(tk, cac_ten)
                if bo:
                    self.in_log(f"Sổ ghi đã tạo {', '.join(bo)} nhưng tài khoản không còn, tạo lại + nhận đồ tân thủ")
            if self.tuy_chon["nhan_do_tan_thu"]:
                chua = [ten for ten in cac_ten if not any(cung_ten(ten, t) for t in da_xong(tk))]
                if chua:
                    self.nhan_do(game, chua[0])
                    continue
            ten_du_dinh = cac_ten_nhan_vat(tk, so_nhan_vat)
            self._nhan_ten_thuc(tk, cac_ten)
            thieu = [t for t in ten_du_dinh if not any(cung_ten(ten_thuc(tk, t), c) for c in cac_ten)]
            # dung_ten (xoay vòng): cần đúng các tên theo quy tắc; không thì chỉ cần đủ số nhân vật.
            if not thieu or (len(cac_ten) >= so_nhan_vat and not self.tuy_chon.get("dung_ten")):
                self.in_log(f"Tài khoản đã đủ {so_nhan_vat} nhân vật: {', '.join(cac_ten)}")
                return
            ten = self.tao_nhan_vat(game.lua, thieu[0], cac_ten)
            if not cung_ten(ten, thieu[0]):
                ghi_ten_thuc(tk, thieu[0], ten)
                self.in_log(f"Tên {thieu[0]} không tạo được, dùng {ten} thay cho nhân vật này")

    def _nhan_ten_thuc(self, tk, cac_ten):
        """
        Nhân vật tạo trước đây bị thêm số vì trùng tên (caychay15 -> caychay151) mà chưa ghi ten_thuc: ghi lại để
        xoay vòng vào đúng nhân vật đó. Không nhận tên trùng với tên định đặt khác (caychay155 là nhân vật round 2).
        """
        tat_ca = cac_ten_nhan_vat(tk, SO_ROUND_GHI_TEN)
        da_dung = {ten_thuc(tk, t).lower() for t in tat_ca} | {t.lower() for t in tat_ca}
        for t in tat_ca:
            if any(cung_ten(ten_thuc(tk, t), c) for c in cac_ten):
                continue
            le = [c for c in cac_ten if c.lower().startswith(t.lower()) and len(c) == len(t) + 1
                  and c[-1].isdigit() and c.lower() not in da_dung]
            if le:
                ghi_ten_thuc(tk, t, le[0])
                da_dung.add(le[0].lower())
                self.in_log(f"Nhân vật {le[0]} được dùng thay cho tên {t}")

    def toi_chon_nhan_vat(self, game):
        """Đi tới màn hình chọn nhân vật (đăng nhập nếu cần; đang trong game thì về chọn máy chủ)."""
        while True:
            try:
                if dang_hien(game.lua, "LoginCreateRole"):
                    game.lua.chay(trong_cua_so("LoginCreateRole", "CreateRole_BnClickReturnSelectRole()"))
                    time.sleep(1)
            except LoiLua:
                pass  # game mới mở, đang tải
            man = self.dieu_khien(game, dung_o=("chon_nhan_vat",))
            if man == "chon_nhan_vat" and \
                    tai_khoan_cua_pid(game.lua.pid) != self.tai_khoan["ten_dang_nhap"].lower():
                # Game dùng lại còn ở màn chọn nhân vật của tài khoản khác: về đăng nhập đúng tài khoản.
                self.in_log("Game đang ở màn chọn nhân vật của tài khoản khác, quay lại đăng nhập")
                game.lua.chay(trong_cua_so("LoginSelectRole", "SelectRole_Return()"))
                time.sleep(2)
                continue
            if man == "chon_nhan_vat":
                time.sleep(GIAY_CHO_DANH_SACH_NHAN_VAT)
                if man_hinh_hien_tai(game.lua) == "chon_nhan_vat":
                    return
            else:
                self.ve_chon_may_chu(game)

    def ve_chon_may_chu(self, game):
        self.bao_trang_thai("Về chọn máy chủ")
        ve_chon_may_chu_game(game, self.dung.is_set, self.in_log)

    def nhan_do(self, game, ten):
        tk = self.tai_khoan["ten_dang_nhap"]
        self.tai_khoan["nhan_vat"] = ten
        self.in_log(f"Vào game bằng {ten} để nhận đồ tân thủ")
        if self.dieu_khien(game) != "vao_game":
            raise LoiDangNhap(f"Chưa vào được game bằng {ten}")
        NhanDoTanThu(game, ten, self.in_log, self.dung.is_set, self.bao_trang_thai).chay()
        ghi_da_xong(tk, ten)
        try:
            nang_cap_nhan_vat.nang_cap(game, ten, self.in_log, self.dung.is_set, self.bao_trang_thai)
        except Exception as loi:
            if self.dung.is_set():
                raise LoiDangNhap("Đã dừng")
            self.in_log(f"{ten}: nâng cấp nhân vật chưa xong ({str(loi) or type(loi).__name__}), "
                        "lần đăng nhập sau làm tiếp")
        self.ve_chon_may_chu(game)

    def ve_chon_nhan_vat(self, lua):
        lua.chay(trong_cua_so("LoginCreateRole", "CreateRole_BnClickReturnSelectRole()"))
        het_han = time.time() + GIAY_CHO_GAME_TRA_LOI
        while time.time() < het_han and dang_hien(lua, "LoginCreateRole"):
            time.sleep(0.5)
        time.sleep(1)

    def mo_man_tao(self, lua):
        """
        Bấm Tạo nhân vật, giải mã kiểm tra tới khi mở cửa sổ LoginCreateRole. Trả về True nếu đã qua mã kiểm tra.
        Vừa từ trong game về, game có lúc mở thẳng màn hình tạo mà không hỏi mã, rồi server báo "Kiểm tra chưa được
        duyệt": khi đó trả về False để người gọi về chọn nhân vật bấm lại.
        """
        if dang_hien(lua, "LoginCreateRole"):
            if self.da_qua_ma:
                return True
            self.ve_chon_nhan_vat(lua)
        self.bao_trang_thai("Bấm Tạo nhân vật")
        lua.chay("SelectRole_CreateRole()")
        het_han = time.time() + GIAY_CHO_HOP_MA
        while time.time() < het_han and not (dang_hien(lua, "TextValidate") or dang_hien(lua, "LoginCreateRole")):
            time.sleep(0.5)
        if dang_hien(lua, "TextValidate"):
            self.bao_trang_thai("Giải mã kiểm tra tạo nhân vật")
            self.da_qua_ma = giai_ma_kiem_tra(lua, self.in_log, self.dung.is_set)
        if not dang_hien(lua, "LoginCreateRole"):
            raise LoiDangNhap("Không mở được màn hình tạo nhân vật")
        return self.da_qua_ma

    def kiem_tra_ds_nhan_vat(self, cac_ten):
        if not self.tuy_chon.get("dung_ten"):
            return
        sai = ten_sai_rule(self.tai_khoan["ten_dang_nhap"], cac_ten)
        if sai:
            raise LoiSaiRuleNhanVat(sai)

    def tao_nhan_vat(self, lua, ten_goc, cac_ten_dang_co):
        if self.tuy_chon.get("dung_ten"):
            cac_ten_thu = [ten_goc]
        else:
            cac_ten_thu = [ten_goc] + [f"{ten_goc}{so}" for so in range(1, SO_TEN_THU)]
        self.da_qua_ma = False
        for ten in cac_ten_thu:
            if any(cung_ten(ten, c) for c in cac_ten_dang_co):
                continue
            for _ in range(SO_LAN_TAO_MOT_TEN):
                self.mo_man_tao(lua)
                self.bao_trang_thai(f"Chờ lượt bấm Tạo {ten}")
                # Nhiều game bấm Tạo cùng lúc thì server báo bận / lỗi nội bộ (có khi vẫn tạo): mỗi lần một game.
                with KHOA_TAO:
                    self.bao_trang_thai(f"Tạo nhân vật {ten}")
                    lua.chay(trong_cua_so("LoginCreateRole",
                                          f"CreateRole_SelectGirl() CreateRole_BnSelFace1() "
                                          f"CreateRole_Name:SetText({chuoi_lua(ten)}) CreateRole_BnClickCreateRole()"))
                    loi = self.cho_tao_xong(lua, ten)
                if loi is None:
                    self.in_log(f"Đã tạo nhân vật {ten} (nữ, avatar đầu tiên)")
                    return ten
                if la_loi_may_chu_ban(loi):
                    self.in_log(f"Tạo {ten}: game báo \"{loi}\", xem lại danh sách rồi thử lại đúng tên này")
                    self.ve_chon_nhan_vat(lua)
                    self.da_qua_ma = False
                    time.sleep(GIAY_CHO_MAY_CHU_BAN)
                    if any(cung_ten(ten, c) for c in ds_nhan_vat(lua)):
                        self.in_log(f"Đã tạo nhân vật {ten} (nữ, avatar đầu tiên)")
                        return ten
                    continue
                if not la_loi_ma_kiem_tra(loi):
                    break
                self.da_qua_ma = False
                self.in_log(f"Không tạo được {ten}: {loi}, làm lại mã kiểm tra")
            else:
                raise LoiDangNhap(f"Tạo {ten} {SO_LAN_TAO_MOT_TEN} lần vẫn chưa được")
            # Còn lại là lỗi về tên (trùng, không hợp lệ...): thử tên sau, vẫn ở màn hình tạo, khỏi nhập lại mã.
            self.in_log(f"Không tạo được {ten}: {loi}" + (", thử tên khác" if ten != cac_ten_thu[-1] else ""))
        if self.tuy_chon.get("dung_ten"):
            raise LoiSaiRuleNhanVat([f"{ten_goc} (không tạo được đúng tên)"])
        raise LoiDangNhap(f"Không tạo được nhân vật nào trong các tên {', '.join(cac_ten_thu)}")

    def cho_tao_xong(self, lua, ten):
        """
        None nếu nhân vật ten đã có trong danh sách; game báo lỗi thì trả về chữ game báo. Quá lâu không rõ kết quả
        thì ném LoiDangNhap (không thử tên khác, kẻo nhân vật đã tạo mà danh sách chưa kịp hiện).
        """
        het_han = time.time() + GIAY_CHO_TAO_XONG
        chu_bao, luc_bao = "", None
        while time.time() < het_han:
            if self.dung.is_set():
                raise LoiDangNhap("Đã dừng")
            thong_bao = dang_hien(lua, "LoginSelectServerQuest")
            dang_tao = dang_hien(lua, "LoginCreateRole")
            if thong_bao:
                chu_bao = noi_dung_thong_bao(lua) or chu_bao
                luc_bao = luc_bao or time.time()
                if time.time() - luc_bao > GIAY_DONG_THONG_BAO_TAO:
                    dong_thong_bao(lua)
                    luc_bao = None
            elif not dang_tao and dang_hien(lua, "LoginSelectRole"):
                if any(cung_ten(ten, c) for c in ds_nhan_vat(lua)):
                    return None
            elif dang_tao and chu_bao:
                return chu_bao
            time.sleep(0.5)
        if chu_bao and dang_hien(lua, "LoginCreateRole"):
            return chu_bao
        raise LoiDangNhap(f"Bấm Tạo {ten} mà sau {GIAY_CHO_TAO_XONG} giây chưa thấy nhân vật mới"
                          + (f" (game báo: {chu_bao})" if chu_bao else ""))
