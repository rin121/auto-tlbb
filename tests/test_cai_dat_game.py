import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cai_dat_game  # noqa: E402


class TestCapNhatCfg(unittest.TestCase):
    def test_them_fps_back(self):
        with tempfile.TemporaryDirectory() as td:
            duong = os.path.join(td, "a.pfc")
            with open(duong, "w", encoding="utf-8") as f:
                f.write("[Variable]\nView_EffectLevel=1\n")
            doi = cai_dat_game._cap_nhat_tep_cfg(duong, {"System_MaxFPS_Back": "5"})
            self.assertGreaterEqual(doi, 1)
            with open(duong, encoding="utf-8") as f:
                chu = f.read()
            self.assertIn("System_MaxFPS_Back=5", chu)
            self.assertIn("View_EffectLevel=1", chu)


class TestChuanBiThuMuc(unittest.TestCase):
    def test_ghi_fps_va_view(self):
        chung = {"giam_do_hoa": True, "fps_max": 25, "fps_front": 25, "fps_back": 5}
        with tempfile.TemporaryDirectory() as td:
            bin_cfg = os.path.join(td, "Bin")
            acc = os.path.join(td, "Accounts")
            os.makedirs(bin_cfg)
            os.makedirs(acc)
            with open(os.path.join(bin_cfg, "System.cfg"), "w", encoding="utf-8") as f:
                f.write("[Variable]\nSystem_MaxFPS=100\n")
            with open(os.path.join(acc, "System.cfg"), "w", encoding="utf-8") as f:
                f.write("[Variable]\n")
            with open(os.path.join(acc, "x.pfc"), "w", encoding="utf-8") as f:
                f.write("[Variable]\n")
            tong = cai_dat_game.chuan_bi_thu_muc_game(td, chung)
            self.assertGreater(tong, 0)
            with open(os.path.join(bin_cfg, "System.cfg"), encoding="utf-8") as f:
                chu = f.read()
            self.assertIn("System_MaxFPS=25", chu)
            self.assertIn("System_MaxFPS_Back=5", chu)
            self.assertIn("View_EffectLevel=0", chu)

    def test_tat_giam_do_hoa_thi_bo_qua(self):
        with tempfile.TemporaryDirectory() as td:
            os.makedirs(os.path.join(td, "Bin"))
            with open(os.path.join(td, "Bin", "System.cfg"), "w", encoding="utf-8") as f:
                f.write("[Variable]\nSystem_MaxFPS=100\n")
            self.assertEqual(cai_dat_game.chuan_bi_thu_muc_game(td, {"giam_do_hoa": False}), 0)


class TestMaApDung(unittest.TestCase):
    def test_giam_do_hoa_co_fps_lua(self):
        ma = cai_dat_game.ma_ap_dung(False, True, {"fps_max": 25, "fps_front": 25, "fps_back": 5})
        self.assertIn('bien("System_MaxFPS", "25")', ma)
        self.assertIn('bien("System_MaxFPS_Front", "25")', ma)
        self.assertIn('bien("System_MaxFPS_Back", "5")', ma)

    def test_tat_hieu_ung_co_wtdh_va_effect_level(self):
        ma = cai_dat_game.ma_ap_dung_hieu_ung()
        self.assertIn('hien_thi("wtdh", 0)', ma)
        self.assertIn('bien("View_EffectLevel", "0")', ma)
        self.assertIn('bien("View_ModelEffect", "0")', ma)


if __name__ == "__main__":
    unittest.main()
