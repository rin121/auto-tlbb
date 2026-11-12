"""GA-05: GAuto khiêu chiến Ác Tặc, cả đội vào «Tặc Khấu doanh địa» thì AutoHoc không kéo về Đại Lý."""
import itertools
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

    def test_trong_pho_ban_o_auto_tat_thi_tich_lai(self):
        luong = _luong(het_luc=time.time() + 600)
        luong.ac_tac.gauto_khung = ("2026-10-30", 13)
        with patch.object(gd.gauto_ac_tac, "bat_lai_auto_neu_tat", return_value=True) as giu:
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": PHO_BAN}, {}, AT))
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": PHO_BAN}, {}, AT))
        giu.assert_called_once()
        self.assertIn("tích lại", luong.in_log.call_args[0][0])

    def test_trong_pho_ban_auto_dang_bat_thi_khong_bam_lai(self):
        luong = _luong(het_luc=time.time() + 600)
        luong.ac_tac.gauto_khung = ("2026-10-30", 13)
        with patch.object(gd.gauto_ac_tac, "bat_lai_auto_neu_tat", return_value=False) as giu:
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": PHO_BAN}, {}, AT))
        giu.assert_called_once()
        luong.in_log.assert_not_called()

    def test_ngoai_pho_ban_khong_cham_o_auto(self):
        luong = _luong(het_luc=time.time() + 600)
        luong.ac_tac.gauto_khung = ("2026-10-30", 13)
        with patch.object(gd.gauto_ac_tac, "bat_lai_auto_neu_tat") as giu:
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT))
        giu.assert_not_called()

    def test_doi_vien_trong_pho_ban_khong_tu_di(self):
        truong = MagicMock()
        truong.ac_tac = MagicMock(khung_xong=None, gauto_het_luc=0.0)
        luong = _luong(truong=truong)
        with patch.object(gd, "buoc_doi_vien") as buoc:
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": PHO_BAN}, {}, AT))
        buoc.assert_not_called()

    def _doi_vien_gauto(self, map_truong, het_luc_truong):
        truong = MagicMock()
        truong.ten = "cosato144"
        truong.ac_tac = MagicMock(khung_xong=None, gauto_het_luc=het_luc_truong)
        truong.game.thong_tin.return_value = {"map": map_truong}
        luong = _luong(truong=truong)
        return luong

    def test_doi_vien_bi_bo_lai_dai_ly_khi_gauto_dang_chay_thi_tu_di(self):
        """20:57 khung 21h: game bỏ đội viên ở Đại Lý, đội trưởng bật GAuto ở Kiếm Các → đội viên tự đi."""
        luong = self._doi_vien_gauto("Kiếm Các", time.time() + 600)
        self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Đại Lý"}, {}, AT))
        luong.ac_tac.di_rieng.assert_not_called()
        luong.ac_tac_state["luc_bi_bo_lai"] -= sk.GIAY_BI_BO_LAI_DAI_LY
        self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Đại Lý"}, {}, AT))
        luong.ac_tac.di_rieng.assert_called_once()
        self.assertEqual(luong.ac_tac.di_rieng.call_args[0][4], "Kiếm Các")
        self.assertIn("bị bỏ lại", luong.in_log.call_args[0][0])

    def test_doi_vien_bi_bo_lai_khi_truong_toi_map_chua_bat_gauto(self):
        luong = self._doi_vien_gauto("Kiếm Các", 0.0)
        luong.ac_tac_state["luc_bi_bo_lai"] = time.time() - sk.GIAY_BI_BO_LAI_DAI_LY
        self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Đại Lý"}, {}, AT))
        luong.ac_tac.di_rieng.assert_called_once()

    def test_doi_vien_cung_map_truong_khong_tu_di(self):
        luong = self._doi_vien_gauto("Kiếm Các", time.time() + 600)
        luong.ac_tac_state["luc_bi_bo_lai"] = time.time() - 100
        self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT))
        luong.ac_tac.di_rieng.assert_not_called()
        self.assertIn("theo đội trưởng", luong.trang_thai["mo_ta"])
        self.assertNotIn("luc_bi_bo_lai", luong.ac_tac_state)

    def test_truong_con_o_dai_ly_thi_doi_vien_khong_tu_di(self):
        luong = self._doi_vien_gauto("Đại Lý", 0.0)
        luong.ac_tac_state["luc_bi_bo_lai"] = time.time() - 100
        luong.truong_ac_tac_trong_auto()[0].doi_ac_tac = None
        self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Đại Lý"}, {}, AT))
        luong.ac_tac.di_rieng.assert_not_called()

    def test_het_gio_gauto_thi_bo_tich(self):
        luong = _luong(het_luc=time.time() - 1)
        self.assertFalse(luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT))
        gd.gauto_ac_tac.tat_ac_tac.assert_called_once()
        self.assertEqual(luong.ac_tac.gauto_het_luc, 0.0)
        self.assertEqual(luong.ac_tac.khung_xong, ("2026-10-30", 13))

    def test_het_gio_trong_pho_ban_cho_xong_aoi(self):
        luong = _luong(het_luc=time.time() - 1)
        luong.game = MagicMock()
        sk.nhan_khung(("2026-10-30", 13), luong.ten)
        with patch.object(gd, "doc_nhom", return_value={"thanh_vien": [luong.ten]}):
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": PHO_BAN}, {}, AT))
        gd.gauto_ac_tac.tat_ac_tac.assert_not_called()
        self.assertIn("chờ", luong.trang_thai["mo_ta"])

    def test_het_gio_trong_pho_ban_do_vien_ngoai_thi_tat(self):
        luong = _luong(het_luc=time.time() - 1)
        luong.game = MagicMock()
        dv = MagicMock()
        dv.game.thong_tin.return_value = {"map": "Kiếm Các"}
        luong.tim_luong = lambda ten: dv if ten != luong.ten else None
        sk.nhan_khung(("2026-10-30", 13), luong.ten)
        with patch.object(gd, "doc_nhom", return_value={"thanh_vien": [luong.ten, "doi_vien"]}):
            self.assertFalse(luong.xu_ly_gauto_ac_tac({"map": PHO_BAN}, {}, AT))
        gd.gauto_ac_tac.tat_ac_tac.assert_called_once()

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

    def test_loi_che_cua_so_thi_thu_lai_khung(self):
        """GAuto bị cửa sổ game che lúc tích ô đầu dòng — chưa thao tác xong thì thử lại khung."""
        luong = _luong()
        loi = gd.gauto_ac_tac.LoiGautoAcTac("cửa sổ GAuto đang bị cửa sổ khác che chỗ ô đầu dòng nhân vật")
        with patch.object(gd.gauto_ac_tac, "dat_cai_dat_ac_tac", side_effect=loi) as dat, \
                patch.object(gd.gauto_ac_tac, "tom_tat_cua_so", return_value="GAuto"), \
                patch.object(gd.gauto_ac_tac, "tim_chi_so_dong_theo_ten", return_value=1):
            luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT)
            luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT)
        self.assertEqual(dat.call_count, 2)
        self.assertIsNone(luong.ac_tac.gauto_khung)

    def test_toi_map_truoc_gio_thi_bat_ngay(self):
        """Tới map trước giờ tròn (vd 01:59) thì bật GAuto liền. Giờ tắt vẫn là cuối khung."""
        luong = _luong()
        gd.luc_bat_dau_khung.return_value = time.time() + 90
        with patch.object(gd.gauto_ac_tac, "dat_cai_dat_ac_tac") as dat, \
                patch.object(gd.gauto_ac_tac, "tom_tat_cua_so", return_value="GAuto"), \
                patch.object(gd.gauto_ac_tac, "tim_chi_so_dong_theo_ten", return_value=1):
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT))
        dat.assert_called_once()
        luong.ac_tac.di_den_map_gauto.assert_not_called()
        self.assertNotIn("chờ", luong.trang_thai["mo_ta"])
        self.assertEqual(luong.ac_tac.gauto_het_luc, gd.luc_het_khung.return_value)

    def test_bat_gauto_thi_het_luc_la_cuoi_khung(self):
        luong = _luong()
        with patch.object(gd.gauto_ac_tac, "dat_cai_dat_ac_tac") as dat, \
                patch.object(gd.gauto_ac_tac, "tom_tat_cua_so", return_value="GAuto"), \
                patch.object(gd.gauto_ac_tac, "tim_chi_so_dong_theo_ten", return_value=1):
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Kiếm Các"}, {}, AT))
        dat.assert_called_once()
        self.assertEqual(luong.ac_tac.gauto_het_luc, gd.luc_het_khung.return_value)

    def test_nguoi_nhan_con_online_thi_cho_khong_khoa_khung(self):
        sk.nhan_khung(("2026-10-30", 13), "truongnhom")
        luong = _luong()
        khac = MagicMock()
        khac.doi_ac_tac = None
        luong.tim_luong = lambda ten: khac if ten == "truongnhom" else None
        with patch.object(gd, "doc_nhom", return_value={"thanh_vien": []}):
            self.assertTrue(luong.xu_ly_gauto_ac_tac({"map": "Đại Lý"}, {}, AT))
        self.assertIsNone(luong.ac_tac.khung_xong)
        self.assertIn("chờ vào nhóm", luong.trang_thai["mo_ta"])
        luong.ac_tac.di_den_map_gauto.assert_not_called()

    def test_truong_moi_gianh_lai_khung_roi_ra_map(self):
        sk.nhan_khung(("2026-10-30", 13), "doi_vien")
        luong = _luong()
        luong.truong_nhom_xoay_vong = lambda: luong.ten
        khac = MagicMock()
        khac.doi_ac_tac = None
        luong.tim_luong = lambda ten: khac if ten == "doi_vien" else None
        luong.xu_ly_gauto_ac_tac({"map": "Đại Lý"}, {}, AT)
        luong.ac_tac.di_den_map_gauto.assert_called_once()
        self.assertIsNone(luong.ac_tac.khung_xong)
        self.assertEqual(sk.nguoi_nhan_khung(("2026-10-30", 13)), luong.ten)

    def test_truong_moi_khong_online_thi_tu_ra_map(self):
        luong = _luong()
        luong.ten = "caychay35"
        luong.truong_nhom_xoay_vong = lambda: "caychay32"
        luong.tim_luong = lambda ten: None
        luong.xu_ly_gauto_ac_tac({"map": "Đại Lý"}, {}, AT)
        luong.ac_tac.di_den_map_gauto.assert_called_once()

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


