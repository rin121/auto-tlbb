import os
import sys
import unittest
from contextlib import nullcontext
from unittest.mock import MagicMock, patch

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
                  patch.object(g, "dat_dau_dong", return_value=[]),
                  patch.object(g, "nhan_vat_dang_cai", lambda h: self.dang_cai)):
            p.start()
            self.addCleanup(p.stop)

    def test_gauto_doi_nhan_vat_giua_chung_thi_khong_tich(self):
        da_dat = []

        def dat(h, o, bat, ten):
            da_dat.append((ten, bat))
            self.dang_cai = "caychay255"
        with patch.object(g, "_chon_nhan_vat", return_value=dict(self.O)), patch.object(g, "dat_o_chuot", dat), \
                patch.object(g, "doc_map", return_value="Kiếm Các"):
            with self.assertRaises(g.LoiGautoAcTac):
                g.dat_cai_dat_ac_tac(1, {}, "caychay10")
        self.assertNotIn((g.O_AC_TAC, True), da_dat)

    def _chay(self, at):
        da_dat = []
        with patch.object(g, "_chon_nhan_vat", return_value=dict(self.O)), \
                patch.object(g, "dat_o_chuot", lambda h, o, bat, ten: da_dat.append((ten, bat))), \
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
                patch.object(g, "dat_o_chuot", lambda h, o, bat, ten: thu_tu.append((ten, bat))), \
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
                patch.object(g, "dat_o_chuot", lambda *a: None), patch.object(g, "doc_map", return_value=""):
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


class _BangTich:
    """Bảng GAuto giả: bấm chuột vào ô đầu dòng thì đảo trạng thái tích dòng đó."""

    def __init__(self, tich):
        self.ten_dong, self.tich = list(tich), dict(tich)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def vi_tri(self, i):
        return (100, 200 + 17 * (i - 1), 300, 17)

    def da_tich(self, i):
        return self.tich[self.ten_dong[i - 1]]

    def bam(self, diem):
        i = (diem[1] - 200) // 17 + 1
        self.x_bam = diem[0]
        ten = self.ten_dong[i - 1]
        self.tich[ten] = not self.tich[ten]

    def ds(self, h):
        return [(i, t, False, self.tich[t]) for i, t in enumerate(self.ten_dong, 1)]


