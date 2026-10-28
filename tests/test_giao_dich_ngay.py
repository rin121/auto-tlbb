"""Nút "Giao dịch ngay": đội viên giao đồ cho trưởng nhóm giữa chừng (có hoặc không chạy xoay vòng) rồi đi tiếp."""
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import cau_hinh
import giao_dich_ngay as gdn
import xoay_vong as xv


def _nv(bat_auto=True, bat_pb=True):
    return {"bat_auto": bat_auto, "bat_chuyen_sinh": False,
            "pho_ban_pmp": dict(cau_hinh.MAC_DINH_PHO_BAN_PMP, bat=bat_pb, xoay_vong=True,
                                hom_nay={"ngay": "2026-10-26", "so_vong": 2, "so_het_luot": False,
                                         "het_luot": False, "st_vong": 1, "st_het": False})}


class TestGiaoDichNgay(unittest.TestCase):
    def setUp(self):
        p = patch.object(cau_hinh, "_ghi_json_an_toan", lambda duong_dan, chu: None)
        p.start()
        self.addCleanup(p.stop)
        p2 = patch.dict(cau_hinh._du_lieu, {"nhan_vat": {"Truong": _nv(), "DV1": _nv(), "DV2": _nv(bat_pb=False)}})
        p2.start()
        self.addCleanup(p2.stop)
        p3 = patch.object(xv, "GIAY_CHO_DUNG_AUTO_TRUOC_GIAO_DICH", 0)
        p3.start()
        self.addCleanup(p3.stop)
        with patch.object(xv, "cac_tai_khoan_dang_tich", return_value=[]):
            self.luong = xv.LuongXoayVong(MagicMock(), 1, False, True)
        self.truong = SimpleNamespace(ten="Truong", pid=1)
        self.dv1 = SimpleNamespace(ten="DV1", pid=2)
        self.dv2 = SimpleNamespace(ten="DV2", pid=3)
        self.thanh_vien = [self.truong, self.dv1, self.dv2]

    def nv(self, ten):
        return cau_hinh._du_lieu["nhan_vat"][ten]

    def test_chua_chay_hoac_chua_vao_pho_ban_thi_tu_choi(self):
        self.assertFalse(self.luong.giao_dich_ngay())
        with patch.object(self.luong, "is_alive", return_value=True):
            self.assertFalse(self.luong.giao_dich_ngay())
            self.luong.thanh_vien_dang_pb = self.thanh_vien
            self.assertTrue(self.luong.giao_dich_ngay())
        self.assertTrue(self.luong.yeu_cau_giao_dich.is_set())

    def test_tam_dung_va_bat_lai_giu_bo_dem(self):
        da_luu = self.luong._tam_dung_auto(self.thanh_vien)
        for ten in ("Truong", "DV1", "DV2"):
            self.assertFalse(self.nv(ten)["bat_auto"])
            self.assertFalse(self.nv(ten)["pho_ban_pmp"]["bat"])
        self.nv("Truong")["pho_ban_pmp"]["hom_nay"]["so_vong"] = 3
        self.luong._bat_lai_auto(da_luu)
        self.assertTrue(self.nv("Truong")["bat_auto"])
        self.assertTrue(self.nv("Truong")["pho_ban_pmp"]["bat"])
        self.assertFalse(self.nv("DV2")["pho_ban_pmp"]["bat"])
        self.assertTrue(self.nv("DV2")["pho_ban_pmp"]["xoay_vong"])
        self.assertEqual(self.nv("Truong")["pho_ban_pmp"]["hom_nay"]["so_vong"], 3)

    def test_doi_vien_giao_cho_truong_khi_dang_tat_auto(self):
        luc_giao = []

        def chuyen_do(tv, truong, mo_ta):
            luc_giao.append((tv.ten, truong.ten, self.nv(tv.ten)["bat_auto"], set(self.luong.pid_dieu_khien)))
        with patch.object(self.luong, "_tv_dang_choi", return_value=True), \
                patch.object(self.luong, "_doi_vien_co_do", side_effect=lambda ds, mo_ta: ds), \
                patch.object(self.luong, "_tap_trung") as tap_trung, \
                patch.object(self.luong, "_chuyen_do", side_effect=chuyen_do):
            self.luong._giao_dich_giua_chung(self.thanh_vien, self.truong, "Nhóm 1 round 1")
        tap_trung.assert_called_once()
        self.assertEqual(tap_trung.call_args[0][0], [self.dv1, self.dv2])
        self.assertEqual([(t, tr, auto) for t, tr, auto, _ in luc_giao],
                         [("DV1", "Truong", False), ("DV2", "Truong", False)])
        self.assertEqual(luc_giao[0][3], {1, 2, 3})
        self.assertEqual(self.luong.pid_dieu_khien, set())
        self.assertTrue(self.nv("DV1")["bat_auto"])
        self.assertTrue(self.nv("DV1")["pho_ban_pmp"]["bat"])

    def test_loi_giua_chung_van_bat_lai_auto(self):
        with patch.object(self.luong, "_tv_dang_choi", return_value=True), \
                patch.object(self.luong, "_doi_vien_co_do", side_effect=lambda ds, mo_ta: ds), \
                patch.object(self.luong, "_tap_trung", side_effect=RuntimeError("x")):
            with self.assertRaises(RuntimeError):
                self.luong._giao_dich_giua_chung(self.thanh_vien, self.truong, "Nhóm 1 round 1")
        self.assertTrue(self.nv("Truong")["bat_auto"])
        self.assertTrue(self.nv("DV1")["pho_ban_pmp"]["bat"])
        self.assertEqual(self.luong.pid_dieu_khien, set())

    def _co_game(self, *cac_tv):
        for tv in cac_tv:
            tv.game = SimpleNamespace(lua=SimpleNamespace(pid=tv.pid))
            tv.anh_tui = {("base", 1): 1}

    def test_khong_ai_co_do_thi_khong_dung_pho_ban(self):
        self._co_game(self.dv1, self.dv2)
        with patch.object(self.luong, "_tv_dang_choi", return_value=True), \
                patch.object(xv, "o_do_moi", return_value=[]), \
                patch.object(self.luong, "_tam_dung_auto") as tam_dung, \
                patch.object(self.luong, "_tap_trung") as tap_trung, \
                patch.object(self.luong, "_chuyen_do") as chuyen_do:
            self.luong._giao_dich_giua_chung(self.thanh_vien, self.truong, "Nhóm 1 round 1")
        tam_dung.assert_not_called()
        tap_trung.assert_not_called()
        chuyen_do.assert_not_called()

    def test_chi_doi_vien_co_do_moi_giao_dich(self):
        self._co_game(self.dv1, self.dv2)
        with patch.object(self.luong, "_tv_dang_choi", return_value=True), \
                patch.object(xv, "o_do_moi", side_effect=lambda lua, anh: [("base", 5)] if lua.pid == 3 else []), \
                patch.object(self.luong, "_tap_trung") as tap_trung, \
                patch.object(self.luong, "_chuyen_do") as chuyen_do:
            self.luong._giao_dich_giua_chung(self.thanh_vien, self.truong, "Nhóm 1 round 1")
        self.assertEqual(tap_trung.call_args[0][0], [self.dv2])
        self.assertEqual([c.args[0] for c in chuyen_do.call_args_list], [self.dv2])

    def test_khong_co_doi_vien_trong_game_thi_bo_qua(self):
        with patch.object(self.luong, "_tv_dang_choi", side_effect=lambda tv: tv is self.truong), \
                patch.object(self.luong, "_chuyen_do") as chuyen_do:
            self.luong._giao_dich_giua_chung(self.thanh_vien, self.truong, "Nhóm 1 round 1")
        chuyen_do.assert_not_called()
        self.assertTrue(self.nv("DV1")["bat_auto"])


