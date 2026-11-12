"""Model OCR mã kiểm tra: rảnh 30 phút thì giải phóng, lần giải mã sau tự nạp lại."""
import os
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import giai_captcha as gc_  # noqa: E402


class TestGiaiPhongOcr(unittest.TestCase):
    def setUp(self):
        self._cu = (gc_._ocr, gc_._luc_dung_ocr, gc_._so_dang_giai)
        gc_._ocr, gc_._luc_dung_ocr, gc_._so_dang_giai = MagicMock(), 1000.0, 0

    def tearDown(self):
        gc_._ocr, gc_._luc_dung_ocr, gc_._so_dang_giai = self._cu

    def test_chua_du_gio_ranh_thi_giu(self):
        self.assertFalse(gc_.giai_phong_ocr_neu_ranh(bay_gio=1000 + gc_.GIAY_RANH_GIAI_PHONG_OCR - 1))
        self.assertTrue(gc_.ocr_dang_nap())

    def test_ranh_du_lau_thi_giai_phong(self):
        self.assertTrue(gc_.giai_phong_ocr_neu_ranh(bay_gio=1000 + gc_.GIAY_RANH_GIAI_PHONG_OCR))
        self.assertFalse(gc_.ocr_dang_nap())
        self.assertFalse(gc_.giai_phong_ocr_neu_ranh(bay_gio=10 ** 9))

    def test_dang_giai_ma_thi_khong_giai_phong(self):
        gc_._so_dang_giai = 1
        self.assertFalse(gc_.giai_phong_ocr_neu_ranh(bay_gio=10 ** 9))
        self.assertTrue(gc_.ocr_dang_nap())

    def test_win7_tat_tien_trinh_ocr(self):
        con = gc_._OcrSubprocess("python.exe", "giai_ocr.py")
        con._tien_trinh = MagicMock()
        gc_._ocr = con
        self.assertTrue(gc_.giai_phong_ocr_neu_ranh(bay_gio=10 ** 9))
        self.assertIsNone(con._tien_trinh)

    def test_giai_phong_xong_lan_sau_tu_nap_lai(self):
        gc_.giai_phong_ocr_neu_ranh(bay_gio=10 ** 9)
        moi = MagicMock()
        with patch.object(gc_, "_nen_dung_ocr_subprocess", return_value=True), \
                patch.object(gc_, "_lay_ocr_subprocess", return_value=moi) as nap:
            self.assertIs(gc_._lay_ocr(), moi)
            self.assertIs(gc_._lay_ocr(), moi)
        nap.assert_called_once()
        self.assertTrue(gc_.ocr_dang_nap())

    def test_giai_ma_cap_nhat_luc_dung_va_dem(self):
        thay = []

        def _giai(anh):
            thay.append(gc_._so_dang_giai)
            return "1234"

        with patch.object(gc_, "_giai", side_effect=_giai):
            self.assertEqual(gc_.giai(b""), "1234")
        self.assertEqual(thay, [1])
        self.assertEqual(gc_._so_dang_giai, 0)
        self.assertGreater(gc_._luc_dung_ocr, 1000)

    def test_giai_ma_loi_van_tra_dem(self):
        with patch.object(gc_, "_giai", side_effect=gc_.LoiGiaiCaptcha("x")):
            with self.assertRaises(gc_.LoiGiaiCaptcha):
                gc_.giai(b"")
        self.assertEqual(gc_._so_dang_giai, 0)

    def test_hai_luong_cung_luc(self):
        cho = threading.Event()

        def _giai(anh):
            cho.wait(2)
            return "1"

        with patch.object(gc_, "_giai", side_effect=_giai):
            ts = [threading.Thread(target=gc_.giai, args=(b"",)) for _ in range(2)]
            for t in ts:
                t.start()
            while gc_._so_dang_giai < 2:
                pass
            self.assertFalse(gc_.giai_phong_ocr_neu_ranh(giay_ranh=0, bay_gio=10 ** 9))
            cho.set()
            for t in ts:
                t.join()
        self.assertEqual(gc_._so_dang_giai, 0)


if __name__ == "__main__":
    unittest.main()
