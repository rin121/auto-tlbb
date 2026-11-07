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
        self.assertTrue(g.la_cua_so_quan_ly_gauto("GAuto_2025"))
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
                patch.object(g, "_bam_chuot", lambda h, diem, cho: bang.bam(diem)), patch.object(g, "CHUOT_AO", False):
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

    def test_loi_che_o_dau_dong_thi_chua_thao_tac(self):
        """VM/màn nhỏ: GAuto bị che lúc tích ô đầu dòng — cho AutoHoc thử lại khung, không bỏ cả khung."""
        with patch.object(g, "kiem_tra_quyen", lambda h: None), \
                patch.object(g, "dat_dau_dong", side_effect=g.LoiGautoAcTac(
                    "cửa sổ GAuto đang bị cửa sổ khác che chỗ ô đầu dòng nhân vật")):
            with self.assertRaises(g.LoiGautoAcTac) as ng:
                g.dat_cai_dat_ac_tac(1, {}, "caychay32")
        self.assertFalse(getattr(ng.exception, "da_thao_tac", False))

    def test_loi_quyen_thi_chua_thao_tac(self):
        with patch.object(g, "kiem_tra_quyen", side_effect=g.LoiGautoAcTac(g.THONG_BAO_CAN_ADMIN)):
            with self.assertRaises(g.LoiGautoAcTac) as ng:
                g.dat_cai_dat_ac_tac(1, {}, "caychay32")
        self.assertFalse(getattr(ng.exception, "da_thao_tac", False))


class TestChuotAo(unittest.TestCase):
    """GA-10: bấm GAuto bằng chuột ảo (không di con trỏ thật); không ăn thì tự dùng chuột thật, báo log 1 lần."""

    def setUp(self):
        self.tt = {"v": False, "sel": 0}
        self.that = []
        for p in (patch.object(g, "_noi_len", lambda h: nullcontext()),
                  patch.object(g, "_muon_chuot", lambda h, v: nullcontext()),
                  patch.object(g, "_DA_BAO_CHUOT_THAT", set()), patch.object(g, "_CHO_BAO", []),
                  patch.object(g, "CHUOT_AO", True)):
            p.start()
            self.addCleanup(p.stop)

    def _bam(self, ao_an):
        def ao(h, diem, he_so=0):
            if ao_an:
                self.tt["v"] = True

        def that(h, diem, cho=""):
            self.that.append(cho)
            self.tt["v"] = True
        with patch.object(g, "_bam_ao", ao), patch.object(g, "_bam_chuot", that):
            return g._bam_ao_hoac_that(1, 2, (10, 10), "ô «Ác Tặc»", lambda: self.tt["v"], giay=0.2)

    def test_chuot_ao_an_thi_khong_dung_chuot_that(self):
        self.assertEqual(self._bam(ao_an=True), "ảo")
        self.assertEqual(self.that, [])

    def test_chuot_ao_khong_an_thi_dung_chuot_that_bao_mot_lan(self):
        self.assertEqual(self._bam(ao_an=False), "thật")
        self.tt["v"] = False
        self.assertEqual(self._bam(ao_an=False), "thật")
        self.assertEqual(len(self.that), 2)
        log = []
        g.rut_bao_chuot(log.append)
        self.assertEqual(log, ["GAuto không nhận chuột ảo ở ô «Ác Tặc», dùng chuột thật"])

    def _chon_map(self, ao_an):
        def gui(h, msg, w, l):
            return self.tt["sel"] if msg == g.win32con.CB_GETCURSEL else 0

        def chon_dong_map(hc, info, dich, bam):
            if bam is g._bam_ao:
                if ao_an:
                    self.tt["sel"] = dich
            else:
                self.that.append("map")
                self.tt["sel"] = dich
            return True
        with patch.object(g, "cac_map", return_value=["Kiếm Các", "Tung Sơn"]), \
                patch.object(g.win32gui, "SendMessage", gui), \
                patch.object(g.ctypes.windll.user32, "GetComboBoxInfo", return_value=1), \
                patch.object(g, "_chon_dong_map", chon_dong_map), patch.object(g, "GIAY_GIU_MAP", 0):
            return g.chon_map(1, 5, "Tung Sơn")

    def test_chon_map_chuot_ao(self):
        self.assertEqual(self._chon_map(ao_an=True), "ảo")
        self.assertEqual(self.that, [])

    def test_chon_map_chuot_ao_khong_an_thi_chuot_that(self):
        self.assertEqual(self._chon_map(ao_an=False), "thật")
        self.assertEqual(self.that, ["map"])
        log = []
        g.rut_bao_chuot(log.append)
        self.assertEqual(log, ["GAuto không nhận chuột ảo ở ô Map, dùng chuột thật"])


