import os
import queue
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import xoay_vong as xv  # noqa: E402

TK = [{"ten_dang_nhap": f"caychay{i}", "mat_khau": "x", "bat": True} for i in (32, 34, 35)]


def _cua_so(*hwnd):
    return [{"hwnd": h, "pid": h * 10, "tieu_de": ""} for h in hwnd]


class _Game:
    """Game giả: hwnd -> (tên nhân vật, tài khoản, PT trong game)."""
    DU_LIEU = {}

    def __init__(self, hwnd):
        self.ten, self.tk, self.pt = self.DU_LIEU[hwnd]
        self.lua = MagicMock(pid=hwnd * 10, pt=self.pt)

    def thong_tin(self):
        if not self.ten:
            return None
        return {"ten": self.ten, "tai_khoan": self.tk}


def _doc_nhom(lua):
    return {"thanh_vien": lua.pt}


class TestNhomDangOnline(unittest.TestCase):
    def _chay(self, du_lieu, giu=()):
        _Game.DU_LIEU = du_lieu
        with patch.object(xv, "tim_cua_so_game", return_value=_cua_so(*du_lieu)), \
                patch.object(xv, "Game", _Game), patch.object(xv, "doc_nhom", _doc_nhom), \
                patch.object(xv, "hwnd_giu_khi_xoay_vong", return_value=set(giu)), \
                patch.object(xv.cau_hinh, "tai_khoan_pho_ban", return_value=TK):
            return xv.nhom_dang_online()

    def test_truong_pt_trong_game_dung_dau(self):
        pt = ["GaoDẻLâu", "caychay32", "caychay34"]
        nhom = self._chay({1: ("caychay32", "caychay32", pt), 2: ("caychay35", "caychay35", []),
                           3: ("GaoDẻLâu", "gaode", pt), 4: ("caychay34", "caychay34", pt)})
        self.assertEqual([tv.ten for tv in nhom], ["GaoDẻLâu", "caychay32", "caychay34", "caychay35"])
        self.assertIs(nhom[1].tai_khoan, TK[0])
        self.assertEqual(nhom[0].tai_khoan, {"ten_dang_nhap": "gaode"})
        self.assertEqual(nhom[0].hwnd, 3)

    def test_khong_co_pt_thi_theo_so_tai_khoan(self):
        nhom = self._chay({1: ("caychay35", "caychay35", []), 2: ("caychay32", "caychay32", [])})
        self.assertEqual([tv.ten for tv in nhom], ["caychay32", "caychay35"])

    def test_bo_acc_chinh_va_game_chua_vao(self):
        nhom = self._chay({1: ("caychay32", "caychay32", []), 2: ("", "", []), 3: ("AccChinh", "chinh", [])},
                          giu={3})
        self.assertEqual([tv.ten for tv in nhom], ["caychay32"])

    def test_toi_da_6_nguoi(self):
        du_lieu = {i: (f"caychay{i}", f"caychay{i}", []) for i in range(1, 9)}
        self.assertEqual(len(self._chay(du_lieu)), xv.SO_NGUOI_MOT_NHOM_TOI_DA)


class TestLuongNhomOnline(unittest.TestCase):
    def _nhom(self):
        ds = []
        for tk, ten in ((TK[0], "caychay32"), (TK[1], "caychay34")):
            tv = xv.ThanhVien(tk)
            tv.ten, tv.hwnd, tv.game = ten, 1, MagicMock()
            ds.append(tv)
        return ds

    def test_che_do_test_khong_chay_lai_ngay_moi(self):
        nhom = self._nhom()
        luong = xv.LuongXoayVong(queue.Queue(), 3, False, True, True, False, nhom_online=nhom)
        self.assertTrue(luong.che_do_test)
        self.assertFalse(luong.chay_lai_ngay_moi)
        self.assertEqual(luong.ds_tai_khoan, [TK[0], TK[1]])

    def test_chay_mot_round_khong_dang_nhap(self):
        nhom = self._nhom()
        luong = xv.LuongXoayVong(queue.Queue(), 1, True, True, False, False, nhom_online=nhom)
        luong._di_round = MagicMock(return_value=nhom)
        luong._dang_nhap = MagicMock()
        luong._mot_luot = MagicMock()
        with patch.object(xv.cau_hinh, "chung", return_value={k: None for k in xv.KHOA_CHUNG_NHOM}), \
                patch.object(xv.cau_hinh, "dat_chung"):
            luong._chay()
        luong._di_round.assert_called_once()
        self.assertIs(luong._di_round.call_args[0][1], nhom)
        luong._dang_nhap.assert_not_called()
        luong._mot_luot.assert_not_called()
        self.assertEqual(luong.so_round_da_chay, 1)


