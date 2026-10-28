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

    def test_khong_bam_duyet_hop_thoat_game(self):
        lua, log = self._chay(CHU_THOAT, so_lan=3)
        self.assertEqual(lua.so_lan_bam, 0)
        self.assertEqual(len(log), 1)
        self.assertIn("Không tự duyệt", log[0])

    def test_van_duyet_hop_thuong(self):
        lua, log = self._chay("Các hạ có chắc muốn tiêu hủy vật phẩm này?")
        self.assertEqual(lua.so_lan_bam, 1)
        self.assertTrue(log[0].startswith("Tự duyệt [MessageBox_Self]"))

    def test_hop_ngan_luong_nhac_thoat_tro_choi_van_duyet(self):
        lua, _ = self._chay(CHU_NGAN_LUONG)
        self.assertEqual(lua.so_lan_bam, 1)

    def test_nguoi_dung_vua_tat_cua_so_thi_duyet_hop_thoat(self):
        lua, log = LuaGia(CHU_THOAT), []
        td = tu_duyet.TuDuyet(lua, log.append, lambda: True)
        td.kiem_tra(False)
        self.assertEqual(lua.so_lan_bam, 1)
        self.assertTrue(log[0].startswith("Tự duyệt [MessageBox_Self]"))

    def test_hop_thoat_tu_hien_o_game_nen_bam_vao_sau_van_khong_duyet(self):
        tren_cung = [False]
        lua, log = LuaGia(CHU_THOAT), []
        td = tu_duyet.TuDuyet(lua, log.append, lambda: tren_cung[0])
        td.kiem_tra(False)
        tren_cung[0] = True
        td.kiem_tra(False)
        self.assertEqual(lua.so_lan_bam, 0)
        self.assertIn("Không tự duyệt", log[0])

    def test_vua_o_tren_cung(self):
        tu_duyet._luc_tren_cung[123] = tu_duyet.time.time() - 3
        tu_duyet._luc_tren_cung[456] = tu_duyet.time.time() - tu_duyet.GIAY_NGUOI_DUNG_TAT - 5
        self.assertTrue(tu_duyet.vua_o_tren_cung(123))
        self.assertFalse(tu_duyet.vua_o_tren_cung(456))
        self.assertFalse(tu_duyet.vua_o_tren_cung(789))

    def test_khong_duoc_duyet(self):
        self.assertTrue(tu_duyet.khong_duoc_duyet(CHU_THOAT))
        self.assertTrue(tu_duyet.khong_duoc_duyet("#cff0000Các hạ quyết RỜI BỎ thế giới?"))
        self.assertFalse(tu_duyet.khong_duoc_duyet(CHU_NGAN_LUONG))


if __name__ == "__main__":
    unittest.main()
