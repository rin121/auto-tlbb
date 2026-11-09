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

    def test_ten_online_trung_nhieu_round_uu_tien_round_cao(self):
        """cosato11 online khớp cả round 1 và 2 (cùng tên hiển thị) — phải chọn round cao, không round 1."""
        ds = [{"ten_dang_nhap": f"cosato{i}"} for i in (11, 22, 33, 44)]

        def ten_cua(tk, r):
            return tk if r < 2 else tk + tk[-1] * r

        online = ["cosato11", "cosato22", "cosato33", "cosato44"]
        r, tk = xv.chon_round_online(ds, online, 3, da_xong=lambda ten: False, ten_cua=ten_cua)
        self.assertEqual(r, 1)
        self.assertEqual([t["ten_dang_nhap"] for t in tk], ["cosato11", "cosato22", "cosato33", "cosato44"])

    def test_cap_nhat_hwnd_khi_process_con_song(self):
        luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, True, False)
        tv = xv.ThanhVien({"ten_dang_nhap": "caychay10", "mat_khau": "x"})
        tv.ten, tv.hwnd = "caychay10", 999
        tv.game = MagicMock()
        tv.game.lua.pid = 42
        with patch.object(xv, "con_chay", return_value=True), \
                patch("xoay_vong.win32gui.IsWindow", side_effect=lambda h: h == 1000), \
                patch.object(xv, "tim_hwnd_chinh_game_pid", return_value=1000), \
                patch.object(xv, "Game", side_effect=lambda h: MagicMock(lua=MagicMock(pid=42, hwnd=h))):
            self.assertTrue(luong._cap_nhat_hwnd_tv(tv))
        self.assertEqual(tv.hwnd, 1000)

        luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, True, False)
        luong.in_log = MagicMock()
        tv = xv.ThanhVien({"ten_dang_nhap": "caychay10", "mat_khau": "x"})
        tv.ten, tv.hwnd = "caychay10", 999
        game = MagicMock()
        game.lua.hwnd = 999
        luong_ok = MagicMock(thanh_cong=True, game=game, sai_rule=None, sai_tai_khoan=None, pid=1)
        with patch.object(luong, "_gan_game"), \
                patch.object(luong, "_chay_luong_vao", return_value=[(tv, luong_ok)]):
            con = luong._dang_nhap([tv])
        self.assertEqual(con, [tv])

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


class TestDungGiuaRoundThiDiTiepDungNhom(unittest.TestCase):
    """XV: Dừng lúc nhóm đang ở round 3 rồi Bắt đầu lại → đi tiếp round 3 của nhóm đó, không mở nhóm mới từ round 1."""

    DS = [{"ten_dang_nhap": f"anhzero{i}"} for i in (57, 58, 59, 60, 61, 62)]

    def test_dung_luu_round_dang_do(self):
        luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, False, False)
        a57, a58, a59, a60, a61, a62 = self.DS
        luong._xv_ds_map = xv._map_tk_theo_ten(self.DS)
        luong._xv_hang_cho = [[a60, a61, a62], [a60, a61, a62], [a60, a61, a62]]
        luong._xv_so_nhom = 9
        luong._xv_thu_lai = {}
        luong._xv_dang_round = {"r": 2, "thanh_vien": ["anhzero57", "anhzero58", "anhzero59"]}
        luu = {}
        with patch.object(xv.cau_hinh, "dat_chung", lambda d: luu.update(d)), \
                patch.object(xv.cau_hinh, "chung", lambda: luu):
            luong._luu_xv_tien_trinh_neu_can()
            tt = xv.doc_xv_tien_trinh(self.DS, False, False, 3)
        self.assertEqual(tt["r_dang"], 2)
        self.assertEqual(tt["so_nhom"], 9)
        self.assertEqual([t["ten_dang_nhap"] for t in tt["hang_cho"][2]][:3],
                         ["anhzero57", "anhzero58", "anhzero59"])

    def test_round_sau_uu_tien_dung_nhom(self):
        luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, False, False)
        a57, a58, a59, a60, a61, a62 = self.DS
        nhom = [xv.ThanhVien(a60), xv.ThanhVien(a61), xv.ThanhVien(a62)]
        hang_cho = [[], [], [a57, a58, a59, a60, a61, a62]]
        with patch.object(xv, "da_xong_hom_nay", return_value=False):
            choi = luong._lay_thanh_vien_nhom(hang_cho, 2, nhom, 3)
        self.assertEqual([tv.tk for tv in choi], ["anhzero60", "anhzero61", "anhzero62"])
        self.assertEqual([t["ten_dang_nhap"] for t in hang_cho[2]], ["anhzero57", "anhzero58", "anhzero59"])

    def test_nhom_thieu_nguoi_thi_bu_tu_dau_hang(self):
        luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, False, False)
        a57, a58, a59, a60, a61, a62 = self.DS
        nhom = [xv.ThanhVien(a60), xv.ThanhVien(a61), xv.ThanhVien(a62)]
        hang_cho = [[], [], [a57, a60, a61]]
        tv_map = {tv.tk.lower(): tv for tv in nhom}
        with patch.object(xv, "da_xong_hom_nay", return_value=False), \
                patch.object(luong, "_loai_neu_trung_ten_nv", return_value=False):
            choi = luong._lay_thanh_vien_nhom(hang_cho, 2, nhom, 3)
            luong._them_acc_tu_hang_cho(hang_cho, 2, choi, 3, tv_map)
        self.assertEqual([tv.tk for tv in choi], ["anhzero60", "anhzero61", "anhzero57"])


