import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, THU_MUC)

import giao_dich  # noqa: E402
import nang_cap_vip as vip  # noqa: E402


def _o(ma, so, bat_dau, so_o):
    return {("base", bat_dau + i): (ma, so, "m") for i in range(so_o)}


class TestManh(unittest.TestCase):
    def test_khoa_ten_va_ma(self):
        self.assertEqual(vip.khoa_tu_ten("#-09Mảnh Vỡ Trang Bị"), "trang bi")
        self.assertEqual(vip.khoa_tu_ten("Mảnh Vỡ Thú Cưỡi"), "thu cuoi")
        self.assertEqual(vip.khoa_tu_ten("Mảnh Vỡ Thời Trang"), "thoi trang")
        self.assertEqual(vip.khoa_tu_ten("30503234"), "trang bi")
        self.assertIsNone(vip.khoa_tu_ten("Mảnh Vỡ Trang Bị VIP"))

    def test_du_thi_rut_phan_tui_con_thieu(self):
        tui = {"trang bi": 1000, "thu cuoi": 500, "thoi trang": 0}
        tccn = {"trang bi": 9000, "thu cuoi": 0, "thoi trang": 500}
        rut, thieu = vip.phan_manh(tui, tccn)
        self.assertEqual(thieu, {})
        self.assertEqual(rut, {"trang bi": 4000, "thoi trang": 500})

    def test_thieu_mot_loai_thi_khong_coi_la_du(self):
        tui = {"trang bi": 0, "thu cuoi": 0, "thoi trang": 0}
        tccn = {"trang bi": 5000, "thu cuoi": 100, "thoi trang": 500}
        _, thieu = vip.phan_manh(tui, tccn)
        self.assertEqual(thieu, {"thu cuoi": 400})
        self.assertIn("Thú Cưỡi", vip.mo_ta_thieu(thieu))

    def test_tui_da_du_thi_khong_rut(self):
        tui = {m["khoa"]: m["so"] for m in vip.MANH}
        rut, thieu = vip.phan_manh(tui, {m["khoa"]: 0 for m in vip.MANH})
        self.assertEqual(rut, {})
        self.assertEqual(thieu, {})

    def test_mot_buoc_khong_ke_loai_khac(self):
        tui = {m["khoa"]: 0 for m in vip.MANH}
        tccn = {"trang bi": 5000, "thu cuoi": 0, "thoi trang": 0}
        rut, thieu = vip.phan_manh(tui, tccn, "trang bi")
        self.assertEqual(thieu, {})
        self.assertEqual(rut, {"trang bi": 5000})
        _, thieu_thu = vip.phan_manh(tui, tccn, "thu cuoi")
        self.assertEqual(thieu_thu, {"thu cuoi": 500})

    def test_o_tung_buoc(self):
        self.assertEqual(vip.so_o_can(5000), 25)
        self.assertEqual(vip.so_lan_giao(25), 5)
        self.assertEqual(vip.so_o_can(500), 3)
        self.assertEqual(vip.so_lan_giao(3), 1)

    def test_lag_rut_khong_dung(self):
        self.assertEqual(vip.ket_luan_rut(0, 250, 5000, 4750), "xong")
        self.assertEqual(vip.ket_luan_rut(0, 0, 5000, 4750), "cho")
        self.assertEqual(vip.ket_luan_rut(0, 0, 5000, None), "cho")
        self.assertEqual(vip.ket_luan_rut(0, 0, 5000, 5000), "rut_lai")
        self.assertEqual(vip.ket_luan_doi(True, 5000, 4500), "xong")
        self.assertEqual(vip.ket_luan_doi(False, 5000, 4500), "cho")
        self.assertEqual(vip.ket_luan_doi(False, 5000, None), "cho")
        self.assertEqual(vip.ket_luan_doi(False, None, 5000), "cho")
        self.assertEqual(vip.ket_luan_doi(False, 5000, 5000), "doi_lai")
        self.assertEqual(vip.ket_luan_giao(None), "xong")
        self.assertEqual(vip.ket_luan_giao(giao_dich.LoiGiaoDich("đã dừng")), "dung")
        self.assertEqual(
            vip.ket_luan_giao(giao_dich.LoiGiaoDich("cosato3 không nhận được lời mời giao dịch")),
            "gui_lai")
        self.assertEqual(vip.ket_luan_giao(giao_dich.LoiGiaoDich("cửa sổ giao dịch không mở")), "loi")
        self.assertEqual(vip.buoc_chon(["thoi trang", "trang bi", "khac"]), ["trang bi", "thoi trang"])
        self.assertEqual(vip.buoc_chon(()), [])

    def test_mon_mot_buoc(self):
        con = vip.mon_chua_co(set(), "thu cuoi")
        self.assertEqual([ma for _, _, ma, _ in con], [10165078])
        self.assertEqual(vip.mo_ta_bang({"trang bi"}), "Level 2 · Kim Vương")
        self.assertEqual(vip.mo_ta_bang(vip.KHOA_BUOC), "Đã VIP")
        self.assertEqual(vip.so_o_can(5000) + vip.so_o_can(500) + vip.so_o_can(500), 31)
        self.assertEqual(vip.so_lan_giao(31), 7)
        tui = {}
        tui.update(_o(30503234, 200, 0, 25))
        tui.update(_o(30503264, 200, 25, 2))
        tui[("base", 27)] = (30503264, 100, "thu")
        tui.update(_o(30503263, 200, 28, 2))
        tui[("base", 30)] = (30503263, 100, "tt")
        tui[("base", 40)] = (30503234, 200, "du")
        cac_o = vip.o_can_giao(tui, {30503234: 5000, 30503264: 500, 30503263: 500})
        self.assertEqual(len(cac_o), 31)
        self.assertNotIn(("base", 40), cac_o)
        self.assertEqual(vip.so_lan_giao(len(cac_o)), 7)


