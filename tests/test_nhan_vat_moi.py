import unittest
from unittest.mock import MagicMock, patch

from dang_nhap import LoiDangNhap, LoiSaiRuleNhanVat
import nang_cap_nhan_vat as ncnv
from nhan_vat_moi import (CHUA_VAO_PHAI, DONG_TIEU_DAO, MA_TRANG_BI_TAN_THU, MA_TUI_BACH_BAO,
                          MON_PHAI_TIEU_DAO, LuongTaoNhanVat, NhanDoTanThu, buoc_truoc_pho_ban_xong,
                          da_gia_nhap_phai, la_loi_ten_da_ton_tai, san_sang_di_pho_ban)
from pho_ban_pmp import LoiPhoBan

MA_KHOI_HOANG_KIM = next(iter(ncnv.MA_HOANG_KIM))  # Hoàng Kim - Khôi
MA_KHOI_TAN_THU = 10162420


def _lua_mac(ma_khoi=MA_KHOI_HOANG_KIM, da_mang=True):
    """Mock lua.chay: mũ đang mang + cờ đã mang."""

    def chay(ma):
        if "GetDefineID" in ma:
            return str(ma_khoi).encode()
        return b"1" if da_mang else b"0"

    return chay


# Thứ tự cứng trong NhanDoTanThu.chay() — không được bỏ / đảo bước.
THU_TU_NHAN_DO_TAN_THU = (
    "vao_tieu_dao",
    "nhan_vang",
    "mang_tui_bach_bao",
    "nhan_trang_bi",
    "mang_trang_bi_tan_thu",
    "dung_hop_point",
    "cong_noi_luc",
    "roi_cong_point",
    "can_khon_ho",
    "thu_cuoi",
    "hoi_mau",
)


