"""Bot quản lý: mã kết nối, lệnh khi 0/1/nhiều máy, im một lần, tắt, cắt tin."""
import json
import logging
import os
import re
import tempfile
import unittest

from bot_quan_ly.http_may import nhan_bao_cao
from bot_quan_ly.kho_may import KhoMay
from bot_quan_ly.lenh import cat_tin, tin_ds, tin_help, tra_loi
from bot_quan_ly.menu import (
    _nhan_may,
    hoat_dong_nhan_vat,
    keyboard_danh_sach,
    keyboard_may,
    khoi_may,
    may_tu_slug,
    slug_tu_may,
    vong_tu_snapshot,
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


class TestCatFileLog(unittest.TestCase):
    def test_cat_luc_nua_dem_giu_7_ngay(self):
        from bot_quan_ly.__main__ import tao_file_log

        with tempfile.TemporaryDirectory() as td:
            duong = os.path.join(td, "bot_quan_ly.log")
            h = tao_file_log(duong)
            try:
                self.assertEqual(h.when, "MIDNIGHT")
                self.assertEqual(h.backupCount, 7)
                h.emit(logging.makeLogRecord({"msg": "hom qua"}))
                h.doRollover()
                h.emit(logging.makeLogRecord({"msg": "hom nay"}))
            finally:
                h.close()
            cu = [f for f in os.listdir(td) if re.fullmatch(r"bot_quan_ly\.log\.\d{4}-\d{2}-\d{2}", f)]
            self.assertEqual(len(cu), 1)
            with open(os.path.join(td, cu[0]), encoding="utf-8") as f:
                self.assertIn("hom qua", f.read())
            with open(duong, encoding="utf-8") as f:
                chu = f.read()
            self.assertIn("hom nay", chu)
            self.assertNotIn("hom qua", chu)


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
        self.assertIn("Danh sách máy", ban["text"])
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

    def test_vong_tu_xoay_vong(self):
        self.assertEqual(
            vong_tu_snapshot({"xoay_vong": "Nhóm 1 round 2: đang đi phó bản (trưởng nhóm cosato1)"}),
            "Vòng 2",
        )
        self.assertEqual(vong_tu_snapshot({"xoay_vong": "vòng 1"}), "Vòng 1")
        self.assertEqual(vong_tu_snapshot({"xoay_vong": ""}), "")

    def test_hoat_dong_rut_gon(self):
        self.assertEqual(
            hoat_dong_nhan_vat({"mo_ta": "Phó bản PMP: Sát Tinh: đánh giữa lôi đài | Đánh Hoa Dung"}),
            "Phó bản Sát Tinh: đánh giữa lôi đài",
        )
        self.assertEqual(
            hoat_dong_nhan_vat({"mo_ta": "Phó bản PMP: theo đội trưởng cosato1 | Không có quái trong vùng"}),
            "Phó bản PMP: theo đội trưởng cosato1",
        )
        self.assertEqual(hoat_dong_nhan_vat({"mo_ta": ""}), "chưa có hoạt động")

    def _kho_rin(self, bay_gio):
        kho = KhoMay("", giay_im=90)
        snap = _snap("Máy Của Rin", "id-rin")
        snap["xoay_vong"] = "Nhóm 1 round 1: đang đi phó bản (trưởng nhóm cosato1)"
        snap["cua_so"] = [
            {"ten": "cosato1", "mo_ta": "Phó bản PMP: Sát Tinh: đánh giữa lôi đài | Đánh Hoa Dung"},
            {"ten": "cosato2", "mo_ta": "Phó bản PMP: theo đội trưởng cosato1"},
        ]
        snap["so_cua_so"] = 2
        kho.nap(snap, bay_gio=bay_gio)
        return kho

    def _cac_nut(self, ban):
        return [(b["text"], b["callback_data"]) for h in ban["reply_markup"]["inline_keyboard"] for b in h]

    def test_menu_khoi_chu_tung_may_va_nut_hai_cot(self):
        kho = self._kho_rin(bay_gio=100)
        snap = json.loads(json.dumps(kho.danh_sach_gom_ten(bay_gio=100)[0]["snapshot"]))
        snap["cua_so"][0]["luot_hom_nay"] = {"pmp": 0, "sat_tinh": 13, "ac_tac": 0}
        kho.nap(snap, bay_gio=100)
        ban = keyboard_danh_sach(kho, bay_gio=100)
        self.assertEqual(ban["parse_mode"], "HTML")
        self.assertIn("<b>Máy Của Rin</b>", ban["text"])
        self.assertIn("🟢 Online · Vòng 1 · 2 người", ban["text"])
        self.assertIn("cosato1 — Sát Tinh: đánh giữa lôi đài", ban["text"])
        self.assertIn("Hôm nay: Sát Tinh 13 vòng, PMP 0 vòng, Ác Tặc 0 lần", ban["text"])
        nut = self._cac_nut(ban)
        self.assertEqual(len(nut), 2)
        self.assertTrue(nut[0][0].endswith("Máy Của Rin"))
        self.assertTrue(nut[0][1].startswith("m:"))
        self.assertEqual(nut[-1], ("🔄 Làm mới", "ds"))
        may = kho.danh_sach_gom_ten(bay_gio=100)[0]
        self.assertIn("cosato1", keyboard_may(kho, may, bay_gio=100)["text"])

    def test_bam_nut_thong_tin_khong_lam_gi(self):
        kho = self._kho_rin(bay_gio=100)
        self.assertEqual(xuly_callback(kho, "_", bay_gio=100), {"loai": "bo_qua"})

    def test_may_offline_chi_hien_lan_cuoi(self):
        kho = self._kho_rin(bay_gio=0)
        ban = keyboard_danh_sach(kho, bay_gio=500)
        self.assertIn("⚪ Offline · 2 người · lần cuối", ban["text"])
        self.assertNotIn("cosato1", ban["text"])

    def test_ten_may_co_ky_tu_html(self):
        kho = KhoMay("", giay_im=90)
        kho.nap(_snap("May <A&B>", "id-html"), bay_gio=100)
        self.assertIn("<b>May &lt;A&amp;B&gt;</b>", keyboard_danh_sach(kho, bay_gio=100)["text"])

    def test_menu_hien_so_luot_cua_doi_truong(self):
        kho = self._kho_rin(bay_gio=100)
        may = kho.danh_sach_gom_ten(bay_gio=100)[0]
        snap = json.loads(json.dumps(may["snapshot"]))
        snap["cua_so"][0]["luot_hom_nay"] = {"pmp": 0, "sat_tinh": 8, "ac_tac": 1}
        snap["cua_so"][1]["luot_hom_nay"] = {"pmp": 0, "sat_tinh": 0, "ac_tac": 0}
        kho.nap(snap, bay_gio=100)
        dong = khoi_may(kho, kho.danh_sach_gom_ten(bay_gio=100)[0], bay_gio=100)
        self.assertIn("   Hôm nay: Sát Tinh 8 vòng, PMP 0 vòng, Ác Tặc 1 lần", dong)
        self.assertEqual(sum("Hôm nay:" in d for d in dong), 1)

    def test_offline_khong_hien_nhan_vat_cu(self):
        kho = self._kho_rin(bay_gio=0)
        may = kho.danh_sach_gom_ten(bay_gio=500)[0]
        dong = khoi_may(kho, may, bay_gio=500)
        self.assertEqual(len(dong), 1)
        self.assertIn("offline - lần cuối", dong[0])
