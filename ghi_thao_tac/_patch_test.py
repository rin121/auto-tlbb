from pathlib import Path

p = Path(r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\tests\test_gop_acc_chinh.py")
t = p.read_text(encoding="utf-8")
start = t.index("    def test_tim_o_phieu_dung_khi_doc_ten_sau_chon(self):")
end = t.index("    def test_mot_lan_doi_phieu_loi_lua_thi_false(self):")
new = r'''    def test_tim_o_phieu_dung_khi_doc_ten_sau_chon(self):
        from unittest.mock import MagicMock, patch
        import giao_acc_chinh as gac
        luong = gac.GiaoAccChinhEngine.__new__(gac.GiaoAccChinhEngine)
        luong.tk_chinh = {"nhan_vat": "Gao"}
        luong.dung = MagicMock()
        luong.dung.wait = lambda *_: None
        luong._kiem_tra_dung = lambda: None
        logs = []
        luong.in_log = logs.append
        luong._o_phieu_20k_30k = lambda _mo, bao_raw=False: []
        luong.chinh = MagicMock()
        ten_theo_o = {7: "Phiếu KNB 20K", 9: "Phiếu KNB 30K"}

        def chay(ma, giay_cho=3, so_lan_thu=5):
            for i, ten in ten_theo_o.items():
                if f", {i} " in ma or ma.rstrip().endswith(f", {i}"):
                    return ten.encode("utf-8")
            return b""

        luong.chinh.lua.chay.side_effect = chay
        with patch.object(gac, "giai_ma", side_effect=lambda b: b.decode("utf-8") if isinstance(b, bytes) else b), \
                patch.object(gac, "SO_O_DOI_TIM_TOI_DA", 12):
            self.assertEqual(luong._tim_o_phieu_20k_30k("XiaoXiang_DuiHuanUI2"), [7, 9])
        self.assertTrue(any("ô 7 = Phiếu KNB 20K" in d for d in logs))
        self.assertTrue(any("ô 9 = Phiếu KNB 30K" in d for d in logs))
        self.assertEqual(luong._o_phieu_20k_30k_tu_chuoi(
            "7\tPhiếu KNB 20K\n9\tPhiếu KNB 30K\n"), [7, 9])

'''
p.write_text(t[:start] + new + t[end:], encoding="utf-8")
print("patched ok")