class TestTuNhom1KhongGiuNhomOnline(unittest.TestCase):
    """XV-20: qua 0h / Làm mới danh sách / Chạy lại từ đầu thì đi từ nhóm 1 round 1, không giữ nhóm đang online."""

    DS = [{"ten_dang_nhap": f"caychay{i}"} for i in (14, 16, 24, 25)]

    def _mot_luot(self, tu_nhom_1):
        with patch.object(xv, "cac_tai_khoan_dang_tich", return_value=list(self.DS)):
            luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, True, True, tu_nhom_1=tu_nhom_1)
        online = MagicMock(return_value=(1, [self.DS[2], self.DS[3]]))
        with patch.object(xv.cau_hinh, "dat_chung", lambda d: None), \
                patch.object(xv, "so_nguoi_mot_nhom", return_value=2), \
                patch.object(xv, "da_xong_hom_nay", return_value=False), \
                patch.object(xv, "doc_xv_tien_trinh", return_value=None), \
                patch.object(xv, "chon_round_online", online), \
                patch.object(luong, "_ten_dang_online", return_value=["caychay244", "caychay255"]), \
                patch.object(luong, "_neu_qua_ngay", return_value=True):
            luong._mot_luot(xv.date.today())
        return luong, online

    def test_tu_nhom_1_bo_qua_nhom_online(self):
        luong, online = self._mot_luot(True)
        online.assert_not_called()
        self.assertEqual([t["ten_dang_nhap"] for t in luong._xv_hang_cho[1]],
                         ["caychay14", "caychay16", "caychay24", "caychay25"])
        self.assertFalse(luong.tu_nhom_1)

    def test_bat_dau_thuong_van_giu_nhom_online(self):
        luong, online = self._mot_luot(False)
        online.assert_called_once()
        self.assertEqual([t["ten_dang_nhap"] for t in luong._xv_hang_cho[1]][:2], ["caychay24", "caychay25"])

    def test_qua_0h_bat_tu_nhom_1(self):
        with patch.object(xv, "cac_tai_khoan_dang_tich", return_value=list(self.DS)):
            luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, True, True)
            with patch.object(luong, "_cho", lambda *a, **k: None), patch.object(xv, "xoa_xv_tien_trinh"):
                luong._xu_ly_qua_ngay(xv.date.today())
        self.assertTrue(luong.tu_nhom_1)


