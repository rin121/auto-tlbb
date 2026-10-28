import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import giao_acc_chinh as gac  # noqa: E402
import so_tui_do  # noqa: E402

LOAI_TRU = so_tui_do.cac_tu_loai_tru("Tân Thủ, Càn Khôn Hồ")
TUI_CO_DO = {("base", 0): (101, 1, "Tân Thủ Lệnh"), ("base", 1): (202, 3, "Huyền Thiết"),
             ("material", 0): (303, 1, "Đồ khóa")}
TUI_TRONG = {("base", 0): (101, 1, "Tân Thủ Lệnh")}


class TestSoTuiDo(unittest.TestCase):
    """GAC-03: sổ túi đồ lưu mãi, xoay vòng ghi, giao acc chính đọc / đánh dấu đã giao."""

    def setUp(self):
        self.thu_muc = tempfile.mkdtemp()
        self.file = os.path.join(self.thu_muc, "so_tui_do.json")

    def tearDown(self):
        shutil.rmtree(self.thu_muc, ignore_errors=True)

    def _muc(self, ten):
        return so_tui_do.muc_cua(so_tui_do.doc(self.file), ten)

    def test_dem_o_tru_loai_tru_va_ma_khong_giao(self):
        self.assertEqual(so_tui_do.dem_o(TUI_CO_DO, LOAI_TRU), 2)
        self.assertEqual(so_tui_do.dem_o(TUI_CO_DO, LOAI_TRU, {303}), 1)
        self.assertEqual(so_tui_do.dem_o(TUI_TRONG, LOAI_TRU), 0)

    def test_dau_round_chua_ro_cuoi_round_ghi_so_o(self):
        so_tui_do.ghi_chua_ro("caychay16", "caychay166", self.file)
        muc = self._muc("caychay166")
        self.assertTrue(so_tui_do.can_giao(muc))
        self.assertFalse(so_tui_do.chac_khong_co_do(muc))
        so_tui_do.ghi_so_o("caychay16", "caychay166", TUI_TRONG, LOAI_TRU, self.file)
        muc = self._muc("caychay166")
        self.assertTrue(so_tui_do.chac_khong_co_do(muc))
        self.assertFalse(so_tui_do.can_giao(muc))

    def test_giao_xong_danh_dau_va_nho_ma_khong_giao(self):
        so_tui_do.ghi_so_o("caychay16", "caychay166", TUI_CO_DO, LOAI_TRU, self.file)
        self.assertEqual(self._muc("caychay166")["so_o"], 2)
        so_tui_do.ghi_da_giao("caychay16", "caychay166", {303}, self.file)
        muc = self._muc("caychay166")
        self.assertTrue(muc["da_giao_acc_chinh"])
        self.assertEqual(muc["so_o"], 0)
        # Lần sau đồ khóa còn nằm trong túi thì không đếm, không phải đăng nhập lại chỉ vì nó.
        so_tui_do.ghi_so_o("caychay16", "caychay166", {("material", 0): (303, 1, "Đồ khóa")}, LOAI_TRU, self.file)
        self.assertTrue(so_tui_do.chac_khong_co_do(self._muc("caychay166")))

    def test_co_do_moi_bo_dau_da_giao(self):
        so_tui_do.ghi_da_giao("caychay16", "caychay166", (), self.file)
        so_tui_do.ghi_so_o("caychay16", "caychay166", TUI_CO_DO, LOAI_TRU, self.file)
        muc = self._muc("caychay166")
        self.assertFalse(muc["da_giao_acc_chinh"])
        self.assertTrue(so_tui_do.can_giao(muc))

    def test_so_luu_mai_khong_xoa_theo_ngay(self):
        so_tui_do.ghi_so_o("caychay16", "caychay166", TUI_CO_DO, LOAI_TRU, self.file)
        so_tui_do.ghi_so_o("caychay18", "caychay188", TUI_TRONG, LOAI_TRU, self.file)
        self.assertEqual(set(so_tui_do.doc(self.file)), {"caychay166", "caychay188"})


class TestApDungSoTui(unittest.TestCase):
    TK = {f"caychay{i}": {"ten_dang_nhap": f"caychay{i}", "mat_khau": "x"} for i in (14, 16, 18)}

    def _chay(self, ds, so):
        with patch.object(gac.cau_hinh, "tai_khoan_pho_ban", return_value=list(self.TK.values())):
            return gac.ap_dung_so_tui([(self.TK[tk], ten) for tk, ten in ds], "acc_chinh", so)

    def test_bo_nhan_vat_so_ghi_khong_co_do(self):
        so = {"caychay14": {"tk": "caychay14", "ten": "caychay14", "trang_thai": "da_ghi", "so_o": 0}}
        kq, bo, them = self._chay([("caychay14", "caychay14"), ("caychay18", "caychay18")], so)
        self.assertEqual([ten for _, ten in kq], ["caychay18"])
        self.assertEqual(bo, ["caychay14"])
        self.assertEqual(them, [])

    def test_them_doi_vien_so_ghi_con_do_hoac_chua_ro(self):
        so = {"caychay166": {"tk": "caychay16", "ten": "caychay166", "trang_thai": "da_ghi", "so_o": 3},
              "caychay1666": {"tk": "caychay16", "ten": "caychay1666", "trang_thai": "chua_ro"},
              "caychay16": {"tk": "caychay16", "ten": "caychay16", "trang_thai": "da_ghi", "so_o": 0},
              "khac": {"tk": "khong_co_mat_khau", "ten": "khac", "trang_thai": "da_ghi", "so_o": 5}}
        kq, _, them = self._chay([("caychay14", "caychay14"), ("caychay18", "caychay18")], so)
        self.assertEqual([ten for _, ten in kq], ["caychay14", "caychay166", "caychay1666", "caychay18"])
        self.assertEqual({ten for _, ten in them}, {"caychay166", "caychay1666"})

    def test_khong_them_trung_nhan_vat_da_co(self):
        so = {"caychay14": {"tk": "caychay14", "ten": "caychay14", "trang_thai": "da_ghi", "so_o": 2}}
        kq, _, them = self._chay([("caychay14", "caychay14")], so)
        self.assertEqual([ten for _, ten in kq], ["caychay14"])
        self.assertEqual(them, [])


if __name__ == "__main__":
    unittest.main()