class TestRaMapTruocAcTac(unittest.TestCase):
    def test_ket_pmp_thi_ve_dai_ly_khong_bam_theo_doi(self):
        game = MagicMock()
        game.lua.chay.return_value = b"0"
        doi = MagicMock(vi_tri=(10, 10, "Đại Lý"), map_dich="Kiếm Các", truong="truong")
        doi.vung_cho.return_value = None
        with patch.object(sk, "chuan_bi_ve_thanh", return_value=True) as chuan_bi, \
                patch.object(sk, "dong_y_theo_doi_popup"):
            loai, chu = sk.buoc_doi_vien(
                game, doi, {"map": "Phiêu Miễu Phong", "x": 1, "y": 1}, {})
        self.assertEqual(loai, "mo_ta")
        self.assertIn("Đại Lý", chu)
        self.assertNotIn("không tự về", chu)
        chuan_bi.assert_called_once()
        self.assertNotIn(sk.MA_THEO_DOI, [c.args[0] for c in game.lua.chay.call_args_list])

    def test_dang_o_map_ac_tac_thi_khong_ve_thanh(self):
        game = MagicMock()
        game.lua.chay.return_value = b"0"
        doi = MagicMock(vi_tri=(10, 10, "Đại Lý"), map_dich="Kiếm Các", truong="truong")
        doi.vung_cho.return_value = None
        with patch.object(sk, "chuan_bi_ve_thanh") as chuan_bi, \
                patch.object(sk, "dong_y_theo_doi_popup"):
            _, chu = sk.buoc_doi_vien(game, doi, {"map": "Kiếm Các", "x": 1, "y": 1}, {})
        self.assertIn("không tự về", chu)
        chuan_bi.assert_not_called()


