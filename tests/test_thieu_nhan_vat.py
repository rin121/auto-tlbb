"""XV-21: sổ ghi đã tạo nhân vật nhưng tài khoản không có (bị xóa / server reset) thì xoay vòng tạo lại rồi đăng nhập."""
import os
import queue
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dang_nhap  # noqa: E402
import nhan_vat_moi  # noqa: E402
import xoay_vong as xv  # noqa: E402


class TestLamBuocThieuNhanVat(unittest.TestCase):
    def _lam(self, cac_ten, so_giay, tao_khi_thieu=True):
        luong = dang_nhap.LuongDangNhap({"ten_dang_nhap": "caychay30", "mat_khau": "x", "nhan_vat": "caychay30"},
                                        {}, queue.Queue())
        luong.tao_khi_thieu = tao_khi_thieu
        lua = MagicMock()
        with patch.object(dang_nhap, "ds_ten_nhan_vat", return_value=cac_ten), \
                patch.object(luong, "kiem_tra_ds_nhan_vat"):
            return luong.lam_buoc(lua, "chon_nhan_vat", so_giay), lua

    def test_danh_sach_khong_co_ten_thi_bao_thieu(self):
        with self.assertRaises(dang_nhap.LoiThieuNhanVat) as ng:
            self._lam(["caychay3"], 1)
        self.assertEqual(ng.exception.cac_ten, ["caychay3"])

    def test_danh_sach_trong_cho_du_lau_moi_bao_thieu(self):
        da_lam, lua = self._lam([], dang_nhap.GIAY_DS_NHAN_VAT_TRONG - 1)
        self.assertFalse(da_lam)
        lua.chay.assert_not_called()
        with self.assertRaises(dang_nhap.LoiThieuNhanVat) as ng:
            self._lam([], dang_nhap.GIAY_DS_NHAN_VAT_TRONG)
        self.assertEqual(ng.exception.cac_ten, [])

    def test_co_nhan_vat_thi_vao_game(self):
        da_lam, lua = self._lam(["khac", "CayChay30"], 1)
        self.assertTrue(da_lam)
        lua.chay.assert_called_once_with("GameProduceLogin:SendEnterGameMsg(1)")

    def test_khong_bat_tao_khi_thieu_thi_cho_nhu_cu(self):
        da_lam, _ = self._lam([], 100, tao_khi_thieu=False)
        self.assertFalse(da_lam)
        with self.assertRaises(dang_nhap.LoiDangNhap) as ng:
            self._lam(["caychay3"], 100, tao_khi_thieu=False)
        self.assertNotIsInstance(ng.exception, dang_nhap.LoiThieuNhanVat)

    def test_luong_vao_nhan_vat_xoay_vong_bat_tao_khi_thieu(self):
        tk = {"ten_dang_nhap": "caychay30", "mat_khau": "x", "nhan_vat": "caychay30"}
        self.assertTrue(xv.LuongVaoNhanVat(tk, {}, queue.Queue()).tao_khi_thieu)
        self.assertFalse(xv.LuongVaoNhanVat(tk, {}, queue.Queue(), kiem_tra_rule_ten=False).tao_khi_thieu)


class TestDongBoDaXong(unittest.TestCase):
    def setUp(self):
        self.cai_dat = {"tao_nhan_vat_moi": {
            "da_xong": {"caychay30": ["caychay30", "caychay300", "caychay3000"], "khac": ["khac"]},
            "ten_thuc": {"caychay30": {"caychay300": "caychay300a"}}}}
        self.luu = MagicMock()
        p1 = patch.object(nhan_vat_moi.cau_hinh, "doc_tai_khoan", return_value=self.cai_dat)
        p2 = patch.object(nhan_vat_moi.cau_hinh, "luu_tai_khoan", self.luu)
        p1.start()
        p2.start()
        self.addCleanup(p1.stop)
        self.addCleanup(p2.stop)

    def test_khong_con_nhan_vat_nao_thi_xoa_het(self):
        bo = nhan_vat_moi.dong_bo_da_xong("CayChay30", [])
        self.assertEqual(bo, ["caychay30", "caychay300", "caychay3000"])
        tao = self.cai_dat["tao_nhan_vat_moi"]
        self.assertEqual(tao["da_xong"]["caychay30"], [])
        self.assertEqual(tao["ten_thuc"]["caychay30"], {})
        self.assertEqual(tao["da_xong"]["khac"], ["khac"])
        self.luu.assert_called_once()

    def test_chi_bo_ten_khong_con(self):
        bo = nhan_vat_moi.dong_bo_da_xong("caychay30", ["CayChay30", "caychay300a"])
        self.assertEqual(bo, ["caychay300", "caychay3000"])
        tao = self.cai_dat["tao_nhan_vat_moi"]
        self.assertEqual(tao["da_xong"]["caychay30"], ["caychay30"])
        self.assertEqual(tao["ten_thuc"]["caychay30"], {"caychay300": "caychay300a"})

    def test_du_het_thi_khong_luu(self):
        nhan_vat_moi.dong_bo_da_xong("caychay30", ["caychay30", "caychay300", "caychay3000", "caychay300a"])
        self.luu.assert_not_called()


