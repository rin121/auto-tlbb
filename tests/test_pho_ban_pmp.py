"""Test logic Phiêu Miểu Phong: bộ đếm, map, gom đội, về thành, xoay vòng."""
import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import cau_hinh
import pho_ban_pmp as pb
from lua_game import LoiLua


def _pmp(**kw):
    gia_tri = dict(cau_hinh.MAC_DINH_PHO_BAN_PMP)
    gia_tri.update(kw)
    return gia_tri


def _dem(**kw):
    """Bộ đếm hôm nay (sau hom_nay)."""
    hom = {"ngay": date.today().isoformat(), "so_vong": 0, "so_het_luot": False, "het_luot": False,
           "st_vong": 0, "st_het": False}
    hom.update(kw)
    return pb.hom_nay({"hom_nay": hom})


class TestHomNay(unittest.TestCase):
    def test_ngay_moi_reset_dem(self):
        hom_qua = (date.today() - timedelta(days=1)).isoformat()
        dem = pb.hom_nay({"hom_nay": {"ngay": hom_qua, "so_vong": 9, "het_luot": True, "st_vong": 5, "st_het": True}})
        self.assertEqual(dem["so_vong"], 0)
        self.assertFalse(dem["het_luot"])
        self.assertEqual(dem["st_vong"], 0)
        self.assertFalse(dem["st_het"])

    def test_giu_dem_cung_ngay(self):
        hom = date.today().isoformat()
        dem = pb.hom_nay({"hom_nay": {"ngay": hom, "so_vong": 3, "het_luot": True}})
        self.assertEqual(dem["so_vong"], 3)
        self.assertTrue(dem["het_luot"])


class TestConPmp(unittest.TestCase):
    def test_con_pmp_thuong_khi_chua_het_luot(self):
        self.assertTrue(pb.con_pmp_thuong(_dem()))
        self.assertFalse(pb.con_pmp_thuong(_dem(het_luot=True)))

    def test_con_pmp_so(self):
        self.assertTrue(pb.con_pmp_so(_dem()))
        self.assertFalse(pb.con_pmp_so(_dem(so_het_luot=True)))

    def test_con_pmp_dung_khi_chi_sat_tinh(self):
        pmp = _pmp(bat=True, chi_sat_tinh=True)
        self.assertFalse(pb.con_pmp(pmp, _dem()))

    def test_con_pmp_dung_khi_dat_so_vong(self):
        pmp = _pmp(bat=True, so_vong=2)
        self.assertTrue(pb.con_pmp(pmp, _dem(so_vong=1)))
        self.assertFalse(pb.con_pmp(pmp, _dem(so_vong=2)))

    def test_con_luot_pmp_thuong(self):
        pmp = _pmp(so_vong=0)
        self.assertTrue(pb.con_luot_pmp_thuong(pmp, _dem()))
        self.assertFalse(pb.con_luot_pmp_thuong(pmp, _dem(het_luot=True)))
        pmp2 = _pmp(so_vong=1, chi_sat_tinh=False)
        self.assertFalse(pb.con_luot_pmp_thuong(pmp2, _dem(so_vong=1)))


class TestMapPhoBan(unittest.TestCase):
    def test_la_map_pho_ban(self):
        self.assertTrue(pb.la_map_pho_ban(pb.MAP_DAI_LY))
        self.assertTrue(pb.la_map_pho_ban(pb.MAP_LAC_DUONG))
        self.assertFalse(pb.la_map_pho_ban("Hỏa Diệm Sơn"))

    def test_la_map_trong_pho_ban(self):
        self.assertTrue(pb.la_map_trong_pho_ban(pb.MAP_PMP))
        self.assertTrue(pb.la_map_trong_pho_ban(pb.MAP_SAT_TINH))
        self.assertFalse(pb.la_map_trong_pho_ban(pb.MAP_LAC_DUONG))

    def test_can_ve_khi_het_luot_pmp(self):
        self.assertTrue(pb.can_ve_khi_het_luot_pmp(pb.MAP_PMP))
        self.assertFalse(pb.can_ve_khi_het_luot_pmp(pb.MAP_DAI_LY))

    def test_can_ve_vi_map_la(self):
        self.assertFalse(pb.can_ve_vi_map_la(""))
        self.assertFalse(pb.can_ve_vi_map_la(pb.MAP_DAI_LY))
        self.assertTrue(pb.can_ve_vi_map_la("Túc Mộng Sơn"))


