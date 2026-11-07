"""Bot quản lý: mã kết nối, lệnh khi 0/1/nhiều máy, im một lần, tắt, cắt tin."""
import json
import unittest

from bot_quan_ly.http_may import nhan_bao_cao
from bot_quan_ly.kho_may import KhoMay
from bot_quan_ly.lenh import cat_tin, tra_loi

SNAP = {
    "phien_ban": 1,
    "ten_may": "MayA",
    "luc": 1,
    "uptime_giay": 3660,
    "so_cua_so": 1,
    "tat": False,
    "cua_so": [{
        "ten": "NhanVat",
        "tai_khoan": "acc",
        "map": "Đại Lý",
        "hp": 10,
        "level": 5,
        "mon_phai": "Nga My",
        "trong_game": True,
        "mo_ta": "Đang auto",
        "loi": "đứt lua",
        "nhom": ["NhanVat", "Ban"],
        "mo_ta_nhom": "Trưởng nhóm (2 người)",
    }],
    "acc": [{
        "ten": "acc",
        "loai": "pho_ban",
        "nhan_vat": "NhanVat",
        "bat": True,
        "trang_thai": "Đang online (NhanVat)",
    }],
    "xoay_vong": "",
}


def _snap(ten, id_may=None):
    ban = json.loads(json.dumps(SNAP))
    ban["ten_may"] = ten
    ban["id_may"] = id_may if id_may is not None else ten
    return ban


class TestKhoVaLenh(unittest.TestCase):
    def test_sai_ma_khong_ghi(self):
        kho = KhoMay("", giay_im=90)
        body = json.dumps(SNAP).encode("utf-8")
        status, tin = nhan_bao_cao("sai", body, "dung", kho, bay_gio=1)
        self.assertEqual(status, 403)
        self.assertEqual(tin, [])
        self.assertEqual(kho.danh_sach(), [])
        status, tin = nhan_bao_cao("dung", b"x" * 200_001, "dung", kho, bay_gio=1)
        self.assertEqual(status, 413)
        status, tin = nhan_bao_cao("dung", body, "dung", kho, bay_gio=1)
        self.assertEqual(status, 204)
        self.assertEqual(tin, [])
        self.assertEqual(kho.tim("MayA")["ten"], "MayA")
        self.assertEqual(kho.tim("maya")["ten"], "MayA")

    def test_status_khong_mot_va_nhieu_may(self):
        trong = KhoMay("", giay_im=90)
        self.assertIn("Chưa có máy", tra_loi(trong, "status", "", bay_gio=0))

        mot = KhoMay("", giay_im=90)
        mot.nap(_snap("MayA"), bay_gio=0)
        chu = tra_loi(mot, "status", "", bay_gio=0)
        self.assertIn("NhanVat", chu)
        self.assertIn("Đang auto", chu)
        self.assertIn("đứt lua", chu)
        self.assertIn("NhanVat", tra_loi(mot, "nhom", ""))
        self.assertIn("phó bản", tra_loi(mot, "acc", ""))
        self.assertIn("đứt lua", tra_loi(mot, "loi", ""))
        self.assertIn("1 giờ 1 phút", tra_loi(mot, "ping", "", bay_gio=0))

        nhieu = KhoMay("", giay_im=90)
        nhieu.nap(_snap("MayA", "id-a"), bay_gio=0)
        nhieu.nap(_snap("MayB", "id-b"), bay_gio=0)
        self.assertIn("nhiều máy", tra_loi(nhieu, "status", "", bay_gio=0))
        self.assertIn("NhanVat", tra_loi(nhieu, "status", "maya", bay_gio=0))
        self.assertIn("MayA", tra_loi(nhieu, "status", "maya", bay_gio=0))

    def test_im_mot_lan_va_tat(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("MayA"), bay_gio=0)
        self.assertEqual(kho.quet_im(90), [])
        self.assertEqual(kho.quet_im(90.1), ["Máy MayA im."])
        self.assertEqual(kho.quet_im(200), [])
        self.assertEqual(kho.nap({**_snap("MayA"), "tat": True}, bay_gio=5), ["Máy MayA đã tắt."])
        self.assertEqual(kho.nap({**_snap("MayA"), "tat": True}, bay_gio=6), [])
        self.assertEqual(kho.quet_im(500), [])
        self.assertEqual(kho.nap(_snap("MayA"), bay_gio=7), ["Máy MayA đã báo cáo lại."])

    def test_doi_ten_hien_thi_giu_mot_may(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("DESKTOP-PC", "stable-1"), bay_gio=0)
        kho.nap(_snap("Máy Của Rin", "stable-1"), bay_gio=1)
        self.assertEqual(len(kho.danh_sach()), 1)
        self.assertEqual(kho.danh_sach()[0]["ten"], "Máy Của Rin")

    def test_doi_ten_xoa_ban_cu(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("TenCu", "id-a"), bay_gio=0)
        kho.nap(_snap("TenMoi", "id-b"), bay_gio=1)
        self.assertEqual(len(kho.danh_sach()), 2)
        ban = json.loads(json.dumps(_snap("TenMoi", "id-b")))
        ban["ten_may_cu"] = "TenCu"
        kho.nap(ban, bay_gio=2)
        self.assertEqual(len(kho.danh_sach()), 1)
        self.assertEqual(kho.danh_sach()[0]["ten"], "TenMoi")

    def test_cat_tin_dai(self):
        chu = "x" * 9000
        doan = cat_tin(chu)
        self.assertGreater(len(doan), 1)
        self.assertTrue(all(len(d) <= 4000 for d in doan))
        self.assertEqual("".join(doan), chu)