class TestNhanVatMoiHoiThoai(unittest.TestCase):
    def test_dong_tieu_dao_theo_ten_hien_thi(self):
        self.assertEqual(DONG_TIEU_DAO, ("Tiêu Dao",))

    def test_dong_hien_theo_chu(self):
        nc = NhanDoTanThu.__new__(NhanDoTanThu)
        ht = ("npc", [
            ("0", 0, 320, "Tinh Túc"),
            ("0", 0, 321, "Tiêu Dao"),
            ("0", 0, 327, "Võ Đang"),
        ])
        nc._hoi_thoai = lambda: ht
        self.assertTrue(nc._dong_hien_trong_hoi_thoai(DONG_TIEU_DAO))
        self.assertFalse(nc._dong_hien_trong_hoi_thoai(("Cái Bang",)))

    def test_da_co_phai_thi_bo_gia_nhap(self):
        self.assertFalse(da_gia_nhap_phai(-1))
        self.assertTrue(da_gia_nhap_phai(3))
        self.assertTrue(da_gia_nhap_phai(MON_PHAI_TIEU_DAO))
        self.assertFalse(da_gia_nhap_phai(9))
        self.assertFalse(da_gia_nhap_phai(None))
        nc = NhanDoTanThu.__new__(NhanDoTanThu)
        nc.ten = "azumi44"
        nc.in_log = lambda _: None
        goi = []
        nc._noi_chuyen = lambda *a: goi.append(a)
        nc._vao_tieu_dao({"mon_phai": 3})
        nc._vao_tieu_dao({"mon_phai": MON_PHAI_TIEU_DAO})
        self.assertEqual(goi, [])
        nc._cho = lambda *a, **k: True
        nc._chu_hoi_thoai = lambda: ""
        nc._vao_tieu_dao({"mon_phai": -1})
        nc._vao_tieu_dao({"mon_phai": 9})
        self.assertEqual(len(goi), 2)

    def test_am_mot_van_nhan_tien(self):
        nc = NhanDoTanThu.__new__(NhanDoTanThu)
        nc.ten = "azumi44"
        log = []
        nc.in_log = log.append
        nc._tt_on_dinh = lambda: {"map": "Đại Lý", "x": 160, "y": 166, "mon_phai": -1}
        nc._tt = lambda: {"map": "Đại Lý", "x": 160, "y": 166, "mon_phai": MON_PHAI_TIEU_DAO}
        goi = []
        nc._vao_tieu_dao = lambda tt: goi.append("vao")
        nc._nhan_vang = lambda: goi.append("vang")
        nc._mang = lambda *_: None
        nc._nhan_trang_bi = lambda: None
        nc._dung_hop_point = lambda: None
        nc._cong_noi_luc = lambda: None
        nc.roi_cong_point = lambda: None
        nc._can_khon_ho = lambda: None
        nc._thu_cuoi = lambda: None
        nc.hoi_mau = lambda: None
        nc.game = MagicMock()
        nc.game.lua.chay.return_value = b"1"
        nc.game.diem_tiem_nang.return_value = 0
        nc._so_luong = lambda *_: 0
        nc.chay()
        self.assertEqual(goi[:2], ["vao", "vang"])
        self.assertFalse(any("bỏ qua nhận đồ" in d for d in log))

    def test_san_sang_khi_da_mac_va_nang_cap(self):
        game = MagicMock()
        game.thong_tin.return_value = {"map": "Đại Lý", "mon_phai": MON_PHAI_TIEU_DAO}
        game.lua.chay.side_effect = _lua_mac(MA_KHOI_HOANG_KIM)
        with patch("nhan_vat_moi.nang_cap_nhan_vat.da_lam", return_value=True), \
                patch("nhan_vat_moi.roi_dia_phu", return_value=True), \
                patch("nhan_vat_moi.NhanDoTanThu") as lop:
            self.assertTrue(buoc_truoc_pho_ban_xong(game, "anhzero11"))
            self.assertTrue(san_sang_di_pho_ban(game, "anhzero11", "anhzero11", lambda *_: None, lambda: False))
            lop.assert_not_called()

    def test_chua_mac_do_thi_chua_cho_di_pho_ban(self):
        game = MagicMock()
        game.thong_tin.return_value = {"map": "Đại Lý", "mon_phai": MON_PHAI_TIEU_DAO}
        game.lua.chay.side_effect = _lua_mac(0, da_mang=False)
        log = []
        with patch("nhan_vat_moi.nang_cap_nhan_vat.da_lam", return_value=False), \
                patch("nhan_vat_moi.roi_dia_phu", return_value=True), \
                patch("nhan_vat_moi.NhanDoTanThu") as lop:
            lop.return_value.chay.side_effect = RuntimeError("chưa mang")
            self.assertFalse(san_sang_di_pho_ban(game, "anhzero111", "anhzero11", log.append, lambda: False))
            lop.return_value.chay.assert_called_once()
        self.assertTrue(any("chưa cho đi phó bản" in d or "chưa xong trước phó bản" in d for d in log))