class TestHoiMauDaiLy(unittest.TestCase):
    def test_can_hoi_mau(self):
        self.assertTrue(pb.can_hoi_mau_tai_dai_ly({"hp": 40, "hp_toi_da": 100}))
        self.assertFalse(pb.can_hoi_mau_tai_dai_ly({"hp": 60, "hp_toi_da": 100}))
        self.assertFalse(pb.can_hoi_mau_tai_dai_ly(None))


class TestNpcLacDuong(unittest.TestCase):
    def test_uu_tien_pmp_truoc_sat_tinh(self):
        pmp = _pmp(sat_tinh=True)
        ten, xy = pb.npc_lac_duong_can_toi(pmp, _dem())
        self.assertEqual(ten, pb.TEN_NPC_PMP)
        self.assertEqual(xy, pb.XY_NPC_PMP)

    def test_het_pmp_thuong_thi_sat_tinh(self):
        pmp = _pmp(sat_tinh=True)
        ten, xy = pb.npc_lac_duong_can_toi(pmp, _dem(het_luot=True))
        self.assertEqual(ten, pb.TEN_NPC_SAT_TINH)
        self.assertEqual(xy, pb.XY_NPC_SAT_TINH)

    def test_het_hai_khong_npc(self):
        pmp = _pmp(sat_tinh=False)
        ten, xy = pb.npc_lac_duong_can_toi(pmp, _dem(het_luot=True))
        self.assertIsNone(ten)


class TestTapHopVaVeThanh(unittest.TestCase):
    def _doi(self, tap_hop=False, map_tap_hop=None):
        doi = pb.DoiPMP("truong", {})
        doi.tap_hop = tap_hop
        doi.map_tap_hop = map_tap_hop
        return doi

    def test_can_ve_tap_hop_dai_ly(self):
        doi = self._doi(True, pb.MAP_DAI_LY)
        self.assertTrue(pb.can_ve_tap_hop(doi, "Lạc Dương"))
        self.assertFalse(pb.can_ve_tap_hop(doi, pb.MAP_DAI_LY))

    def test_khong_ve_khi_trong_an(self):
        doi = self._doi(True, pb.MAP_DAI_LY)
        self.assertFalse(pb.can_ve_tap_hop(doi, pb.MAP_PMP))

    def test_nen_ve_thanh_het_luot_ngoai_an(self):
        ve, ly = pb.nen_ve_thanh_theo_doi(None, pb.MAP_LAC_DUONG, pb.MAP_DAI_LY, True, False)
        self.assertTrue(ve)
        self.assertIn("hết lượt", ly)

    def test_khong_ve_khi_dang_theo_doi(self):
        ve, _ = pb.nen_ve_thanh_theo_doi(None, pb.MAP_LAC_DUONG, pb.MAP_DAI_LY, True, True)
        self.assertFalse(ve)

    def test_ket_an_truong_con_trong_pmp(self):
        ve, _ = pb.nen_ve_thanh_theo_doi(None, pb.MAP_PMP, pb.MAP_PMP, True, False)
        self.assertFalse(ve)

    def test_ket_an_dv_truong_ra_an(self):
        ve, ly = pb.nen_ve_thanh_theo_doi(None, pb.MAP_PMP, pb.MAP_DAI_LY, True, False)
        self.assertTrue(ve)
        self.assertIn("kẹt", ly)