class TestDoiVienBiBoLaiDaiLy(unittest.TestCase):
    """Đội trưởng đã ở map đích, đội viên còn Đại Lý quá 20 giây thì tự đi (di_rieng)."""

    def test_chua_du_giay_thi_chua_di(self):
        state = {}
        self.assertIsNone(sk.doi_vien_bi_bo_lai("Đại Lý", "Kiếm Các", "Kiếm Các", state, bay_gio=100))
        self.assertIsNone(sk.doi_vien_bi_bo_lai("Đại Lý", "Kiếm Các", "Kiếm Các", state, bay_gio=119))

    def test_du_giay_thi_di_roi_cho_lan_thu_lai(self):
        state = {}
        sk.doi_vien_bi_bo_lai("Đại Lý", "Kiếm Các", "Kiếm Các", state, bay_gio=100)
        self.assertEqual(sk.doi_vien_bi_bo_lai("Đại Lý", "Kiếm Các", "Kiếm Các", state, bay_gio=120),
                         ("di", "Kiếm Các"))
        loai, chu = sk.doi_vien_bi_bo_lai("Đại Lý", "Kiếm Các", "Kiếm Các", state, bay_gio=130)
        self.assertEqual(loai, "mo_ta")
        self.assertIn("bị bỏ lại", chu)
        self.assertEqual(sk.doi_vien_bi_bo_lai("Đại Lý", "Kiếm Các", "Kiếm Các", state,
                                               bay_gio=120 + sk.GIAY_GIUA_HAI_LAN_DI_RIENG),
                         ("di", "Kiếm Các"))

    def test_khong_bi_bo_lai_thi_xoa_moc(self):
        state = {"luc_bi_bo_lai": 0}
        for map_dv, map_tr in (("Kiếm Các", "Kiếm Các"), ("Đại Lý", "Đại Lý"), ("Lạc Dương", "Kiếm Các"),
                               ("Đại Lý", PHO_BAN), ("Đại Lý", None)):
            state["luc_bi_bo_lai"] = 0
            self.assertIsNone(sk.doi_vien_bi_bo_lai(map_dv, map_tr, "Kiếm Các", state, bay_gio=1000))
            self.assertNotIn("luc_bi_bo_lai", state)

    def _buoc(self, state, dang_theo=b"1"):
        game = MagicMock()
        game.lua.chay.return_value = dang_theo
        doi = MagicMock(vi_tri=(98, 78, "Kiếm Các"), map_dich="Kiếm Các", truong="cosato144")
        doi.vung_cho.return_value = None
        with patch.object(sk, "dong_y_theo_doi_popup"):
            return sk.buoc_doi_vien(game, doi, {"map": "Đại Lý", "x": 160, "y": 157}, state)

    def test_buoc_doi_vien_co_theo_doi_cu_van_tu_di(self):
        """Cờ Theo đội đọc «đang theo» mà game đã bỏ lại ở Đại Lý: quá 20 giây vẫn tự đi."""
        state = {}
        loai, chu = self._buoc(state)
        self.assertEqual(loai, "mo_ta")
        self.assertIn("theo đội trưởng", chu)
        state["luc_bi_bo_lai"] -= sk.GIAY_BI_BO_LAI_DAI_LY
        self.assertEqual(self._buoc(state), ("di", "Kiếm Các"))

    def test_buoc_doi_vien_khong_theo_doi_cung_tu_di(self):
        state = {"luc_bi_bo_lai": time.time() - sk.GIAY_BI_BO_LAI_DAI_LY}
        self.assertEqual(self._buoc(state, dang_theo=b"0"), ("di", "Kiếm Các"))

    def test_di_rieng_bo_theo_doi_truoc_khi_di(self):
        r = sk.AcTacRunner.__new__(sk.AcTacRunner)
        r._bat_dau = lambda *a: ({}, ("2026-11-10", 21))
        r.nen_dung = lambda: False
        r._tt = lambda: {"map": "Đại Lý"}
        r._log = MagicMock()
        r._di_toi_map = MagicMock()
        r.game = MagicMock()
        with patch.object(sk, "bo_theo_doi") as bo:
            r.di_rieng("cosato155", {}, {}, lambda: False, "Kiếm Các")
        bo.assert_called_once_with(r.game)
        r._di_toi_map.assert_called_once_with("Kiếm Các", ve_thanh_truoc=True, gom_doi=False)