class TestNhomTiepTheo(unittest.TestCase):
    def setUp(self):
        with patch.object(xv, "cac_tai_khoan_dang_tich", return_value=[]):
            self.luong = xv.LuongXoayVong(MagicMock(), 1, False, False)
        self.truong = SimpleNamespace(ten="Truong", pid=1)
        self.dv1 = SimpleNamespace(ten="DV1", pid=2)
        self.dv2 = SimpleNamespace(ten="DV2", pid=3)
        self.thanh_vien = [self.truong, self.dv1, self.dv2]

    def test_chi_nhan_khi_dang_cho_nhom_hoac_dang_pho_ban(self):
        self.assertFalse(self.luong.nhom_tiep_theo())
        with patch.object(self.luong, "is_alive", return_value=True):
            self.assertFalse(self.luong.nhom_tiep_theo())
            self.luong._dang_cho_du_nhom = True
            self.assertTrue(self.luong.nhom_tiep_theo())
            self.luong._dang_cho_du_nhom = False
            self.luong.yeu_cau_nhom_tiep.clear()
            self.luong.thanh_vien_dang_pb = self.thanh_vien
            self.assertTrue(self.luong.nhom_tiep_theo())
        self.assertTrue(self.luong.yeu_cau_nhom_tiep.is_set())

    def test_dang_pho_ban_bam_thi_dung_va_bao_bo_qua(self):
        self.luong.yeu_cau_nhom_tiep.set()
        with patch.object(self.luong, "_xong_pho_ban", return_value=False):
            self.assertTrue(self.luong._cho_xong_pho_ban(self.thanh_vien, self.truong, None, "Nhóm 5 round 1"))
        self.assertFalse(self.luong.yeu_cau_nhom_tiep.is_set())

    def test_xong_binh_thuong_khong_bo_qua(self):
        with patch.object(self.luong, "_xong_pho_ban", return_value=True):
            self.assertFalse(self.luong._cho_xong_pho_ban(self.thanh_vien, self.truong, None, "Nhóm 5 round 1"))

    def test_dang_cho_lap_nhom_bam_thi_bo_round(self):
        self.luong.yeu_cau_nhom_tiep.set()
        with patch.object(self.luong, "_du_nhom", return_value=False):
            self.assertFalse(self.luong._cho_du_nhom_truoc_pb("Nhóm 5 round 1", self.truong, self.thanh_vien, []))
        self.assertFalse(self.luong._dang_cho_du_nhom)
        self.assertFalse(self.luong.yeu_cau_nhom_tiep.is_set())

    def test_chi_doi_vien_con_trong_game_giao_dich(self):
        with patch.object(self.luong, "_tv_dang_choi", side_effect=lambda tv: tv is not self.dv2):
            self.assertEqual(self.luong._doi_vien_giao_khi_bo_qua("m", self.truong, self.thanh_vien), [self.dv1])
        with patch.object(self.luong, "_tv_dang_choi", return_value=True):
            self.assertEqual(self.luong._doi_vien_giao_khi_bo_qua("m", self.truong, self.thanh_vien),
                             [self.dv1, self.dv2])
        with patch.object(self.luong, "_tv_dang_choi", side_effect=lambda tv: tv is not self.truong):
            self.assertEqual(self.luong._doi_vien_giao_khi_bo_qua("m", self.truong, self.thanh_vien), [])


