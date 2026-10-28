"""
GIAO DỊCH CHO ACC CHÍNH: lần lượt đăng nhập acc phó bản (mặc định: trưởng nhóm; tùy chọn: mọi acc trong nhóm xoay vòng,
từng nhân vật round 1..3), kiểm tra túi Đạo cụ + Nguyên liệu; có đồ thì giao cho acc chính (trừ loại trừ, đồ khóa),
chế độ «tất cả acc» thì không có đồ sẽ thoát game và sang acc tiếp. Acc chính đứng ở NPC Tân Thủ (Đại Lý).
Cả hai chế độ đều xem sổ túi đồ (so_tui_do.py, xoay vòng ghi cuối mỗi round): sổ ghi 0 ô thì bỏ qua, sổ ghi còn đồ /
chưa rõ thì đăng nhập giao dù không phải trưởng nhóm; giao xong đánh dấu đã giao cho acc chính trong sổ.
Bấm Bắt đầu: mọi client đang trong game (trừ acc chính đã đúng nhân vật) về chọn máy chủ, giữ client; acc chính rồi
lần lượt các acc giao dịch đăng nhập trên chính các client đó, không mở game mới (trừ khi không còn client nào).

Túi acc chính còn dưới SO_O_TOI_THIEU ô trống thì cất đồ đã nhận:
    Thiên Cơ Cẩm Nang (cửa sổ Packet_Temporary, mở bằng MainMenuBar_KuaiJieYiZhan()):
        Packet_Temporary_PutInItem(ô túi Đạo cụ); món không nhận (Phiếu KNB...) thì nằm lại trong túi.
    Thương khố (NPC Tân Thủ, dòng (111111, 9993)): chuột phải ô túi khi cửa sổ Bank đang mở là cất vào kho.
        Số ô kho = Bank:GetRentBoxInfo(r) (ô đầu, số ô) của các ngăn r = 1..Bank:GetRentBoxNum().
Cả hai đều đầy thì dừng, giữ tiến trình. Tiến trình (trưởng nhóm đã giao xong trong ngày, mã đồ đã nhận) lưu ở
cau_hinh chung "giao_acc_chinh", bấm Bắt đầu lại thì đi tiếp từ trưởng nhóm chưa xong.
"""
import copy
import math
import os
import threading
import time
import traceback
from datetime import date

import cau_hinh
from auto_chuyen_sinh import chuan_hoa
from bang_ma_viscii import ma_hoa
from chien_dau import KY_NANG_VE_THANH, ma_dung_ky_nang_theo_dinh_nghia
from cua_so_game import tim_cua_so_game
from dang_nhap import (LoiDangNhap, bo_dau, man_hinh_hien_tai, tai_khoan_cua_pid, thoat_ve_chon_may_chu, trong_cua_so,
                       ve_chon_may_chu)
from game_api import Game
from giao_dich import GiaoDich, LoiGiaoDich, doc_tui
from lua_game import LoiLua
from nhan_vat_moi import NPC_TAN_THU, NhanDoTanThu, da_xong
from pho_ban_pmp import LoiPhoBan, _Dung as DungPhoBan, cai_dat_pmp, chuan_bi_ve_thanh, hom_nay, la_dai_ly
import so_tui_do
from so_tui_do import LOAI_TRU_MAC_DINH, bi_loai_tru, cac_tu_loai_tru
from xoay_vong import (SO_ROUND_TOI_DA, LuongVaoNhanVat, cac_tai_khoan_dang_tich, chia_nhom, khoa_sap_xep_tai_khoan,
                       ten_round, ten_trong_tieu_de, tim_game_cua_tai_khoan, tim_hwnd_cua_tai_khoan)

KHOA_CAI_DAT = "giao_acc_chinh"
MAC_DINH = {"tai_khoan": "", "mat_khau": "", "nhan_vat": "", "loai_tru": LOAI_TRU_MAC_DINH, "chi_hom_nay": True,
            "tat_ca_pho_ban": False, "tien_trinh": {}}
DONG_THUONG_KHO = (111111, 9993)
SO_O_TOI_THIEU = 5
SO_O_MOT_LAN = 5
SO_LAN_THU_GIAO_DICH = 3
KHOANG_CACH_DUNG_CHO = 3
GIAY_CHAY_TOI = 90
GIAY_CHO_VE_DAI_LY = 90
GIAY_GIUA_HAI_LAN_VE_THANH = 15
GIAY_CHO_CUA_SO = 6
GIAY_CHO_CAT = 2.5
# Lệnh cất gửi liền sau lệnh trước (dưới ~1 giây) thì game bỏ qua.
GIAY_GIUA_HAI_LAN_CAT = 1.5
SO_LAN_THU_CAT = 2

MA_KICH_THUOC_TUI = 'return DataPool:GetBaseBag_Num() .. "\\t" .. DataPool:GetMatBag_Num()'
MA_MO_TCCN = trong_cua_so("MainMenuBar", "MainMenuBar_KuaiJieYiZhan()")
MA_TCCN_DANG_MO = 'return tostring(IsWindowShow("Packet_Temporary"))'
MA_CAT_TCCN = trong_cua_so("Packet_Temporary", 'if not IsWindowShow("Packet_Temporary") then return "dong" end '
                                               'Packet_Temporary_PutInItem({o}) return "1"')