class _LuongGia:
    """Luồng đăng nhập / tạo nhân vật giả, chạy xong ngay."""

    def __init__(self, thanh_cong=True, thieu=None, pid=0):
        self.thanh_cong, self.thieu_nhan_vat, self.pid = thanh_cong, thieu, pid
        self.game = MagicMock() if thanh_cong else None
        self.sai_rule = None
        self.sai_tai_khoan = False
        self.dung = MagicMock()

    def start(self):
        pass

    def is_alive(self):
        return False


class TestXoayVongTaoKhiThieu(unittest.TestCase):
    def _nhom(self):
        ds = []
        for i, ten in ((30, "caychay30"), (31, "caychay31")):
            tv = xv.ThanhVien({"ten_dang_nhap": f"caychay{i}", "mat_khau": "x"})
            tv.ten, tv.hwnd = ten, i
            ds.append(tv)
        return ds

    def test_thieu_nhan_vat_thi_tao_roi_dang_nhap_lai(self):
        nhom = self._nhom()
        luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, False, False)
        lan_vao = []

        def vao(tk, cai_dat, hang_doi, hwnd=None, **k):
            lan_vao.append(tk["ten_dang_nhap"])
            if tk["ten_dang_nhap"] == "caychay30" and lan_vao.count("caychay30") == 1:
                return _LuongGia(False, thieu=[], pid=300)
            return _LuongGia()

        tao = MagicMock(side_effect=lambda *a, **k: _LuongGia(pid=300))
        with patch.object(xv, "LuongVaoNhanVat", vao), patch.object(xv, "LuongTaoNhanVat", tao), \
                patch.object(xv.cau_hinh, "doc_tai_khoan", return_value={}), \
                patch.object(xv, "tim_cua_so_game", return_value=[{"hwnd": 30, "pid": 300}]), \
                patch.object(xv, "con_chay", return_value=True), \
                patch.object(xv, "ten_round", lambda tk, r: tk + "0" * r), \
                patch.object(xv, "cac_ten_nhan_vat", lambda tk, n: [tk + "0" * r for r in range(n)]), \
                patch.object(luong, "_gan_game"), patch.object(luong, "_nha_client"):
            con = luong._dang_nhap(nhom)
        self.assertEqual([tv.ten for tv in con], ["caychay30", "caychay31"])
        self.assertEqual(lan_vao, ["caychay30", "caychay31", "caychay30"])
        tao.assert_called_once()
        self.assertEqual(tao.call_args[0][0], [nhom[0].tai_khoan])
        self.assertEqual(tao.call_args[0][2], {"so_nhan_vat": 1, "nhan_do_tan_thu": True, "dung_ten": True})
        self.assertEqual(tao.call_args[1]["hwnd"], 30)
        self.assertTrue(tao.call_args[1]["giu_game"])
        self.assertEqual(luong.cac_luong_con, [])

    def test_round_sau_tao_du_nhan_vat_toi_round(self):
        tv = self._nhom()[0]
        tv.ten = "caychay3000"
        luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, False, False)
        tao = MagicMock(side_effect=lambda *a, **k: _LuongGia(pid=300))
        with patch.object(xv, "LuongTaoNhanVat", tao), \
                patch.object(xv.cau_hinh, "doc_tai_khoan", return_value={}), \
                patch.object(xv, "tim_cua_so_game", return_value=[]), \
                patch.object(xv, "con_chay", return_value=True), \
                patch.object(xv, "ten_round", lambda tk, r: tk + "0" * r), \
                patch.object(xv, "cac_ten_nhan_vat", lambda tk, n: [tk + "0" * r for r in range(n)]):
            luong._tao_nhan_vat_thieu([(tv, _LuongGia(False, thieu=[]))])
        self.assertEqual(tao.call_args[0][2]["so_nhan_vat"], 3)


if __name__ == "__main__":
    unittest.main()
