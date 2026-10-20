"""
CHIẾN ĐẤU: tự đánh quái quanh nhân vật hoặc quanh một điểm (tab "Chiến đấu").

Game không có hàm Lua nào liệt kê quái xung quanh, nên danh sách quái được đọc thẳng từ bộ nhớ Game.exe
(CHỈ ĐỌC, địa chỉ tìm bằng cách dịch ngược, chỉ đúng với bản Game.exe này):

    Quản lý đối tượng : con trỏ ở 0x646564. +0x64 = nhân vật của mình, +0x4C = std::map<id client, đối tượng>
                        (nút: trái +0, cha +4, phải +8, id client +0x0C, đối tượng +0x10, cờ nút rỗng +0x15)
                                                                          (UpdatePlayerList, 0x56d230)
    Loại đối tượng    : hàm ảo +0x34 trả về lớp; quái / NPC / trân thú là đúng lớp CObject_PlayerNPC (0x63e1e4,
                        hàm 0x408da0), người chơi khác là lớp con CObject_PlayerOther (0x63e498, hàm 0x429610)
    Đối tượng         : id client +0x30 (riêng từng cửa sổ game, = Target:GetData("NPCID"), hàm ảo 0x406950),
                        id server +0x34 (giống nhau ở mọi cửa sổ game, hàm ảo GetID 0x5625f0),
                        tọa độ x +0x44, y +0x4C (đúng số hiện trên bản đồ), dữ liệu nhân vật +0x154 -> +4 = bảng
    Bảng dữ liệu      : +0x00 và +0x64 id chủ (-1 nếu không phải trân thú / đồ triệu hồi)   (lấy phe, 0x4393d0)
                        +0x08 phần trăm máu (float 0..1, <= 0 là đã chết)     (Target:GetHPPercent, 0x507d00)
                        +0x10 GUID nhân vật của người chơi (giống nhau ở mọi cửa sổ game, khác id server)
                        +0x2C tên (std::string)                                 (GetPlayerFromList, 0x452544)
                        +0x8F0 GUID người chơi vừa đánh mình, -1 nếu chưa ai (chỉ có ở nhân vật của mình;
                        server gửi trong gói thuộc tính, game hiện "bị ... công kích")      (0x4de8a0, 0x498590)

Đánh bằng hàm Lua có sẵn của game:
    SetMainTargetFromList(id server, false, true) : chọn đối tượng làm mục tiêu rồi đánh thường (danh sách người
        chơi PlayerList.lua dùng hàm này). Game tự từ chối nếu đối tượng không phải kẻ địch (NPC, trân thú...).
        Tham số 2 = true (kiểu bạn bè) thì chọn được mọi người chơi, kể cả người game không coi là địch.
        Id server giống nhau ở mọi cửa sổ, nên thành viên đánh được đúng con quái Key đang chọn.
    Button_ActionN:DoAction() của cửa sổ MainMenuBar : như bấm phím FN trên thanh kỹ năng (MainMenuBar_Clicked).
    Pet:EnumPetSkillBarItem(i) : kỹ năng của trân thú đang xuất chiến, dùng qua nút ActionSkill_ZhaoshiTarget
        (nút "Dùng" của bảng kỹ năng, ActionSkill.lua).
    EnumAction(i, "skill") / GetActionNum("skill") : kỹ năng của nhân vật (bảng kỹ năng), mã kỹ năng là
        LifeAbility:GetLifeAbility_Number(action:GetID()); dùng qua nút ActionSkill_ZhaoshiTarget như trên.
    Player:GetData("MEMPAI") : môn phái, 0 Thiếu Lâm, 1 Minh Giáo, 2 Cái Bang, 3 Võ Đang, 4 Nga My, 5 Tinh Túc,
        6 Thiên Long, 7 Thiên Sơn, 8 Tiêu Dao, 9 chưa vào phái (ActionSkill.lua, ZhengyouSearch.lua).
        SetMainTargetFromList(id server, true, false) chọn được cả đồng đội lẫn chính mình (để buff máu).
    AutoRunToTarget(x, y) : tự chạy tới tọa độ (AutoSearch.lua).
    Player:GetPKMode() : 0 hòa bình, 1 PK cá nhân, 2 thiện ác, 3 PK đội, 4 bang phái (MiniMap.lua). Hòa bình vẫn
        được phản kích người đang đánh mình, chỉ không được đánh người khác trước.
    Target:GetData("RELATIVE") : 2 là phe bạn (tên trắng), khác 2 là kẻ địch (tên đỏ) (TargetFrame.lua).
    GetMountID() : mã thú cưỡi đang cưỡi, <= 0 nếu đi bộ (Shop_Fitting.lua). Cưỡi thú là một buff có biểu tượng
        "Ride..." (vd. RideHeader8_10 "Thú Cưỡi: Diệt Thế Hỏa Phụng"); Player:DispelBuffByIndex(i) là chuột phải
        vào biểu tượng buff (PlayerImpactFrame.lua) - với buff thú cưỡi thì xuống thú.
"""
import ctypes
import math
import struct
import time
from collections import namedtuple

from auto_chuyen_sinh import chuan_hoa
from bang_ma_viscii import giai_ma
from dang_nhap import chuoi_lua, trong_cua_so
from lua_game import kernel32

MAU_CODE = {
    0x56D24B: "a164656400538b5864",
    0x56D28D: "8b514c8b02",
    0x56D355: "8b04b78b4cb70483c044",
    0x408DA0: "b8e4e16300c3",
    0x5625F0: "8b4134c3",
    0x507D16: "8b80540100008b4804d94108",
    0x4393D4: "8bb15401000085f674598b4e048b0183f8ff75088b416483f8ff",
    0x452544: "8b4f0483c12c",
    0x406950: "8b4130c3",
    0x429610: "b898e46300c3",
    0x4DE8DF: "8b4e048b750889b1f0080000",
}
CON_TRO_QUAN_LY_DOI_TUONG = 0x646564
LECH_NHAN_VAT_CUA_MINH, LECH_CAY_DOI_TUONG = 0x64, 0x4C
HAM_LOP_PLAYER_NPC = bytes.fromhex("b8e4e16300c3")  # mov eax, CObject_PlayerNPC / ret
HAM_LOP_PLAYER_OTHER = bytes.fromhex("b898e46300c3")  # mov eax, CObject_PlayerOther / ret
LECH_HAM_LAY_LOP = 0x34
LECH_KE_DANH = 0x8F0
LECH_ID_CLIENT, LECH_ID, LECH_X, LECH_Y, LECH_DU_LIEU = 0x30, 0x34, 0x44, 0x4C, 0x154
LECH_CHU, LECH_HP, LECH_GUID, LECH_TEN, LECH_CHU_2 = 0x00, 0x08, 0x10, 0x2C, 0x64
SO_NUT_TOI_DA = 5000
DO_DAI_TEN_TOI_DA = 64
QUYEN_DOC = 0x0010 | 0x0400