class TestCaDoiPhoBanAcTac(unittest.TestCase):
    def test_ca_doi_mot_minh_trong_pho_ban(self):
        self.assertTrue(sk.ca_doi_trong_pho_ban_ac_tac(PHO_BAN, [], lambda t: PHO_BAN))

    def test_ca_doi_co_nguoi_ngoai_aoi(self):
        ds = ["a", "b"]
        self.assertFalse(sk.ca_doi_trong_pho_ban_ac_tac(
            PHO_BAN, ds, lambda t: PHO_BAN if t == "a" else "Kiếm Các"))

    def test_ca_doi_ca_hai_trong_aoi(self):
        ds = ["a", "b"]
        self.assertTrue(sk.ca_doi_trong_pho_ban_ac_tac(PHO_BAN, ds, lambda t: PHO_BAN))


class TestKhungAcTac(unittest.TestCase):
    """GA-07: khung 21h, 20 phút → ra map 20:57, bật GAuto 21:00, ngưng 21:20; mỗi khung một nhóm."""

    AT20 = {"phut_gauto": 20}

    def _khung(self, gio, phut):
        return sk.khung_hien_tai(self.AT20, datetime(2026, 10, 30, gio, phut))

    def test_cua_so_khung(self):
        self.assertIsNone(self._khung(20, 56))
        self.assertEqual(self._khung(20, 57), ("2026-10-30", 21))
        self.assertEqual(self._khung(20, 58), ("2026-10-30", 21))
        self.assertEqual(self._khung(21, 0), ("2026-10-30", 21))
        self.assertEqual(self._khung(21, 19), ("2026-10-30", 21))
        self.assertIsNone(self._khung(21, 20))
        self.assertIsNone(self._khung(21, 45))

    def test_khung_02h_luon_di(self):
        """Không còn bỏ khung 02h: 01:57 đã tính khung 02, kể cả json cũ còn bo_khung_02h."""
        self.assertEqual(self._khung(1, 57), ("2026-10-30", 2))
        self.assertEqual(self._khung(2, 0), ("2026-10-30", 2))
        self.assertEqual(self._khung(2, 19), ("2026-10-30", 2))
        self.assertIsNone(self._khung(2, 20))
        self.assertEqual(sk.cac_khung({"bo_khung_02h": True}), sk.KHUNG_GIO)
        self.assertIn("02:00-02:20", sk.mo_ta_lich(self.AT20))

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


class TestMapKinhHo(unittest.TestCase):
    """Map Ác Tặc qua Tô Châu là Kính Hồ (không phải Tây Hồ)."""

    def test_danh_sach_map_co_kinh_ho(self):
        self.assertIn("Kính Hồ", gd.cau_hinh.CAC_MAP_AC_TAC)
        self.assertNotIn("Tây Hồ", gd.cau_hinh.CAC_MAP_AC_TAC)
        self.assertEqual(sk.ten_map_chuan("kinh ho"), "Kính Hồ")
        self.assertIsNone(sk.ten_map_chuan("Tây Hồ"))

    def test_kinh_ho_di_qua_to_chau(self):
        self.assertEqual(sk.hub_cua_map("Kính Hồ"), sk.MAP_TO_CHAU)
        chang = sk.chuoi_buoc_toi("Kính Hồ", {})
        self.assertEqual([c.map_toi for c in chang], [sk.MAP_TO_CHAU, "Kính Hồ"])
        self.assertIsNone(chang[-1].ten_npc)
        self.assertEqual(chang[-1].xy, sk.CONG_TOI_MAP["Kính Hồ"])

    def test_cong_tien_nhan_chi_lo(self):
        """Tọa độ cổng theo Tiên Nhân Chỉ Lộ (Config.axp, loại 99 «Vận chuyển»): Tô Châu scene 1, Lạc Dương scene 0."""
        self.assertEqual(sk.CONG_TOI_MAP["Kính Hồ"], (32, 162))
        self.assertNotEqual(sk.CONG_TOI_MAP["Kính Hồ"], (182, 287))  # cổng Tây Hồ
        self.assertEqual(sk.CONG_TOI_MAP["Thái Hồ"], (181, 33))
        self.assertEqual(sk.CONG_TOI_MAP["Đôn Hoàng"], (33, 130))
        self.assertEqual(sk.CONG_TOI_MAP["Tung Sơn"], (159, 287))

    def test_json_cu_tay_ho_doi_sang_kinh_ho(self):
        cai_dat = {"ac_tac": {"map_uu_tien": ["Kiếm Các", "Tây Hồ"],
                              "thu_tu_map": ["Vô Lượng Sơn", "Kiếm Các", "Tây Hồ", "Đôn Hoàng", "Thái Hồ", "Tung Sơn"]}}
        self.assertTrue(gd.cau_hinh._them_ac_tac(cai_dat))
        self.assertEqual(cai_dat["ac_tac"]["map_uu_tien"], ["Kiếm Các", "Kính Hồ"])
        self.assertEqual(cai_dat["ac_tac"]["thu_tu_map"], gd.cau_hinh.CAC_MAP_AC_TAC)
        self.assertFalse(gd.cau_hinh._them_ac_tac(cai_dat))