MA_KHO_DANG_MO = 'return tostring(IsWindowShow("Bank"))'
MA_O_TRONG_KHO = ('if not IsWindowShow("Bank") then return "-1" end local tong, n = 0, 0 '
                  'for r = 1, (tonumber(Bank:GetRentBoxNum()) or 0) do local dau, so = Bank:GetRentBoxInfo(r) '
                  'tong = math.max(tong, (tonumber(dau) or 0) + (tonumber(so) or 0)) end '
                  'for i = 0, tong - 1 do local a = Bank:EnumItem(i) if a and a:GetID() ~= 0 then n = n + 1 end end '
                  'return tostring(tong - n)')
# Chuột phải ô túi lúc cửa sổ kho đóng là DÙNG món đó (Phiếu KNB thành KNB): kiểm tra kho đang mở ngay trong lệnh.
MA_CAT_KHO = trong_cua_so("Packet", 'if not IsWindowShow("Bank") then return "dong" end '
                                    'local a = PlayerPackage:EnumItem("{tui}", {o}) '
                                    'if not a or a:GetID() == 0 then return "0" end '
                                    'Packet_Space_Line1_Row1_button:SetActionItem(a:GetID()) '
                                    'Packet_Space_Line1_Row1_button:DoAction() return "1"')
MA_DONG_CUA_SO = ('for _, w in ipairs({"Packet_Temporary", "Bank", "Quest"}) do '
                  'if IsWindowShow(w) then CloseWindow(w, true) end end')


class _Dung(Exception):
    pass


class LoiGiaoAccChinh(Exception):
    pass


def cai_dat():
    gia_tri = dict(MAC_DINH)
    gia_tri.update(cau_hinh.chung().get(KHOA_CAI_DAT) or {})
    return gia_tri


def luu_cai_dat(**thay_doi):
    cau_hinh.dat_chung({KHOA_CAI_DAT: dict(cai_dat(), **thay_doi)})


def la_phieu_knb(ten):
    khoa = bo_dau(ten)
    return "phieu knb" in khoa or "phieu kim nguyen bao" in khoa


def ten_nhan_vat_acc_chinh_online():
    """Tên nhân vật acc chính nếu đang trong game, None nếu không."""
    cd = cai_dat()
    tk = (cd.get("tai_khoan") or "").strip()
    ten = (cd.get("nhan_vat") or "").strip()
    if not tk or not ten:
        return None
    import win32gui
    hwnd = tim_game_cua_tai_khoan(tk)
    if not hwnd or not win32gui.IsWindow(hwnd):
        return None
    try:
        tt = Game(hwnd).thong_tin()
    except (LoiLua, OSError):
        return None
    except Exception:
        return None
    if tt and chuan_hoa(tt["ten"]) == chuan_hoa(ten):
        return ten
    return None


def hwnd_acc_chinh_train():
    """Cửa sổ game acc chính đang train (tab Giao dịch cho acc chính), None nếu chưa online đúng nhân vật."""
    if not ten_nhan_vat_acc_chinh_online():
        return None
    tk = (cai_dat().get("tai_khoan") or "").strip()
    return tim_game_cua_tai_khoan(tk) if tk else None


def tk_acc_chinh_bo_pho_ban():
    """Tài khoản acc chính đang online (để train), không đưa vào nhóm phó bản xoay vòng."""
    if not ten_nhan_vat_acc_chinh_online():
        return None
    return (cai_dat().get("tai_khoan") or "").strip().lower() or None


def _ma_thu_muc(ten):
    """Tên thư mục / file game ghi cho tài khoản, nhân vật: "#" + hex bytes VISCII (caychay72 -> #636179636861793732)."""
    try:
        du_lieu = ma_hoa(ten)
    except KeyError:
        du_lieu = ten.encode("utf-8")
    return "#" + du_lieu.hex()


def thu_muc_accounts():
    return os.path.join(cau_hinh.doc_tai_khoan().get("thu_muc_game") or "", "Accounts")


def cac_nhan_vat_dang_online():
    ten = set()
    for cua_so in tim_cua_so_game():
        khop = ten_trong_tieu_de(cua_so["hwnd"])
        if khop:
            ten.add(chuan_hoa(khop))
    return ten


def ly_do_khong_co_nhan_vat(tk, ten, thu_muc, da_tao=(), online=()):
    """
    Game ghi Accounts\\#<hex tài khoản>\\#<hex nhân vật>.pfc cho tài khoản đã từng đăng nhập / nhân vật đã từng vào game
    (file nhân vật ghi lúc thoát). Lý do bỏ qua (chưa từng đăng nhập / chưa có nhân vật), None nếu có nhân vật hoặc
    không xác định được (không thấy thư mục Accounts). Nhân vật auto đã tạo (da_tao) hoặc đang online thì luôn có.
    """
    if not thu_muc or not os.path.isdir(thu_muc):
        return None
    khoa = chuan_hoa(ten)
    if khoa in online or khoa in da_tao:
        return None
    thu_muc_tk = os.path.join(thu_muc, _ma_thu_muc(tk))
    if not os.path.isdir(thu_muc_tk):
        return "tài khoản chưa từng đăng nhập"
    if not os.path.isfile(os.path.join(thu_muc_tk, _ma_thu_muc(ten) + ".pfc")):
        return "chưa có nhân vật"
    return None


