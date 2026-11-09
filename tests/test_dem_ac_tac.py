"""Bộ đếm «Hôm nay Ác Tặc»: mỗi khung đội trưởng đi xong chỉ cộng một lần."""
import unittest
from unittest.mock import MagicMock, patch

import pho_ban_pmp as pb
from su_kien_ac_tac import AcTacRunner


class TestDemAcTac(unittest.TestCase):
    def setUp(self):
        self.kho = {"cosato1": {}}

        def sua_nhan_vat(ten, sua):
            cai_dat = self.kho.setdefault(ten, {})
            sua(cai_dat)
            return cai_dat

        vo = patch("cau_hinh.sua_nhan_vat", side_effect=sua_nhan_vat)
        vo.start()
        self.addCleanup(vo.stop)
        self.runner = AcTacRunner(MagicMock(), lambda *_: None)

    def _so_lan(self):
        return pb.so_luot_hom_nay(self.kho["cosato1"])["ac_tac"]

    def test_moi_khung_mot_lan(self):
        khung = ("2026-11-09", 21)
        self.runner.dem_xong_khung("cosato1", khung)
        self.runner.dem_xong_khung("cosato1", khung)
        self.assertEqual(self._so_lan(), 1)
        self.runner.dem_xong_khung("cosato1", ("2026-11-09", 23))
        self.assertEqual(self._so_lan(), 2)

    def test_khong_co_khung_thi_khong_dem(self):
        self.runner.dem_xong_khung("cosato1", None)
        self.assertEqual(self._so_lan(), 0)


if __name__ == "__main__":
    unittest.main()