class TestGiaLapAcTac(unittest.TestCase):
    def tearDown(self):
        sk.huy_gia_lap_ac_tac()

    def test_gia_lap_mo_khung_ngay_va_het_sau_phut(self):
        truoc = time.time()
        khung = sk.bat_gia_lap_ac_tac(20, bay_gio=truoc)
        self.assertTrue(sk.gia_lap_con_hieu_luc(truoc + 10))
        self.assertFalse(sk.gia_lap_con_hieu_luc(truoc + 20 * 60))
        self.assertEqual(sk.khung_hien_tai({"bat": False}), khung)
        self.assertEqual(sk.luc_het_khung(khung, {}), truoc + 20 * 60)
        self.assertTrue(sk.ac_tac_dang_bat({"bat": False}))
        self.assertIn("giả lập", sk.mo_ta_khung(khung, {}))
        # Đồng hồ truyền vào vẫn là lịch thật, không bị giả lập nuốt.
        self.assertIsNone(sk.khung_hien_tai({"bat": False}, datetime(2026, 10, 30, 10, 0)))

    def test_het_gio_thi_khong_con_khung(self):
        sk.huy_gia_lap_ac_tac()
        self.assertFalse(sk.ac_tac_dang_bat({"bat": False}))

    def test_dung_gia_lap_tra_khung_va_tat_ngay(self):
        khung = sk.bat_gia_lap_ac_tac(20)
        self.assertEqual(sk.huy_gia_lap_ac_tac(), khung)
        self.assertIsNone(sk.huy_gia_lap_ac_tac())
        self.assertFalse(sk.gia_lap_con_hieu_luc())
        self.assertNotEqual(sk.khung_hien_tai({"bat": False}), khung)
        # Khung đã hủy: giờ hết rơi về mốc bắt đầu, luồng nào còn giữ khóa khung cũng coi là hết giờ.
        self.assertLessEqual(sk.luc_het_khung(khung, {}), time.time())

    def _runner(self, khung, gauto_het_luc):
        r = sk.AcTacRunner.__new__(sk.AcTacRunner)
        r.khung = r.gauto_khung = khung
        r.het_khung = time.time() + 1200
        r.gauto_het_luc = gauto_het_luc
        return r

    def test_dung_gia_lap_het_khung_runner_va_gauto(self):
        bay_gio = time.time()
        khung = ("gia_lap", int(bay_gio))
        r = self._runner(khung, bay_gio + 1200)
        r.dung_gia_lap(khung, bay_gio=bay_gio)
        self.assertEqual(r.het_khung, bay_gio)
        self.assertEqual(r.gauto_het_luc, bay_gio)

    def test_dung_gia_lap_khong_dong_khung_khac_va_gauto_chua_bat(self):
        bay_gio = time.time()
        khung_that = ("2026-10-30", 21)
        r = self._runner(khung_that, bay_gio + 1200)
        r.dung_gia_lap(("gia_lap", int(bay_gio)), bay_gio=bay_gio)
        self.assertEqual(r.het_khung, bay_gio + 1200)
        self.assertEqual(r.gauto_het_luc, bay_gio + 1200)
        khung = ("gia_lap", int(bay_gio))
        r = self._runner(khung, 0.0)
        r.dung_gia_lap(khung, bay_gio=bay_gio)
        self.assertEqual(r.gauto_het_luc, 0.0)
        r.dung_gia_lap(None, bay_gio=bay_gio)

    def test_dung_khi_dang_di_toi_map_gauto_khong_vang_loi(self):
        khung = ("gia_lap", int(time.time()))
        r = sk.AcTacRunner.__new__(sk.AcTacRunner)
        r._bat_dau = lambda *a: ({}, khung)
        r._dong_hoi_thoai = MagicMock()
        r._di_toi_map = MagicMock(side_effect=sk._HetKhung())
        r.game = MagicMock()
        doi = MagicMock()
        with patch.object(sk, "bo_theo_doi"):
            r.di_den_map_gauto("truong", {}, {}, lambda: False, "Kiếm Các", doi)
        self.assertEqual(doi.map_dich, "Kiếm Các")
        self.assertIsNone(r.doi_at)