class TestBamChuotKhiChe(unittest.TestCase):
    """Máy ảo / màn nhỏ: cửa sổ game đè GAuto — đẩy xuống dưới rồi bấm lại."""

    def test_ha_cua_so_che_roi_bam(self):
        thu_tu = []

        def thuoc(_h, _d):
            return len(thu_tu) >= 2

        def ha(h, d):
            thu_tu.append(("ha", h, d))
            return 99

        with patch.object(g, "SO_LAN_THU_CHE", 3), patch.object(g, "GIAY_GIUA_THU_CHE", 0), \
                patch.object(g, "_thuoc_gauto", side_effect=thuoc), \
                patch.object(g, "_ha_cua_so_che", ha), \
                patch.object(g.win32gui, "SetWindowPos") as swp, \
                patch.object(g.win32gui, "BringWindowToTop"), \
                patch.object(g.win32api, "SetCursorPos"), \
                patch.object(g.win32api, "mouse_event") as me:
            g._bam_chuot(1, (100, 200), "ô đầu dòng nhân vật")
        self.assertGreaterEqual(len(thu_tu), 1)
        self.assertEqual(me.call_count, 2)
        self.assertTrue(any(c.args[1] == g.win32con.HWND_TOPMOST for c in swp.call_args_list))

    def test_ha_cua_so_topmost_thi_go_co_truoc(self):
        swp = []

        def set_pos(hwnd, sau, *a):
            swp.append(sau)

        with patch.object(g.win32gui, "WindowFromPoint", return_value=5), \
                patch.object(g.win32gui, "GetAncestor", return_value=5), \
                patch.object(g.win32gui, "IsWindow", return_value=True), \
                patch.object(g, "_ten_lop", return_value="TianLongBaBu WndClass"), \
                patch.object(g.win32gui, "GetWindowLong", return_value=g.win32con.WS_EX_TOPMOST), \
                patch.object(g.win32gui, "SetWindowPos", side_effect=set_pos):
            self.assertEqual(g._ha_cua_so_che(1, (10, 10)), 5)
        self.assertEqual(swp, [g.win32con.HWND_NOTOPMOST, g.win32con.HWND_BOTTOM])

    def test_diem_trong_khung_nhung_game_de_thi_chua_san_sang(self):
        with patch.object(g, "_thuoc_gauto", return_value=False), \
                patch.object(g, "_diem_trong_cua_so", return_value=True):
            self.assertFalse(g._san_sang_bam(1, (10, 10)))

    def test_van_che_thi_bao_loi(self):
        with patch.object(g, "SO_LAN_THU_CHE", 2), patch.object(g, "GIAY_GIUA_THU_CHE", 0), \
                patch.object(g, "_thuoc_gauto", return_value=False), \
                patch.object(g, "_ha_cua_so_che", return_value=None), \
                patch.object(g.win32gui, "SetWindowPos"), \
                patch.object(g.win32gui, "BringWindowToTop"):
            with self.assertRaises(g.LoiGautoAcTac) as ng:
                g._bam_chuot(1, (10, 10), "ô đầu dòng nhân vật")
        self.assertIn("che chỗ ô đầu dòng nhân vật", str(ng.exception))


