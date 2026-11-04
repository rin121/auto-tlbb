import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from an_nguoi_choi import nen_bam_f12  # noqa: E402


class TestAnNguoiChoi(unittest.TestCase):
    def test_dung_yen_moi_bam_mot_lan(self):
        bam, toa, da, luc = nen_bam_f12(None, 10, 20, False, 0.0, 0.0, nguong=0.4)
        self.assertFalse(bam)
        bam, toa, da, luc = nen_bam_f12(toa, 10, 20, da, 0.5, luc, nguong=0.4)
        self.assertTrue(bam)
        self.assertTrue(da)
        bam, toa, da, luc = nen_bam_f12(toa, 10, 20, da, 2.0, luc, nguong=0.4)
        self.assertFalse(bam)

    def test_di_chuyen_roi_dung_lai_bam_nua(self):
        bam, toa, da, luc = nen_bam_f12((10, 20), 10, 20, True, 1.0, 0.0, nguong=0.4)
        bam, toa, da, luc = nen_bam_f12(toa, 15, 20, da, 1.2, luc, nguong=0.4)
        self.assertFalse(bam)
        self.assertFalse(da)
        self.assertEqual(toa, (15, 20))
        bam, toa, da, luc = nen_bam_f12(toa, 15, 20, da, 1.7, luc, nguong=0.4)
        self.assertTrue(bam)
