import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, THU_MUC)
sys.path.insert(0, os.path.join(THU_MUC, "cong_cu"))

import nang_cap_nhan_vat as ncnv  # noqa: E402
import ghi_thao_tac  # noqa: E402


class TestDanhSachDaNangCap(unittest.TestCase):
    def setUp(self):
        self.thu_muc = tempfile.mkdtemp()
        self.file = os.path.join(self.thu_muc, "nang_cap_da_xong.json")

    def tearDown(self):
        shutil.rmtree(self.thu_muc, ignore_errors=True)

    def test_chua_co_file_thi_chua_lam(self):
        self.assertEqual(ncnv.doc(self.file), {})
        self.assertFalse(ncnv.da_lam("caychay24", self.file))

    def test_danh_dau_roi_bo_qua(self):
        ncnv.danh_dau_da_lam("CayChay24", datetime(2026, 10, 27, 21, 30), self.file)
        self.assertTrue(ncnv.da_lam("caychay24", self.file))
        self.assertFalse(ncnv.da_lam("caychay25", self.file))
        with open(self.file, encoding="utf-8") as f:
            du_lieu = json.load(f)
        self.assertEqual(list(du_lieu.values()), [{"ten": "CayChay24", "luc": "2026-10-27 21:30:00"}])
        self.assertEqual([t for t in os.listdir(self.thu_muc) if t.endswith(".tmp")], [])

    def test_bo_danh_dau(self):
        ncnv.danh_dau_da_lam("caychay24", duong_dan=self.file)
        self.assertTrue(ncnv.bo_danh_dau("caychay24", self.file))
        self.assertFalse(ncnv.da_lam("caychay24", self.file))
        self.assertFalse(ncnv.bo_danh_dau("caychay24", self.file))

    def test_file_hong_coi_nhu_rong(self):
        with open(self.file, "w", encoding="utf-8") as f:
            f.write("{hỏng")
        self.assertFalse(ncnv.da_lam("caychay24", self.file))
        ncnv.danh_dau_da_lam("caychay24", duong_dan=self.file)
        self.assertTrue(ncnv.da_lam("caychay24", self.file))

    def test_du_4_giftcode(self):
        self.assertEqual(len(ncnv.GIFTCODE), 4)

    def test_lam_do_ghi_buoc_chua_tinh_la_xong(self):
        ncnv.danh_dau_buoc("caychay24", 1, self.file)
        ncnv.danh_dau_buoc("CayChay24", 2, self.file)
        ncnv.danh_dau_buoc("caychay24", 2, self.file)
        self.assertFalse(ncnv.da_lam("caychay24", self.file))
        self.assertEqual(ncnv.cac_buoc_da_xong("caychay24", self.file), {1, 2})
        self.assertEqual(ncnv.cac_buoc_da_xong("caychay25", self.file), set())
        ncnv.danh_dau_da_lam("caychay24", duong_dan=self.file)
        self.assertTrue(ncnv.da_lam("caychay24", self.file))
        self.assertEqual(ncnv.cac_buoc_da_xong("caychay24", self.file), set())

    def test_da_xong_roi_ghi_buoc_lai_bat_dau_moi(self):
        ncnv.danh_dau_da_lam("caychay24", duong_dan=self.file)
        ncnv.bo_danh_dau("caychay24", self.file)
        ncnv.danh_dau_buoc("caychay24", 3, self.file)
        self.assertEqual(ncnv.cac_buoc_da_xong("caychay24", self.file), {3})


