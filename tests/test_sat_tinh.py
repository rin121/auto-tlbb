"""Test logic Thập Nhị Sát Tinh: lượt, hội thoại NPC, điều kiện đội viên."""
import unittest
from datetime import date
from unittest.mock import MagicMock

import cau_hinh
import pho_ban_pmp as pb
from pho_ban_pmp import PhoBanPMP


def _pmp(**kw):
    gia_tri = dict(cau_hinh.MAC_DINH_PHO_BAN_PMP)
    gia_tri.update(kw)
    return gia_tri


def _dem(**kw):
    hom = {"ngay": date.today().isoformat(), "so_vong": 0, "so_het_luot": False, "het_luot": False,
           "st_vong": 0, "st_het": False}
    hom.update(kw)
    return pb.hom_nay({"hom_nay": hom})


class TestConSatTinh(unittest.TestCase):
    def test_mac_dinh_con_sat_tinh(self):
        pmp = _pmp(sat_tinh=True)
        self.assertTrue(pb.con_sat_tinh(pmp, _dem()))

    def test_tat_sat_tinh(self):
        pmp = _pmp(sat_tinh=False)
        self.assertFalse(pb.con_sat_tinh(pmp, _dem()))

    def test_st_het(self):
        pmp = _pmp(sat_tinh=True)
        self.assertFalse(pb.con_sat_tinh(pmp, _dem(st_het=True)))

    def test_dang_phai_di_sat_tinh(self):
        pmp = _pmp(bat=True, sat_tinh=True)
        self.assertFalse(pb.dang_phai_di_sat_tinh(pmp, _dem()))
        self.assertTrue(pb.dang_phai_di_sat_tinh(pmp, _dem(het_luot=True)))
        self.assertFalse(pb.dang_phai_di_sat_tinh(_pmp(bat=False), _dem(het_luot=True)))


class TestLaSatTinhMap(unittest.TestCase):
    def test_la_sat_tinh(self):
        self.assertTrue(pb.la_sat_tinh(pb.MAP_SAT_TINH))
        self.assertTrue(pb.la_sat_tinh("lôi đài sinh tử"))
        self.assertFalse(pb.la_sat_tinh(pb.MAP_PMP))


class TestHoiThoaiNpcSatTinh(unittest.TestCase):
    """PhoBanPMP._chu_het_sat_tinh / _con_lai_sat_tinh — parse hội thoại NPC SÁT TINH."""

    def test_chu_het_20_lan(self):
        chu = "Ngươi đã tham gia #G20#w lần rồi, xin ngày mai hãy quay lại"
        self.assertEqual(PhoBanPMP._chu_het_sat_tinh([chu]), chu)

    def test_chu_het_ngay_mai(self):
        chu = "Hôm nay đã đủ, ngày mai hãy quay lại nhé"
        self.assertEqual(PhoBanPMP._chu_het_sat_tinh([chu]), chu)

    def test_doi_vien_da_du_luot(self):
        chu = "Trong tổ đội của các hạ có caychay16, caychay18 đã tham gia phụ bản #G20 lần#W trong ngày hôm nay!"
        self.assertEqual(PhoBanPMP._chu_het_sat_tinh([chu]), chu)
        chu = "Trong tổ đội của các hạ có caychay16, caychay18 đã tham gia phụ bản 20 lần trong ngày hôm nay!"
        self.assertEqual(PhoBanPMP._chu_het_sat_tinh([chu]), chu)

    def test_khong_het(self):
        self.assertIsNone(PhoBanPMP._chu_het_sat_tinh(["Khiêu chiến Thập Nhị Sát Tinh"]))

    def test_con_lai_luot(self):
        self.assertEqual(PhoBanPMP._con_lai_sat_tinh(["Hôm nay còn lại #G5 lượt nữa"]), 5)
        self.assertEqual(PhoBanPMP._con_lai_sat_tinh(["còn lại 0 lượt"]), 0)

    def test_con_lai_khong_co(self):
        self.assertIsNone(PhoBanPMP._con_lai_sat_tinh(["Chọn độ khó"]))


