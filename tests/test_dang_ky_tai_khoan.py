"""Đăng ký tài khoản web: tên 1→n và phân loại thông báo (không gọi mạng thật)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dang_ky_tai_khoan as dk  # noqa: E402


class _Resp:
    def __init__(self, html):
        self.html = html.encode("utf-8")

    def read(self):
        return self.html

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class _Opener:
    def __init__(self, thong_bao):
        self.thong_bao = thong_bao
        self.lan = 0

    def open(self, req, timeout=45):
        self.lan += 1
        if self.lan == 1:
            return _Resp('<input name="csrf" value="tok123">')
        return _Resp(f'<div class="form-message">{self.thong_bao}</div>')


class TestDangKyTaiKhoan(unittest.TestCase):
    def test_danh_sach_tu_den(self):
        self.assertEqual(dk.danh_sach_tai_khoan("sonoko", 1, 3), ["sonoko1", "sonoko2", "sonoko3"])

    def test_phan_loai(self):
        self.assertEqual(dk.phan_loai_thong_bao("Đăng ký thành công"), (True, False, False))
        self.assertEqual(dk.phan_loai_thong_bao("Tài khoản đã được sử dụng"), (False, True, False))
        self.assertTrue(dk.phan_loai_thong_bao("Vui lòng thử lại sau 20 giây")[2])

    def test_dang_ky_thanh_cong(self):
        kq = dk.dang_ky_mot(_Opener("Đăng ký thành công"), "sonoko1", "123123")
        self.assertTrue(kq.ok)
        self.assertEqual(kq.account, "sonoko1")

    def test_dang_ky_da_ton_tai(self):
        kq = dk.dang_ky_mot(_Opener("Tên đã được sử dụng"), "sonoko1", "123123")
        self.assertFalse(kq.ok)
        self.assertTrue(kq.skipped_exists)

    def test_cho_giay_dung_ngay(self):
        self.assertTrue(dk.cho_giay(5, lambda: True))


if __name__ == "__main__":
    unittest.main()
