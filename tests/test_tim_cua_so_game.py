import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cua_so_game as cs  # noqa: E402


class TestTimCuaSoGameAn(unittest.TestCase):
    """Client ẩn (SW_HIDE / GAuto kiểu 2) vẫn phải được tim_cua_so_game thấy."""

    def setUp(self):
        cs._cua_so_da_an.clear()

    @patch.object(cs.psutil, "process_iter", return_value=[])
    @patch.object(cs, "vung_client", return_value=(0, 0, 800, 600))
    @patch.object(cs.psutil, "Process")
    @patch.object(cs.win32process, "GetWindowThreadProcessId", return_value=(0, 42))
    @patch.object(cs.win32gui, "GetWindowText", return_value="nv (1) [map] - ChickenAuto")
    @patch.object(cs.win32gui, "IsIconic", return_value=False)
    @patch.object(cs.win32gui, "IsWindow", return_value=True)
    @patch.object(cs.win32gui, "IsWindowVisible", return_value=False)
    def test_an_van_tim_thay(self, _vis, _win, _ico, _txt, _gtid, proc, _vc, _iter):
        proc.return_value.name.return_value = "Game.exe"

        def enum(cb, _):
            cb(100, None)
            return True

        with patch.object(cs.win32gui, "EnumWindows", side_effect=enum):
            ds = cs.tim_cua_so_game()
        self.assertEqual(len(ds), 1)
        self.assertEqual(ds[0]["hwnd"], 100)
        self.assertEqual(ds[0]["pid"], 42)

    @patch.object(cs, "vung_client", return_value=(0, 0, 800, 600))
    @patch.object(cs.psutil, "Process")
    @patch.object(cs.win32process, "GetWindowThreadProcessId", return_value=(0, 99))
    @patch.object(cs.win32gui, "GetWindowText", return_value="title")
    @patch.object(cs.win32gui, "IsIconic", return_value=False)
    @patch.object(cs.win32gui, "IsWindow", return_value=True)
    @patch.object(cs.win32gui, "IsWindowVisible", return_value=False)
    def test_bo_sung_theo_pid_khi_enum_bo_sot(self, _vis, _win, _ico, _txt, _gtid, proc, _vc):
        proc.return_value.name.return_value = "Game.exe"
        calls = {"n": 0}

        def enum(cb, _):
            calls["n"] += 1
            if calls["n"] == 1:
                return True
            cb(200, None)
            return True

        proc_iter = MagicMock()
        proc_iter.info = {"pid": 99, "name": "Game.exe"}

        with patch.object(cs.win32gui, "EnumWindows", side_effect=enum), \
                patch.object(cs.psutil, "process_iter", return_value=[proc_iter]):
            ds = cs.tim_cua_so_game()
        self.assertEqual([c["hwnd"] for c in ds], [200])
        self.assertEqual(ds[0]["pid"], 99)


if __name__ == "__main__":
    unittest.main()
