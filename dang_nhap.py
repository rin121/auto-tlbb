"""
TỰ MỞ GAME VÀ ĐĂNG NHẬP.

Game hay bị diss (tự tắt). LuongDangNhap mở lại game và đăng nhập cho một tài khoản (có cửa sổ cũ thì về chọn máy
chủ EnterQuitWait(1), không tắt process trừ khi game đã chết):
    chạy Bin\\Game.exe -fl (đúng lệnh launcher "Vao Game - Update.exe" chạy khi bấm Start Game)
    -> chờ game tải xong mới nạp DLL (nạp lúc game đang khởi động làm game văng)
    -> bấm "Bước tiếp theo" ở màn hình sự kiện -> chọn máy chủ -> điền tài khoản, mật khẩu -> vào nhân vật -> nhập mã kiểm tra -> vào game.
Tài khoản không ghi tên nhân vật thì tới màn hình chọn nhân vật sẽ chờ người chơi tự chọn
(vào game rồi giao_dien tự ghi tên nhân vật đó cho lần đăng nhập sau).
Mã kiểm tra: nhập mã cố định trong cài đặt, hoặc bật "giai_ma_kiem_tra" để đọc ảnh và giải (giai_captcha.py).

Mọi bước gọi hàm Lua của chính giao diện game (Data\\Interface.axp), không click chuột:
    Sự kiện       : GameProduceLogin:ExitToSelectServer()                      (Huodongricheng.lua)
    Chọn máy chủ  : GameProduceLogin:GetAreaLoginServerInfo, SelectLoginServer   (SelectServer.lua)
    Đăng nhập     : LogOn_ID, LogOn_PassWord, LogOn_CheckAccount()             (LogOn.lua)
    Chọn nhân vật : GameProduceLogin:GetRoleInfo, SendEnterGameMsg             (SelectRole.lua)
    Mã kiểm tra   : TextValidate_Input, TextValidate_BtnCommitClick()          (TextValidate.lua)

Ô nhập (LogOn_ID...) không nằm trong bảng biến chung của Lua mà trong bảng riêng của từng cửa sổ
(LoginLogOn_Env...). Lúc chạy script của một cửa sổ, game trỏ __index của bảng biến chung sang bảng
riêng đó; trong_cua_so() làm y hệt rồi trả lại như cũ.
"""
import os
import re
import subprocess
import threading
import time
import traceback
import unicodedata

import psutil

import giai_captcha
from auto_chuyen_sinh import chuan_hoa
from bang_ma_viscii import giai_ma, ma_hoa
from cua_so_game import tim_cua_so_game
from game_api import Game
from lua_game import LoiLua

# Tên cửa sổ lấy từ Config.axp/InterfaceEx.txt. Xét theo thứ tự: màn hình đứng trước che màn hình sau.
CAC_MAN_HINH = (
    ("vao_game", "PlayerFrame"),
    ("ma_kiem_tra", "TextValidate"),
    ("thong_bao", "LoginSelectServerQuest"),
    ("chon_nhan_vat", "LoginSelectRole"),
    ("dang_nhap", "LoginLogOn"),
    ("chon_may_chu", "LoginSelectServer"),
    ("su_kien", "HuoDongRiCheng"),
)
MO_TA_MAN_HINH = {
    "vao_game": "đã vào game",
    "ma_kiem_tra": "nhập mã kiểm tra",
    "thong_bao": "hộp thông báo",
    "chon_nhan_vat": "chọn nhân vật",
    "dang_nhap": "đăng nhập",
    "chon_may_chu": "chọn máy chủ",
    "su_kien": "màn hình sự kiện",
    "": "đang tải",
}
GIAY_LAM_LAI = 10
GIAY_DONG_THONG_BAO = 3
# "Có nhân vật đối ứng đang online" (bị diss mà nhân vật còn kẹt trên server): game khóa nút Đóng 20 giây
# (USERONLINE, SelectServerQuest.lua) cho server kịp đá nhân vật cũ, hết 20 giây thì Đóng rồi đăng nhập lại.
GIAY_DONG_THONG_BAO_DANG_ONLINE = 21
CHU_DANG_ONLINE = "dang online"
# Hộp báo lỗi mạng ("Xin kiểm tra lại đường mạng và đăng nhập lại") và "Máy chủ đang bận": bấm Đóng ngay.
# Máy chủ bận lúc chọn nhân vật thì còn bấm Quay lại để đăng nhập lại từ đầu.
CHU_LOI_MANG = "kiem tra lai duong mang"
CHU_MAY_CHU_BAN = "may chu dang ban"
GIAY_DONG_THONG_BAO_NGAY = 1
# Sau mỗi lần gửi mã / đổi ảnh, hộp mã kiểm tra khóa nút 3 giây.
GIAY_GIUA_HAI_LAN_NHAP_MA = 4
MAU_MA_MAU = re.compile(r"#[cegCEG][0-9a-fA-F]{6}|#[a-zA-Z]")


