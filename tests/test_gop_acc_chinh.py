import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gop_acc_chinh as gop  # noqa: E402


class TestVatPhamGop(unittest.TestCase):
    def test_dung_danh_sach(self):
        from giao_acc_chinh import la_vat_pham_gop
        for ten in ("Mảnh Ngọc Vip", "Phiếu KNB 100", "Phiếu KNB 500", "Càn Khôn Hồ",
                    "Thiên Mệnh Thần Thạch", "Mảnh Vỡ Trân Thú", "#-09Mảnh vỡ Thiên Ngoại",
                    "Mảnh Vỡ Bảo Thạch", "#-09Mảnh Vỡ Trang Bị VIP"):
            self.assertTrue(la_vat_pham_gop(ten), ten)
        self.assertFalse(la_vat_pham_gop(""))
        self.assertFalse(la_vat_pham_gop("Mảnh Vỡ Thời Trang"))
        self.assertFalse(la_vat_pham_gop("#-09Mảnh Vỡ Thú Cưỡi"))
        self.assertFalse(la_vat_pham_gop("Mảnh Vỡ Trang Bị"))
        self.assertFalse(la_vat_pham_gop("#-09#c33ff99Mảnh Vỡ Thời Trang"))

    def test_liet_ke_viscii_van_loai_manh_vo_thoi_trang(self):
        from bang_ma_viscii import ma_hoa
        from giao_acc_chinh import GiaoAccChinhEngine, la_vat_pham_gop
        raw = b"4\t" + ma_hoa("#-09#c33ff99Mảnh Vỡ Thời Trang") + b"\t7\n"
        raw += b"5\t" + ma_hoa("Mảnh Vỡ Trân Thú") + b"\t5\n"
        hang = GiaoAccChinhEngine._doc_bang_vat(raw)
        self.assertEqual([o for o, _, _ in hang], [4, 5])
        self.assertFalse(la_vat_pham_gop(hang[0][1]))
        self.assertTrue(la_vat_pham_gop(hang[1][1]))

    def test_phieu_nho_khong_gom_2000(self):
        from giao_acc_chinh import la_phieu_nho, la_phieu_cat_tccn, muc_phieu_knb
        self.assertEqual(muc_phieu_knb("Phiếu KNB 100"), 100)
        self.assertEqual(muc_phieu_knb("Phiếu KNB 3K"), 3000)
        self.assertTrue(la_phieu_nho("Phiếu KNB 300"))
        self.assertFalse(la_phieu_nho("Phiếu KNB 2000"))
        self.assertFalse(la_phieu_nho("Mảnh Ngọc Vip"))
        self.assertTrue(la_phieu_cat_tccn("Phiếu KNB 2000"))
        self.assertTrue(la_phieu_cat_tccn("Phiếu KNB 2K"))
        self.assertFalse(la_phieu_cat_tccn("Phiếu KNB 100"))
        self.assertFalse(la_phieu_cat_tccn("Phiếu KNB 3000"))
        self.assertFalse(la_phieu_cat_tccn("Mảnh Ngọc Vip"))

    def test_cong_thuc_20k_30k(self):
        from giao_acc_chinh import la_cong_thuc_phieu
        self.assertTrue(la_cong_thuc_phieu("#-09Phiếu KNB 20K", 20000))
        self.assertTrue(la_cong_thuc_phieu("Phiếu KNB 30000", 30000))
        self.assertFalse(la_cong_thuc_phieu("Phiếu KNB 2K", 20000))
        self.assertFalse(la_cong_thuc_phieu("Phiếu KNB 3K", 30000))

    def test_doi_phieu_can_mot_o_trong(self):
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong._o_trong = lambda: {"base": 0}
        luong._kiem_tra_dung = lambda: None
        luong.in_log = lambda *_: None
        luong.tk_chinh = {"nhan_vat": "chinh"}
        luong._tui_chinh = lambda: {}
        luong._mo_kho = lambda: False
        luong._rut_phieu_nho_tu_kho = lambda: False
        self.assertFalse(luong._chua_o_truoc_doi())
        luong._o_trong = lambda: {"base": 1}
        self.assertTrue(luong._chua_o_truoc_doi())

    def test_dem_phieu_nho_trong_tui(self):
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong._tui_chinh = lambda: {
            ("base", 0): (1, 200, "Phiếu KNB 100"),
            ("base", 1): (2, 50, "Phiếu KNB 300"),
            ("base", 2): (3, 10, "Phiếu KNB 2000"),
        }
        self.assertEqual(luong._so_phieu_nho(), 250)
        self.assertEqual(luong._so_phieu_theo_muc(), {100: 200, 300: 50})

    def test_o_doi_phieu_du_hai_loai(self):
        import giao_acc_chinh as gac
        self.assertEqual(gac.O_DOI_PHIEU, (6, 7))
        self.assertEqual(gac.O_PHIEU_KNB_20K, 6)
        self.assertEqual(gac.O_PHIEU_KNB_30K, 7)
        self.assertEqual(gac.MA_PHIEU_KNB_20K, 30004614)
        self.assertEqual(gac.MA_PHIEU_KNB_30K, 30004615)
        self.assertIn("_Clicked", gac.MA_BAM_O_DOI)
        self.assertIn('mo .. "_Clicked"', gac.MA_BAM_O_DOI)
        self.assertIn("DuiHuanUI_Bk_Icon", gac.MA_BAM_O_DOI)
        self.assertIn("_OK_Clicked", gac.MA_XAC_NHAN_DOI)

    def test_o_phieu_20k_30k_co_dinh_theo_ghi(self):
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        self.assertEqual(luong._o_phieu_20k_30k("XiaoXiang_DuiHuanUI2"), [6, 7])
        self.assertEqual(luong._tim_o_phieu_20k_30k("XiaoXiang_DuiHuanUI2"), [6, 7])
        self.assertEqual(luong._o_phieu_20k_30k_tu_chuoi(
            "3\tPhiếu khác\n7\t#-09Phiếu KNB 20K\n15\tPhiếu KNB 30K\n"), [7, 15])

    def test_tccn_dung_action_button_va_select(self):
        import giao_acc_chinh as gac
        self.assertIn("Packet_Temporary_ItemID", gac.MA_LIET_KE_TCCN)
        self.assertIn("Packet_Temporary_ItemNum_Data", gac.MA_LIET_KE_TCCN)
        self.assertIn("UpdateProductAction", gac.MA_LIET_KE_TCCN)
        self.assertIn("Packet_Temporary_Select", gac.MA_RUT_TCCN)
        self.assertIn("g_EveryNum", gac.MA_RUT_TCCN)
        self.assertIn("setupvalue(sel, i, 250)", gac.MA_RUT_TCCN)
        self.assertIn("sel({i})", gac.MA_RUT_TCCN)
        self.assertNotIn("GetPixelRect", gac.MA_RUT_TCCN)
        self.assertNotIn("DoSubAction", gac.MA_RUT_TCCN)
        self.assertNotIn("Packet_Temporary:EnumItem", gac.MA_LIET_KE_TCCN)
        self.assertIn("Bank:MoveItemToPacket", gac.MA_RUT_KHO)
        self.assertIn("Bank:IsPresent()", gac.MA_RUT_KHO)
        self.assertIn("Bank:EnumItem", gac.MA_RUT_KHO)
        self.assertIn("Bank:EnumItem", gac.MA_TOA_DO_O_KHO)
        self.assertIn("GetPixelRect", gac.MA_TOA_DO_O_KHO)
        self.assertIn("Bank_Env", gac.MA_TOA_DO_O_KHO)
        self.assertIn("cung_mon", gac.MA_TOA_DO_O_KHO)
        self.assertIn('"Bank_Item" .. (i + 1)', gac.MA_TOA_DO_O_KHO_THAT)
        self.assertNotIn("MoveItemToPacket", gac.MA_TOA_DO_O_KHO)
        from keo_tha import bam_phai
        self.assertTrue(callable(bam_phai))
        diem, ten_nut = gac.GiaoAccChinhEngine._parse_toa_do_o_kho(b"1|10,30,40,60|Bank_Item0")
        self.assertEqual(diem, (20, 50))
        self.assertEqual(ten_nut, "Bank_Item0")
        diem0, _ = gac.GiaoAccChinhEngine._parse_toa_do_o_kho(b"0|1,5,2,8|Packet_Temporary_Space_Line1_Row1_button")
        self.assertEqual(diem0, (3, 5))

    def test_het_do_gop_nguon_can_tui_va_hai_kho(self):
        import giao_acc_chinh as gac
        from unittest.mock import MagicMock
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.in_log = lambda *_: None
        game = MagicMock()
        game.lua.chay.return_value = b"x"

        luong._do_can_giao = lambda *_: [("base", 0)]
        self.assertFalse(luong._het_do_gop_nguon(game, "nv"))

        luong._do_can_giao = lambda *_: []
        luong._mo_tccn = lambda _g: True
        luong._mo_kho_game = lambda _g, _t: True
        lan = {"n": 0}

        def doc_con(_raw):
            lan["n"] += 1
            return [(1, "Phiếu KNB 100", 10)] if lan["n"] == 1 else []

        luong._doc_bang_vat = doc_con
        self.assertFalse(luong._het_do_gop_nguon(game, "nv"))

        luong._doc_bang_vat = lambda _raw: []
        self.assertTrue(luong._het_do_gop_nguon(game, "nv"))

        luong._doc_bang_vat = lambda _raw: "khong"
        self.assertFalse(luong._het_do_gop_nguon(game, "nv"))

    def test_rut_kho_fail_con_mon_tra_none(self):
        import giao_acc_chinh as gac
        from unittest.mock import MagicMock
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.in_log = lambda *_: None
        luong.dung = MagicMock()
        luong.dung.wait = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        luong._o_trong_dao_cu = lambda _g: 10
        luong._tong_trong_tui = lambda _g, _t: 0
        luong._do_can_giao = lambda *_: []
        game = MagicMock()
        luong._liet_ke_vat = lambda _g, _ma: [(0, "Thiên Mệnh Thần Thạch", 1)]
        luong._doc_bang_vat = lambda _raw: [(0, "Thiên Mệnh Thần Thạch", 1)]
        game.lua.chay = MagicMock(return_value=b"khong")
        self.assertIsNone(
            luong._rut_mot_kho(
                game, "nv", "Thương khố", lambda _g: True, "liet_ke", "rut_{i}", 0.1,
            )
        )

    def test_rut_kho_chuot_phai_tui_tang_thi_ok(self):
        import giao_acc_chinh as gac
        from unittest.mock import MagicMock
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.in_log = lambda *_: None
        luong.dung = MagicMock()
        luong.dung.wait = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        luong._o_trong_dao_cu = lambda _g: 10
        dem = {"n": 0}

        def tong(_g, _t):
            dem["n"] += 1
            return 0 if dem["n"] <= 2 else 5

        luong._tong_trong_tui = tong
        game = MagicMock()
        lan_liet = {"n": 0}

        def liet(_g, _ma):
            lan_liet["n"] += 1
            return [(0, "Thiên Mệnh Thần Thạch", 5)] if lan_liet["n"] == 1 else []

        luong._liet_ke_vat = liet
        game.lua.chay = MagicMock(return_value=b"1")
        self.assertTrue(
            luong._rut_mot_kho(
                game, "nv", "Thương khố", lambda _g: True, "liet_ke", "rut_{i}", 0.1,
            )
        )

    def test_rut_kho_lay_het_nhieu_o(self):
        import giao_acc_chinh as gac
        from unittest.mock import MagicMock
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.in_log = lambda *_: None
        luong.dung = MagicMock()
        luong.dung.wait = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        luong._o_trong_dao_cu = lambda _g: 20
        luong._tong_trong_tui = lambda _g, _t: 1
        luong._cho_tui_tang = lambda *_a, **_k: True
        luong._ruong_mat_o = lambda *_a, **_k: True
        con = {"ds": [(0, "A", 1), (1, "B", 1), (2, "C", 1)]}

        def liet(_g, _ma):
            return list(con["ds"])

        def rut(ma, *a, **k):
            if isinstance(ma, str) and ma.startswith("rut_"):
                chi_so = int(ma.split("_", 1)[1])
                con["ds"] = [(i, t, s) for i, t, s in con["ds"] if i != chi_so]
                con["ds"] = [(j, t, s) for j, (_, t, s) in enumerate(con["ds"])]
            return b"1"

        luong._liet_ke_vat = liet
        game = MagicMock()
        game.lua.chay = rut
        self.assertTrue(
            luong._rut_mot_kho(
                game, "nv", "Thương khố", lambda _g: True, "liet_ke", "rut_{i}", 0.1,
            )
        )
        self.assertEqual(con["ds"], [])

    def test_mot_truong_nhom_khong_bo_qua_khi_rut_none(self):
        import inspect
        import giao_acc_chinh as gac
        src_rut = inspect.getsource(gac.GiaoAccChinhEngine._rut_mot_kho)
        self.assertIn("while True:", src_rut)
        self.assertIn("khop[0]", src_rut)
        self.assertIn("return None", src_rut)
        src_pha = inspect.getsource(gac.GiaoAccChinhEngine._mot_truong_nhom)
        self.assertIn("if kq_rut is None:", src_pha)
        self.assertIn("vẫn giao", src_pha)


