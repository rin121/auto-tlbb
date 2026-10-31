"""GA-05: GAuto khiêu chiến Ác Tặc, cả đội vào «Tặc Khấu doanh địa» thì AutoHoc không kéo về Đại Lý."""
import os
import sys
import time
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import giao_dien as gd  # noqa: E402
import su_kien_ac_tac as sk  # noqa: E402

AT = {"map_uu_tien": ["Kiếm Các"], "duong_dan_gauto": "x", "gauto_phut": 30}
PHO_BAN = "Tặc Khấu doanh địa"


def _luong(het_luc=0.0, truong=None):
    luong = gd.LuongNhanVat.__new__(gd.LuongNhanVat)
    luong.ten = "caychay288"
    luong.trang_thai = {}
    luong.ac_tac_state = {}
    luong.doi_ac_tac = luong.truong_ac_tac = luong.doi_pmp = luong.truong_pmp = None
    luong.dang_ac_tac = False
    luong.in_log = MagicMock()
    luong.nen_dung_ac_tac = lambda: False
    luong.ac_tac = MagicMock(khung_xong=None, gauto_khung=None, gauto_het_luc=het_luc, gauto_chi_so=0,
                             gauto_dong_cache={})
    luong.truong_ac_tac_trong_auto = lambda: (truong, [])
    luong.chon_doi_vien_ac_tac = lambda tv: {}
    luong.doc_doi_vien_ac_tac = lambda: {}
    luong.truong_nhom_xoay_vong = lambda: ""
    return luong