class TestBuocVaoSatTinh(unittest.TestCase):
    def test_buoc_vao_co_npc_va_map_dich(self):
        map_o, ten, xy, dong, map_toi = pb.BUOC_VAO_SAT_TINH
        self.assertEqual(map_o, pb.MAP_LAC_DUONG)
        self.assertEqual(ten, "SÁT TINH")
        self.assertEqual(map_toi, pb.MAP_SAT_TINH)
        self.assertEqual(len(dong), 2)

    def test_toa_do_cho_sat_tinh_gan_npc(self):
        self.assertEqual(pb.XY_NPC_SAT_TINH, pb.BUOC_VAO_SAT_TINH[2])
        self.assertLess(pb.KHOANG_TOI_CHO_SAT_TINH, pb.KHOANG_GAN_NPC_SAT_TINH)


class TestSatTinhDaRa(unittest.TestCase):
    def test_co_quai_trong_ban_kinh(self):
        game = MagicMock()
        pb_inst = PhoBanPMP(game, lambda *_: None)
        quai = MagicMock()
        quai.hp = 100
        quai.x, quai.y = pb.DIEM_SAT_TINH
        pb_inst._quanh = lambda: [("boss", quai)]
        self.assertTrue(pb_inst._sat_tinh_da_ra())

    def test_ngoai_ban_kinh(self):
        game = MagicMock()
        pb_inst = PhoBanPMP(game, lambda *_: None)
        quai = MagicMock()
        quai.hp = 100
        quai.x, quai.y = 0, 0
        pb_inst._quanh = lambda: [("boss", quai)]
        self.assertFalse(pb_inst._sat_tinh_da_ra())


class TestLuongPmpSatTinh(unittest.TestCase):
    """Chuyển tiếp PMP → Sát Tinh theo bộ đếm."""

    def test_het_pmp_van_con_sat_tinh(self):
        pmp = _pmp(bat=True, sat_tinh=True)
        dem = _dem(het_luot=True)
        self.assertFalse(pb.con_pmp(pmp, dem))
        self.assertTrue(pb.con_sat_tinh(pmp, dem))
        self.assertTrue(pb.dang_phai_di_sat_tinh(pmp, dem))

    def test_chi_sat_tinh_bo_pmp(self):
        pmp = _pmp(bat=True, chi_sat_tinh=True, sat_tinh=True)
        dem = _dem()
        self.assertFalse(pb.con_pmp(pmp, dem))
        self.assertTrue(pb.con_sat_tinh(pmp, dem))
        ten, _ = pb.npc_lac_duong_can_toi(pmp, dem)
        self.assertEqual(ten, pb.TEN_NPC_SAT_TINH)


class TestVeKhiHetLuot(unittest.TestCase):
    """Hết lượt: khi nào tự về Đại Lý, khi nào ở lại Lạc Dương."""

    def test_xoay_vong_xong_sat_tinh_o_lai_lac_duong(self):
        # caychay21/22: xong 20 vòng Sát Tinh, xoay vòng giao dịch cho trưởng nhóm ngay ở Lạc Dương.
        pmp = _pmp(bat=False, sat_tinh=True, xoay_vong=True)
        dem = _dem(het_luot=True, st_het=True)
        self.assertFalse(pb.can_ve_khi_het_luot(pmp, dem, pb.MAP_LAC_DUONG))

    def test_con_sat_tinh_o_lai_lac_duong(self):
        pmp = _pmp(bat=True, sat_tinh=True)
        self.assertFalse(pb.can_ve_khi_het_luot(pmp, _dem(het_luot=True), pb.MAP_LAC_DUONG))

    def test_khong_xoay_vong_het_ca_hai_thi_ve(self):
        pmp = _pmp(bat=False, sat_tinh=True, xoay_vong=False)
        self.assertTrue(pb.can_ve_khi_het_luot(pmp, _dem(het_luot=True, st_het=True), pb.MAP_LAC_DUONG))

    def test_xoay_vong_ket_trong_pmp_van_ve(self):
        pmp = _pmp(bat=False, sat_tinh=True, xoay_vong=True)
        self.assertTrue(pb.can_ve_khi_het_luot(pmp, _dem(het_luot=True, st_het=True), pb.MAP_PMP))

    def test_chua_het_luot_khong_ve(self):
        self.assertFalse(pb.can_ve_khi_het_luot(_pmp(), _dem(), pb.MAP_LAC_DUONG))

    def test_o_dai_ly_khong_ve(self):
        self.assertFalse(pb.can_ve_khi_het_luot(_pmp(), _dem(het_luot=True, st_het=True), pb.MAP_DAI_LY))

    def test_trong_loi_dai_khong_ve(self):
        self.assertFalse(pb.can_ve_khi_het_luot(_pmp(), _dem(het_luot=True, st_het=True), pb.MAP_SAT_TINH))