class TestNangCapLogic(unittest.TestCase):
    def test_doc_bang(self):
        self.assertEqual(ncnv.doc_bang(b"9\t10141030\tB\xe1ch\n10\t10163512.0\tR\nr\xe1c\n"),
                         {9: (10141030, ncnv.giai_ma(b"B\xe1ch")), 10: (10163512, "R")})

    def test_thay_bach_bao_khi_tui_co_9_sao(self):
        tui = {0: (10163506, "Bách Bảo Nang"), 1: (10163512, "Bách Bảo Rương")}
        trang_bi = {9: (10141030, "Bách Bảo Nang"), 10: (10141040, "Bách Bảo Rương")}
        self.assertEqual([(o, ma) for o, _, ma, _ in ncnv.can_thay_bach_bao(tui, trang_bi)],
                         [(9, 10163506), (10, 10163512)])

    def test_khong_co_9_sao_thi_bo_qua_buoc_1(self):
        tui = {0: (10141030, "Bách Bảo Nang"), 1: (10141040, "Bách Bảo Rương")}
        trang_bi = {9: (10163506, "Bách Bảo Nang"), 10: (10163512, "Bách Bảo Rương")}
        self.assertEqual(ncnv.can_thay_bach_bao(tui, trang_bi), [])
        self.assertEqual(ncnv.can_thay_bach_bao({}, {}), [])

    def test_chi_thay_o_chua_mang_9_sao(self):
        tui = {3: (10163512, "Bách Bảo Rương")}
        trang_bi = {9: (10163506, "Bách Bảo Nang"), 10: (10141040, "Bách Bảo Rương")}
        self.assertEqual([o for o, *_ in ncnv.can_thay_bach_bao(tui, trang_bi)], [10])

    def test_hoang_kim_bo_qua_mon_da_mang(self):
        tui = {8: (10162450, "Hoàng Kim - Khôi"), 9: (10162457, "Hoàng Kim - Giới"), 10: (30004622, "Hộp")}
        trang_bi = {6: (10162457, "Hoàng Kim - Giới"), 1: (10162420, "Tân Thủ - Khôi")}
        self.assertEqual(ncnv.hoang_kim_can_mang(tui, trang_bi), {10162450: "Hoàng Kim - Khôi"})
        self.assertEqual(len(ncnv.MA_HOANG_KIM), 10)

    def test_do_cu_khong_gom_do_moi(self):
        self.assertIn(10100000, ncnv.MA_DO_CU)
        self.assertIn(10141030, ncnv.MA_DO_CU)
        self.assertIn(10162429, ncnv.MA_DO_CU)
        for ma in (10163506, 10163512, 10162570, 10163500, 10163518, *ncnv.MA_HOANG_KIM):
            self.assertNotIn(ma, ncnv.MA_DO_CU)

    def test_mon_dau_tien_chi_khi_co_gia_diem_tang(self):
        self.assertIsNone(ncnv.mon_dau_tien({1: ("Thông Thiên Linh Đan", ""), 2: ("Thanh Tâm Đan", "")}))
        self.assertIsNone(ncnv.mon_dau_tien({}))
        self.assertEqual(ncnv.mon_dau_tien({1: ("Minh Tôn", "?Điểm Tặng: 1000"), 2: ("Minh Tôn", "x")}),
                         (1, "Minh Tôn"))

    def test_cong_noi_luc_khi_chua_max(self):
        self.assertTrue(ncnv.can_cong_noi_luc(4_316_278, 50_000_000, 10_000_000))
        self.assertFalse(ncnv.can_cong_noi_luc(250_000_000, 50_000_000, 10_000_000))
        self.assertFalse(ncnv.can_cong_noi_luc(300_000_000, 50_000_000, 10_000_000))
        self.assertFalse(ncnv.can_cong_noi_luc(4_316_278, 9_999_999, 10_000_000))

    def test_vut_theo_ma_khong_co_mon_thi_khong_mo_bo_nho(self):
        import vut_rac

        class LuaGia:
            pid = 0

            def chay(self, ma):
                return b"0|10163506\n1|30004622.0\n"
        self.assertEqual(vut_rac.vut_theo_ma(LuaGia(), "caychay24", ncnv.MA_DO_CU, lambda chu: None), [])

    def test_ma_lua_thao_va_xep(self):
        ma = ncnv.MA_THAO.replace("{o}", "9").replace("{nut}", "OtherInfo_Packet1_Skill1")
        self.assertIn('EnumAction(9, "equip")', ma)
        self.assertIn("OtherInfo_Packet1_Skill1:DoSubAction()", ma)
        self.assertIn("Packet_PackUp_Clicked()", ncnv.MA_XEP_TUI)


