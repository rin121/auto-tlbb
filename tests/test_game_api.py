"""Parse Game.thong_tin — chuỗi Lua thiếu trường không được văng IndexError."""
import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import game_api as ga  # noqa: E402


class TestThongTin(unittest.TestCase):
    def _game(self, raw):
        game = ga.Game.__new__(ga.Game)
        game.lua = MagicMock()
        game.lua.chay.return_value = raw
        return game

    def test_du_truong(self):
        raw = b"beai1000|69|Dai Ly|10|20|100|200|50|80|3|beai10"
        tt = self._game(raw).thong_tin()
        self.assertEqual(tt["ten"], "beai1000")
        self.assertEqual(tt["level"], 69)
        self.assertEqual(tt["map"], "Dai Ly")
        self.assertEqual(tt["x"], 10)
        self.assertEqual(tt["y"], 20)
        self.assertEqual(tt["hp"], 100)
        self.assertEqual(tt["mon_phai"], 3)
        self.assertEqual(tt["tai_khoan"], "beai10")

    def test_thieu_truong_thi_none(self):
        self.assertIsNone(self._game(b"beai1000|69|Dai Ly").thong_tin())
        self.assertIsNone(self._game(b"").thong_tin())
        self.assertIsNone(self._game(b"|69|Dai Ly|1|2|3|4|5|6|7|tk").thong_tin())

    def test_so_khong_hop_le_thi_none(self):
        raw = b"beai1000|xx|Dai Ly|10|20|100|200|50|80|3|beai10"
        self.assertIsNone(self._game(raw).thong_tin())

    def test_mon_phai_nil(self):
        raw = b"beai1000|69|Dai Ly|10|20|100|200|50|80|nil|beai10"
        tt = self._game(raw).thong_tin()
        self.assertIsNone(tt["mon_phai"])
        self.assertEqual(tt["tai_khoan"], "beai10")


if __name__ == "__main__":
    unittest.main()