class TestKhongGianhFocusAutohoc(unittest.TestCase):
    def test_muon_chuot_khong_tra_focus_ve_autohoc(self):
        with patch.object(g.win32gui, "GetForegroundWindow", return_value=7), \
                patch.object(g.win32api, "GetCursorPos", return_value=(1, 2)), \
                patch.object(g.win32gui, "GetWindowLong", return_value=0), \
                patch.object(g.win32gui, "IsWindow", return_value=True), \
                patch.object(g.win32gui, "SetWindowPos"), \
                patch.object(g.win32api, "SetCursorPos"), \
                patch.object(g, "_len_truoc") as len_truoc, \
                patch.object(g, "_la_cua_so_autohoc", return_value=True):
            with g._muon_chuot(1, "ô Ác Tặc"):
                pass
        self.assertEqual(len_truoc.call_args_list, [((1,),)])

    def test_muon_chuot_tra_focus_cua_so_khac(self):
        with patch.object(g.win32gui, "GetForegroundWindow", return_value=7), \
                patch.object(g.win32api, "GetCursorPos", return_value=(1, 2)), \
                patch.object(g.win32gui, "GetWindowLong", return_value=0), \
                patch.object(g.win32gui, "IsWindow", return_value=True), \
                patch.object(g.win32gui, "SetWindowPos"), \
                patch.object(g.win32api, "SetCursorPos"), \
                patch.object(g, "_len_truoc") as len_truoc, \
                patch.object(g, "_la_cua_so_autohoc", return_value=False):
            with g._muon_chuot(1, "ô Ác Tặc"):
                pass
        self.assertEqual([c.args[0] for c in len_truoc.call_args_list], [1, 7])


class TestQuyenAdmin(unittest.TestCase):
    def test_gauto_admin_autohoc_thuong_thi_bao_can_admin(self):
        with patch.object(g, "gauto_la_admin", return_value=True), patch.object(g, "autohoc_la_admin", return_value=False):
            with self.assertRaises(g.LoiGautoAcTac) as ctx:
                g.kiem_tra_quyen(1)
        self.assertEqual(str(ctx.exception), g.THONG_BAO_CAN_ADMIN)

    def test_cung_quyen_thi_qua(self):
        with patch.object(g, "gauto_la_admin", return_value=True), patch.object(g, "autohoc_la_admin", return_value=True):
            g.kiem_tra_quyen(1)

    def test_khong_doc_duoc_token_gauto_thi_coi_la_admin(self):
        with patch.object(g, "_tien_trinh_admin", return_value=None), \
                patch.object(g.win32process, "GetWindowThreadProcessId", return_value=(0, 9)):
            self.assertTrue(g.gauto_la_admin(1))