class TestVeDaiLyTruoc(unittest.TestCase):
    """NC-08: chưa ở Đại Lý thì về Đại Lý trước rồi mới làm các bước."""

    def setUp(self):
        self.thu_muc = tempfile.mkdtemp()
        self.file = os.path.join(self.thu_muc, "nang_cap_da_xong.json")
        self.goi = []

        class GameGia:
            lua = object()
        self.nc = ncnv.tao_nang_cap(GameGia(), "caychay24", lambda chu: None, lambda: False,
                                    lambda chu: None, self.file)
        self.nc._tt = lambda: {"ten": "caychay24"}
        self.nc._ve_thanh = lambda: self.goi.append("ve_thanh")
        for so in range(1, 7):
            setattr(self.nc, f"buoc_{so}", lambda so=so: self.goi.append(so))

    def tearDown(self):
        shutil.rmtree(self.thu_muc, ignore_errors=True)

    def test_o_map_khac_thi_ve_dai_ly_truoc(self):
        self.nc._map = lambda: "Lạc Dương"
        self.nc.chay()
        self.assertEqual(self.goi, ["ve_thanh", 1, 2, 3, 4, 5, 6])
        self.assertTrue(ncnv.da_lam("caychay24", self.file))

    def test_dang_o_dai_ly_thi_khong_ve(self):
        self.nc._map = lambda: "Đại Lý"
        self.nc.chay()
        self.assertEqual(self.goi, [1, 2, 3, 4, 5, 6])

    def test_ve_khong_duoc_thi_khong_lam_buoc_nao(self):
        from pho_ban_pmp import LoiPhoBan
        self.nc._map = lambda: "Tô Châu"

        def loi():
            raise LoiPhoBan("nhân vật không có kỹ năng Quay về Đại Lý thành")
        self.nc._ve_thanh = loi
        with self.assertRaises(LoiPhoBan):
            self.nc.chay()
        self.assertEqual(self.goi, [])
        self.assertFalse(ncnv.da_lam("caychay24", self.file))


