import os
import queue
import shutil
import sys
import tempfile
import threading
import unittest
from unittest.mock import MagicMock, patch

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
        self.assertEqual(vip.khoa_tu_ten("Mảnh Vỡ Trang Bị (Khóa)"), "trang bi")
        self.assertIsNone(vip.khoa_tu_ten("Mảnh Vỡ Trang Bị VIP"))

    def test_chon_chong_lon_va_so_doc_khong_duoc(self):
        bang = [(7, "Mảnh Vỡ Trang Bị", 6), (80, "30503234", 260000), (1, "Khác", 9)]
        self.assertEqual(vip.o_manh_tccn(bang, "trang bi"), (80, 260000))
        self.assertEqual(vip.o_manh_tccn([(3, "Mảnh Vỡ Trang Bị", 0)], "trang bi"), (3, 250))
        self.assertIsNone(vip.o_manh_tccn("dong", "trang bi"))
        self.assertIsNone(vip.o_manh_tccn([], "trang bi"))

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
            "giao_lai")
        self.assertEqual(vip.ket_luan_giao(giao_dich.LoiGiaoDich("hai bên chưa khóa được giao dịch")), "giao_lai")
        self.assertEqual(vip.ket_luan_giao(giao_dich.LoiGiaoDich("cửa sổ giao dịch không mở")), "giao_lai")
        self.assertEqual(vip.ket_luan_giao(giao_dich.LoiGiaoDich("hai bên chưa thấy nhau khóa")), "giao_lai")
        self.assertEqual(vip.ket_luan_giao(giao_dich.LoiGiaoDich("bấm đồng ý mà giao dịch chưa xong")), "giao_lai")
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


class TestDoiKhongDuocThiXepTui(unittest.TestCase):
    def _luong(self):
        luong = vip.LuongNangCapVip.__new__(vip.LuongNangCapVip)
        luong.buoc = "trang bi"
        luong.dung = threading.Event()
        luong.dung.wait = lambda *_: None
        luong.in_log = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        luong.phu = MagicMock()
        return luong

    def test_chua_thay_mon_thi_xep_tui_roi_doi_lai(self):
        luong = self._luong()
        luong._cua_doi_mo = lambda _g: True
        luong._so_manh_tui = lambda _g: 100
        buoc = []

        def co_mon(_g, _ma):
            return "xep" in buoc

        luong._co_mon = co_mon
        luong._xep_roi_mo_doi = lambda ten: buoc.append("xep")
        self.assertTrue(luong._doi_mot("cosato88", 9, 10162468, "Kim Vương - Ngọc"))
        self.assertEqual(buoc, ["xep"])

    def test_xep_roi_mo_doi_dong_cua_so_roi_mo_menu(self):
        luong = self._luong()
        lenh = []
        luong.phu.lua.chay.side_effect = lambda ma: lenh.append(ma)
        luong._xep_tui = lambda g, t: lenh.append("xep")
        luong._mo_menu = lambda t, d: lenh.append(("mo", d))
        luong._xep_roi_mo_doi("cosato88")
        self.assertIn('CloseWindow("XiaoXiang_DuiHuanUI2"', lenh[0])
        self.assertEqual(lenh[1:], ["xep", ("mo", 1)])