class TestChoCaDoiTheoKhiDiMap(unittest.TestCase):
    """Đội trưởng không dịch chuyển khi còn đội viên chưa cùng map hoặc chưa Theo đội."""

    def _runner(self, maps, theo, map_truong="Lạc Dương"):
        r = sk.AcTacRunner.__new__(sk.AcTacRunner)
        r.ten, r.la_truong, r.in_log = "truong", True, MagicMock()
        r.trang_thai = {}
        r.nen_dung = lambda: False
        r.het_khung = float("inf")
        r.dang_ket_thuc = False
        r._map = lambda: map_truong
        r._trieu_at_state = {}
        r.game = MagicMock()
        doi = MagicMock()
        doi.cac_doi_vien = {"a": MagicMock(), "b": MagicMock()}
        doi.lam_moi = MagicMock()
        doi.map_doi_vien.side_effect = lambda: dict(maps)
        doi.chua_theo.side_effect = lambda: list(theo)
        doi.gui_trieu_tap = MagicMock()
        r.doi_at = doi
        return r

    def test_du_theo_thi_di(self):
        r = self._runner({"a": "Lạc Dương", "b": "Lạc Dương"}, [])
        r._cho_tat_ca_theo_truoc_khi_di()
        r.game.lua.chay.assert_not_called()

    def test_chua_theo_thi_khong_di(self):
        r = self._runner({"a": "Lạc Dương", "b": "Lạc Dương"}, ["b"])
        with patch.object(sk.time, "sleep"), patch.object(sk.time, "time", side_effect=[0, 0, 1000]):
            with self.assertRaises(sk.LoiAcTac) as cm:
                r._cho_tat_ca_theo_truoc_khi_di()
        self.assertIn("chưa theo đội: b", str(cm.exception))

    def test_gom_dai_ly_thieu_nguoi_thi_khong_di(self):
        r = self._runner({"a": "Đại Lý", "b": "Kiếm Các"}, [], map_truong="Đại Lý")
        r._goi_doi_vien_ve_thanh = lambda bat_buoc=False: ["b"]
        with patch.object(sk.time, "sleep"), patch.object(sk.time, "time", side_effect=[0, 0, 1000]):
            with self.assertRaises(sk.LoiAcTac) as cm:
                r._gom_doi_dai_ly()
        self.assertIn("b chưa về Đại Lý", str(cm.exception))

    def test_doi_vien_o_hub_khi_truong_dai_ly_thi_ve_gom(self):
        game, doi = MagicMock(), MagicMock()
        doi.vi_tri = (1, 2, "Đại Lý")
        doi.vung_cho = lambda m: None
        doi.map_dich = "Tung Sơn"
        doi.truong = "truong"
        state = {}
        with patch.object(sk, "dong_y_theo_doi_popup"), \
                patch.object(sk, "_ve_dai_ly_gom_doi", return_value=True) as ve, \
                patch.object(game.lua, "chay", return_value=b"0"):
            loai, chu = sk.buoc_doi_vien(game, doi, {"map": "Lạc Dương", "x": 1, "y": 1}, state)
        self.assertEqual(loai, "mo_ta")
        self.assertIn("về Đại Lý gom đội", chu)
        ve.assert_called_once()

    def test_da_toi_map_thi_cho_doi_vien(self):
        r = self._runner({"a": "Tung Sơn", "b": "Lạc Dương"}, [])
        with patch.object(sk.time, "sleep"), patch.object(sk.time, "time", side_effect=[0, 0, 1000]):
            with self.assertRaises(sk.LoiAcTac) as cm:
                r._cho_doi_vien_toi_map("Tung Sơn")
        self.assertIn("b chưa tới Tung Sơn", str(cm.exception))


class TestRotTheoDoiTruocKhiDichChuyen(unittest.TestCase):
    """14:03 / 14:07 ngày 12/11: đội viên rớt Theo đội lúc đội trưởng chạy tới Di Chuyển — chưa chọn dòng, mời lại."""

    def _runner(self, chua_theo):
        r = sk.AcTacRunner.__new__(sk.AcTacRunner)
        r.ten, r.la_truong, r.in_log = "cosato10", True, MagicMock()
        r.trang_thai = {}
        r.doi_at = MagicMock(cac_doi_vien={"cosato12": MagicMock(), "cosato13": MagicMock()})
        r.doi_at.chua_theo.side_effect = chua_theo
        for ten in ("_cho_tat_ca_theo_truoc_khi_di", "_cho_doi_gan_npc", "_chon", "_cho_dong", "_dong_hoi_thoai",
                    "_cho_doi_vien_toi_map"):
            setattr(r, ten, MagicMock())
        r._mo_npc = MagicMock(return_value=[])
        r._cho_sang_map = MagicMock(return_value=sk.MAP_TO_CHAU)
        return r

    def _chang(self):
        return sk.Chang(sk.MAP_DAI_LY, sk.NPC_DI_CHUYEN, sk.XY_DI_CHUYEN_DAI_LY,
                        ((111116, 8888), (111116, 1002)), sk.MAP_TO_CHAU)

    def test_rot_theo_thi_moi_lai_roi_moi_dich_chuyen(self):
        r = self._runner([["cosato12", "cosato13"], []])
        with patch.object(sk.time, "sleep"):
            r._qua_chang(self._chang())
        self.assertEqual(r._cho_tat_ca_theo_truoc_khi_di.call_count, 2)
        self.assertEqual(r._chon.call_count, 1)
        self.assertTrue(any("rớt Theo đội" in c.args[0] for c in r.in_log.call_args_list))
        r._cho_doi_vien_toi_map.assert_called_once_with(sk.MAP_TO_CHAU)

    def test_ca_doi_con_theo_thi_dich_chuyen_ngay(self):
        r = self._runner([[]])
        with patch.object(sk.time, "sleep"):
            r._qua_chang(self._chang())
        self.assertEqual(r._cho_tat_ca_theo_truoc_khi_di.call_count, 1)
        r._chon.assert_called_once_with((111116, 8888))

    def test_rot_mai_thi_khong_dich_chuyen_mot_minh(self):
        r = self._runner([["cosato12"]] * sk.SO_LAN_THU)
        with patch.object(sk.time, "sleep"):
            with self.assertRaises(sk.LoiAcTac):
                r._qua_chang(self._chang())
        r._chon.assert_not_called()