class LoiDangNhap(Exception):
    pass


class LoiSaiTaiKhoan(LoiDangNhap):
    """Thử lại cũng không vào được, phải sửa tài khoản/mật khẩu."""


class LoiSaiRuleNhanVat(LoiDangNhap):
    """Tài khoản có nhân vật không theo quy tắc tên (caychay10 -> caychay10, caychay100, caychay1000)."""

    def __init__(self, cac_ten):
        super().__init__("có nhân vật sai quy tắc tên: " + ", ".join(cac_ten))
        self.cac_ten = list(cac_ten)


def bo_ma_mau(chu):
    """"#e6633ff#gFFFF99#bMáy Chủ Mới" -> "Máy Chủ Mới"."""
    return MAU_MA_MAU.sub("", chu).strip()


def bo_dau(chu):
    """"Máy Chủ Mới" -> "may chu moi", để gõ có dấu hay không, hoa hay thường đều khớp."""
    chu = bo_ma_mau(chu).replace("đ", "d").replace("Đ", "D")
    chu = "".join(c for c in unicodedata.normalize("NFD", chu) if not unicodedata.combining(c))
    return " ".join(chu.casefold().split())


def chuoi_lua(chu):
    """Chuỗi Python -> chuỗi Lua viết trong code, theo bảng mã VISCII của game."""
    try:
        du_lieu = ma_hoa(chu)
    except KeyError as loi:
        raise LoiDangNhap(f"Ký tự {loi} trong \"{chu}\" không gõ được vào game") from None
    return '"' + "".join(chr(b) if 32 <= b < 127 and b not in (34, 92) else f"\\{b:03d}" for b in du_lieu) + '"'


def trong_cua_so(ten_cua_so, ma_lua):
    """Bọc đoạn Lua để nó thấy được các ô của cửa sổ ten_cua_so, giống lúc game tự chạy script cửa sổ đó."""
    return ("local mt = getmetatable(getfenv(0)) local cu = mt.__index "
            f'mt.__index = rawget(getfenv(0), "{ten_cua_so}_Env") '
            "local ok, ket_qua = pcall(function()\n" + ma_lua + "\nend) "
            "mt.__index = cu "
            "if not ok then error(ket_qua) end "
            "return ket_qua")


def man_hinh_hien_tai(lua):
    """Trả về một khóa trong MO_TA_MAN_HINH."""
    ma = " ".join(f'if IsWindowShow("{ten}") then return "{khoa}" end' for khoa, ten in CAC_MAN_HINH)
    return lua.chay(ma).decode("latin-1")


def chon_may_chu(lua, ten_may_chu, chi_co_mot_thi_chon=False):
    """
    Chọn máy chủ theo tên. Trả về tên máy chủ đã chọn, None nếu danh sách chưa tải xong.
    chi_co_mot_thi_chon: không có máy chủ tên đó mà game chỉ có một máy chủ thì chọn máy chủ đó.
    """
    ket_qua = lua.chay(
        'local s = "" '
        'for a = 0, GameProduceLogin:GetServerAreaCount() - 1 do '
        'for i = 0, GameProduceLogin:GetAreaLoginServerCount(a) - 1 do '
        's = s .. a .. "\\t" .. i .. "\\t" .. GameProduceLogin:GetAreaLoginServerInfo(a, i) .. "\\n" '
        'end end return s')
    cac_may_chu = []
    for dong in ket_qua.split(b"\n"):
        if dong:
            khu, so, ten = dong.split(b"\t", 2)
            cac_may_chu.append((int(khu), int(so), bo_ma_mau(giai_ma(ten))))
    if not cac_may_chu:
        return None
    for khu, so, ten in cac_may_chu:
        if bo_dau(ten) == bo_dau(ten_may_chu):
            lua.chay(f"GameProduceLogin:SelectLoginServer({khu}, {so}, 0)")
            return ten
    if chi_co_mot_thi_chon and len(cac_may_chu) == 1:
        khu, so, ten = cac_may_chu[0]
        lua.chay(f"GameProduceLogin:SelectLoginServer({khu}, {so}, 0)")
        return ten
    raise LoiDangNhap(f'Không có máy chủ "{ten_may_chu}". Các máy chủ đang có: '
                      + ", ".join(ten for _, _, ten in cac_may_chu))