class TestLoiTheoBuoc(unittest.TestCase):
    def _luong(self):
        luong = vip.LuongNangCapVip.__new__(vip.LuongNangCapVip)
        luong.buoc = "trang bi"
        luong.dung = threading.Event()
        luong.dung.wait = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        luong.in_log = lambda *_: None
        luong.tk_chinh = {"nhan_vat": "chinh"}
        luong.chinh = MagicMock()
        luong.phu = MagicMock()
        return luong

    def test_loi_diss_va_khi_nao_mo_lai(self):
        dong = vip.LoiLua("cửa sổ game đã đóng (Invalid window handle.)")
        treo = vip.LoiLua("Game không phản hồi (đang loading hoặc bị treo?)")
        self.assertTrue(vip.la_loi_diss(dong))
        self.assertTrue(vip.la_loi_diss(treo))
        self.assertFalse(vip.la_loi_diss(vip.LoiGiaoAccChinh("không mở được Thiên Cơ Cẩm Nang")))
        self.assertTrue(vip.can_mo_lai_client(dong, False, False))
        self.assertFalse(vip.can_mo_lai_client(treo, True, False))
        self.assertTrue(vip.can_mo_lai_client(treo, False, False))
        self.assertTrue(vip.can_mo_lai_client(treo, True, True))

    def test_cua_so_dong_thi_mo_lai_khong_rut_mai(self):
        luong = self._luong()
        log = []
        luong.in_log = log.append
        lan = {"n": 0}

        def chuan(_ten):
            lan["n"] += 1
            if lan["n"] == 1:
                raise vip.LoiLua("cửa sổ game đã đóng (Invalid window handle.)")

        luong._chuan_bi_manh = chuan
        luong._phuc_hoi_diss_acc_chinh = lambda loi: log.append("mo") or True
        luong._rut_tiep("bacmori14")
        self.assertEqual(lan["n"], 2)
        self.assertEqual(log, ["mo"])

    def test_treo_ba_lan_thi_tat_roi_mo_lai(self):
        luong = self._luong()
        luong.in_log = lambda *_: None
        luong._cua_so_song = lambda _g: True
        luong._bam_duyet_mat_ket_noi = lambda: False
        tat, mo = [], []
        luong._tat_client_treo = lambda: tat.append(1)
        luong._mo_lai_acc_chinh = lambda: mo.append(1)
        loi = vip.LoiLua("Game không phản hồi (đang loading hoặc bị treo?)")
        luong._phuc_hoi_diss_acc_chinh(loi)
        luong._phuc_hoi_diss_acc_chinh(loi)
        self.assertEqual(mo, [])
        luong._phuc_hoi_diss_acc_chinh(loi)
        self.assertEqual(tat, [1])
        self.assertEqual(mo, [1])

    def test_loi_mo_tccn_thi_rut_tiep(self):
        luong = self._luong()
        lan = {"n": 0}

        def chuan(_ten):
            lan["n"] += 1
            if lan["n"] == 1:
                raise vip.LoiGiaoAccChinh("không mở được Thiên Cơ Cẩm Nang")

        luong._chuan_bi_manh = chuan
        luong._rut_tiep("cosato88")
        self.assertEqual(lan["n"], 2)

    def test_het_manh_thi_khong_rut_mai(self):
        luong = self._luong()

        def chuan(_ten):
            raise vip.LoiGiaoAccChinh("Thiên Cơ hết Mảnh Vỡ Trang Bị khi còn thiếu 100")

        luong._chuan_bi_manh = chuan
        with self.assertRaises(vip.LoiGiaoAccChinh):
            luong._rut_tiep("cosato88")

    def test_loi_giao_dich_thi_chay_gan_roi_giao_lai(self):
        luong = self._luong()
        du = {("base", 0): (30503234, 5000, "Mảnh Vỡ Trang Bị")}
        trang = {"nhan": False}

        def tui(game):
            if game is luong.chinh:
                return du
            if trang["nhan"]:
                return du
            return {}

        luong._tui = tui
        di = []
        luong._chay_lai_gan_acc_chinh = lambda ten: di.append(ten)

        class GD:
            def __init__(self, *a, **k):
                pass

            def chuyen(self, _o):
                if not di:
                    raise vip.LoiGiaoDich("cửa sổ giao dịch không mở")
                trang["nhan"] = True

        with patch.object(vip, "GiaoDich", GD):
            luong._giao("cosato88")
        self.assertEqual(di, ["cosato88"])

    def test_khac_map_thi_ca_hai_chay_toi_npc(self):
        luong = self._luong()
        luong.chinh.thong_tin.return_value = {"map": "Lạc Dương", "x": 1, "y": 1}
        luong.phu.thong_tin.return_value = {"map": "Đại Lý", "x": 2, "y": 2}
        den = []
        luong._ve_dai_ly = lambda g, t: den.append(("ve", t))
        luong._chay_toi = lambda g, t, xy: den.append(("chay", t, xy))
        luong._chay_lai_gan_acc_chinh("cosato88")
        self.assertEqual(den, [
            ("ve", "chinh"), ("chay", "chinh", (155, 173)),
            ("ve", "cosato88"), ("chay", "cosato88", (155, 173)),
        ])


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


class TestXongDanhSach(unittest.TestCase):
    def _luong(self):
        luong = vip.LuongNangCapVip.__new__(vip.LuongNangCapVip)
        luong.hang_doi = queue.Queue()
        luong.cac_buoc = ["trang bi"]
        luong.tk_chinh = {"ten_dang_nhap": "chinh", "nhan_vat": "AccChinh"}
        luong._kiem_tra_dung = lambda: None
        luong._giu_nhan_vat_dang_online = lambda con: []
        luong._vao_acc_chinh = lambda: None
        luong._dang_xuat_phien = lambda: None
        return luong

    def test_giao_het_tai_khoan_cuoi_thi_dang_xuat(self):
        thoat = []
        luong = self._luong()
        luong._dang_xuat_phien = lambda: thoat.append("dang_xuat")
        luong._danh_sach = lambda: [({"ten_dang_nhap": "cosato14"}, "cosato144")]
        da_giao = []
        luong._mot_acc = lambda tk, ten: da_giao.append(ten)
        luong._chay()
        self.assertEqual(da_giao, ["cosato144"])
        self.assertEqual(thoat, ["dang_xuat"])
        trang = [nd for loai, nd in list(luong.hang_doi.queue) if loai == "trang_thai_nang_cap_vip"]
        self.assertEqual(trang[-1], "Xong — xoay vòng")

    def test_khong_con_nhan_vat_thi_khong_dang_xuat(self):
        thoat = []
        luong = self._luong()
        luong._dang_xuat_phien = lambda: thoat.append("dang_xuat")
        luong._danh_sach = lambda: []
        luong._chay()
        self.assertEqual(thoat, [])
        trang = [nd for loai, nd in list(luong.hang_doi.queue) if loai == "trang_thai_nang_cap_vip"]
        self.assertTrue(trang[-1].startswith("Xong"))
        self.assertNotIn("xoay vòng", trang[-1])


if __name__ == "__main__":
    unittest.main()