class TestXyGomDoiVien(unittest.TestCase):
    def test_uu_tien_vi_tri_truong_tren_map(self):
        doi = pb.DoiPMP("t", {})
        doi.vi_tri_truong = (100, 200, pb.MAP_DAI_LY)
        xy = pb.xy_gom_doi_vien(doi, None, pb.MAP_DAI_LY, (1, 2))
        self.assertEqual(xy, (100, 200))

    def test_fallback_npc(self):
        doi = pb.DoiPMP("t", {})
        xy = pb.xy_gom_doi_vien(doi, None, pb.MAP_DAI_LY, (50, 60))
        self.assertEqual(xy, (50, 60))

    def test_doc_thong_tin_truong(self):
        truong = MagicMock()
        truong.game.thong_tin.return_value = {"map": pb.MAP_DAI_LY, "x": 11, "y": 22}
        doi = pb.DoiPMP("t", {})
        xy = pb.xy_gom_doi_vien(doi, truong, pb.MAP_DAI_LY, (1, 2))
        self.assertEqual(xy, (11, 22))

    def test_loi_lua_fallback_vi_tri_truong(self):
        truong = MagicMock()
        truong.game.thong_tin.side_effect = LoiLua("x")
        doi = pb.DoiPMP("t", {})
        doi.vi_tri_truong = (3, 4, pb.MAP_DAI_LY)
        self.assertEqual(pb.xy_gom_doi_vien(doi, truong, pb.MAP_DAI_LY, (1, 2)), (3, 4))


class TestPhienXoayVong(unittest.TestCase):
    def tearDown(self):
        pb.dat_phien_xoay_vong(False)

    def test_pmp_chi_chay_khi_xv_bat(self):
        pb.dat_phien_xoay_vong(True)
        cai_dat = {"pho_ban_pmp": _pmp(bat=True, xoay_vong=True)}
        self.assertTrue(pb.pmp_dang_duoc_phep_chay(cai_dat))
        pb.dat_phien_xoay_vong(False)
        self.assertFalse(pb.pmp_dang_duoc_phep_chay(cai_dat))


class TestMoTaHomNay(unittest.TestCase):
    def test_mo_ta_co_sat_tinh(self):
        cai_dat = {"pho_ban_pmp": _pmp(sat_tinh=True, hom_nay={"ngay": date.today().isoformat(),
                                                               "so_vong": 1, "st_vong": 2})}
        chu = pb.mo_ta_hom_nay(cai_dat)
        self.assertIn("PMP", chu)
        self.assertIn("Sát Tinh", chu)

    def test_cac_doan_hom_nay(self):
        cai_dat = {"pho_ban_pmp": _pmp(sat_tinh=True, so_vong=5,
                                       hom_nay={"ngay": date.today().isoformat(), "so_vong": 2, "het_luot": True,
                                                "st_vong": 1, "st_het": False})}
        doan = pb.cac_doan_hom_nay(cai_dat)
        chu = "".join(s for s, _ in doan)
        self.assertIn("hết lượt", chu)
        self.assertIn("Sát Tinh", chu)