class TestDoiVaVut(unittest.TestCase):
    def test_mon_chua_co_bo_mon_da_co(self):
        co = {10162460, 10163082}
        con = vip.mon_chua_co(co)
        self.assertFalse(any(ma in co for _, _, ma, _ in con))
        self.assertEqual(len(con), len(vip.MON) - 2)

    def test_chi_vut_mon_roi_khoi_nguoi(self):
        truoc = {0: 10162570, 1: 10162450, 4: 10162451, 8: 10158130, 11: 10162427}
        sau = {0: 10162570, 1: 10162460, 4: 10162461, 8: 10165078, 11: 10162427, 16: 10163082}
        self.assertEqual(vip.ma_vua_thao(truoc, sau), {10162450, 10162451, 10158130})

    def test_xac_nhan_gio_giao_dich(self):
        ma = giao_dich.ma_xac_nhan_exchange_safe("15:45")
        self.assertIn("ExchangeSafe_Confirm", ma)
        self.assertIn("15:45", ma)
        self.assertIn('IsWindowShow("ExchangeSafe")', ma)


class TestUngVien(unittest.TestCase):
    def _tk(self, login, ten=""):
        return {"ten_dang_nhap": login, "mat_khau": "x", "nhan_vat": ten, "bat": True}

    def test_bang_chon_an_chua_level_2_va_acc_chinh(self):
        ds = [self._tk("chinh", "Gao"), self._tk("a", "cosato777"), self._tk("b", "chua"),
              self._tk("c", "roi")]
        da_lv2 = {"cosato777", "roi", "Gao"}
        da_vip = {"roi"}

        def ten_round(tk, r):
            goc = {"a": "cosato777", "b": "chua", "c": "roi", "chinh": "Gao"}[tk]
            return goc if r == 0 else f"{goc}{r}"

        with patch.object(vip, "ten_round", side_effect=ten_round):
            hang = vip.dong_bang(ds, "Gao", "chinh", lambda t: t in da_lv2, lambda t: t in da_vip)
        self.assertEqual([(ten, trang) for _, ten, trang, _xong in hang],
                         [("cosato777", "level2"), ("roi", "vip")])
        self.assertEqual(hang[0][3], frozenset())
        self.assertEqual(hang[1][3], frozenset(vip.KHOA_BUOC))
        ds = [self._tk("chinh", "Gao"), self._tk("a", "cosato777"), self._tk("b", "chua"),
              self._tk("c", "roi")]
        da_lv2 = {"cosato777", "roi"}
        da_vip = {"roi"}
        kq = vip.ung_vien(ds, "Gao", "chinh", lambda t: t in da_lv2, lambda t: t in da_vip)
        self.assertEqual([ten for _, ten in kq], ["cosato777"])

    def test_moi_tai_khoan_ba_nhan_vat(self):
        with patch.object(vip, "ten_round", side_effect=lambda tk, r: f"{tk}{tk[-1] * r}"):
            hang = vip.dong_bang(
                [self._tk("cosato1", "cosato1")], "Gao", "kduy121",
                lambda t: t in {"cosato1", "cosato11", "cosato111"}, lambda t: t == "cosato11")
        self.assertEqual([(ten, trang) for _, ten, trang, _ in hang],
                         [("cosato1", "level2"), ("cosato11", "vip"), ("cosato111", "level2")])

    def test_trong_ten_thi_lay_round_da_xong(self):
        with patch.object(vip, "ten_round", side_effect=lambda tk, r: f"{tk}-{r}"):
            kq = vip.ung_vien(
                [self._tk("phu", "")], "Gao", "chinh",
                lambda t: t == "phu-1", lambda t: False)
        self.assertEqual([ten for _, ten in kq], ["phu-1"])


