import os
import sys
import unittest

THU_MUC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, THU_MUC)
sys.path.insert(0, os.path.join(THU_MUC, "cong_cu"))

import ghi_pmp  # noqa: E402


class TestDocTrangThai(unittest.TestCase):
    def test_doc_day_du(self):
        tt = ghi_pmp.doc_trang_thai("caychay24|Phiêu Miểu Phong|41.5|105|800|1000|50|100|0|1|1|Tang Thổ Công|0.42")
        self.assertEqual((tt["ten"], tt["map"], tt["x"], tt["y"]), ("caychay24", "Phiêu Miểu Phong", 41, 105))
        self.assertEqual(ghi_pmp.phan_tram(tt["hp"], tt["hp_max"]), 80)
        self.assertTrue(tt["theo"] and tt["truong"] and not tt["cuoi"])
        self.assertEqual((tt["muc_tieu"], tt["mau_muc_tieu"]), ("Tang Thổ Công", 42))

    def test_khong_muc_tieu(self):
        tt = ghi_pmp.doc_trang_thai("a|Đại Lý|1|2|1|1|1|1|1|0|0||")
        self.assertEqual((tt["muc_tieu"], tt["mau_muc_tieu"]), ("", None))

    def test_chua_vao_game(self):
        self.assertIsNone(ghi_pmp.doc_trang_thai(""))
        self.assertIsNone(ghi_pmp.doc_trang_thai("thiếu|cột"))


class TestDocHoiThoai(unittest.TestCase):
    def test_khong_mo(self):
        self.assertIsNone(ghi_pmp.doc_hoi_thoai(""))

    def test_cac_dong_va_thong_tin(self):
        npc, dong = ghi_pmp.doc_hoi_thoai("1\tTang Thổ Công\n3\t402271\t1\tKhiêu chiến\ninfo\t-1\t-1\tChờ 5 giây\n")
        self.assertEqual(npc, "Tang Thổ Công")
        self.assertEqual(dong, ["Khiêu chiến (mã 402271, 1; loại 3)", "[thông tin] Chờ 5 giây"])


if __name__ == "__main__":
    unittest.main()
