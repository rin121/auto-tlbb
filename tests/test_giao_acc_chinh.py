import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import giao_acc_chinh as gac  # noqa: E402


class TestBoQuaTaiKhoanChuaCoNhanVat(unittest.TestCase):
    """GAC-01: giao cho acc chính bỏ tài khoản chưa từng đăng nhập / nhân vật chưa có (khoảng trống caychay48..68)."""

    def setUp(self):
        self.thu_muc = tempfile.mkdtemp()
        tk = os.path.join(self.thu_muc, "#636179636861793437")  # caychay47
        os.makedirs(tk)
        open(os.path.join(tk, "#636179636861793437.pfc"), "w").close()

    def tearDown(self):
        shutil.rmtree(self.thu_muc, ignore_errors=True)

    def test_ma_thu_muc_giong_game(self):
        self.assertEqual(gac._ma_thu_muc("caychay72"), "#636179636861793732")
        self.assertEqual(gac._ma_thu_muc("GaoDẻLâu"), "#47616f44eb4ce275")

    def test_ly_do(self):
        ly_do = gac.ly_do_khong_co_nhan_vat
        self.assertIsNone(ly_do("caychay47", "caychay47", self.thu_muc))
        self.assertEqual(ly_do("caychay47", "caychay477", self.thu_muc), "chưa có nhân vật")
        self.assertEqual(ly_do("caychay48", "caychay48", self.thu_muc), "tài khoản chưa từng đăng nhập")

    def test_da_tao_hoac_dang_online_thi_co(self):
        ly_do = gac.ly_do_khong_co_nhan_vat
        self.assertIsNone(ly_do("caychay47", "caychay477", self.thu_muc, da_tao={"caychay477"}))
        self.assertIsNone(ly_do("caychay48", "caychay48", self.thu_muc, online={"caychay48"}))

    def test_khong_thay_thu_muc_accounts_thi_khong_loc(self):
        self.assertIsNone(gac.ly_do_khong_co_nhan_vat("caychay48", "caychay48",
                                                      os.path.join(self.thu_muc, "khong_co")))

    def test_danh_sach_bo_qua_va_ghi_ly_do(self):
        ds = [{"ten_dang_nhap": t} for t in ("caychay47", "caychay48")]
        bo_qua = []
        with patch.object(gac, "cac_tai_khoan_dang_tich", return_value=ds), \
                patch.object(gac, "thu_muc_accounts", return_value=self.thu_muc), \
                patch.object(gac, "cac_nhan_vat_dang_online", return_value=set()), \
                patch.object(gac, "da_xong", return_value=[]), \
                patch.object(gac, "ten_round", lambda tk, r: tk + tk[-1] * r), \
                patch.object(gac, "_loc_nhan_vat_pho_ban", return_value=True):
            kq = gac.cac_nhan_vat_pho_ban("acc_chinh", True, bo_qua)
        self.assertEqual([ten for _, ten in kq], ["caychay47"])
        self.assertIn(("caychay48", "caychay48", "tài khoản chưa từng đăng nhập"), bo_qua)
        self.assertEqual(len(bo_qua), 1)


