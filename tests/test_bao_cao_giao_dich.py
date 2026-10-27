"""Báo cáo giao dịch (bao_cao_giao_dich.csv) và đếm món / số lượng đã giao trong GiaoDich.chuyen."""
import csv
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import bao_cao_giao_dich as bc
import giao_dich


class TestBaoCao(unittest.TestCase):
    def setUp(self):
        self.thu_muc = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.thu_muc, True)
        self.duong_dan = os.path.join(self.thu_muc, "bao_cao_giao_dich.csv")
        bc._cho_ghi.clear()
        self.addCleanup(bc._cho_ghi.clear)

    def doc(self):
        with open(self.duong_dan, encoding="utf-8-sig", newline="") as f:
            return list(csv.reader(f))

    def test_tom_tat_gop_cung_ten(self):
        self.assertEqual(bc.tom_tat([("Bảo thạch", 2), ("Ngọc", 1), ("Bảo thạch", 3)]), "Bảo thạch x5, Ngọc x1")

    def test_ghi_tieu_de_mot_lan_va_dung_cot(self):
        luc = datetime(2026, 10, 27, 9, 52, 5)
        self.assertIsNone(bc.ghi("Nhóm 5 round 1", "DV1", "Truong", [("Bảo thạch", 2), ("Ngọc", 1)], luc,
                                 self.duong_dan))
        bc.ghi("Nhóm 5 round 1", "DV2", "Truong", [("Ngọc", 4)], luc, self.duong_dan)
        dong = self.doc()
        self.assertEqual(dong[0], bc.CAC_COT)
        self.assertEqual(dong[1], ["2026-10-27", "09:52:05", "Nhóm 5 round 1", "DV1", "Truong", "2", "3",
                                   "Bảo thạch x2, Ngọc x1"])
        self.assertEqual(dong[2][3:7], ["DV2", "Truong", "1", "4"])
        self.assertEqual(len(dong), 3)
        with open(self.duong_dan, "rb") as f:
            self.assertEqual(f.read().count(b"\xef\xbb\xbf"), 1)

    def test_khong_giao_duoc_mon_nao_thi_khong_ghi(self):
        self.assertIsNone(bc.ghi("Nhóm 1", "A", "B", [], duong_dan=self.duong_dan))
        self.assertFalse(os.path.exists(self.duong_dan))

    def test_file_bi_khoa_thi_ghi_bu_lan_sau(self):
        khoa = os.path.join(self.thu_muc, "dang_mo")
        os.mkdir(khoa)
        loi = bc.ghi("Nhóm 1", "A", "B", [("X", 1)], duong_dan=khoa)
        self.assertIn("ghi bù", loi)
        bc.ghi("Nhóm 2", "C", "D", [("Y", 2)], duong_dan=self.duong_dan)
        self.assertEqual([d[2] for d in self.doc()[1:]], ["Nhóm 1", "Nhóm 2"])
        self.assertEqual(bc._cho_ghi, [])

    def test_ghi_va_bao_log_khi_loi(self):
        in_log = MagicMock()
        with patch.object(bc, "ghi", return_value="lỗi"):
            bc.ghi_va_bao(in_log, "Nhóm 1", "A", "B", [("X", 1)])
        in_log.assert_called_once()


class TestDemMonDaGiao(unittest.TestCase):
    def test_chi_tiet_chi_tinh_o_da_sang_tay(self):
        truoc = {("base", 3): (10, 2, "Bảo thạch"), ("base", 4): (11, 5, "Ngọc"), ("base", 5): (12, 1, "Áo")}
        sau = {("base", 5): (12, 1, "Áo")}
        game = SimpleNamespace(lua=None)
        gd = giao_dich.GiaoDich(game, game, "DV1", "Truong", MagicMock())
        with patch.object(giao_dich, "doc_tui", side_effect=[truoc, truoc, sau, sau]), \
                patch.object(gd, "_lai_gan"), \
                patch.object(gd, "_mot_lan", return_value=[("base", 3), ("base", 4), ("base", 5)]):
            so = gd.chuyen([("base", 3), ("base", 4), ("base", 5)])
        self.assertEqual(so, 2)
        self.assertEqual(gd.chi_tiet, [("Bảo thạch", 2), ("Ngọc", 5)])


if __name__ == "__main__":
    unittest.main()