class TestConSatTinhThem(unittest.TestCase):
    def test_thieu_khoa_sat_tinh_mac_dinh_bat(self):
        self.assertTrue(pb.con_sat_tinh({}, _dem()))

    def test_chi_sat_tinh_khong_tinh_luot_pmp(self):
        pmp = _pmp(bat=True, chi_sat_tinh=True, sat_tinh=True)
        self.assertFalse(pb.con_luot_pmp_thuong(pmp, _dem()))

    def test_het_ca_hai_khong_npc(self):
        pmp = _pmp(bat=True, sat_tinh=True)
        ten, xy = pb.npc_lac_duong_can_toi(pmp, _dem(het_luot=True, st_het=True))
        self.assertIsNone(ten)

    def test_dem_st_reset_ngay_moi(self):
        dem = pb.hom_nay({"hom_nay": {"ngay": "2000-01-01", "st_vong": 20, "st_het": True}})
        self.assertTrue(pb.con_sat_tinh(_pmp(sat_tinh=True), dem))


class TestHoiThoaiNpcSatTinhThem(unittest.TestCase):
    def test_bo_ma_mau(self):
        chu = "#cff0000Ngày mai hãy quay lại#W nhé"
        self.assertEqual(PhoBanPMP._chu_het_sat_tinh([chu]), chu)

    def test_chu_hoa(self):
        chu = "NGƯƠI ĐÃ THAM GIA 20 LẦN RỒI"
        self.assertEqual(PhoBanPMP._chu_het_sat_tinh([chu]), chu)

    def test_lay_dong_khop_trong_nhieu_dong(self):
        chu = "Ngươi đã tham gia #G20#w lần rồi"
        self.assertEqual(PhoBanPMP._chu_het_sat_tinh(["Khiêu chiến", chu, "Rời khỏi"]), chu)

    def test_tham_gia_it_hon_20_khong_het(self):
        self.assertIsNone(PhoBanPMP._chu_het_sat_tinh(["Ngươi đã tham gia 5 lần, còn lại 15 lượt"]))

    def test_con_lai_chu_hoa_va_ma_mau(self):
        self.assertEqual(PhoBanPMP._con_lai_sat_tinh(["CÒN LẠI #G12 LƯỢT"]), 12)

    def test_con_lai_lay_dong_dau_tien(self):
        self.assertEqual(PhoBanPMP._con_lai_sat_tinh(["Chọn", "còn lại 3 lượt", "còn lại 9 lượt"]), 3)


class TestSatTinhDaRaThem(unittest.TestCase):
    def _pb(self, *cac_quai):
        pb_inst = PhoBanPMP(MagicMock(), lambda *_: None)
        pb_inst._quanh = lambda: [("q", q) for q in cac_quai]
        return pb_inst

    def _quai(self, hp, x, y):
        quai = MagicMock()
        quai.hp, quai.x, quai.y = hp, x, y
        return quai

    def test_quai_chet_khong_tinh(self):
        self.assertFalse(self._pb(self._quai(0, *pb.DIEM_SAT_TINH))._sat_tinh_da_ra())

    def test_mep_ban_kinh(self):
        x, y = pb.DIEM_SAT_TINH
        self.assertTrue(self._pb(self._quai(1, x + pb.BAN_KINH_SAT_TINH + 2, y))._sat_tinh_da_ra())
        self.assertFalse(self._pb(self._quai(1, x + pb.BAN_KINH_SAT_TINH + 3, y))._sat_tinh_da_ra())

    def test_khong_co_quai(self):
        self.assertFalse(self._pb()._sat_tinh_da_ra())