class TestTatCaAccTheoBangTaiKhoan(unittest.TestCase):
    """GAC-28: «Tất cả acc phó bản» — thứ tự bảng XV, một NV/acc; resume qua da_xong."""

    class _KiemTraCo:
        def __init__(self, bo_qua=None):
            self.thu_muc = ""
            self.online = set()

        def co(self, tk, ten):
            return True

    def test_thu_tu_bang_mot_nv_khong_chia_nhom(self):
        ds = [
            {"ten_dang_nhap": "acc_b", "nhan_vat": "NvB"},
            {"ten_dang_nhap": "acc_a", "nhan_vat": "NvA"},
        ]

        def _chia_nhom_khong_go(*_a, **_k):
            raise AssertionError("chia_nhom không dùng trong cac_nhan_vat_pho_ban")

        with patch.object(gac, "cac_tai_khoan_dang_tich", return_value=ds), \
                patch.object(gac, "chia_nhom", side_effect=_chia_nhom_khong_go), \
                patch.object(gac, "_KiemTraNhanVat", self._KiemTraCo), \
                patch.object(gac, "_loc_nhan_vat_pho_ban", return_value=True):
            kq = gac.cac_nhan_vat_pho_ban("acc_chinh", True)
        self.assertEqual([(tk["ten_dang_nhap"], ten) for tk, ten in kq],
                         [("acc_b", "NvB"), ("acc_a", "NvA")])

    def test_dung_cot_nhan_vat_khong_goi_ten_round(self):
        ds = [{"ten_dang_nhap": "tk1", "nhan_vat": "  TenBang  "}]

        def _ten_round_fail(*_a, **_k):
            raise AssertionError("ten_round không gọi khi đã có cột Nhân vật")

        with patch.object(gac, "cac_tai_khoan_dang_tich", return_value=ds), \
                patch.object(gac, "ten_round", side_effect=_ten_round_fail), \
                patch.object(gac, "_KiemTraNhanVat", self._KiemTraCo), \
                patch.object(gac, "_loc_nhan_vat_pho_ban", return_value=True):
            kq = gac.cac_nhan_vat_pho_ban("main", True)
        self.assertEqual(kq, [(ds[0], "TenBang")])

    def test_resume_loc_bo_qua_da_xong(self):
        ds_truong = [
            ({"ten_dang_nhap": "x"}, "nv1"),
            ({"ten_dang_nhap": "y"}, "nv2"),
            ({"ten_dang_nhap": "z"}, "nv3"),
        ]
        da_xong_ds = {gac.chuan_hoa("nv1"), gac.chuan_hoa("nv2")}
        con = [(tk, ten) for tk, ten in ds_truong if gac.chuan_hoa(ten) not in da_xong_ds]
        self.assertEqual([(tk["ten_dang_nhap"], ten) for tk, ten in con], [("z", "nv3")])


class TestBoQuaCungTaiKhoanKhongCoDo(unittest.TestCase):
    """GAC-02: «Tất cả acc phó bản» — một nhân vật không có đồ thì bỏ các nhân vật còn lại của tài khoản đó."""

    DS = [{"ten_dang_nhap": f"caychay{i}"} for i in (14, 16, 18, 19)]

    def _truong(self):
        with patch.object(gac, "cac_tai_khoan_dang_tich", return_value=self.DS), \
                patch.object(gac, "chia_nhom", lambda ds: [ds]), \
                patch.object(gac, "ten_round", lambda tk, r: tk + tk[-1] * r), \
                patch.object(gac.cau_hinh, "chung", return_value={"xv_truong_nhom": [["caychay18", "caychay188"]]}):
            return gac.ten_cac_truong_nhom("acc_chinh")

    def test_truong_nhom_gom_moi_round_va_nguoi_bu(self):
        self.assertEqual(self._truong(), {"caychay14", "caychay144", "caychay1444", "caychay188"})

    def test_bo_qua_nhan_vat_khac_cung_tai_khoan(self):
        truong = self._truong()
        khong_co = {"caychay16"}
        self.assertTrue(gac.bo_qua_cung_tai_khoan(self.DS[1], "caychay166", khong_co, truong))
        self.assertTrue(gac.bo_qua_cung_tai_khoan(self.DS[1], "caychay1666", khong_co, truong))
        self.assertFalse(gac.bo_qua_cung_tai_khoan(self.DS[2], "caychay188", {"caychay18"}, truong))
        self.assertFalse(gac.bo_qua_cung_tai_khoan(self.DS[3], "caychay199", khong_co, truong))