class TestKetAiPmp(unittest.TestCase):
    """Ải đánh quá lâu chưa chết quái: lần 2 đội trưởng đánh cùng, vẫn không được thì về Đại Lý chạy vòng mới."""

    def _pho_ban(self, doi, so_lan_loi):
        pho_ban = pb.PhoBanPMP(MagicMock(), lambda *_: None)
        pho_ban.ten = "chaien55"
        pho_ban.doi = doi
        pho_ban._mo_hoi_thoai = lambda *a, **k: True
        pho_ban._quanh = lambda: []
        pho_ban._chon = lambda *_: None
        pho_ban._giu_thu = lambda: None
        pho_ban._bo_theo_doi = lambda: None
        pho_ban._chay_qua = lambda *a: None
        pho_ban._dung_tai = lambda *a: None
        pho_ban._dat_buoc = lambda *a, **k: None
        dem = {"lan": 0}

        def danh(*_):
            dem["lan"] += 1
            if dem["lan"] <= so_lan_loi:
                raise pb.LoiPhoBan("ải 3 quá 120 giây chưa giết Ô Lão Đại")
        pho_ban._danh = danh
        return pho_ban, dem

    def _doi(self):
        doi = pb.DoiPMP("chaien55", {"chaien66": MagicMock()})
        doi.truong_khong_danh = True
        return doi

    def test_hai_lan_khong_giet_duoc_thi_ve_chay_vong_moi(self):
        doi = self._doi()
        pho_ban, dem = self._pho_ban(doi, 2)
        orig = pb.GIAY_CHO_BO_THEO
        pb.GIAY_CHO_BO_THEO = 0
        try:
            with self.assertRaises(pb._TreoPMP) as ctx:
                pho_ban._qua_ai(3, pb.CAC_AI[2])
        finally:
            pb.GIAY_CHO_BO_THEO = orig
        self.assertEqual(dem["lan"], 2)
        self.assertIn("Ô Lão Đại", ctx.exception.chu)

    def test_lan_hai_doi_truong_xuong_thu_danh_cung(self):
        doi = self._doi()
        pho_ban, dem = self._pho_ban(doi, 1)
        orig = pb.GIAY_CHO_BO_THEO
        pb.GIAY_CHO_BO_THEO = 0
        try:
            pho_ban._qua_ai(3, pb.CAC_AI[2])
        finally:
            pb.GIAY_CHO_BO_THEO = orig
        self.assertEqual(dem["lan"], 2)
        self.assertFalse(doi.truong_khong_danh)
        self.assertTrue(doi.truong_vao_danh)

    def test_treo_mac_dinh_van_la_khong_co_quai(self):
        self.assertIn("không có quái", pb._TreoPMP().chu)


class _DongHo:
    def __init__(self):
        self.t = 1000.0

    def time(self):
        return self.t

    def sleep(self, giay):
        self.t += giay


