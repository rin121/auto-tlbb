"""XV: tài khoản có tên đăng nhập trùng nhân vật round của acc khác (bacmori2 -> bacmori22)."""
import os
import queue
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import xoay_vong as xv  # noqa: E402


class TestTrungTenTaiKhoan(unittest.TestCase):
    def test_bacmori22_trung_nv_bacmori2(self):
        ds = [{"ten_dang_nhap": "bacmori2"}, {"ten_dang_nhap": "bacmori22"}]
        tk_khac, r = xv.tai_khoan_trung_ten_nv_khac(ds[1], ds)
        self.assertEqual(tk_khac, "bacmori2")
        self.assertEqual(r, 1)
        self.assertEqual(xv.ten_round("bacmori2", 1), "bacmori22")
        self.assertEqual(xv.tai_khoan_trung_ten_nv_khac(ds[0], ds), (None, None))

    def test_caychay10_khong_trung_chinh_minh(self):
        ds = [{"ten_dang_nhap": "caychay10"}]
        self.assertEqual(xv.tai_khoan_trung_ten_nv_khac(ds[0], ds), (None, None))

    def test_caychay100_trung_round2_caychay10(self):
        ds = [{"ten_dang_nhap": "caychay10"}, {"ten_dang_nhap": "caychay100"}]
        tk_khac, r = xv.tai_khoan_trung_ten_nv_khac(ds[1], ds)
        self.assertEqual((tk_khac, r), ("caychay10", 1))

    def test_loai_neu_trung_bo_tich_va_them_acc_khac(self):
        ds = [
            {"ten_dang_nhap": "bacmori2", "mat_khau": "x", "bat": True},
            {"ten_dang_nhap": "bacmori22", "mat_khau": "x", "bat": True},
            {"ten_dang_nhap": "bacmori23", "mat_khau": "x", "bat": True},
        ]
        luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, False, False)
        luong.ds_tai_khoan = list(ds)
        luong.tk_sai_rule = set()
        hang = [list(ds), [], []]
        tv_map = {}
        choi = []
        with patch.object(xv, "bo_tich_tai_khoan") as bo_tich, \
                patch.object(xv.cau_hinh, "luu_tai_khoan"):
            luong._them_acc_tu_hang_cho(hang, 0, choi, 2, tv_map)
        self.assertEqual(len(choi), 2)
        self.assertEqual(choi[0].tk, "bacmori2")
        self.assertEqual(choi[1].tk, "bacmori23")
        bo_tich.assert_called_once_with("bacmori22")
        self.assertIn("bacmori22", luong.tk_sai_rule)


class TestTruongNhomCoGame(unittest.TestCase):
    def test_du_nhom_khong_loi_khi_truong_khong_co_game(self):
        luong = xv.LuongXoayVong(queue.Queue(), 1, False, False, False, False)
        truong = xv.ThanhVien({"ten_dang_nhap": "a", "mat_khau": "x"})
        truong.ten, truong.game = "a", None
        self.assertFalse(luong._du_nhom(truong, [truong]))


if __name__ == "__main__":
    unittest.main()