class _KiemTraNhanVat:
    """Gom lý do bỏ qua nhân vật không có thật, đọc thư mục Accounts / client online một lần cho cả danh sách."""

    def __init__(self, bo_qua):
        self.bo_qua = bo_qua
        self.thu_muc = thu_muc_accounts()
        self.online = cac_nhan_vat_dang_online()

    def co(self, tk, ten):
        da_tao = {chuan_hoa(t) for t in da_xong(tk["ten_dang_nhap"])}
        ly_do = ly_do_khong_co_nhan_vat(tk["ten_dang_nhap"], ten, self.thu_muc, da_tao, self.online)
        if ly_do and self.bo_qua is not None:
            self.bo_qua.append((tk["ten_dang_nhap"], ten, ly_do))
        return ly_do is None


def _loc_nhan_vat_pho_ban(tk, ten, chi_hom_nay):
    if chi_hom_nay:
        dem = hom_nay(cai_dat_pmp(cau_hinh.cua_nhan_vat(ten)))
        if not (dem["so_vong"] or dem["st_vong"] or dem["st_het"]):
            return False
    elif chuan_hoa(ten) not in {chuan_hoa(t) for t in da_xong(tk["ten_dang_nhap"])}:
        return False
    return True


def _ung_vien_truong_nhom(tk_chinh):
    """[(tài khoản, tên nhân vật)] có thể là trưởng nhóm (nhận đồ của cả round), chưa lọc."""
    ds = [tk for tk in cac_tai_khoan_dang_tich() if tk["ten_dang_nhap"].lower() != tk_chinh.lower()]
    theo_tk = {tk["ten_dang_nhap"].lower(): tk for tk in ds}
    ung_vien = [(nhom[0], ten_round(nhom[0]["ten_dang_nhap"], r))
                for nhom in chia_nhom(ds) for r in range(SO_ROUND_TOI_DA)]
    # Nhóm có người bù vào thì trưởng nhóm thay đổi; xoay vòng ghi lại các trưởng nhóm thật.
    ung_vien += [(theo_tk[tk.lower()], ten) for tk, ten in cau_hinh.chung()["xv_truong_nhom"]
                 if tk.lower() in theo_tk]
    return ung_vien


def ten_cac_truong_nhom(tk_chinh):
    return {chuan_hoa(ten) for _, ten in _ung_vien_truong_nhom(tk_chinh)}


def bo_qua_cung_tai_khoan(tk, ten, tk_khong_co_do, ten_truong):
    """
    Chế độ «tất cả acc»: một nhân vật của tài khoản không có đồ thì các nhân vật khác của tài khoản đó cũng đã giao
    hết cho trưởng nhóm, bỏ qua — trừ nhân vật là trưởng nhóm (nhận đồ cả round, có thể đang giữ đồ).
    """
    return tk["ten_dang_nhap"].lower() in tk_khong_co_do and chuan_hoa(ten) not in ten_truong


def cac_truong_nhom(tk_chinh, chi_hom_nay, bo_qua=None):
    """
    [(tài khoản, tên nhân vật)] các trưởng nhóm theo thứ tự xoay vòng; chi_hom_nay: chỉ nhân vật đã đi hôm nay.
    Bỏ nhân vật không có thật (tài khoản chưa từng đăng nhập / chưa tạo nhân vật), ghi (tk, tên, lý do) vào bo_qua.
    """
    kiem_tra = _KiemTraNhanVat(bo_qua)
    kq, da_co = [], set()
    for tk, ten in _ung_vien_truong_nhom(tk_chinh):
        if chuan_hoa(ten) in da_co:
            continue
        da_co.add(chuan_hoa(ten))
        if not kiem_tra.co(tk, ten) or not _loc_nhan_vat_pho_ban(tk, ten, chi_hom_nay):
            continue
        kq.append((tk, ten))
    return kq


def cac_nhan_vat_pho_ban(tk_chinh, chi_hom_nay, bo_qua=None):
    """[(tài khoản, tên nhân vật)] mọi acc trong nhóm xoay vòng (từng round), không chỉ trưởng nhóm."""
    kiem_tra = _KiemTraNhanVat(bo_qua)
    ds = [tk for tk in cac_tai_khoan_dang_tich() if tk["ten_dang_nhap"].lower() != tk_chinh.lower()]
    kq, da_co = [], set()
    for nhom in chia_nhom(ds):
        for tk in nhom:
            for r in range(SO_ROUND_TOI_DA):
                ten = ten_round(tk["ten_dang_nhap"], r)
                khoa = chuan_hoa(ten)
                if khoa in da_co:
                    continue
                da_co.add(khoa)
                if not kiem_tra.co(tk, ten) or not _loc_nhan_vat_pho_ban(tk, ten, chi_hom_nay):
                    continue
                kq.append((tk, ten))
    return kq


