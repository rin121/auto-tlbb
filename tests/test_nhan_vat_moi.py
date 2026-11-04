import unittest
from unittest.mock import MagicMock, patch

from dang_nhap import LoiDangNhap, LoiSaiRuleNhanVat
from nhan_vat_moi import (DONG_TIEU_DAO, MON_PHAI_TIEU_DAO, LuongTaoNhanVat, NhanDoTanThu,
                          la_loi_ten_da_ton_tai)


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

    def test_vao_tieu_dao_khong_bo_qua_phai_khac(self):
        nc = NhanDoTanThu.__new__(NhanDoTanThu)
        nc.ten = "testnv"
        nc.in_log = lambda _: None
        nc._cho = lambda *a, **k: True
        nc._chu_hoi_thoai = lambda: ""
        goi = []
        nc._noi_chuyen = lambda *a: goi.append(a)
        nc._vao_tieu_dao({"mon_phai": 3})
        self.assertEqual(len(goi), 1)
        goi.clear()
        nc._vao_tieu_dao({"mon_phai": MON_PHAI_TIEU_DAO})
        self.assertEqual(len(goi), 0)


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
