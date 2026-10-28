import os
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import giao_acc_chinh as gac  # noqa: E402


class TestBoQuaTaiKhoanChuaCoNhanVat(unittest.TestCase):
    """GAC-01: giao cho acc chính bỏ tài khoản chưa từng đăng nhập / nhân vật chưa có (khoảng trống caychay48..68)."""

    def setUp(self):
        self.thu_muc = tempfile.mkdtemp()
        tk = os.path.join(self.thu_muc, "#636179636861793437")  # caychay47
        os.makedirs(tk)
        open(os.path.join(tk, "#636179636861793437.pfc"), "w").close()

    def tearDown(self):
        shutil.rmtree(self.thu_muc, ignore_errors=True)

    def test_ma_thu_muc_giong_game(self):
        self.assertEqual(gac._ma_thu_muc("caychay72"), "#636179636861793732")
        self.assertEqual(gac._ma_thu_muc("GaoDẻLâu"), "#47616f44eb4ce275")

    def test_ly_do(self):
        ly_do = gac.ly_do_khong_co_nhan_vat
        self.assertIsNone(ly_do("caychay47", "caychay47", self.thu_muc))
        self.assertEqual(ly_do("caychay47", "caychay477", self.thu_muc), "chưa có nhân vật")
        self.assertEqual(ly_do("caychay48", "caychay48", self.thu_muc), "tài khoản chưa từng đăng nhập")

    def test_da_tao_hoac_dang_online_thi_co(self):
        ly_do = gac.ly_do_khong_co_nhan_vat
        self.assertIsNone(ly_do("caychay47", "caychay477", self.thu_muc, da_tao={"caychay477"}))
        self.assertIsNone(ly_do("caychay48", "caychay48", self.thu_muc, online={"caychay48"}))

    def test_khong_thay_thu_muc_accounts_thi_khong_loc(self):
        self.assertIsNone(gac.ly_do_khong_co_nhan_vat("caychay48", "caychay48",
                                                      os.path.join(self.thu_muc, "khong_co")))

    def test_danh_sach_bo_qua_va_ghi_ly_do(self):
        ds = [{"ten_dang_nhap": t} for t in ("caychay47", "caychay48")]
        bo_qua = []
        with patch.object(gac, "cac_tai_khoan_dang_tich", return_value=ds), \
                patch.object(gac, "thu_muc_accounts", return_value=self.thu_muc), \
                patch.object(gac, "cac_nhan_vat_dang_online", return_value=set()), \
                patch.object(gac, "da_xong", return_value=[]), \
                patch.object(gac, "ten_round", lambda tk, r: tk + tk[-1] * r), \
                patch.object(gac, "_loc_nhan_vat_pho_ban", return_value=True):
            kq = gac.cac_nhan_vat_pho_ban("acc_chinh", True, bo_qua)
        self.assertEqual([ten for _, ten in kq], ["caychay47"])
        self.assertIn(("caychay48", "caychay48", "tài khoản chưa từng đăng nhập"), bo_qua)
        self.assertIn(("caychay47", "caychay477", "chưa có nhân vật"), bo_qua)


class TestBoQuaCungTaiKhoanKhongCoDo(unittest.TestCase):
    """GAC-02: «Tất cả acc phó bản» — một nhân vật không có đồ thì bỏ các nhân vật còn lại của tài khoản đó."""

    DS = [{"ten_dang_nhap": f"caychay{i}"} for i in (14, 16, 18, 19)]

    def _truong(self):
        with patch.object(gac, "cac_tai_khoan_dang_tich", return_value=self.DS), \
                patch.object(gac, "chia_nhom", lambda ds: [ds]), \
                patch.object(gac, "ten_round", lambda tk, r: tk + tk[-1] * r), \
                patch.object(gac.cau_hinh, "chung", return_value={"xv_truong_nhom": [["caychay18", "caychay188"]]}):
            return gac.ten_cac_truong_nhom("acc_chinh")

    def test_truong_nhom_gom_moi_round_va_nguoi_bu(self):
        self.assertEqual(self._truong(), {"caychay14", "caychay144", "caychay1444", "caychay188"})

    def test_bo_qua_nhan_vat_khac_cung_tai_khoan(self):
        truong = self._truong()
        khong_co = {"caychay16"}
        self.assertTrue(gac.bo_qua_cung_tai_khoan(self.DS[1], "caychay166", khong_co, truong))
        self.assertTrue(gac.bo_qua_cung_tai_khoan(self.DS[1], "caychay1666", khong_co, truong))
        self.assertFalse(gac.bo_qua_cung_tai_khoan(self.DS[2], "caychay188", {"caychay18"}, truong))
        self.assertFalse(gac.bo_qua_cung_tai_khoan(self.DS[3], "caychay199", khong_co, truong))


if __name__ == "__main__":
    unittest.main()