class TestAiAnThan(unittest.TestCase):
    """Ải 2 Tang Thổ Công ẩn thân giữa trận (ghi tay 27/10/2026): biến mất khi còn máu không phải đã chết."""

    def _danh(self, ai, lich):
        """lich(giây kể từ lúc bắt đầu) -> None (không thấy) hoặc % máu (0..1) của quái đầu tiên của ải."""
        dong_ho, log = _DongHo(), []
        bat_dau = dong_ho.t
        pho_ban = pb.PhoBanPMP(MagicMock(), lambda chu: log.append(chu))
        pho_ban.ten = "GaoDeLau"
        pho_ban.doi = None
        ten = pb.chuan_hoa(ai.cac_quai[0])

        def quanh():
            mau = lich(dong_ho.t - bat_dau)
            if mau is None:
                return []
            return [(ten, MagicMock(id=7, hp=mau, x=ai.diem_danh[0], y=ai.diem_danh[1]))]
        pho_ban._quanh = quanh
        pho_ban._kiem_tra = lambda: None
        pho_ban._doc_thong_bao = lambda: []
        pho_ban._giu_thu = lambda: None
        pho_ban._mo_ta = lambda *_: None
        pho_ban._dat_buoc = lambda *a, **k: None
        with patch.object(pb, "time", dong_ho):
            pho_ban._danh(2, ai)
        return dong_ho.t - bat_dau, log

    @staticmethod
    def _tran_ghi_tay(t):
        if t < 10:
            return 1.0 - t * 0.014
        if t < 28:
            return None
        if t < 50:
            return 0.8 - (t - 28) * 0.018
        if t < 70:
            return None
        if t < 85:
            return max(0.4 - (t - 70) * 0.03, 0.01)
        return 0.0

    def test_ai_2_bat_an_than(self):
        self.assertTrue(pb.CAC_AI[1].an_than)
        self.assertFalse(any(ai.an_than for so, ai in enumerate(pb.CAC_AI) if so != 1))

    def test_an_than_cho_hien_lai_den_khi_chet(self):
        giay, log = self._danh(pb.CAC_AI[1], self._tran_ghi_tay)
        self.assertGreaterEqual(giay, 85)
        self.assertEqual(sum("ẩn thân" in d for d in log), 2)
        self.assertEqual(sum("đánh tiếp" in d for d in log), 2)
        self.assertIn("đã giết", log[-1])

    def test_an_than_xac_bien_mat_ngay_khi_mau_gan_het(self):
        def lich(t):
            if t < 20:
                return max(1.0 - t * 0.06, 0.02)
            return None
        giay, log = self._danh(pb.CAC_AI[1], lich)
        self.assertLess(giay, 30)
        self.assertIn("đã giết", log[-1])
        self.assertFalse(any("ẩn thân" in d for d in log))

    def test_an_than_qua_lau_khong_hien_lai(self):
        def lich(t):
            return 0.9 if t < 5 else None
        with self.assertRaises(pb._TreoPMP):
            self._danh(pb.CAC_AI[1], lich)

    def test_tran_dai_hon_120_giay_van_danh_khi_mau_con_giam(self):
        def lich(t):
            if t < 200:
                return 1.0 - t * 0.0045
            return 0.0
        giay, log = self._danh(pb.CAC_AI[1], lich)
        self.assertGreaterEqual(giay, 200)
        self.assertIn("đã giết", log[-1])

    def test_ai_thuong_bien_mat_van_tinh_la_chet(self):
        def lich(t):
            return 0.9 if t < 5 else None
        giay, log = self._danh(pb.CAC_AI[2], lich)
        self.assertLess(giay, 15)
        self.assertIn("đã giết", log[-1])


class TestCaiDatPmp(unittest.TestCase):
    def test_gop_mac_dinh(self):
        pmp = pb.cai_dat_pmp({})
        self.assertIn("sat_tinh", pmp)
        self.assertFalse(pmp["bat"])

    def test_gia_tri_rieng_de_len_mac_dinh(self):
        pmp = pb.cai_dat_pmp({"pho_ban_pmp": {"bat": True, "so_vong": 7}})
        self.assertTrue(pmp["bat"])
        self.assertEqual(pmp["so_vong"], 7)
        self.assertIn("sat_tinh", pmp)

    def test_pho_ban_pmp_none(self):
        self.assertFalse(pb.cai_dat_pmp({"pho_ban_pmp": None})["bat"])


class TestHomNayThieuTruong(unittest.TestCase):
    def test_khong_co_hom_nay(self):
        dem = pb.hom_nay({})
        self.assertEqual(dem["ngay"], date.today().isoformat())
        self.assertEqual(dem["so_vong"], 0)
        self.assertFalse(dem["so_het_luot"])

    def test_bo_dem_cu_thieu_truong_st(self):
        dem = pb.hom_nay({"hom_nay": {"ngay": date.today().isoformat(), "so_vong": 4}})
        self.assertEqual(dem["so_vong"], 4)
        self.assertEqual(dem["st_vong"], 0)
        self.assertFalse(dem["st_het"])


class TestPmpSo(unittest.TestCase):
    def test_chu_het_pmp_so(self):
        chu = "Ngươi đã tham gia Khiêu Chiến quá 1 lần, không thể vào nữa"
        self.assertEqual(pb.PhoBanPMP._chu_het_pmp_so(["", chu]), chu)

    def test_chu_het_pmp_so_khong_co(self):
        self.assertIsNone(pb.PhoBanPMP._chu_het_pmp_so(["Khiêu chiến Phiêu Miểu Phong", None]))

    def test_het_so_van_con_pmp_thuong(self):
        dem = _dem(so_het_luot=True)
        self.assertFalse(pb.con_pmp_so(dem))
        self.assertTrue(pb.con_pmp(_pmp(bat=True), dem))