class TestDauDong(unittest.TestCase):
    """GA-06: chỉ dòng trưởng nhóm: tích ô đầu dòng + «Ác Tặc» 1 lần lúc bật, bỏ tích 1 lần lúc tắt."""

    def _dat(self, bang, cac_ten, bat):
        with patch.object(g, "danh_sach_nhan_vat", bang.ds), patch.object(g, "_bang_nhan_vat", lambda h: 0), \
                patch.object(g, "_msaa", lambda h: bang), patch.object(g, "_muon_chuot", lambda h, v: nullcontext()), \
                patch.object(g, "_bam_chuot", lambda h, diem, cho: bang.bam(diem)):
            return g.dat_dau_dong(1, cac_ten, bat)

    def test_tich_doi_truong_va_doi_vien(self):
        bang = _BangTich({"caychay2888": False, "caychay2999": True, "caychay3111": False, "khac": False})
        da = self._dat(bang, ("caychay2888", "caychay2999", "caychay3111"), True)
        self.assertEqual(da, ["caychay2888", "caychay3111"])
        self.assertEqual(bang.tich, {"caychay2888": True, "caychay2999": True, "caychay3111": True, "khac": False})
        self.assertLess(bang.x_bam, 100 + 30)

    def test_bo_tich(self):
        bang = _BangTich({"caychay2888": True, "caychay2999": True})
        self.assertEqual(self._dat(bang, ["caychay2888"], False), ["caychay2888"])
        self.assertEqual(bang.tich, {"caychay2888": False, "caychay2999": True})

    def _bat_tat(self, da_tich_dau_dong, doc_ac_tac=None):
        """
        Bật rồi tắt Ác Tặc; ghi lại mọi lần bấm vào GAuto theo thứ tự. doc_ac_tac: các lần đọc ô «Ác Tặc» lúc canh
        GAuto nạp lại (mặc định luôn ☑).
        """
        cache, thu_tu = {}, []
        doc = list(doc_ac_tac or [])

        def dau_dong(h, ten, bat):
            thu_tu.append(("dau_dong", tuple(ten), bat))
            return [] if da_tich_dau_dong else list(ten)
        with patch.object(g, "kiem_tra_quyen", lambda h: None), \
                patch.object(g, "_chon_nhan_vat", lambda h, t, c: thu_tu.append(("chon", t)) or {g.O_AC_TAC: 1}), \
                patch.object(g, "_dam_bao_dang_cai", lambda h, t: None), \
                patch.object(g, "dat_o_chuot", lambda h, o, bat, ten: thu_tu.append((ten, bat))), \
                patch.object(g, "da_tich", lambda o: doc.pop(0) if doc else True), \
                patch.object(g, "GIAY_CANH_NAP_LAI", 1.5), \
                patch.object(g, "dat_dau_dong", dau_dong), patch.object(g, "GIAY_CHO_GAUTO_NAP", 0):
            g.dat_cai_dat_ac_tac(1, {}, "caychay32", cache=cache)
            bat = list(thu_tu)
            thu_tu.clear()
            g.tat_ac_tac(1, "caychay32", cache=cache)
        return bat, thu_tu, cache

    def test_chi_dong_truong_nhom_tich_mot_lan_bat_mot_lan_tat(self):
        bat, tat, cache = self._bat_tat(da_tich_dau_dong=False)
        # Ô đầu dòng chỉ của trưởng nhóm, tích trước (GAuto nạp lại cài đặt), «Ác Tặc» tích đúng 1 lần sau cùng.
        self.assertEqual(bat[0], ("dau_dong", ("caychay32",), True))
        self.assertEqual(bat[-1], (g.O_AC_TAC, True))
        self.assertEqual(bat.count((g.O_AC_TAC, True)), 1)
        self.assertEqual({t for _, t in [x for x in bat if x[0] == "chon"]}, {"caychay32"})
        self.assertEqual(tat, [("dau_dong", ("caychay32",), False), ("chon", "caychay32"), (g.O_AC_TAC, False)])
        self.assertNotIn("dau_dong", cache)

    def test_gauto_nap_lai_xoa_o_ac_tac_thi_tich_lai_mot_lan(self):
        bat, _, _ = self._bat_tat(da_tich_dau_dong=False, doc_ac_tac=[True, False, False])
        self.assertEqual(bat.count((g.O_AC_TAC, True)), 2)
        self.assertEqual(bat[-1], (g.O_AC_TAC, True))

    def test_o_dau_dong_da_tich_san_thi_khong_canh_nap_lai(self):
        bat, _, _ = self._bat_tat(da_tich_dau_dong=True, doc_ac_tac=[False, False])
        self.assertEqual(bat.count((g.O_AC_TAC, True)), 1)

    def test_dau_dong_da_tich_san_thi_khong_bo_tich(self):
        _, tat, _ = self._bat_tat(da_tich_dau_dong=True)
        self.assertEqual(tat, [("chon", "caychay32"), (g.O_AC_TAC, False)])

    def test_loi_sau_khi_bam_danh_dau_da_thao_tac(self):
        with patch.object(g, "kiem_tra_quyen", lambda h: None), patch.object(g, "dat_dau_dong", return_value=[]), \
                patch.object(g, "_chon_nhan_vat", return_value={g.O_CHAY_TIM: 1}), \
                patch.object(g, "_dam_bao_dang_cai", lambda h, t: None), patch.object(g, "dat_o_chuot"):
            with self.assertRaises(g.LoiGautoAcTac) as ng:
                g.dat_cai_dat_ac_tac(1, {}, "caychay32")
        self.assertTrue(ng.exception.da_thao_tac)

    def test_loi_quyen_thi_chua_thao_tac(self):
        with patch.object(g, "kiem_tra_quyen", side_effect=g.LoiGautoAcTac(g.THONG_BAO_CAN_ADMIN)):
            with self.assertRaises(g.LoiGautoAcTac) as ng:
                g.dat_cai_dat_ac_tac(1, {}, "caychay32")
        self.assertFalse(getattr(ng.exception, "da_thao_tac", False))


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