class TestDonTuiGop(unittest.TestCase):
    def test_thu_tu_cat_doi_cat_ruong(self):
        import giao_acc_chinh as gac
        thu_tu = []

        class Luong(gac.GiaoAccChinhEngine):
            pass

        luong = Luong.__new__(Luong)
        luong.chi_giao_gop = True
        luong.tk_chinh = {"nhan_vat": "chinh"}
        luong.in_log = lambda *_: None
        luong.bao_trang_thai = lambda *_: None
        # Sau kho vẫn chật → gọi thêm TCCN tạm rồi đủ chỗ.
        trang = {"n": 0}

        def o_trong():
            trang["n"] += 1
            if trang["n"] <= 2:
                return {"base": 0, "material": 5}
            return {"base": 10, "material": 5}

        luong._o_trong = o_trong

        def cat_tccn(cat_bat_ky=False):
            thu_tu.append(("tccn", cat_bat_ky))

        luong._cat_tccn = cat_tccn
        luong._hop_thanh_phieu = lambda: thu_tu.append("doi")
        luong._cat_kho = lambda **kw: thu_tu.append(("kho", kw)) or True
        luong._kiem_tra_dung = lambda: None

        luong._don_tui_chinh()
        self.assertEqual(thu_tu, [
            ("tccn", False), "doi", ("kho", {"cat_het": True}), ("tccn", True),
        ])

    def test_giao_dich_chi_cat_tccn_va_kho_khong_doi_phieu(self):
        import giao_acc_chinh as gac
        thu_tu = []

        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.chi_giao_gop = False
        luong.tk_chinh = {"nhan_vat": "chinh"}
        luong.in_log = lambda *_: None
        luong.bao_trang_thai = lambda *_: None
        trang = {"n": 0}

        def o_trong():
            trang["n"] += 1
            if trang["n"] <= 2:
                return {"base": 0, "material": 5}
            return {"base": 10, "material": 5}

        luong._o_trong = o_trong
        luong._cat_tccn = lambda cat_bat_ky=False: thu_tu.append(("tccn", cat_bat_ky))
        luong._hop_thanh_phieu = lambda: thu_tu.append("doi")
        luong._cat_kho = lambda **kw: thu_tu.append(("kho", kw)) or True
        luong._rut_mot_kho = lambda *a, **k: thu_tu.append("rut")
        luong._co_phieu_nho = lambda: True

        luong._don_tui_chinh()
        self.assertEqual(thu_tu, [
            ("tccn", False), ("kho", {"cat_het": True}), ("tccn", True),
        ])
        self.assertNotIn("doi", thu_tu)
        self.assertNotIn("rut", thu_tu)

    def test_don_tui_ruong_day_cat_tam_tccn_van_that_bai(self):
        import giao_acc_chinh as gac
        thu_tu = []
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.chi_giao_gop = True
        luong.tk_chinh = {"nhan_vat": "Gao"}
        logs = []
        luong.in_log = logs.append
        luong.bao_trang_thai = lambda *_: None
        luong._o_trong = lambda: {"base": 0, "material": 30}
        luong._cat_tccn = lambda cat_bat_ky=False: thu_tu.append(("tccn", cat_bat_ky))
        luong._hop_thanh_phieu = lambda: thu_tu.append("doi")
        luong._cat_kho = lambda **kw: thu_tu.append(("kho", kw)) or True
        with self.assertRaises(gac.LoiGiaoAccChinh) as cm:
            luong._don_tui_chinh()
        self.assertIn("đã đầy", str(cm.exception))
        self.assertEqual(thu_tu, [
            ("tccn", False), "doi", ("kho", {"cat_het": True}), ("tccn", True),
        ])
        self.assertTrue(any("cất tạm mọi món" in d for d in logs))

    def test_cat_tccn_bat_ky_gom_phieu_nho(self):
        import giao_acc_chinh as gac
        from unittest.mock import MagicMock
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.chinh = MagicMock()
        luong.in_log = lambda *_: None
        luong.luc_cat = 0.0
        luong._tui_chinh = lambda: {
            ("base", 0): (1, 1, "Mảnh Ngọc Vip"),
            ("base", 1): (2, 10, "Phiếu KNB 100"),
            ("base", 2): (3, 5, "Phiếu KNB 20K"),
        }
        luong._cho = lambda dieu_kien, *_a, **_k: True
        da_cat = []
        luong._cat_mot_o = lambda o, ma: da_cat.append(o) or "1"
        luong.chinh.lua.chay = MagicMock(return_value=b"true")
        luong._cat_tccn(cat_bat_ky=True)
        self.assertEqual(da_cat, [("base", 0), ("base", 1), ("base", 2)])

    def test_cat_kho_gop_gom_ca_phieu(self):
        import giao_acc_chinh as gac
        from unittest.mock import MagicMock

        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.chi_giao_gop = True
        luong.chinh = MagicMock()
        luong.in_log = lambda *_: None
        luong._tui_chinh = lambda: {
            ("base", 0): (1, 1, "Phiếu KNB 100"),
            ("base", 1): (2, 1, "Mảnh Ngọc Vip"),
        }
        luong._mo_kho = lambda: True
        luong.luc_cat = 0.0
        luong.dung = MagicMock()
        luong.dung.wait = lambda *_: None
        luong._cho = lambda dieu_kien, *_a, **_k: dieu_kien()
        da_cat = []

        def cat_mot(o, ma):
            da_cat.append(o)
            return "1"

        luong._cat_mot_o = cat_mot
        luong.chinh.lua.chay = MagicMock(return_value=b"10")
        luong._cat_kho()
        self.assertEqual(set(da_cat), {("base", 0), ("base", 1)})

    def test_cat_tccn_gom_phieu_2000_bo_phieu_nho(self):
        import giao_acc_chinh as gac
        from unittest.mock import MagicMock

        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.chinh = MagicMock()
        luong.in_log = lambda *_: None
        luong.luc_cat = 0.0
        luong._tui_chinh = lambda: {
            ("base", 0): (1, 1, "Mảnh Ngọc Vip"),
            ("base", 1): (2, 5, "Phiếu KNB 2000"),
            ("base", 2): (3, 10, "Phiếu KNB 100"),
            ("base", 3): (4, 2, "Phiếu KNB 2K"),
            ("material", 0): (5, 1, "Đá"),
        }
        luong._cho = lambda dieu_kien, *_a, **_k: True
        da_cat = []

        def cat_mot(o, ma):
            da_cat.append(o)
            self.assertIn("PutInItem", ma)
            return "1"

        luong._cat_mot_o = cat_mot
        luong.chinh.lua.chay = MagicMock(return_value=b"true")
        luong._cat_tccn()
        self.assertEqual(da_cat, [("base", 0), ("base", 1), ("base", 3)])
        self.assertNotIn(("base", 2), da_cat)
        self.assertNotIn(("material", 0), da_cat)