class TestKhongDanhSatTinhKhiMapCu(unittest.TestCase):
    """Vòng chính chạy luồng Ác Tặc thì map_hien_tai còn «Lôi đài» cũ: luồng đánh không được coi NPC Đại Lý là Sát Tinh."""

    def _luong(self, map_cu, map_that, dang_ac_tac=False):
        luong = gd.LuongNhanVat.__new__(gd.LuongNhanVat)
        luong.ten = "cosato10"
        luong.map_hien_tai = map_cu
        luong.da_noi = luong.dang_trong_game = True
        luong.dang_ac_tac = dang_ac_tac
        luong.game = MagicMock()
        luong.game.thong_tin.return_value = {"map": map_that}
        luong._bo_theo_de_danh_sat_tinh = MagicMock()
        chien_dau = MagicMock()
        npc = MagicMock(hp=100, ten="Vệ Binh", x=160, y=158)
        chien_dau._doc_quanh_minh.return_value = MagicMock(cac_quai=[npc], vi_tri=(160, 157))
        return luong, chien_dau

    def test_da_ve_dai_ly_ma_map_cu_la_loi_dai(self):
        luong, cd = self._luong(gd.MAP_SAT_TINH, "Đại Lý")
        luong._cap_nhat_danh_npc_do_sat_tinh(cd)
        self.assertFalse(luong.danh_npc_do_sat_tinh)
        luong._bo_theo_de_danh_sat_tinh.assert_not_called()
        cd._doc_quanh_minh.assert_not_called()

    def test_dang_di_ac_tac_thi_khong_danh_sat_tinh(self):
        luong, cd = self._luong(gd.MAP_SAT_TINH, gd.MAP_SAT_TINH, dang_ac_tac=True)
        luong._cap_nhat_danh_npc_do_sat_tinh(cd)
        self.assertFalse(luong.danh_npc_do_sat_tinh)
        luong._bo_theo_de_danh_sat_tinh.assert_not_called()

    def test_that_trong_loi_dai_van_danh(self):
        luong, cd = self._luong(gd.MAP_SAT_TINH, gd.MAP_SAT_TINH)
        luong._cap_nhat_danh_npc_do_sat_tinh(cd)
        self.assertTrue(luong.danh_npc_do_sat_tinh)
        luong._bo_theo_de_danh_sat_tinh.assert_called_once()


class TestChoDoiGanNpcDiChuyen(unittest.TestCase):
    """Cả đội đang theo ở Đại Lý: đội trưởng chờ 2 đội viên tới cạnh NPC Di Chuyển rồi mới chọn dịch chuyển."""

    NPC = (165, 156)

    def _runner(self, vi_tri_dv, vi_tri_truong=(165, 156)):
        r = sk.AcTacRunner.__new__(sk.AcTacRunner)
        r.ten, r.la_truong, r.in_log = "cosato11", True, MagicMock()
        r.trang_thai = {}
        r.nen_dung = lambda: False
        r.het_khung = float("inf")
        r.dang_ket_thuc = False
        r._map = lambda: "Đại Lý"
        r._tt = lambda: {"map": "Đại Lý", "x": vi_tri_truong[0], "y": vi_tri_truong[1]}
        r._trieu_at_state = {}
        r.game = MagicMock()
        r._moi_theo_doi = MagicMock()
        doi = MagicMock()
        doi.cac_doi_vien = {}
        for ten, (m, x, y) in vi_tri_dv.items():
            luong = MagicMock()
            luong.game.thong_tin.return_value = {"map": m, "x": x, "y": y}
            doi.cac_doi_vien[ten] = luong
        r.doi_at = doi
        return r

    def test_ca_doi_gan_npc_thi_di(self):
        r = self._runner({"cosato22": ("Đại Lý", 164, 157), "cosato33": ("Đại Lý", 166, 155)})
        r._cho_doi_gan_npc("Di Chuyển", self.NPC)
        r._moi_theo_doi.assert_not_called()
        self.assertIn("cả đội đã tới cạnh Di Chuyển", r.in_log.call_args[0][0])

    def test_doi_vien_con_o_cho_gom_thi_khong_dich_chuyen(self):
        r = self._runner({"cosato22": ("Đại Lý", 164, 157), "cosato33": ("Đại Lý", 140, 157)})
        with patch.object(sk.time, "sleep"), patch.object(sk.time, "time", side_effect=itertools.count(0, 20)):
            with self.assertRaises(sk.LoiAcTac) as cm:
                r._cho_doi_gan_npc("Di Chuyển", self.NPC)
        self.assertIn("cosato33 chưa tới cạnh Di Chuyển", str(cm.exception))
        self.assertNotIn("cosato22", str(cm.exception))
        r._moi_theo_doi.assert_called()

    def test_truong_xa_npc_thi_chay_toi_truoc(self):
        r = self._runner({"cosato22": ("Đại Lý", 164, 157)}, vi_tri_truong=(150, 157))
        with patch.object(sk.time, "sleep"), patch.object(sk.time, "time", side_effect=itertools.count(0, 20)):
            with self.assertRaises(sk.LoiAcTac) as cm:
                r._cho_doi_gan_npc("Di Chuyển", self.NPC)
        self.assertIn("đội trưởng chưa tới cạnh", str(cm.exception))
        self.assertIn("AutoRunToTarget(165, 156)", r.game.lua.chay.call_args[0][0])

    def test_qua_chang_npc_cho_doi_gan_truoc_khi_mo_npc(self):
        r = self._runner({"cosato22": ("Đại Lý", 164, 157)})
        thu_tu = []
        r._cho_tat_ca_theo_truoc_khi_di = lambda: thu_tu.append("theo")
        r._cho_doi_gan_npc = lambda ten, xy: thu_tu.append(("gan_npc", ten, xy))

        def mo_npc(ten, xy):
            thu_tu.append("mo_npc")
            raise sk.LoiAcTac("dừng test")

        r._mo_npc = mo_npc
        r._dong_hoi_thoai = MagicMock()
        r._log = MagicMock()
        r._mo_ta = MagicMock()
        chang = sk.Chang("Đại Lý", "Di Chuyển", self.NPC, ((111116, 5555),), "Kiếm Các")
        with self.assertRaises(sk.LoiAcTac):
            r._qua_chang(chang)
        self.assertEqual(thu_tu[:3], ["theo", ("gan_npc", "Di Chuyển", self.NPC), "mo_npc"])