class TestVeThanhSauCongPoint(unittest.TestCase):
    """NC-10: NPC Cộng Point có góc lag (chạy đi bị giật về) — tăng point xong thì Về thành Đại Lý."""

    def setUp(self):
        self.thu_muc = tempfile.mkdtemp()
        self.file = os.path.join(self.thu_muc, "nang_cap_da_xong.json")
        self.goi = []
        self.ve_duoc_sau = 1

        class LuaGia:
            def chay(self, ma):
                return b""

        class GameGia:
            lua = LuaGia()
        self.nc = ncnv.tao_nang_cap(GameGia(), "caychay24", lambda chu: None, lambda: False,
                                    lambda chu: None, self.file)
        self.nc._tt = lambda: {"ten": "caychay24"}
        self.nc._map = lambda: "Đại Lý"
        self.nc._noi_chuyen = lambda npc, cac_dong: setattr(self.nc, "da_toi_cong_point", True)
        self.nc._ve_thanh_tai_dai_ly = self._ve_thanh
        for so in range(1, 7):
            setattr(self.nc, f"buoc_{so}", lambda so=so: self.goi.append(so))
        self.nc.buoc_6 = lambda: (self.goi.append(6), self.nc._noi_chuyen(None, ()))

    def tearDown(self):
        shutil.rmtree(self.thu_muc, ignore_errors=True)

    def _ve_thanh(self):
        self.goi.append("ve_thanh")
        return self.goi.count("ve_thanh") >= self.ve_duoc_sau

    def test_cong_point_xong_thi_ve_thanh(self):
        self.nc.chay()
        self.assertEqual(self.goi, [1, 2, 3, 4, 5, 6, "ve_thanh"])
        self.assertFalse(self.nc.da_toi_cong_point)
        self.assertTrue(ncnv.da_lam("caychay24", self.file))

    def test_ve_thanh_chua_doi_cho_thi_thu_lai(self):
        self.ve_duoc_sau = 2
        self.nc.chay()
        self.assertEqual(self.goi, [1, 2, 3, 4, 5, 6, "ve_thanh", "ve_thanh"])

    def test_khong_toi_npc_cong_point_thi_khong_ve_thanh(self):
        self.nc.buoc_6 = lambda: self.goi.append(6)
        self.nc.chay()
        self.assertEqual(self.goi, [1, 2, 3, 4, 5, 6])

    def test_nhan_do_tan_thu_cong_noi_luc_xong_thi_ve_thanh(self):
        import nhan_vat_moi
        diem = [25_000_000]

        def noi_chuyen(npc, cac_dong):
            self.assertEqual(npc, nhan_vat_moi.NPC_CONG_POINT)
            self.nc.da_toi_cong_point = True
            diem[0] -= nhan_vat_moi.DIEM_MOI_LAN_CONG
        self.nc._noi_chuyen = noi_chuyen
        self.nc.game.diem_tiem_nang = lambda: diem[0]
        nhan_vat_moi.NhanDoTanThu._cong_noi_luc(self.nc)
        self.nc.roi_cong_point()
        self.assertEqual(diem[0], 5_000_000)
        self.assertEqual(self.goi, ["ve_thanh"])


class TestMangKhiGameCham(unittest.TestCase):
    """NC-09: máy ảo lag — mang đồ phải kiểm tra lại, chưa lên người thì làm lại, không bấm trùng khi game trả lời trễ."""

    def setUp(self):
        from unittest import mock
        import pho_ban_pmp

        class LuaGia:
            def chay(self, ma):
                return b""

        class GameGia:
            lua = LuaGia()
        self.cac_patch = [mock.patch.object(pho_ban_pmp, "GIAY_CHO_GAME_TRA_LOI", 0.2),
                          mock.patch.object(pho_ban_pmp, "GIAY_CHO_LAG", 1.5),
                          mock.patch.object(pho_ban_pmp, "dang_hien", lambda lua, ten: False)]
        for p in self.cac_patch:
            p.start()
        self.nc = ncnv.tao_nang_cap(GameGia(), "caychay24", lambda chu: None, lambda: False, lambda chu: None,
                                    os.path.join(tempfile.gettempdir(), "khong_dung.json"))
        self.tui = {3: (10162450, 1), 5: (30004622, 2)}
        self.so_click = 0
        self.doc_sau_click = 0
        self.mat_sau = None
        self.nc._tui = self._tui
        self.nc._chuot_phai = self._click

    def tearDown(self):
        for p in self.cac_patch:
            p.stop()

    def _click(self, o):
        self.so_click += 1
        self.doc_sau_click = 0

    def _tui(self):
        self.doc_sau_click += 1
        if self.mat_sau and self.so_click >= self.mat_sau[0] and self.doc_sau_click >= self.mat_sau[1]:
            self.tui.pop(3, None)
        return dict(self.tui)

    def test_game_tra_loi_tre_thi_cho_khong_bam_lai(self):
        self.mat_sau = (1, 4)
        self.assertEqual(self.nc._mang({10162450: "Hoàng Kim - Khôi"}), {})
        self.assertEqual(self.so_click, 1)

    def test_lan_dau_khong_an_thi_mang_lai(self):
        self.mat_sau = (2, 1)
        self.assertEqual(self.nc._mang({10162450: "Hoàng Kim - Khôi"}), {})
        self.assertEqual(self.so_click, 2)

    def test_khong_mang_duoc_thi_thu_toi_da_roi_bao_con_lai(self):
        self.assertEqual(self.nc._mang({10162450: "Hoàng Kim - Khôi"}), {10162450: "Hoàng Kim - Khôi"})
        import pho_ban_pmp
        self.assertEqual(self.so_click, pho_ban_pmp.SO_LAN_THU_MANG)