class TestPhaGopAccPhu(unittest.TestCase):
    def test_cac_pha_gop_tui_truoc_ruong_tccn(self):
        import inspect
        import giao_acc_chinh as gac
        src = inspect.getsource(gac.GiaoAccChinhEngine._mot_truong_nhom)
        self.assertIn('("tui", "túi")', src)
        idx_tui = src.index('("tui", "túi")')
        idx_kho = src.index('("kho", "Thương khố")')
        idx_tccn = src.index('("tccn", "Thiên Cơ Cẩm Nang")')
        self.assertLess(idx_tui, idx_kho)
        self.assertLess(idx_kho, idx_tccn)
        self.assertIn('pha in ("kho", "tccn")', src)
        self.assertIn("Thương khố đã trống sau giao", src)
        self.assertIn("sang Thiên Cơ", src)


class TestParseDanhSach(unittest.TestCase):
    def test_hop_le_phay(self):
        ds = gop.parse_danh_sach("a1, pass1, nv1\na2,pass2,nv2")
        self.assertEqual(len(ds), 2)
        self.assertEqual(ds[0][0]["ten_dang_nhap"], "a1")
        self.assertEqual(ds[0][0]["mat_khau"], "pass1")
        self.assertEqual(ds[0][1], "nv1")

    def test_tab_va_bo_comment(self):
        ds = gop.parse_danh_sach("# ghi chú\n\nacc1\tmk1\tnv1")
        self.assertEqual(len(ds), 1)
        self.assertEqual(ds[0][1], "nv1")

    def test_thieu_cot(self):
        with self.assertRaises(ValueError) as ctx:
            gop.parse_danh_sach("only, two")
        self.assertIn("Dòng 1", str(ctx.exception))

    def test_trong(self):
        with self.assertRaises(ValueError):
            gop.parse_danh_sach("  \n# empty\n")


