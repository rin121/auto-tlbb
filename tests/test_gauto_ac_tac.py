import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gauto_ac_tac as g  # noqa: E402


class TestTenDong(unittest.TestCase):
    def test_bo_hau_to_server(self):
        self.assertEqual(g.ten_tu_dong_gauto("caychay10 (TL/123)"), "caychay10")
        self.assertEqual(g.ten_tu_dong_gauto("GaoDẻLâu (TL/144)"), "GaoDẻLâu")
        self.assertEqual(g.ten_tu_dong_gauto("caychay28"), "caychay28")

    def test_khop_ten_khong_phan_biet_hoa_thuong(self):
        self.assertTrue(g._khop_ten("CayChay10", "caychay10"))
        self.assertFalse(g._khop_ten("caychay10", "caychay100"))

    def test_nhan_dien_cua_so_quan_ly(self):
        self.assertTrue(g.la_cua_so_quan_ly_gauto("GAuto TLBB-2.5.3.3 | 0,0 GG"))
        self.assertTrue(g.la_cua_so_quan_ly_gauto("ChickenAuto (ver.116)"))
        self.assertFalse(g.la_cua_so_quan_ly_gauto("caychay10 - ChickenAuto"))


class TestDatCaiDatAcTac(unittest.TestCase):
    """Bật Ác Tặc GAuto theo tùy chọn AutoHoc: đặt các ô phụ trước, tích «Ác Tặc» sau cùng."""

    O = {ten: i for i, ten in enumerate(g.CAC_O_KHUNG_AC_TAC, 1)} | {"map": 99}

    def setUp(self):
        self.dang_cai = "caychay10"
        for p in (patch.object(g, "kiem_tra_quyen", lambda h: None),
                  patch.object(g, "bo_tich_dong_khac", return_value=[]),
                  patch.object(g, "nhan_vat_dang_cai", lambda h: self.dang_cai)):
            p.start()
            self.addCleanup(p.stop)

    def test_gauto_doi_nhan_vat_giua_chung_thi_khong_tich(self):
        da_dat = []

        def dat(h, bat, ten):
            da_dat.append((ten, bat))
            self.dang_cai = "caychay255"
        with patch.object(g, "_chon_nhan_vat", return_value=dict(self.O)), patch.object(g, "dat_o", dat), \
                patch.object(g, "doc_map", return_value="Kiếm Các"):
            with self.assertRaises(g.LoiGautoAcTac):
                g.dat_cai_dat_ac_tac(1, {}, "caychay10")
        self.assertNotIn((g.O_AC_TAC, True), da_dat)

    def _chay(self, at):
        da_dat = []
        with patch.object(g, "_chon_nhan_vat", return_value=dict(self.O)), \
                patch.object(g, "dat_o", lambda h, bat, ten: da_dat.append((ten, bat))), \
                patch.object(g, "doc_map", return_value="Kiếm Các"):
            ten_map = g.dat_cai_dat_ac_tac(1, at, "caychay10")
        return da_dat, ten_map

    def test_chay_tim_mac_dinh(self):
        da_dat, ten_map = self._chay({})
        self.assertEqual(dict(da_dat), {g.O_CHAY_PATHPOINTS: False, g.O_CHAY_TIM: True, g.O_CHO_PARTY: True,
                                        g.O_TU_TIM: True, g.O_AC_TAC: True})
        self.assertEqual(da_dat[-1], (g.O_AC_TAC, True))
        self.assertEqual(ten_map, "Kiếm Các")

    def test_chay_pathpoints_tat_chay_tim(self):
        da_dat, _ = self._chay({"chay_pathpoints": True, "cho_party": False, "tu_tim": False})
        self.assertEqual(dict(da_dat), {g.O_CHAY_PATHPOINTS: True, g.O_CHAY_TIM: False, g.O_CHO_PARTY: False,
                                        g.O_TU_TIM: False, g.O_AC_TAC: True})

    def test_chon_map_autohoc_truoc_khi_tich(self):
        thu_tu = []
        with patch.object(g, "_chon_nhan_vat", return_value=dict(self.O)), \
                patch.object(g, "chon_map", lambda h, cb, ten: thu_tu.append(("map", ten))), \
                patch.object(g, "dat_o", lambda h, bat, ten: thu_tu.append((ten, bat))), \
                patch.object(g, "doc_map", return_value="Kiếm Các"):
            g.dat_cai_dat_ac_tac(1, {}, "caychay10", ten_map="Kiếm Các")
        self.assertEqual(thu_tu[0], ("map", "Kiếm Các"))
        self.assertEqual(thu_tu[-1], (g.O_AC_TAC, True))

    def test_vi_tri_map_so_khong_dau(self):
        cac = ["Đôn Hoàng", "Kiếm Các", "Thái Hồ", "Tung Sơn", "Vô Lượng Sơn", "Kính Hồ"]
        self.assertEqual(g.vi_tri_map(cac, "kiem cac"), 1)
        self.assertEqual(g.vi_tri_map(cac, "Vô Lượng Sơn"), 4)
        self.assertIsNone(g.vi_tri_map(cac, "Tây Hồ"))

    def test_thieu_o_ac_tac_thi_bao_loi(self):
        with patch.object(g, "_chon_nhan_vat", return_value={g.O_CHAY_TIM: 1}), \
                patch.object(g, "dat_o", lambda *a: None), patch.object(g, "doc_map", return_value=""):
            with self.assertRaises(g.LoiGautoAcTac):
                g.dat_cai_dat_ac_tac(1, {}, "caychay10")