class TestOnDinhGAuto(unittest.TestCase):
    def test_diem_dong_map_lay_tam_rect(self):
        """Màn 125/150%: bấm tâm dòng thật, không dùng CB_GETITEMHEIGHT (lệch lên 1 dòng, Vô Lượng Sơn thành Tung Sơn)."""
        self.assertEqual(g._tam_rect(0, 80, 120, 100), (60, 90))

        def send(hwnd, msg, w, l):
            return 0

        def rect(hwnd, chi_so):
            self.assertEqual(chi_so, 4)
            return 0, 80, 120, 100

        with patch.object(g.win32gui, "SendMessage", send), patch.object(g, "_rect_dong_list", rect):
            self.assertEqual(g._diem_dong_map(1, 2, 4), (60, 90))

    def test_bam_ao_chi_mot_click(self):
        posts = []
        with patch.object(g.win32gui, "ScreenToClient", return_value=(144, 72)), \
                patch.object(g.win32gui, "PostMessage", side_effect=lambda *a: posts.append(a[1])), \
                patch.object(g, "_he_so_logic_cua_so", return_value=96 / 144), \
                patch.object(g.time, "sleep"):
            g._bam_ao(1, (100, 200))
        self.assertEqual(posts.count(g.win32con.WM_LBUTTONDOWN), 1)

    def test_diem_o_tich_sat_mep_trai(self):
        self.assertEqual(g._diem_o_tich_client(0, 20, 180, 36), (8, 28))

    def test_sua_diem_logic_vao_cua_so_vat_ly(self):
        """MSAA trả (80, 60) trong khi GAuto vật lý nằm ở (120, 90)-(400, 300) — 150%."""
        def trong(_h, diem):
            x, y = diem
            return 120 <= x < 400 and 90 <= y < 300

        with patch.object(g, "_diem_trong_cua_so", side_effect=trong), \
                patch.object(g.ctypes.windll.user32, "GetDpiForWindow", return_value=144):
            self.assertEqual(g._sua_diem_man_hinh(1, (80, 60)), (120, 90))

    def test_o_dau_dong_bam_rect_listview(self):
        bang = _BangTich({"caychay32": False})
        da_bam = []

        def bam_client(h, hd, xy, cho, da_xong, giay=g.GIAY_CHO_O_TICH):
            da_bam.append((xy, cho))
            bang.tich["caychay32"] = True
            return "ảo"

        with patch.object(g, "danh_sach_nhan_vat", bang.ds), patch.object(g, "_bang_nhan_vat", lambda h: 9), \
                patch.object(g, "_msaa", lambda h: bang), patch.object(g, "_hien_cua_so_gauto", lambda h: None), \
                patch.object(g, "_rect_dong_bang", lambda h, i: (0, 20, 180, 36)), \
                patch.object(g, "_bam_client_hoac_that", bam_client):
            self.assertEqual(g.dat_dau_dong(1, ("caychay32",), True), ["caychay32"])
        self.assertEqual(da_bam, [((8, 28), "ô đầu dòng nhân vật")])

    def test_lp_chuot_doi_pixel_logic_khi_khong_dpi(self):
        self.assertEqual(g._lp_chuot(144, 72, 96 / 144), g._lp_chuot(96, 48))
        self.assertEqual(g._lp_chuot(10, 20), g.win32api.MAKELONG(10, 20))

    def test_chon_hwnd_uu_tien_dung_duong_dan_co_bang(self):
        with patch.object(g, "_bang_nhan_vat", side_effect=lambda h, bat_buoc=False: h == 2):
            self.assertEqual(g._chon_hwnd_gauto([1, 2], [3]), 2)

    def test_chon_hwnd_thu_muc_khac_neu_khong_khop_duong(self):
        with patch.object(g, "_bang_nhan_vat", side_effect=lambda h, bat_buoc=False: h == 8):
            self.assertEqual(g._chon_hwnd_gauto([], [7, 8]), 8)

    def test_cac_map_rong_thi_doc_msaa(self):
        with patch.object(g.win32gui, "SendMessage", return_value=0), \
                patch.object(g, "_doc_ds_list_combo", return_value=[]), \
                patch.object(g, "_ten_map_msaa", return_value=("", ["Kiếm Các", "Tung Sơn"])):
            self.assertEqual(g.cac_map(1), ["Kiếm Các", "Tung Sơn"])

    def test_cac_map_doc_list_tha_xuong(self):
        """MSAA của combo ra Đường đi/Open; list hwndList (cùng GetComboBoxInfo với chon_map) mới là map."""
        with patch.object(g, "_gui_con_tro_toi_gauto", return_value=False), \
                patch.object(g, "_doc_ds_list_combo", return_value=["Kiếm Các", "Tung Sơn"]), \
                patch.object(g, "_ten_map_msaa", return_value=("Đường đi", ["Đường đi", "Open"])):
            self.assertEqual(g.cac_map(1), ["Kiếm Các", "Tung Sơn"])

    def test_64bit_khong_gui_lvm_getitemrect(self):
        """GAuto 32-bit + AutoHoc 64-bit: LVM_GETITEMRECT → hộp .NET protected memory."""
        msgs = []

        def send(_h, msg, _w, _l):
            msgs.append(msg)
            if msg == g.LVM_GETCOUNTPERPAGE:
                return 10
            if msg == g.LVM_GETTOPINDEX:
                return 0
            return 1

        with patch.object(g, "_gui_con_tro_toi_gauto", return_value=False), \
                patch.object(g.ctypes.windll.user32, "SendMessageW", send), \
                patch.object(g.win32gui, "GetClientRect", return_value=(0, 0, 180, 170)):
            rc = g._rect_dong_bang(9, 2)
        self.assertNotIn(g.LVM_GETITEMRECT, msgs)
        self.assertEqual(rc, (0, 17, 180, 34))

    def test_64bit_khong_gui_lb_getitemrect(self):
        with patch.object(g, "_gui_con_tro_toi_gauto", return_value=False), \
                patch.object(g.ctypes.windll.user32, "SendMessageW") as sm:
            self.assertIsNone(g._rect_dong_list(2, 4))
            sm.assert_not_called()

    def test_64bit_chu_combo_khong_gui_buffer(self):
        with patch.object(g, "_gui_con_tro_toi_gauto", return_value=False), \
                patch.object(g.ctypes.windll.user32, "SendMessageW") as sm:
            self.assertEqual(g._chu_combo_theo_lenh(1, 0), "")
            sm.assert_not_called()

    def test_64bit_diem_dong_map_dung_itemheight(self):
        def send(_h, msg, _w, _l):
            if msg == g.LB_GETITEMHEIGHT:
                return 20
            if msg == g.LB_GETTOPINDEX:
                return 0
            return 0

        with patch.object(g, "_gui_con_tro_toi_gauto", return_value=False), \
                patch.object(g.win32gui, "SendMessage", send), \
                patch.object(g.win32gui, "GetClientRect", return_value=(0, 0, 120, 200)):
            self.assertEqual(g._diem_dong_map(1, 2, 4), (60, 90))