class TestNangCapSauDangNhap(unittest.TestCase):
    """LuongDangNhap.nang_cap_sau_dang_nhap: tự nâng cấp khi vừa vào game (NC-06)."""

    def setUp(self):
        import threading
        from unittest import mock
        import dang_nhap
        self.dang_nhap = dang_nhap
        self.log = []
        self.goi = []

        class GameGia:
            def __init__(self, hwnd):
                self.hwnd = hwnd

            def thong_tin(self):
                return {"ten": "caychay24"}
        self.luong = mock.Mock()
        self.luong.pid = 100
        self.luong.dung = threading.Event()
        self.luong.in_log = self.log.append
        self.cac_patch = [
            mock.patch.object(dang_nhap, "tim_cua_so_game", lambda: [{"hwnd": 7, "pid": 100}]),
            mock.patch.object(dang_nhap, "Game", GameGia),
        ]
        for p in self.cac_patch:
            p.start()

    def tearDown(self):
        for p in self.cac_patch:
            p.stop()

    def _chay(self, da_lam, nang_cap):
        from unittest import mock
        with mock.patch.object(ncnv, "da_lam", lambda ten: da_lam), mock.patch.object(ncnv, "nang_cap", nang_cap):
            self.dang_nhap.LuongDangNhap.nang_cap_sau_dang_nhap(self.luong)

    def test_chua_lam_thi_nang_cap(self):
        self._chay(False, lambda game, ten, *a: self.goi.append((game.hwnd, ten)))
        self.assertEqual(self.goi, [(7, "caychay24")])

    def test_da_lam_thi_bo_qua(self):
        self._chay(True, lambda *a: self.goi.append(a))
        self.assertEqual(self.goi, [])

    def test_loi_chi_ghi_log(self):
        def loi(*a):
            raise RuntimeError("không mở được hội thoại GIFTCODE")
        self._chay(False, loi)
        self.assertTrue(any("lần đăng nhập sau làm tiếp" in d for d in self.log))

    def test_dang_dung_thi_bao_dung(self):
        self.luong.dung.set()

        def loi(*a):
            raise RuntimeError("dừng")
        with self.assertRaises(self.dang_nhap.LoiDangNhap):
            self._chay(False, loi)


class TestGhiThaoTac(unittest.TestCase):
    def test_khac_vat_pham(self):
        cu = {0: ("10141030", "Bách Bảo Nang", "1"), 3: ("30004622", "Hộp Point", "3")}
        moi = {3: ("30004622", "Hộp Point", "2"), 5: ("10100000", "Thần Khí", "1")}
        self.assertEqual(ghi_thao_tac.khac_vat_pham(cu, moi, "túi"), [
            "túi ô 0: mất Bách Bảo Nang (mã 10141030) x1",
            "túi ô 3: Hộp Point số lượng 3 -> 2",
            "túi ô 5: thêm Thần Khí (mã 10100000) x1",
        ])

    def test_doc_bang_va_chi_so(self):
        self.assertEqual(ghi_thao_tac.doc_bang_vat_pham("2\t10141040\t#cff0000Bách Bảo Rương\t1\nrác\n"),
                         {2: ("10141040", "Bách Bảo Rương", "1")})
        self.assertEqual(ghi_thao_tac.doc_chi_so("SPR=10\nDEX=5\n"), {"SPR": "10", "DEX": "5"})

    def test_ma_boc_ham_khong_boc_ham_chuan_lua(self):
        self.assertIn("select = 1", ghi_thao_tac.MA_BOC_HAM)
        self.assertIn('"click"', ghi_thao_tac.MA_BOC_HAM)


if __name__ == "__main__":
    unittest.main()