class TestDamBaoNhomPb(unittest.TestCase):
    """Đang chuyển map (GAuto vào Tặc Khấu doanh địa): đọc PT một lần, không báo «nhóm chưa đúng» khi đủ người."""

    def _chay(self, cac_lan_doc):
        luong = xv.LuongXoayVong(queue.Queue(), 3, False, False, False, False)
        luong.in_log = MagicMock()
        nhom = []
        for tk, ten in ((TK[0], "caychay32"), (TK[1], "caychay34")):
            tv = xv.ThanhVien(tk)
            tv.ten, tv.game = ten, MagicMock()
            nhom.append(tv)
        doc = iter(cac_lan_doc)
        with patch.object(xv, "doc_nhom", lambda lua: {"thanh_vien": next(doc)}), \
                patch.object(luong, "_tv_dang_choi", return_value=True), \
                patch.object(luong, "_roi_nhom_neu_sai") as roi, \
                patch.object(luong, "_lam_moi_cau_hinh_moi_nhom") as moi:
            luong._dam_bao_nhom_pb("Nhóm 6 round 2", nhom[0], nhom, ["caychay32", "caychay34"])
        return luong, roi, moi

    def test_du_nhom_thi_khong_lam_gi(self):
        luong, roi, moi = self._chay([["caychay32", "caychay34"], [], []])
        luong.in_log.assert_not_called()
        roi.assert_not_called()
        moi.assert_not_called()

    def test_thieu_nguoi_thi_moi_lai(self):
        luong, _, moi = self._chay([["caychay32"]])
        self.assertIn("thiếu caychay34", luong.in_log.call_args[0][0])
        moi.assert_called_once()


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


class TestDuNhomDungSoNguoi(unittest.TestCase):
    def test_thieu_nguoi_trong_game_thi_chua_du(self):
        luong = xv.LuongXoayVong(queue.Queue(), 1, False, False, False, False)
        nhom = []
        for ten in ("a", "b", "c", "d", "e", "f"):
            tv = xv.ThanhVien({"ten_dang_nhap": ten, "mat_khau": "", "nhan_vat": ten})
            tv.ten = ten
            tv.game = MagicMock()
            nhom.append(tv)
        dang_choi = {tv: True for tv in nhom}
        dang_choi[nhom[-1]] = False
        luong._tv_dang_choi = lambda tv: dang_choi[tv]
        with patch.object(xv, "doc_nhom", lambda lua: {"thanh_vien": [tv.ten for tv in nhom]}):
            self.assertFalse(luong._du_nhom(nhom[0], nhom))
        dang_choi[nhom[-1]] = True
        with patch.object(xv, "doc_nhom", lambda lua: {"thanh_vien": [tv.ten for tv in nhom[:5]]}):
            self.assertFalse(luong._du_nhom(nhom[0], nhom))
        with patch.object(xv, "doc_nhom", lambda lua: {"thanh_vien": [tv.ten for tv in nhom]}):
            self.assertTrue(luong._du_nhom(nhom[0], nhom))

    def test_dang_nhap_lai_nguoi_thieu_khong_logout_ca_nhom(self):
        luong = xv.LuongXoayVong(queue.Queue(), 1, False, False, False, False)
        a, b = xv.ThanhVien({"ten_dang_nhap": "a", "mat_khau": ""}), xv.ThanhVien({"ten_dang_nhap": "b", "mat_khau": ""})
        a.hwnd, b.hwnd = 11, 22
        a.ten, b.ten = "a", "b"
        lan = {"n": 0}
        luong.dung.is_set = lambda: lan["n"] > 0
        luong._du_nhom = lambda *_: False
        luong._tv_dang_choi = lambda tv: tv is a
        luong.in_log = lambda *_: None

        def dn(offline, giu_them=()):
            lan["n"] += 1
            self.assertEqual(offline, [b])
            self.assertEqual(list(giu_them), [11, 22])
            return []

        luong._dang_nhap = dn
        self.assertFalse(luong._cho_du_nhom("nhóm", a, [a, b], None, 2))