def _luong(ten, pid, anh_tui=None, trong_game=True):
    return SimpleNamespace(ten=ten, dang_trong_game=trong_game, anh_tui=anh_tui, anh_tui_cua=ten if anh_tui else None,
                           game=SimpleNamespace(lua=SimpleNamespace(pid=pid)))


class TestChiaDoi(unittest.TestCase):
    def test_chia_theo_nhom_trong_game(self):
        a, b, c, d, e = (_luong(t, i) for i, t in enumerate(["TruongA", "DvA", "TruongB", "DvB", "MotMinh"]))
        nhom = {"TruongA": ["TruongA", "DvA", "NguoiNgoai"], "DvA": ["TruongA", "DvA", "NguoiNgoai"],
                "TruongB": ["TruongB", "DvB"], "DvB": ["truongb", "DvB"], "MotMinh": []}
        cac_doi = gdn.chia_doi([a, b, c, d, e], lambda l: nhom[l.ten])
        self.assertEqual(cac_doi, [(a, [b]), (c, [d])])

    def test_truong_khong_trong_auto_thi_bo(self):
        dv = _luong("Dv", 1)
        self.assertEqual(gdn.chia_doi([dv], lambda l: ["NguoiNgoai", "Dv"]), [])

    def test_doc_nhom_loi(self):
        self.assertEqual(gdn.chia_doi([_luong("A", 1)], lambda l: None), [])


