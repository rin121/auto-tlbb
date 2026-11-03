import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gop_acc_chinh as gop  # noqa: E402


class TestParseDanhSach(unittest.TestCase):
    def test_hop_le_phay(self):
        ds = gop.parse_danh_sach("a1, pass1, nv1\na2,pass2,nv2")
        self.assertEqual(len(ds), 2)
        self.assertEqual(ds[0][0]["ten_dang_nhap"], "a1")
        self.assertEqual(ds[0][0]["mat_khau"], "pass1")
        self.assertEqual(ds[0][1], "nv1")

    def test_tab_va_bo_comment(self):
        ds = gop.parse_danh_sach("# ghi chú\n\nacc1\tmk1\tnv1")
        self.assertEqual(len(ds), 1)
        self.assertEqual(ds[0][1], "nv1")

    def test_thieu_cot(self):
        with self.assertRaises(ValueError) as ctx:
            gop.parse_danh_sach("only, two")
        self.assertIn("Dòng 1", str(ctx.exception))

    def test_trong(self):
        with self.assertRaises(ValueError):
            gop.parse_danh_sach("  \n# empty\n")


class TestLuuCaiDat(unittest.TestCase):
    def test_gop_vao_cau_hinh_chung(self):
        from unittest.mock import patch
        with patch("gop_acc_chinh.cau_hinh") as mock_ch:
            mock_ch.chung.return_value = {}
            gop.luu_cai_dat(tai_khoan="acc1", danh_sach="a, b, c")
            mock_ch.dat_chung.assert_called_once()
            luu = mock_ch.dat_chung.call_args[0][0]["gop_acc_chinh"]
            self.assertEqual(luu["tai_khoan"], "acc1")
            self.assertEqual(luu["danh_sach"], "a, b, c")


class TestLuongGopAccChinh(unittest.TestCase):
    def test_cac_tai_khoan(self):
        luong = gop.LuongGopAccChinh.__new__(gop.LuongGopAccChinh)
        luong.tk_chinh = {"ten_dang_nhap": "nhan", "mat_khau": "", "nhan_vat": ""}
        luong.ds_nguon = [({"ten_dang_nhap": "s1", "mat_khau": "x"}, "nv1")]
        luong.tk_da_thoat = {"s2"}
        luong.is_alive = lambda: True
        self.assertEqual(luong.cac_tai_khoan(), {"nhan", "s1", "s2"})