class _BangGia:
    """Bảng nhân vật GAuto giả qua MSAA: dòng 1..n, chọn dòng thì GAuto đổi tab cài đặt sau so_lan_cho lần đọc."""

    def __init__(self, ten_dong, dang_chon, dang_cai, so_lan_cho=0):
        self.ten_dong, self.chon_id, self.dang_cai = ten_dong, dang_chon, dang_cai
        self.so_lan_cho, self.so_lan_chon = so_lan_cho, 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def ten(self, i):
        return f"{self.ten_dong[i - 1]} (TL/120)"

    def dang_chon(self, i):
        return self.chon_id == i

    def chon(self, i):
        self.chon_id = i
        self.so_lan_chon += 1

    def doc_dang_cai(self):
        if self.so_lan_cho:
            self.so_lan_cho -= 1
            return self.dang_cai
        if self.chon_id:
            self.dang_cai = self.ten_dong[self.chon_id - 1]
        return self.dang_cai


class TestChonDongDungNhanVat(unittest.TestCase):
    """GA-04: dòng hiện «đang chọn» chưa đủ — chờ tab cài đặt GAuto đúng tên đội trưởng mới coi là đã chọn."""

    def _chon(self, bang, id_dong, ten):
        with patch.object(g, "_bang_nhan_vat", lambda h: 0), patch.object(g, "_msaa", lambda h: bang), \
                patch.object(g, "nhan_vat_dang_cai", lambda h: bang.doc_dang_cai()), \
                patch.object(g, "GIAY_CHO_DOI_NHAN_VAT", 0):
            g.chon_dong(1, id_dong, ten)

    def test_dong_dang_chon_nhung_gauto_cai_nhan_vat_khac_thi_chon_lai(self):
        bang = _BangGia(["caychay255", "caychay244"], dang_chon=2, dang_cai="caychay255", so_lan_cho=1)
        self._chon(bang, 2, "caychay244")
        self.assertEqual(bang.so_lan_chon, 1)
        self.assertEqual(bang.dang_cai, "caychay244")

    def test_da_dung_nhan_vat_thi_khong_bam(self):
        bang = _BangGia(["caychay255", "caychay244"], dang_chon=2, dang_cai="caychay244")
        self._chon(bang, 2, "caychay244")
        self.assertEqual(bang.so_lan_chon, 0)

    def test_dong_doi_ten_thi_bao_loi(self):
        bang = _BangGia(["caychay255", "caychay266"], dang_chon=1, dang_cai="caychay255")
        with self.assertRaises(g.LoiGautoAcTac):
            self._chon(bang, 2, "caychay244")


class TestBoTichDongKhac(unittest.TestCase):
    """GA-04: chỉ đội trưởng đang login được tích Ác Tặc; dòng khác đang tích thì bỏ."""

    def test_bo_tich_cac_dong_khac_doi_truong(self):
        tich = {"caychay255": True, "caychay244": True, "caychay266": False, "caychay24": True}
        dang = ["caychay255"]
        ds = [(i, t, False, False) for i, t in enumerate(tich, 1)]

        def chon(h, i, ten):
            dang[0] = ten
        with patch.object(g, "danh_sach_nhan_vat", return_value=ds), patch.object(g, "chon_dong", chon), \
                patch.object(g, "khung_ac_tac", lambda h: {g.O_AC_TAC: dang[0]}), \
                patch.object(g, "da_tich", lambda o: tich[o]), \
                patch.object(g, "nhan_vat_dang_cai", lambda h: dang[0]), \
                patch.object(g, "dat_o", lambda o, bat, ten: tich.__setitem__(dang[0], bat)):
            da_bo = g.bo_tich_dong_khac(1, "caychay244")
        self.assertEqual(da_bo, ["caychay255", "caychay24"])
        self.assertEqual(tich, {"caychay255": False, "caychay244": True, "caychay266": False, "caychay24": False})


class TestQuyenAdmin(unittest.TestCase):
    def test_gauto_admin_autohoc_thuong_thi_bao_can_admin(self):
        with patch.object(g, "gauto_la_admin", return_value=True), patch.object(g, "autohoc_la_admin", return_value=False):
            with self.assertRaises(g.LoiGautoAcTac) as ctx:
                g.kiem_tra_quyen(1)
        self.assertEqual(str(ctx.exception), g.THONG_BAO_CAN_ADMIN)

    def test_cung_quyen_thi_qua(self):
        with patch.object(g, "gauto_la_admin", return_value=True), patch.object(g, "autohoc_la_admin", return_value=True):
            g.kiem_tra_quyen(1)


if __name__ == "__main__":
    unittest.main()
