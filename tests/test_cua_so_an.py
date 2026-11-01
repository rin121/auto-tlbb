import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cua_so_game  # noqa: E402


class TestDuyTriAn(unittest.TestCase):
    def setUp(self):
        cua_so_game._cua_so_da_an.clear()
        cua_so_game._pid_can_an.clear()

    def tearDown(self):
        cua_so_game._cua_so_da_an.clear()
        cua_so_game._pid_can_an.clear()

    @patch.object(cua_so_game, "tim_cua_so_game", return_value=[])
    @patch.object(cua_so_game, "_luu_cua_so_da_an")
    @patch.object(cua_so_game.win32gui, "ShowWindow")
    @patch.object(cua_so_game.win32gui, "IsWindowVisible", return_value=True)
    @patch.object(cua_so_game, "_con_la_cua_so_da_an", return_value=True)
    def test_an_lai_khi_hien(self, _con, _vis, show, _luu, _tim):
        cua_so_game._cua_so_da_an[100] = 200
        cua_so_game._pid_can_an.add(200)
        so = cua_so_game.duy_tri_an()
        self.assertEqual(so, 1)
        show.assert_called_with(100, cua_so_game.win32con.SW_HIDE)

    @patch.object(cua_so_game, "tim_cua_so_game", return_value=[{"hwnd": 300, "pid": 400}])
    @patch.object(cua_so_game, "_luu_cua_so_da_an")
    @patch.object(cua_so_game.win32gui, "ShowWindow")
    @patch.object(cua_so_game.win32gui, "IsWindowVisible", return_value=True)
    @patch.object(cua_so_game, "_con_la_cua_so_da_an", return_value=True)
    def test_pid_moi_an_hwnd_moi(self, _con, _vis, show, _luu, _tim):
        cua_so_game._pid_can_an.add(400)
        so = cua_so_game.duy_tri_an()
        self.assertEqual(so, 1)
        self.assertIn(300, cua_so_game._cua_so_da_an)
        show.assert_called_with(300, cua_so_game.win32con.SW_HIDE)

    @patch.object(cua_so_game, "_pid_cua", return_value=500)
    @patch.object(cua_so_game.win32gui, "IsWindow", return_value=True)
    @patch.object(cua_so_game.win32gui, "IsWindowVisible", return_value=True)
    @patch.object(cua_so_game.win32gui, "ShowWindow")
    @patch.object(cua_so_game, "_luu_cua_so_da_an")
    def test_an_cua_so_them_pid(self, _luu, show, _vis, _win, _pid):
        cua_so_game.an_cua_so([999])
        self.assertIn(500, cua_so_game._pid_can_an)
        show.assert_called_with(999, cua_so_game.win32con.SW_HIDE)


if __name__ == "__main__":
    unittest.main()