def dang_nhap(lua, ten_dang_nhap, mat_khau):
    lua.chay(trong_cua_so(
        "LoginLogOn",
        f"LogOn_ID:SetText({chuoi_lua(ten_dang_nhap)}) "
        f"LogOn_PassWord:SetText({chuoi_lua(mat_khau)}) "
        "LogOn_CheckAccount()"))


def ds_ten_nhan_vat(lua):
    """Tên các nhân vật ở màn hình chọn nhân vật (rỗng nếu danh sách chưa tải xong)."""
    ket_qua = lua.chay('local s = "" for i = 0, GameProduceLogin:GetRoleCount() - 1 do '
                       's = s .. GameProduceLogin:GetRoleInfo(i) .. "\\n" end return s')
    return [giai_ma(ten) for ten in ket_qua.split(b"\n")[:-1]]


def chon_nhan_vat(lua, ten_nhan_vat, cac_ten=None):
    """
    Vào game bằng nhân vật có tên này.
    Trả về tên đã chọn, None nếu danh sách nhân vật chưa tải xong.
    """
    cac_ten = cac_ten if cac_ten is not None else ds_ten_nhan_vat(lua)
    if not cac_ten:
        return None
    for so_sanh in (chuan_hoa, bo_dau):
        for chi_so, ten in enumerate(cac_ten):
            if so_sanh(ten) == so_sanh(ten_nhan_vat):
                lua.chay(f"GameProduceLogin:SendEnterGameMsg({chi_so})")
                return ten
    raise LoiDangNhap(f'Tài khoản không có nhân vật "{ten_nhan_vat}". Các nhân vật: ' + ", ".join(cac_ten))


def dang_hien(lua, ten_cua_so):
    return lua.chay(f'if IsWindowShow("{ten_cua_so}") then return "1" end return "0"') == b"1"


def nhap_ma_kiem_tra(lua, ma):
    lua.chay(trong_cua_so("TextValidate",
                          f"TextValidate_Input:SetText({chuoi_lua(ma)}) TextValidate_BtnCommitClick()"))


def giai_hop_ma_kiem_tra(lua, nen_dung, giay_toi_da):
    """
    Đọc ảnh, giải và nhập mã tới khi hộp mã kiểm tra (TextValidate) đóng; ảnh khó đọc thì đổi ảnh khác.
    Trả về số lần đã nhập nếu hộp đã đóng, None nếu quá giay_toi_da giây hoặc bị dừng.
    Lỗi đọc ảnh (thiếu ddddocr, khác bản Game.exe) thì ném giai_captcha.LoiGiaiCaptcha.
    """
    het_han = time.time() + giay_toi_da
    anh_da_gui, so_lan_nhap = None, 0
    while time.time() < het_han and not nen_dung():
        if not dang_hien(lua, "TextValidate"):
            return so_lan_nhap
        anh = giai_captcha.doc_anh(lua.pid)
        # Vẫn là ảnh đã gửi mã (sai mà server không gửi ảnh mới) thì đổi ảnh như ảnh khó đọc.
        ma = None if anh == anh_da_gui else giai_captcha.giai(anh)
        if ma:
            nhap_ma_kiem_tra(lua, ma)
            anh_da_gui = anh
            so_lan_nhap += 1
        else:
            lua.chay(trong_cua_so("TextValidate", "TextValidate_BtnChangePicClick()"))
        time.sleep(GIAY_GIUA_HAI_LAN_NHAP_MA)
    if not nen_dung() and not dang_hien(lua, "TextValidate"):
        return so_lan_nhap
    return None


def noi_dung_thong_bao(lua):
    try:
        return bo_ma_mau(giai_ma(lua.chay(trong_cua_so(
            "LoginSelectServerQuest", "return SelectServerQuest_InfoWindow:GetText()"))))
    except LoiLua:
        return ""


def dong_thong_bao(lua):
    """Bấm nút thứ nhất (Đóng/Duyệt) của hộp thông báo ở màn hình đăng nhập."""
    lua.chay(trong_cua_so("LoginSelectServerQuest", "SelectServerQuest_Bn1Click()"))


def con_chay(pid):
    try:
        return psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except psutil.Error:
        return False


GIAY_CHO_VE_CHON_MAY_CHU = 40


def tat_game(pid):
    try:
        psutil.Process(pid).kill()
    except psutil.Error:
        pass


def tim_hwnd_theo_tai_khoan(ten_dang_nhap):
    """hwnd game đang trong game bằng tài khoản này, None nếu không thấy."""
    for cua_so in tim_cua_so_game():
        try:
            tt = Game(cua_so["hwnd"]).thong_tin()
        except (LoiLua, OSError):
            continue
        except Exception:
            continue
        if tt and (tt["tai_khoan"] or "").lower() == ten_dang_nhap.lower():
            return cua_so["hwnd"]
    return None