class TestThuTuNhanDoTanThu(unittest.TestCase):
    """NC-13: nhận đồ tân thủ chạy đúng thứ tự từng bước, không bỏ bước."""

    def _nc(self, mon_phai_dau, mon_phai_cuoi=MON_PHAI_TIEU_DAO):
        nc = NhanDoTanThu.__new__(NhanDoTanThu)
        nc.ten = "anhzero111"
        nc.in_log = lambda *_: None
        nc.game = MagicMock()
        nc.game.lua.chay.return_value = b"1"
        nc.game.diem_tiem_nang.return_value = 0
        nc._tt_on_dinh = lambda: {"map": "Đại Lý", "x": 160, "y": 166, "mon_phai": mon_phai_dau}
        nc._tt = lambda: {"map": "Đại Lý", "x": 160, "y": 166, "mon_phai": mon_phai_cuoi}
        nc._so_luong = lambda *_: 0
        goi = []
        nc._vao_tieu_dao = lambda tt: goi.append("vao_tieu_dao")

        def mang(cac_ma):
            if cac_ma is MA_TUI_BACH_BAO or cac_ma == MA_TUI_BACH_BAO:
                goi.append("mang_tui_bach_bao")
            elif cac_ma is MA_TRANG_BI_TAN_THU or cac_ma == MA_TRANG_BI_TAN_THU:
                goi.append("mang_trang_bi_tan_thu")
            else:
                goi.append(("mang", cac_ma))

        nc._mang = mang
        for ten, khoa in (
            ("_nhan_vang", "nhan_vang"),
            ("_nhan_trang_bi", "nhan_trang_bi"),
            ("_dung_hop_point", "dung_hop_point"),
            ("_cong_noi_luc", "cong_noi_luc"),
            ("roi_cong_point", "roi_cong_point"),
            ("_can_khon_ho", "can_khon_ho"),
            ("_thu_cuoi", "thu_cuoi"),
            ("hoi_mau", "hoi_mau"),
        ):
            setattr(nc, ten, lambda khoa=khoa: goi.append(khoa))
        return nc, goi

    def test_chua_vao_phai_thi_chay_du_thu_tu(self):
        nc, goi = self._nc(CHUA_VAO_PHAI)
        nc.chay()
        self.assertEqual(tuple(goi), THU_TU_NHAN_DO_TAN_THU)

    def test_ma_am_mot_van_chay_du_thu_tu(self):
        nc, goi = self._nc(-1)
        nc.chay()
        self.assertEqual(tuple(goi), THU_TU_NHAN_DO_TAN_THU)

    def test_da_tieu_dao_van_nhan_tien_do_du_thu_tu(self):
        nc, goi = self._nc(MON_PHAI_TIEU_DAO)
        nc.chay()
        self.assertEqual(tuple(goi), THU_TU_NHAN_DO_TAN_THU)

    def test_phai_khac_van_nhan_tien_do_khong_bo_buoc(self):
        """Đã vào phái khác: vẫn nhận tiền / đồ theo đúng thứ tự; checklist cuối báo chưa Tiêu Dao."""
        nc, goi = self._nc(3, mon_phai_cuoi=3)
        with self.assertRaises(LoiPhoBan) as bat:
            nc.chay()
        self.assertIn("chưa vào Tiêu Dao", str(bat.exception))
        self.assertEqual(tuple(goi), THU_TU_NHAN_DO_TAN_THU)

    def test_loi_giua_chung_thi_dung_khong_nhay_buoc_sau(self):
        nc, goi = self._nc(CHUA_VAO_PHAI)

        def loi_trang_bi():
            goi.append("nhan_trang_bi")
            raise LoiPhoBan("chưa nhận được đồ")

        nc._nhan_trang_bi = loi_trang_bi
        with self.assertRaises(LoiPhoBan):
            nc.chay()
        self.assertEqual(goi, [
            "vao_tieu_dao", "nhan_vang", "mang_tui_bach_bao", "nhan_trang_bi",
        ])
        self.assertNotIn("mang_trang_bi_tan_thu", goi)
        self.assertNotIn("dung_hop_point", goi)
        self.assertNotIn("hoi_mau", goi)