def ap_dung_so_tui(ds, tk_chinh, so):
    """
    Lọc danh sách [(tài khoản, tên)] theo sổ túi đồ: bỏ nhân vật sổ ghi chắc 0 ô; thêm nhân vật sổ ghi còn đồ / chưa rõ
    mà chưa có trong danh sách (đội viên giao lỗi, nhân vật không đi hôm nay...). Trả về (danh sách, tên bỏ, thêm).
    """
    kq, bo = [], []
    for tk, ten in ds:
        if so_tui_do.chac_khong_co_do(so_tui_do.muc_cua(so, ten)):
            bo.append(ten)
        else:
            kq.append((tk, ten))
    co = {chuan_hoa(ten) for _, ten in ds}
    theo_tk = {tk["ten_dang_nhap"].lower(): tk for tk in cau_hinh.tai_khoan_pho_ban()
               if tk.get("ten_dang_nhap") and tk.get("mat_khau")}
    them = []
    for khoa, muc in so.items():
        tk = theo_tk.get((muc.get("tk") or "").lower())
        if khoa in co or tk is None or tk["ten_dang_nhap"].lower() == tk_chinh.lower() or not so_tui_do.can_giao(muc):
            continue
        them.append((tk, muc.get("ten") or khoa))
    kq = sorted(kq + them, key=lambda x: khoa_sap_xep_tai_khoan(x[0]["ten_dang_nhap"]))
    return kq, bo, them


