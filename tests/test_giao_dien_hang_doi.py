import os
import queue
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import giao_dien  # noqa: E402


class TestLamSachHangDoi(unittest.TestCase):
    def test_khong_cat_khi_it_tin(self):
        hd = queue.Queue()
        for i in range(10):
            hd.put(("log", f"m{i}"))
        self.assertEqual(giao_dien._lam_sach_hang_doi(hd), 0)
        self.assertEqual(hd.qsize(), 10)

    def test_gom_cap_nhat_theo_hwnd(self):
        hd = queue.Queue()
        hwnd = 12345
        for i in range(500):
            hd.put(("cap_nhat", hwnd, {"hp": i}))
            hd.put(("log", f"m{i}"))
        # vượt ngưỡng
        while hd.qsize() <= giao_dien.SO_TIN_HANG_DOI_TOI_DA:
            hd.put(("cap_nhat", hwnd, {"hp": 9999}))
        bo = giao_dien._lam_sach_hang_doi(hd)
        self.assertGreater(bo, 0)
        self.assertLessEqual(hd.qsize(), giao_dien.SO_TIN_HANG_DOI_TOI_DA)
        cap = [t for t in list(hd.queue) if t[0] == "cap_nhat"]
        self.assertEqual(len(cap), 1)
        self.assertEqual(cap[0][2]["hp"], 9999)

    def test_giu_mat(self):
        hd = queue.Queue()
        hwnd = 99
        for i in range(giao_dien.SO_TIN_HANG_DOI_TOI_DA + 500):
            hd.put(("xung_quanh", hwnd, ["a"]))
        hd.put(("mat", hwnd))
        giao_dien._lam_sach_hang_doi(hd)
        loai = [t[0] for t in list(hd.queue)]
        self.assertIn("mat", loai)


class TestKhoaCapNhatBang(unittest.TestCase):
    def test_khoa_tt_bang_bo_qua_mo_ta(self):
        tt1 = {"ten": "A", "level": 1, "tai_khoan": "x", "map": "m", "hp": 10, "hp_toi_da": 100,
               "mp": 5, "mp_toi_da": 50, "x": 1, "y": 2, "mo_ta": "old"}
        tt2 = dict(tt1, mo_ta="new")
        self.assertEqual(giao_dien._khoa_tt_bang(tt1), giao_dien._khoa_tt_bang(tt2))

    def test_khoa_xung_quanh_sort(self):
        self.assertEqual(giao_dien._khoa_xung_quanh(["b", "a"]), giao_dien._khoa_xung_quanh(["a", "b"]))


class TestCatNhatKyFile(unittest.TestCase):
    def test_cat_khi_qua_lon(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
            duong = f.name
            f.write(b"x" * (giao_dien.SO_BYTE_NHAT_KY_TOI_DA + 1000))
        try:
            self.assertTrue(giao_dien._cat_nhat_ky_file(duong))
            self.assertLess(os.path.getsize(duong), giao_dien.SO_BYTE_NHAT_KY_TOI_DA + 500_000)
        finally:
            os.remove(duong)

    def test_khong_cat_file_nho(self):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".log") as f:
            duong = f.name
            f.write(b"ok\n")
        try:
            self.assertFalse(giao_dien._cat_nhat_ky_file(duong))
        finally:
            os.remove(duong)


if __name__ == "__main__":
    unittest.main()
