"""
NÂNG CẤP NHÂN VẬT: tự chạy mỗi khi đăng nhập xong một nhân vật chưa nâng cấp (LuongDangNhap.nang_cap_sau_dang_nhap,
tab Tài khoản / xoay vòng; nhân vật mới tạo thì sau khi nhận đồ tân thủ). Kịch bản ghi từ một lần chơi tay caychay344
(ghi_thao_tac/ghi_20261027_211657.txt):
    0. Chưa ở Đại Lý thì dùng kỹ năng Quay về Đại Lý thành trước (NPC GIFTCODE / Cộng Point đều ở Đại Lý).
    1. Túi: Xếp (Packet_PackUp_Clicked). Túi có Bách Bảo Nang / Rương 9 sao thì tháo bộ thường ở ô trang bị 9 / 10
       (nút ô "Khác" của bảng nhân vật :DoSubAction() = chuột phải) rồi mang bộ 9 sao. Không có thì bỏ qua.
    2. Tiệm KNB: Nhiệt Mại Thương Phẩm -> Thần Khí Tân Thủ, mua món đầu; Tiệm Trân Thú -> Trân Thú Sơ Cấp, mua
       Nga Mi Biến Dị. Đóng shop, mang thần khí, dùng trứng. Danh sách món về chậm: chờ món đầu có giá Điểm Tặng.
    3. NPC GIFTCODE (156, 165): dòng (350097, 999) mở NewbieCardActivation, NewUserCard(code, 0) cho từng code.
    4. Mang 10 món Hoàng Kim từ code, vứt đồ cũ (Tân Thủ, Thanh Đồng Đao, Bách Bảo thường), dùng hết Hộp Point.
    5. NPC Cộng Point: (111114, 7333) Rút 10.000.000 -> (111114, 7351) Nội Lực, 2 lần.
    6. Nội lực (SPR, bảng Alt+C) chưa tới NOI_LUC_TOI_DA: (111114, 7111) Cộng 10.000.000 -> (111114, 7121) Nội Lực.
       Còn lại: cộng 10.000.000 Thân Pháp (7124) tới khi dưới 10.000.000, lẻ thì cộng thẳng như bấm Duyệt ở Alt+C.

File DUONG_DAN (cạnh AutoHoc.exe) lưu nhân vật đã nâng cấp; có trong file (xong) thì không làm lại. Đang làm dở thì
ghi các bước đã xong để chạy lại không mua / rút trùng:
    {"<tên chuẩn hóa>": {"ten": "<tên>", "luc": "YYYY-mm-dd HH:MM:SS"[, "xong": false, "buoc": [1, 2]]}}
"""
import json
import os
import threading
import time
import traceback
from datetime import datetime

from auto_chuyen_sinh import chuan_hoa
from bang_ma_viscii import giai_ma
from dang_nhap import bo_dau, dang_hien, trong_cua_so, chuoi_lua
from thu_muc import THU_MUC_APP

DUONG_DAN = os.path.join(THU_MUC_APP, "nang_cap_da_xong.json")
GIFTCODE = ("CHAOMUNGNHATKIEM01", "MUNG100THANHVIENZL", "MUNG150THANHVIENZL", "ZALO200THANHVIEN26")

NPC_GIFTCODE = ("GIFTCODE", (156, 165))
DONG_NHAP_CODE = (350097, 999)
DONG_RUT_10_TRIEU = (111114, 7333)
DONG_RUT_NOI_LUC = (111114, 7351)
DONG_CONG_THAN_PHAP = (111114, 7124)
SO_LAN_RUT_NOI_LUC = 2
NOI_LUC_TOI_DA = 250_000_000
SO_LAN_THU_CONG = 3