class TestThoatGameNgoaiNhom(unittest.TestCase):
    def test_tieu_de_launcher_khong_bi_dua_ve_may_chu(self):
        cua = {"hwnd": 5, "pid": 9, "tieu_de": "Thien Long Bat Bo"}
        with patch.object(xv, "tim_cua_so_game", return_value=[cua]), \
                patch.object(xv, "hwnd_giu_khi_xoay_vong", return_value=set()), \
                patch.object(xv, "ten_trong_tieu_de", return_value=None), \
                patch.object(xv, "thoat_ve_chon_may_chu") as thoat:
            xv.thoat_game_khac([], lambda *_: None)
        thoat.assert_not_called()

    def test_da_vao_game_ngoai_nhom_van_logout(self):
        cua = {"hwnd": 5, "pid": 9, "tieu_de": "cosato777 (10) [Lac Duong] - ChickenAuto"}
        with patch.object(xv, "tim_cua_so_game", return_value=[cua]), \
                patch.object(xv, "hwnd_giu_khi_xoay_vong", return_value=set()), \
                patch.object(xv, "ten_trong_tieu_de", return_value="cosato777"), \
                patch.object(xv, "Game") as game_cls, \
                patch.object(xv, "man_hinh_hien_tai", return_value="vao_game"), \
                patch.object(xv, "thoat_ve_chon_may_chu") as thoat:
            game_cls.return_value.thong_tin.return_value = {"ten": "cosato777"}
            xv.thoat_game_khac([], lambda *_: None)
        thoat.assert_called_once()


class TestBoSungHangCho(unittest.TestCase):
    def test_acc_chua_het_luot_bi_roi_khoi_hang_thi_duoc_them_lai(self):
        a = {"ten_dang_nhap": "a"}
        b = {"ten_dang_nhap": "b"}
        hang = [[a], []]
        them = xv.bo_sung_hang_cho(hang, [a, b], 2, set(), {}, da_xong_fn=lambda ten: ten == "a")
        self.assertEqual(them, ["aa", "b", "bb"])
        self.assertEqual([tk["ten_dang_nhap"] for tk in hang[0]], ["a", "b"])
        self.assertEqual([tk["ten_dang_nhap"] for tk in hang[1]], ["a", "b"])

    def test_het_luot_va_thu_dang_nhap_du_thi_khong_them(self):
        a = {"ten_dang_nhap": "a"}
        hang = [[], []]
        thu = {"a|0": xv.SO_LAN_XEP_LAI_DANG_NHAP}
        them = xv.bo_sung_hang_cho(hang, [a], 2, set(), thu, da_xong_fn=lambda ten: ten == "aa")
        self.assertEqual(them, [])
        self.assertEqual(hang, [[], []])


class TestMoDuClient(unittest.TestCase):
    def test_thieu_client_thi_mo_them_roi_giu_hwnd(self):
        luong = xv.LuongXoayVong(queue.Queue(), 1, False, False, False, False)
        luong.cac_hwnd = [1, 2, 3, 4]
        log = []
        luong.in_log = log.append
        with patch.object(xv, "hwnd_giu_khi_xoay_vong", return_value=set()), \
                patch.object(xv, "tim_cua_so_game", side_effect=[[{"hwnd": i} for i in range(4)],
                                                              [{"hwnd": i} for i in range(5)]]), \
                patch.object(xv.cau_hinh, "doc_tai_khoan", return_value={"thu_muc_game": "G", "giay_cho_truoc_khi_nap_dll": 1}), \
                patch.object(xv, "mo_game", return_value=99) as mo, \
                patch.object(xv, "cho_cua_so", return_value=50):
            luong._mo_du_client(5)
        mo.assert_called_once_with("G")
        self.assertIn(50, luong.cac_hwnd)
        self.assertTrue(any("mở thêm 1" in dong for dong in log))


class TestChuaXongThiKhongPhoBan(unittest.TestCase):
    def test_chua_nhan_do_thi_khong_bat_pho_ban(self):
        luong = xv.LuongXoayVong.__new__(xv.LuongXoayVong)
        luong.in_log = lambda *_: None
        luong._bo_dang_nhap = []
        luong.dung = MagicMock()
        luong.dung.is_set.return_value = False
        tv = MagicMock()
        tv.game, tv.ten, tv.tk = MagicMock(), "anhzero111", "anhzero11"
        with patch.object(xv, "san_sang_di_pho_ban", return_value=False):
            kq = luong._di_round("Nhóm 1 round 2", [tv])
        self.assertEqual(kq, [])
        self.assertEqual(luong._bo_dang_nhap, [tv])


if __name__ == "__main__":
    unittest.main()