class TestThuTuTruocPhoBan(unittest.TestCase):
    """Trước phó bản: nhận đồ tân thủ rồi nâng cấp, pass hết mới True."""

    def test_san_sang_chay_nhan_do_roi_nang_cap(self):
        game = MagicMock()
        game.thong_tin.return_value = {"map": "Đại Lý", "mon_phai": MON_PHAI_TIEU_DAO}
        game.lua.chay.side_effect = _lua_mac(0, da_mang=False)
        goi = []
        da_lam = {"xong": False}

        def chay():
            goi.append("nhan_do")
            game.lua.chay.side_effect = _lua_mac(MA_KHOI_TAN_THU)

        def nang_cap(*_a, **_k):
            goi.append("nang_cap")
            da_lam["xong"] = True
            game.lua.chay.side_effect = _lua_mac(MA_KHOI_HOANG_KIM)

        with patch("nhan_vat_moi.roi_dia_phu", return_value=True), \
                patch("nhan_vat_moi.nang_cap_nhan_vat.da_lam", side_effect=lambda *_: da_lam["xong"]), \
                patch("nhan_vat_moi.nang_cap_nhan_vat.nang_cap", side_effect=nang_cap), \
                patch("nhan_vat_moi.NhanDoTanThu") as lop, \
                patch("nhan_vat_moi.ghi_da_xong") as ghi:
            lop.return_value.chay.side_effect = chay
            self.assertTrue(san_sang_di_pho_ban(
                game, "anhzero111", "anhzero11", lambda *_: None, lambda: False))
            ghi.assert_called_once_with("anhzero11", "anhzero111")
        self.assertEqual(goi, ["nhan_do", "nang_cap"])

    def test_co_co_nang_cap_nhung_con_mu_tan_thu_thi_lam_lai(self):
        """anhzero111: cờ da_lam sẵn nhưng còn mũ Tân Thủ → xóa cờ, chạy nâng cấp (giftcode, thần khí…)."""
        game = MagicMock()
        game.thong_tin.return_value = {"map": "Đại Lý", "mon_phai": MON_PHAI_TIEU_DAO}
        game.lua.chay.side_effect = _lua_mac(MA_KHOI_TAN_THU)
        goi = []
        log = []
        da_lam = {"xong": True}

        def nang_cap(*_a, **_k):
            goi.append("nang_cap")
            da_lam["xong"] = True
            game.lua.chay.side_effect = _lua_mac(MA_KHOI_HOANG_KIM)

        with patch("nhan_vat_moi.roi_dia_phu", return_value=True), \
                patch("nhan_vat_moi.nang_cap_nhan_vat.da_lam", side_effect=lambda *_: da_lam["xong"]), \
                patch("nhan_vat_moi.nang_cap_nhan_vat.bo_danh_dau",
                      side_effect=lambda *_: da_lam.update(xong=False) or True) as bo, \
                patch("nhan_vat_moi.nang_cap_nhan_vat.nang_cap", side_effect=nang_cap), \
                patch("nhan_vat_moi._thieu_nhan_tien_do", return_value=False), \
                patch("nhan_vat_moi.NhanDoTanThu") as lop:
            self.assertTrue(san_sang_di_pho_ban(
                game, "anhzero111", "anhzero11", log.append, lambda: False))
            lop.assert_not_called()
            bo.assert_called_once_with("anhzero111")
        self.assertEqual(goi, ["nang_cap"])
        self.assertTrue(any("làm lại nâng cấp" in d for d in log))

    def test_chi_nhan_do_chua_nang_cap_thi_chua_di_pho_ban(self):
        game = MagicMock()
        game.thong_tin.return_value = {"map": "Đại Lý", "mon_phai": MON_PHAI_TIEU_DAO}
        game.lua.chay.side_effect = _lua_mac(MA_KHOI_TAN_THU)
        log = []
        with patch("nhan_vat_moi.roi_dia_phu", return_value=True), \
                patch("nhan_vat_moi.nang_cap_nhan_vat.da_lam", return_value=False), \
                patch("nhan_vat_moi.nang_cap_nhan_vat.nang_cap"), \
                patch("nhan_vat_moi._thieu_nhan_tien_do", return_value=False), \
                patch("nhan_vat_moi.NhanDoTanThu") as lop:
            self.assertFalse(san_sang_di_pho_ban(
                game, "anhzero111", "anhzero11", log.append, lambda: False))
            lop.assert_not_called()
        self.assertTrue(any("chưa cho đi phó bản" in d for d in log))