class TestBatDauLaiKhiNhomDangOnline(unittest.TestCase):
    """Dừng rồi Bắt đầu lại xoay vòng: nhóm đang trong game còn lượt thì đi tiếp, không đăng xuất / đăng nhập lại."""

    DS = [{"ten_dang_nhap": f"caychay{i}"} for i in (10, 11, 12, 13, 14)]

    @staticmethod
    def _ten(tk, r):
        return tk + tk[-1] * r

    def test_chon_round_cua_nhom_dang_online(self):
        online = ["caychay111", "caychay122", "caychay133", "caychay10", "nguoi_ngoai"]
        r, tk = xv.chon_round_online(self.DS, online, 3, da_xong=lambda ten: False, ten_cua=self._ten)
        self.assertEqual(r, 1)
        self.assertEqual([t["ten_dang_nhap"] for t in tk], ["caychay11", "caychay12", "caychay13"])

    def test_het_luot_thi_khong_tinh(self):
        online = ["caychay111", "caychay122", "caychay10"]
        r, tk = xv.chon_round_online(self.DS, online, 3, da_xong=lambda ten: ten != "caychay10",
                                     ten_cua=self._ten)
        self.assertEqual((r, [t["ten_dang_nhap"] for t in tk]), (0, ["caychay10"]))
        self.assertEqual(xv.chon_round_online(self.DS, online, 3, da_xong=lambda ten: True, ten_cua=self._ten),
                         (None, []))

    def test_khong_ai_online(self):
        self.assertEqual(xv.chon_round_online(self.DS, [], 3, da_xong=lambda t: False, ten_cua=self._ten),
                         (None, []))

    def test_dua_len_dau_hang(self):
        a, b, c, d = self.DS[:4]
        hang = [a, b, c]
        xv.dua_len_dau_hang(hang, [c, d])
        self.assertEqual(hang, [c, d, a, b])

    def test_tien_trinh_nho_round_dang_do(self):
        ds = self.DS
        luu = {}
        with patch.object(xv.cau_hinh, "dat_chung", lambda d: luu.update(d)), \
                patch.object(xv.cau_hinh, "chung", lambda: luu):
            hang_cho = [[ds[4]], [ds[3], ds[4]], list(ds)]
            xv.luu_xv_tien_trinh(3, hang_cho, False, False, 3,
                                 dang_round={"r": 1, "thanh_vien": ["caychay11", "caychay12"]})
            tt = xv.doc_xv_tien_trinh(ds, False, False, 3)
        self.assertEqual(tt["r_dang"], 1)
        self.assertEqual(tt["so_nhom"], 3)
        self.assertEqual([t["ten_dang_nhap"] for t in tt["hang_cho"][1]],
                         ["caychay11", "caychay12", "caychay13", "caychay14"])


class TestXepLaiDangNhapLoi(unittest.TestCase):
    """XV-14: đăng nhập lỗi (mã kiểm tra, game treo...) thì xếp lại cuối hàng chờ, không bỏ hẳn cả ngày."""

    DS = [{"ten_dang_nhap": f"caychay{i}"} for i in (48, 49, 50, 69)]

    def test_xep_cuoi_hang_va_gioi_han_so_lan(self):
        a, b, c, d = self.DS
        hang, thu_lai = [d], {}
        self.assertEqual(xv.xep_lai_dang_nhap_loi(hang, [a, b], 0, thu_lai), [a, b])
        self.assertEqual(hang, [d, a, b])
        for _ in range(xv.SO_LAN_XEP_LAI_DANG_NHAP):
            hang.clear()
            xv.xep_lai_dang_nhap_loi(hang, [a], 0, thu_lai)
        self.assertEqual(hang, [])
        self.assertEqual(thu_lai["caychay48|0"], xv.SO_LAN_XEP_LAI_DANG_NHAP)
        self.assertEqual(xv.xep_lai_dang_nhap_loi(hang, [a], 1, thu_lai), [a])

    def test_da_trong_hang_thi_khong_them(self):
        a = self.DS[0]
        hang, thu_lai = [a], {}
        self.assertEqual(xv.xep_lai_dang_nhap_loi(hang, [a], 0, thu_lai), [])
        self.assertEqual(hang, [a])
        self.assertEqual(thu_lai, {})

    def test_luong_xep_lai_sau_round(self):
        luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, False, False)
        a, b, c, d = self.DS
        luong._xv_ds_map = xv._map_tk_theo_ten(self.DS)
        luong.tk_sai_rule = {"caychay50"}
        luong._bo_dang_nhap = [xv.ThanhVien(a), xv.ThanhVien(c)]
        hang_cho = [[d], [], []]
        with patch.object(xv, "ten_round", lambda tk, r: tk):
            luong._xep_lai_dang_nhap_loi(hang_cho, 0)
        self.assertEqual(hang_cho[0], [d, a])
        self.assertEqual(luong._bo_dang_nhap, [])

    def test_tien_trinh_nho_so_lan_thu_lai(self):
        luu = {}
        with patch.object(xv.cau_hinh, "dat_chung", lambda d: luu.update(d)), \
                patch.object(xv.cau_hinh, "chung", lambda: luu):
            xv.luu_xv_tien_trinh(2, [list(self.DS), [], []], False, False, 3, thu_lai={"caychay48|0": 1})
            tt = xv.doc_xv_tien_trinh(self.DS, False, False, 3)
        self.assertEqual(tt["thu_lai"], {"caychay48|0": 1})


if __name__ == "__main__":
    unittest.main()
