"""Sao chép nhanh / ghi cau_hinh.json một lần / không để bản cũ ghi đè bản mới."""
import copy
import unittest
from collections import OrderedDict
from unittest.mock import patch

import cau_hinh


class TestSaoChep(unittest.TestCase):
    def test_giong_deepcopy(self):
        goc = {"a": [1, 2.5, {"b": None, "c": True}], "d": "chu", "e": {"f": [[5, 1], [5, 2]]}}
        ban = cau_hinh._sao_chep(goc)
        self.assertEqual(ban, copy.deepcopy(goc))

    def test_khong_dung_chung_tham_chieu(self):
        goc = {"a": [1, {"b": [2]}]}
        ban = cau_hinh._sao_chep(goc)
        ban["a"][1]["b"].append(3)
        ban["a"].append(4)
        self.assertEqual(goc, {"a": [1, {"b": [2]}]})

    def test_kieu_la_dung_deepcopy(self):
        goc = {"t": ([1], 2), "o": OrderedDict(x=[1])}
        ban = cau_hinh._sao_chep(goc)
        self.assertEqual(ban, goc)
        self.assertIsNot(ban["t"][0], goc["t"][0])
        self.assertIsInstance(ban["o"], OrderedDict)
        self.assertIsNot(ban["o"]["x"], goc["o"]["x"])


class TestGhiMotLan(unittest.TestCase):
    def setUp(self):
        self.da_ghi = []
        p = patch.object(cau_hinh, "_ghi_json_an_toan", lambda duong_dan, chu: self.da_ghi.append(chu))
        p.start()
        self.addCleanup(p.stop)
        p2 = patch.dict(cau_hinh._du_lieu, {"nhan_vat": {"A": {"x": 1, "ds": [1]}, "B": {"x": 2, "ds": [2]}}})
        p2.start()
        self.addCleanup(p2.stop)

    def test_thay_tat_ca_nhan_vat(self):
        dung_chung = [9]

        def chep(ten, cai_dat):
            cai_dat["x"] += 10
            cai_dat["chung"] = dung_chung
            cai_dat["ten"] = ten
            return cai_dat
        cau_hinh.thay_tat_ca_nhan_vat(chep)
        nv = cau_hinh._du_lieu["nhan_vat"]
        self.assertEqual(nv["A"]["x"], 11)
        self.assertEqual(nv["B"]["x"], 12)
        self.assertEqual(nv["B"]["ten"], "B")
        self.assertEqual(len(self.da_ghi), 1)
        nv["A"]["chung"].append(1)
        self.assertEqual(nv["B"]["chung"], [9])
        self.assertEqual(dung_chung, [9])

    def test_cap_nhat_tat_ca_ghi_mot_lan(self):
        cau_hinh.cap_nhat_tat_ca_nhan_vat(lambda c: c.update(x=0) or True)
        self.assertEqual([c["x"] for c in cau_hinh._du_lieu["nhan_vat"].values()], [0, 0])
        self.assertEqual(len(self.da_ghi), 1)

    def test_cap_nhat_tat_ca_khong_doi_khong_ghi(self):
        self.assertFalse(cau_hinh.cap_nhat_tat_ca_nhan_vat(lambda c: False))
        self.assertEqual(self.da_ghi, [])

    def test_sua_nhan_vat_tra_ban_sao(self):
        ban = cau_hinh.sua_nhan_vat("A", lambda c: c["ds"].append(5))
        self.assertEqual(ban["ds"], [1, 5])
        ban["ds"].append(6)
        self.assertEqual(cau_hinh._du_lieu["nhan_vat"]["A"]["ds"], [1, 5])
        self.assertEqual(len(self.da_ghi), 1)

    def test_ban_cu_khong_ghi_de_ban_moi(self):
        with cau_hinh._khoa:
            cu = cau_hinh._chup_ban_luu()
            cau_hinh._du_lieu["nhan_vat"]["A"]["x"] = 99
            moi = cau_hinh._chup_ban_luu()
        cau_hinh._ghi_ban_luu(moi)
        cau_hinh._ghi_ban_luu(cu)
        self.assertEqual(len(self.da_ghi), 1)
        self.assertIn("99", self.da_ghi[0])


class TestDocTaiKhoanKhongGhiLai(unittest.TestCase):
    """doc_tai_khoan gọi mỗi 3 giây: file đã đúng dạng thì không được ghi lại (ghi liên tục làm lag, đụng .tmp)."""

    def setUp(self):
        import json
        import os
        import tempfile
        self.json, self.os = json, os
        thu_muc = tempfile.mkdtemp()
        self.duong_dan = os.path.join(thu_muc, "tai_khoan.json")
        self.so_lan_ghi = 0
        ghi_that = cau_hinh._ghi_json_an_toan

        def dem_ghi(duong_dan, chu):
            self.so_lan_ghi += 1
            ghi_that(duong_dan, chu)
        for p in (patch.object(cau_hinh, "DUONG_DAN_TAI_KHOAN", self.duong_dan),
                  patch.object(cau_hinh, "_ghi_json_an_toan", dem_ghi),
                  patch.object(cau_hinh, "la_thu_muc_game", return_value=True)):
            p.start()
            self.addCleanup(p.stop)

    def ghi_file(self, du_lieu):
        with open(self.duong_dan, "w", encoding="utf-8") as f:
            self.json.dump(du_lieu, f)

    def test_dang_moi_khong_ghi(self):
        self.ghi_file({"thu_muc_game": "x", "tai_khoan_pho_ban": [{"ten_dang_nhap": "a"}], "tai_khoan_train": []})
        for _ in range(3):
            gia_tri = cau_hinh.doc_tai_khoan()
        self.assertEqual(self.so_lan_ghi, 0)
        self.assertNotIn("tai_khoan", gia_tri)
        self.assertEqual(gia_tri["tai_khoan_pho_ban"], [{"ten_dang_nhap": "a"}])

    def test_dang_cu_chuyen_mot_lan_giu_tai_khoan(self):
        self.ghi_file({"thu_muc_game": "x", "tai_khoan": [{"ten_dang_nhap": "a"}, {"ten_dang_nhap": "b"}]})
        gia_tri = cau_hinh.doc_tai_khoan()
        self.assertEqual([t["ten_dang_nhap"] for t in gia_tri["tai_khoan_pho_ban"]], ["a", "b"])
        self.assertEqual(gia_tri["tai_khoan_train"], [])
        self.assertEqual(self.so_lan_ghi, 1)
        cau_hinh.doc_tai_khoan()
        self.assertEqual(self.so_lan_ghi, 1)
        with open(self.duong_dan, encoding="utf-8") as f:
            tren_file = self.json.load(f)
        self.assertNotIn("tai_khoan", tren_file)
        self.assertEqual(len(tren_file["tai_khoan_pho_ban"]), 2)


if __name__ == "__main__":
    unittest.main()
