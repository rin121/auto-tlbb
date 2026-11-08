"""Tab Tài khoản: nút Xóa chỉ theo dòng đang chọn (multi-select), không theo ô tick XV/Bật."""
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cau_hinh  # noqa: E402
from giao_dien import UngDung  # noqa: E402


class TestTenTaiKhoanDangChon(unittest.TestCase):
    def test_gom_multi_select_hai_bang(self):
        pb = MagicMock()
        pb.selection.return_value = (
            f"{cau_hinh.KHOA_TK_PHO_BAN}:cosato33",
            f"{cau_hinh.KHOA_TK_PHO_BAN}:cosato34",
        )
        tr = MagicMock()
        tr.selection.return_value = (f"{cau_hinh.KHOA_TK_TRAIN}:train1",)
        kq = UngDung.ten_tai_khoan_dang_chon({
            cau_hinh.KHOA_TK_PHO_BAN: pb,
            cau_hinh.KHOA_TK_TRAIN: tr,
        })
        self.assertEqual(kq, {"cosato33", "cosato34", "train1"})

    def test_khong_chon_thi_rong(self):
        bang = MagicMock()
        bang.selection.return_value = ()
        self.assertEqual(UngDung.ten_tai_khoan_dang_chon({cau_hinh.KHOA_TK_PHO_BAN: bang}), set())


if __name__ == "__main__":
    unittest.main()