class TestLuuCaiDat(unittest.TestCase):
    def test_gop_vao_cau_hinh_chung(self):
        from unittest.mock import patch
        with patch("gop_acc_chinh.cau_hinh") as mock_ch:
            mock_ch.chung.return_value = {}
            gop.luu_cai_dat(tai_khoan="acc1", danh_sach="a, b, c")
            mock_ch.dat_chung.assert_called_once()
            luu = mock_ch.dat_chung.call_args[0][0]["gop_acc_chinh"]
            self.assertEqual(luu["tai_khoan"], "acc1")
            self.assertEqual(luu["danh_sach"], "a, b, c")


class TestLuongGopAccChinh(unittest.TestCase):
    def test_cac_tai_khoan(self):
        luong = gop.LuongGopAccChinh.__new__(gop.LuongGopAccChinh)
        luong.tk_chinh = {"ten_dang_nhap": "nhan", "mat_khau": "", "nhan_vat": ""}
        luong.ds_nguon = [({"ten_dang_nhap": "s1", "mat_khau": "x"}, "nv1")]
        luong.tk_da_thoat = {"s2"}
        luong.is_alive = lambda: True
        self.assertEqual(luong.cac_tai_khoan(), {"nhan", "s1", "s2"})

    def test_nhieu_acc_nguon_thi_logout_tru_acc_cuoi(self):
        from unittest.mock import MagicMock, patch
        import giao_acc_chinh as gac
        cd = dict(gop.MAC_DINH, danh_sach="a,b,nv1\nc,d,nv2")
        nguon = [({"ten_dang_nhap": "a"}, "nv1"), ({"ten_dang_nhap": "c"}, "nv2")]
        with patch.object(gop, "cai_dat", return_value=cd), \
                patch.object(gop, "parse_danh_sach", return_value=nguon):
            luong = gop.LuongGopAccChinh(MagicMock())
        self.assertTrue(luong.thoat_sau_giao)
        luong.chi_giao_gop = True
        thu = []

        def mot(_tk, ten):
            thu.append((ten, luong.thoat_sau_giao))
            return True

        luong._vao_acc_chinh = lambda: None
        luong._mot_truong_nhom = mot
        luong._luu_tien_trinh = lambda: None
        luong.tien_trinh = {"da_xong": []}
        luong.in_log = lambda *_: None
        luong.bao_trang_thai = lambda *_: None
        luong.tk_chinh = {"ten_dang_nhap": "nhan", "nhan_vat": "chinh"}
        gac.GiaoAccChinhEngine._chay_giao_don(luong, nguon, "nguon")
        self.assertEqual(thu, [("nv1", True), ("nv2", False)])

    def test_gop_mo_du_hai_client_truoc_khi_dang_nhap(self):
        from unittest.mock import patch
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.chi_giao_gop = True
        luong.dung = type("E", (), {"is_set": lambda self: False})()
        luong.in_log = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        da_mo = []
        with patch.object(gac, "tim_cua_so_game", side_effect=[[{"hwnd": 1}], [{"hwnd": 1}, {"hwnd": 2}]]), \
                patch.object(gac, "mo_game", side_effect=lambda *_a, **_k: da_mo.append(1) or 99), \
                patch.object(gac, "cho_cua_so"), \
                patch.object(gac.cau_hinh, "doc_tai_khoan", return_value={
                    "thu_muc_game": "D:\\game", "giay_cho_truoc_khi_nap_dll": 1}):
            luong._mo_du_hai_client()
        self.assertEqual(da_mo, [1])
        luong.chi_giao_gop = False
        da_mo.clear()
        with patch.object(gac, "mo_game", side_effect=lambda *_a, **_k: da_mo.append(1) or 99):
            luong._mo_du_hai_client()
        self.assertEqual(da_mo, [])

    def test_gop_mo_them_client_khi_xv_da_co_4(self):
        """Song song XV nhóm 4: vẫn mở 2 client gộp dù tổng cửa sổ đã ≥ 2."""
        from unittest.mock import patch
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.chi_giao_gop = True
        luong.dung = type("E", (), {"is_set": lambda self: False})()
        luong.in_log = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        xv = [{"hwnd": 10 + i, "pid": 100 + i} for i in range(4)]
        sau = xv + [{"hwnd": 20}, {"hwnd": 21}]
        da_mo = []
        with patch.object(luong, "_hwnd_giu_xoay_vong", return_value={10, 11, 12, 13}), \
                patch.object(gac, "tim_cua_so_game", side_effect=[xv, sau]), \
                patch.object(gac, "mo_game", side_effect=lambda *_a, **_k: da_mo.append(1) or 99), \
                patch.object(gac, "cho_cua_so"), \
                patch.object(gac.cau_hinh, "doc_tai_khoan", return_value={
                    "thu_muc_game": "D:\\game", "giay_cho_truoc_khi_nap_dll": 1}):
            luong._mo_du_hai_client()
        self.assertEqual(len(da_mo), 2)

    def test_gop_khong_thoat_client_nhom_xv(self):
        from unittest.mock import patch
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.chi_giao_gop = True
        luong.ten_giu_online = set()
        luong.tk_giu_online = set()
        luong.tk_da_thoat = set()
        luong.pid_dieu_khien = set()
        luong.dung = type("D", (), {"is_set": lambda self: False})()
        luong.in_log = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        cua_so = [{"hwnd": 1, "pid": 9, "tieu_de": "Cosato01 - TL"}]
        game = type("G", (), {"thong_tin": lambda self: {"ten": "Cosato01", "tai_khoan": "cosato01"},
                              "lua": object()})()
        with patch.object(luong, "_hwnd_giu_xoay_vong", return_value={1}), \
                patch.object(gac, "tim_cua_so_game", return_value=cua_so), \
                patch.object(gac, "Game", return_value=game), \
                patch.object(gac, "thoat_ve_chon_may_chu") as thoat:
            luong._thoat_cac_client()
        thoat.assert_not_called()

    def test_chon_game_truong_bo_qua_hwnd_xv(self):
        from unittest.mock import patch
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.chi_giao_gop = True
        luong.hwnd_truong = None
        luong.chinh = type("C", (), {"lua": type("L", (), {"hwnd": 100})()})()
        luong._thoat_cac_client = lambda giu=(): None
        cua = [{"hwnd": 11}, {"hwnd": 22}, {"hwnd": 100}]
        with patch.object(luong, "_hwnd_giu_xoay_vong", return_value={11}), \
                patch.object(luong, "_hwnd_dll_san", side_effect=lambda h: h), \
                patch.object(gac, "tim_game_cua_tai_khoan", return_value=None), \
                patch.object(gac, "tim_cua_so_game", return_value=cua):
            hwnd = luong._chon_game_truong({"ten_dang_nhap": "bong1"})
        self.assertEqual(hwnd, 22)

    def test_xac_nhan_phieu_delay(self):
        import inspect
        import giao_acc_chinh as gac
        src = inspect.getsource(gac.GiaoAccChinhEngine._mot_lan_doi_phieu)
        self.assertIn("GIAY_XAC_NHAN_PHIEU", src)
        self.assertIn("GIAY_SAU_CHON_O_DOI", src)
        self.assertNotIn("MA_DOI_DA_CHON", src)
        self.assertEqual(gac.GIAY_XAC_NHAN_PHIEU, 0.5)
        self.assertEqual(gac.GIAY_GIUA_RUT_KHO, 0.5)
        self.assertEqual(gac.GIAY_GIUA_HAI_LAN_CAT, 0.5)
        self.assertIn("ô cố định", gac.GiaoAccChinhEngine._o_phieu_20k_30k.__doc__.lower())

    def test_hop_thanh_chi_bam_o_20k_30k(self):
        """Chỉ bấm ô cố định 6 (20K) rồi 7 (30K) theo ghi tay."""
        from unittest.mock import MagicMock
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.tk_chinh = {"nhan_vat": "Gao"}
        luong.dung = MagicMock()
        luong.dung.wait = lambda *_: None
        luong.dung.is_set = lambda: False
        luong._kiem_tra_dung = lambda: None
        luong.in_log = lambda *_: None
        luong.bao_trang_thai = lambda *_: None
        luong._chua_o_truoc_doi = lambda: True
        luong._rut_phieu_nho_tu_kho = lambda: True
        luong._o_trong = lambda: {"base": 10, "material": 10}
        luong.chinh = MagicMock()
        luong.chinh.lua.chay.return_value = b"true"
        luong._mo_cua_so_doi = lambda _t: "XiaoXiang_DuiHuanUI2"
        bam = []
        luong._co_phieu_nho = lambda: len(bam) < 2
        luong._so_phieu_theo_muc = lambda: ({100: 0, 300: 0} if len(bam) >= 2 else {100: 10, 300: 5})

        def mot(_mo, _ten, o, im_lang=False):
            if o in bam:
                return False
            bam.append(o)
            return True

        luong._mot_lan_doi_phieu = mot
        luong._hop_thanh_phieu()
        self.assertEqual(bam, [6, 7])

    def test_hop_thanh_rut_phieu_truoc_khi_doi(self):
        from unittest.mock import MagicMock
        import giao_acc_chinh as gac
        thu_tu = []
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.tk_chinh = {"nhan_vat": "Gao"}
        luong.dung = MagicMock()
        luong.dung.wait = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        luong.in_log = lambda *_: None
        luong.bao_trang_thai = lambda *_: None
        luong.chinh = MagicMock()
        luong.chinh.lua.chay.return_value = b"true"
        luong._rut_phieu_nho_tu_kho = lambda: thu_tu.append("rut") or True
        luong._co_phieu_nho = lambda: False
        luong._hop_thanh_phieu()
        self.assertEqual(thu_tu, ["rut"])

    def test_rut_phieu_nho_tu_kho_dung_loc_la_phieu_nho(self):
        from unittest.mock import MagicMock
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.tk_chinh = {"nhan_vat": "Gao"}
        luong.chinh = MagicMock()
        luong.in_log = lambda *_: None
        luong._mo_kho = lambda: True
        goi = {}

        def rut(game, ten, ten_kho, mo, ma_liet_ke, ma_rut, giay_cho, loc=None):
            goi["loc"] = loc
            goi["ma_rut"] = ma_rut
            goi["ten_kho"] = ten_kho
            return True

        luong._rut_mot_kho = rut
        self.assertTrue(luong._rut_phieu_nho_tu_kho())
        self.assertIs(goi["loc"], gac.la_phieu_nho)
        self.assertEqual(goi["ten_kho"], "Thương khố")
        self.assertIs(goi["ma_rut"], gac.MA_RUT_KHO)

    def test_hop_thanh_khong_doi_khi_het_o_phieu(self):
        from unittest.mock import MagicMock, patch
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.tk_chinh = {"nhan_vat": "Gao"}
        luong.dung = MagicMock()
        luong.dung.wait = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        logs = []
        luong.in_log = logs.append
        luong.bao_trang_thai = lambda *_: None
        luong._co_phieu_nho = lambda: True
        luong._chua_o_truoc_doi = lambda: True
        luong._rut_phieu_nho_tu_kho = lambda: True
        luong._o_trong = lambda: {"base": 10, "material": 10}
        luong._so_phieu_theo_muc = lambda: {100: 10, 300: 0}
        luong.chinh = MagicMock()
        luong.chinh.lua.chay.return_value = b"true"
        luong._mo_cua_so_doi = lambda _t: "XiaoXiang_DuiHuanUI2"
        bam = []
        luong._mot_lan_doi_phieu = lambda *_a, **_k: bam.append(1) or True
        with patch.object(gac, "O_DOI_PHIEU", ()):
            luong._hop_thanh_phieu()
        self.assertEqual(bam, [])
        self.assertTrue(any("không có khung" in d for d in logs))

    def test_tim_o_phieu_co_dinh_6_7(self):
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        self.assertEqual(luong._tim_o_phieu_20k_30k("XiaoXiang_DuiHuanUI2"), [6, 7])
        self.assertEqual(luong._o_phieu_20k_30k_tu_chuoi(
            "7\tPhiếu KNB 20K\n9\tPhiếu KNB 30K\n"), [7, 9])

    def test_mot_lan_doi_phieu_loi_lua_thi_false(self):
        from unittest.mock import MagicMock
        import giao_acc_chinh as gac
        from lua_game import LoiLua
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.dung = MagicMock()
        luong.dung.wait = lambda *_: None
        luong._so_phieu_theo_muc = lambda: {100: 5, 300: 0}
        luong.in_log = lambda *_: None
        luong.chinh = MagicMock()
        luong.chinh.lua.chay.side_effect = LoiLua("treo")
        self.assertFalse(luong._mot_lan_doi_phieu("XiaoXiang_DuiHuanUI2", "Gao", 6))