MAC_DINH = {
    "bat": False,
    "ban_kinh": 12,
    "quanh_diem": False,
    "diem": {"map": "", "x": 0, "y": 0},
    "dung_f1": True,
    "lua_quai": False,
    "so_quai_lua": 4,
    "danh_theo_key": False,
    "ten_key": "",
    "dung_skill_pet": False,
    "cac_phim_skill": [],
    "uu_tien_nguoi_choi": True,
    "xuong_thu": True,
    "nhat_do": True,
    "buff_mau": False,
    "phan_tram_buff": 70,
    "an_don": True,
    "phan_tram_an_don": 50,
    "xuat_chien_tran_thu": False,
    "hoan_hi_toi_thieu": 80,
}
CHE_DO_PK_DANH_NGUOI = (1, 3)  # PK cá nhân, PK đội
MON_PHAI_NGA_MY = 4
MA_KY_NANG_BUFF_MAU = 424  # Thanh Tâm Phổ Thiện Chú (Nga My)
TEN_KY_NANG_BUFF_MAU = "Thanh Tâm Phổ Thiện Chú"
PHIM_BUFF_DU_PHONG = 8
# Mã định nghĩa kỹ năng (action:GetDefineID()) mọi nhân vật đều có, dùng qua ma_dung_ky_nang_theo_dinh_nghia.
KY_NANG_KY_THUAT = 21        # lên thú cưỡi
KY_NANG_VE_THANH = 22        # Quay về Đại Lý thành
# Vận công khoảng 1,5 giây: trong lúc đó không bấm phím đánh (sẽ cắt ngang). Hai lần buff liền nhau cách 3,4 giây
# vẫn trúng cả hai.
GIAY_VAN_CONG_BUFF = 1.8
GIAY_GIUA_HAI_LAN_BUFF = 3.0
# Ẩn Độn Sơ Cấp: kỹ năng chung mọi phái, dùng ngay (không vận công), thêm buff "Ẩn Thân Sơ Cấp". Đánh / dùng kỹ năng
# là lộ, nên đang ẩn thân thì không làm gì tới khi máu hồi lại MAU_HET_AN_THAN hoặc hết ẩn thân.
MA_KY_NANG_AN_DON = 248
TEN_KY_NANG_AN_DON = "Ẩn Độn Sơ Cấp"
TEN_BUFF_AN_THAN = "Ẩn Thân"
MAU_HET_AN_THAN = 0.9
GIAY_GIUA_HAI_LAN_AN_DON = 3.0
GIAY_DOC_LAI_CHE_DO_PK = 2.0
GIAY_NHO_KE_DANH = 10.0
CAC_PHIM_SKILL = range(2, 11)
GIAY_GIUA_HAI_LAN_BAM_PHIM = 1.0
GIAY_GIUA_HAI_LAN_DUNG_SKILL_PET = 3.0
GIAY_GIUA_HAI_LAN_CHAY_VE = 3.0
GIAY_GIUA_HAI_LAN_XEM_THU_CUOI = 1.0
GIAY_DANH_LAI_KHI_MAU_KHONG_GIAM = 4.0
GIAY_BO_QUA_KHI_MAU_KHONG_GIAM = 10.0
GIAY_BO_QUA_QUAI_KHONG_DANH_DUOC = 30.0
GIAY_TOI_DA_LUA_MOT_CON = 5.0
SO_LAN_CHON_HONG_THI_BO_TEN = 2
MAU_DAY = 0.999
MA_XUONG_THU = ('if (tonumber(GetMountID()) or -1) > 0 then '
                'for i = 0, Player:GetBuffNumber() - 1 do '
                'if string.find(tostring(Player:GetBuffIconNameByIndex(i)), "^Ride") then '
                'xuong = tostring(Player:GetBuffToolTipsByIndex(i)) Player:DispelBuffByIndex(i) break end end end')
MA_DANG_AN_THAN = ("for i = 0, Player:GetBuffNumber() - 1 do "
                   f"if string.find(tostring(Player:GetBuffToolTipsByIndex(i)), {chuoi_lua(TEN_BUFF_AN_THAN)}, 1, true) "
                   'then return "1" end end return ""')


def ma_dung_ky_nang(ma_ky_nang):
    """Lua dùng kỹ năng có mã ma_ky_nang của nhân vật (như bấm "Dùng" ở bảng kỹ năng): "skill", hoặc "" nếu không có."""
    return trong_cua_so(
        "ActionSkill",
        "local id = -1 "
        'for i = 0, GetActionNum("skill") - 1 do local a = EnumAction(i, "skill") '
        f"if a and LifeAbility:GetLifeAbility_Number(a:GetID()) == {ma_ky_nang} then id = a:GetID() break end end "
        'if id == -1 then return "" end '
        "local nut = ActionSkill_ZhaoshiTarget nut:SetActionItem(id) nut:DoAction() "
        'if not IsWindowShow("ActionSkill") then nut:SetActionItem(-1) end return "skill"')


