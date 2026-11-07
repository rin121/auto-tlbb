"""Tab Chiến đấu: máu dưới 20% thì về Đại Lý trị liệu (mặc định bật)."""
import unittest

import pho_ban_pmp as pb
from chien_dau import PHAN_TRAM_VE_TRI_LIEU, cai_dat_chien_dau, can_ve_tri_lieu, mau_duoi_phan_tram, nen_ve_tri_lieu
from su_kien_ac_tac import la_pho_ban_ac_tac


def _cam(ten_map):
    return pb.la_dai_ly(ten_map) or pb.la_map_trong_pho_ban(ten_map) or la_pho_ban_ac_tac(ten_map)


def _tt(hp, hp_max=100, ten_map="Hỏa Diệm Sơn"):
    return {"hp": hp, "hp_toi_da": hp_max, "map": ten_map}


class TestMauDuoiPhanTram(unittest.TestCase):
    def test_duoi_20(self):
        self.assertTrue(mau_duoi_phan_tram(_tt(19), 20))
        self.assertTrue(mau_duoi_phan_tram(_tt(1), 20))

    def test_dung_20_thi_khong(self):
        self.assertFalse(mau_duoi_phan_tram(_tt(20), 20))
        self.assertFalse(mau_duoi_phan_tram(_tt(50), 20))

    def test_chet_hoac_thieu_du_lieu(self):
        self.assertFalse(mau_duoi_phan_tram(_tt(0), 20))
        self.assertFalse(mau_duoi_phan_tram({"hp": 10, "hp_toi_da": 0}, 20))
        self.assertFalse(mau_duoi_phan_tram(None, 20))


class TestCanVeTriLieu(unittest.TestCase):
    def test_mac_dinh_bat(self):
        self.assertTrue(cai_dat_chien_dau({})["ve_tri_lieu"])
        self.assertTrue(cai_dat_chien_dau({"chien_dau": {"bat": True}})["ve_tri_lieu"])
        self.assertEqual(PHAN_TRAM_VE_TRI_LIEU, 20)

    def test_tat_thi_khong_ve(self):
        cai = {"chien_dau": {"ve_tri_lieu": False}}
        self.assertFalse(can_ve_tri_lieu(cai, _tt(10)))

    def test_bat_va_mau_thap(self):
        self.assertTrue(can_ve_tri_lieu({}, _tt(10)))
        self.assertFalse(can_ve_tri_lieu({}, _tt(20)))


class TestNenVeTriLieu(unittest.TestCase):
    def test_map_thuong_mau_thap_thi_ve(self):
        self.assertTrue(nen_ve_tri_lieu({}, _tt(10, ten_map="Hỏa Diệm Sơn"), _cam))

    def test_dai_ly_thi_khong_bam_ve_thanh(self):
        self.assertFalse(nen_ve_tri_lieu({}, _tt(10, ten_map=pb.MAP_DAI_LY), _cam))

    def test_trong_loi_dai_thi_khong_ve(self):
        self.assertFalse(nen_ve_tri_lieu({}, _tt(10, ten_map=pb.MAP_SAT_TINH), _cam))

    def test_trong_pmp_thi_khong_ve(self):
        self.assertFalse(nen_ve_tri_lieu({}, _tt(10, ten_map=pb.MAP_PMP), _cam))

    def test_theo_doi_hoac_ac_tac_thi_khong_ve(self):
        tt = _tt(10)
        self.assertFalse(nen_ve_tri_lieu({}, tt, _cam, dang_theo_doi=True))
        self.assertFalse(nen_ve_tri_lieu({}, tt, _cam, dang_ac_tac=True))


if __name__ == "__main__":
    unittest.main()