class TestChoDoiVienTaiXongDaiLy(unittest.TestCase):
    """Về thành cả đội: chỉ bấm Theo đội khi mọi đội viên đã qua màn chuyển cảnh (đọc được Đại Lý + máu ổn định)."""

    def _runner(self, cac_tt):
        r = sk.AcTacRunner.__new__(sk.AcTacRunner)
        r.ten, r.la_truong, r.in_log = "cosato144", True, MagicMock()
        r.trang_thai = {}
        r.nen_dung = lambda: False
        r.het_khung = float("inf")
        r.dang_ket_thuc = False
        r._map = lambda: "Đại Lý"
        r._goi_doi_vien_ve_thanh = lambda bat_buoc=False: []
        r._cho_tat_ca_theo_truoc_khi_di = MagicMock()
        doi = MagicMock()
        doi.cac_doi_vien = {}
        for ten, tt in cac_tt.items():
            luong = MagicMock()
            if isinstance(tt, Exception):
                luong.game.thong_tin.side_effect = tt
            else:
                luong.game.thong_tin.return_value = tt
            doi.cac_doi_vien[ten] = luong
        doi.map_doi_vien.side_effect = lambda: {t: "Đại Lý" for t in cac_tt}
        r.doi_at = doi
        return r

    DA_TAI = {"map": "Đại Lý", "x": 160, "y": 157, "hp": 1000, "hp_toi_da": 1000}

    def test_da_tai_xong_thi_bo_theo_cu_roi_moi_theo(self):
        r = self._runner({"cosato155": dict(self.DA_TAI), "cosato166": dict(self.DA_TAI)})
        with patch.object(sk.time, "sleep"), patch.object(sk.time, "time", side_effect=itertools.count(0, 1)):
            r._gom_doi_dai_ly()
        for luong in r.doi_at.cac_doi_vien.values():
            luong.game.lua.chay.assert_any_call(sk.MA_BO_THEO_DOI)
        r._cho_tat_ca_theo_truoc_khi_di.assert_called_once()
        self.assertIn("tải xong, mời Theo đội", r.in_log.call_args[0][0])

    def test_con_chuyen_canh_thi_chua_moi_theo(self):
        dang_tai = {"map": "Đại Lý", "x": 0, "y": 0, "hp": 0, "hp_toi_da": 0}
        r = self._runner({"cosato155": dict(self.DA_TAI), "cosato166": dang_tai})
        with patch.object(sk.time, "sleep"), patch.object(sk.time, "time", side_effect=itertools.count(0, 5)):
            with self.assertRaises(sk.LoiAcTac) as cm:
                r._gom_doi_dai_ly()
        self.assertIn("cosato166 chưa tải xong Đại Lý", str(cm.exception))
        self.assertNotIn("cosato155", str(cm.exception))
        r._cho_tat_ca_theo_truoc_khi_di.assert_not_called()

    def test_lua_khong_tra_loi_tinh_la_dang_tai(self):
        r = self._runner({"cosato166": sk.LoiLua("Game không phản hồi (đang loading hoặc bị treo?)")})
        with patch.object(sk.time, "sleep"), patch.object(sk.time, "time", side_effect=itertools.count(0, 5)):
            with self.assertRaises(sk.LoiAcTac):
                r._gom_doi_dai_ly()
        r._cho_tat_ca_theo_truoc_khi_di.assert_not_called()

    def test_vua_doc_duoc_thi_cho_on_dinh_moi_tinh_xong(self):
        r = self._runner({"cosato155": dict(self.DA_TAI)})
        luc = {}
        self.assertEqual(r._doi_vien_chua_tai_xong("Đại Lý", luc, 100), ["cosato155"])
        self.assertEqual(r._doi_vien_chua_tai_xong("Đại Lý", luc, 100 + sk.GIAY_DOI_VIEN_TAI_XONG), [])


class TestDiThangTuThanhTrungChuyen(unittest.TestCase):
    """Có đội: luôn về Đại Lý gom rồi mới đi. Một mình ở hub: vẫn đi thẳng Tung Sơn / Đôn Hoàng."""

    def _di(self, map_hien, ten_map, co_doi=True):
        r = sk.AcTacRunner.__new__(sk.AcTacRunner)
        r.ten, r.la_truong, r.in_log = "caychay32", True, MagicMock()
        doi = MagicMock()
        doi.cac_doi_vien = {"a": MagicMock()} if co_doi else {}
        r.doi_at = doi
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

    def test_co_doi_o_lac_duong_ve_dai_ly_truoc_tung_son(self):
        self.assertEqual(self._di("Lạc Dương", "Tung Sơn"),
                         ["ve_dai_ly", "gom_dai_ly", ("Đại Lý", "Lạc Dương"), ("Lạc Dương", "Tung Sơn")])

    def test_co_doi_o_lac_duong_ve_dai_ly_truoc_don_hoang(self):
        self.assertEqual(self._di("Lạc Dương", "Đôn Hoàng"),
                         ["ve_dai_ly", "gom_dai_ly", ("Đại Lý", "Lạc Dương"), ("Lạc Dương", "Đôn Hoàng")])

    def test_mot_minh_lac_duong_di_thang_tung_son(self):
        self.assertEqual(self._di("Lạc Dương", "Tung Sơn", co_doi=False),
                         ["gom_tai_cho", ("Lạc Dương", "Tung Sơn")])

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
