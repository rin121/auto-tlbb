import unittest
from unittest.mock import patch

import proxy_broker_ui


class TestProxyBrokerUi(unittest.TestCase):
    def test_mo_ta_hien_thi_xanh_khi_co_proxy_khong_daemon(self):
        st = {
            "health": "healthy",
            "proxy_active": {"host": "1.2.3.4", "port": 1080, "latency_ms": 120},
            "acc_online": 0,
            "cho_phep_login_them": True,
        }
        with patch.object(proxy_broker_ui, "broker_dang_chay", return_value=(False, None)):
            with patch.object(proxy_broker_ui, "doc_state", return_value=st):
                chuoi, mau, chay = proxy_broker_ui.mo_ta_hien_thi()
        self.assertFalse(chay)
        self.assertEqual(mau, "#0a7a0a")
        self.assertIn("1.2.3.4", chuoi)

    def test_phan_tich_log_gan_moi_khong_lay_dong_thu(self):
        log = (
            "--- Tìm gán proxy mới ---\n"
            "Thử [12/199] socks5 IP 1.2.3.4:1080...\n"
            "  → bỏ (TCP: timed out)\n"
            "Không tìm được proxy khả dụng.\n"
        )
        ok, msg = proxy_broker_ui._phan_tich_log_gan_moi(log)
        self.assertFalse(ok)
        self.assertIn("Không tìm", msg)
        self.assertNotIn("Thử [12", msg)

    def test_phan_tich_log_gan_moi_thanh_cong(self):
        log = "Thử [1/5] ...\n  → OK — IP 9.9.9.9 · ~100ms\nĐã gắn proxy 9.9.9.9:1080 — IP 9.9.9.9 · ~100ms\n"
        ok, msg = proxy_broker_ui._phan_tich_log_gan_moi(log)
        self.assertTrue(ok)
        self.assertIn("9.9.9.9", msg)


if __name__ == "__main__":
    unittest.main()