class TestChayToiNpcTanThu(unittest.TestCase):
    """GAC-03: lệnh chạy tới NPC Tân Thủ bị game bỏ (vừa Về thành) thì gửi lại, không đứng yên tới hết giờ."""

    class _Lua:
        def __init__(self):
            self.lenh = []

        def chay(self, ma):
            self.lenh.append(ma)
            return b""

    def _luong(self, cac_vi_tri):
        import threading
        luong = gac.LuongGiaoAccChinh.__new__(gac.LuongGiaoAccChinh)
        luong.dung = threading.Event()
        vi_tri = iter(cac_vi_tri)
        luong._doc = lambda game: next(vi_tri)
        luong._ve_dai_ly = lambda game, ten: None
        return luong

    def test_gui_lai_lenh_chay_khi_chua_toi(self):
        dung_yen = {"x": 100, "y": 100, "map": "Đại Lý"}
        toi = {"x": 160, "y": 167, "map": "Đại Lý"}
        luong = self._luong([dung_yen, dung_yen, dung_yen, toi])
        game = type("G", (), {"lua": self._Lua()})()
        with patch.object(gac, "GIAY_GUI_LAI_CHAY", 0), patch.object(gac, "la_dai_ly", lambda m: True):
            luong._chay_toi(game, "caychay144", (160, 166))
        self.assertEqual(game.lua.lenh, ["AutoRunToTarget(160, 168)"] * 3)

    def test_het_gio_van_bao_loi(self):
        dung_yen = {"x": 100, "y": 100, "map": "Đại Lý"}
        luong = self._luong([dung_yen] * 1000)
        game = type("G", (), {"lua": self._Lua()})()
        with patch.object(gac, "GIAY_CHAY_TOI", 0.2), patch.object(gac, "la_dai_ly", lambda m: True):
            with self.assertRaises(gac.LoiGiaoAccChinh):
                luong._chay_toi(game, "caychay144", (160, 166))
        self.assertTrue(game.lua.lenh)

    def test_xep_tui_sau_giao(self):
        luong = self._luong([])
        luong.tk_chinh = {"nhan_vat": "accchinh"}
        luong.in_log = lambda *_: None
        lua_phu = self._Lua()
        lua_chinh = self._Lua()
        game = type("G", (), {"lua": lua_phu})()
        luong.chinh = type("G", (), {"lua": lua_chinh})()
        with patch.object(gac.time, "sleep"):
            luong._xep_tui_sau_giao(game, "accphu")
        for lua in (lua_phu, lua_chinh):
            self.assertTrue(any("OpenWindow" in m and "Packet" in m for m in lua.lenh))
            self.assertTrue(any("Packet_PackUp_Clicked" in m for m in lua.lenh))

    def test_xep_roi_doc_lai_o_truoc_khi_giao_tiep(self):
        import inspect
        src = inspect.getsource(gac.GiaoAccChinhEngine._mot_truong_nhom)
        i = src.index("self._xep_tui_sau_giao(game, ten)")
        self.assertLess(i, src.index("self._do_can_giao(game, bo_qua)", i))
        self.assertIn("o not in tui", src)

    def test_gan_bo_qua_sau_xep_theo_mon_khong_theo_o_cu(self):
        luong = self._luong([])
        game = type("G", (), {"lua": object()})()
        tui = {
            ("base", 0): (111, 5, "Mảnh A"),
            ("base", 12): (222, 1, "Khác"),
        }
        with patch.object(gac, "doc_tui", return_value=tui):
            bo = luong._gan_bo_qua_sau_xep(game, [("base", 111, 5, "Mảnh A")])
        self.assertEqual(bo, {("base", 0, 111)})
        self.assertNotIn(("base", 12, 111), bo)


class TestDangNhapLaiKhiDiss(unittest.TestCase):
    def _luong(self):
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.tk_chinh = {"ten_dang_nhap": "chinh", "mat_khau": "x", "nhan_vat": "Gao"}
        luong.in_log = lambda *_: None
        luong._cho = lambda *a, **k: True
        luong._ve_dai_ly = lambda *a: None
        luong._chay_toi = lambda *a: None
        luong._doc = lambda g: {"ten": "x"}
        return luong

    def test_hop_ngat_ket_noi_khong_con_trong_game(self):
        luong = self._luong()
        game = type("G", (), {})()
        game.thong_tin = lambda: None
        game.lua = object()
        with patch.object(gac, "man_hinh_hien_tai", return_value="thong_bao"):
            self.assertFalse(luong._con_trong_game(game))
        game.thong_tin = lambda: {"ten": "Gao"}
        self.assertTrue(luong._con_trong_game(game))
        game.thong_tin = lambda: (_ for _ in ()).throw(gac.LoiLua("cửa sổ game đã đóng"))
        self.assertFalse(luong._con_trong_game(game))

    def test_loi_timeout_khong_phai_diss(self):
        self.assertTrue(gac.GiaoAccChinhEngine._la_loi_mat_game(gac.LoiLua("cửa sổ game đã đóng")))
        self.assertFalse(gac.GiaoAccChinhEngine._la_loi_mat_game(gac.LoiLua("Game không phản hồi")))

    def test_chi_login_lai_acc_bi_diss(self):
        luong = self._luong()
        logs = []
        luong.in_log = logs.append
        chinh = type("G", (), {"lua": type("L", (), {"hwnd": 1})()})()
        phu = type("G", (), {"lua": type("L", (), {"hwnd": 2})()})()
        luong.chinh = chinh
        luong._con_trong_game = lambda game: game is chinh
        da_dn = []

        def dang_nhap(tk, hwnd):
            da_dn.append((tk["nhan_vat"], hwnd))
            return type("G", (), {"lua": type("L", (), {"hwnd": 9, "chay": lambda *_a, **_k: None})()})()

        luong._dang_nhap = dang_nhap
        game = luong._dang_nhap_lai_acc_diss({"ten_dang_nhap": "phu", "mat_khau": "y"}, "Phu", phu)
        self.assertEqual(da_dn, [("Phu", 2)])
        self.assertIs(luong.chinh, chinh)
        self.assertEqual(game.lua.hwnd, 9)
        self.assertEqual(luong.hwnd_truong, 9)
        self.assertTrue(any("Phu: bị ngắt kết nối, đăng nhập lại" in d for d in logs))

    def test_vong_giao_co_dang_nhap_lai(self):
        import inspect
        src = inspect.getsource(gac.GiaoAccChinhEngine._mot_truong_nhom)
        self.assertIn("_dang_nhap_lai_acc_diss", src)
        self.assertIn("SO_LAN_DANG_NHAP_LAI", src)
        self.assertLess(src.index("đăng nhập lại rồi giao tiếp"), src.index("đã giao xong"))