class TestDanhDau(unittest.TestCase):
    def setUp(self):
        self.thu_muc = tempfile.mkdtemp()
        self.file = os.path.join(self.thu_muc, "vip.json")

    def tearDown(self):
        shutil.rmtree(self.thu_muc, ignore_errors=True)

    def test_nhan_roi_khong_rut_lai_den_khi_xong(self):
        self.assertFalse(vip.da_nhan_manh("cosato777", self.file))
        vip.danh_dau_nhan("cosato777", self.file)
        self.assertTrue(vip.da_nhan_manh("Cosato777", self.file))
        self.assertFalse(vip.da_xong("cosato777", self.file))
        vip.danh_dau_thao("cosato777", [10162450, 10158130], self.file)
        self.assertEqual(vip.ma_thao_da_ghi("cosato777", self.file), {10162450, 10158130})
        vip.danh_dau_xong("cosato777", self.file)
        self.assertTrue(vip.da_xong("cosato777", self.file))
        self.assertEqual(vip.ma_thao_da_ghi("cosato777", self.file), {10162450, 10158130})
        self.assertTrue(all(vip.da_xong_buoc("cosato777", k, self.file) for k in vip.KHOA_BUOC))

    def test_tung_buoc_roi_moi_xong(self):
        vip.danh_dau_nhan_buoc("cosato7", "trang bi", self.file)
        self.assertTrue(vip.da_nhan_buoc("cosato7", "trang bi", self.file))
        self.assertFalse(vip.da_nhan_buoc("cosato7", "thu cuoi", self.file))
        self.assertFalse(vip.da_xong_buoc("cosato7", "trang bi", self.file))
        vip.danh_dau_buoc("cosato7", "trang bi", self.file)
        self.assertTrue(vip.da_xong_buoc("cosato7", "trang bi", self.file))
        self.assertFalse(vip.da_xong("cosato7", self.file))
        self.assertEqual(vip.mo_ta_bang(vip.buoc_da_xong("cosato7", self.file)), "Level 2 · Kim Vương")
        vip.danh_dau_buoc("cosato7", "thu cuoi", self.file)
        vip.danh_dau_buoc("cosato7", "thoi trang", self.file)
        self.assertTrue(vip.da_xong("cosato7", self.file))

    def test_dang_nhap_san_thi_giu_va_lam_truoc(self):
        self.assertEqual(
            vip.sap_uu_tien_dang_online(
                [("a", "cosato3"), ("b", "cosato33"), ("c", "cosato14")],
                ["cosato14"]),
            [("a", "cosato3"), ("b", "cosato33"), ("c", "cosato14")])
        luong = vip.LuongNangCapVip.__new__(vip.LuongNangCapVip)
        luong.ten_giu_online = {vip.chuan_hoa("GaoDẻLâu")}
        with patch.object(vip, "tim_hwnd_theo_nhan_vat", side_effect=lambda ten, gan_tk=None: 5 if ten == "cosato2" else None):
            dang = luong._giu_nhan_vat_dang_online([("a", "cosato1"), ("b", "cosato2")])
        self.assertEqual(dang, ["cosato2"])
        self.assertIn(vip.chuan_hoa("cosato2"), luong.ten_giu_online)
        self.assertNotIn(vip.chuan_hoa("cosato1"), luong.ten_giu_online)

    def test_chon_client_dung_nhan_vat_dang_mo(self):
        luong = vip.LuongNangCapVip.__new__(vip.LuongNangCapVip)
        luong.chinh = type("C", (), {"lua": type("L", (), {"hwnd": 10})()})()
        luong.ten_giu_online = set()
        luong.hwnd_truong = None
        da_giu = []
        luong._thoat_cac_client = lambda giu=(): da_giu.append(set(giu))
        luong._cac_hwnd_giu = lambda *them: {h for h in them if h}
        with patch.object(vip, "tim_hwnd_theo_nhan_vat", return_value=22):
            hwnd = luong._chon_game_truong({"ten_dang_nhap": "cosato2"}, "cosato2")
        self.assertEqual(hwnd, 22)
        self.assertIn(22, da_giu[0])
        self.assertIn(10, da_giu[0])

    def test_khong_lay_client_nhan_vat_khac_dang_giu(self):
        luong = vip.LuongNangCapVip.__new__(vip.LuongNangCapVip)
        luong.chinh = type("C", (), {"lua": type("L", (), {"hwnd": 10})()})()
        luong.ten_giu_online = set()
        luong.hwnd_truong = None
        luong._hwnd_giu_xoay_vong = lambda: set()
        luong._cac_hwnd_giu = lambda *them: {10, 33}
        luong._hwnd_dll_san = lambda h: h
        luong._thoat_cac_client = lambda giu=(): None
        with patch.object(vip, "tim_hwnd_theo_nhan_vat", return_value=None), \
                patch.object(vip, "tim_game_cua_tai_khoan", return_value=33), \
                patch.object(vip, "tim_cua_so_game", return_value=[{"hwnd": 10}, {"hwnd": 33}, {"hwnd": 44}]):
            hwnd = luong._chon_game_truong({"ten_dang_nhap": "cosato1"}, "cosato1")
        self.assertEqual(hwnd, 44)

    def test_nhan_cu_la_da_giao_ca_ba(self):
        vip.danh_dau_nhan("cosato8", self.file)
        self.assertTrue(all(vip.da_nhan_buoc("cosato8", k, self.file) for k in vip.KHOA_BUOC))
        self.assertFalse(vip.da_xong("cosato8", self.file))


if __name__ == "__main__":
    unittest.main()