def ma_dung_ky_nang_theo_dinh_nghia(ma_dinh_nghia, o_du_phong=0):
    """
    Lua dùng kỹ năng có mã định nghĩa ma_dinh_nghia (action:GetDefineID(), vd. KY_NANG_VE_THANH) qua nút "Dùng" của
    bảng kỹ năng, không cần đặt ra ô F, không đụng chuột. Không có kỹ năng thì bấm ô F o_du_phong (0 = không bấm).
    Trả về "skill", "phim" hoặc "".
    """
    dung = trong_cua_so(
        "ActionSkill",
        "local id = -1 "
        'for i = 0, GetActionNum("skill") - 1 do local a = EnumAction(i, "skill") '
        f"if a and a:GetDefineID() == {ma_dinh_nghia} then id = a:GetID() break end end "
        'if id == -1 then return "" end '
        "local nut = ActionSkill_ZhaoshiTarget nut:SetActionItem(id) nut:DoAction() "
        'if not IsWindowShow("ActionSkill") then nut:SetActionItem(-1) end return "skill"')
    phim = (trong_cua_so("MainMenuBar", f'Button_Action{o_du_phong}:DoAction() return "phim"') if o_du_phong
            else 'return ""')
    return (f"local dung = function() {dung} end local kq = dung() "
            f"if kq == \"\" then local phim = function() {phim} end kq = phim() end return kq")


def ma_co_ky_nang(ma_dinh_nghia):
    return ('for i = 0, GetActionNum("skill") - 1 do local a = EnumAction(i, "skill") '
            f'if a and a:GetDefineID() == {ma_dinh_nghia} then return "1" end end return "0"')


MA_DUNG_KY_NANG_BUFF = ma_dung_ky_nang(MA_KY_NANG_BUFF_MAU)
MA_BAM_PHIM_BUFF = trong_cua_so("MainMenuBar", f'Button_Action{PHIM_BUFF_DU_PHONG}:DoAction() return "phim"')
MA_DUNG_AN_DON = (f"if not DataPool:IsCanDoAction() then return \"ban\" end "
                  f"local ky_nang = function() {ma_dung_ky_nang(MA_KY_NANG_AN_DON)} end return ky_nang()")


def ma_buff(ma_id):
    """Lua chọn ma_id (đồng đội / mình) rồi dùng kỹ năng buff máu, không có kỹ năng thì bấm phím dự phòng."""
    return (f"if not DataPool:IsCanDoAction() then return \"\" end SetMainTargetFromList({ma_id}, true, false) "
            f"local ky_nang = function() {MA_DUNG_KY_NANG_BUFF} end local kq = ky_nang() "
            f"if kq == \"\" then local phim = function() {MA_BAM_PHIM_BUFF} end kq = phim() end return kq")

DoiTuong = namedtuple("DoiTuong", "id id_client ten x y hp guid", defaults=(-1,))
# ke_danh: id server người chơi vừa đánh mình (-1 nếu chưa ai hoặc người đó không ở gần); id_minh: id server của mình
CanhQuanh = namedtuple("CanhQuanh", "vi_tri mau cac_quai cac_nguoi ke_danh id_minh")


class LoiChienDau(Exception):
    pass


def cai_dat_chien_dau(cai_dat_nhan_vat):
    """Cài đặt chiến đấu của nhân vật, thêm giá trị mặc định cho khóa chưa có."""
    cai_dat = dict(MAC_DINH, diem=dict(MAC_DINH["diem"]))
    cai_dat.update({khoa: gia_tri for khoa, gia_tri in cai_dat_nhan_vat.get("chien_dau", {}).items()
                    if khoa in MAC_DINH})
    cai_dat["cac_phim_skill"] = sorted({phim for phim in cai_dat["cac_phim_skill"] if phim in CAC_PHIM_SKILL})
    for khoa, toi_da in (("phan_tram_buff", 99), ("phan_tram_an_don", 99), ("hoan_hi_toi_thieu", 100)):
        try:
            cai_dat[khoa] = min(max(int(cai_dat[khoa]), 1), toi_da)
        except (TypeError, ValueError):
            cai_dat[khoa] = MAC_DINH[khoa]
    return cai_dat


def cac_phim_can_bam(cai_dat):
    """Các ô trên thanh kỹ năng được bấm lần lượt: F1 (nếu bật) rồi các ô F2-F10 đã tích."""
    return ([1] if cai_dat["dung_f1"] else []) + cai_dat["cac_phim_skill"]