class TestNutTestGauto(unittest.TestCase):
    """Hai nút bật / tắt: OK chỉ khi đọc lại ô trên GAuto đúng, không ghi theo cú bấm."""

    def _chay(self, bat, doc_lan, **them):
        log = []
        lan = {"n": 0}

        def doc(_h, ten):
            lan["n"] += 1
            return doc_lan[min(lan["n"], len(doc_lan)) - 1]

        moi = dict(
            tim_cua_so_quan_ly=lambda d: 1,
            tom_tat_cua_so=lambda h: "GAuto TLBB",
            _hien_cua_so_gauto=lambda h: None,
            gauto_la_admin=lambda h: True,
            autohoc_la_admin=lambda: True,
            kiem_tra_quyen=lambda h: None,
            danh_sach_nhan_vat=lambda h: [(1, "beai47", True, False)],
            tim_chi_so_dong_theo_ten=lambda h, t, c=None: 1,
            chon_dong=lambda h, i, t: None,
            nhan_vat_dang_cai=lambda h: "beai47",
            _doc_lai_gauto=doc,
            dat_cai_dat_ac_tac=lambda *a, **k: "",
            _doi_dau_dong=lambda *a, **k: False,
            _chon_nhan_vat=lambda *a, **k: {g.O_AC_TAC: 9},
            dat_o_chuot=lambda *a, **k: "ảo",
        )
        moi.update(them)
        patches = [patch.object(g, ten, fn) for ten, fn in moi.items()]
        for p in patches:
            p.start()
        try:
            g.test_gauto("C:/GAuto_2025.exe", "beai47", log.append, bat, ["Vô Lượng Sơn"], {})
        finally:
            for p in patches:
                p.stop()
        return log

    def test_bat_ok_khi_doc_lai_dung(self):
        truoc = ((1, "beai47", True, False), {g.O_AC_TAC: False}, "Tung Sơn",
                 ["Đôn Hoàng", "Tung Sơn", "Vô Lượng Sơn"])
        sau = ((1, "beai47", True, True), {g.O_AC_TAC: True, g.O_CHAY_TIM: True}, "Vô Lượng Sơn",
               ["Đôn Hoàng", "Tung Sơn", "Vô Lượng Sơn"])
        log = self._chay(True, [truoc, sau])
        chu = "\n".join(log)
        self.assertIn("Test GAuto bật: 7) đọc lại trên GAuto", chu)
        self.assertIn("OK — đã bật, để nguyên: ô đầu dòng ☑, Ác Tặc ☑, map «Vô Lượng Sơn»", chu)
        self.assertNotIn("3 giây", chu)

    def test_bat_khong_ok_khi_map_lech(self):
        truoc = ((1, "beai47", True, False), {g.O_AC_TAC: False}, "Tung Sơn", ["Tung Sơn", "Vô Lượng Sơn"])
        sau = ((1, "beai47", True, True), {g.O_AC_TAC: True}, "Tung Sơn", ["Tung Sơn", "Vô Lượng Sơn"])
        with self.assertRaises(g.LoiGautoAcTac) as ng:
            self._chay(True, [truoc, sau])
        self.assertIn("bật không ăn", str(ng.exception))
        self.assertIn("Tung Sơn", str(ng.exception))
        self.assertNotIn("OK", str(ng.exception))

    def test_tat_ok_khi_doc_lai_tat(self):
        truoc = ((1, "beai47", True, True), {g.O_AC_TAC: True}, "Vô Lượng Sơn", ["Vô Lượng Sơn"])
        sau = ((1, "beai47", True, False), {g.O_AC_TAC: False}, "Vô Lượng Sơn", ["Vô Lượng Sơn"])
        log = self._chay(False, [truoc, sau])
        chu = "\n".join(log)
        self.assertIn("Test GAuto tắt: 6) tắt: bỏ tích ô đầu dòng", chu)
        self.assertIn("bỏ tích ô «Ác Tặc» bằng chuột ảo", chu)
        self.assertIn("OK — đã tắt: ô đầu dòng ☐, Ác Tặc ☐", chu)

    def test_log_cua_so_vua_mo_khi_thu_nho(self):
        """_hien_cua_so_gauto trả chuỗi, không phải context manager — nối log không TypeError."""
        truoc = ((1, "beai47", True, False), {g.O_AC_TAC: False}, "Tung Sơn",
                 ["Đôn Hoàng", "Tung Sơn", "Vô Lượng Sơn"])
        sau = ((1, "beai47", True, True), {g.O_AC_TAC: True, g.O_CHAY_TIM: True}, "Vô Lượng Sơn",
               ["Đôn Hoàng", "Tung Sơn", "Vô Lượng Sơn"])
        log = self._chay(True, [truoc, sau], _hien_cua_so_gauto=lambda h: "đang thu nhỏ")
        chu = "\n".join(log)
        self.assertIn("cửa sổ vừa mở (đang thu nhỏ)", chu)
        self.assertIn("OK — đã bật", chu)


class TestHienCuaSoGauto(unittest.TestCase):
    def test_thu_nho_tra_chuoi(self):
        with patch.object(g.win32gui, "IsIconic", return_value=True), \
                patch.object(g.win32gui, "ShowWindow"):
            self.assertEqual(g._hien_cua_so_gauto(1), "đang thu nhỏ")

    def test_noi_len_dung_duoc_trong_with(self):
        da_vao = []
        with patch.object(g, "_hien_cua_so_gauto", return_value=None), \
                patch.object(g.win32gui, "GetWindowLong", return_value=0), \
                patch.object(g.win32gui, "IsIconic", return_value=False), \
                patch.object(g.win32gui, "GetForegroundWindow", return_value=9), \
                patch.object(g.win32gui, "SetWindowPos"), \
                patch.object(g.win32gui, "IsWindow", return_value=True), \
                patch.object(g, "_la_cua_so_autohoc", return_value=False):
            with g._noi_len(1):
                da_vao.append(True)
        self.assertEqual(da_vao, [True])


if __name__ == "__main__":
    unittest.main()