class TestGautoPhoBanAcTac(unittest.TestCase):
    def setUp(self):
        bay_gio = time.time()
        for p in (patch.object(gd, "khung_hien_tai", return_value=("2026-10-30", 13)),
                  patch.object(gd, "luc_bat_dau_khung", return_value=bay_gio - 60),
                  patch.object(gd, "luc_het_khung", return_value=bay_gio + 600),
                  patch.object(gd, "cai_dat_ac_tac", return_value=dict(AT, bat=True)),
                  patch.dict(sk._NHAN_KHUNG, clear=True),
                  patch.object(gd.gauto_ac_tac, "tim_cua_so_quan_ly", return_value=1),
                  patch.object(gd.gauto_ac_tac, "tat_ac_tac")):
            p.start()
            self.addCleanup(p.stop)

    def test_nhan_ten_pho_ban(self):
        self.assertTrue(sk.la_pho_ban_ac_tac(PHO_BAN))
        self.assertTrue(sk.la_pho_ban_ac_tac("tac khau doanh dia"))
        self.assertFalse(sk.la_pho_ban_ac_tac("Kiếm Các"))
        self.assertFalse(sk.la_pho_ban_ac_tac(None))

    def test_truong_trong_pho_ban_khong_ve_dai_ly(self):
        luong = _luong()
        self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": PHO_BAN}, {}, AT))
        luong.ac_tac.di_den_map_gauto.assert_not_called()
        self.assertIn(PHO_BAN, luong.trang_thai["mo_ta"])

    def test_truong_o_thanh_van_di_toi_map(self):
        luong = _luong()
        luong.xu_ly_gauto_ac_tac({"map": "Đại Lý"}, {}, AT)
        luong.ac_tac.di_den_map_gauto.assert_called_once()

    def test_doi_vien_trong_pho_ban_khong_tu_di(self):
        truong = MagicMock()
        truong.ac_tac = MagicMock(khung_xong=None, gauto_het_luc=0.0)
        luong = _luong(truong=truong)
        with patch.object(gd, "buoc_doi_vien") as buoc:
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": PHO_BAN}, {}, AT))
        buoc.assert_not_called()

    def test_het_gio_gauto_thi_bo_tich(self):
        luong = _luong(het_luc=time.time() - 1)
        self.assertFalse(luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT))
        gd.gauto_ac_tac.tat_ac_tac.assert_called_once()
        self.assertEqual(luong.ac_tac.gauto_het_luc, 0.0)
        self.assertEqual(luong.ac_tac.khung_xong, ("2026-10-30", 13))

    def test_het_gio_trong_pho_ban_van_tat_ngay(self):
        luong = _luong(het_luc=time.time() - 1)
        self.assertFalse(luong.xu_ly_gauto_ac_tac({"map": PHO_BAN}, {}, AT))
        gd.gauto_ac_tac.tat_ac_tac.assert_called_once()
        self.assertEqual(luong.ac_tac.khung_xong, ("2026-10-30", 13))

    def test_ngoai_pt_khong_phai_truong_nhom_thi_khong_dung_gauto(self):
        luong = _luong()
        luong.ten = "caychay35"
        luong.truong_nhom_xoay_vong = lambda: "caychay32"
        with patch.object(gd.gauto_ac_tac, "dat_cai_dat_ac_tac") as dat:
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT))
        dat.assert_not_called()
        luong.ac_tac.di_den_map_gauto.assert_not_called()
        self.assertIn("caychay32", luong.trang_thai["mo_ta"])

    def test_loi_sau_khi_bam_gauto_thi_khong_lam_lai(self):
        luong = _luong()
        loi = gd.gauto_ac_tac.LoiGautoAcTac("GAuto đổi dòng")
        loi.da_thao_tac = True
        with patch.object(gd.gauto_ac_tac, "dat_cai_dat_ac_tac", side_effect=loi) as dat, \
                patch.object(gd.gauto_ac_tac, "tom_tat_cua_so", return_value="GAuto"), \
                patch.object(gd.gauto_ac_tac, "tim_chi_so_dong_theo_ten", return_value=1):
            luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT)
            luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT)
        dat.assert_called_once()
        self.assertGreater(luong.ac_tac.gauto_het_luc, time.time())

    def test_toi_map_truoc_gio_bat_dau_thi_cho(self):
        luong = _luong()
        gd.luc_bat_dau_khung.return_value = time.time() + 90
        with patch.object(gd.gauto_ac_tac, "dat_cai_dat_ac_tac") as dat:
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT))
        dat.assert_not_called()
        luong.ac_tac.di_den_map_gauto.assert_not_called()
        self.assertIn("chờ", luong.trang_thai["mo_ta"])

    def test_bat_gauto_thi_het_luc_la_cuoi_khung(self):
        luong = _luong()
        with patch.object(gd.gauto_ac_tac, "dat_cai_dat_ac_tac") as dat, \
                patch.object(gd.gauto_ac_tac, "tom_tat_cua_so", return_value="GAuto"), \
                patch.object(gd.gauto_ac_tac, "tim_chi_so_dong_theo_ten", return_value=1):
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT))
        dat.assert_called_once()
        self.assertEqual(luong.ac_tac.gauto_het_luc, gd.luc_het_khung.return_value)

    def test_nhom_khac_da_nhan_khung_thi_khong_di(self):
        sk.nhan_khung(("2026-10-30", 13), "caychay322")
        luong = _luong()
        with patch.object(gd.gauto_ac_tac, "dat_cai_dat_ac_tac") as dat:
            self.assertFalse(luong.xu_ly_gauto_ac_tac({"map": "Đại Lý"}, {}, AT))
        dat.assert_not_called()
        luong.ac_tac.di_den_map_gauto.assert_not_called()
        self.assertEqual(luong.ac_tac.khung_xong, ("2026-10-30", 13))

    def test_het_khung_ngoai_gio_van_bo_tich(self):
        luong = _luong(het_luc=time.time() - 1)
        luong.ac_tac.gauto_khung = ("2026-10-30", 13)
        luong.dang_ac_tac = True
        with patch.object(gd, "ve_thanh_neu_o_map_ac_tac", return_value=False):
            luong.ket_thuc_ac_tac({"map": "Kiếm Các"})
        gd.gauto_ac_tac.tat_ac_tac.assert_called_once()
        self.assertEqual(luong.ac_tac.gauto_het_luc, 0.0)
        self.assertEqual(luong.ac_tac.khung_xong, ("2026-10-30", 13))
        self.assertFalse(luong.dang_ac_tac)

    def test_chua_het_gio_thi_giu_gauto(self):
        luong = _luong(het_luc=time.time() + 600)
        self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT))
        gd.gauto_ac_tac.tat_ac_tac.assert_not_called()
        luong.ac_tac.di_den_map_gauto.assert_not_called()


