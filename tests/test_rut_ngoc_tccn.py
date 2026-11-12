"""Rút ngọc từ Thiên Cơ Cẩm Nang: quy đổi viên → mảnh, rút từng lần ≤ 250, túi đầy thì cất Thương khố rồi rút tiếp."""
import os
import queue
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import giao_acc_chinh as gac  # noqa: E402
import rut_ngoc_tccn as rn  # noqa: E402


class TestQuyDoi(unittest.TestCase):
    def test_vien_ra_manh(self):
        self.assertEqual(rn.MANH_MOT_VIEN, 500)
        self.assertEqual(rn.so_manh_can(3), 1500)
        self.assertEqual(rn.so_manh_can(0), 0)
        self.assertEqual(rn.so_manh_can(-2), 0)
        self.assertEqual(rn.so_manh_can("x"), 0)

    def test_so_moi_lan_rut(self):
        self.assertEqual(rn.so_manh_lan_rut(1500), 250)
        self.assertEqual(rn.so_manh_lan_rut(120), 120)
        self.assertEqual(rn.so_manh_lan_rut(1500, trong_o=80), 80)
        # Thiên Cơ không có bảng số lượng (đọc ra 1): vẫn nhập 250, không rút từng mảnh.
        self.assertEqual(rn.so_manh_lan_rut(1500, trong_o=1), 250)

    def test_mo_ta(self):
        self.assertEqual(rn.mo_ta_manh(1000), "1000 mảnh (2 viên)")
        self.assertEqual(rn.mo_ta_manh(750), "750 mảnh (1 viên + 250 mảnh)")

    def test_nhan_manh_ngoc(self):
        self.assertTrue(rn.la_manh_ngoc("Mảnh Ngọc Vip"))
        self.assertTrue(rn.la_manh_ngoc("#cFF0000Mảnh Ngọc"))
        self.assertTrue(rn.la_manh_ngoc("manh ngoc"))
        self.assertFalse(rn.la_manh_ngoc("Mảnh Vỡ Trân Thú"))
        self.assertFalse(rn.la_manh_ngoc("Phiếu KNB 100"))

    def test_lenh_rut_co_so_luong(self):
        ma = rn.ma_rut_tccn(3, 120)
        self.assertIn("setupvalue(sel, i, 120)", ma)
        self.assertIn("sel(3)", ma)
        self.assertNotIn("{so}", ma)
        self.assertNotIn("{i}", ma)
        # Gộp đồ vẫn rút 250 như cũ.
        self.assertIn("setupvalue(sel, i, 250)", gac.MA_RUT_TCCN)
        self.assertIn("sel({i})", gac.MA_RUT_TCCN)


class _GameGia:
    """Thiên Cơ có `tccn` mảnh; túi chứa tối đa `suc_chua` mảnh; cất rương dời hết mảnh trong túi sang rương."""

    def __init__(self, tccn, suc_chua=10 ** 9, ruong_day=False):
        self.tccn, self.tui, self.ruong = tccn, 0, 0
        self.suc_chua, self.ruong_day = suc_chua, ruong_day
        self.cac_lan_rut = []
        self.so_lan_cat = 0


def _luong(game_gia, so_vien):
    r = rn.LuongRutNgoc(queue.Queue(), MagicMock(), "GaoDẻLâu", so_vien)
    r._o_ngoc_tccn = lambda: [(1, "Mảnh Ngọc Vip", game_gia.tccn)] if game_gia.tccn else []
    r._tong_ngoc_tui = lambda: game_gia.tui

    def rut(chi_so, so):
        game_gia.cac_lan_rut.append(so)
        lay = max(0, min(so, game_gia.tccn, game_gia.suc_chua - game_gia.tui))
        game_gia.tccn -= lay
        game_gia.tui += lay

    def cat_ruong():
        game_gia.so_lan_cat += 1
        if not game_gia.ruong_day:
            game_gia.ruong += game_gia.tui
            game_gia.tui = 0

    r._rut_mot_lan = rut
    r._cat_ruong = cat_ruong
    r._o_trong = lambda: {"base": 0 if game_gia.tui >= game_gia.suc_chua else 5, "material": 0}
    return r