class TestThongBaoHetPmpThuong(unittest.TestCase):
    def test_co_dau(self):
        self.assertTrue(pb.PhoBanPMP._la_bao_het_pmp_thuong("Hôm nay ngươi đã khiêu chiến 20 lần rồi"))

    def test_khong_dau(self):
        self.assertTrue(pb.PhoBanPMP._la_bao_het_pmp_thuong("Hom nay da du 20 luot Phieu Mieu Phong"))

    def test_da_du_khong_chu_luot(self):
        self.assertTrue(pb.PhoBanPMP._la_bao_het_pmp_thuong("Phiêu Miểu Phong: ngươi đã đủ 20"))

    def test_khong_phai_het_luot(self):
        self.assertFalse(pb.PhoBanPMP._la_bao_het_pmp_thuong("Khiêu chiến Phiêu Miểu Phong"))
        self.assertFalse(pb.PhoBanPMP._la_bao_het_pmp_thuong("Phiêu Miểu Phong còn 200 lượt"))
        self.assertFalse(pb.PhoBanPMP._la_bao_het_pmp_thuong(""))
        self.assertFalse(pb.PhoBanPMP._la_bao_het_pmp_thuong(None))


class TestMapLauLan(unittest.TestCase):
    """Lâu Lan: map NPC cũ, vẫn coi là đường PMP để về thành."""

    def test_la_map_pho_ban(self):
        self.assertTrue(pb.la_map_pho_ban(pb.MAP_LAU_LAN))
        self.assertFalse(pb.can_ve_vi_map_la(pb.MAP_LAU_LAN))
        self.assertFalse(pb.la_map_trong_pho_ban(pb.MAP_LAU_LAN))

    def test_het_luot_o_lau_lan_thi_ve(self):
        self.assertTrue(pb.can_ve_khi_het_luot_pmp(pb.MAP_LAU_LAN))
        pmp = _pmp(bat=True, sat_tinh=True, xoay_vong=True)
        self.assertTrue(pb.can_ve_khi_het_luot(pmp, _dem(het_luot=True), pb.MAP_LAU_LAN))

    def test_ten_map_khong_phan_biet_hoa_thuong(self):
        self.assertTrue(pb.la_dai_ly("đại lý"))
        self.assertTrue(pb.la_lac_duong("LẠC DƯƠNG"))
        self.assertFalse(pb.la_dai_ly(None))


class TestBatTatTapHop(unittest.TestCase):
    def test_bat_tat(self):
        doi = pb.DoiPMP("t", {})
        pb.bat_tap_hop(doi, pb.MAP_LAC_DUONG)
        self.assertTrue(doi.tap_hop)
        self.assertEqual(doi.map_tap_hop, pb.MAP_LAC_DUONG)
        pb.tat_tap_hop(doi)
        self.assertFalse(doi.tap_hop)
        self.assertIsNone(doi.map_tap_hop)

    def test_doi_none_khong_loi(self):
        pb.bat_tap_hop(None)
        pb.tat_tap_hop(None)


class TestTapHopLacDuong(unittest.TestCase):
    def _doi(self, map_gom):
        doi = pb.DoiPMP("t", {})
        pb.bat_tap_hop(doi, map_gom)
        return doi

    def test_gom_lac_duong(self):
        doi = self._doi(pb.MAP_LAC_DUONG)
        self.assertFalse(pb.can_ve_tap_hop(doi, pb.MAP_LAC_DUONG))
        self.assertFalse(pb.can_ve_tap_hop(doi, pb.MAP_DAI_LY))
        self.assertTrue(pb.can_ve_tap_hop(doi, "Hỏa Diệm Sơn"))

    def test_truong_trong_an_khong_gom(self):
        doi = self._doi(pb.MAP_DAI_LY)
        self.assertFalse(pb.can_ve_tap_hop(doi, pb.MAP_LAC_DUONG, pb.MAP_PMP))
        self.assertFalse(pb.can_ve_tap_hop(doi, pb.MAP_LAC_DUONG, pb.MAP_SAT_TINH))

    def test_khong_tap_hop(self):
        doi = pb.DoiPMP("t", {})
        self.assertFalse(pb.can_ve_tap_hop(doi, "Hỏa Diệm Sơn"))
        self.assertFalse(pb.can_ve_tap_hop(None, "Hỏa Diệm Sơn"))