class TestTuBatDauKhiLoi(unittest.TestCase):
    def test_loi_khi_chua_xong_thi_bat_lai(self):
        self.assertTrue(gac.nen_bat_lai_sau_loi("Dừng: túi đầy", True, 0))
        self.assertTrue(gac.nen_bat_lai_sau_loi("Lỗi, xem log", True, 7))
        self.assertTrue(gac.nen_bat_lai_sau_loi("Lỗi, xem log", True, 100))
        self.assertFalse(gac.nen_bat_lai_sau_loi("Đã dừng", True, 0))
        self.assertFalse(gac.nen_bat_lai_sau_loi("Xong", True, 0))
        self.assertFalse(gac.nen_bat_lai_sau_loi("Dừng: túi đầy", False, 0))

    def test_con_chua_xong_khi_con_acc_nguon(self):
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.ds_nguon = [({"ten_dang_nhap": "a"}, "Phu")]
        luong.tien_trinh = {"ngay": gac.date.today().isoformat(), "da_xong": []}
        luong.dung = type("E", (), {"is_set": lambda self: False})()
        self.assertTrue(luong.con_chua_xong())
        luong._danh_dau_chay_lai_neu_chua_xong()
        self.assertTrue(luong.chay_lai_khi_loi)
        luong.tien_trinh["da_xong"] = ["Phu"]
        self.assertFalse(luong.con_chua_xong())
        luong.dung = type("E", (), {"is_set": lambda self: True})()
        luong._danh_dau_chay_lai_neu_chua_xong()
        self.assertFalse(luong.chay_lai_khi_loi)


class TestThoatAccChinh(unittest.TestCase):
    def test_giao_xong_thi_thoat_acc_chinh(self):
        luong = gac.LuongGiaoAccChinh.__new__(gac.LuongGiaoAccChinh)
        luong.tk_chinh = {"ten_dang_nhap": "AccChinh", "nhan_vat": "chinh"}
        luong.chinh = object()
        luong.tk_da_thoat = set()
        luong.in_log = lambda *_: None
        da_thoat = []
        luong._thoat_game_pho_ban = lambda game, ten: da_thoat.append(ten)
        luong._thoat_acc_chinh()
        self.assertEqual(da_thoat, ["chinh"])
        self.assertIsNone(luong.chinh)
        self.assertIn("accchinh", luong.tk_da_thoat)

    def test_acc_dang_trong_game_thi_khong_logout(self):
        luong = gac.LuongGiaoAccChinh.__new__(gac.LuongGiaoAccChinh)
        luong.ten_giu_online = {gac.chuan_hoa("GaoCáMặp")}
        luong.tk_da_thoat = set()
        luong.pid_dieu_khien = set()
        luong.dung = type("D", (), {"is_set": lambda self: False})()
        luong.in_log = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        cua_so = [{"hwnd": 1, "pid": 9, "tieu_de": "GaoCáMặp"}]
        game = type("G", (), {"thong_tin": lambda self: {"ten": "GaoCáMặp", "tai_khoan": "kduy122"},
                              "lua": object()})()
        with patch.object(gac, "tim_cua_so_game", return_value=cua_so), \
                patch.object(gac, "Game", return_value=game), \
                patch.object(gac, "thoat_ve_chon_may_chu") as thoat:
            luong._thoat_cac_client()
        thoat.assert_not_called()
        self.assertNotIn("kduy122", luong.tk_da_thoat)


if __name__ == "__main__":
    unittest.main()
