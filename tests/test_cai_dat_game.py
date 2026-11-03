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

    def test_scale_800x600_ghi_resoution(self):
        with tempfile.TemporaryDirectory() as td:
            bin_cfg = os.path.join(td, "Bin")
            os.makedirs(bin_cfg)
            with open(os.path.join(bin_cfg, "System.cfg"), "w", encoding="utf-8") as f:
                f.write("[Variable]\nView_Resoution=1024,768\nView_FullScreen=1\n")
            tong = cai_dat_game.chuan_bi_thu_muc_game(
                td, {"giam_do_hoa": False, "scale_800x600": True,
                     "scale_rong": 800, "scale_cao": 600})
            self.assertGreater(tong, 0)
            with open(os.path.join(bin_cfg, "System.cfg"), encoding="utf-8") as f:
                chu = f.read()
            self.assertIn("View_Resoution=800,600", chu)
            self.assertIn("View_FullScreen=0", chu)

    def test_scale_tuy_chinh_ghi_resoution(self):
        with tempfile.TemporaryDirectory() as td:
            bin_cfg = os.path.join(td, "Bin")
            os.makedirs(bin_cfg)
            with open(os.path.join(bin_cfg, "System.cfg"), "w", encoding="utf-8") as f:
                f.write("[Variable]\nView_Resoution=800,600\nView_FullScreen=1\n")
            tong = cai_dat_game.chuan_bi_thu_muc_game(
                td, {"giam_do_hoa": False, "scale_800x600": True,
                     "scale_rong": 1024, "scale_cao": 768})
            self.assertGreater(tong, 0)
            with open(os.path.join(bin_cfg, "System.cfg"), encoding="utf-8") as f:
                chu = f.read()
            self.assertIn("View_Resoution=1024,768", chu)
            self.assertIn("View_FullScreen=0", chu)

    def test_chi_tat_hieu_ung_van_ghi_view(self):
        with tempfile.TemporaryDirectory() as td:
            bin_cfg = os.path.join(td, "Bin")
            os.makedirs(bin_cfg)
            with open(os.path.join(bin_cfg, "System.cfg"), "w", encoding="utf-8") as f:
                f.write("[Variable]\nView_EffectLevel=2\n")
            tong = cai_dat_game.chuan_bi_thu_muc_game(
                td, {"giam_do_hoa": False, "tat_het_hieu_ung": True})
            self.assertGreater(tong, 0)
            with open(os.path.join(bin_cfg, "System.cfg"), encoding="utf-8") as f:
                chu = f.read()
            self.assertIn("View_EffectLevel=0", chu)
            self.assertIn("View_HumanHighLight=0", chu)

    def test_giam_do_hoa_va_tat_hieu_ung_gop_cfg(self):
        chung = {"giam_do_hoa": True, "tat_het_hieu_ung": True,
                 "fps_max": 25, "fps_front": 25, "fps_back": 5}
        with tempfile.TemporaryDirectory() as td:
            bin_cfg = os.path.join(td, "Bin")
            os.makedirs(bin_cfg)
            with open(os.path.join(bin_cfg, "System.cfg"), "w", encoding="utf-8") as f:
                f.write("[Variable]\nSystem_MaxFPS=100\nView_HumanHighLight=1\n")
            tong = cai_dat_game.chuan_bi_thu_muc_game(td, chung)
            self.assertGreater(tong, 0)
            with open(os.path.join(bin_cfg, "System.cfg"), encoding="utf-8") as f:
                chu = f.read()
            self.assertIn("System_MaxFPS=25", chu)
            self.assertIn("View_HumanHighLight=0", chu)


class TestMaApDung(unittest.TestCase):
    def test_giam_do_hoa_co_fps_lua(self):
        ma = cai_dat_game.ma_ap_dung(False, True, {"fps_max": 25, "fps_front": 25, "fps_back": 5})
        self.assertIn('bien("System_MaxFPS", "25")', ma)
        self.assertIn('bien("System_MaxFPS_Front", "25")', ma)
        self.assertIn('bien("System_MaxFPS_Back", "5")', ma)
        self.assertIn("if Variable:GetVariable(k) ~= v then", ma)

    def test_tat_hieu_ung_co_wtdh_va_effect_level(self):
        ma = cai_dat_game.ma_ap_dung_hieu_ung()
        self.assertIn('hien_thi("wtdh", 0)', ma)
        self.assertIn('hien_thi("qpfg", 0)', ma)
        self.assertIn('bien("View_EffectLevel", "0")', ma)
        self.assertIn('bien("View_ModelEffect", "0")', ma)
        self.assertIn('bien("View_HumanHighLight", "0")', ma)
        self.assertIn('bien("View_Floodlight", "0")', ma)
        self.assertNotIn("if Variable:GetVariable(k) ~= v then", ma)
        self.assertNotIn("if tonumber(SystemSetup:View_GetData(k)) ~= v then", ma)
        self.assertIn("Variable:SetVariable(k, v, 0) doi = doi + 1 end", ma)
        self.assertIn("SystemSetup:View_SetData(k, v) doi = doi + 1 end", ma)

    def test_scale_800x600_lua(self):
        ma = cai_dat_game.ma_ap_dung_do_phan_giai(
            {"scale_rong": 800, "scale_cao": 600})
        self.assertIn('bien("View_Resoution", "")', ma)
        self.assertIn('bien("View_Resoution", "800,600")', ma)
        self.assertIn('bien("View_FullScreen", "0")', ma)
        self.assertIn('hien_thi("qpms", 0)', ma)

    def test_scale_tuy_chinh_lua(self):
        ma = cai_dat_game.ma_ap_dung_do_phan_giai(
            {"scale_rong": 960, "scale_cao": 540})
        self.assertIn('bien("View_Resoution", "960,540")', ma)

    def test_do_phan_giai_kep_khoang(self):
        rong, cao = cai_dat_game.do_phan_giai_tu_cau_hinh(
            {"scale_rong": 100, "scale_cao": 9999})
        self.assertEqual(rong, cai_dat_game.DO_PHAN_GIAI_RONG_MIN)
        self.assertEqual(cao, cai_dat_game.DO_PHAN_GIAI_CAO_MAX)


if __name__ == "__main__":
    unittest.main()