def ve_chon_may_chu(game, nen_dung=None, in_log=None):
    """Hệ thống → Về chọn máy chủ (giữ client, không tắt game)."""
    if in_log:
        in_log("Về chọn máy chủ")
    game.lua.chay("EnterQuitWait(1)")
    het_han = time.time() + GIAY_CHO_VE_CHON_MAY_CHU
    while time.time() < het_han:
        if nen_dung and nen_dung():
            raise LoiDangNhap("Đã dừng")
        try:
            if man_hinh_hien_tai(game.lua) not in ("vao_game", ""):
                if in_log:
                    in_log("Đã về màn hình chọn máy chủ")
                return
        except LoiLua:
            pass
        time.sleep(1)
    raise LoiDangNhap(f"Bấm về chọn máy chủ mà sau {GIAY_CHO_VE_CHON_MAY_CHU} giây vẫn ở trong game")


def thoat_ve_chon_may_chu(pid, in_log=None, nen_dung=None):
    """Trước khi đăng nhập lại: về chọn máy chủ thay vì tắt process (không có cửa sổ thì vẫn kill)."""
    if not pid or not con_chay(pid):
        return
    for cua_so in tim_cua_so_game():
        if cua_so["pid"] != pid:
            continue
        try:
            ve_chon_may_chu(Game(cua_so["hwnd"]), nen_dung=nen_dung, in_log=in_log)
            return
        except (LoiDangNhap, LoiLua, OSError):
            break
    tat_game(pid)


def mo_game(thu_muc_game):
    """Mở Game.exe -fl, trả về pid của Game.exe."""
    duong_dan = os.path.join(thu_muc_game, "Bin", "Game.exe")
    if not os.path.isfile(duong_dan):
        raise LoiDangNhap(f"Không thấy {duong_dan}. Sửa ô Thư mục game ở tab Tài khoản rồi bấm Lưu cài đặt")
    try:
        import cai_dat_game
        import cau_hinh
        if cau_hinh.chung().get("giam_do_hoa"):
            cai_dat_game.chuan_bi_thu_muc_game(thu_muc_game)
    except OSError:
        pass
    return subprocess.Popen([duong_dan, "-fl"], cwd=os.path.dirname(duong_dan)).pid


def cho_cua_so(pid, giay_cho, nen_dung):
    """Chờ tới khi game có cửa sổ và đã chạy đủ giay_cho giây. Trả về hwnd."""
    bat_dau = psutil.Process(pid).create_time()
    while True:
        if nen_dung():
            raise LoiDangNhap("Đã dừng")
        if not con_chay(pid):
            raise LoiDangNhap("Game tự tắt lúc đang khởi động")
        tuoi = time.time() - bat_dau
        cac_cua_so = [c for c in tim_cua_so_game() if c["pid"] == pid]
        if cac_cua_so and tuoi >= giay_cho:
            return cac_cua_so[0]["hwnd"]
        if tuoi > giay_cho + 120:
            raise LoiDangNhap("Quá lâu không thấy cửa sổ game")
        time.sleep(1)


class CongMoGame:
    """
    Mở nhiều client cùng lúc thì client bị chặn (tự tắt lúc khởi động), nên mọi lần mở game (kể cả thử lại)
    phải xin lượt: trong mỗi giay_giua_moi_dot giây chỉ mở tối đa so_game_moi_dot game.
    """

    def __init__(self):
        self._khoa = threading.Lock()
        self._cac_lan_mo = []

    def cho_luot(self, so_game_moi_dot, giay_giua_moi_dot, nen_dung):
        while True:
            with self._khoa:
                bay_gio = time.time()
                self._cac_lan_mo = [luc for luc in self._cac_lan_mo if bay_gio - luc < giay_giua_moi_dot]
                if len(self._cac_lan_mo) < so_game_moi_dot:
                    self._cac_lan_mo.append(bay_gio)
                    return
            if nen_dung():
                raise LoiDangNhap("Đã dừng")
            time.sleep(0.2)


CONG_MO_GAME = CongMoGame()

# pid game đang mở/đăng nhập theo tài khoản (chưa vào game thì tim_game_cua_tai_khoan chưa thấy).
_PID_THEO_TAI_KHOAN = {}


def _gan_pid_dang_nhap(ten_dang_nhap, pid):
    ten = (ten_dang_nhap or "").strip().lower()
    if ten and pid:
        for khac in [k for k, p in _PID_THEO_TAI_KHOAN.items() if p == pid and k != ten]:
            del _PID_THEO_TAI_KHOAN[khac]
        _PID_THEO_TAI_KHOAN[ten] = pid


