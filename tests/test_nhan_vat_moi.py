import unittest

from nhan_vat_moi import DONG_TIEU_DAO, MON_PHAI_TIEU_DAO, NhanDoTanThu


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


if __name__ == "__main__":
    unittest.main()