class TestKhungAcTac(unittest.TestCase):
    """GA-07: khung 21h, 20 phút → ra map 20:58, bật GAuto 21:00, ngưng 21:20; mỗi khung một nhóm."""

    AT20 = {"phut_gauto": 20}

    def _khung(self, gio, phut):
        return sk.khung_hien_tai(self.AT20, datetime(2026, 10, 30, gio, phut))

    def test_cua_so_khung(self):
        self.assertIsNone(self._khung(20, 57))
        self.assertEqual(self._khung(20, 58), ("2026-10-30", 21))
        self.assertEqual(self._khung(21, 0), ("2026-10-30", 21))
        self.assertEqual(self._khung(21, 19), ("2026-10-30", 21))
        self.assertIsNone(self._khung(21, 20))
        self.assertIsNone(self._khung(21, 45))

    def test_gio_bat_dau_va_het(self):
        khung = ("2026-10-30", 21)
        self.assertEqual(sk.luc_bat_dau_khung(khung), datetime(2026, 10, 30, 21).timestamp())
        self.assertEqual(sk.luc_het_khung(khung, self.AT20), datetime(2026, 10, 30, 21, 20).timestamp())
        self.assertEqual(sk.mo_ta_khung(khung, self.AT20), "21:00-21:20")

    def test_moi_khung_mot_nhom(self):
        with patch.dict(sk._NHAN_KHUNG, clear=True):
            khung = ("2026-10-30", 21)
            self.assertTrue(sk.nhan_khung(khung, "caychay322"))
            self.assertTrue(sk.nhan_khung(khung, "caychay322"))
            self.assertFalse(sk.nhan_khung(khung, "caychay30"))
            self.assertEqual(sk.nguoi_nhan_khung(khung), "caychay322")
            self.assertTrue(sk.nhan_khung(("2026-10-30", 22), "caychay30"))


class TestDiThangTuThanhTrungChuyen(unittest.TestCase):
    """GA-09: đứng ở Lạc Dương đi Tung Sơn / Đôn Hoàng thì đi thẳng; map đi từ Đại Lý (Kiếm Các) thì vẫn về Đại Lý."""

    def _di(self, map_hien, ten_map):
        r = sk.AcTacRunner.__new__(sk.AcTacRunner)
        r.ten, r.la_truong, r.doi_at, r.in_log = "caychay32", True, MagicMock(), MagicMock()
        r.vi_tri = {"map": map_hien}
        r.da_lam = []
        r._map = lambda: r.vi_tri["map"]

        def ve_thanh():
            r.da_lam.append("ve_dai_ly")
            r.vi_tri["map"] = "Đại Lý"

        def qua(chang):
            r.da_lam.append((chang.map_tu, chang.map_toi))
            r.vi_tri["map"] = chang.map_toi
        r._ve_thanh_at = ve_thanh
        r._qua_chang = qua
        r._gom_doi_dai_ly = lambda: r.da_lam.append("gom_dai_ly")
        r._gom_doi_tai_cho = lambda: r.da_lam.append("gom_tai_cho")
        with patch.object(sk, "tuy_chinh_map", return_value={}):
            r._di_toi_map(ten_map, ve_thanh_truoc=True, gom_doi=True)
        return r.da_lam

    def test_lac_duong_di_thang_tung_son(self):
        self.assertEqual(self._di("Lạc Dương", "Tung Sơn"), ["gom_tai_cho", ("Lạc Dương", "Tung Sơn")])

    def test_lac_duong_di_thang_don_hoang(self):
        self.assertEqual(self._di("Lạc Dương", "Đôn Hoàng"), ["gom_tai_cho", ("Lạc Dương", "Đôn Hoàng")])

    def test_lac_duong_di_kiem_cac_thi_ve_dai_ly(self):
        da_lam = self._di("Lạc Dương", "Kiếm Các")
        self.assertEqual(da_lam[:2], ["ve_dai_ly", "gom_dai_ly"])
        self.assertEqual(da_lam[-1], ("Đại Lý", "Kiếm Các"))

    def test_lac_duong_di_vo_luong_son_thi_ve_dai_ly(self):
        self.assertEqual(self._di("Lạc Dương", "Vô Lượng Sơn")[:2], ["ve_dai_ly", "gom_dai_ly"])

    def test_map_khac_di_tung_son_van_ve_dai_ly(self):
        self.assertEqual(self._di("Kiếm Các", "Tung Sơn"),
                         ["ve_dai_ly", "gom_dai_ly", ("Đại Lý", "Lạc Dương"), ("Lạc Dương", "Tung Sơn")])


if __name__ == "__main__":
    unittest.main()