# (ô trang bị, nút ô ở tab "Khác" của bảng nhân vật, mã bộ thường, mã bộ 9 sao, tên)
BACH_BAO = ((9, "OtherInfo_Packet1_Skill1", 10141030, 10163506, "Bách Bảo Nang"),
            (10, "OtherInfo_Packet2_Skill1", 10141040, 10163512, "Bách Bảo Rương"))
TIEM_THAN_KHI = ("Nhiệt Mại Thương Phẩm", "Thần Khí Tân Thủ")
TIEM_TRUNG = ("Tiệm Trân Thú", "Trân Thú Sơ Cấp", "Nga Mi Biến Dị")
TIEM_LAM_MOI = "Quảng Trường Hình Tượng"
O_VU_KHI = 0
MA_HOANG_KIM = {
    10162450: "Hoàng Kim - Khôi", 10162451: "Hoàng Kim - Ngoa", 10162452: "Hoàng Kim - Thủ",
    10162453: "Hoàng Kim - Giáp", 10162454: "Hoàng Kim - Kiên", 10162455: "Hoàng Kim - Liên",
    10162456: "Hoàng Kim - Đái", 10162457: "Hoàng Kim - Giới", 10162458: "Hoàng Kim - Ngọc",
    10162459: "Hoàng Kim - Uyển",
}
MA_DO_CU = {10100000, 10141030, 10141040} | set(range(10162420, 10162430))
GIAY_MOT_NHAN_VAT = 30 * 60
GIAY_CHO_SHOP_DOI = 8
GIAY_CHO_CODE = 6

MA_TUI_TEN = ('local s = "" for i = 0, 99 do local a = PlayerPackage:EnumItem("base", i) '
              'if a and a:GetID() ~= 0 then s = s .. i .. "\\t" .. a:GetDefineID() .. "\\t" .. a:GetName() .. "\\n" '
              'end end return s')
MA_TRANG_BI = ('local s = "" for i = 0, 23 do local a = EnumAction(i, "equip") '
               'if a and a:GetID() ~= 0 then s = s .. i .. "\\t" .. a:GetDefineID() .. "\\t" .. a:GetName() .. "\\n" '
               'end end return s')
MA_NOI_LUC = 'return tostring(Player:GetData("SPR"))'
MA_MO_TUI_XEP = ('if not IsWindowShow("Packet") then OpenWindow("Packet") end')
MA_XEP_TUI = trong_cua_so("Packet", "Packet_PackUp_Clicked()")
MA_THAO = trong_cua_so("OtherInfo", 'local a = EnumAction({o}, "equip") if not a or a:GetID() == 0 then return "0" end '
                                    '{nut}:SetActionItem(a:GetID()) {nut}:DoSubAction() return "1"')

_khoa = threading.Lock()


def doc(duong_dan=None):
    """{tên chuẩn hóa: {"ten", "luc"[, "xong", "buoc"]}}; file chưa có / hỏng thì rỗng."""
    duong_dan = duong_dan or DUONG_DAN
    try:
        with open(duong_dan, encoding="utf-8") as f:
            du_lieu = json.load(f)
    except (OSError, ValueError):
        return {}
    return du_lieu if isinstance(du_lieu, dict) else {}


def _ghi(du_lieu, duong_dan):
    tam = f"{duong_dan}.{os.getpid()}.{threading.get_ident()}.tmp"
    with open(tam, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=1)
    os.replace(tam, duong_dan)


def da_lam(ten, duong_dan=None):
    muc = doc(duong_dan).get(chuan_hoa(ten)) if ten else None
    return isinstance(muc, dict) and muc.get("xong", True) is not False


def cac_buoc_da_xong(ten, duong_dan=None):
    muc = doc(duong_dan).get(chuan_hoa(ten))
    return set(muc.get("buoc", [])) if isinstance(muc, dict) else set()


