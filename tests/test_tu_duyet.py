import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bang_ma_viscii import ma_hoa  # noqa: E402
import tu_duyet  # noqa: E402

CHU_THOAT = "Các hạ quyết rời bỏ thế giới Thiên Long Bát Bộ?"
CHU_NGAN_LUONG = ("Ngân lượng của các hạ đã quá mức giới hạn, hãy tiêu bớt đi. Lưu ý: không được "
                  "thoát khỏi trò chơi hoặc dịch đổi địa danh")


class LuaGia:
    """MessageBox_Self đang hiện với nội dung cho trước; ghi lại có bấm Duyệt hay không."""

    def __init__(self, noi_dung):
        self.noi_dung = ma_hoa(noi_dung)
        self.so_lan_bam = 0

    def chay(self, ma, so_lan_thu=1):
        if "MessageBox_Self_OK_Clicked()" in ma:
            self.so_lan_bam += 1
            return b"da_duyet\t0\t" + self.noi_dung
        if "return chu" in ma:
            return self.noi_dung
        return b"MessageBox_Self\n"


class TestTuDuyetHopThoatGame(unittest.TestCase):
    def _chay(self, noi_dung, so_lan=1):
        lua, log = LuaGia(noi_dung), []
        td = tu_duyet.TuDuyet(lua, log.append)
        for _ in range(so_lan):
            td.kiem_tra(False)
        return lua, log

    def test_duyet_hop_thoat_game(self):
        """Tắt game (bấm X, «Đóng tất cả cửa sổ» ở taskbar): hộp «rời bỏ thế giới» được duyệt, game tự tắt."""
        lua, log = self._chay(CHU_THOAT)
        self.assertEqual(lua.so_lan_bam, 1)
        self.assertEqual(log, [f"Tự duyệt [MessageBox_Self]: {CHU_THOAT}"])

    def test_van_duyet_hop_thuong(self):
        lua, log = self._chay("Các hạ có chắc muốn tiêu hủy vật phẩm này?")
        self.assertEqual(lua.so_lan_bam, 1)
        self.assertTrue(log[0].startswith("Tự duyệt [MessageBox_Self]"))

    def test_hop_ngan_luong_nhac_thoat_tro_choi_van_duyet(self):
        lua, _ = self._chay(CHU_NGAN_LUONG)
        self.assertEqual(lua.so_lan_bam, 1)


if __name__ == "__main__":
    unittest.main()