def tai_khoan_cua_pid(pid):
    """Tài khoản đăng nhập gần nhất trên game pid (chữ thường), None nếu không rõ."""
    return next((k for k, p in _PID_THEO_TAI_KHOAN.items() if p == pid), None)


def _go_pid_dang_nhap(ten_dang_nhap):
    _PID_THEO_TAI_KHOAN.pop((ten_dang_nhap or "").strip().lower(), None)


def hwnd_dang_dang_nhap(ten_dang_nhap):
    """hwnd cửa sổ game đang đăng nhập tài khoản này (kể cả chưa vào nhân vật), None nếu không có."""
    pid = _PID_THEO_TAI_KHOAN.get((ten_dang_nhap or "").strip().lower())
    if not pid or not con_chay(pid):
        if pid:
            _go_pid_dang_nhap(ten_dang_nhap)
        return None
    for cua_so in tim_cua_so_game():
        if cua_so["pid"] == pid:
            return cua_so["hwnd"]
    return None


# Client (pid) đang do luồng đăng nhập nào điều khiển. Server bảo trì / đăng nhập lỗi thì client vẫn mở ở màn hình
# đăng nhập: lần thử sau và luồng khác phải dùng lại client đó, chỉ mở game mới khi không còn client rảnh.
_KHOA_CLIENT = threading.Lock()
_CHU_CLIENT = {}


def _luong_con_dung(luong):
    return luong.ident is None or luong.is_alive()


def giu_client(pid, luong):
    """Giữ client pid cho luong. False nếu luồng khác đang điều khiển client đó."""
    if not pid:
        return False
    with _KHOA_CLIENT:
        chu = _CHU_CLIENT.get(pid)
        if chu is not None and chu is not luong and _luong_con_dung(chu) and con_chay(pid):
            return False
        _CHU_CLIENT[pid] = luong
        return True


def client_dang_dang_nhap(pid):
    """Có luồng đăng nhập / tạo nhân vật đang điều khiển client pid."""
    with _KHOA_CLIENT:
        chu = _CHU_CLIENT.get(pid)
        return chu is not None and _luong_con_dung(chu)


def nha_cac_client(luong):
    with _KHOA_CLIENT:
        for pid in [p for p, l in _CHU_CLIENT.items() if l is luong]:
            del _CHU_CLIENT[pid]


def lay_client_ranh(luong):
    """Client đang mở, không luồng nào giữ và đang ở màn hình đăng nhập (chưa vào game): giữ cho luong, trả về hwnd."""
    with _KHOA_CLIENT:
        for pid in [p for p, l in _CHU_CLIENT.items() if l is not luong and (not con_chay(p) or not _luong_con_dung(l))]:
            del _CHU_CLIENT[pid]
        for cua_so in tim_cua_so_game():
            pid = cua_so["pid"]
            if _CHU_CLIENT.get(pid, luong) is not luong:
                continue
            try:
                game = Game(cua_so["hwnd"])
                if game.thong_tin() or man_hinh_hien_tai(game.lua) in ("vao_game", "chon_nhan_vat", ""):
                    continue
            except (LoiLua, OSError):
                continue
            _CHU_CLIENT[pid] = luong
            return cua_so["hwnd"]
    return None


def ve_dang_nhap_neu_tk_khac(game, ten_dang_nhap, in_log=None):
    """Client dùng lại còn ở màn chọn nhân vật của tài khoản khác: quay lại màn đăng nhập."""
    try:
        if man_hinh_hien_tai(game.lua) != "chon_nhan_vat" or \
                tai_khoan_cua_pid(game.lua.pid) == (ten_dang_nhap or "").strip().lower():
            return
        if in_log:
            in_log("Client đang ở màn chọn nhân vật của tài khoản khác, quay lại đăng nhập")
        game.lua.chay(trong_cua_so("LoginSelectRole", "SelectRole_Return()"))
    except LoiLua:
        return
    het_han = time.time() + 15
    while time.time() < het_han:
        try:
            if man_hinh_hien_tai(game.lua) != "chon_nhan_vat":
                return
        except LoiLua:
            pass
        time.sleep(0.5)


