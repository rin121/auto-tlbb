"""Gộp đồ song song xoay vòng khi nhóm ≤ 4 người."""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gop_acc_chinh as gop  # noqa: E402
import xoay_vong as xv  # noqa: E402


class TestCoTheGopSongSong(unittest.TestCase):
    def test_nhom_4_cho_phep(self):
        self.assertTrue(xv.co_the_gop_song_song_xv(4))
        self.assertTrue(xv.co_the_gop_song_song_xv(1))

    def test_nhom_5_6_chan(self):
        self.assertFalse(xv.co_the_gop_song_song_xv(5))
        self.assertFalse(xv.co_the_gop_song_song_xv(6))

    def test_hang_so(self):
        self.assertEqual(xv.SO_NGUOI_CHO_PHEP_GOP_SONG_SONG, 4)


class TestHwndGiuCheo(unittest.TestCase):
    def test_hwnd_cua_nhom_xoay_vong_tu_cac_hwnd(self):
        luong = MagicMock()
        luong.is_alive.return_value = True
        luong.cac_hwnd = [1, 2, 3, 4]
        luong.thanh_vien_dang_pb = None
        luong.pid_dieu_khien = set()
        luong.cac_luong_con = []
        with patch.object(xv, "_luong_xv_hien_tai", luong), \
                patch.object(xv, "tim_cua_so_game", return_value=[]):
            self.assertEqual(xv.hwnd_cua_nhom_xoay_vong(), {1, 2, 3, 4})

    def test_hwnd_giu_khi_gop_theo_cau_hinh(self):
        with patch.object(gop, "cai_dat", return_value={
                "tai_khoan": "kduy121", "danh_sach": "bong1, 123, ThỏA\nbong2, 123, ThỏB"}), \
                patch.object(gop, "luong_gop_dang_chay", return_value=None), \
                patch("xoay_vong.tim_hwnd_cua_tai_khoan",
                      side_effect=lambda tk: {"kduy121": 50, "bong1": 51}.get(tk.lower())):
            giu = gop.hwnd_giu_khi_gop()
        self.assertEqual(giu, {50, 51})

    def test_hwnd_giu_xoay_vong_gom_gop(self):
        with patch("giao_acc_chinh.cai_dat", return_value={"tai_khoan": ""}), \
                patch.object(xv.cau_hinh, "tai_khoan_train", return_value=[]), \
                patch.object(gop, "hwnd_giu_khi_gop", return_value={77, 88}):
            giu = xv.hwnd_giu_khi_xoay_vong()
        self.assertIn(77, giu)
        self.assertIn(88, giu)


if __name__ == "__main__":
    unittest.main()