class TestDaVaoLoiDaiKhiDangGom(unittest.TestCase):
    """xeko1: NPC đã đưa cả đội vào lôi đài (game đổi map chậm) — không báo lỗi, dắt đội tới chỗ đánh."""

    def _pb(self, map_sau):
        inst = PhoBanPMP(MagicMock(), lambda *_: None)
        inst.ten, inst.doi, inst.trang_thai = "xeko1", None, {}
        inst.bao_doi = lambda: None
        inst.het_han_vong = 10 ** 12
        trang = {"map": pb.MAP_LAC_DUONG}
        inst._map = lambda: trang["map"]
        inst._gom_doi_neu_lech_map = lambda: None
        inst._sua_dem = lambda ten_ds, **kw: [{"pho_ban_pmp": {}}]
        self.danh = []
        inst._danh_sat_tinh = lambda: self.danh.append(trang["map"])

        def vao():
            trang["map"] = map_sau
            raise pb._TruongSaiMap(map_sau, pb.MAP_LAC_DUONG)
        inst._vao_sat_tinh = vao
        return inst

    def test_da_o_loi_dai_thi_danh_tiep(self):
        self._pb(pb.MAP_SAT_TINH)._vong_sat_tinh(_pmp())
        self.assertEqual(self.danh, [pb.MAP_SAT_TINH])

    def test_sai_map_khac_van_bao_loi(self):
        with self.assertRaises(pb._TruongSaiMap):
            self._pb(pb.MAP_DAI_LY)._vong_sat_tinh(_pmp())
        self.assertEqual(self.danh, [])


class TestKetDiChuyenThiVeThanh(unittest.TestCase):
    """chaiko5: không mở được hội thoại Di Chuyển sau 90 giây — dùng Về thành Đại Lý rồi thử lại."""

    def _pb(self, map_o, toi_sau_ve_thanh):
        inst = PhoBanPMP(MagicMock(), lambda *_: None)
        inst.ten, inst.doi, inst.trang_thai = "chaiko5", None, {}
        trang = {"map": map_o}
        inst._map = lambda: trang["map"]
        self.goi_npc = 0
        self.ve_thanh = 0

        def mo(*a, **kw):
            self.goi_npc += 1
            raise pb._KhongMoDuocHoiThoai("không mở được hội thoại Di Chuyển sau 90 giây")

        def ve():
            self.ve_thanh += 1
            if toi_sau_ve_thanh:
                trang["map"] = pb.MAP_LAC_DUONG
        inst._mo_hoi_thoai = mo
        inst._ve_thanh_tai_dai_ly = ve
        return inst

    def test_ket_o_dai_ly_thi_ve_thanh_roi_thu_lai(self):
        inst = self._pb(pb.MAP_DAI_LY, True)
        inst._vao(pb.BUOC_DI_CHUYEN_LAC_DUONG)
        self.assertEqual((self.goi_npc, self.ve_thanh), (1, 1))

    def test_ket_mai_thi_bao_loi_sau_so_lan_thu(self):
        inst = self._pb(pb.MAP_DAI_LY, False)
        with self.assertRaises(pb._KhongMoDuocHoiThoai):
            inst._vao(pb.BUOC_DI_CHUYEN_LAC_DUONG)
        self.assertEqual((self.goi_npc, self.ve_thanh), (pb.SO_LAN_THU, pb.SO_LAN_THU - 1))

    def test_khong_o_dai_ly_thi_khong_ve_thanh(self):
        inst = self._pb(pb.MAP_LAC_DUONG, False)
        buoc = (pb.MAP_LAC_DUONG, "Trình Thanh Sương", (1, 1), ((1, 1),), pb.MAP_PMP)
        with self.assertRaises(pb._KhongMoDuocHoiThoai):
            inst._vao(buoc)
        self.assertEqual(self.ve_thanh, 0)


if __name__ == "__main__":
    unittest.main()
