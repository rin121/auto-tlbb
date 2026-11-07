"""Snapshot từng máy AutoHoc và chuyển online / im / tắt."""
import json
import os
import threading
import time

TRANG_ONLINE = "online"
TRANG_IM = "im"
TRANG_TAT = "tat"


def tin_im(ten):
    return f"Máy {ten} im."


def tin_tat(ten):
    return f"Máy {ten} đã tắt."


def tin_lai(ten):
    return f"Máy {ten} đã báo cáo lại."


def _id_may_tu_snapshot(snapshot):
    chu = str(snapshot.get("id_may") or snapshot.get("ten_may") or "").strip()
    return chu.casefold(), chu


class KhoMay:
    def __init__(self, duong_dan, giay_im=90):
        self.duong_dan = duong_dan
        self.giay_im = giay_im
        self._khoa = threading.Lock()
        self._may = {}
        self._tai()

    def _xoa_ten(self, ten):
        khoa = (ten or "").strip().casefold()
        if not khoa:
            return
        self._may.pop(khoa, None)
        for kk in list(self._may):
            if (self._may[kk].get("ten") or "").casefold() == khoa:
                self._may.pop(kk, None)

    def _xoa_trung_id(self, id_khoa, giu_khoa):
        for kk in list(self._may):
            if kk == giu_khoa:
                continue
            rec = self._may[kk]
            rid = (rec.get("id") or rec.get("ten") or "").casefold()
            snap_id = str((rec.get("snapshot") or {}).get("id_may") or "").casefold()
            if rid == id_khoa or snap_id == id_khoa:
                self._may.pop(kk, None)

    def _don_trung_ten(self, id_khoa, ten_hien):
        """Một tên hiển thị — một máy trên /ds (bỏ id cũ / clone trùng tên)."""
        ten_cf = (ten_hien or "").casefold()
        if not ten_cf:
            return
        for kk in list(self._may):
            if kk == id_khoa:
                continue
            if (self._may[kk].get("ten") or "").casefold() == ten_cf:
                self._may.pop(kk, None)

    def nap(self, snapshot, bay_gio=None):
        """Ghi snapshot. Trả về các câu cần nhắn (tắt hoặc báo cáo lại)."""
        bay_gio = time.time() if bay_gio is None else bay_gio
        ten = str(snapshot.get("ten_may") or "").strip()
        id_khoa, id_chu = _id_may_tu_snapshot(snapshot)
        if not id_khoa:
            return []
        tat = bool(snapshot.get("tat"))
        ten_cu = str(snapshot.get("ten_may_cu") or "").strip()
        with self._khoa:
            if ten_cu:
                self._xoa_ten(ten_cu)
            cu = self._may.get(id_khoa)
            trang_cu = cu["trang_thai"] if cu else None
            if tat:
                trang = TRANG_TAT
                ten_tin = ten or (cu["ten"] if cu else "")
                tin = [tin_tat(ten_tin)] if trang_cu != TRANG_TAT and ten_tin else []
            else:
                trang = TRANG_ONLINE
                tin = [tin_lai(ten)] if trang_cu in (TRANG_IM, TRANG_TAT) else []
            if not tat:
                self._xoa_trung_id(id_khoa, id_khoa)
                self._don_trung_ten(id_khoa, ten)
            self._may[id_khoa] = {
                "id": id_chu,
                "ten": ten or (cu["ten"] if cu else id_chu),
                "snapshot": snapshot,
                "luc_thay": bay_gio,
                "trang_thai": trang,
            }
            self._luu()
        return tin

    def quet_im(self, bay_gio=None):
        """Máy online quá giay_im không gửi thêm thì chuyển im, mỗi lần một câu."""
        bay_gio = time.time() if bay_gio is None else bay_gio
        tin = []
        with self._khoa:
            doi = False
            for rec in self._may.values():
                if rec["trang_thai"] != TRANG_ONLINE:
                    continue
                if bay_gio - rec["luc_thay"] <= self.giay_im:
                    continue
                rec["trang_thai"] = TRANG_IM
                tin.append(tin_im(rec["ten"]))
                doi = True
            if doi:
                self._luu()
        return tin

    def danh_sach(self):
        with self._khoa:
            ban = [self._sao(rec) for rec in self._may.values()]
        ban.sort(key=lambda rec: rec["ten"].casefold())
        return ban

    def _uu_tien_trang(self, trang):
        return {TRANG_ONLINE: 3, TRANG_IM: 2, TRANG_TAT: 1}.get(trang, 0)

    def _chon_tot_nhat_theo_ten(self, danh_sach_may, bay_gio=None):
        if not danh_sach_may:
            return None
        bay_gio = time.time() if bay_gio is None else bay_gio
        tot = danh_sach_may[0]
        tot_t = self.trang_thai_luc(tot, bay_gio)
        for may in danh_sach_may[1:]:
            trang = self.trang_thai_luc(may, bay_gio)
            if self._uu_tien_trang(trang) > self._uu_tien_trang(tot_t):
                tot, tot_t = may, trang
            elif trang == tot_t and may["luc_thay"] > tot["luc_thay"]:
                tot = may
        return tot

    def danh_sach_gom_ten(self, bay_gio=None):
        """Một bản ghi / tên hiển thị (ưu tiên online, rồi lần cuối mới nhất)."""
        bay_gio = time.time() if bay_gio is None else bay_gio
        gom = {}
        with self._khoa:
            for rec in self._may.values():
                may = self._sao(rec)
                ten_cf = may["ten"].casefold()
                trang = self.trang_thai_luc(may, bay_gio)
                cu = gom.get(ten_cf)
                if not cu:
                    gom[ten_cf] = may
                    continue
                cu_trang = self.trang_thai_luc(cu, bay_gio)
                if self._uu_tien_trang(trang) > self._uu_tien_trang(cu_trang):
                    gom[ten_cf] = may
                elif trang == cu_trang and may["luc_thay"] > cu["luc_thay"]:
                    gom[ten_cf] = may
        ban = list(gom.values())
        ban.sort(key=lambda rec: rec["ten"].casefold())
        return ban

    def tim(self, ten, bay_gio=None):
        khoa = (ten or "").strip().casefold()
        if not khoa:
            return None
        with self._khoa:
            rec = self._may.get(khoa)
            if rec:
                return self._sao(rec)
            trung = [self._sao(rec) for rec in self._may.values() if rec["ten"].casefold() == khoa]
        if not trung:
            return None
        if len(trung) == 1:
            return trung[0]
        return self._chon_tot_nhat_theo_ten(trung, bay_gio)

    def trang_thai_luc(self, rec, bay_gio=None):
        """online / im / tat tại thời điểm bay_gio, kể cả khi chưa kịp quét."""
        bay_gio = time.time() if bay_gio is None else bay_gio
        trang = rec["trang_thai"]
        if trang == TRANG_ONLINE and bay_gio - rec["luc_thay"] > self.giay_im:
            return TRANG_IM
        return trang

    def _sao(self, rec):
        return {
            "ten": rec["ten"],
            "id": rec.get("id") or rec["ten"],
            "snapshot": json.loads(json.dumps(rec["snapshot"])),
            "luc_thay": rec["luc_thay"],
            "trang_thai": rec["trang_thai"],
        }

    def _gom_theo_id(self):
        """File cũ lưu theo tên hiển thị — gộp thành một bản / id_may."""
        gom = {}
        for rec in self._may.values():
            snap = rec.get("snapshot") or {}
            id_khoa, id_chu = _id_may_tu_snapshot(snap)
            if not id_khoa:
                id_khoa, id_chu = rec["ten"].casefold(), rec["ten"]
            cu = gom.get(id_khoa)
            if not cu or rec["luc_thay"] >= cu["luc_thay"]:
                gom[id_khoa] = {**rec, "id": rec.get("id") or id_chu}
        self._may = gom

    def _tai(self):
        if not self.duong_dan or not os.path.isfile(self.duong_dan):
            return
        try:
            with open(self.duong_dan, encoding="utf-8") as f:
                du_lieu = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        for rec in du_lieu.get("may") or []:
            ten = str(rec.get("ten") or "").strip()
            snap = rec.get("snapshot")
            if not ten or not isinstance(snap, dict):
                continue
            trang = rec.get("trang_thai")
            if trang not in (TRANG_ONLINE, TRANG_IM, TRANG_TAT):
                trang = TRANG_IM
            id_khoa, id_chu = _id_may_tu_snapshot(snap)
            if not id_khoa:
                id_khoa = ten.casefold()
                id_chu = ten
            self._may[id_khoa] = {
                "id": str(rec.get("id") or id_chu).strip() or id_chu,
                "ten": ten,
                "snapshot": snap,
                "luc_thay": float(rec.get("luc_thay") or 0),
                "trang_thai": trang,
            }
        self._gom_theo_id()

    def _luu(self):
        if not self.duong_dan:
            return
        thu_muc = os.path.dirname(self.duong_dan)
        if thu_muc:
            os.makedirs(thu_muc, exist_ok=True)
        chu = json.dumps(
            {"may": list(self._may.values())},
            ensure_ascii=False,
        )
        tam = f"{self.duong_dan}.tmp.{os.getpid()}.{threading.get_ident()}"
        with open(tam, "w", encoding="utf-8") as f:
            f.write(chu)
        os.replace(tam, self.duong_dan)