class TestNenVeThanhTheoDoiThem(unittest.TestCase):
    def test_map_la(self):
        ve, ly = pb.nen_ve_thanh_theo_doi(None, "Túc Mộng Sơn", pb.MAP_DAI_LY, False, False)
        self.assertTrue(ve)
        self.assertEqual(ly, "map lạ")

    def test_o_dai_ly_khong_ve(self):
        self.assertFalse(pb.nen_ve_thanh_theo_doi(None, pb.MAP_DAI_LY, pb.MAP_LAC_DUONG, False, False)[0])

    def test_dang_load_map_khong_ve(self):
        self.assertFalse(pb.nen_ve_thanh_theo_doi(None, "", pb.MAP_DAI_LY, False, False)[0])

    def test_gom_dai_ly(self):
        doi = pb.DoiPMP("t", {})
        pb.bat_tap_hop(doi, pb.MAP_DAI_LY)
        ve, ly = pb.nen_ve_thanh_theo_doi(doi, pb.MAP_LAC_DUONG, pb.MAP_DAI_LY, False, False)
        self.assertTrue(ve)
        self.assertEqual(ly, f"gom {pb.MAP_DAI_LY}")

    def test_gom_lac_duong(self):
        doi = pb.DoiPMP("t", {})
        pb.bat_tap_hop(doi, pb.MAP_LAC_DUONG)
        ve, ly = pb.nen_ve_thanh_theo_doi(doi, "Hỏa Diệm Sơn", pb.MAP_LAC_DUONG, False, False)
        self.assertTrue(ve)
        self.assertIn("map lạ", ly)

    def test_trong_an_truong_ra_chua_het_luot_cho(self):
        doi = pb.DoiPMP("t", {})
        pb.bat_tap_hop(doi, pb.MAP_DAI_LY)
        self.assertFalse(pb.nen_ve_thanh_theo_doi(doi, pb.MAP_PMP, pb.MAP_DAI_LY, False, False)[0])

    def test_truong_trong_loi_dai_khong_ve(self):
        self.assertFalse(pb.nen_ve_thanh_theo_doi(None, pb.MAP_LAC_DUONG, pb.MAP_SAT_TINH, True, False)[0])