class TestLuongRutNgoc(unittest.TestCase):
    def setUp(self):
        for p in (patch.object(rn, "GIAY_GIUA_RUT_TCCN", 0), patch.object(rn, "LAN_CHO_TUI", 0)):
            p.start()
            self.addCleanup(p.stop)

    def test_rut_du_so_vien(self):
        g = _GameGia(tccn=5000)
        r = _luong(g, 2)
        r._chay()
        self.assertEqual(r.da_rut, 1000)
        self.assertEqual(g.cac_lan_rut, [250, 250, 250, 250])
        self.assertEqual(g.tccn, 4000)
        self.assertEqual(g.so_lan_cat, 0)

    def test_lan_cuoi_chi_rut_phan_con_thieu(self):
        g = _GameGia(tccn=5000)
        r = _luong(g, 1)
        r.can = 620
        r._chay()
        self.assertEqual(g.cac_lan_rut, [250, 250, 120])
        self.assertEqual(r.da_rut, 620)

    def test_tui_day_thi_cat_ruong_roi_rut_tiep(self):
        g = _GameGia(tccn=5000, suc_chua=600)
        r = _luong(g, 2)
        r._chay()
        self.assertEqual(r.da_rut, 1000)
        self.assertGreaterEqual(g.so_lan_cat, 1)
        self.assertEqual(g.ruong + g.tui, 1000)

    def test_cat_roi_van_khong_rut_duoc_thi_dung(self):
        g = _GameGia(tccn=5000, suc_chua=500, ruong_day=True)
        r = _luong(g, 2)
        with self.assertRaises(gac.LoiGiaoAccChinh):
            r._chay()
        self.assertEqual(r.da_rut, 500)

    def test_thien_co_het_ngoc_thi_xong_som(self):
        g = _GameGia(tccn=300)
        r = _luong(g, 2)
        r._chay()
        self.assertEqual(r.da_rut, 300)
        trang_thai = [m for m in list(r.hang_doi.queue) if m[0] == "trang_thai_rut_ngoc"]
        self.assertTrue(trang_thai[-1][1].startswith("Xong"))

    def test_dung_giua_chung(self):
        g = _GameGia(tccn=5000)
        r = _luong(g, 2)
        r.dung.set()
        with self.assertRaises(gac._Dung):
            r._chay()
        self.assertEqual(g.cac_lan_rut, [])

    def test_so_vien_khong_hop_le(self):
        r = _luong(_GameGia(tccn=5000), 0)
        with self.assertRaises(gac.LoiGiaoAccChinh):
            r._chay()

    def test_dieu_khien_dung_pid_nhan_vat(self):
        r = _luong(_GameGia(tccn=0), 1)
        r.chinh.lua.pid = 123
        with patch.object(r, "is_alive", return_value=True):
            self.assertTrue(r.dang_dieu_khien(123))
            self.assertFalse(r.dang_dieu_khien(456))


class TestCatRuong(unittest.TestCase):
    def _r(self, tui):
        r = rn.LuongRutNgoc(queue.Queue(), MagicMock(), "GaoDẻLâu", 1)
        r._ve_dai_ly = MagicMock()
        r._chay_toi = MagicMock()
        r._tui_chinh = lambda: tui
        r._cat_kho = MagicMock(return_value=False)
        r._o_trong = lambda: {"base": 3, "material": 3}
        return r

    def test_chi_cat_o_manh_ngoc(self):
        r = self._r({("base", 0): (1, 1, "Thuốc"), ("material", 2): (2, 250, "Mảnh Ngọc Vip"),
                     ("material", 5): (2, 250, "Mảnh Ngọc Vip")})
        r._cat_ruong()
        r._ve_dai_ly.assert_called_once()
        r._chay_toi.assert_called_once_with(r.chinh, "GaoDẻLâu", rn.NPC_TAN_THU[1])
        r._cat_kho.assert_called_once_with(cac_o=[("material", 2), ("material", 5)])

    def test_khong_co_manh_ngoc_thi_cat_moi_o(self):
        r = self._r({("base", 0): (1, 1, "Thuốc")})
        r._cat_ruong()
        r._cat_kho.assert_called_once_with(cat_het=True)

    def test_tui_va_ruong_deu_day_thi_dung(self):
        r = self._r({("base", 0): (1, 1, "Thuốc")})
        r._cat_kho.return_value = True
        r._o_trong = lambda: {"base": 0, "material": 0}
        with self.assertRaises(gac.LoiGiaoAccChinh):
            r._cat_ruong()


class TestCatKhoChiO(unittest.TestCase):
    def test_cat_kho_chi_cac_o_chon(self):
        e = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        e.chinh = MagicMock()
        e.chinh.lua.chay.return_value = b"10"
        e._tui_chinh = MagicMock()
        e._mo_kho = lambda: True
        e._cat_mot_o = MagicMock(return_value="1")
        e.in_log = MagicMock()
        self.assertFalse(e._cat_kho(cac_o=[("material", 2)]))
        e._tui_chinh.assert_not_called()
        e._cat_mot_o.assert_called_once()
        self.assertIn('"material", 2', e._cat_mot_o.call_args[0][1])


if __name__ == "__main__":
    unittest.main()
