"""Snapshot báo cáo Telegram: không mật khẩu, đủ nhóm / acc / lỗi."""
import json
import tempfile
import unittest
from pathlib import Path

import bao_cao_telegram as bc


class TestSnapshot(unittest.TestCase):
    def test_nhom_acc_online_cho_va_loi(self):
        dang_chay = bc.cua_so_bao_cao(
            ten="Kiem", tai_khoan="acc1", map="Đại Lý", hp=100, level=50,
            mon_phai="Thiếu Lâm", trong_game=True,
            mo_ta=bc.mo_ta_auto(False, True, "Phó bản: đi", "", "", True),
            loi="", nhom=["Kiem", "Dong"], mo_ta_nhom="Trưởng nhóm (2 người)",
        )
        cua_loi = bc.cua_so_bao_cao(
            ten="Hong", tai_khoan="acc2", map="", hp=None, level=None,
            mon_phai="", trong_game=False,
            mo_ta=bc.mo_ta_auto(True, False, "Đang kết nối...", "", "", False),
            loi="Lua đứt", nhom=[], mo_ta_nhom="",
        )
        online = bc.acc_bao_cao(
            "acc1", "pho_ban", "Kiem", True,
            bc.trang_thai_acc(True, "Kiem", False, "", False, "", True),
        )
        cho = bc.acc_bao_cao(
            "acc3", "train", "", True,
            bc.trang_thai_acc(False, "", False, "", False, "", True),
        )
        snap = bc.hop_snapshot("PhongKhach", 125, [dang_chay, cua_loi], [online, cho], xoay_vong="vòng 1")
        chu = json.dumps(snap, ensure_ascii=False)
        self.assertNotIn("mat_khau", chu)
        self.assertNotIn("ma_kiem_tra", chu)
        self.assertEqual(snap["phien_ban"], 1)
        self.assertEqual(snap["so_cua_so"], 2)
        self.assertEqual(snap["ten_may"], "PhongKhach")
        self.assertFalse(snap["tat"])
        self.assertEqual(dang_chay["nhom"], ["Kiem", "Dong"])
        self.assertEqual(dang_chay["mo_ta_nhom"], "Trưởng nhóm (2 người)")
        self.assertIn("Phó bản", dang_chay["mo_ta"])
        self.assertEqual(cua_loi["mo_ta"], "Chưa đọc được game")
        self.assertEqual(cua_loi["loi"], "Lua đứt")
        self.assertEqual(online["trang_thai"], "Đang online (Kiem)")
        self.assertEqual(cho["trang_thai"], "Chờ mở game")
        self.assertEqual(snap["xoay_vong"], "vòng 1")

    def test_mo_ta_chua_vao_game_va_tam_dung(self):
        self.assertEqual(bc.mo_ta_auto(False, False, "", "", "", False), "Đang kết nối...")
        self.assertEqual(
            bc.trang_thai_acc(False, "", False, "", True, "", True),
            "Tạm dừng",
        )
        self.assertEqual(
            bc.trang_thai_acc(False, "", True, "Đang đăng nhập", False, "", True),
            "Đang đăng nhập",
        )
        self.assertEqual(
            bc.trang_thai_acc(False, "", False, "", False, "", False),
            "Không tự mở lại khi diss",
        )

    def test_kiem_tra_dia_chi(self):
        with self.assertRaises(ValueError):
            bc.kiem_tra({"bat": True, "ten_may": "A", "dia_chi": "https://x.example/bao-cao", "ma_ket_noi": "s"})
        cau = bc.kiem_tra({
            "bat": True, "ten_may": "Phong khach",
            "dia_chi": "https://abc.trycloudflare.com/", "ma_ket_noi": "bi-mat",
        })
        self.assertEqual(cau["dia_chi"], "https://abc.trycloudflare.com")
        self.assertTrue(cau["bat"])

    def test_chuan_hoa_ip_va_cong(self):
        self.assertEqual(bc.chuan_hoa_dia_chi("113.22.183.60"), "http://113.22.183.60:8787")
        self.assertEqual(bc.chuan_hoa_dia_chi("http://113.22.183.60:9000"), "http://113.22.183.60:9000")
        self.assertEqual(bc.chuan_hoa_dia_chi("https://x.trycloudflare.com"), "https://x.trycloudflare.com")

    def test_hub_dang_nghe_local(self):
        ket = bc.hub_dang_nghe("127.0.0.1")
        self.assertIn(ket, (True, False))
        self.assertIsNone(bc.hub_dang_nghe("https://example.com"))

    def test_dam_bao_id_may_ngau_nhien(self):
        a = bc.dam_bao_id_may({"id_may": ""})
        b = bc.dam_bao_id_may({"id_may": ""})
        self.assertNotEqual(a["id_may"], b["id_may"])
        self.assertEqual(len(a["id_may"]), 16)

    def test_lam_moi_id_may(self):
        with tempfile.TemporaryDirectory() as td:
            duong = Path(td) / "ket_noi_telegram.json"
            duong.write_text(
                json.dumps({"bat": True, "ten_may": "VM", "dia_chi": "http://x", "ma_ket_noi": "m", "id_may": "cu"}),
                encoding="utf-8",
            )
            cu = bc.doc(duong)
            moi = bc.lam_moi_id_may(duong)
            self.assertNotEqual(moi, "cu")
            self.assertEqual(bc.doc(duong)["id_may"], moi)