class TestXoayVongCo(unittest.TestCase):
    def tearDown(self):
        pb.dat_phien_xoay_vong(False)
        pb.dat_chan_vong_moi(False)
        pb._dang_chay_vong.clear()

    def test_xv_bat_nhung_pmp_tat(self):
        pb.dat_phien_xoay_vong(True)
        self.assertFalse(pb.pmp_dang_duoc_phep_chay({"pho_ban_pmp": _pmp(bat=False, xoay_vong=True)}))
        self.assertFalse(pb.pmp_dang_duoc_phep_chay({"pho_ban_pmp": _pmp(bat=True, xoay_vong=False)}))

    def test_phien_xoay_vong_dang_chay(self):
        pb.dat_phien_xoay_vong(True)
        self.assertTrue(pb.phien_xoay_vong_dang_chay())
        pb.dat_phien_xoay_vong(False)
        self.assertFalse(pb.phien_xoay_vong_dang_chay())

    def test_dang_chay_vong(self):
        pb._dang_chay_vong.add(pb.chuan_hoa("CayChay10"))
        self.assertTrue(pb.dang_chay_vong("caychay10"))
        self.assertFalse(pb.dang_chay_vong("caychay11"))
        self.assertFalse(pb.dang_chay_vong(None))

    def test_qua_0h_chan_vong_moi(self):
        """XV-03: qua 0h thì không vào vòng mới dù còn lượt."""
        pb.dat_phien_xoay_vong(True)
        pho_ban = pb.PhoBanPMP(MagicMock(), lambda *_: None)
        cai_dat = {"pho_ban_pmp": _pmp(bat=True, xoay_vong=True, sat_tinh=True)}
        self.assertTrue(pho_ban.can_di(cai_dat))
        pb.dat_chan_vong_moi(True)
        self.assertFalse(pho_ban.can_di(cai_dat))
        pb.dat_chan_vong_moi(False)
        self.assertTrue(pho_ban.can_di(cai_dat))

    def test_can_di_dang_nghi(self):
        pb.dat_phien_xoay_vong(True)
        pho_ban = pb.PhoBanPMP(MagicMock(), lambda *_: None)
        pho_ban.nghi_den = float("inf")
        self.assertFalse(pho_ban.can_di({"pho_ban_pmp": _pmp(bat=True, xoay_vong=True)}))

    def test_can_di_het_ca_pmp_va_sat_tinh(self):
        pb.dat_phien_xoay_vong(True)
        pho_ban = pb.PhoBanPMP(MagicMock(), lambda *_: None)
        hom = {"ngay": date.today().isoformat(), "het_luot": True, "st_het": True}
        self.assertFalse(pho_ban.can_di({"pho_ban_pmp": _pmp(bat=True, xoay_vong=True, hom_nay=hom)}))

    def test_xoa_co_xoay_vong_luu(self):
        cac_nv = [{"pho_ban_pmp": _pmp(bat=True, xoay_vong=True)}, {"pho_ban_pmp": _pmp(xoay_vong=False)}, {}]
        ket_qua = []
        with patch.object(cau_hinh, "cap_nhat_tat_ca_nhan_vat",
                          side_effect=lambda sua: ket_qua.extend(sua(nv) for nv in cac_nv)):
            pb.xoa_co_xoay_vong_luu_tat_ca()
        self.assertEqual(ket_qua, [True, False, False])
        self.assertFalse(cac_nv[0]["pho_ban_pmp"]["xoay_vong"])
        self.assertTrue(cac_nv[0]["pho_ban_pmp"]["bat"])


class TestMoTaHomNayThem(unittest.TestCase):
    def test_tat_sat_tinh_khong_hien(self):
        cai_dat = {"pho_ban_pmp": _pmp(sat_tinh=False)}
        self.assertNotIn("Sát Tinh", pb.mo_ta_hom_nay(cai_dat))
        self.assertNotIn("Sát Tinh", "".join(s for s, _ in pb.cac_doan_hom_nay(cai_dat)))

    def test_co_gioi_han_so_vong(self):
        cai_dat = {"pho_ban_pmp": _pmp(so_vong=5, hom_nay={"ngay": date.today().isoformat(), "so_vong": 2})}
        self.assertIn("2 vòng / 5", pb.mo_ta_hom_nay(cai_dat))
        doan = pb.cac_doan_hom_nay(cai_dat)
        self.assertIn(("5", True), doan)
        self.assertIn(("2", True), doan)

    def test_ngay_cu_hien_0(self):
        hom_qua = (date.today() - timedelta(days=1)).isoformat()
        cai_dat = {"pho_ban_pmp": _pmp(hom_nay={"ngay": hom_qua, "so_vong": 9, "het_luot": True})}
        chu = pb.mo_ta_hom_nay(cai_dat)
        self.assertIn("PMP 0 vòng", chu)
        self.assertNotIn("PMP 0 vòng, hết lượt", chu)


if __name__ == "__main__":
    unittest.main()
