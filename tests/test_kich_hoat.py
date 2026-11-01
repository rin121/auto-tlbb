import base64
import json
import os
import tempfile
import unittest
import unittest.mock

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

import kich_hoat
from kich_hoat import PHIEN_BAN, _chuan_hoa_hwid, _noi_dung_ky, doc_hwid, xac_minh_chu_ky, xac_thuc_license


class TestKichHoat(unittest.TestCase):
    def test_doc_hwid_dinh_dang(self):
        hwid = doc_hwid()
        self.assertRegex(hwid, r"^[0-9A-F]{4}(-[0-9A-F]{4}){3}$")

    def test_chuan_hoa_hwid(self):
        self.assertEqual(_chuan_hoa_hwid("abcd-1234-5678-90ef"), "ABCD1234567890EF")

    def test_xac_minh_chu_ky_tam(self):
        khoa = Ed25519PrivateKey.generate()
        payload = {"v": PHIEN_BAN, "hwid": "AAAA-BBBB-CCCC-DDDD", "ghi_chu": "test"}
        chu_ky = khoa.sign(_noi_dung_ky(payload))
        ban = {"payload": payload, "chu_ky": base64.b64encode(chu_ky).decode("ascii")}
        with unittest.mock.patch.object(kich_hoat, "_khoa_cong", return_value=khoa.public_key()):
            hop, _ = xac_minh_chu_ky(ban)
        self.assertTrue(hop)

    def test_xac_thuc_hwid_may(self):
        khoa = Ed25519PrivateKey.generate()
        hwid = doc_hwid()
        payload = {"v": PHIEN_BAN, "hwid": hwid}
        chu_ky = khoa.sign(_noi_dung_ky(payload))
        ban = {"payload": payload, "chu_ky": base64.b64encode(chu_ky).decode("ascii")}
        with tempfile.NamedTemporaryFile("w", suffix=".dat", delete=False, encoding="utf-8") as f:
            json.dump(ban, f)
            duong = f.name
        try:
            with unittest.mock.patch.object(kich_hoat, "_khoa_cong", return_value=khoa.public_key()):
                with unittest.mock.patch.object(kich_hoat, "bat_buoc_kich_hoat", return_value=True):
                    hop, mo_ta = xac_thuc_license(duong)
            self.assertTrue(hop, mo_ta)
        finally:
            os.unlink(duong)

    @unittest.skipUnless(
        os.path.isfile(os.path.join(os.path.dirname(__file__), "..", "dong_goi", "kich_hoat", "license_private.pem")),
        "không có license_private.pem",
    )
    def test_pem_khop_khoa_cong_trong_repo(self):
        from cryptography.hazmat.primitives.serialization import load_pem_private_key

        from kich_hoat_khoa_cong import KHOA_CONG_B64

        pem = os.path.join(os.path.dirname(__file__), "..", "dong_goi", "kich_hoat", "license_private.pem")
        with open(pem, "rb") as f:
            priv = load_pem_private_key(f.read(), None)
        pub_pem = priv.public_key().public_bytes_raw()
        pub_emb = base64.b64decode(KHOA_CONG_B64)
        self.assertEqual(pub_pem, pub_emb)


if __name__ == "__main__":
    unittest.main()