def danh_dau_buoc(ten, buoc, duong_dan=None):
    """Ghi bước buoc (1..6) của nhân vật đang nâng cấp dở đã xong."""
    duong_dan = duong_dan or DUONG_DAN
    with _khoa:
        du_lieu = doc(duong_dan)
        muc = du_lieu.get(chuan_hoa(ten))
        if not isinstance(muc, dict) or muc.get("xong", True) is not False:
            muc = {"ten": ten, "xong": False, "buoc": []}
        muc["buoc"] = sorted(set(muc.get("buoc", [])) | {buoc})
        muc["luc"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        du_lieu[chuan_hoa(ten)] = muc
        _ghi(du_lieu, duong_dan)


def danh_dau_da_lam(ten, luc=None, duong_dan=None):
    """Ghi nhân vật đã nâng cấp xong (ghi đè lúc làm nếu đã có)."""
    duong_dan = duong_dan or DUONG_DAN
    luc = luc or datetime.now()
    with _khoa:
        du_lieu = doc(duong_dan)
        du_lieu[chuan_hoa(ten)] = {"ten": ten, "luc": luc.strftime("%Y-%m-%d %H:%M:%S")}
        _ghi(du_lieu, duong_dan)


def bo_danh_dau(ten, duong_dan=None):
    """Xóa nhân vật khỏi danh sách (để làm lại). True nếu có xóa."""
    duong_dan = duong_dan or DUONG_DAN
    with _khoa:
        du_lieu = doc(duong_dan)
        if du_lieu.pop(chuan_hoa(ten), None) is None:
            return False
        _ghi(du_lieu, duong_dan)
        return True


def doc_bang(chu):
    """{ô: (mã, tên)} từ chuỗi "ô\\tmã\\ttên" mỗi dòng (bytes)."""
    bang = {}
    for dong in chu.split(b"\n"):
        phan = dong.split(b"\t", 2)
        if len(phan) == 3:
            bang[int(phan[0])] = (int(float(phan[1])), giai_ma(phan[2]))
    return bang


def can_thay_bach_bao(tui, trang_bi):
    """[(ô trang bị, nút, mã 9 sao, tên)] cần thay: túi có bộ 9 sao mà ô đó chưa mang bộ 9 sao."""
    co = {ma for ma, _ in tui.values()}
    return [(o, nut, ma_9, ten) for o, nut, _, ma_9, ten in BACH_BAO
            if ma_9 in co and trang_bi.get(o, (0, ""))[0] != ma_9]


def hoang_kim_can_mang(tui, trang_bi):
    """{mã: tên} các món Hoàng Kim trong túi mà chưa mang món cùng mã."""
    da_mang = {ma for ma, _ in trang_bi.values()}
    return {ma: ten for ma, _ in tui.values() if ma in MA_HOANG_KIM and ma not in da_mang
            for ten in (MA_HOANG_KIM[ma],)}


def mon_dau_tien(ds_mon):
    """(số ô, tên) món đầu của trang shop đang hiện nếu đã có giá Điểm Tặng, chưa thì None."""
    if 1 not in ds_mon:
        return None
    ten, gia = ds_mon[1]
    return (1, ten) if ten and "diem tang" in bo_dau(gia) else None


def can_cong_noi_luc(noi_luc, diem, diem_moi_lan):
    """Bước 6: cộng 10.000.000 Nội Lực khi nội lực chưa max và còn đủ điểm."""
    return noi_luc < NOI_LUC_TOI_DA and diem >= diem_moi_lan


def tao_nang_cap(game, ten, in_log, nen_dung, bao_trang_thai, duong_dan=None):
    """NangCapNhanVat (lớp con NhanDoTanThu, import muộn vì nhan_vat_moi cũng import module này)."""
    from nhan_vat_moi import NhanDoTanThu, NPC_CONG_POINT, DONG_CONG_10_TRIEU, DONG_NOI_LUC, DIEM_MOI_LAN_CONG
    from pho_ban_pmp import GIAY_CHO_GAME_TRA_LOI, GIAY_CHO_LAG, MAP_DAI_LY, SO_LAN_THU_MANG, LoiPhoBan, la_dai_ly
    from tu_dung_vat_pham import LoiVatPham, TiemKNB
    from vut_rac import LoiVutRac, vut_theo_ma

    class NangCapNhanVat(NhanDoTanThu):
        def __init__(self):
            super().__init__(game, ten, in_log, nen_dung, bao_trang_thai)
            self.het_han_vong = time.time() + GIAY_MOT_NHAN_VAT
            self.duong_dan = duong_dan

        def _tui_ten(self):
            return doc_bang(self.game.lua.chay(MA_TUI_TEN))

        def _trang_bi(self):
            return doc_bang(self.game.lua.chay(MA_TRANG_BI))

        def _noi_luc(self):
            return int(float(self.game.lua.chay(MA_NOI_LUC)))

        def chay(self):
            if self._tt() is None:
                raise LoiPhoBan("chưa vào game")
            xong = cac_buoc_da_xong(self.ten, self.duong_dan)
            self.in_log(f"{self.ten}: bắt đầu nâng cấp nhân vật"
                        + (f" (đã xong bước {', '.join(map(str, sorted(xong)))})" if xong else ""))
            self._ve_dai_ly_truoc()
            for so, buoc in enumerate((self.buoc_1, self.buoc_2, self.buoc_3, self.buoc_4, self.buoc_5,
                                       self.buoc_6), 1):
                if so in xong:
                    continue
                self._kiem_tra()
                buoc()
                danh_dau_buoc(self.ten, so, self.duong_dan)
            danh_dau_da_lam(self.ten, duong_dan=self.duong_dan)
            self.in_log(f"{self.ten}: đã nâng cấp xong nhân vật")

        # 0. NPC GIFTCODE / Cộng Point và các bước đều ở Đại Lý.
        def _ve_dai_ly_truoc(self):
            m = self._map()
            if la_dai_ly(m):
                return
            self._kiem_tra()
            self.in_log(f"{self.ten}: đang ở [{m}], về {MAP_DAI_LY} trước khi nâng cấp")
            self._mo_ta(f"về {MAP_DAI_LY}")
            self._ve_thanh()

        # 1. Xếp túi, thay Bách Bảo Nang / Rương 9 sao.
        def buoc_1(self):
            self._mo_ta("xếp túi")
            self.game.lua.chay(MA_MO_TUI_XEP)
            time.sleep(0.5)
            self.game.lua.chay(MA_XEP_TUI)
            time.sleep(1)
            can = can_thay_bach_bao(self._tui_ten(), self._trang_bi())
            if not can:
                self.in_log(f"{self.ten}: túi không có Bách Bảo Nang / Rương 9 sao cần mang, bỏ qua bước 1")
                return
            for _ in range(SO_LAN_THU_MANG):
                for o, nut, ma_9, ten_mon in can:
                    self._kiem_tra()
                    cu = self._trang_bi().get(o)
                    if cu:
                        self._mo_ta(f"tháo {cu[1]}")
                        self.game.lua.chay(MA_THAO.replace("{o}", str(o)).replace("{nut}", nut))
                        if self._cho(lambda: self._trang_bi().get(o) != cu, GIAY_CHO_GAME_TRA_LOI + GIAY_CHO_LAG):
                            self.in_log(f"{self.ten}: đã tháo {cu[1]}")
                        else:
                            self.in_log(f"{self.ten}: tháo {cu[1]} không được, thử mang thẳng {ten_mon} 9 sao")
                    self._mang({ma_9: f"{ten_mon} 9 sao"})
                can = can_thay_bach_bao(self._tui_ten(), self._trang_bi())
                if not can:
                    self.in_log(f"{self.ten}: đã mang Bách Bảo Nang / Rương 9 sao")
                    return
            raise LoiPhoBan(f"chưa mang được {', '.join(f'{t} 9 sao' for *_, t in can)}")

        # 2. Mua Thần Khí Tân Thủ + trứng Nga Mi Biến Dị, mang thần khí, dùng trứng.
        def _mua_mon(self, tiem, tiem_ten, nhom, ten_can=None, da_co=lambda ten_mon: False):
            """
            Mua món đầu (hoặc món ten_can) của tiệm / nhóm. Trả về tên món; túi đã có hoặc da_co(tên) thì không mua.
            """
            self._kiem_tra()
            tiem.chon(TIEM_LAM_MOI)
            tiem.chon(tiem_ten, nhom)

            def mon():
                ds = tiem.doc()["mon"]
                if ten_can:
                    o = next((o for o, (t, gia) in ds.items()
                              if chuan_hoa(t) == chuan_hoa(ten_can) and "diem tang" in bo_dau(gia)), None)
                    return (o, ds[o][0]) if o else None
                return mon_dau_tien(ds)
            tim = self._cho(mon, GIAY_CHO_SHOP_DOI + GIAY_CHO_LAG)
            if not tim:
                raise LoiVatPham(f"{tiem_ten} -> {nhom}: danh sách món chưa hiện ({tiem.doc()['mon']})")
            o, ten_mon = tim

            def trong_tui():
                return any(chuan_hoa(t) == chuan_hoa(ten_mon) for _, t in self._tui_ten().values())
            if da_co(ten_mon) or trong_tui():
                return ten_mon
            self._mo_ta(f"mua {ten_mon}")
            tiem.bam_mua(o)
            if not self._cho(trong_tui, GIAY_CHO_GAME_TRA_LOI + GIAY_CHO_LAG):
                raise LoiVatPham(f"bấm mua {ten_mon} mà túi không có (hết Điểm Tặng?)")
            self.in_log(f"{self.ten}: đã mua {ten_mon}")
            return ten_mon

        def buoc_2(self):
            tiem = TiemKNB(self.game.lua)
            ten_vu_khi = None
            try:
                vu_khi = self._trang_bi().get(O_VU_KHI, (0, ""))[1]
                ten_vu_khi = self._mua_mon(tiem, *TIEM_THAN_KHI,
                                           da_co=lambda ten_mon: chuan_hoa(ten_mon) == chuan_hoa(vu_khi))
                if chuan_hoa(vu_khi) == chuan_hoa(ten_vu_khi):
                    self.in_log(f"{self.ten}: đã mang {ten_vu_khi}")
                    ten_vu_khi = None
                self._mua_mon(tiem, TIEM_TRUNG[0], TIEM_TRUNG[1], TIEM_TRUNG[2])
            except LoiVatPham as loi:
                raise LoiPhoBan(f"mua thần khí / trứng trân thú: {loi}")
            finally:
                tiem.dong()
            if ten_vu_khi:
                ma = next((ma for ma, t in self._tui_ten().values() if chuan_hoa(t) == chuan_hoa(ten_vu_khi)), None)
                if ma and self._mang({ma: ten_vu_khi}):
                    raise LoiPhoBan(f"chưa mang được {ten_vu_khi}")

            def so_trung():
                return sum(1 for _, t in self._tui_ten().values() if chuan_hoa(t) == chuan_hoa(TIEM_TRUNG[2]))
            for lan in range(1, SO_LAN_THU_MANG + 1):
                self._kiem_tra()
                o = next((o for o, (_, t) in sorted(self._tui_ten().items())
                          if chuan_hoa(t) == chuan_hoa(TIEM_TRUNG[2])), None)
                if o is None:
                    return
                con = so_trung()
                self._mo_ta(f"dùng {TIEM_TRUNG[2]}" + (f" (lần {lan})" if lan > 1 else ""))
                self._chuot_phai(o)
                if self._cho(lambda: so_trung() < con, GIAY_CHO_GAME_TRA_LOI + GIAY_CHO_LAG):
                    self.in_log(f"{self.ten}: đã dùng {TIEM_TRUNG[2]}")
                    return
                self.in_log(f"{self.ten}: dùng {TIEM_TRUNG[2]} chưa được (lần {lan}/{SO_LAN_THU_MANG})")
            self.in_log(f"{self.ten}: dùng {TIEM_TRUNG[2]} không được (đủ trân thú rồi?)")

        # 3. Nhập 4 giftcode ở NPC GIFTCODE.
        def buoc_3(self):
            ten_npc, xy = NPC_GIFTCODE
            for code in GIFTCODE:
                for lan in range(1, SO_LAN_THU_MANG + 1):
                    if self._nhap_code(ten_npc, xy, code, lan):
                        break
                else:
                    self.in_log(f"{self.ten}: giftcode {code} nhập {SO_LAN_THU_MANG} lần game không trả lời, bỏ qua")
            self.game.lua.chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')

        def _nhap_code(self, ten_npc, xy, code, lan):
            """Một lần nhập code. True nếu game đã trả lời (túi đổi hoặc có thông báo), False thì nhập lại."""
            self._kiem_tra()
            self._mo_ta(f"nhập giftcode {code}" + (f" (lần {lan})" if lan > 1 else ""))
            self._mo_hoi_thoai(ten_npc, xy, DONG_NHAP_CODE, dan_doi=False)
            self._chon(DONG_NHAP_CODE)
            if not self._cho(lambda: dang_hien(self.game.lua, "NewbieCardActivation"),
                             GIAY_CHO_GAME_TRA_LOI + GIAY_CHO_LAG):
                self.in_log(f"{self.ten}: chọn \"Nhập Mã GiftCode\" mà chưa hiện ô nhập code "
                            f"({self._chu_hoi_thoai()}), thử lại")
                self.game.lua.chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
                return False
            tui = self._tui_ten()
            self._doc_thong_bao()
            bao = []

            def tra_loi():
                bao.extend(self._doc_thong_bao())
                return self._tui_ten() != tui or bao
            self.game.lua.chay(trong_cua_so("NewbieCardActivation",
                                            f"NewUserCard({chuoi_lua(code)}, 0) NewUserCard_Close()"))
            co = self._cho(tra_loi, GIAY_CHO_CODE + GIAY_CHO_LAG)
            if co and bao and self._tui_ten() == tui:
                self._cho(lambda: self._tui_ten() != tui, GIAY_CHO_GAME_TRA_LOI)
            self.game.lua.chay('if IsWindowShow("NewbieCardActivation") then '
                               'CloseWindow("NewbieCardActivation", true) end')
            if self._tui_ten() != tui:
                self.in_log(f"{self.ten}: đã nhập giftcode {code}")
                return True
            if bao:
                self.in_log(f"{self.ten}: giftcode {code} không nhận thêm gì ({' / '.join(bao[-2:])})")
                return True
            self.in_log(f"{self.ten}: giftcode {code} chưa thấy game trả lời (lần {lan}/{SO_LAN_THU_MANG})")
            return False

        # 4. Mang Hoàng Kim, vứt đồ cũ, dùng Hộp Point.
        def buoc_4(self):
            for _ in range(SO_LAN_THU_MANG):
                can = hoang_kim_can_mang(self._tui_ten(), self._trang_bi())
                if not can:
                    break
                self._mang(can)
            can = hoang_kim_can_mang(self._tui_ten(), self._trang_bi())
            if can:
                raise LoiPhoBan(f"chưa mang được {', '.join(can.values())}")
            for _ in range(SO_LAN_THU_MANG):
                if not any(ma in MA_DO_CU for ma, _ in self._tui_ten().values()):
                    break
                self._mo_ta("vứt đồ cũ")
                try:
                    vut_theo_ma(self.game.lua, self.ten, MA_DO_CU, self.in_log, self.nen_dung)
                except LoiVutRac as loi:
                    self.in_log(f"{self.ten}: không vứt được đồ cũ: {loi}")
                    break
                self._cho(lambda: not any(ma in MA_DO_CU for ma, _ in self._tui_ten().values()), GIAY_CHO_LAG)
            con = [t for ma, t in self._tui_ten().values() if ma in MA_DO_CU]
            if con:
                self.in_log(f"{self.ten}: còn đồ cũ chưa vứt được: {', '.join(con)}")
            self._dung_hop_point()

        # 5. Rút 10.000.000 điểm Nội Lực, 2 lần.
        def buoc_5(self):
            da_rut = that_bai = 0
            while da_rut < SO_LAN_RUT_NOI_LUC and that_bai < SO_LAN_THU_CONG:
                self._kiem_tra()
                lan = da_rut + 1
                diem = self.game.diem_tiem_nang()
                self._mo_ta(f"rút 10.000.000 điểm Nội Lực (lần {lan})")
                self._noi_chuyen(NPC_CONG_POINT, (DONG_RUT_10_TRIEU, DONG_RUT_NOI_LUC))
                if self._cho(lambda: self.game.diem_tiem_nang() > diem, GIAY_CHO_GAME_TRA_LOI * 2 + GIAY_CHO_LAG):
                    da_rut += 1
                    self.in_log(f"{self.ten}: đã rút Nội Lực lần {lan}, điểm tiềm năng {diem} -> "
                                f"{self.game.diem_tiem_nang()}")
                else:
                    that_bai += 1
                    self.in_log(f"{self.ten}: rút Nội Lực lần {lan} chưa thấy cộng điểm "
                                f"({that_bai}/{SO_LAN_THU_CONG}) ({self._chu_hoi_thoai()})")
            if da_rut < SO_LAN_RUT_NOI_LUC:
                self.in_log(f"{self.ten}: chỉ rút được Nội Lực {da_rut}/{SO_LAN_RUT_NOI_LUC} lần")

        # 6. Cộng 10.000.000 Nội Lực (chưa max), còn lại vào Thân Pháp.
        def _cong_npc(self, dong_thuoc_tinh, ten_thuoc_tinh):
            for lan in range(1, SO_LAN_THU_CONG + 1):
                diem = self.game.diem_tiem_nang()
                self._mo_ta(f"cộng 10.000.000 {ten_thuoc_tinh}")
                self._noi_chuyen(NPC_CONG_POINT, (DONG_CONG_10_TRIEU, dong_thuoc_tinh))
                if self._cho(lambda: self.game.diem_tiem_nang() <= diem - DIEM_MOI_LAN_CONG,
                             GIAY_CHO_GAME_TRA_LOI * 2 + GIAY_CHO_LAG):
                    self.in_log(f"{self.ten}: đã cộng 10.000.000 {ten_thuoc_tinh}, còn "
                                f"{self.game.diem_tiem_nang()} điểm")
                    return True
                self.in_log(f"{self.ten}: cộng {ten_thuoc_tinh} lần {lan} chưa thấy trừ điểm "
                            f"({self._chu_hoi_thoai()})")
            return False

        def buoc_6(self):
            noi_luc = self._noi_luc()
            if noi_luc >= NOI_LUC_TOI_DA:
                self.in_log(f"{self.ten}: Nội lực đã max ({noi_luc}), cộng hết điểm vào Thân Pháp")
            elif can_cong_noi_luc(noi_luc, self.game.diem_tiem_nang(), DIEM_MOI_LAN_CONG):
                if self._cong_npc(DONG_NOI_LUC, "Nội Lực"):
                    self.in_log(f"{self.ten}: Nội lực {noi_luc} -> {self._noi_luc()}")
                else:
                    self.in_log(f"{self.ten}: cộng Nội Lực {SO_LAN_THU_CONG} lần không được, cộng tiếp Thân Pháp")
            while self.game.diem_tiem_nang() >= DIEM_MOI_LAN_CONG:
                if not self._cong_npc(DONG_CONG_THAN_PHAP, "Thân Pháp"):
                    raise LoiPhoBan(f"cộng Thân Pháp {SO_LAN_THU_CONG} lần không được")
            self.game.lua.chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
            for lan in range(1, SO_LAN_THU_CONG + 1):
                le = self.game.diem_tiem_nang()
                if le <= 0:
                    return
                self.game.cong_diem_tiem_nang({"dex": le})
                if self._cho(lambda: self.game.diem_tiem_nang() < le, GIAY_CHO_GAME_TRA_LOI + GIAY_CHO_LAG):
                    self.in_log(f"{self.ten}: đã cộng {le} điểm lẻ vào Thân Pháp")
                    return
                self.in_log(f"{self.ten}: cộng {le} điểm lẻ vào Thân Pháp chưa được (lần {lan}/{SO_LAN_THU_CONG})")

    return NangCapNhanVat()


def nang_cap(game, ten, in_log, nen_dung=lambda: False, bao_trang_thai=lambda chu: None, duong_dan=None):
    """Nâng cấp nhân vật đang trong game nếu chưa có trong file. True nếu đã làm (hoặc đã xong từ trước)."""
    if da_lam(ten, duong_dan):
        return True
    tao_nang_cap(game, ten, in_log, nen_dung, bao_trang_thai, duong_dan).chay()
    return True


class LuongNangCapOnline(threading.Thread):
    """Nút "Test nâng cấp NV": mỗi nhân vật đang trong game (chưa có trong file) một luồng, chạy song song."""

    def __init__(self, hang_doi):
        super().__init__(daemon=True)
        self.hang_doi = hang_doi
        self.dung = threading.Event()
        self.ket_qua = {}

    def in_log(self, chu):
        self.hang_doi.put(("log", f"[Nâng cấp NV] {chu}"))

    def bao_trang_thai(self, chu):
        self.hang_doi.put(("trang_thai_nang_cap", chu))

    def _mot_nhan_vat(self, game, ten):
        try:
            nang_cap(game, ten, self.in_log, self.dung.is_set, self.bao_trang_thai)
            self.ket_qua[ten] = "xong"
        except Exception as loi:
            if self.dung.is_set():
                self.ket_qua[ten] = "đã dừng"
                return
            self.ket_qua[ten] = "lỗi"
            chi_tiet = str(loi) or type(loi).__name__
            self.in_log(f"{ten}: lỗi: {chi_tiet}"
                        + ("" if type(loi).__name__ in ("LoiPhoBan", "LoiVatPham") else f"\n{traceback.format_exc()}"))

    def run(self):
        from cua_so_game import tim_cua_so_game
        from game_api import Game
        from lua_game import LoiLua
        cac_luong = []
        for cua_so in tim_cua_so_game():
            try:
                game = Game(cua_so["hwnd"])
                tt = game.thong_tin()
            except (LoiLua, OSError):
                continue
            if not tt or not tt["ten"]:
                continue
            if da_lam(tt["ten"]):
                self.in_log(f"{tt['ten']}: đã nâng cấp từ trước, bỏ qua")
                continue
            luong = threading.Thread(target=self._mot_nhan_vat, args=(game, tt["ten"]), daemon=True)
            cac_luong.append(luong)
            luong.start()
        if not cac_luong:
            self.in_log("Không có nhân vật online nào cần nâng cấp")
        for luong in cac_luong:
            luong.join()
        tom_tat = ", ".join(f"{ten}: {kq}" for ten, kq in self.ket_qua.items())
        self.in_log(("Đã dừng" if self.dung.is_set() else "Xong") + (f". {tom_tat}" if tom_tat else ""))
        self.bao_trang_thai("Đã dừng" if self.dung.is_set() else "Xong")