class LuongDangNhap(threading.Thread):
    """Mở game và đăng nhập một tài khoản, thử lại tối đa so_lan_thu_toi_da lần."""

    def __init__(self, tai_khoan, cai_dat, hang_doi):
        super().__init__(daemon=True)
        self.tai_khoan = tai_khoan
        self.cai_dat = cai_dat
        self.hang_doi = hang_doi
        self.dung = threading.Event()
        self.thanh_cong = False
        self.pid = None
        # Tài khoản không ghi tên nhân vật: tới màn hình chọn nhân vật thì chờ người chơi tự chọn.
        self.cho_nguoi_choi = False
        self.can_quay_lai = False
        self.chi_co_mot_may_chu_thi_chon = False
        self.sai_rule = None
        self.sai_tai_khoan = False

    def in_log(self, chu):
        ten = self.tai_khoan.get("nhan_vat") or self.tai_khoan["ten_dang_nhap"]
        self.hang_doi.put(("log", f"[Đăng nhập {ten}] {chu}"))

    def kiem_tra_ds_nhan_vat(self, cac_ten):
        """Màn hình chọn nhân vật đã có danh sách; lớp con raise LoiSaiRuleNhanVat nếu tài khoản không dùng được."""

    def bao_trang_thai(self, mo_ta):
        self.hang_doi.put(("trang_thai_tai_khoan", self.tai_khoan["ten_dang_nhap"], mo_ta))

    def run(self):
        try:
            self._chay_cac_lan()
        finally:
            nha_cac_client(self)

    def _chay_cac_lan(self):
        so_lan = self.cai_dat["so_lan_thu_toi_da"]
        for lan in range(1, so_lan + 1):
            try:
                self.dang_nhap_mot_lan(lan, so_lan)
                self.thanh_cong = True
                self.bao_trang_thai("Đã vào game")
                return
            except LoiSaiTaiKhoan as loi:
                self.sai_tai_khoan = True
                self.in_log(f"Dừng: {loi}")
                if self.pid:
                    thoat_ve_chon_may_chu(self.pid, self.in_log, self.dung.is_set)
                    _go_pid_dang_nhap(self.tai_khoan["ten_dang_nhap"])
                self.bao_trang_thai("Tạm dừng: sai tài khoản/mật khẩu")
                return
            except LoiSaiRuleNhanVat as loi:
                self.sai_rule = loi.cac_ten
                self.in_log(f"Dừng: {loi}")
                if self.pid:
                    thoat_ve_chon_may_chu(self.pid, self.in_log, self.dung.is_set)
                    _go_pid_dang_nhap(self.tai_khoan["ten_dang_nhap"])
                self.bao_trang_thai("Tạm dừng: tên nhân vật sai rule")
                return
            except (LoiDangNhap, LoiLua, OSError, psutil.Error) as loi:
                self.in_log(f"Lần {lan}/{so_lan} thất bại: {loi}")
            except Exception:
                self.in_log(f"Lần {lan}/{so_lan} lỗi không mong đợi\n{traceback.format_exc()}")
            if self.dung.is_set():
                return
            if self.pid:
                thoat_ve_chon_may_chu(self.pid, self.in_log, self.dung.is_set)
                if not con_chay(self.pid):
                    _go_pid_dang_nhap(self.tai_khoan["ten_dang_nhap"])
            self.dung.wait(5)
        self.bao_trang_thai("Tạm dừng: thất bại nhiều lần")

    def dang_nhap_mot_lan(self, lan, so_lan):
        tk, cd = self.tai_khoan, self.cai_dat
        hwnd = hwnd_dang_dang_nhap(tk["ten_dang_nhap"]) or tim_hwnd_theo_tai_khoan(tk["ten_dang_nhap"])
        if hwnd:
            try:
                game = Game(hwnd)
                self.pid = game.lua.pid
                giu_client(self.pid, self)
                _gan_pid_dang_nhap(tk["ten_dang_nhap"], self.pid)
                self.bao_trang_thai(f"Dùng lại game (lần {lan}/{so_lan})")
                tt = None
                try:
                    tt = game.thong_tin()
                except (LoiLua, OSError):
                    pass
                if tt or man_hinh_hien_tai(game.lua) in ("vao_game", ""):
                    ve_chon_may_chu(game, self.dung.is_set, self.in_log)
                self.dieu_khien(game)
                return
            except (LoiDangNhap, LoiLua, OSError) as loi:
                if self.pid and con_chay(self.pid):
                    raise
                self.in_log(f"Game cũ đã tắt ({loi})")
        if self.dung_client_ranh(lan, so_lan):
            return
        self.bao_trang_thai(f"Chờ lượt mở game (lần {lan}/{so_lan})")
        CONG_MO_GAME.cho_luot(cd["so_game_moi_dot"], cd["giay_giua_moi_dot"], self.dung.is_set)
        if self.dung_client_ranh(lan, so_lan):
            return
        self.bao_trang_thai(f"Mở game (lần {lan}/{so_lan})")
        self.pid = mo_game(cd["thu_muc_game"])
        giu_client(self.pid, self)
        _gan_pid_dang_nhap(tk["ten_dang_nhap"], self.pid)
        self.in_log(f"Đã mở game (pid {self.pid}), "
                    f"chờ {cd['giay_cho_truoc_khi_nap_dll']} giây cho game tải xong")
        hwnd = cho_cua_so(self.pid, cd["giay_cho_truoc_khi_nap_dll"], self.dung.is_set)
        self.dieu_khien(Game(hwnd))

    def dung_client_ranh(self, lan, so_lan):
        """Còn client rảnh ở màn hình đăng nhập thì đăng nhập trên đó thay vì mở game mới. True nếu đã dùng."""
        hwnd = lay_client_ranh(self)
        if not hwnd:
            return False
        tk = self.tai_khoan["ten_dang_nhap"]
        game = Game(hwnd)
        self.pid = game.lua.pid
        self.in_log(f"Dùng client đang rảnh (pid {self.pid}), không mở game mới")
        self.bao_trang_thai(f"Dùng lại game (lần {lan}/{so_lan})")
        ve_dang_nhap_neu_tk_khac(game, tk, self.in_log)
        _gan_pid_dang_nhap(tk, self.pid)
        self.dieu_khien(game)
        return True

    def dieu_khien(self, game, dung_o=()):
        """
        Làm lần lượt từng màn hình cho tới khi nhân vật vào game, hoặc tới một màn hình trong dung_o.
        Trả về khóa màn hình lúc dừng ("vao_game" hoặc màn hình trong dung_o).
        """
        tk, cd = self.tai_khoan, self.cai_dat
        het_han = time.time() + cd["giay_toi_da_moi_buoc"] * len(CAC_MAN_HINH)
        man_truoc, luc_doi, luc_lam, thong_bao_truoc = None, time.time(), 0, None
        while True:
            if self.dung.is_set():
                raise LoiDangNhap("Đã dừng")
            if not con_chay(game.lua.pid):
                raise LoiDangNhap("Game đã tắt")
            bay_gio = time.time()
            if bay_gio > het_han:
                raise LoiDangNhap("Đăng nhập quá lâu")
            try:
                man = man_hinh_hien_tai(game.lua)
            except LoiLua:
                man = ""
            if man in dung_o and not (man == "chon_nhan_vat" and self.can_quay_lai):
                return man
            if man == "dang_nhap":
                self.can_quay_lai = False
            cho_nguoi_choi = man == "chon_nhan_vat" and not tk.get("nhan_vat")
            if man != man_truoc:
                man_truoc, luc_doi, luc_lam = man, bay_gio, 0
                self.bao_trang_thai(MO_TA_MAN_HINH[man].capitalize())
            elif not cho_nguoi_choi:
                # Lúc đang tải (mới mở game, hoặc vào map) DLL có thể chưa đọc được game một lúc.
                gioi_han = cd["giay_toi_da_moi_buoc"] * (2 if man == "" else 1)
                if man not in ("vao_game", "thong_bao") and bay_gio - luc_doi > gioi_han:
                    raise LoiDangNhap(f"Kẹt ở bước {MO_TA_MAN_HINH[man]} quá {gioi_han} giây")
            if cho_nguoi_choi != self.cho_nguoi_choi:
                self.cho_nguoi_choi = cho_nguoi_choi
                if cho_nguoi_choi:
                    self.in_log("Chưa ghi tên nhân vật, chờ người chơi tự chọn nhân vật và bấm Vào trò chơi")
                    self.bao_trang_thai("Chờ người chơi chọn nhân vật")
            if cho_nguoi_choi:
                # Người chơi chọn lâu bao nhiêu cũng được; chọn xong còn đủ thời gian cho các bước sau.
                het_han = max(het_han, bay_gio + cd["giay_toi_da_moi_buoc"] * 3)

            if man == "thong_bao":
                thong_bao = noi_dung_thong_bao(game.lua)
                if thong_bao != thong_bao_truoc:
                    thong_bao_truoc = thong_bao
                    self.in_log(f"Game báo: {thong_bao}")
                    if "khong dung" in bo_dau(thong_bao):
                        raise LoiSaiTaiKhoan(f"Game báo sai tài khoản hoặc mật khẩu ({tk['ten_dang_nhap']})")
                    if CHU_DANG_ONLINE in bo_dau(thong_bao):
                        self.in_log(f"Nhân vật còn kẹt online trên server, chờ {GIAY_DONG_THONG_BAO_DANG_ONLINE} giây "
                                    "(game khóa nút Đóng) rồi bấm Đóng để đăng nhập lại")
            else:
                thong_bao_truoc = None

            try:
                if man == "vao_game":
                    tt = game.thong_tin()
                    if tt:
                        if tk.get("nhan_vat") and chuan_hoa(tt["ten"]) != chuan_hoa(tk["nhan_vat"]):
                            self.in_log(f"Chú ý: vào game bằng {tt['ten']}, không phải {tk['nhan_vat']}")
                        self.in_log(f"{tt['ten']} đã vào game [{tt['map']}]")
                        return man
                elif bay_gio - luc_lam >= GIAY_LAM_LAI and self.lam_buoc(game.lua, man, bay_gio - luc_doi):
                    luc_lam = bay_gio
            except LoiLua:
                pass
            time.sleep(1)

    def lam_buoc(self, lua, man, so_giay_o_man_nay):
        """Làm việc của màn hình hiện tại. Trả về True nếu đã làm (để không làm lại ngay)."""
        tk, cd = self.tai_khoan, self.cai_dat
        if man == "su_kien":
            lua.chay("GameProduceLogin:ExitToSelectServer()")
            self.in_log("Bấm Bước tiếp theo")
            return True
        if man == "chon_may_chu":
            ten = chon_may_chu(lua, cd["may_chu"], self.chi_co_mot_may_chu_thi_chon)
            if ten:
                self.in_log(f"Chọn máy chủ {ten}")
            return bool(ten)
        if man == "dang_nhap":
            dang_nhap(lua, tk["ten_dang_nhap"], tk["mat_khau"])
            _gan_pid_dang_nhap(tk["ten_dang_nhap"], lua.pid)
            self.in_log(f"Đăng nhập tài khoản {tk['ten_dang_nhap']}")
            return True
        if man == "chon_nhan_vat":
            if self.can_quay_lai:
                lua.chay(trong_cua_so("LoginSelectRole", "SelectRole_Return()"))
                self.in_log("Máy chủ đang bận: bấm Quay lại để đăng nhập lại")
                return True
            if not tk.get("nhan_vat"):
                return False
            cac_ten = ds_ten_nhan_vat(lua)
            if cac_ten:
                self.kiem_tra_ds_nhan_vat(cac_ten)
            ten = chon_nhan_vat(lua, tk["nhan_vat"], cac_ten)
            if ten:
                self.in_log(f"Vào trò chơi bằng nhân vật {ten}")
            return bool(ten)
        if man == "ma_kiem_tra":
            if cd["giai_ma_kiem_tra"]:
                return self.giai_ma_kiem_tra(lua)
            nhap_ma_kiem_tra(lua, cd["ma_kiem_tra"])
            self.in_log(f"Nhập mã kiểm tra {cd['ma_kiem_tra']}")
            return True
        if man == "thong_bao":
            chu = bo_dau(noi_dung_thong_bao(lua))
            dang_online = CHU_DANG_ONLINE in chu
            may_chu_ban = CHU_MAY_CHU_BAN in chu
            loi_mang = CHU_LOI_MANG in chu
            if dang_online:
                cho = GIAY_DONG_THONG_BAO_DANG_ONLINE
            elif may_chu_ban or loi_mang:
                cho = GIAY_DONG_THONG_BAO_NGAY
            else:
                cho = GIAY_DONG_THONG_BAO
            if so_giay_o_man_nay > cho:
                dong_thong_bao(lua)
                if may_chu_ban:
                    self.can_quay_lai = True
                self.in_log("Bấm Đóng hộp \"nhân vật đang online\", đăng nhập lại" if dang_online
                            else "Bấm Đóng hộp \"máy chủ đang bận\"" if may_chu_ban
                            else "Bấm Đóng hộp báo lỗi mạng, đăng nhập lại" if loi_mang
                            else "Đóng hộp thông báo để thử lại")
                return True
        return False

    def giai_ma_kiem_tra(self, lua):
        ma_co_dinh = self.cai_dat["ma_kiem_tra"]
        bat_dau = time.time()
        self.in_log("Giải mã kiểm tra")
        try:
            so_lan_nhap = giai_hop_ma_kiem_tra(lua, self.dung.is_set, self.cai_dat["giay_toi_da_moi_buoc"])
        except giai_captcha.LoiGiaiCaptcha as loi:
            self.in_log(f"Không giải được mã kiểm tra ({loi}), nhập mã {ma_co_dinh}")
            nhap_ma_kiem_tra(lua, ma_co_dinh)
            return True
        if so_lan_nhap is not None:
            self.in_log(f"Qua mã kiểm tra (nhập {so_lan_nhap} lần, {time.time() - bat_dau:.0f} giây)")
        return True