def khoang_cach(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


class BoNho:
    """Đọc bộ nhớ tiến trình game (chỉ đọc)."""

    def __init__(self, pid):
        self.tay_cam = kernel32.OpenProcess(QUYEN_DOC, False, pid)
        if not self.tay_cam:
            raise LoiChienDau(f"không mở được tiến trình game {pid} (lỗi {ctypes.get_last_error()})")
        self.lop_theo_vtable = {}

    def dong(self):
        kernel32.CloseHandle(self.tay_cam)

    def doc(self, dia_chi, so_byte):
        dem = ctypes.create_string_buffer(so_byte)
        da_doc = ctypes.c_size_t()
        if not kernel32.ReadProcessMemory(self.tay_cam, dia_chi, dem, so_byte, ctypes.byref(da_doc)) \
                or da_doc.value != so_byte:
            raise LoiChienDau(f"không đọc được bộ nhớ game ở {dia_chi:#x}")
        return dem.raw

    def so(self, dia_chi):
        return struct.unpack("<I", self.doc(dia_chi, 4))[0]

    def kiem_tra_ban_game(self):
        for dia_chi, mau in MAU_CODE.items():
            if self.doc(dia_chi, len(mau) // 2) != bytes.fromhex(mau):
                raise LoiChienDau(f"bản Game.exe này khác bản đã dịch ngược (code ở {dia_chi:#x}), "
                                  "chưa hỗ trợ tự đánh")

    def loai_doi_tuong(self, doi_tuong):
        """"quai" (quái / NPC / trân thú), "nguoi" (người chơi khác) hoặc None."""
        vtable = self.so(doi_tuong)
        if vtable not in self.lop_theo_vtable:
            ham = self.doc(self.so(vtable + LECH_HAM_LAY_LOP), len(HAM_LOP_PLAYER_NPC))
            self.lop_theo_vtable[vtable] = {HAM_LOP_PLAYER_NPC: "quai", HAM_LOP_PLAYER_OTHER: "nguoi"}.get(ham)
        return self.lop_theo_vtable[vtable]

    def doc_doi_tuong(self, doi_tuong):
        """DoiTuong, hoặc None nếu là đối tượng rỗng (chưa dùng tới, không có tên) hay trân thú có chủ."""
        khoi = self.doc(doi_tuong + LECH_ID_CLIENT, LECH_Y + 4 - LECH_ID_CLIENT)
        id_client, ma_id = struct.unpack_from("<ii", khoi, 0)
        x = struct.unpack_from("<f", khoi, LECH_X - LECH_ID_CLIENT)[0]
        y = struct.unpack_from("<f", khoi, LECH_Y - LECH_ID_CLIENT)[0]
        du_lieu = self.so(doi_tuong + LECH_DU_LIEU)
        if not du_lieu:
            return None
        bang = self.so(du_lieu + 4)
        khoi = self.doc(bang, LECH_CHU_2 + 4)
        chu, chu_2 = struct.unpack_from("<i", khoi, LECH_CHU)[0], struct.unpack_from("<i", khoi, LECH_CHU_2)[0]
        if chu != -1 or chu_2 != -1:
            return None
        hp = struct.unpack_from("<f", khoi, LECH_HP)[0]
        # std::string: con trỏ / 16 byte chữ ở +4, độ dài +0x14, sức chứa +0x18
        do_dai, suc_chua = struct.unpack_from("<II", khoi, LECH_TEN + 0x14)
        if not 0 < do_dai <= DO_DAI_TEN_TOI_DA or not 0 <= hp <= 1:
            return None
        if suc_chua >= 16:
            ten = self.doc(struct.unpack_from("<I", khoi, LECH_TEN + 4)[0], do_dai)
        else:
            ten = khoi[LECH_TEN + 4:LECH_TEN + 4 + do_dai]
        return DoiTuong(ma_id, id_client, ten, x, y, hp, struct.unpack_from("<i", khoi, LECH_GUID)[0])

    def doc_quanh_minh(self):
        """CanhQuanh: vị trí và % máu của mình, quái / NPC không có chủ, người chơi khác, kẻ vừa đánh mình."""
        quan_ly = self.so(CON_TRO_QUAN_LY_DOI_TUONG)
        minh = self.so(quan_ly + LECH_NHAN_VAT_CUA_MINH)
        if not minh:
            raise LoiChienDau("chưa có nhân vật trong game")
        vi_tri = struct.unpack("<ff", self.doc(minh + LECH_X, 4) + self.doc(minh + LECH_Y, 4))
        id_minh = struct.unpack("<i", self.doc(minh + LECH_ID, 4))[0]
        bang_minh = self.so(self.so(minh + LECH_DU_LIEU) + 4)
        mau_minh = struct.unpack("<f", self.doc(bang_minh + LECH_HP, 4))[0]
        guid_ke_danh = struct.unpack("<i", self.doc(bang_minh + LECH_KE_DANH, 4))[0]

        dau = self.so(quan_ly + LECH_CAY_DOI_TUONG)
        theo_loai, can_xem, so_nut = {"quai": [], "nguoi": []}, [self.so(dau + 4)], 0
        while can_xem and so_nut < SO_NUT_TOI_DA:
            so_nut += 1
            nut = can_xem.pop()
            try:
                khoi = self.doc(nut, 0x16)
                if khoi[0x15]:
                    continue
                trai, _, phai, _, doi_tuong = struct.unpack_from("<5I", khoi)
                can_xem += [trai, phai]
                loai = self.loai_doi_tuong(doi_tuong) if doi_tuong and doi_tuong != minh else None
                if loai is None:
                    continue
                doi_tuong = self.doc_doi_tuong(doi_tuong)
            except LoiChienDau:
                continue  # game vừa xóa đối tượng này trong lúc đọc
            if doi_tuong and doi_tuong.id != -1:
                theo_loai[loai].append(doi_tuong)
        ke_danh = next((nguoi.id for nguoi in theo_loai["nguoi"] if guid_ke_danh != -1 and nguoi.guid == guid_ke_danh),
                       -1)
        return CanhQuanh(vi_tri, mau_minh, theo_loai["quai"], theo_loai["nguoi"], ke_danh, id_minh)


class ChienDau:
    """Trạng thái tự đánh của một cửa sổ game; buoc() được gọi đều đặn ở luồng chiến đấu."""

    def __init__(self, lua, in_log):
        self.lua = lua
        self.in_log = in_log
        self.bo_nho = None
        self.muc_tieu = None
        self.ten_muc_tieu = b""
        self.luc_chon = 0.0
        self.mau_muc_tieu = 1.0
        self.luc_mau_giam = 0.0
        self.da_danh_lai = False
        self.cho_xac_nhan = None
        self.bo_qua_den = {}
        self.lan_hong_theo_ten = {}
        self.ten_bo_qua = set()
        self.khong_bo_qua_ten = False
        self.chi_danh_ten = ()
        self.da_lua = set()
        self.dang_lua = None
        self.luc_bam_phim = 0.0
        self.thu_tu_phim = 0
        self.luc_skill_pet = 0.0
        self.luc_chay_ve = 0.0
        self.luc_xem_thu_cuoi = 0.0
        self.muc_tieu_la_nguoi = False
        self.ke_danh = -1
        self.nguoi_da_bao = None
        self.luc_bi_danh = 0.0
        self.mau_minh_truoc = None
        self.che_do_pk = 0
        self.luc_doc_pk = 0.0
        self.luc_buff = 0.0
        self.mo_ta_buff = ""
        self.da_bao_phim_buff = False
        self.luc_an_don = 0.0
        self.dang_an_than = False
        self.da_bao_khong_co_an_don = False

    def dong(self):
        if self.bo_nho:
            self.bo_nho.dong()
            self.bo_nho = None

    def _bo_nho(self):
        if self.bo_nho is None:
            bo_nho = BoNho(self.lua.pid)
            try:
                bo_nho.kiem_tra_ban_game()
            except LoiChienDau:
                bo_nho.dong()
                raise
            self.bo_nho = bo_nho
        return self.bo_nho

    def bo_nho_game(self):
        """BoNho đọc bộ nhớ game (đã kiểm tra đúng bản Game.exe)."""
        try:
            return self._bo_nho()
        except LoiChienDau:
            self.dong()
            raise

    def bo_muc_tieu(self):
        self.muc_tieu = None
        self.cho_xac_nhan = None
        self.dang_lua = None
        self.muc_tieu_la_nguoi = False

    def _xac_nhan(self, cac_quai_theo_id, cac_nguoi_theo_id):
        """
        Lần chọn trước có thành mục tiêu thật không. Game từ chối NPC / quái không đánh được; người chơi thì chọn
        được cả người phe bạn nên xem thêm tên đỏ / trắng.
        """
        ma_id, ten, la_nguoi = self.cho_xac_nhan
        self.cho_xac_nhan = None
        ten_game = self.lua.chay('if not Target:IsPresent() then return "" end return Target:GetName()')
        if la_nguoi:
            # RELATIVE không dùng được: người cùng nhóm cũng trả về 0. Đánh không trúng thì _buoc_pk tự bỏ qua.
            if ten_game == ten:
                return True
            if ma_id in cac_nguoi_theo_id:
                self.bo_qua_den[ma_id] = time.time() + GIAY_BO_QUA_QUAI_KHONG_DANH_DUOC
                self.in_log(f"Tự đánh: không chọn được người chơi {giai_ma(ten)} "
                            f"(mục tiêu đang là {giai_ma(ten_game) or 'không có'}), bỏ qua "
                            f"{GIAY_BO_QUA_QUAI_KHONG_DANH_DUOC:.0f} giây")
            return False
        if ten_game == ten:
            self.lan_hong_theo_ten.pop(ten, None)
            return True
        quai = cac_quai_theo_id.get(ma_id)
        if quai is None or quai.hp < MAU_DAY:
            return False  # quái đã chết / đang bị người khác đánh: đánh được, chỉ là chọn không kịp
        if self.khong_bo_qua_ten:
            return False  # Phó bản: NPC hóa quái cùng tên, chọn lại ở lượt sau
        self.bo_qua_den[ma_id] = time.time() + GIAY_BO_QUA_QUAI_KHONG_DANH_DUOC
        self.lan_hong_theo_ten[ten] = self.lan_hong_theo_ten.get(ten, 0) + 1
        if self.lan_hong_theo_ten[ten] >= SO_LAN_CHON_HONG_THI_BO_TEN:
            self.ten_bo_qua.add(ten)
            self.in_log(f"Tự đánh: bỏ qua {giai_ma(ten)} (game không cho chọn làm mục tiêu, có thể là NPC)")
        return False

    @staticmethod
    def _ma_danh(doi_tuong, la_nguoi):
        """
        Lua chọn và đánh doi_tuong. Người chơi mà game không coi là địch thì SetMainTargetFromList(id, false, true)
        không chọn: chọn lại kiểu bạn bè (luôn chọn được) rồi các phím kỹ năng đánh vào mục tiêu đó.
        """
        ma = f"SetMainTargetFromList({doi_tuong.id}, false, true)"
        if la_nguoi:
            ma += (f' if not Target:IsPresent() or tonumber(Target:GetData("NPCID")) ~= {doi_tuong.id_client} '
                   f"then SetMainTargetFromList({doi_tuong.id}, true, false) end")
        return ma

    def _chon(self, quai, la_nguoi=False):
        self.lua.chay(self._ma_danh(quai, la_nguoi))
        self.muc_tieu, self.ten_muc_tieu, self.muc_tieu_la_nguoi = quai.id, quai.ten, la_nguoi
        self.luc_chon = self.luc_mau_giam = time.time()
        self.mau_muc_tieu = quai.hp
        self.da_danh_lai = False
        self.cho_xac_nhan = (quai.id, quai.ten, la_nguoi)

    def _theo_doi_bi_danh(self, canh, bay_gio):
        if canh.ke_danh != self.ke_danh:
            self.ke_danh = canh.ke_danh
            if canh.ke_danh != -1:
                self.luc_bi_danh = bay_gio
        elif canh.ke_danh != -1 and self.mau_minh_truoc is not None and canh.mau < self.mau_minh_truoc:
            self.luc_bi_danh = bay_gio
        self.mau_minh_truoc = canh.mau

    def ke_danh_gan_day(self):
        """Id server người chơi đang đánh mình (mới đánh hoặc mình mới mất máu trong 10 giây), None nếu không có."""
        if self.ke_danh == -1 or time.time() - self.luc_bi_danh > GIAY_NHO_KE_DANH:
            return None
        return self.ke_danh

    def cap_nhat_bi_danh(self):
        """Cập nhật kẻ đang đánh mình khi không tự đánh (để cả nhóm vẫn biết mà đánh giúp)."""
        self._theo_doi_bi_danh(self._doc_quanh_minh(), time.time())

    def _dang_bat_pk(self, bay_gio):
        if bay_gio - self.luc_doc_pk >= GIAY_DOC_LAI_CHE_DO_PK:
            self.luc_doc_pk = bay_gio
            try:
                self.che_do_pk = int(float(self.lua.chay("return tostring(Player:GetPKMode())")))
            except ValueError:
                self.che_do_pk = 0
        return self.che_do_pk in CHE_DO_PK_DANH_NGUOI

    def _theo_doi_mau(self, quai, bay_gio):
        """
        Máu mục tiêu không giảm 4 giây thì ra lệnh đánh lại. Trả về True nếu không giảm quá 10 giây (bị kẹt).
        So với lần đọc trước chứ không phải mức thấp nhất: người chơi hồi máu rồi bị đánh tiếp vẫn là đang trúng.
        """
        giam = quai.hp < self.mau_muc_tieu
        self.mau_muc_tieu = quai.hp
        if giam:
            self.luc_mau_giam, self.da_danh_lai = bay_gio, False
            return False
        if bay_gio - self.luc_mau_giam >= GIAY_BO_QUA_KHI_MAU_KHONG_GIAM:
            return True
        if bay_gio - self.luc_mau_giam >= GIAY_DANH_LAI_KHI_MAU_KHONG_GIAM and not self.da_danh_lai:
            self.lua.chay(self._ma_danh(quai, self.muc_tieu_la_nguoi))
            self.da_danh_lai = True
        return False

    def doc_muc_tieu_dang_chon(self):
        """Id server của quái nhân vật này đang chọn (dùng khi nhân vật là Key), None nếu không chọn quái."""
        ket_qua = self.lua.chay('if not Target:IsPresent() then return "" end return tostring(Target:GetData("NPCID"))')
        try:
            id_client = int(float(ket_qua))
        except ValueError:
            return None
        cac_quai = self._doc_quanh_minh().cac_quai
        return next((quai.id for quai in cac_quai if quai.id_client == id_client and quai.hp > 0), None)

    def doc_nguoi_dang_chon(self):
        """Id server người chơi phe địch (tên đỏ) nhân vật này đang chọn (khi là trưởng nhóm), None nếu không có."""
        ket_qua = self.lua.chay('if not Target:IsPresent() then return "" end '
                                'return tostring(Target:GetData("NPCID")) .. "\\t" .. tostring(Target:GetData("RELATIVE"))')
        id_client, _, quan_he = ket_qua.partition(b"\t")
        try:
            id_client = int(float(id_client))
        except ValueError:
            return None
        if quan_he.strip() in (b"2", b"2.0"):
            return None
        cac_nguoi = self._doc_quanh_minh().cac_nguoi
        return next((nguoi.id for nguoi in cac_nguoi if nguoi.id_client == id_client and nguoi.hp > 0), None)

    def _doc_quanh_minh(self):
        try:
            return self._bo_nho().doc_quanh_minh()
        except LoiChienDau:
            self.dong()
            raise

    def _danh_duoc(self, quai, bay_gio):
        if self.chi_danh_ten and chuan_hoa(giai_ma(quai.ten)) not in self.chi_danh_ten:
            return False
        return quai.hp > 0 and quai.ten not in self.ten_bo_qua and self.bo_qua_den.get(quai.id, 0) <= bay_gio

    def _chon_muc_tieu_moi(self, cac_quai, vi_tri, cai_dat):
        """Chọn quái gần nhất (ưu tiên quái đã lùa). Trả về False nếu quanh đó không còn quái."""
        if cai_dat["lua_quai"]:
            self.da_lua &= {quai.id for quai in cac_quai if quai.hp > 0}
            if len(self.da_lua) < cai_dat["so_quai_lua"]:
                chua_lua = [quai for quai in cac_quai if quai.id not in self.da_lua and quai.hp >= MAU_DAY]
                if chua_lua:
                    quai = min(chua_lua, key=lambda q: khoang_cach(vi_tri, (q.x, q.y)))
                    self._chon(quai)
                    self.da_lua.add(quai.id)
                    self.dang_lua = quai.id
                    return True
            da_lua = [quai for quai in cac_quai if quai.id in self.da_lua]
            if da_lua:
                cac_quai = da_lua
        if not cac_quai:
            return False
        self._chon(min(cac_quai, key=lambda q: khoang_cach(vi_tri, (q.x, q.y))))
        return True

    def _ma_dung_ky_nang(self, cai_dat, bay_gio):
        """Đoạn Lua bấm phím / dùng kỹ năng trân thú tới lượt, "" nếu chưa tới lượt."""
        ma = []
        cac_phim = cac_phim_can_bam(cai_dat)
        if cac_phim and bay_gio - self.luc_bam_phim >= GIAY_GIUA_HAI_LAN_BAM_PHIM:
            # Game không cho Lua biết kỹ năng đã hồi chưa, nên mỗi lần chỉ bấm một ô, lần lượt từng ô.
            phim = cac_phim[self.thu_tu_phim % len(cac_phim)]
            self.thu_tu_phim += 1
            self.luc_bam_phim = bay_gio
            ma.append(trong_cua_so("MainMenuBar",
                                   f"if DataPool:IsCanDoAction() then Button_Action{phim}:DoAction() end"))
        if cai_dat["dung_skill_pet"] and bay_gio - self.luc_skill_pet >= GIAY_GIUA_HAI_LAN_DUNG_SKILL_PET:
            self.luc_skill_pet = bay_gio
            ma.append(trong_cua_so(
                "ActionSkill",
                "local nut = ActionSkill_ZhaoshiTarget "
                "for i = 0, (Pet:GetPetSkillBarItemCount() or 0) - 1 do "
                "local a = Pet:EnumPetSkillBarItem(i) "
                "if a and a:GetID() ~= 0 then nut:SetActionItem(a:GetID()) nut:DoAction() end end "
                'if not IsWindowShow("ActionSkill") then nut:SetActionItem(-1) end'))
        # Mỗi đoạn trong_cua_so kết thúc bằng return, nên mỗi đoạn chạy trong một hàm riêng.
        return " ".join(f"local ham{i} = function() {doan} end ham{i}()" for i, doan in enumerate(ma))

    def _dung_ky_nang(self, cai_dat, bay_gio):
        """Gọi mỗi lượt đang đánh: xuống thú cưỡi (nếu bật) rồi bấm kỹ năng tới lượt."""
        ma = self._ma_dung_ky_nang(cai_dat, bay_gio)
        if cai_dat["xuong_thu"] and bay_gio - self.luc_xem_thu_cuoi >= GIAY_GIUA_HAI_LAN_XEM_THU_CUOI:
            self.luc_xem_thu_cuoi = bay_gio
            ma = f'local xuong = "" {MA_XUONG_THU} {ma} return xuong'
        if ma:
            xuong = self.lua.chay(ma)
            if xuong:
                self.in_log(f"Tự đánh: xuống {giai_ma(xuong)} để đánh")

    def _buoc_theo_key(self, theo_id, muc_tieu_key, cai_dat, bay_gio):
        """Đánh đúng con quái Key đang chọn (không xét bán kính). Key chưa chọn quái thì đánh nốt con đang đánh."""
        quai = theo_id.get(muc_tieu_key)
        if quai is not None and self._danh_duoc(quai, bay_gio):
            if quai.id != self.muc_tieu:
                self.dang_lua = None
                self._chon(quai)
            else:
                self._theo_doi_mau(quai, bay_gio)
        else:
            dang_danh = theo_id.get(self.muc_tieu)
            if dang_danh is None or dang_danh.hp <= 0:
                self.bo_muc_tieu()
                return "Chờ Key chọn quái" if muc_tieu_key is None else "Chưa thấy quái Key đang đánh"
            self._theo_doi_mau(dang_danh, bay_gio)
        self._dung_ky_nang(cai_dat, bay_gio)
        return f"Đánh theo Key: {giai_ma(self.ten_muc_tieu)}"

    def _buoc_pk(self, canh, cai_dat, pk, bay_gio, chi_danh_tra=False):
        """
        Đang bật PK: đánh người chơi, ưu tiên người trưởng nhóm đang đánh, rồi kẻ đang đánh mình, rồi kẻ đang đánh
        đồng đội, rồi người gần nhất mà mình thấy được (không xét bán kính: có người thì không đánh quái).
        chi_danh_tra=True (hòa bình / thiện ác / bang phái): chỉ đánh trả kẻ đang đánh mình.
        Trả về mô tả, hoặc None nếu không có người chơi nào để đánh (khi đó đánh quái như thường).
        """
        ban_be = pk.get("ban_be", set())
        ke_danh_nhom = pk.get("ke_danh_nhom", [])
        muc_tieu_truong = pk.get("muc_tieu_truong")
        ke_danh_minh = self.ke_danh_gan_day()

        def uu_tien(nguoi):
            if nguoi.id == muc_tieu_truong:
                return -1, 0
            if nguoi.id == ke_danh_minh:
                return 0, 0
            if nguoi.id in ke_danh_nhom:
                return 1, ke_danh_nhom.index(nguoi.id)
            return 2, khoang_cach(canh.vi_tri, (nguoi.x, nguoi.y))

        cac_muc_tieu = {}
        for nguoi in canh.cac_nguoi:
            if nguoi.hp > 0 and self.bo_qua_den.get(nguoi.id, 0) <= bay_gio \
                    and chuan_hoa(giai_ma(nguoi.ten)) not in ban_be \
                    and (not chi_danh_tra or nguoi.id == ke_danh_minh):
                cac_muc_tieu[nguoi.id] = (uu_tien(nguoi), nguoi)
        tot_nhat = min(cac_muc_tieu.values(), key=lambda cap: cap[0], default=None)
        hien_tai = cac_muc_tieu.get(self.muc_tieu) if self.muc_tieu_la_nguoi else None

        if hien_tai and (tot_nhat is None or hien_tai[0][0] <= tot_nhat[0][0]):
            (loai, _), nguoi = hien_tai
            if self._theo_doi_mau(nguoi, bay_gio):
                if loai == 2:
                    self.bo_qua_den[nguoi.id] = bay_gio + GIAY_BO_QUA_QUAI_KHONG_DANH_DUOC
                    self.bo_muc_tieu()
                    self.in_log(f"Tự đánh: {GIAY_BO_QUA_KHI_MAU_KHONG_GIAM:.0f} giây máu {giai_ma(nguoi.ten)} không "
                                f"giảm (đánh không trúng), bỏ qua {GIAY_BO_QUA_QUAI_KHONG_DANH_DUOC:.0f} giây")
                    return f"Bỏ qua {giai_ma(nguoi.ten)} (đánh không trúng)"
                self.luc_mau_giam, self.da_danh_lai = bay_gio, False  # kẻ đánh mình / đồng đội: cứ đánh tiếp
        elif tot_nhat:
            (loai, _), nguoi = tot_nhat
            self.dang_lua = None
            self._chon(nguoi, la_nguoi=True)
            if nguoi.id != self.nguoi_da_bao:
                self.nguoi_da_bao = nguoi.id
                self.in_log({-1: "Đánh theo trưởng nhóm:", 0: "Bị người chơi đánh, đánh trả",
                             1: "Đánh giúp đồng đội:", 2: "PK"}[loai] + f" {giai_ma(nguoi.ten)}")
        else:
            if self.muc_tieu_la_nguoi:
                self.bo_muc_tieu()
            self.nguoi_da_bao = None
            return None
        self._dung_ky_nang(cai_dat, bay_gio)
        return {-1: "Đánh theo trưởng nhóm:", 0: "Đánh trả", 1: "Đánh giúp đồng đội:", 2: "PK"}[loai] \
            + f" {giai_ma(nguoi.ten)}"

    def an_don(self, cai_dat):
        """
        Đang bị người chơi (còn ở gần) đánh mà máu mình dưới phan_tram_an_don% thì dùng Ẩn Độn Sơ Cấp; đang ẩn thân
        thì đứng yên chờ hồi máu (đánh là lộ). Trả về mô tả nếu lượt này không được đánh / buff, None nếu như thường.
        """
        bay_gio = time.time()
        canh = self._doc_quanh_minh()
        self._theo_doi_bi_danh(canh, bay_gio)
        if canh.mau <= 0:
            self.dang_an_than = False
            return None
        nguong = cai_dat["phan_tram_an_don"] / 100
        if canh.mau >= nguong and not self.dang_an_than:
            return None
        self.dang_an_than = self.lua.chay(MA_DANG_AN_THAN) == b"1"
        if self.dang_an_than:
            if canh.mau >= MAU_HET_AN_THAN:
                return None
            self.bo_muc_tieu()
            return f"Đang ẩn thân, chờ hồi máu ({canh.mau * 100:.0f}%)"
        ke_danh = self.ke_danh_gan_day()
        if canh.mau >= nguong or ke_danh is None or all(nguoi.id != ke_danh for nguoi in canh.cac_nguoi) \
                or bay_gio - self.luc_an_don < GIAY_GIUA_HAI_LAN_AN_DON:
            return None
        self.luc_an_don = bay_gio
        ket_qua = self.lua.chay(MA_DUNG_AN_DON)
        if ket_qua != b"skill":
            if not ket_qua and not self.da_bao_khong_co_an_don:
                self.da_bao_khong_co_an_don = True
                self.in_log(f"Ẩn độn: nhân vật không có kỹ năng {TEN_KY_NANG_AN_DON}")
            return None
        self.bo_muc_tieu()
        self.dang_an_than = True  # lượt sau xem buff ẩn thân dù máu đã hồi quá ngưỡng
        self.in_log(f"Máu còn {canh.mau * 100:.0f}% khi bị PK: dùng {TEN_KY_NANG_AN_DON}")
        return f"Dùng {TEN_KY_NANG_AN_DON} ({canh.mau * 100:.0f}% máu)"

    def buff_mau(self, cai_dat, dong_doi):
        """
        Nga My: mình hoặc đồng đội (tên chuẩn hóa trong dong_doi, phải thấy được) máu dưới phan_tram_buff% thì chọn
        người máu thấp nhất rồi dùng Thanh Tâm Phổ Thiện Chú (không có kỹ năng thì bấm F8).
        Trả về mô tả nếu đang buff (lượt này không đánh), None nếu không cần / chưa tới lúc buff.
        """
        bay_gio = time.time()
        if bay_gio - self.luc_buff < GIAY_VAN_CONG_BUFF:
            return self.mo_ta_buff
        if bay_gio - self.luc_buff < GIAY_GIUA_HAI_LAN_BUFF:
            return None
        canh = self._doc_quanh_minh()
        if canh.mau <= 0:
            return None
        nguong = cai_dat["phan_tram_buff"] / 100
        can_buff = [(nguoi.hp, nguoi.id, giai_ma(nguoi.ten)) for nguoi in canh.cac_nguoi
                    if 0 < nguoi.hp < nguong and chuan_hoa(giai_ma(nguoi.ten)) in dong_doi]
        if canh.mau < nguong:
            can_buff.append((canh.mau, canh.id_minh, "mình"))
        if not can_buff:
            return None
        mau, ma_id, ten = min(can_buff)
        cach = self.lua.chay(ma_buff(ma_id))
        if not cach:
            return None
        if cach == b"phim" and not self.da_bao_phim_buff:
            self.da_bao_phim_buff = True
            self.in_log(f"Buff máu: không thấy kỹ năng {TEN_KY_NANG_BUFF_MAU}, bấm F{PHIM_BUFF_DU_PHONG}")
        self.bo_muc_tieu()  # mục tiêu đang là người được buff: lượt đánh sau chọn lại kẻ địch
        self.luc_buff = bay_gio
        self.mo_ta_buff = f"Buff máu cho {ten} ({mau * 100:.0f}%)"
        return self.mo_ta_buff

    def buoc(self, cai_dat, map_hien_tai, theo_key=False, muc_tieu_key=None, pk=None):
        """
        Một lượt tự đánh. Trả về mô tả ngắn việc đang làm.
        theo_key=True: đánh con quái có id server muc_tieu_key (con Key đang chọn, None nếu Key chưa chọn con nào).
        pk = {"ban_be": {tên chuẩn hóa không được đánh}, "ke_danh_nhom": [id server kẻ đang đánh đồng đội, mới nhất
        trước], "muc_tieu_truong": id server người trưởng nhóm đang chọn hoặc None} - dùng khi đang bật PK đội /
        PK cá nhân và bật "uu_tien_nguoi_choi".
        """
        canh = self._doc_quanh_minh()
        bay_gio = time.time()
        self._theo_doi_bi_danh(canh, bay_gio)
        vi_tri, cac_quai = canh.vi_tri, canh.cac_quai
        if canh.mau <= 0:
            self.bo_muc_tieu()
            return "Đã chết"
        theo_id = {quai.id: quai for quai in cac_quai}
        if self.ten_bo_qua:
            bi_danh = {quai.ten for quai in cac_quai if quai.hp < MAU_DAY} & self.ten_bo_qua
            for ten in bi_danh:
                self.ten_bo_qua.discard(ten)
                self.lan_hong_theo_ten.pop(ten, None)
                self.in_log(f"Tự đánh: {giai_ma(ten)} bị mất máu / chết nên là quái đánh được, đánh lại")

        if self.cho_xac_nhan and not self._xac_nhan(theo_id, {nguoi.id: nguoi for nguoi in canh.cac_nguoi}):
            self.bo_muc_tieu()
        if cai_dat["uu_tien_nguoi_choi"]:
            mo_ta = self._buoc_pk(canh, cai_dat, pk or {}, bay_gio, chi_danh_tra=not self._dang_bat_pk(bay_gio))
            if mo_ta:
                return mo_ta
        elif self.muc_tieu_la_nguoi:
            self.bo_muc_tieu()
        if theo_key:
            return self._buoc_theo_key(theo_id, muc_tieu_key, cai_dat, bay_gio)

        diem = cai_dat["diem"]
        quanh_diem = cai_dat["quanh_diem"] and diem["map"] and diem["map"] == map_hien_tai
        tam = (diem["x"], diem["y"]) if quanh_diem else vi_tri
        ban_kinh = cai_dat["ban_kinh"]
        trong_vung = [quai for quai in cac_quai if quai.hp > 0 and khoang_cach(tam, (quai.x, quai.y)) <= ban_kinh]

        muc_tieu = theo_id.get(self.muc_tieu)
        if muc_tieu is None or muc_tieu.hp <= 0 or muc_tieu not in trong_vung:
            self.bo_muc_tieu()
        elif self.dang_lua == muc_tieu.id and (muc_tieu.hp < MAU_DAY or bay_gio - self.luc_chon >= GIAY_TOI_DA_LUA_MOT_CON):
            self.bo_muc_tieu()  # con này đã bị đánh trúng (đã kéo theo) - sang con kế tiếp
        elif self._theo_doi_mau(muc_tieu, bay_gio):
            self.bo_qua_den[muc_tieu.id] = bay_gio + GIAY_BO_QUA_QUAI_KHONG_DANH_DUOC
            self.bo_muc_tieu()  # không tới được chỗ con quái (kẹt địa hình...)

        if self.muc_tieu is None:
            danh_duoc = [quai for quai in trong_vung if self._danh_duoc(quai, bay_gio)]
            if not self._chon_muc_tieu_moi(danh_duoc, vi_tri, cai_dat):
                if quanh_diem and khoang_cach(vi_tri, tam) > ban_kinh / 2 \
                        and bay_gio - self.luc_chay_ve >= GIAY_GIUA_HAI_LAN_CHAY_VE:
                    self.luc_chay_ve = bay_gio
                    self.lua.chay(f"AutoRunToTarget({diem['x']}, {diem['y']})")
                    return f"Chạy về [{diem['x']},{diem['y']}]"
                return "Không có quái trong vùng"

        self._dung_ky_nang(cai_dat, bay_gio)
        return f"{'Lùa' if self.dang_lua else 'Đánh'} {giai_ma(self.ten_muc_tieu)}"