class LuongGiaoAccChinh(threading.Thread):
    def __init__(self, hang_doi):
        super().__init__(daemon=True)
        self.hang_doi = hang_doi
        self.dung = threading.Event()
        self.cd = cai_dat()
        self.tk_chinh = {"ten_dang_nhap": self.cd["tai_khoan"], "mat_khau": self.cd["mat_khau"],
                         "nhan_vat": self.cd["nhan_vat"]}
        self.loai_tru = cac_tu_loai_tru(self.cd["loai_tru"])
        self.tat_ca_pho_ban = bool(self.cd.get("tat_ca_pho_ban"))
        self.bo_qua = []
        self.tk_khong_co_do = set()
        if self.tat_ca_pho_ban:
            ds = cac_nhan_vat_pho_ban(self.cd["tai_khoan"], self.cd["chi_hom_nay"], self.bo_qua)
        else:
            ds = cac_truong_nhom(self.cd["tai_khoan"], self.cd["chi_hom_nay"], self.bo_qua)
        self.ds_truong, self.bo_vi_so, self.them_tu_so = ap_dung_so_tui(ds, self.cd["tai_khoan"], so_tui_do.doc())
        self.chinh = None
        self.hwnd_truong = None
        self.pid_dieu_khien = set()
        self.cac_luong_con = []
        self.tien_trinh = {}
        self.luc_cat = 0.0
        self._pho_ban_da_luu = {}
        # Tài khoản đã bị đăng xuất để nhường client: tự đăng nhập khi diss không mở lại trong lúc giao.
        self.tk_da_thoat = set()

    # ---------- dùng từ giao diện ----------

    def cac_tai_khoan(self):
        if not self.is_alive():
            return set()
        return ({self.tk_chinh["ten_dang_nhap"].lower()} | {tk["ten_dang_nhap"].lower() for tk, _ in self.ds_truong}
                | self.tk_da_thoat)

    def dang_dieu_khien(self, pid):
        if not self.is_alive():
            return False
        return pid in self.pid_dieu_khien or any(l.pid == pid and l.is_alive() for l in list(self.cac_luong_con))

    # ---------- chung ----------

    def in_log(self, chu):
        self.hang_doi.put(("log", f"[Giao acc chính] {chu}"))

    def bao_trang_thai(self, chu):
        self.hang_doi.put(("trang_thai_giao_acc_chinh", chu))

    def _kiem_tra_dung(self):
        if self.dung.is_set():
            raise _Dung()

    def _cho(self, dieu_kien, giay, buoc=0.5):
        het_han = time.time() + giay
        while True:
            self._kiem_tra_dung()
            ket_qua = dieu_kien()
            if ket_qua or time.time() > het_han:
                return ket_qua
            self.dung.wait(buoc)

    def _luu_tien_trinh(self):
        luu_cai_dat(tien_trinh=self.tien_trinh)

    @staticmethod
    def _doc(game):
        try:
            return game.thong_tin()
        except (LoiLua, OSError):
            return None

    def run(self):
        try:
            self._chay()
        except _Dung:
            self.in_log("Đã dừng (tiến trình đã lưu, bấm Bắt đầu để đi tiếp)")
            self.bao_trang_thai("Đã dừng")
        except LoiGiaoAccChinh as loi:
            self.in_log(f"Dừng: {loi} (tiến trình đã lưu)")
            self.bao_trang_thai(f"Dừng: {loi}")
        except Exception:
            self.in_log(f"Lỗi không mong đợi\n{traceback.format_exc()}")
            self.bao_trang_thai("Lỗi, xem log")
        finally:
            self._khoi_phuc_phó_ban()
            for luong in self.cac_luong_con:
                luong.dung.set()
            if self.chinh:
                try:
                    self.chinh.lua.chay(MA_DONG_CUA_SO)
                except (LoiLua, OSError):
                    pass
            self.pid_dieu_khien.clear()

    def _tam_tat_phó_ban(self):
        """Tắt phó bản trên cấu hình để luồng auto đang chạy thoát vòng PMP/Sát Tinh ngay."""
        if self._pho_ban_da_luu:
            return
        for ten in cau_hinh.cac_nhan_vat():
            cd = cau_hinh.cua_nhan_vat(ten)
            pmp = cai_dat_pmp(cd)
            if not pmp.get("bat"):
                continue
            self._pho_ban_da_luu[ten] = copy.deepcopy(pmp)

            def sua(c):
                moi = dict(cai_dat_pmp(c))
                moi["bat"] = False
                c["pho_ban_pmp"] = moi

            cau_hinh.sua_nhan_vat(ten, sua)
        if self._pho_ban_da_luu:
            self.in_log(f"Tạm tắt phó bản {len(self._pho_ban_da_luu)} nhân vật trong lúc giao dịch")

    def _khoi_phuc_phó_ban(self):
        if not self._pho_ban_da_luu:
            return
        so = len(self._pho_ban_da_luu)
        for ten, pmp in self._pho_ban_da_luu.items():

            def sua(c, luu=pmp):
                c["pho_ban_pmp"] = copy.deepcopy(luu)

            cau_hinh.sua_nhan_vat(ten, sua)
        self._pho_ban_da_luu = {}
        self.in_log(f"Bật lại phó bản {so} nhân vật")

    def _ve_chon_may_chu(self, game, ten):
        try:
            game.lua.chay(MA_DONG_CUA_SO)
        except LoiLua:
            pass
        try:
            ve_chon_may_chu(game, self.dung.is_set, lambda chu: self.in_log(f"{ten}: {chu}"))
        except LoiDangNhap as loi:
            raise LoiGiaoAccChinh(f"{ten}: {loi}") from loi

    def _chay(self):
        hom_nay_chu = date.today().isoformat()
        self.tien_trinh = dict(self.cd.get("tien_trinh") or {})
        if self.tien_trinh.get("ngay") != hom_nay_chu:
            self.tien_trinh = {"ngay": hom_nay_chu, "da_xong": [], "ma_da_nhan": []}
        for ly_do in dict.fromkeys(l for _, _, l in self.bo_qua):
            cac = list(dict.fromkeys(tk if ly_do.startswith("tài khoản") else ten
                                     for tk, ten, l in self.bo_qua if l == ly_do))
            self.in_log(f"Bỏ qua {len(cac)} ({ly_do}): {', '.join(cac)}")
        if self.bo_vi_so:
            self.in_log(f"Bỏ qua {len(self.bo_vi_so)} (sổ túi đồ ghi không có đồ): {', '.join(self.bo_vi_so)}")
        so = so_tui_do.doc()
        if self.them_tu_so:
            self.in_log(f"Thêm {len(self.them_tu_so)} nhân vật sổ túi đồ ghi còn đồ: " + ", ".join(
                f"{ten} ({so_tui_do.mo_ta(so_tui_do.muc_cua(so, ten))})" for _, ten in self.them_tu_so))
        da_xong_ds = {chuan_hoa(t) for t in self.tien_trinh["da_xong"]}
        # Đã giao hôm nay nhưng sau đó đi phó bản tiếp (sổ ghi lại có đồ) thì giao lại.
        con = [(tk, ten) for tk, ten in self.ds_truong
               if chuan_hoa(ten) not in da_xong_ds or so_tui_do.can_giao(so_tui_do.muc_cua(so, ten))]
        loai = "mọi acc phó bản" if self.tat_ca_pho_ban else "trưởng nhóm"
        self.in_log(f"Bắt đầu: acc chính {self.tk_chinh['nhan_vat']}, {len(self.ds_truong)} nhân vật ({loai})"
                    + (" đã đi hôm nay" if self.cd["chi_hom_nay"] else "")
                    + f", đã xong {len(self.ds_truong) - len(con)}, còn {len(con)}: "
                    + ", ".join(ten for _, ten in con))
        if not con:
            self.bao_trang_thai(f"Xong (không còn nhân vật {loai})")
            return
        self._tam_tat_phó_ban()
        try:
            self._chay_giao(con, loai)
        finally:
            self._khoi_phuc_phó_ban()

    def _chay_giao(self, con, loai):
        self._vao_acc_chinh()
        ten_truong = ten_cac_truong_nhom(self.tk_chinh["ten_dang_nhap"]) if self.tat_ca_pho_ban else set()
        so_tui = so_tui_do.doc()
        for so, (tk, ten) in enumerate(con, 1):
            self.bao_trang_thai(f"{so}/{len(con)}: {ten}")
            # Chỉ đoán theo tài khoản khi sổ chưa có nhân vật này; sổ ghi còn đồ / chưa rõ thì luôn đăng nhập.
            if self.tat_ca_pho_ban and so_tui_do.muc_cua(so_tui, ten) is None \
                    and bo_qua_cung_tai_khoan(tk, ten, self.tk_khong_co_do, ten_truong):
                self.in_log(f"{ten}: nhân vật khác của {tk['ten_dang_nhap']} không có đồ (đã giao cho trưởng nhóm), "
                            "bỏ qua không đăng nhập")
                self.tien_trinh["da_xong"].append(ten)
                self._luu_tien_trinh()
                continue
            if self._mot_truong_nhom(tk, ten):
                self.tien_trinh["da_xong"].append(ten)
                self._luu_tien_trinh()
        self.in_log(f"Xong tất cả nhân vật ({loai})")
        self.bao_trang_thai("Xong")

    # ---------- đăng nhập ----------

    def _dang_nhap(self, tai_khoan, hwnd):
        acc_chinh = tai_khoan["ten_dang_nhap"].lower() == self.tk_chinh["ten_dang_nhap"].lower()
        luong = LuongVaoNhanVat(tai_khoan, cau_hinh.doc_tai_khoan(), self.hang_doi, hwnd,
                                kiem_tra_rule_ten=not acc_chinh)
        self.cac_luong_con.append(luong)
        luong.start()
        while luong.is_alive():
            if self.dung.is_set():
                luong.dung.set()
            time.sleep(1)
        self.cac_luong_con.remove(luong)
        self._kiem_tra_dung()
        if not (luong.thanh_cong and luong.game):
            return None
        self.pid_dieu_khien.add(luong.game.lua.pid)
        return luong.game

    def _thoat_cac_client(self, giu=()):
        """Client đang trong game (trừ hwnd trong giu) về chọn máy chủ cùng lúc; giữ client để đăng nhập acc khác."""
        can_thoat = []
        for cua_so in tim_cua_so_game():
            if cua_so["hwnd"] in giu:
                continue
            try:
                game = Game(cua_so["hwnd"])
                tt = game.thong_tin()
                if not tt and man_hinh_hien_tai(game.lua) != "vao_game":
                    continue
            except (LoiLua, OSError):
                continue
            tk = ((tt or {}).get("tai_khoan") or tai_khoan_cua_pid(cua_so["pid"]) or "").strip().lower()
            if tk:
                self.tk_da_thoat.add(tk)
            can_thoat.append((cua_so["pid"], (tt or {}).get("ten") or cua_so["tieu_de"].split(" - ")[0]))
        if not can_thoat:
            return
        self.in_log(f"Đăng xuất {len(can_thoat)} client về chọn máy chủ: {', '.join(ten for _, ten in can_thoat)}")
        self.pid_dieu_khien |= {pid for pid, _ in can_thoat}
        cac_luong = [threading.Thread(target=thoat_ve_chon_may_chu, daemon=True,
                                      args=(pid, lambda chu, t=ten: self.in_log(f"{t}: {chu}"), self.dung.is_set))
                     for pid, ten in can_thoat]
        for luong in cac_luong:
            luong.start()
        for luong in cac_luong:
            luong.join()
        self._kiem_tra_dung()

    def _hwnd_acc_chinh_dung_nhan_vat(self):
        hwnd = tim_game_cua_tai_khoan(self.tk_chinh["ten_dang_nhap"])
        if not hwnd:
            return None
        try:
            tt = Game(hwnd).thong_tin()
        except (LoiLua, OSError):
            return None
        return hwnd if tt and chuan_hoa(tt["ten"]) == chuan_hoa(self.tk_chinh["nhan_vat"]) else None

    def _vao_acc_chinh(self):
        ten = self.tk_chinh["nhan_vat"]
        self.bao_trang_thai(f"Đăng xuất các client, vào acc chính {ten}")
        hwnd = self._hwnd_acc_chinh_dung_nhan_vat()
        self._thoat_cac_client(giu={hwnd} if hwnd else ())
        if hwnd:
            self.in_log(f"Acc chính {ten} đang trong game, giữ nguyên")
        else:
            hwnd = tim_hwnd_cua_tai_khoan(self.tk_chinh["ten_dang_nhap"]) \
                or next((c["hwnd"] for c in tim_cua_so_game()), None)
            if hwnd:
                self.in_log(f"Đăng nhập acc chính {ten} trên client đang mở (không mở game mới)")
        game = self._dang_nhap(self.tk_chinh, hwnd)
        if game is None:
            raise LoiGiaoAccChinh(f"không đăng nhập được acc chính {ten} (xem log Đăng nhập)")
        self.chinh = game
        self._cho(lambda: self._doc(game), 60)
        game.lua.chay(MA_DONG_CUA_SO)
        self._ve_dai_ly(game, ten)
        self._chay_toi(game, ten, NPC_TAN_THU[1])

    def _chon_game_truong(self, tk):
        """
        Client cho acc giao dịch: game đang dùng tài khoản đó, client của acc trước, client khác acc chính (chỉ mở game
        mới khi không còn client nào). Client khác đang trong game thì về chọn máy chủ, không tắt.
        """
        hwnd_chinh = self.chinh.lua.hwnd
        hwnd = tim_game_cua_tai_khoan(tk["ten_dang_nhap"])
        cac_cua_so = [c["hwnd"] for c in tim_cua_so_game() if c["hwnd"] != hwnd_chinh]
        if hwnd is None:
            hwnd = self.hwnd_truong if self.hwnd_truong in cac_cua_so else (cac_cua_so[0] if cac_cua_so else None)
        self._thoat_cac_client(giu={hwnd_chinh, hwnd})
        return hwnd

    # ---------- di chuyển ----------

    def _ve_dai_ly(self, game, ten):
        luc_ve = 0.0
        het_han = time.time() + GIAY_CHO_VE_DAI_LY
        while time.time() < het_han:
            self._kiem_tra_dung()
            tt = self._doc(game)
            if tt and la_dai_ly(tt["map"]):
                return
            if tt and time.time() - luc_ve >= GIAY_GIUA_HAI_LAN_VE_THANH:
                luc_ve = time.time()
                try:
                    chuan_bi_ve_thanh(game)
                    game.lua.chay(ma_dung_ky_nang_theo_dinh_nghia(KY_NANG_VE_THANH))
                except LoiLua:
                    pass
            self.dung.wait(1)
        raise LoiGiaoAccChinh(f"{ten} chưa về được Đại Lý")

    def _chay_toi(self, game, ten, xy):
        def toi():
            tt = self._doc(game)
            return tt and math.hypot(tt["x"] - xy[0], tt["y"] - xy[1]) <= KHOANG_CACH_DUNG_CHO
        if toi():
            return
        game.lua.chay(f"AutoRunToTarget({int(xy[0])}, {int(xy[1]) + 2})")
        if not self._cho(toi, GIAY_CHAY_TOI):
            raise LoiGiaoAccChinh(f"{ten} chạy {GIAY_CHAY_TOI} giây chưa tới ({xy[0]}, {xy[1]})")

    def _thoat_game_pho_ban(self, game, ten):
        if not game:
            return
        hwnd = game.lua.hwnd
        pid = game.lua.pid
        self.pid_dieu_khien.discard(pid)
        try:
            self._ve_chon_may_chu(game, ten)
        except (LoiGiaoAccChinh, LoiDangNhap, LoiLua, OSError) as loi:
            self.in_log(f"{ten}: không về chọn máy chủ ({loi}), thử tắt game")
            thoat_ve_chon_may_chu(pid, self.in_log, self.dung.is_set)
            if self.hwnd_truong == hwnd:
                self.hwnd_truong = None
            return
        self.in_log(f"{ten}: đã về chọn máy chủ, sang nhân vật tiếp theo")
        self.hwnd_truong = hwnd

    # ---------- một nhân vật phó bản / trưởng nhóm ----------

    def _do_can_giao(self, game, bo_qua):
        """Các ô (túi, ô) cần giao, trừ đồ loại trừ và đồ đã thử mà không giao được (bo_qua: {(túi, ô, mã)})."""
        cac_o = []
        for (ten_tui, o), (ma, _, ten) in sorted(doc_tui(game.lua).items()):
            if (ten_tui, o, ma) in bo_qua or bi_loai_tru(ten, self.loai_tru):
                continue
            cac_o.append((ten_tui, o))
        return cac_o

    def _mot_truong_nhom(self, tk, ten):
        """Giao hết đồ của một trưởng nhóm cho acc chính. True khi xong (không còn đồ giao được)."""
        ten_chinh = self.tk_chinh["nhan_vat"]
        self.in_log(f"{ten}: đăng nhập")
        game = self._dang_nhap(dict(tk, nhan_vat=ten), self._chon_game_truong(tk))
        if game is None:
            self.in_log(f"{ten}: đăng nhập thất bại nhiều lần, bỏ qua (lần sau bấm Bắt đầu sẽ thử lại)")
            return False
        self.hwnd_truong = game.lua.hwnd
        self._cho(lambda: self._doc(game), 60)
        bo_qua = set()
        cac_o = self._do_can_giao(game, bo_qua)
        if not cac_o:
            self.in_log(f"{ten}: không có đồ cần giao")
            so_tui_do.ghi_da_giao(tk["ten_dang_nhap"], ten)
            if chuan_hoa(ten) not in ten_cac_truong_nhom(self.tk_chinh["ten_dang_nhap"]):
                self.tk_khong_co_do.add(tk["ten_dang_nhap"].lower())
            if self.tat_ca_pho_ban:
                self._thoat_game_pho_ban(game, ten)
            return True
        self.in_log(f"{ten}: có {len(cac_o)} ô đồ, giao dịch cho {ten_chinh}")
        self._ve_dai_ly(game, ten)
        self._chay_toi(game, ten, NPC_TAN_THU[1])
        lan_loi = 0
        while cac_o:
            self._kiem_tra_dung()
            self._don_tui_chinh()
            lan_nay = cac_o[:SO_O_MOT_LAN]
            tui = doc_tui(game.lua)
            ma_moi = {tui[o][0] for o in lan_nay} - set(self.tien_trinh["ma_da_nhan"])
            if ma_moi:
                self.tien_trinh["ma_da_nhan"] += sorted(ma_moi)
                self._luu_tien_trinh()
            try:
                GiaoDich(game, self.chinh, ten, ten_chinh, self.in_log, self.dung.is_set).chuyen(lan_nay)
                lan_loi = 0
            except LoiGiaoDich as loi:
                self._kiem_tra_dung()
                lan_loi += 1
                self.in_log(f"{ten}: giao dịch lỗi ({loi}), thử lại {lan_loi}/{SO_LAN_THU_GIAO_DICH}")
                if lan_loi >= SO_LAN_THU_GIAO_DICH:
                    self.in_log(f"{ten}: giao dịch lỗi nhiều lần, bỏ qua (lần sau bấm Bắt đầu sẽ thử lại)")
                    try:
                        so_tui_do.ghi_so_o(tk["ten_dang_nhap"], ten, doc_tui(game.lua), self.loai_tru)
                    except (LoiLua, OSError):
                        pass
                    return False
                self.dung.wait(3)
                continue
            sau = doc_tui(game.lua)
            for o in lan_nay:
                if o in sau and sau[o] == tui[o]:
                    bo_qua.add((o[0], o[1], tui[o][0]))
            cac_o = self._do_can_giao(game, bo_qua)
        self._don_tui_chinh()
        self.in_log(f"{ten}: đã giao xong"
                    + (f", còn {len(bo_qua)} ô không giao được (đồ khóa?)" if bo_qua else ""))
        so_tui_do.ghi_da_giao(tk["ten_dang_nhap"], ten, {ma for _, _, ma in bo_qua})
        if self.tat_ca_pho_ban:
            self._thoat_game_pho_ban(game, ten)
        return True

    # ---------- cất đồ của acc chính ----------

    def _o_trong(self):
        """{túi: số ô trống} của acc chính."""
        so_o = [int(float(x)) for x in self.chinh.lua.chay(MA_KICH_THUOC_TUI).decode().split("\t")]
        dung = {"base": 0, "material": 0}
        for ten_tui, _ in doc_tui(self.chinh.lua):
            dung[ten_tui] += 1
        return {"base": so_o[0] - dung["base"], "material": so_o[1] - dung["material"]}

    def _do_da_nhan(self):
        """{(túi, ô): (mã, số, tên)} đồ trong túi acc chính có mã từng nhận từ trưởng nhóm."""
        ma = set(self.tien_trinh["ma_da_nhan"])
        return {o: v for o, v in doc_tui(self.chinh.lua).items() if v[0] in ma}

    def _don_tui_chinh(self):
        trong = self._o_trong()
        if min(trong.values()) >= SO_O_TOI_THIEU:
            return
        ten = self.tk_chinh["nhan_vat"]
        self.in_log(f"{ten}: túi còn {trong['base']} ô Đạo cụ, {trong['material']} ô Nguyên liệu trống, cất đồ")
        self.bao_trang_thai(f"{ten}: cất đồ vào Thiên Cơ Cẩm Nang / Thương khố")
        self._cat_tccn()
        self._cat_kho()
        trong = self._o_trong()
        if min(trong.values()) < SO_O_TOI_THIEU:
            raise LoiGiaoAccChinh(f"Thiên Cơ Cẩm Nang và Thương khố đã đầy (túi {ten} còn {trong['base']} ô Đạo cụ, "
                                  f"{trong['material']} ô Nguyên liệu trống)")

    def _cat_mot_o(self, o, ma_cat):
        """Gửi lệnh cất ô o (ma_cat) rồi chờ ô đổi. Trả về "1" đã cất, "0" không cất được, "dong" cửa sổ đã đóng."""
        lua = self.chinh.lua
        truoc = doc_tui(lua).get(o)
        if truoc is None:
            return "0"
        for _ in range(SO_LAN_THU_CAT):
            self._cho(lambda: time.time() - self.luc_cat >= GIAY_GIUA_HAI_LAN_CAT, GIAY_GIUA_HAI_LAN_CAT, 0.1)
            kq = lua.chay(ma_cat)
            self.luc_cat = time.time()
            if kq == b"dong":
                return "dong"
            if self._cho(lambda: doc_tui(lua).get(o) != truoc, GIAY_CHO_CAT, 0.3):
                return "1"
        return "0"

    def _cat_tccn(self):
        lua = self.chinh.lua
        cac_o = [o for o, (_, _, ten) in sorted(self._do_da_nhan().items())
                 if o[0] == "base" and not la_phieu_knb(ten)]
        if not cac_o:
            return
        lua.chay(MA_DONG_CUA_SO)
        lua.chay(MA_MO_TCCN)
        if not self._cho(lambda: lua.chay(MA_TCCN_DANG_MO) == b"true", GIAY_CHO_CUA_SO):
            self.in_log("Không mở được Thiên Cơ Cẩm Nang")
            return
        da_cat = 0
        for o in cac_o:
            kq = self._cat_mot_o(o, MA_CAT_TCCN.replace("{o}", str(o[1])))
            if kq == "dong":
                self.in_log("Cửa sổ Thiên Cơ Cẩm Nang bị đóng giữa chừng")
                break
            da_cat += kq == "1"
        lua.chay(MA_DONG_CUA_SO)
        self.in_log(f"Đã cất {da_cat}/{len(cac_o)} ô vào Thiên Cơ Cẩm Nang")

    def _mo_kho(self):
        lua = self.chinh.lua
        if lua.chay(MA_KHO_DANG_MO) == b"true":
            return True
        lua.chay(MA_DONG_CUA_SO)
        try:
            NhanDoTanThu(self.chinh, self.tk_chinh["nhan_vat"], self.in_log, self.dung.is_set,
                         lambda _: None)._noi_chuyen(NPC_TAN_THU, (DONG_THUONG_KHO,))
        except DungPhoBan:
            raise _Dung()
        except LoiPhoBan as loi:
            self.in_log(f"Không mở được Thương khố: {loi}")
            return False
        return bool(self._cho(lambda: lua.chay(MA_KHO_DANG_MO) == b"true", GIAY_CHO_CUA_SO))

    def _cat_kho(self):
        lua = self.chinh.lua
        cac_o = sorted(self._do_da_nhan())
        if not cac_o:
            return
        if not self._mo_kho():
            self.in_log("Thương khố không mở")
            return
        da_cat = 0
        for o in cac_o:
            o_trong = int(lua.chay(MA_O_TRONG_KHO))
            if o_trong < 0:
                self.in_log("Cửa sổ Thương khố bị đóng giữa chừng")
                break
            if o_trong == 0:
                self.in_log("Thương khố đã đầy")
                break
            kq = self._cat_mot_o(o, MA_CAT_KHO.replace("{tui}", o[0]).replace("{o}", str(o[1])))
            if kq == "dong":
                self.in_log("Cửa sổ Thương khố bị đóng giữa chừng")
                break
            da_cat += kq == "1"
        lua.chay(MA_DONG_CUA_SO)
        self.in_log(f"Đã cất {da_cat}/{len(cac_o)} ô vào Thương khố")