class TestGiaoDichNgayKhongXoayVong(unittest.TestCase):
    def setUp(self):
        p = patch.object(cau_hinh, "_ghi_json_an_toan", lambda duong_dan, chu: None)
        p.start()
        self.addCleanup(p.stop)
        p2 = patch.dict(cau_hinh._du_lieu, {"nhan_vat": {"Truong": _nv(), "DV1": _nv(), "DV2": _nv(bat_pb=False)}})
        p2.start()
        self.addCleanup(p2.stop)
        p3 = patch.object(gdn, "GIAY_CHO_DUNG_AUTO", 0)
        p3.start()
        self.addCleanup(p3.stop)
        self.bao_cao = []
        p4 = patch.object(gdn.bao_cao_giao_dich, "ghi_va_bao",
                          lambda in_log, nhom, giao, nhan, chi_tiet: self.bao_cao.append((nhom, giao, nhan, chi_tiet)))
        p4.start()
        self.addCleanup(p4.stop)
        self.truong = _luong("Truong", 1, {("base", 1): 1})
        self.dv1 = _luong("DV1", 2, {("base", 1): 1})
        self.dv2 = _luong("DV2", 3, {("base", 1): 1})
        self.ngoai = _luong("ChuaVaoGame", 4, trong_game=False)
        self.nhom = {"Truong": ["Truong", "DV1", "DV2"], "DV1": ["Truong", "DV1", "DV2"],
                     "DV2": ["Truong", "DV1", "DV2"]}

    def nv(self, ten):
        return cau_hinh._du_lieu["nhan_vat"][ten]

    def tao_luong(self):
        luong = gdn.LuongGiaoDichNgay([self.truong, self.dv1, self.dv2, self.ngoai], MagicMock())
        luong._doc_thanh_vien = lambda l: self.nhom.get(l.ten)
        return luong

    def test_giao_cho_truong_khi_tat_auto_roi_bat_lai(self):
        luong = self.tao_luong()
        da_giao = []

        class GiaoDichGia:
            def __init__(gd, dua, nhan, ten_dua, ten_nhan, in_log, nen_dung):
                gd.ten_dua, gd.ten_nhan = ten_dua, ten_nhan
                gd.chi_tiet = []

            def chuyen(gd, cac_o):
                gd.chi_tiet.append(("Bảo thạch", 3))
                da_giao.append((gd.ten_dua, gd.ten_nhan, cac_o, self.nv(gd.ten_dua)["bat_auto"],
                                luong.dang_dieu_khien(2), set(luong.pid_dieu_khien)))
        with patch.object(gdn, "GiaoDich", GiaoDichGia), \
                patch.object(gdn, "o_do_moi", return_value=[("base", 5)]), \
                patch.object(luong, "is_alive", return_value=True):
            luong._chay()
        self.assertEqual([(d, n, o, auto) for d, n, o, auto, _, _ in da_giao],
                         [("DV1", "Truong", [("base", 5)], False), ("DV2", "Truong", [("base", 5)], False)])
        self.assertTrue(da_giao[0][4])
        self.assertEqual(da_giao[0][5], {1, 2, 3})
        self.assertEqual(self.bao_cao, [("Giao dịch ngay (nhóm Truong)", "DV1", "Truong", [("Bảo thạch", 3)]),
                                        ("Giao dịch ngay (nhóm Truong)", "DV2", "Truong", [("Bảo thạch", 3)])])
        self.assertEqual(luong.pid_dieu_khien, set())
        self.assertTrue(self.nv("DV1")["bat_auto"])
        self.assertTrue(self.nv("DV1")["pho_ban_pmp"]["bat"])
        self.assertFalse(self.nv("DV2")["pho_ban_pmp"]["bat"])
        self.assertEqual(self.nv("Truong")["pho_ban_pmp"]["hom_nay"]["so_vong"], 2)

    def test_khong_co_nhom_thi_khong_tat_auto(self):
        self.nhom = {}
        luong = self.tao_luong()
        with patch.object(gdn, "GiaoDich") as gd:
            luong._chay()
        gd.assert_not_called()
        self.assertTrue(self.nv("DV1")["bat_auto"])

    def test_chua_chup_tui_thi_bo_qua(self):
        self.dv1.anh_tui = None
        luong = self.tao_luong()
        with patch.object(gdn, "GiaoDich") as gd, patch.object(gdn, "o_do_moi", return_value=[("base", 5)]):
            luong._chay()
        self.assertEqual([c.args[2] for c in gd.call_args_list], ["DV2"])

    def test_khong_ai_co_do_thi_khong_tam_dung_auto(self):
        luong = self.tao_luong()
        with patch.object(gdn, "GiaoDich") as gd, patch.object(gdn, "o_do_moi", return_value=[]), \
                patch.object(gdn, "tam_dung_auto") as tam_dung:
            luong._chay()
        gd.assert_not_called()
        tam_dung.assert_not_called()

    def test_chi_doi_vien_co_do_thi_giao(self):
        luong = self.tao_luong()
        with patch.object(gdn, "GiaoDich") as gd, \
                patch.object(gdn, "o_do_moi", side_effect=lambda lua, anh: [("base", 5)] if lua.pid == 3 else []):
            luong._chay()
        self.assertEqual([c.args[2] for c in gd.call_args_list], ["DV2"])

    def test_loi_giao_dich_van_bat_lai_auto(self):
        luong = self.tao_luong()
        with patch.object(gdn, "o_do_moi", side_effect=RuntimeError("x")):
            with self.assertRaises(RuntimeError):
                luong._chay()
        self.assertTrue(self.nv("Truong")["bat_auto"])
        self.assertEqual(luong.pid_dieu_khien, set())


