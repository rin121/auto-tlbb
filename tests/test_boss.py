"""Lịch boss 4 giờ/lần và chọn dòng NPC Di Chuyển."""
import unittest
from datetime import datetime

import boss


def _dong(chu, s=1, e=2):
    return ("id", s, e, chu)


class TestLichBoss(unittest.TestCase):
    def test_truoc_3_phut_moi_vao_cua_so(self):
        self.assertIsNone(boss.khung_boss(datetime(2026, 11, 18, 3, 56)))
        moc, bat, ket = boss.khung_boss(datetime(2026, 11, 18, 3, 57))
        self.assertEqual(moc, datetime(2026, 11, 18, 4, 0))
        self.assertEqual(bat, datetime(2026, 11, 18, 3, 57))
        self.assertEqual(ket, datetime(2026, 11, 18, 4, 5))

    def test_phut_5_thi_roi(self):
        self.assertIsNotNone(boss.khung_boss(datetime(2026, 11, 18, 4, 4, 59)))
        self.assertIsNone(boss.khung_boss(datetime(2026, 11, 18, 4, 5)))
        moc = datetime(2026, 11, 18, 4, 0)
        self.assertFalse(boss.den_luc_roi_boss(datetime(2026, 11, 18, 4, 4), moc))
        self.assertTrue(boss.den_luc_roi_boss(datetime(2026, 11, 18, 4, 5), moc))

    def test_nua_dem_thuoc_moc_0h(self):
        moc, _, ket = boss.khung_boss(datetime(2026, 11, 18, 23, 57))
        self.assertEqual(moc, datetime(2026, 11, 19, 0, 0))
        self.assertEqual(ket, datetime(2026, 11, 19, 0, 5))
        self.assertEqual(boss.khung_boss(datetime(2026, 11, 19, 0, 4))[0], datetime(2026, 11, 19, 0, 0))

    def test_moi_moc_mot_lan_va_phai_bat(self):
        bay = datetime(2026, 11, 18, 4, 1)
        khoa = boss.khoa_moc_boss(datetime(2026, 11, 18, 4, 0))
        self.assertTrue(boss.nen_di_boss(bay, "", True))
        self.assertFalse(boss.nen_di_boss(bay, khoa, True))
        self.assertFalse(boss.nen_di_boss(bay, "", False))
        self.assertFalse(boss.nen_di_boss(datetime(2026, 11, 18, 5, 0), "", True))

    def test_nut_test_chi_khi_dang_di_pho_ban(self):
        from unittest.mock import MagicMock
        import xoay_vong as xv
        luong = xv.LuongXoayVong(MagicMock(), 1, False, True)
        self.assertFalse(luong.test_boss())
        luong.is_alive = lambda: True
        self.assertFalse(luong.test_boss())
        luong.thanh_vien_dang_pb = [object()]
        self.assertTrue(luong.test_boss())
        self.assertTrue(luong.yeu_cau_test_boss.is_set())


class TestHoiThoaiBoss(unittest.TestCase):
    def test_chon_menu_roi_map(self):
        menu = [_dong("Tân Thủ 1", 1, 1), _dong("Bản Đồ BOOS VIP", 9, 3), _dong("Bản Đồ Phụ Bản", 4, 4)]
        self.assertEqual(boss.dong_menu_boss(menu), (9, 3))
        con = [_dong("#HNgân Nga Tuyết Nguyên", 9, 8), _dong("#HYến Vương Cổ Mộ Tầng 9", 9, 9),
               _dong("#{loulan_yizhan_20080329}", 1, 1)]
        self.assertEqual(boss.dong_map_boss(con, "Ngân Ngai Tuyết Nguyên"), (9, 8))
        self.assertEqual(boss.dong_map_boss(con, "Yến Vương Cổ Mộ"), (9, 9))
        self.assertTrue(boss.cung_ten_map("Ngân Nga Tuyết Nguyên", "Ngân Ngai Tuyết Nguyên"))
        self.assertTrue(boss.cung_ten_map("Yến Vương Cổ Mộ Tầng 9", "Yến Vương Cổ Mộ"))

    def test_boss_chet_khi_thong_bao_hoac_mau_0(self):
        ten = "Ngân Ngai Tuyết Nguyên"
        self.assertTrue(boss.thong_bao_boss_chet(["Ngân Ngai đã bị tiêu diệt"], ten))
        self.assertFalse(boss.thong_bao_boss_chet(["ai đó đã chết"], ten))
        self.assertEqual(boss.boss_bien_mat(False, [("Ngân Ngai Vương", 0)], ten), (True, True))
        self.assertEqual(boss.boss_bien_mat(True, [], ten), (False, True))
        self.assertEqual(boss.boss_bien_mat(False, [("Ngân Ngai Vương", 100)], ten), (False, True))


if __name__ == "__main__":
    unittest.main()
