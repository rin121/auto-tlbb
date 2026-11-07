"""Bot quản lý: mã kết nối, lệnh khi 0/1/nhiều máy, im một lần, tắt, cắt tin."""
import json
import unittest

from bot_quan_ly.http_may import nhan_bao_cao
from bot_quan_ly.kho_may import KhoMay
from bot_quan_ly.lenh import cat_tin, tin_ds, tin_help, tra_loi
from bot_quan_ly.menu import (
    _nhan_may,
    keyboard_danh_sach,
    keyboard_may,
    may_tu_slug,
    slug_tu_may,
    xuly_callback,
)

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

    def test_hai_id_hien_thi_hai_may(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("May Ao Bac Mori 1", "id-mori-1"), bay_gio=0)
        kho.nap(_snap("May Ao Anh Zero 1", "id-zero-1"), bay_gio=1)
        self.assertEqual(len(kho.danh_sach()), 2)

    def test_online_xoa_ban_tat_trung_ten(self):
        kho = KhoMay("", giay_im=90)
        snap_tat = {**_snap("Máy Của Rin", "legacy-key"), "tat": True}
        kho.nap(snap_tat, bay_gio=0)
        kho.nap(_snap("Máy Của Rin", "stable-rin"), bay_gio=1)
        self.assertEqual(len(kho.danh_sach()), 1)
        self.assertEqual(kho.danh_sach()[0]["trang_thai"], "online")

    def test_gop_trung_id_giu_mot(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("VM Ten 1", "cung-id"), bay_gio=0)
        kho.nap(_snap("VM Ten 2", "cung-id"), bay_gio=1)
        self.assertEqual(len(kho.danh_sach()), 1)
        self.assertEqual(kho.danh_sach()[0]["ten"], "VM Ten 2")

    def test_ds_gom_ten_va_online_offline(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("May Ao Azumi", "id-1"), bay_gio=0)
        kho.nap(_snap("May Ao Azumi", "id-2"), bay_gio=50)
        self.assertEqual(len(kho.danh_sach_gom_ten(bay_gio=50)), 1)
        chu = tin_ds(kho, bay_gio=200)
        self.assertIn("Máy (1)", chu)
        self.assertIn("May Ao Azumi: offline", chu)
        self.assertNotIn("cửa sổ", chu)
        kho.nap(_snap("May Ao Azumi", "id-2"), bay_gio=201)
        chu2 = tin_ds(kho, bay_gio=201)
        self.assertIn("May Ao Azumi: online", chu2)

    def test_nap_online_xoa_trung_ten(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("May Ao Bac Mori 1", "id-a"), bay_gio=0)
        kho.nap(_snap("May Ao Bac Mori 1", "id-b"), bay_gio=1)
        self.assertEqual(len(kho.danh_sach()), 1)

    def test_cat_tin_dai(self):
        chu = "x" * 9000
        doan = cat_tin(chu)
        self.assertGreater(len(doan), 1)
        self.assertTrue(all(len(d) <= 4000 for d in doan))
        self.assertEqual("".join(doan), chu)


class TestMenuInline(unittest.TestCase):
    def test_slug_on_dinh_theo_id_may(self):
        a = _snap("Ten", "id-x")
        b = _snap("Khac", "id-x")
        c = _snap("Ten", "id-y")
        self.assertEqual(slug_tu_may(a), slug_tu_may(b))
        self.assertNotEqual(slug_tu_may(a), slug_tu_may(c))

    def test_nhan_may_co_so_nguoi(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("May Ao Anh Zero 1", "id-1"), bay_gio=100)
        may = kho.danh_sach_gom_ten(bay_gio=100)[0]
        self.assertEqual(_nhan_may(kho, may, bay_gio=100), "May Ao Anh Zero 1 - online - 1 người")

    def test_keyboard_danh_sach_du_may(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("May A", "ida"), bay_gio=0)
        kho.nap(_snap("May B", "idb"), bay_gio=1)
        ban = keyboard_danh_sach(kho, bay_gio=1)
        self.assertIn("Chọn máy (2)", ban["text"])
        hang = ban["reply_markup"]["inline_keyboard"]
        nut = [b for h in hang for b in h]
        ma = [b["callback_data"] for b in nut if b["callback_data"].startswith("m:")]
        self.assertEqual(len(ma), 2)
        for b in nut:
            self.assertLessEqual(len(b["callback_data"]), 64)

    def test_callback_status_gui_noi_dung(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("MayA", "id-a"), bay_gio=100)
        may = kho.danh_sach_gom_ten(bay_gio=100)[0]
        slug = slug_tu_may(may)
        ket = xuly_callback(kho, f"x:{slug}:status", bay_gio=100)
        self.assertEqual(ket["loai"], "send")
        self.assertIn("NhanVat", ket["noi_dung_gui"])
        self.assertIn("inline_keyboard", ket["reply_markup"])
        self.assertIn("status", str(ket["reply_markup"]))

    def test_callback_may_khong_thay(self):
        kho = KhoMay("", giay_im=90)
        ket = xuly_callback(kho, "x:deadbeef:ping", bay_gio=0)
        self.assertEqual(ket["loai"], "send")
        self.assertIn("Không thấy máy", ket["noi_dung_gui"])

    def test_may_tu_slug(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("Rin", "stable-rin"), bay_gio=0)
        slug = slug_tu_may(kho.danh_sach_gom_ten(bay_gio=0)[0])
        self.assertIsNotNone(may_tu_slug(kho, slug, bay_gio=0))

    def test_submenu_co_du_nut(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("MayA", "id-a"), bay_gio=0)
        may = kho.danh_sach_gom_ten(bay_gio=0)[0]
        ban = keyboard_may(kho, may, bay_gio=0)
        self.assertIn("MayA", ban["text"])
        hang = ban["reply_markup"]["inline_keyboard"]
        chu = str(hang)
        self.assertIn("status", chu)
        self.assertIn("Quay lại", chu)

    def test_help_co_menu(self):
        self.assertIn("/menu", tin_help())
