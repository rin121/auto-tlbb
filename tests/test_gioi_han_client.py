import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import gioi_han_client as gh  # noqa: E402


class TestDongHopRuntime(unittest.TestCase):
    def test_bam_ok_hop_visual_cpp(self):
        da_bam = []

        def enum(cb, _):
            cb(7, None)

        def text(hwnd):
            return "Microsoft Visual C++ Runtime Library"

        with patch.object(gh.win32gui, "EnumWindows", side_effect=enum), \
                patch.object(gh.win32gui, "IsWindowVisible", return_value=True), \
                patch.object(gh.win32gui, "GetClassName", return_value="#32770"), \
                patch.object(gh.win32gui, "GetWindowText", side_effect=text), \
                patch.object(gh.win32gui, "GetDlgItem", return_value=99), \
                patch.object(gh.win32gui, "PostMessage", side_effect=lambda *a: da_bam.append(a)):
            self.assertEqual(gh.dong_hop_runtime_error(), ["Microsoft Visual C++ Runtime Library"])
        self.assertTrue(any(a[0] == 99 and a[1] == gh.BM_CLICK for a in da_bam))

    def test_bo_qua_hop_khac(self):
        def enum(cb, _):
            cb(3, None)

        with patch.object(gh.win32gui, "EnumWindows", side_effect=enum), \
                patch.object(gh.win32gui, "IsWindowVisible", return_value=True), \
                patch.object(gh.win32gui, "GetClassName", return_value="#32770"), \
                patch.object(gh.win32gui, "GetWindowText", return_value="Thien Long Bat Bo"), \
                patch.object(gh, "_chu_con", return_value=[]), \
                patch.object(gh.win32gui, "PostMessage") as bam:
            self.assertEqual(gh.dong_hop_runtime_error(), [])
        bam.assert_not_called()


if __name__ == "__main__":
    unittest.main()