class TestAnhTuiGoc(unittest.TestCase):
    """Ảnh túi gốc lưu theo ngày: dừng / chạy lại / vào lại game không chụp lại, đồ nhặt trước đó vẫn là đồ mới."""

    def setUp(self):
        import os
        import tempfile
        self.thu_muc = tempfile.mkdtemp()
        self.file = os.path.join(self.thu_muc, "anh_tui_goc.json")
        self.tui = {("base", 0): (100, 1, "Hộp"), ("base", 1): (200, 2, "Đá")}

    def tearDown(self):
        import shutil
        shutil.rmtree(self.thu_muc, ignore_errors=True)

    def _anh(self, ten, ngay):
        import giao_dich
        from datetime import date
        with patch.object(giao_dich, "doc_tui", lambda lua: dict(self.tui)):
            return giao_dich.anh_tui_goc(ten, None, self.file, date(*ngay))

    def test_chup_lan_dau_roi_dung_lai_trong_ngay(self):
        dau = self._anh("DV1", (2026, 10, 28))
        self.assertEqual(dau, {("base", 100): 1, ("base", 200): 2})
        self.tui[("base", 2)] = (300, 5, "Đồ PMP")
        self.assertEqual(self._anh("dv1", (2026, 10, 28)), dau)
        self.assertNotEqual(self._anh("DV2", (2026, 10, 28)), dau)

    def test_sang_ngay_moi_thi_chup_lai(self):
        self._anh("DV1", (2026, 10, 28))
        self.tui[("base", 2)] = (300, 5, "Đồ PMP")
        self.assertIn(("base", 300), self._anh("DV1", (2026, 10, 29)))


if __name__ == "__main__":
    unittest.main()