class TestDangKyKhongDuoc(unittest.TestCase):
    def test_khong_co_nhan_vat_thi_logout_roi_login_lai(self):
        luong = LuongTaoNhanVat.__new__(LuongTaoNhanVat)
        luong.da_qua_ma = False
        lenh = []

        def chay(self, ma):
            lenh.append(ma if isinstance(ma, str) else str(ma))
            self.da_bam = True

        lua_moi = type("L", (), {"da_bam": False, "chay": chay})()
        luong.game = type("G", (), {"lua": lua_moi})()
        luong.in_log = lambda *_: None
        luong.bao_trang_thai = lambda *_: None
        thu = []
        luong.toi_chon_nhan_vat = lambda _g: thu.append("login")

        def hien(lua, ten):
            return ten == "LoginCreateRole" and getattr(lua, "da_bam", False)

        dong_ho = {"t": 0.0}

        def bay_gio():
            dong_ho["t"] += 20
            return dong_ho["t"]

        with patch("nhan_vat_moi.dang_hien", side_effect=hien), \
                patch("nhan_vat_moi.ds_nhan_vat", return_value=[]), \
                patch("nhan_vat_moi.time.time", side_effect=bay_gio), \
                patch("nhan_vat_moi.time.sleep"):
            lua = type("L", (), {"chay": lambda self, _m: None})()
            self.assertFalse(luong.mo_man_tao(lua))
        self.assertEqual(thu, ["login"])
        self.assertTrue(any("SelectRole_Return" in m for m in lenh))


class TestTenDaTonTai(unittest.TestCase):
    def test_nhan_loi_ten_da_ton_tai(self):
        self.assertTrue(la_loi_ten_da_ton_tai("Tên nhân vật đã tồn tại"))
        self.assertFalse(la_loi_ten_da_ton_tai("Kiểm tra chưa được duyệt"))

    def test_ten_da_ton_tai_dung_ten_thi_dung_nv_co_san_khong_sai_rule(self):
        luong = LuongTaoNhanVat.__new__(LuongTaoNhanVat)
        luong.tuy_chon = {"dung_ten": True}
        luong.da_qua_ma = False
        luong.in_log = lambda *_: None
        luong.bao_trang_thai = lambda *_: None
        luong.mo_man_tao = lambda _lua: True
        luong.cho_tao_xong = lambda _lua, _ten: "Tên nhân vật đã tồn tại"
        luong.ve_chon_nhan_vat = lambda _lua: None
        lua = MagicMock()
        with patch("nhan_vat_moi.KHOA_TAO"), \
                patch("nhan_vat_moi.ds_nhan_vat", return_value=["cosato32"]), \
                patch("nhan_vat_moi.time.sleep"):
            self.assertEqual(luong.tao_nhan_vat(lua, "cosato32", []), "cosato32")

    def test_ten_da_ton_tai_nhung_ds_trong_thi_loi_dang_nhap_khong_sai_rule(self):
        luong = LuongTaoNhanVat.__new__(LuongTaoNhanVat)
        luong.tuy_chon = {"dung_ten": True}
        luong.da_qua_ma = False
        luong.in_log = lambda *_: None
        luong.bao_trang_thai = lambda *_: None
        luong.mo_man_tao = lambda _lua: True
        luong.cho_tao_xong = lambda _lua, _ten: "Tên nhân vật đã tồn tại"
        luong.ve_chon_nhan_vat = lambda _lua: None
        lua = MagicMock()
        with patch("nhan_vat_moi.KHOA_TAO"), \
                patch("nhan_vat_moi.ds_nhan_vat", return_value=[]), \
                patch("nhan_vat_moi.time.sleep"):
            try:
                luong.tao_nhan_vat(lua, "cosato32", [])
            except LoiSaiRuleNhanVat:
                self.fail("không được coi tên đã tồn tại là sai rule")
            except LoiDangNhap:
                return
            self.fail("cần LoiDangNhap để đăng nhập lại")


if __name__ == "__main__":
    unittest.main()
