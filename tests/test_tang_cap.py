import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cau_hinh  # noqa: E402
import tang_cap  # noqa: E402
from chien_dau import cai_dat_chien_dau  # noqa: E402


class _Lua:
    def __init__(self, tra_ve):
        self.tra_ve, self.ma = tra_ve, []

    def chay(self, ma):
        self.ma.append(ma)
        return self.tra_ve


class TestTuTangCap(unittest.TestCase):
    def test_chua_du_kinh_nghiem(self):
        self.assertIsNone(tang_cap.thu_tang_cap(_Lua(b"")))

    def test_du_kinh_nghiem_thi_bam_va_tra_cap(self):
        lua = _Lua(b"44")
        self.assertEqual(tang_cap.thu_tang_cap(lua), 44)
        self.assertEqual(lua.ma, [tang_cap.MA_TANG_CAP])

    def test_ma_lua_giong_nut_thang_cap(self):
        ma = tang_cap.MA_TANG_CAP
        for chu in ('Player:GetData("EXP")', 'Player:GetData("NEEDEXP")', "LEVEL_MAX_ENABLE",
                    "SelfEquip_AskLevelup()", "AskLevelUp(0)", "SelfEquip_Env"):
            self.assertIn(chu, ma)

    def test_mac_dinh_bat_cho_moi_nhan_vat(self):
        self.assertTrue(cai_dat_chien_dau({})["tu_tang_cap"])
        self.assertTrue(cai_dat_chien_dau({"chien_dau": {"bat": True, "ban_kinh": 20}})["tu_tang_cap"])
        self.assertFalse(cai_dat_chien_dau({"chien_dau": {"tu_tang_cap": False}})["tu_tang_cap"])


class TestBatTuDuyetMotLan(unittest.TestCase):
    def test_bat_mot_lan_roi_giu_lua_chon(self):
        du_lieu = {"tu_duyet_popup": False}
        self.assertTrue(cau_hinh._bat_tu_duyet_mot_lan(du_lieu))
        self.assertTrue(du_lieu["tu_duyet_popup"])
        du_lieu["tu_duyet_popup"] = False
        self.assertFalse(cau_hinh._bat_tu_duyet_mot_lan(du_lieu))
        self.assertFalse(du_lieu["tu_duyet_popup"])

    def test_mac_dinh_moi_la_bat(self):
        self.assertTrue(cau_hinh.MAC_DINH_CHUNG["tu_duyet_popup"])


if __name__ == "__main__":
    unittest.main()
