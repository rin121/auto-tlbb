"""
TỰ ĐI PHÓ BẢN PHIÊU MIỄU PHONG MỘT MÌNH (tab "Phó bản", cài riêng từng nhân vật).

Kịch bản ghi từ một vòng chơi tay:
    Đang ở map khác Đại Lý / Lạc Dương / Phiêu Miểu Phong: bấm ô F có kỹ năng về thành, chờ tới Đại Lý.
    Đại Lý     : NPC "Di Chuyển" -> "Bản Đồ Thành Thị" -> "Thành Thị Lạc Dương" -> sang Lạc Dương.
                 Máu dưới 50% khi đứng ở Đại Lý: tới NPC Di Chuyển mở hội thoại để hồi máu (trước khi dịch chuyển).
    Lạc Dương  : NPC "Trịnh Thanh Sương" -> "Khiêu chiến Phiêu Miểu Phong" -> vào phó bản.
    Phó bản  : 4 ải + boss (CAC_AI). Nói chuyện với NPC, chọn dòng, game đếm 5 giây rồi NPC hóa quái.
    Giết boss Lý Thu Thuỷ xong vẫn ở trong ải — không như Sát Tinh (game tự đưa ra map); phải bấm kỹ năng Quay về Đại Lý thành: xong một vòng.

Hết lượt PMP thì đi Thập Nhị Sát Tinh (ghi từ một vòng đội trưởng dẫn đội 01:34):
    Đại Lý -> Lạc Dương (Di Chuyển như trên), rồi NPC "Sát Tinh" -> "Khiêu chiến Thập Nhị Sát Tinh" -> ... -> Lôi đài sinh tử.
    Lôi đài  : chạy tới giữa (25, 32), các Sát Tinh lần lượt vào đánh. Khô Vinh Đại Sư đứng ở cửa (11, 34) không đánh.
    "Nhiệm vụ hoàn thành.Các hạ sẽ rời khỏi đây sau 15 giây!" rồi game tự đưa cả đội về Đại Lý: xong một vòng.

Đi tổ đội (tự dùng khi nhân vật có nhóm trong game; ghi từ một vòng đội trưởng dẫn 3 đội viên):
    Trước khi vào phó bản: mỗi thành viên tự về Đại Lý, Di Chuyển sang Lạc Dương và chạy tới NPC.
    Trong Phiêu Miểu Phong / lôi đài: đội trưởng bấm Theo đội và dẫn đúng script (như bản cũ); chỉ trưởng nói NPC vào ải.
    Đang theo đội thì đội viên không đánh được ("Không cho phép tiến hành thao tác này"): đội trưởng nói chuyện
    NPC, chọn khiêu chiến xong rồi mới bỏ theo (cả đội cùng thoát) để từng người đánh quanh điểm của ải.
    Đội viên (luồng của nhân vật khác trong auto) xem doi.giai_doan để tự về thành và đánh theo vùng của đội trưởng.

Lệnh game:
    AutoRunToTarget(x, y) + SetAutoRunTargetNPCName(tên) : chạy tới NPC, tới nơi tự mở hội thoại (AutoSearch.lua).
    DataPool:GetNPCEventList_Item(i)                       : các dòng của hội thoại đang mở (Quest.lua).
    QuestFrameOptionClicked(-1, scriptId, extra)          : như bấm một dòng (QuestOption_Clicked, Quest.lua).
    DebugListBox_Update(chữ)                               : dòng thông báo hệ thống ("Cuộc chiến bắt đầu"...).
    Player:TeamFrame_AskTeamFollow() / Player:StopFollow() : nút Theo đội / Bỏ theo (TeamFrame.lua).
    Player:InTeamFollowMode()                              : đang theo đội.
Đánh nhau do luồng chiến đấu làm: dat_vung_danh((x, y, bán kính)) bật đánh quanh điểm đó, dat_vung_danh(None) tắt.
"""
import re
import threading
import time
from collections import namedtuple
from datetime import date

import cau_hinh
from auto_chuyen_sinh import chuan_hoa
from bang_ma_viscii import giai_ma
from chien_dau import (KY_NANG_KY_THUAT, KY_NANG_VE_THANH, MA_XUONG_THU, ChienDau, LoiChienDau, khoang_cach,
                       ma_co_ky_nang, ma_dung_ky_nang_theo_dinh_nghia)
from dang_nhap import bo_dau, chuoi_lua, dang_hien, trong_cua_so
from lua_game import LoiLua
from tu_dung_vat_pham import LoiVatPham, TiemKNB, TuDungCanKhonHo

MAP_DAI_LY = "Đại Lý"
MAP_LAC_DUONG = "Lạc Dương"
MAP_LAU_LAN = "Lâu Lan"  # map cũ (trước khi NPC chuyển sang Lạc Dương), vẫn nhận để về thành
MAP_PMP = "Phiêu Miểu Phong"
MAP_SAT_TINH = "Lôi đài sinh tử"
MO_TA = "Phó bản PMP"

# Ghi tay caychay10 17/10/2026: Di Chuyển Phụ Bản (111116,3333) -> Khiêu chiến Phiêu Miễu Phong (111116,4112); SÁT TINH (910112,1)->(910112,3); PMP Trình Thanh Sương (402263,1).
BUOC_VAO_SAT_TINH = (MAP_LAC_DUONG, "SÁT TINH", (156, 195), ((910112, 1), (910112, 3)), MAP_SAT_TINH)
# Sát Tinh vào ở (29-31, 32) rồi chạy tới giữa; bán kính nhỏ để không đánh Khô Vinh Đại Sư ở cửa (11-13, 34).
DIEM_SAT_TINH = (25, 32)
BAN_KINH_SAT_TINH = 8
THONG_BAO_SAT_TINH_XONG = "Nhiệm vụ hoàn thành"
THONG_BAO_SAT_TINH_VAO = "đã vào chiến đấu"
# Game báo Sát Tinh đầu tiên vào sau 5 giây; quá lâu chưa thấy thì vẫn bỏ theo để đánh.
GIAY_CHO_SAT_TINH_RA = 40

# (map, NPC, tọa độ NPC, các dòng chọn lần lượt (script, extra), map tới sau đó)
DONG_PMP_SO = (402276, 1)       # Sơ chiến Phiêu Miểu Phong (ghi tay caychay10)
DONG_PMP_THUONG = (402263, 1)    # Khiêu chiến Phiêu Miểu Phong

CAC_BUOC_VAO = (
    # Di Chuyển -> Phụ Bản -> Phiêu Miểu Phong: game đưa tới Lạc Dương cạnh Trình Thanh Sương / SÁT TINH.
    (MAP_DAI_LY, "Di Chuyển", (165, 156), ((111116, 3333), (111116, 4112)), MAP_LAC_DUONG),
    (MAP_LAC_DUONG, "Trình Thanh Sương", (163, 194), None, MAP_PMP),
)
# duong: các điểm gấp khúc chạy qua trước khi tới NPC; duong_danh: từ NPC tới điểm đánh (ghi từ vòng đội trưởng chơi
# tay 23:20). dan_doi: lên thú + Theo đội trước khi chạy tới NPC (boss thì đội viên đã đứng sẵn ở điểm đánh, đội
# trưởng đi một mình). giu_theo: chọn khiêu chiến khi cả đội còn theo, dẫn tới điểm đánh rồi mới bỏ theo
# (các ải khác cũng chỉ bỏ theo sau khi đã chọn khiêu chiến).
# an_than: quái ẩn thân giữa trận (biến mất khi còn máu, ~15-20 giây sau hiện lại đúng chỗ, máu giữ nguyên); lúc ẩn
# cả đội đứng chờ không đánh, chỉ tính chết khi thấy xác (ghi tay GaoDẻLâu 27/10/2026 sau khi server tăng máu boss).
Ai = namedtuple("Ai", "ten npc xy dong diem_danh cac_quai duong duong_danh dan_doi giu_theo an_than",
                defaults=(False,))
CAC_AI = (
    Ai("ải 1", "Cáp Đại Bá", (124, 86), (402270, 1), (124, 86), ("Cáp Đại Bá",),
       (), (), True, False),
    Ai("ải 2", "Tang Thổ Công", (41, 105), (402271, 1), (41, 105), ("Tang Thổ Công",),
       ((98, 96), (88, 109), (55, 113)), (), True, False, True),
    Ai("ải 3", "Ô Lão Đại", (117, 49), (402272, 1), (117, 49), ("Ô Lão Đại",),
       ((40, 66), (98, 60)), (), True, False),
    Ai("ải 4", "Phù Mẫn Nghi", (159, 54), (402273, 1), (124, 34),
       ("Trác Bất Phàm", "Bất Bình Đạo Nhân", "Nhậm Bình Sinh"),
       ((118, 59),), ((141, 46),), True, True),
    Ai("boss", "Ô Lão Đại", (95, 39), (402275, 1), (124, 35), ("Lý Thu Thuỷ",),
       (), (), False, False),
)

BAN_KINH_DANH = 15
GIAY_CHAY_TOI_NPC = 90
GIAY_CHAY_LAI = 2
GIAY_DUNG_CANH_NPC = 1
# Đội viên đứng chen quanh NPC nên đội trưởng khó tới sát 1 ô: trong khoảng này coi như đã đứng cạnh NPC.
KHOANG_MO_HOI_THOAI = 3
# Đứng gần NPC lâu chừng này mà hội thoại chưa mở: bỏ theo đội, chọn lại NPC làm mục tiêu.
GIAY_KET_CANH_NPC = 6
GIAY_KET_GIU_THEO = 20
GIAY_TOI_DA_CHO_THEO = 20
# Dịch chuyển xong: đội viên đang theo sang map mới chậm hơn đội trưởng vài giây.
GIAY_CHO_THEO_SANG_MAP = 15
KHOANG_LUI_KHOI_NPC = 6
GIAY_MO_HOI_THOAI = 15
GIAY_CHO_DOI_MAP = 20
GIAY_CHO_VE_THANH = 40
GIAY_DANH_MOT_AI = 120
# Đứng trong ải PMP không thấy quái / NPC để đánh: về Đại Lý chạy lại vòng (không tính xong vòng).
GIAY_TREO_PMP_KHONG_QUAI = 30
SO_LAN_CHAY_LAI_PMP_TREO = 5
# Ải quái ẩn thân: cả trận ~2 phút, mỗi lần ẩn ~15-20 giây. Máu quái còn giảm thì gia hạn thêm GIAY_DANH_MOT_AI.
GIAY_DANH_AI_AN_THAN = 300
GIAY_TREO_AI_AN_THAN = 60
# Quái ẩn thân biến mất mà lần cuối thấy còn ít máu hơn mức này (0..1) thì coi như đã chết (không kịp thấy xác).
MAU_COI_NHU_CHET = 0.03
# Game đếm ~5 giây sau khiêu chiến rồi NPC mới hóa quái; chưa thấy sống thì không được coi là đã chết.
GIAY_CHO_QUAI_XUAT_HIEN = 8
# Chọn khiêu chiến xong chờ chừng này rồi mới bỏ theo đội.
GIAY_CHO_BO_THEO = 2
# Ải dẫn đội tới điểm đánh (ải 4 -> chỗ chờ boss): tới nơi đứng chừng này rồi mới bỏ theo đội.
GIAY_DUNG_TRUOC_BO_THEO = 2
# Thông báo NPC Trình Thanh Sương khi cả đội đã đủ 20 lần khiêu chiến trong ngày.
GIAY_MOT_VONG = 15 * 60
GIAY_NGHI_KHI_LOI = 5 * 60
SO_LAN_THU = 3
# Mỗi step (ải) PMP: mỗi lần thử mở khiêu chiến tối đa GIAY_MOT_LAN_THU_AI giây; thử SO_LAN_THU_AI lần không được
# thì cả đội về Đại Lý chạy vòng mới.
GIAY_MOT_LAN_THU_AI = 60
SO_LAN_THU_AI = 2
# Đang gom đội quanh NPC mà đội trưởng ở map khác quá lâu (đã bị NPC đưa đi / về thành): thôi chờ.
GIAY_TOI_DA_TRUONG_SAI_MAP = 20
GIAY_SAU_CON_CUOI = 3
# Sau boss (step 5): game không tự về Đại Lý — chỉ kỹ năng Về thành; hoảng loạn có thể hủy animation, thử lại mỗi 3 giây.
GIAY_RETRY_VE_SAU_BOSS = 3
THONG_BAO_BAT_DAU_DANH = "Cuộc chiến bắt đầu"
GIAY_CHO_DOI_VIEN_VE = 90
GIAY_CHO_DOI_VIEN_TOI_MAP = 30
# Máy yếu: tên map đổi trước khi nhân vật load xong, bấm Theo đội ngay thì nhân vật load chậm không theo được.
GIAY_CHO_LOAD_MAP = 5
# Chờ đội viên tới gần NPC / map trước khi đội trưởng vào phó bản; mỗi vòng kiểm tra cách nhau 5 giây.
GIAY_CHO_GOM_DOI_RETRY = 5
GIAY_CHO_CO_DOI_VIEN = 10
GIAY_CHO_THEO_DOI = 8
GIAY_CHO_LEN_THU = 5
# Lên thú xong (và trước mỗi lần chạy tới NPC) bấm Theo đội lại cho tới khi cả đội vào theo; game chỉ cho người đứng
# gần đội trưởng vào theo, đội viên đứng yên chờ (không tự chạy đi).
GIAY_GIUA_HAI_LAN_MOI_THEO = 3
GIAY_TOI_DA_MOI_THEO = 15
GIAY_GIUA_HAI_LAN_TRIEU_TAP = 5
# Đội viên kẹt không tới được NPC Sát Tinh: chờ tối đa chừng này rồi đội trưởng vào với người đã tới.
GIAY_TOI_DA_CHO_GAN_NPC = 90
# Chạy qua điểm gấp khúc: tới gần chừng này thì sang điểm sau; đứng im quá lâu (kẹt) cũng sang điểm sau.
KHOANG_TOI_DIEM = 4
GIAY_KET_O_DIEM = 5
GIAY_TOI_DA_MOT_DIEM = 30
# Gần NPC hơn thì chạy bộ, khỏi lên thú cưỡi.
KHOANG_CACH_LEN_THU = 20

MA_DANG_THEO_DOI = 'local v = Player:InTeamFollowMode() if v == true or v == 1 then return "1" end return "0"'
MA_THEO_DOI = 'if Player:IsLeader() == 1 then Player:TeamFrame_AskTeamFollow() end'
MA_BO_THEO_DOI = 'Player:StopFollow()'
# Đội trưởng mời theo / triệu tập: MessageBox_Other (theo đội) hoặc Relive (kéo khi chết).
MA_DONG_Y_THEO_DOI_HOP = (
    'if IsWindowShow("MessageBox_Other") then '
    'setmetatable(_G, {__index = MessageBox_Other_Env}); MessageBox_Other_OK_Clicked() end '
    'if IsWindowShow("Relive_Frame") then Friend:CallOf("ok") end')
MA_DANG_CUOI = 'if (tonumber(GetMountID()) or -1) > 0 then return "1" end return "0"'

# Túi / trang bị (dùng chung với nhận đồ tân thủ ở nhan_vat_moi.py).
MA_TUI = ('local s = "" for i = 0, 99 do local a = PlayerPackage:EnumItem("base", i) '
          'if a and a:GetID() ~= 0 then s = s .. i .. "\\t" .. a:GetDefineID() .. "\\t" .. a:GetNum() .. "\\n" end end '
          'return s')
# Chuột phải vào ô túi = Packet_ItemBtnClicked -> nút ô túi :DoAction() (PlayerPackage:UseItem không mang được
# Bách Bảo Nang / trang bị). Mượn nút ô đầu của cửa sổ túi, gắn món cần dùng rồi DoAction; túi đang mở thì game tự vẽ
# lại khi đồ trong túi đổi.
MA_CHUOT_PHAI = trong_cua_so("Packet", 'local a = PlayerPackage:EnumItem("base", {o}) '
                                       'if not a or a:GetID() == 0 then return "0" end '
                                       'Packet_Space_Line1_Row1_button:SetActionItem(a:GetID()) '
                                       'Packet_Space_Line1_Row1_button:DoAction() return "1"')
MA_DA_MANG = 'local a = EnumAction({o}, "equip") if a and a:GetID() ~= 0 then return "1" end return "0"'
O_TRANG_BI_THU_CUOI = 8
MA_DA_CO_THU_CUOI = MA_DA_MANG.replace("{o}", str(O_TRANG_BI_THU_CUOI))
# Tiệm KNB -> Quảng Trường Hình Tượng: (nhóm, tên món, mã). Mua đủ rồi mang Đà Điểu, dùng Kỵ Thuật.
TIEM_THU_CUOI = "Quảng Trường Hình Tượng"
MON_THU_CUOI = ("Thú Cưỡi Tân Thủ", "Cưỡi: Đà Điểu", 10158130)
MON_KY_THUAT = ("Kỵ Thuật", "Kỵ Thuật: Đà Điểu", 31001228)
GIAY_CHO_GAME_TRA_LOI = 5
GIAY_DUNG_KY_THUAT = 15  # có thanh vận công trước khi mất món
SO_LAN_DUNG_TOI_DA = 40
SO_LAN_DUNG_KY_THUAT = 10
# Đang theo đội (cả đội trưởng đã bấm Theo đội) thì game không cho dùng kỹ năng; StopFollow vài trăm ms mới có hiệu lực.
GIAY_CHO_BO_THEO_DOI = 3.0


def bo_theo_doi(game, giay=GIAY_CHO_BO_THEO_DOI):
    """Bỏ theo đội và chờ game xác nhận đã bỏ. True nếu đã không còn theo đội."""
    het_han = time.time() + giay
    while True:
        try:
            if game.lua.chay(MA_DANG_THEO_DOI) != b"1":
                return True
            game.lua.chay(MA_BO_THEO_DOI)
        except LoiLua:
            return False
        if time.time() >= het_han:
            return False
        time.sleep(0.3)


def xuong_thu(game, giay=GIAY_CHO_BO_THEO_DOI):
    """Xuống thú cưỡi (đang cưỡi thì không dùng được Về thành) và chờ game xác nhận. True nếu đã không còn cưỡi."""
    het_han = time.time() + giay
    while True:
        try:
            if game.lua.chay(MA_DANG_CUOI) != b"1":
                return True
            game.lua.chay(f'local xuong = "" {MA_XUONG_THU} return xuong')
        except LoiLua:
            return False
        if time.time() >= het_han:
            return False
        time.sleep(0.3)


def chuan_bi_ve_thanh(game):
    """Bỏ theo đội và xuống thú trước khi dùng kỹ năng Về thành. True nếu đã sẵn sàng."""
    return bo_theo_doi(game) & xuong_thu(game)

# Khung Quest hiện danh sách dòng (QUEST_EVENTLIST) hoặc chữ thông tin (QUEST_INFO, vd. "đã 20 lần khiêu chiến").
# Bọc Quest_OnEvent để biết lần mở gần nhất là loại nào; chưa bọc được thì đọc cả chữ thông tin.
MA_HOI_THOAI = '''
if not AUTOHOC_QEV_HOOK and Quest_OnEvent then
  AUTOHOC_QEV_HOOK = 1
  local cu = Quest_OnEvent
  Quest_OnEvent = function(ev)
    if ev == "QUEST_EVENTLIST" or ev == "QUEST_INFO" then AUTOHOC_QEV = ev end
    return cu(ev)
  end
end
if not IsWindowShow("Quest") then return "" end
local s = ""
for i = 0, (DataPool:GetNPCEventList_Num() or 0) - 1 do
  local a, b, c, d, e = DataPool:GetNPCEventList_Item(i)
  s = s .. tostring(a) .. "\\t" .. tostring(c) .. "\\t" .. tostring(d) .. "\\t" .. tostring(e) .. "\\n"
end
local n = DataPool:GetMissionInfo_Num() or 0
for i = 0, n - 1 do
  s = s .. "info\\t-1\\t-1\\t" .. tostring(DataPool:GetMissionInfo_Text(i)) .. "\\n"
end
local t = ""
if Target:IsPresent() then t = Target:GetName() end
return "1\\t" .. t .. "\\n" .. s
'''
# Bọc DebugListBox_Update để giữ lại thông báo hệ thống cho auto đọc (tối đa 300 dòng chưa đọc).
MA_DOC_THONG_BAO = '''
if not AUTOHOC_TB_HOOK then
  AUTOHOC_TB_HOOK = 1
  AUTOHOC_TB = {}
  local buf = AUTOHOC_TB
  local G = getfenv(0)
  local cu = rawget(G, "DebugListBox_Update")
  if cu then
    rawset(G, "DebugListBox_Update", function(a)
      if table.getn(buf) < 300 then table.insert(buf, tostring(a)) end
      return cu(a)
    end)
  end
end
local t = AUTOHOC_TB
local s = table.concat(t, "\\n")
for i = table.getn(t), 1, -1 do table.remove(t, i) end
return s
'''


class _Dung(Exception):
    """Người chơi tắt auto / tắt phó bản giữa chừng."""


class _HetLuot(Exception):
    """NPC báo đã đủ 20 lần khiêu chiến trong ngày."""
    def __init__(self, chu):
        self.chu = chu


class _HetPmpSo(Exception):
    """Đội / nhân vật đã qua 1 lần Sơ Phiêu Miểu Phong — chuyển PMP thường."""
    def __init__(self, chu):
        self.chu = chu


class _HetSatTinh(Exception):
    """NPC SÁT TINH báo đã hết lượt trong ngày."""
    def __init__(self, chu):
        self.chu = chu


class _TreoPMP(Exception):
    """Kẹt trong ải PMP (lâu không có quái / đánh mãi không chết quái): về thành chạy vòng mới."""

    def __init__(self, chu=f"đứng yên {GIAY_TREO_PMP_KHONG_QUAI}s không có quái"):
        super().__init__(chu)
        self.chu = chu


class _HetGioLanThu(Exception):
    """Một lần thử của step PMP đã quá GIAY_MOT_LAN_THU_AI giây."""


class LoiPhoBan(Exception):
    pass


class _TruongSaiMap(LoiPhoBan):
    """Đội trưởng không còn ở map cần gom đội (vd. NPC đã đưa sang map sau mà luồng vẫn chờ ở map trước)."""

    def __init__(self, map_dang_o, map_can):
        super().__init__(f"đội trưởng đang ở [{map_dang_o}], không phải {map_can}")
        self.map_dang_o = map_dang_o


def hom_nay(cai_dat_pmp):
    """Bộ đếm của hôm nay (sang ngày khác thì coi như chưa đi vòng nào). st_*: Thập Nhị Sát Tinh."""
    moi = {"ngay": date.today().isoformat(), "so_vong": 0, "so_het_luot": False, "het_luot": False,
           "st_vong": 0, "st_het": False}
    dem = cai_dat_pmp.get("hom_nay") or {}
    if dem.get("ngay") != moi["ngay"]:
        return moi
    return dict(moi, **dem)


def con_pmp(pmp, dem):
    if pmp.get("chi_sat_tinh"):
        return False
    if pmp["so_vong"] and dem["so_vong"] >= pmp["so_vong"]:
        return False
    return con_pmp_thuong(dem)


def con_pmp_so(dem):
    return not dem.get("so_het_luot", False)


def con_pmp_thuong(dem):
    return not dem["het_luot"]


def con_luot_pmp_thuong(pmp, dem):
    """Còn lượt PMP thường (quyết định PMP vs Sát Tinh)."""
    if pmp.get("chi_sat_tinh"):
        return False
    if pmp["so_vong"] and dem["so_vong"] >= pmp["so_vong"]:
        return False
    return con_pmp_thuong(dem)


def con_sat_tinh(pmp, dem):
    return pmp.get("sat_tinh", True) and not dem["st_het"]


def dang_phai_di_sat_tinh(pmp, dem):
    """Đã xong PMP thường (hoặc chỉ đi Sát Tinh), còn lượt Sát Tinh — đội viên cần tới NPC ở Đại Lý."""
    return pmp["bat"] and con_sat_tinh(pmp, dem) and dem["het_luot"]


XY_NPC_SAT_TINH = BUOC_VAO_SAT_TINH[2]
TEN_NPC_SAT_TINH = BUOC_VAO_SAT_TINH[1]
# Xong vòng Sát Tinh game trả ra Lạc Dương cạnh NPC SÁT TINH: đội viên đứng chờ ở đây cho vòng sau.
XY_CHO_SAT_TINH = (154, 194)
KHOANG_TOI_CHO_SAT_TINH = 5
BUOC_DI_CHUYEN_LAC_DUONG = CAC_BUOC_VAO[0]
TEN_NPC_HOI_MAU_DAI_LY = BUOC_DI_CHUYEN_LAC_DUONG[1]
XY_NPC_HOI_MAU_DAI_LY = BUOC_DI_CHUYEN_LAC_DUONG[2]
TY_LE_HOI_MAU_DAI_LY = 0.5
GIAY_CHO_HOI_MAU_DAI_LY = 8
GIAY_GIUA_HOI_MAU_DAI_LY = 3
XY_NPC_PMP = CAC_BUOC_VAO[1][2]
TEN_NPC_PMP = CAC_BUOC_VAO[1][1]
GIAY_GIUA_BUOC_DOI_VIEN_GOM = 2.5
# Đội viên cần về Đại Lý (gom / map lạ): thử lại kỹ năng Quay về thành mỗi 3 giây.
GIAY_RETRY_VE_THANH_THEO_DOI = 3
# NPC SÁT TINH trên map thường lệch vài ô so với tọa độ ghi tay; gom đội dùng vị trí NPC đọc từ game.
KHOANG_GAN_NPC_SAT_TINH = 14
# Đội viên đứng trong khoảng này quanh đội trưởng thì Theo đội kéo được (game chỉ kéo người đứng gần).
KHOANG_GAN_TRUONG = 8
GIAY_TOI_DA_CHO_GAN_TRUONG = 90


def cai_dat_pmp(cai_dat_nhan_vat):
    gia_tri = dict(cau_hinh.MAC_DINH_PHO_BAN_PMP)
    gia_tri.update(cai_dat_nhan_vat.get("pho_ban_pmp") or {})
    return gia_tri


_phien_xoay_vong_dang_chay = False


def dat_phien_xoay_vong(dang_chay):
    """Bật/tắt khi bấm Bắt đầu/Dừng xoay vòng (không lưu file — tránh PMP tự chạy lúc mở AutoHoc)."""
    global _phien_xoay_vong_dang_chay
    _phien_xoay_vong_dang_chay = bool(dang_chay)


def phien_xoay_vong_dang_chay():
    return _phien_xoay_vong_dang_chay


# Qua 0h giữa lúc đang trong phó bản: đi nốt vòng đang dở nhưng không vào vòng mới (xoay vòng chờ rồi về nhóm 1).
_chan_vong_moi = False
_dang_chay_vong = set()


def dat_chan_vong_moi(chan):
    global _chan_vong_moi
    _chan_vong_moi = bool(chan)


def dang_chay_vong(ten):
    """Nhân vật đang trong PhoBanPMP.chay() (đi dở một vòng PMP / Sát Tinh)."""
    return chuan_hoa(ten or "") in _dang_chay_vong


def xoa_co_xoay_vong_luu_tat_ca():
    """Xóa cờ xoay_vong còn sót trong cau_hinh.json sau phiên cũ / thoát giữa chừng."""
    def sua(cai_dat):
        pmp = cai_dat_pmp(cai_dat)
        if not pmp.get("xoay_vong"):
            return False
        cai_dat["pho_ban_pmp"] = dict(pmp, xoay_vong=False)
        return True

    cau_hinh.cap_nhat_tat_ca_nhan_vat(sua)


def pmp_dang_duoc_phep_chay(cai_dat_nhan_vat):
    """Chỉ chạy PMP khi đang có phiên xoay vòng (Bắt đầu) và nhân vật được luồng XV bật phó bản."""
    if not phien_xoay_vong_dang_chay():
        return False
    pmp = cai_dat_pmp(cai_dat_nhan_vat)
    return pmp["bat"] and bool(pmp.get("xoay_vong"))


def mo_ta_hom_nay(cai_dat_nhan_vat):
    pmp = cai_dat_pmp(cai_dat_nhan_vat)
    dem = hom_nay(pmp)
    chu = f"Hôm nay PMP {dem['so_vong']} vòng" + (f" / {pmp['so_vong']}" if pmp["so_vong"] else "")
    if dem["het_luot"]:
        chu += ", hết lượt"
    if pmp.get("sat_tinh", True):
        chu += f" - Sát Tinh {dem['st_vong']} vòng" + (", hết lượt" if dem["st_het"] else "")
    return chu


def cac_doan_hom_nay(cai_dat_nhan_vat):
    """Bộ đếm hôm nay để hiện trên giao diện: danh sách (chữ, là_số), mỗi phó bản một dòng."""
    pmp = cai_dat_pmp(cai_dat_nhan_vat)
    dem = hom_nay(pmp)
    doan = [("Hôm nay PMP: ", False), (str(dem["so_vong"]), True)]
    if pmp["so_vong"]:
        doan += [(" / ", False), (str(pmp["so_vong"]), True)]
    het = ", hết lượt" if dem["het_luot"] else ""
    doan.append((" vòng" + het, False))
    if pmp.get("sat_tinh", True):
        doan += [("\nHôm nay Sát Tinh: ", False), (str(dem["st_vong"]), True),
                 (" vòng" + (", hết lượt" if dem["st_het"] else ""), False)]
    return doan


def la_map_pho_ban(ten_map):
    """Đại Lý / Lạc Dương / Phiêu Miểu Phong / Lôi đài sinh tử: đường đi của phó bản."""
    return chuan_hoa(ten_map or "") in {chuan_hoa(m) for m in (MAP_DAI_LY, MAP_LAC_DUONG, MAP_LAU_LAN, MAP_PMP,
                                                                 MAP_SAT_TINH)}


def la_map_trong_pho_ban(ten_map):
    """Đang trong phó bản (đánh ở đây), không phải map đường đi."""
    return chuan_hoa(ten_map or "") in {chuan_hoa(MAP_PMP), chuan_hoa(MAP_SAT_TINH)}


def la_sat_tinh(ten_map):
    return chuan_hoa(ten_map or "") == chuan_hoa(MAP_SAT_TINH)


def can_ve_khi_het_luot_pmp(ten_map):
    """Hết lượt PMP mà còn đứng ở Lạc Dương / Lâu Lan (cũ) / trong PMP thì về Đại Lý."""
    return chuan_hoa(ten_map or "") in {chuan_hoa(MAP_LAC_DUONG), chuan_hoa(MAP_LAU_LAN), chuan_hoa(MAP_PMP)}


def can_ve_khi_het_luot(pmp, dem, ten_map):
    """
    Hết lượt PMP thường mà đứng ở Lạc Dương / Lâu Lan / trong PMP thì về Đại Lý — trừ khi Lạc Dương còn việc: còn lượt
    Sát Tinh (vào lôi đài ở đây), hoặc đang xoay vòng (xong Sát Tinh thì giao dịch cho trưởng nhóm ngay tại Lạc Dương).
    """
    if not dem["het_luot"] or not can_ve_khi_het_luot_pmp(ten_map):
        return False
    return not (la_lac_duong(ten_map) and (con_sat_tinh(pmp, dem) or pmp.get("xoay_vong")))


def la_dai_ly(ten_map):
    return chuan_hoa(ten_map or "") == chuan_hoa(MAP_DAI_LY)


def can_hoi_mau_tai_dai_ly(tt, ty_le=TY_LE_HOI_MAU_DAI_LY):
    """Máu còn dưới ty_le (mặc định 50%) so với HP tối đa."""
    if not tt:
        return False
    hp_max = tt.get("hp_toi_da") or 0
    hp = tt.get("hp") or 0
    return hp_max > 0 and hp > 0 and hp < hp_max * ty_le


def cap_nhat_hoi_mau_dai_ly(game, map_dang_o, ten, in_log, state, nen_dung=None):
    """Ở Đại Lý: máu dưới 50% thì tới NPC Di Chuyển mở hội thoại để hồi máu."""
    if not la_dai_ly(map_dang_o):
        return
    if nen_dung and nen_dung():
        return
    try:
        tt = game.thong_tin()
    except LoiLua:
        return
    if not can_hoi_mau_tai_dai_ly(tt):
        return
    bay_gio = time.time()
    if bay_gio - state.get("luc", 0) < GIAY_GIUA_HOI_MAU_DAI_LY:
        return
    state["luc"] = bay_gio
    try:
        _HoiMauDaiLy(game, ten, in_log, nen_dung).thuc_hien()
    except _Dung:
        raise


def _doc_hoi_thoai_game(game):
    try:
        dong = giai_ma(game.lua.chay(MA_HOI_THOAI)).split("\n")
    except LoiLua:
        return None
    if not dong[0].startswith("1\t"):
        return None
    cac_dong = []
    for chu in dong[1:]:
        phan = chu.split("\t", 3)
        if len(phan) == 4:
            try:
                cac_dong.append((phan[0], int(float(phan[1])), int(float(phan[2])), phan[3]))
            except ValueError:
                cac_dong.append((phan[0], -1, -1, phan[3]))
    return dong[0][2:], cac_dong


def _chay_toi_xy(game, xy, ten_npc=None):
    if ten_npc:
        game.lua.chay(f"AutoRunToTarget({xy[0]}, {xy[1]}) SetAutoRunTargetNPCName({chuoi_lua(ten_npc)})")
    else:
        game.lua.chay(f"AutoRunToTarget({xy[0]}, {xy[1]})")


def _doc_dang_theo_doi(luong):
    try:
        return luong.game.lua.chay(MA_DANG_THEO_DOI) == b"1"
    except (LoiLua, OSError, AttributeError):
        return luong.dang_theo_doi


def dong_y_theo_doi_popup(game):
    """Đồng ý hộp theo đội / triệu tập của đội trưởng (luồng đội viên gọi khi đang chạy tới trưởng)."""
    try:
        game.lua.chay(MA_DONG_Y_THEO_DOI_HOP)
    except LoiLua:
        pass


def xoa_lenh_gom_doi(doi):
    """Hủy lệnh chạy NPC / triệu tập khi đội trưởng đổi map (ví dụ về Đại Lý giữa bước Lạc Dương)."""
    if not doi:
        return
    doi.npc_gom = None
    doi.vi_tri_truong = None
    for luong in doi.cac_doi_vien.values():
        luong.trieu_tap_den = None


def cap_nhat_trieu_tap_doi_vien(game, trieu_tap, state):
    """
    Đội trưởng đã gửi lệnh triệu tập: chạy tới tọa độ trưởng, đồng ý popup theo đội nếu có.
    trieu_tap: (x, y, map, het_han) hoặc None.
    """
    if not trieu_tap or time.time() >= trieu_tap[3]:
        return
    if state.get("trieu_tap") != trieu_tap:
        state.clear()
        state["trieu_tap"] = trieu_tap
    bay_gio = time.time()
    if bay_gio - state.get("luc", 0) < GIAY_GIUA_BUOC_DOI_VIEN_GOM:
        return
    state["luc"] = bay_gio
    try:
        tt = game.thong_tin()
    except LoiLua:
        return
    if not tt or chuan_hoa(tt["map"]) != chuan_hoa(trieu_tap[2]):
        return
    xy = (int(trieu_tap[0]), int(trieu_tap[1]))
    if khoang_cach((tt["x"], tt["y"]), xy) > KHOANG_GAN_TRUONG // 2:
        _chay_toi_xy(game, xy)
    dong_y_theo_doi_popup(game)


def xy_gom_doi_vien(doi, truong_luong, map_can, xy_npc):
    """Tọa độ đội viên nên chạy tới: ưu tiên vị trí đội trưởng trên cùng map, không có thì NPC."""
    khoa = chuan_hoa(map_can)
    if truong_luong is not None:
        try:
            tt = truong_luong.game.thong_tin()
            if tt and chuan_hoa(tt["map"]) == khoa:
                return (tt["x"], tt["y"])
        except (LoiLua, OSError, AttributeError):
            pass
    vt = doi.vi_tri_truong
    if vt and chuan_hoa(vt[2]) == khoa:
        return vt[0], vt[1]
    return xy_npc


def cap_nhat_di_lac_duong_doi_vien(game, map_dang_o, state):
    """Đội viên ở Đại Lý: một bước tự NPC Di Chuyển sang Lạc Dương (gọi lặp từ luồng đội viên)."""
    if la_lac_duong(map_dang_o):
        state.clear()
        return
    if not la_dai_ly(map_dang_o):
        return
    bay_gio = time.time()
    if bay_gio - state.get("luc", 0) < GIAY_GIUA_BUOC_DOI_VIEN_GOM:
        return
    state["luc"] = bay_gio
    _, ten_npc, xy, cac_dong, map_toi = BUOC_DI_CHUYEN_LAC_DUONG
    try:
        tt = game.thong_tin()
    except LoiLua:
        return
    if not tt:
        return
    vi_tri = (tt["x"], tt["y"])
    if khoang_cach(vi_tri, xy) > KHOANG_GAN_NPC_SAT_TINH:
        _chay_toi_xy(game, xy, ten_npc)
        return
    buoc = state.get("dong", 0)
    if buoc < len(cac_dong):
        ht = _doc_hoi_thoai_game(game)
        if ht and ht[1]:
            dong = cac_dong[buoc]
            if isinstance(dong[0], str):
                khop = [(s, e) for _, s, e, chu in ht[1] if chuan_hoa(dong[0]) in chuan_hoa(chu)]
                if not khop:
                    return
                dong = khop[0]
            game.lua.chay(f"QuestFrameOptionClicked(-1, {dong[0]}, {dong[1]})")
            state["dong"] = buoc + 1
            state["luc_chon_xong"] = bay_gio
        else:
            _chay_toi_xy(game, xy, ten_npc)
        return
    try:
        moi = game.thong_tin()
    except LoiLua:
        return
    if moi and chuan_hoa(moi["map"]) == chuan_hoa(map_toi):
        state.clear()
    elif bay_gio - state.get("luc_chon_xong", bay_gio) >= GIAY_CHO_DOI_MAP:
        # Chọn hết dòng mà chưa đổi map (hội thoại bị đóng giữa chừng): làm lại từ đầu.
        state.clear()


def npc_lac_duong_can_toi(pmp, dem):
    """NPC Lạc Dương mà đội viên cần tự chạy tới (PMP trước, hết PMP thường thì Sát Tinh)."""
    if con_luot_pmp_thuong(pmp, dem):
        return TEN_NPC_PMP, XY_NPC_PMP
    if con_sat_tinh(pmp, dem):
        return TEN_NPC_SAT_TINH, XY_NPC_SAT_TINH
    return None, None


def cap_nhat_chay_gan_npc_co_dinh(game, map_dang_o, ten_npc, xy_npc, state):
    """Tự chạy tới tọa độ NPC cố định trên Lạc Dương."""
    if not la_lac_duong(map_dang_o):
        return
    bay_gio = time.time()
    if bay_gio - state.get("luc", 0) < GIAY_GIUA_BUOC_DOI_VIEN_GOM:
        return
    try:
        tt = game.thong_tin()
    except LoiLua:
        return
    if not tt or khoang_cach((tt["x"], tt["y"]), xy_npc) <= KHOANG_GAN_NPC_SAT_TINH:
        return
    state["luc"] = bay_gio
    _chay_toi_xy(game, xy_npc, ten_npc)


def cap_nhat_doi_vien_tu_lac_duong(game, map_dang_o, pmp, dem, state_di_ld, state_chay):
    """Chỉ trước khi vào phó bản: đội viên tự Đại Lý -> Di Chuyển -> NPC Lạc Dương."""
    if la_map_trong_pho_ban(map_dang_o):
        return
    ten_npc, xy = npc_lac_duong_can_toi(pmp, dem)
    if not ten_npc:
        return
    if la_dai_ly(map_dang_o):
        cap_nhat_di_lac_duong_doi_vien(game, map_dang_o, state_di_ld)
        return
    if la_lac_duong(map_dang_o):
        cap_nhat_chay_gan_npc_co_dinh(game, map_dang_o, ten_npc, xy, state_chay)


def cap_nhat_doi_vien_cho_sat_tinh(game, map_dang_o, state):
    """Đội viên ở Lạc Dương giữa hai vòng Sát Tinh: không đứng ở điểm chờ thì tự chạy tới (gọi lặp từ luồng đội viên)."""
    if not la_lac_duong(map_dang_o):
        return
    bay_gio = time.time()
    if bay_gio - state.get("luc", 0) < GIAY_GIUA_BUOC_DOI_VIEN_GOM:
        return
    state["luc"] = bay_gio
    try:
        tt = game.thong_tin()
    except LoiLua:
        return
    if not tt or khoang_cach((tt["x"], tt["y"]), XY_CHO_SAT_TINH) <= KHOANG_TOI_CHO_SAT_TINH:
        return
    _chay_toi_xy(game, XY_CHO_SAT_TINH)


def cap_nhat_doi_vien_toi_truong(game, doi, truong_luong, map_dang_o, state):
    """Đội trưởng đang gom: đội viên đứng xa thì tự chạy tới chỗ đội trưởng (Đại Lý hoặc Lạc Dương)."""
    if not doi.gom_truong or not (la_dai_ly(map_dang_o) or la_lac_duong(map_dang_o)):
        return
    bay_gio = time.time()
    if bay_gio - state.get("luc", 0) < GIAY_GIUA_BUOC_DOI_VIEN_GOM:
        return
    state["luc"] = bay_gio
    xy = xy_gom_doi_vien(doi, truong_luong, MAP_DAI_LY, None)
    if not xy:
        return
    try:
        tt = game.thong_tin()
    except LoiLua:
        return
    if not tt or khoang_cach((tt["x"], tt["y"]), xy) <= KHOANG_GAN_TRUONG // 2:
        return
    _chay_toi_xy(game, (int(xy[0]), int(xy[1])))


def la_lac_duong(ten_map):
    return chuan_hoa(ten_map or "") == chuan_hoa(MAP_LAC_DUONG)


def bat_tap_hop(doi, map_gom=MAP_DAI_LY):
    if not doi:
        return
    doi.tap_hop = True
    doi.map_tap_hop = map_gom


def tat_tap_hop(doi):
    if not doi:
        return
    doi.tap_hop = False
    doi.map_tap_hop = None


def can_ve_vi_map_la(ten_map):
    """Map lạ ngoài đường PMP; tên map trống (đang load) thì không tự về."""
    if not chuan_hoa(ten_map or ""):
        return False
    return not la_map_pho_ban(ten_map)


def can_ve_tap_hop(doi, ten_map, map_truong=None):
    """Đội viên tự về Đại Lý khi trưởng gom và chưa ở map gom (không kéo người trong ải PMP/lôi đài)."""
    if not doi or not doi.tap_hop or la_map_trong_pho_ban(ten_map):
        return False
    if map_truong and la_map_trong_pho_ban(map_truong):
        return False
    map_gom = chuan_hoa(doi.map_tap_hop or MAP_DAI_LY)
    o_dai_ly = la_dai_ly(ten_map)
    o_lac_duong = la_lac_duong(ten_map)
    if map_gom == chuan_hoa(MAP_DAI_LY):
        return not o_dai_ly
    if map_gom == chuan_hoa(MAP_LAC_DUONG):
        return not o_lac_duong and not o_dai_ly
    return False


def nen_ve_thanh_theo_doi(doi, map_dv, map_truong, het_luot, dang_theo_doi):
    """
    Đội viên tự bấm Quay về Đại Lý. Trưởng đã vào PMP/lôi đài thì không về (kể cả hết lượt / map chưa cập nhật).
    Trưởng đã ra ải mà đội viên còn kẹt trong PMP/lôi đài: vẫn về (gom / hết lượt).
    Trả về (bool, lý_do ngắn cho log).
    """
    trong_an = la_map_trong_pho_ban(map_dv)
    if map_truong and la_map_trong_pho_ban(map_truong):
        return False, ""
    if dang_theo_doi:
        return False, ""
    if trong_an:
        if not map_truong or la_map_trong_pho_ban(map_truong):
            return False, ""
        if het_luot:
            return True, "hết lượt (kẹt ải)"
        # Trong ải đang gom: không bấm Về thành (dễ tắt client); chờ trưởng / thoát ải tự nhiên.
        return False, ""
    if het_luot:
        return True, "hết lượt"
    if la_dai_ly(map_dv):
        return False, ""
    if can_ve_vi_map_la(map_dv):
        return True, "map lạ"
    if can_ve_tap_hop(doi, map_dv, map_truong):
        map_gom = chuan_hoa((doi.map_tap_hop if doi else None) or MAP_DAI_LY)
        return True, f"gom {MAP_DAI_LY if map_gom == chuan_hoa(MAP_DAI_LY) else MAP_LAC_DUONG}"
    return False, ""


class DoiPMP:
    """Đội đang theo một đội trưởng đi PMP: đội trưởng ghi vùng đánh, luồng của đội viên đọc."""

    def __init__(self, truong, cac_doi_vien, doc_lai=None):
        self.truong = truong
        # {tên đội viên: luồng của đội viên}, luồng có map_hien_tai và dang_theo_doi (luồng đó tự cập nhật)
        self.cac_doi_vien = cac_doi_vien
        # doc_lai() -> {tên: luồng} mới (None nếu đọc lỗi): đội viên bật auto / vào nhóm sau lúc lập đội
        self.doc_lai = doc_lai
        self.vung = None
        # Đội trưởng đang gom đội: tap_hop + map_tap_hop (Đại Lý / Lạc Dương).
        self.tap_hop = False
        self.map_tap_hop = None
        # Đội trưởng đang vào Lạc Dương: đội viên tự NPC Di Chuyển (không điều khiển từ xa).
        self.di_lac_duong = False
        # (map, tên NPC, tọa độ gợi ý) khi chờ gom quanh NPC; None khi không gom.
        self.npc_gom = None
        # (x, y, map) vị trí đội trưởng cập nhật khi gom — đội viên chạy tới đây.
        self.vi_tri_truong = None
        # Đội trưởng đang chờ đội viên tới gần mình ở Đại Lý (trước khi bấm Theo đội đi Di Chuyển).
        self.gom_truong = False
        self.so_ai = 0
        self.giai_doan = ""   # "" / "di" / "noi" / "danh"
        self.quai_danh = ()   # tên chuẩn hóa quái của ải đang đánh
        # Ở PMP đội trưởng chỉ cưỡi thú dẫn đường, không tự đánh (luồng chiến đấu của đội trưởng đọc).
        self.truong_khong_danh = False
        # Đội viên đánh quá lâu chưa chết quái: đội trưởng xuống thú đánh cùng (bỏ qua tùy chọn cưỡi thú).
        self.truong_vao_danh = False
        # Sau giết boss: đội viên tự retry Về thành mỗi GIAY_RETRY_VE_SAU_BOSS (None khi không áp dụng).
        self.cho_ve_sau_boss = None

    def xoa_lenh_gom(self):
        xoa_lenh_gom_doi(self)

    def truong_dang_khong_danh(self):
        return self.truong_khong_danh and bool(self.cac_doi_vien)

    def dat_buoc(self, so_ai=0, giai_doan="", quai=(), vung=None):
        self.so_ai = so_ai
        self.giai_doan = giai_doan
        self.quai_danh = tuple(chuan_hoa(ten) for ten in quai)
        self.vung = vung

    def lam_moi(self):
        """Đọc lại đội viên; True nếu danh sách đổi."""
        moi = self.doc_lai() if self.doc_lai else None
        if moi is None or list(moi) == list(self.cac_doi_vien):
            return False
        self.cac_doi_vien = moi
        return True

    def co(self, ten):
        return any(chuan_hoa(ten) == chuan_hoa(dv) for dv in self.cac_doi_vien)

    def map_doi_vien(self):
        """Map đọc thẳng từ game đội viên (map_hien_tai của luồng có thể chưa cập nhật)."""
        kq = {}
        for ten, luong in self.cac_doi_vien.items():
            try:
                tt = luong.game.thong_tin()
                kq[ten] = tt["map"] if tt else luong.map_hien_tai
            except (LoiLua, OSError, AttributeError):
                kq[ten] = luong.map_hien_tai
        return kq

    def chua_theo(self):
        """Đội viên chưa ở chế độ Theo đội, đọc thẳng từ game đội viên."""
        return [ten for ten, luong in self.cac_doi_vien.items() if not _doc_dang_theo_doi(luong)]

    def can_trieu_tap(self, game_truong):
        """
        Đội viên chưa Theo đội hoặc cùng map mà đứng xa đội trưởng (game chỉ kéo người gần).
        Trả về [(tên, luồng), ...].
        """
        try:
            tt_tr = game_truong.thong_tin()
        except LoiLua:
            return []
        if not tt_tr:
            return []
        xy_tr = (tt_tr["x"], tt_tr["y"])
        map_tr = tt_tr["map"]
        khoa_map = chuan_hoa(map_tr)
        can = []
        for ten, luong in self.cac_doi_vien.items():
            if _doc_dang_theo_doi(luong):
                luong.trieu_tap_den = None
                continue
            can.append((ten, luong))
        return can

    def gui_trieu_tap(self, game_truong, het_han, in_log, ten_truong, luc_bao):
        """Gửi lệnh triệu tập (luồng đội viên tự chạy tới đội trưởng)."""
        can = self.can_trieu_tap(game_truong)
        if not can:
            return
        try:
            tt_tr = game_truong.thong_tin()
        except LoiLua:
            return
        if not tt_tr:
            return
        xy = (tt_tr["x"], tt_tr["y"])
        map_tr = tt_tr["map"]
        self.vi_tri_truong = (xy[0], xy[1], map_tr)
        khoa_tr = chuan_hoa(map_tr)
        ten_ds = []
        for ten, luong in can:
            try:
                tt = luong.game.thong_tin()
            except (LoiLua, OSError, AttributeError):
                continue
            if not tt or chuan_hoa(tt["map"]) != khoa_tr:
                continue
            luong.trieu_tap_den = (xy[0], xy[1], map_tr, het_han)
            ten_ds.append(ten)
        if not ten_ds:
            return
        bay_gio = time.time()
        if bay_gio - luc_bao.get("luc", 0) >= GIAY_GIUA_HAI_LAN_TRIEU_TAP:
            luc_bao["luc"] = bay_gio
            in_log(f"{ten_truong}: PMP triệu tập {', '.join(ten_ds)} tới đội trưởng "
                   f"({int(xy[0])}, {int(xy[1])}) [{map_tr}]")


class PhoBanPMP:
    def __init__(self, game, in_log):
        self.game = game
        self.in_log = in_log
        self.doc_quanh = ChienDau(game.lua, lambda chu: None)
        self.nghi_den = 0.0
        self.thong_bao = []
        self.doi = None
        self.che_do = "pmp"
        self._vong_vao_so = False

    def can_di(self, cai_dat_nhan_vat):
        pmp = cai_dat_pmp(cai_dat_nhan_vat)
        dem = hom_nay(pmp)
        return pmp_dang_duoc_phep_chay(cai_dat_nhan_vat) and not _chan_vong_moi \
            and (con_pmp(pmp, dem) or con_sat_tinh(pmp, dem)) and time.time() >= self.nghi_den

    # ---------- đọc game ----------

    def _kiem_tra(self):
        if self.nen_dung():
            raise _Dung()
        if time.time() > self.het_han_vong:
            raise LoiPhoBan(f"quá {GIAY_MOT_VONG // 60} phút mà chưa xong vòng")
        het_han_lan_thu = getattr(self, "het_han_lan_thu", None)
        if het_han_lan_thu is not None and time.time() > het_han_lan_thu:
            raise _HetGioLanThu()

    def _cho(self, dieu_kien, giay, buoc=0.3):
        """Chờ dieu_kien() trả về giá trị khác None / False trong giay giây; hết giờ thì trả về None."""
        het_han = time.time() + giay
        while True:
            self._kiem_tra()
            ket_qua = dieu_kien()
            if ket_qua:
                return ket_qua
            if time.time() >= het_han:
                return None
            time.sleep(buoc)

    def _tt(self):
        try:
            tt = self.game.thong_tin()
        except LoiLua:
            return None  # đang tải map
        if tt and tt["hp"] <= 0 < tt["hp_toi_da"]:
            raise LoiPhoBan("nhân vật đã chết")
        return tt

    def _doc_thong_bao(self):
        try:
            moi = [dong for dong in giai_ma(self.game.lua.chay(MA_DOC_THONG_BAO)).split("\n") if dong]
        except LoiLua:
            return []
        self.thong_bao += moi
        del self.thong_bao[:-50]
        return moi

    def _quanh(self):
        """[(tên chuẩn hóa, DoiTuong)] quái / NPC quanh nhân vật."""
        try:
            canh = self.doc_quanh._doc_quanh_minh()
        except LoiChienDau:
            return []
        return [(chuan_hoa(giai_ma(d.ten)), d) for d in canh.cac_quai]

    @staticmethod
    def _dong_khop(dong, script, extra, chu):
        """dong là (script, extra) hoặc (chuỗi gợi ý,) để khớp dòng hội thoại theo chữ."""
        if isinstance(dong[0], str):
            return chuan_hoa(dong[0]) in chuan_hoa(chu)
        if (script, extra) == dong:
            return True
        # VM / client khác bản: scriptId đổi nhưng chữ vẫn «Khiêu chiến Phiêu Miểu Phong».
        if dong in (DONG_PMP_SO, DONG_PMP_THUONG):
            c = chuan_hoa(chu)
            return "khiêu chiến" in c and "phiêu" in c and "miêu" in c
        return False

    def _hoi_thoai(self):
        """(tên mục tiêu, [(loại, script, extra, chữ)]) của hội thoại NPC đang mở, None nếu không mở."""
        try:
            dong = giai_ma(self.game.lua.chay(MA_HOI_THOAI)).split("\n")
        except LoiLua:
            return None
        if not dong[0].startswith("1\t"):
            return None
        cac_dong = []
        for chu in dong[1:]:
            phan = chu.split("\t", 3)
            if len(phan) == 4:
                try:
                    cac_dong.append((phan[0], int(float(phan[1])), int(float(phan[2])), phan[3]))
                except ValueError:
                    cac_dong.append((phan[0], -1, -1, phan[3]))
        return dong[0][2:], cac_dong

    @staticmethod
    def _la_bao_het_pmp_thuong(chu):
        """Quest / NPC báo đủ 20 lượt Phiêu Miểu Phong trong ngày (có dấu, không dấu, hoặc VISCII)."""
        if not chu:
            return False
        c = chuan_hoa(chu)
        if "20 lần" in c and "khiêu chiến" in c:
            return True
        b = bo_dau(chu)
        if "phieu mieu phong" not in b or not re.search(r"\b20\b", b):
            return False
        if "luot" in b or re.search(r"\bda\s+du\b", b):
            return True
        return "lan" in b and "khieu chien" in b

    def _het_trong_hoi_thoai(self):
        """'#het:<chữ>' nếu hội thoại đang mở báo đủ 20 lượt PMP, None nếu không."""
        ht = self._hoi_thoai()
        for chu in (dong[3] for dong in ht[1]) if ht else ():
            if self._la_bao_het_pmp_thuong(chu):
                return "#het:" + chu
        return None

    @staticmethod
    def _chu_het_pmp_so(cac_chu):
        """NPC báo đã qua 1 lần Sơ (vd. «… đã tham gia Khiêu Chiến quá 1 lần»)."""
        for chu in cac_chu:
            if not chu:
                continue
            c = chuan_hoa(chu)
            if "khiêu chiến" in c and re.search(r"quá\s*1\s*lần", c):
                return chu
            if "tham gia" in c and "khiêu chiến" in c and "1" in c and "lần" in c and "quá" in c:
                return chu
        return None

    def _kiem_tra_het_pmp_so_hoi_thoai(self):
        if not getattr(self, "_vao_het_so", False):
            return
        ht = self._hoi_thoai()
        if not ht:
            return
        ly_do = self._chu_het_pmp_so([chu for _, _, _, chu in ht[1]])
        if ly_do:
            raise _HetPmpSo(ly_do)

    def _danh_dau_het_pmp_so(self, ly_do):
        """Ghi so_het_luot, đóng Quest, không về thành — vòng này chuyển PMP thường."""
        self.in_log(f"{self.ten}: PMP Sơ không vào được ({ly_do}), chuyển Phiêu Miểu Phong thường")
        try:
            self.game.lua.chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
        except LoiLua:
            pass

        def sua(cai_dat):
            pmp = cai_dat.setdefault("pho_ban_pmp", dict(cau_hinh.MAC_DINH_PHO_BAN_PMP))
            dem = hom_nay(pmp)
            dem["so_het_luot"] = True
            pmp["hom_nay"] = dem

        ten_ds = [self.ten] + list(self.doi.cac_doi_vien if self.doi else ())
        for ten in ten_ds:
            cau_hinh.sua_nhan_vat(ten, sua)
        self.bao_doi()

    def _chu_het_luot(self, them=()):
        """Chữ thông báo hết 20 lượt PMP (hội thoại NPC hoặc kênh hệ thống), None nếu chưa có."""
        cac = list(them)
        ht = self._hoi_thoai()
        if ht:
            cac += [dong[3] for dong in ht[1]]
        cac += self._doc_thong_bao()
        for chu in cac:
            if self._la_bao_het_pmp_thuong(chu):
                return chu
        return None

    def _map(self):
        tt = self._tt()
        return tt["map"] if tt else None

    def _mo_ta(self, chu):
        self.trang_thai["mo_ta"] = f"{MO_TA}: {chu}"

    def _lua_dung(self, ma):
        try:
            return self.game.lua.chay(ma) == b"1"
        except LoiLua:
            return False

    # ---------- tổ đội (chỉ đội trưởng chạy) ----------

    def _cho_doi_vien(self, map_can):
        """Chờ mọi đội viên trong auto tới map_can (chưa đọc được map cũng tính là chưa tới). Không bỏ ai."""
        if not self.doi or not self.doi.cac_doi_vien:
            return

        def chua_toi():
            return [ten for ten, m in self.doi.map_doi_vien().items()
                    if chuan_hoa(m or "") != chuan_hoa(map_can)]
        if not chua_toi():
            return
        luc_bao = 0.0
        while True:
            if self.nen_dung():
                raise _Dung()
            self.doi.lam_moi()
            thieu = chua_toi()
            if not thieu:
                return
            cho = f"chờ {', '.join(thieu)} tới {map_can}"
            self._mo_ta(cho)
            bay_gio = time.time()
            if bay_gio - luc_bao >= 60:
                luc_bao = bay_gio
                self.in_log(f"{self.ten}: PMP {cho}")
            time.sleep(GIAY_CHO_GOM_DOI_RETRY)

    def _xy_npc_gan(self, ten_npc, xy_goi):
        """Tọa độ NPC đang đứng (game có thể lệch so với xy ghi trong BUOC_VAO), không thấy thì dùng xy_goi."""
        if not ten_npc:
            return xy_goi
        khoa = chuan_hoa(ten_npc)
        cac = [(int(d.x), int(d.y)) for ten, d in self._quanh() if ten == khoa and d.hp > 0]
        if not cac:
            return xy_goi
        return min(cac, key=lambda p: khoang_cach(p, xy_goi))

    def _truong_chay_toi_npc(self, ten_npc, xy_goi, map_can=None):
        """Đội trưởng tự chạy tới NPC (không chỉ đứng chờ đội viên). Chỉ chạy khi đang ở map_can."""
        if map_can is not None:
            tt_map = self._tt()
            if not tt_map or chuan_hoa(tt_map["map"]) != chuan_hoa(map_can):
                return
        xy = self._xy_npc_gan(ten_npc, xy_goi)
        tt = self._tt()
        if not tt or khoang_cach((tt["x"], tt["y"]), xy) <= KHOANG_GAN_NPC_SAT_TINH:
            return
        self.game.lua.chay(f"AutoRunToTarget({xy[0]}, {xy[1]}) "
                           f"SetAutoRunTargetNPCName({chuoi_lua(ten_npc)})")

    def _cho_doi_gan_xy(self, xy, map_can, ten_npc=None):
        """
        Đội trưởng chờ mọi đội viên cùng map và đứng gần xy (game chỉ kéo cả đội vào phó bản khi đủ người gần NPC).
        Kiểm tra lại mỗi GIAY_CHO_GOM_DOI_RETRY giây. ten_npc: đọc vị trí NPC thật và trưởng nhóm tự chạy tới.
        """
        if not self.doi or not self.doi.cac_doi_vien:
            return
        luc_bao = 0.0
        luc_theo_doi = 0.0
        luc_trieu = {}
        luc_gan_du = None
        luc_sai_map = 0.0
        luc_dau_sai_map = None
        luc_bat_dau = time.time()
        het_han_trieu = time.time() + GIAY_TOI_DA_CHO_GAN_NPC
        khoa_map = chuan_hoa(map_can)
        while True:
            if self.nen_dung():
                raise _Dung()
            self.doi.lam_moi()
            xy_gan = self._xy_npc_gan(ten_npc, xy) if ten_npc else xy
            tt_tr = self._tt()
            if tt_tr and chuan_hoa(tt_tr["map"]) != khoa_map:
                if self.doi:
                    self.doi.npc_gom = None
                    if chuan_hoa(tt_tr["map"]) == chuan_hoa(MAP_DAI_LY):
                        self.doi.di_lac_duong = True
                bay_gio = time.time()
                luc_dau_sai_map = luc_dau_sai_map or bay_gio
                if bay_gio - luc_dau_sai_map >= GIAY_TOI_DA_TRUONG_SAI_MAP:
                    raise _TruongSaiMap(tt_tr["map"], map_can)
                if bay_gio - luc_sai_map >= 60:
                    luc_sai_map = bay_gio
                    self.in_log(f"{self.ten}: PMP đội trưởng đang ở {tt_tr['map']}, không chạy tới NPC "
                                f"({xy_gan[0]}, {xy_gan[1]}) trên {map_can}")
                time.sleep(GIAY_CHO_GOM_DOI_RETRY)
                continue
            luc_dau_sai_map = None
            if self.doi:
                self.doi.npc_gom = (map_can, ten_npc, xy)
                if tt_tr:
                    self.doi.vi_tri_truong = (tt_tr["x"], tt_tr["y"], map_can)
            if ten_npc:
                self._truong_chay_toi_npc(ten_npc, xy, map_can)
            thieu = []
            for ten, luong in self.doi.cac_doi_vien.items():
                m = luong.map_hien_tai
                if chuan_hoa(m or "") != khoa_map:
                    thieu.append(f"{ten} (đang ở {m or '?'})")
                    continue
                try:
                    tt = luong.game.thong_tin()
                except (LoiLua, OSError, AttributeError):
                    thieu.append(f"{ten} (chưa đọc vị trí)")
                    continue
                if not tt or khoang_cach((tt["x"], tt["y"]), xy_gan) > KHOANG_GAN_NPC_SAT_TINH:
                    thieu.append(ten)
            if thieu and ten_npc and time.time() - luc_bat_dau >= GIAY_TOI_DA_CHO_GAN_NPC:
                self.in_log(f"{self.ten}: PMP chờ {', '.join(thieu)} tới NPC quá {GIAY_TOI_DA_CHO_GAN_NPC} giây, "
                            "vào phó bản với người đã tới")
                if self.doi:
                    self.doi.npc_gom = None
                return
            if not thieu:
                chua_theo = self.doi.chua_theo()
                if chua_theo:
                    cho = f"chờ {', '.join(chua_theo)} Theo đội"
                    self._mo_ta(cho)
                    bay_gio = time.time()
                    if luc_gan_du is None:
                        luc_gan_du = bay_gio
                    elif bay_gio - luc_gan_du >= GIAY_TOI_DA_MOI_THEO:
                        self.in_log(f"{self.ten}: PMP cả đội đã gần NPC ({xy_gan[0]}, {xy_gan[1]}), "
                                    "tiếp tục vào phó bản (không chờ Theo đội)")
                        return
                    if bay_gio - luc_theo_doi >= GIAY_GIUA_HAI_LAN_MOI_THEO:
                        luc_theo_doi = bay_gio
                        # Đội viên tự chạy tới NPC Sát Tinh sẽ mất theo; trưởng nhóm phải bấm lại Theo đội.
                        self._theo_doi(xy_gan)
                        self.doi.gui_trieu_tap(self.game, het_han_trieu, self.in_log, self.ten, luc_trieu)
                    if bay_gio - luc_bao >= 60:
                        luc_bao = bay_gio
                        self.in_log(f"{self.ten}: PMP {cho}")
                    time.sleep(GIAY_CHO_GOM_DOI_RETRY)
                    continue
                if self.doi:
                    self.doi.npc_gom = None
                return
            luc_gan_du = None
            cho = f"chờ {', '.join(thieu)} tới gần NPC ({xy_gan[0]}, {xy_gan[1]})"
            self._mo_ta(cho)
            bay_gio = time.time()
            if bay_gio - luc_bao >= 60:
                luc_bao = bay_gio
                self.in_log(f"{self.ten}: PMP {cho}")
            time.sleep(GIAY_CHO_GOM_DOI_RETRY)

    def _cho_load_map(self, ten_map):
        """Cả đội đã tới ten_map: đứng chờ GIAY_CHO_LOAD_MAP giây cho mọi nhân vật load xong rồi mới đi tiếp."""
        self._mo_ta(f"chờ {GIAY_CHO_LOAD_MAP} giây cho cả đội load xong {ten_map}")
        het_han = time.time() + GIAY_CHO_LOAD_MAP
        while time.time() < het_han:
            if self.nen_dung():
                raise _Dung()
            time.sleep(0.3)

    def _tap_hop_doi(self, map_gom=MAP_DAI_LY):
        """
        Đội trưởng ở map_gom: chờ mọi đội viên trong auto cũng ở map đó rồi bắt đầu (đã ở rồi thì không về thành).
        Theo đội bấm lúc chạy tới NPC, không chặn lúc gom đội. Tắt auto / tắt phó bản thì dừng.
        """
        if not self.doi:
            return
        o_map = la_lac_duong if chuan_hoa(map_gom) == chuan_hoa(MAP_LAC_DUONG) else la_dai_ly
        luc_bao = 0.0
        bat_dau = time.time()
        da_bao = None
        while True:
            if self.nen_dung():
                raise _Dung()
            self._tt()
            self.doi.lam_moi()
            bay_gio = time.time()
            if not self.doi.cac_doi_vien:
                if bay_gio - bat_dau >= GIAY_CHO_CO_DOI_VIEN:
                    self.in_log(f"{self.ten}: PMP không có đội viên nào trong auto bật Auto + Tự đi, đi một mình")
                    return
                self._mo_ta("chờ đội viên bật Auto + Tự đi")
                time.sleep(GIAY_CHO_GOM_DOI_RETRY)
                continue
            if da_bao != list(self.doi.cac_doi_vien):
                da_bao = list(self.doi.cac_doi_vien)
                self.in_log(f"{self.ten}: PMP gom đội ở {map_gom}: {', '.join(da_bao)}")
            maps = self.doi.map_doi_vien()
            chua_ve = [ten for ten, m in maps.items() if not o_map(m)]
            if chua_ve:
                chi_tiet = ", ".join(f"{ten} ({maps.get(ten) or '?'})" for ten in chua_ve)
                cho = f"chờ {chi_tiet} về {map_gom}"
                self._mo_ta(cho)
                if bay_gio - luc_bao >= 60:
                    luc_bao = bay_gio
                    self.in_log(f"{self.ten}: PMP {cho}")
                time.sleep(GIAY_CHO_GOM_DOI_RETRY)
                continue
            self._cho_load_map(map_gom)
            self.game.lua.chay(MA_THEO_DOI)
            ds = ", ".join(self.doi.cac_doi_vien)
            self.in_log(f"{self.ten}: PMP cả đội ({ds}) đã ở {map_gom}, bắt đầu đi")
            return

    def _cho_doi_gan_truong(self):
        """
        Đội trưởng đứng yên ở Đại Lý, chờ mọi đội viên tới gần mình (đội viên tự chạy tới qua doi.gom_truong).
        Quá GIAY_TOI_DA_CHO_GAN_TRUONG thì đi tiếp với người đã tới.
        """
        if not self.doi or not self.doi.cac_doi_vien:
            return
        self.doi.gom_truong = True
        luc_bao = 0.0
        bat_dau = time.time()
        try:
            while True:
                if self.nen_dung():
                    raise _Dung()
                self.doi.lam_moi()
                tt_tr = self._tt()
                if not tt_tr:
                    time.sleep(1)
                    continue
                xy_tr = (tt_tr["x"], tt_tr["y"])
                self.doi.vi_tri_truong = (xy_tr[0], xy_tr[1], MAP_DAI_LY)
                thieu = []
                for ten, luong in self.doi.cac_doi_vien.items():
                    if not la_dai_ly(luong.map_hien_tai):
                        thieu.append(f"{ten} (đang ở {luong.map_hien_tai or '?'})")
                        continue
                    try:
                        tt = luong.game.thong_tin()
                    except (LoiLua, OSError, AttributeError):
                        thieu.append(f"{ten} (chưa đọc vị trí)")
                        continue
                    if not tt or khoang_cach((tt["x"], tt["y"]), xy_tr) > KHOANG_GAN_TRUONG:
                        thieu.append(ten)
                if not thieu:
                    self.in_log(f"{self.ten}: PMP đủ đội viên quanh đội trưởng ({', '.join(self.doi.cac_doi_vien)})")
                    return
                bay_gio = time.time()
                if bay_gio - bat_dau >= GIAY_TOI_DA_CHO_GAN_TRUONG:
                    self.in_log(f"{self.ten}: PMP chờ {', '.join(thieu)} tới đội trưởng quá "
                                f"{GIAY_TOI_DA_CHO_GAN_TRUONG} giây, đi tiếp với người đã tới")
                    return
                cho = f"chờ {', '.join(thieu)} chạy tới đội trưởng"
                self._mo_ta(cho)
                if bay_gio - luc_bao >= 30:
                    luc_bao = bay_gio
                    self.in_log(f"{self.ten}: PMP {cho}")
                time.sleep(1)
        finally:
            self.doi.gom_truong = False
            self.doi.vi_tri_truong = None

    def _chuan_bi_di_tu_dai_ly(self):
        """Ở Đại Lý: gom đủ đội, đội viên chạy tới đội trưởng, rồi đội trưởng bấm Theo đội trước khi tới Di Chuyển."""
        if not self.doi or not la_dai_ly(self._map()):
            return
        self._hoi_mau_dai_ly_neu_can()
        bat_tap_hop(self.doi, MAP_DAI_LY)
        try:
            self._tap_hop_doi()
        finally:
            tat_tap_hop(self.doi)
        self._cho_doi_gan_truong()
        self.in_log(f"{self.ten}: PMP bấm Theo đội trước khi tới {BUOC_DI_CHUYEN_LAC_DUONG[1]}")
        self._theo_doi(BUOC_DI_CHUYEN_LAC_DUONG[2])
        self._cho_doi_theo()

    def _doi_vien_dang_cho_sat_tinh_tai_lac_duong(self):
        """
        Sau hết lượt PMP đội viên thường vẫn ở Lạc Dương (luồng theo đội không về Đại Lý khi còn Sát Tinh).
        Đội trưởng đã Về thành thì không gom ở Đại Lý — đi Di Chuyển sang Lạc Dương, gom ở đó.
        """
        if not self.doi:
            return False
        self.doi.lam_moi()
        maps = self.doi.map_doi_vien()
        if not maps:
            return False
        for m in maps.values():
            if m and not la_lac_duong(m) and not la_dai_ly(m):
                return False
        return any(la_lac_duong(m) for m in maps.values())

    def _ca_doi_dang_o_lac_duong(self):
        """Mọi đội viên trong auto đều đang ở Lạc Dương."""
        if not self.doi or not self.doi.cac_doi_vien:
            return la_lac_duong(self._map())
        self.doi.lam_moi()
        maps = self.doi.map_doi_vien()
        return maps and all(la_lac_duong(m) for m in maps.values())

    def _giu_lac_duong_sau_het_pmp(self, pmp, dem):
        """Hết PMP còn Sát Tinh: không cần về Đại Lý nếu đang / đội đang ở Lạc Dương (NPC Sát Tinh cạnh PMP)."""
        if not con_sat_tinh(pmp, dem) or la_map_trong_pho_ban(self._map()):
            return False
        if la_lac_duong(self._map()):
            return True
        return self._doi_vien_dang_cho_sat_tinh_tai_lac_duong()

    def _gom_sat_tinh_sau_het_pmp(self):
        """Hết lượt PMP ở Lạc Dương: triệu tập / gom đội quanh chỗ chờ Sát Tinh, không về thành."""
        if not la_lac_duong(self._map()):
            return
        if self.doi:
            self.doi.dat_buoc(giai_doan="gom_sat_tinh")
            self.doi.npc_gom = (MAP_LAC_DUONG, TEN_NPC_SAT_TINH, XY_NPC_SAT_TINH)
            self.doi.gom_truong = True
        luc_trieu = {}
        het_han_trieu = time.time() + GIAY_TOI_DA_CHO_GAN_TRUONG
        luc_bao = 0.0
        bat_dau = time.time()
        try:
            while time.time() - bat_dau < GIAY_TOI_DA_CHO_GAN_TRUONG:
                if self.nen_dung():
                    raise _Dung()
                if self.doi:
                    self.doi.lam_moi()
                tt = self._tt()
                if not tt or not la_lac_duong(tt["map"]):
                    break
                xy_gom = XY_CHO_SAT_TINH
                xy_tr = (tt["x"], tt["y"])
                if khoang_cach(xy_tr, xy_gom) > KHOANG_TOI_CHO_SAT_TINH:
                    _chay_toi_xy(self.game, xy_gom)
                    xy_tr = xy_gom
                if self.doi:
                    self.doi.vi_tri_truong = (xy_tr[0], xy_tr[1], MAP_LAC_DUONG)
                    self.doi.gui_trieu_tap(self.game, het_han_trieu, self.in_log, self.ten, luc_trieu)
                if not self.doi or not self.doi.cac_doi_vien:
                    break
                thieu = []
                for ten, luong in self.doi.cac_doi_vien.items():
                    if not la_lac_duong(luong.map_hien_tai):
                        thieu.append(f"{ten} (đang ở {luong.map_hien_tai or '?'})")
                        continue
                    try:
                        tt_dv = luong.game.thong_tin()
                    except (LoiLua, OSError, AttributeError):
                        thieu.append(f"{ten} (chưa đọc vị trí)")
                        continue
                    if not tt_dv or khoang_cach((tt_dv["x"], tt_dv["y"]), xy_gom) > KHOANG_GAN_TRUONG:
                        thieu.append(ten)
                if not thieu:
                    ds = ", ".join(self.doi.cac_doi_vien)
                    self.in_log(f"{self.ten}: PMP cả đội ({ds}) đã tập trung ở {MAP_LAC_DUONG} "
                                f"({xy_gom[0]}, {xy_gom[1]}) chờ Sát Tinh")
                    return
                bay_gio = time.time()
                if bay_gio - luc_bao >= 30:
                    luc_bao = bay_gio
                    self.in_log(f"{self.ten}: PMP chờ {', '.join(thieu)} tập trung chờ Sát Tinh")
                time.sleep(1)
            if self.doi and self.doi.cac_doi_vien:
                self.in_log(f"{self.ten}: PMP hết thời gian gom đội ở {MAP_LAC_DUONG}, tiếp tục Sát Tinh")
        finally:
            if self.doi:
                self.doi.gom_truong = False
                self.doi.vi_tri_truong = None
                self.doi.npc_gom = None

    def _cho_doi_theo(self):
        """Bấm Theo đội lại cho tới khi mọi đội viên đọc từ game đã ở chế độ theo (tối đa GIAY_TOI_DA_CHO_THEO)."""
        if not self.doi or not self.doi.cac_doi_vien:
            return
        het_han = time.time() + GIAY_TOI_DA_CHO_THEO
        luc_bam = time.time()
        luc_trieu = {}
        while True:
            if self.nen_dung():
                raise _Dung()
            chua = self.doi.chua_theo()
            if not chua:
                self.in_log(f"{self.ten}: PMP cả đội đã Theo đội ({', '.join(self.doi.cac_doi_vien)})")
                return
            bay_gio = time.time()
            if bay_gio >= het_han:
                self.in_log(f"{self.ten}: PMP {', '.join(chua)} chưa Theo đội sau {GIAY_TOI_DA_CHO_THEO} giây, "
                            "vẫn đi (đội viên chưa sang sẽ tự Di Chuyển)")
                return
            self._mo_ta(f"chờ {', '.join(chua)} Theo đội")
            if bay_gio - luc_bam >= GIAY_GIUA_HAI_LAN_MOI_THEO:
                luc_bam = bay_gio
                self.game.lua.chay(MA_THEO_DOI)
                self.doi.gui_trieu_tap(self.game, het_han, self.in_log, self.ten, luc_trieu)
            time.sleep(0.5)

    def _cho_doi_sang_lac_duong(self):
        """
        Sau Di Chuyển: chờ đội viên theo sang Lạc Dương. Ai bị bỏ lại ở Đại Lý thì bật di_lac_duong để đội viên đó tự
        đi NPC Di Chuyển, rồi chờ tới khi cả đội sang.
        """
        if not self.doi or not self.doi.cac_doi_vien:
            return
        het_han = time.time() + GIAY_CHO_THEO_SANG_MAP
        while time.time() < het_han:
            if self.nen_dung():
                raise _Dung()
            if all(la_lac_duong(m) for m in self.doi.map_doi_vien().values()):
                return
            time.sleep(1)
        chua = [ten for ten, m in self.doi.map_doi_vien().items() if not la_lac_duong(m)]
        if not chua:
            return
        self.in_log(f"{self.ten}: PMP {', '.join(chua)} không theo sang {MAP_LAC_DUONG}, tự đi NPC Di Chuyển")
        self.doi.di_lac_duong = True
        try:
            self._cho_doi_vien(MAP_LAC_DUONG)
        finally:
            self.doi.di_lac_duong = False

    def _theo_doi(self, xy, dan_doi=True):
        """Lên thú (nếu NPC xa) rồi luôn bấm Theo đội. Đổi map / F9 là mất theo đội."""
        if not self.doi or not dan_doi:
            return
        tt = self._tt()
        da_len_thu = False
        if tt and khoang_cach((tt["x"], tt["y"]), xy) > KHOANG_CACH_LEN_THU and not self._lua_dung(MA_DANG_CUOI) \
                and self._co_thu():
            if self._len_thu():
                da_len_thu = True
            else:
                self.in_log(f"{self.ten}: PMP dùng Kỵ thuật mà không lên được thú cưỡi, chạy bộ")
        if da_len_thu:
            time.sleep(0.4)
        self.game.lua.chay(MA_THEO_DOI)
        self.in_log(f"{self.ten}: PMP {'lên thú, ' if da_len_thu else ''}bấm Theo đội")
        if self.doi:
            self.doi.gui_trieu_tap(self.game, time.time() + GIAY_TOI_DA_CHO_THEO, self.in_log, self.ten, {})

    def _chay_qua(self, duong, dich):
        """
        Chạy lần lượt qua các điểm gấp khúc trên đường tới dich (giống đường đội trưởng chơi tay). Bỏ qua điểm nằm
        "sau lưng" (mình đã gần dich hơn điểm đó).
        """
        for diem in duong:
            tt = self._tt()
            if tt is None or khoang_cach((tt["x"], tt["y"]), dich) <= khoang_cach(diem, dich):
                continue
            self._mo_ta(f"chạy qua ({diem[0]}, {diem[1]})")
            self.game.lua.chay(f"AutoRunToTarget({diem[0]}, {diem[1]})")
            het_han = time.time() + GIAY_TOI_DA_MOT_DIEM
            vi_tri_cu, luc_di = (tt["x"], tt["y"]), time.time()
            while True:
                self._kiem_tra()
                tt = self._tt()
                bay_gio = time.time()
                if tt is not None:
                    vi_tri = (tt["x"], tt["y"])
                    if khoang_cach(vi_tri, diem) <= KHOANG_TOI_DIEM:
                        break
                    if khoang_cach(vi_tri, vi_tri_cu) >= 1:
                        vi_tri_cu, luc_di = vi_tri, bay_gio
                    elif bay_gio - luc_di >= GIAY_KET_O_DIEM:
                        break
                if bay_gio >= het_han:
                    break
                time.sleep(0.3)

    def _len_thu(self):
        bo_theo_doi(self.game)
        self.game.lua.chay(ma_dung_ky_nang_theo_dinh_nghia(KY_NANG_KY_THUAT))
        if self._cho(lambda: self._lua_dung(MA_DANG_CUOI), GIAY_CHO_LEN_THU):
            return True
        if self._lua_dung(MA_DA_CO_THU_CUOI) or not self._dam_bao_thu_cuoi():
            return False
        self.game.lua.chay(ma_dung_ky_nang_theo_dinh_nghia(KY_NANG_KY_THUAT))
        return bool(self._cho(lambda: self._lua_dung(MA_DANG_CUOI), GIAY_CHO_LEN_THU))

    def _co_thu(self):
        return self._lua_dung(ma_co_ky_nang(KY_NANG_KY_THUAT))

    # ---------- túi / thú cưỡi ----------

    def _tui(self):
        """{ô: (mã, số lượng)} của túi đạo cụ."""
        tui = {}
        for dong in self.game.lua.chay(MA_TUI).split(b"\n"):
            if dong:
                o, ma, so = dong.split(b"\t")
                tui[int(o)] = (int(float(ma)), int(float(so)))
        return tui

    def _so_luong(self, cac_ma):
        return sum(so for ma, so in self._tui().values() if ma in cac_ma)

    def _chuot_phai(self, o):
        self.game.lua.chay(MA_CHUOT_PHAI.replace("{o}", str(o)))

    def _chu_hoi_thoai(self):
        ht = self._hoi_thoai()
        return " / ".join(chu for loai, _, _, chu in ht[1] if loai in ("text", "info")) if ht else ""

    def _mang(self, cac_mon):
        """Mang (như chuột phải) mọi món trong cac_mon {mã: tên} đang có trong túi."""
        bo_qua = set()
        for _ in range(SO_LAN_DUNG_TOI_DA):
            self._kiem_tra()
            tui = self._tui()
            o = next((o for o, (ma, _) in sorted(tui.items()) if ma in cac_mon and o not in bo_qua), None)
            if o is None:
                return
            ma, _ = tui[o]
            self._mo_ta(f"mang {cac_mon[ma]}")
            self._chuot_phai(o)
            doi = self._cho(lambda: self._tui().get(o) != tui[o] or dang_hien(self.game.lua, "MessageBox_Self"),
                            GIAY_CHO_GAME_TRA_LOI)
            if doi and self._tui().get(o) == tui[o]:
                # Hộp "Trang bị sẽ bị khóa sau khi mang": bấm OK như người chơi (MessageBox_OnOKClick -> EquipItem).
                self.game.lua.chay(trong_cua_so("MessageBox_Self", "MessageBox_Self_OK_Clicked()"))
                doi = self._cho(lambda: self._tui().get(o) != tui[o], GIAY_CHO_GAME_TRA_LOI)
            if doi:
                self.in_log(f"{self.ten}: đã mang {cac_mon[ma]}")
            else:
                bo_qua.add(o)
                self.in_log(f"{self.ten}: không mang được {cac_mon[ma]} (ô {o + 1})")

    def _thu_cuoi(self):
        """
        Chưa mang thú cưỡi: Tiệm KNB -> Quảng Trường Hình Tượng, mua Đà Điểu (Thú Cưỡi Tân Thủ) và Kỵ Thuật: Đà Điểu
        (Kỵ Thuật) nếu túi chưa có, đóng shop, mang Đà Điểu, dùng Kỵ Thuật. True nếu đã mang thú cưỡi.
        """
        lua = self.game.lua
        if lua.chay(MA_DA_CO_THU_CUOI) != b"1":
            thieu = [mon for mon in (MON_THU_CUOI, MON_KY_THUAT) if not self._so_luong({mon[2]})]
            tiem = TiemKNB(lua)
            try:
                for nhom, ten, ma in thieu:
                    self._kiem_tra()
                    self._mo_ta(f"mua {ten}")
                    tiem.chon(TIEM_THU_CUOI, nhom)
                    o, gia = tiem.tim(ten)
                    tiem.bam_mua(o)
                    if not self._cho(lambda: self._so_luong({ma}), GIAY_CHO_GAME_TRA_LOI):
                        raise LoiVatPham(f"bấm mua {ten} ({gia} Điểm Tặng) mà túi không có (hết Điểm Tặng?)")
                    self.in_log(f"{self.ten}: đã mua {ten} ({gia} Điểm Tặng)")
            except LoiVatPham as loi:
                self.in_log(f"{self.ten}: không mua được thú cưỡi: {loi}")
                return False
            finally:
                tiem.dong()
            self._mang({MON_THU_CUOI[2]: MON_THU_CUOI[1]})
        _, ten, ma = MON_KY_THUAT
        for _ in range(SO_LAN_DUNG_KY_THUAT):
            o = next((o for o, (m, _) in sorted(self._tui().items()) if m == ma), None)
            if o is None:
                break
            con = self._so_luong({ma})
            self._mo_ta(f"dùng {ten}")
            self._chuot_phai(o)
            if not self._cho(lambda: self._so_luong({ma}) < con, GIAY_DUNG_KY_THUAT):
                self.in_log(f"{self.ten}: dùng {ten} không được ({self._chu_hoi_thoai()})")
                break
            self.in_log(f"{self.ten}: đã dùng {ten}")
        return lua.chay(MA_DA_CO_THU_CUOI) == b"1"

    def _dam_bao_thu_cuoi(self):
        """
        Đội trưởng chưa mang thú cưỡi (Kỵ thuật không lên được thú): mở Tiệm KNB mua Đà Điểu + Kỵ Thuật như lúc tạo nhân
        vật mới. Mỗi vòng chỉ thử một lần. True nếu đã có thú cưỡi.
        """
        try:
            if self._lua_dung(MA_DA_CO_THU_CUOI):
                return True
            if getattr(self, "_da_thu_mua_thu", False):
                return False
            self._da_thu_mua_thu = True
            self.in_log(f"{self.ten}: PMP chưa có thú cưỡi, mở Tiệm KNB mua {MON_THU_CUOI[1]}")
            bo_theo_doi(self.game)
            if self._thu_cuoi():
                self.in_log(f"{self.ten}: PMP đã mang thú cưỡi {MON_THU_CUOI[1]}")
                return True
            return False
        except LoiLua as loi:
            self.in_log(f"{self.ten}: PMP không mua được thú cưỡi: {loi}")
            return False

    def _tu_dung_can_khon_ho(self):
        """Hết buff Càn Khôn Hồ: túi hết thì mở Tiệm KNB mua, rồi dùng (như lúc tạo nhân vật mới)."""
        if getattr(self, "_ckh", None) is None:
            self._ckh = TuDungCanKhonHo(self.game.lua, self.in_log)
        try:
            self._ckh.kiem_tra(self.ten, self.nen_dung)
        except LoiLua as loi:
            self.in_log(f"{self.ten}: PMP không kiểm tra được Càn Khôn Hồ: {loi}")

    def _dung_tai(self, diem):
        """Chạy hẳn tới diem (cả đội đang theo), đứng GIAY_DUNG_TRUOC_BO_THEO giây cho đội viên tới kịp."""
        self._mo_ta(f"dẫn đội tới ({diem[0]}, {diem[1]}), đứng chờ rồi bỏ theo")
        self.game.lua.chay(f"AutoRunToTarget({diem[0]}, {diem[1]})")
        self._cho(lambda: (lambda tt: tt and khoang_cach((tt["x"], tt["y"]), diem) <= 1)(self._tt()), GIAY_TOI_DA_MOT_DIEM)
        het_han = time.time() + GIAY_DUNG_TRUOC_BO_THEO
        while time.time() < het_han:
            self._kiem_tra()
            time.sleep(0.3)

    def _giu_thu(self):
        """Đội trưởng không đánh (truong_khong_danh): bị xuống thú thì lên lại."""
        if not (self.doi and self.doi.truong_dang_khong_danh()) or self._lua_dung(MA_DANG_CUOI):
            return
        if not self._len_thu():
            self.in_log(f"{self.ten}: PMP dùng Kỵ thuật mà không lên được thú cưỡi")

    def _bo_theo_doi(self):
        if self.doi:
            bo_theo_doi(self.game)

    # ---------- các bước ----------

    def _mo_hoi_thoai(self, ten_npc, xy, dong_can, bo_qua_neu_khong_co=False, duong=(), dan_doi=True,
                      giu_theo=False):
        """
        Chạy tới NPC (qua các điểm gấp khúc duong) và mở hội thoại có dòng dong_can (script, extra). Trả về True khi
        đã mở. bo_qua_neu_khong_co: NPC không có mặt hoặc hội thoại không có dòng đó (ải đã qua) thì trả về False.
        dan_doi: đi tổ đội thì bấm Theo đội trước khi chạy (False: chỉ lên thú, đội trưởng đi một mình).
        giu_theo: NPC dịch chuyển cả đội — không bỏ theo đội khi đứng cạnh NPC (bỏ thì đội viên bị bỏ lại),
        trừ khi kẹt quá GIAY_KET_GIU_THEO giây vẫn chưa mở được hội thoại.
        """
        khoa_npc = chuan_hoa(ten_npc)
        self._theo_doi(xy, dan_doi)
        self._chay_qua(duong, xy)
        luc_chay = luc_toi = 0.0
        luc_gan = luc_go_ket = luc_bao_ket = 0.0
        lan_goi = 0
        het_han = time.time() + GIAY_CHAY_TOI_NPC
        while True:
            self._kiem_tra()
            ht = self._hoi_thoai()
            if ht is not None:
                muc_tieu, cac_dong = ht
                if getattr(self, "che_do", None) == "ac_tac" and any(
                        loai == "id" and (chu or "").strip() for loai, _, _, chu in cac_dong):
                    if not khoa_npc or chuan_hoa(muc_tieu or "") == khoa_npc:
                        return True
                for _, _, _, chu in cac_dong:
                    if self.che_do == "pmp" and self._la_bao_het_pmp_thuong(chu):
                        raise _HetLuot(chu)
                if getattr(self, "_vao_het_so", False):
                    ly_do = self._chu_het_pmp_so([chu for _, _, _, chu in cac_dong])
                    if ly_do:
                        raise _HetPmpSo(ly_do)
                if any(self._dong_khop(dong_can, s, e, chu) for _, s, e, chu in cac_dong):
                    return True
                if bo_qua_neu_khong_co and chuan_hoa(muc_tieu) == khoa_npc and cac_dong:
                    return False
            tt = self._tt()
            if tt is None:
                time.sleep(0.5)
                continue
            vi_tri = (tt["x"], tt["y"])
            cung_ten_npc = [d for ten, d in self._quanh() if ten == khoa_npc and d.hp > 0]
            cac_npc = [d for d in cung_ten_npc if khoang_cach((d.x, d.y), xy) <= BAN_KINH_DANH] or cung_ten_npc
            npc = min(cac_npc, key=lambda d: khoang_cach(vi_tri, (d.x, d.y)), default=None)
            dich = (int(npc.x), int(npc.y)) if npc else xy
            bay_gio = time.time()
            if getattr(self, "che_do", None) == "sat_tinh" and npc is not None \
                    and khoang_cach(vi_tri, dich) <= KHOANG_GAN_NPC_SAT_TINH:
                luc_gan = luc_gan or bay_gio
                if bay_gio - luc_gan >= GIAY_KET_CANH_NPC and bay_gio - luc_go_ket >= GIAY_KET_CANH_NPC:
                    luc_go_ket = luc_chay = bay_gio
                    if not giu_theo or bay_gio - luc_gan >= GIAY_KET_GIU_THEO:
                        bo_theo_doi(self.game)
                    self.game.lua.chay(f"SetMainTargetFromList({npc.id}, true, true) "
                                       f"AutoRunToTarget({dich[0]}, {dich[1]}) "
                                       f"SetAutoRunTargetNPCName({chuoi_lua(ten_npc)})")
                    if bay_gio - luc_bao_ket >= 30:
                        luc_bao_ket = bay_gio
                        self.in_log(f"{self.ten}: đứng cạnh {ten_npc} {int(bay_gio - luc_gan)}s chưa mở hội thoại, "
                                    "chọn lại NPC")
                    time.sleep(0.4)
                    continue
            else:
                luc_gan = 0.0
            if khoang_cach(vi_tri, dich) <= KHOANG_MO_HOI_THOAI:
                luc_toi = luc_toi or bay_gio
                if npc is None and bo_qua_neu_khong_co and bay_gio - luc_toi >= GIAY_DUNG_CANH_NPC:
                    return False
                if npc is not None and bay_gio - luc_chay >= GIAY_CHAY_LAI:
                    if self.che_do == "pmp" and self.doi and (not giu_theo or bay_gio - luc_toi >= GIAY_KET_GIU_THEO):
                        bo_theo_doi(self.game)
                    # Đứng sát NPC mà hội thoại chưa mở (vd. vừa đổi map đã ở cạnh NPC nên chưa từng "chạy tới"):
                    # chạy tới đúng chỗ NPC kèm tên, rồi lùi ra xa để chạy lại, cuối cùng chọn NPC làm mục tiêu.
                    lan_goi += 1
                    cach = lan_goi % 3
                    if cach == 1:
                        self.game.lua.chay(f"AutoRunToTarget({int(npc.x)}, {int(npc.y)}) "
                                           f"SetAutoRunTargetNPCName({chuoi_lua(ten_npc)})")
                    elif cach == 2:
                        dx, dy = vi_tri[0] - npc.x, vi_tri[1] - npc.y
                        dai = max(khoang_cach(vi_tri, (npc.x, npc.y)), 0.1)
                        if dai < 1:
                            dx, dy, dai = 1.0, 0.0, 1.0
                        lui = (int(npc.x + dx / dai * KHOANG_LUI_KHOI_NPC), int(npc.y + dy / dai * KHOANG_LUI_KHOI_NPC))
                        self.game.lua.chay(f"AutoRunToTarget({lui[0]}, {lui[1]})")
                    else:
                        self.game.lua.chay(f"SetMainTargetFromList({npc.id}, true, true)")
                    luc_chay = bay_gio
                    if cach == 2:
                        luc_chay = bay_gio - GIAY_CHAY_LAI + 3
            else:
                luc_toi = 0.0
                if bay_gio - luc_chay >= GIAY_CHAY_LAI:
                    self.game.lua.chay(f"AutoRunToTarget({dich[0]}, {dich[1]}) "
                                       f"SetAutoRunTargetNPCName({chuoi_lua(ten_npc)})")
                    luc_chay = bay_gio
            if bay_gio >= het_han:
                if bo_qua_neu_khong_co and npc is None:
                    return False
                raise LoiPhoBan(f"không mở được hội thoại {ten_npc} sau {GIAY_CHAY_TOI_NPC} giây")
            time.sleep(0.4)

    def _chon(self, dong):
        self._doc_thong_bao()
        self.game.lua.chay(f"QuestFrameOptionClicked(-1, {dong[0]}, {dong[1]})")

    def _chon_dong(self, dong):
        if isinstance(dong[0], str):
            goi = chuan_hoa(dong[0])
            ht = self._hoi_thoai()
            if not ht:
                raise LoiPhoBan(f"không mở hội thoại để chọn «{dong[0]}»")
            for _, s, e, chu in ht[1]:
                if goi in chuan_hoa(chu):
                    self._chon((s, e))
                    return
            ds = [c[3] for c in ht[1] if c[3]]
            self.in_log(f"{self.ten}: PMP hội thoại có {len(ds)} dòng: "
                        f"{'; '.join(ds[:6])}{'…' if len(ds) > 6 else ''}")
            raise LoiPhoBan(f"không thấy dòng «{dong[0]}» ({', '.join(ds)})")
        self._chon(dong)

    def _hoi_mau_dai_ly_neu_can(self):
        if not getattr(self, "ten", None):
            return
        try:
            _HoiMauDaiLy(self.game, self.ten, self.in_log, getattr(self, "nen_dung", lambda: False)).thuc_hien()
        except _Dung:
            raise

    def _ve_thanh(self):
        if la_dai_ly(self._map()):
            if self.doi:
                self.doi.xoa_lenh_gom()
            self._hoi_mau_dai_ly_neu_can()
            return
        self._mo_ta("về thành")
        map_dau = self._map()
        for _ in range(SO_LAN_THU):
            if not chuan_bi_ve_thanh(self.game):
                self.in_log(f"{self.ten}: PMP chưa bỏ được theo đội / xuống thú, vẫn thử dùng kỹ năng Về thành")
            if not self.game.lua.chay(ma_dung_ky_nang_theo_dinh_nghia(KY_NANG_VE_THANH)):
                raise LoiPhoBan("nhân vật không có kỹ năng Quay về Đại Lý thành")
            moi = self._cho(lambda: (lambda m: m if m and m != map_dau else None)(self._map()), GIAY_CHO_VE_THANH)
            if moi:
                if chuan_hoa(moi) != chuan_hoa(MAP_DAI_LY):
                    raise LoiPhoBan(f"kỹ năng Về thành đưa tới [{moi}], không phải {MAP_DAI_LY}")
                self.in_log(f"{self.ten}: PMP đã về {MAP_DAI_LY} bằng kỹ năng Về thành")
                if self.doi:
                    self.doi.xoa_lenh_gom()
                self._hoi_mau_dai_ly_neu_can()
                return
        raise LoiPhoBan(f"dùng kỹ năng Về thành {SO_LAN_THU} lần mà vẫn chưa về thành "
                        f"({'; '.join(self.thong_bao[-3:])})")

    @staticmethod
    def _thu_ve_thanh_mot(game, ten, in_log=None):
        """Một lần bấm Quay về Đại Lý (bỏ theo đội / xuống thú trước)."""
        try:
            if not chuan_bi_ve_thanh(game):
                if in_log:
                    in_log(f"{ten}: PMP chưa bỏ được theo đội / xuống thú, vẫn thử Về thành")
            return bool(game.lua.chay(ma_dung_ky_nang_theo_dinh_nghia(KY_NANG_VE_THANH)))
        except LoiLua:
            return False

    def _map_game_cua_doi(self):
        """(tên, game) trưởng + đội viên."""
        ds = [(self.ten, self.game)]
        if self.doi:
            for ten, luong in self.doi.cac_doi_vien.items():
                if luong.game:
                    ds.append((ten, luong.game))
        return ds

    def _ve_dai_ly_ca_doi_retry(self, doi):
        """
        Sau step 5: game không tự đưa về Đại Lý — mỗi nhân vật bấm kỹ năng Về thành, lặp mỗi GIAY_RETRY_VE_SAU_BOSS.
        """
        luc_bat_dau = time.time()
        if doi:
            doi.cho_ve_sau_boss = luc_bat_dau
        self.in_log(f"{self.ten}: PMP xong boss — chỉ dùng kỹ năng về {MAP_DAI_LY} (game không tự về)")
        luc_ve = {}
        het_han = luc_bat_dau + max(GIAY_CHO_VE_THANH, GIAY_CHO_DOI_VIEN_VE)
        chua = []
        try:
            while time.time() < het_han:
                self._kiem_tra()
                chua = []
                for ten, game in self._map_game_cua_doi():
                    try:
                        tt = game.thong_tin()
                        map_hien = (tt or {}).get("map") or ""
                    except (LoiLua, OSError):
                        map_hien = ""
                    if la_dai_ly(map_hien):
                        continue
                    chua.append((ten, game, map_hien))
                if not chua:
                    self.in_log(f"{self.ten}: PMP cả đội đã về {MAP_DAI_LY}")
                    if doi:
                        doi.xoa_lenh_gom()
                    return
                bay_gio = time.time()
                for ten, game, map_hien in chua:
                    if bay_gio - luc_ve.get(ten, 0) < GIAY_RETRY_VE_SAU_BOSS:
                        continue
                    luc_ve[ten] = bay_gio
                    if not self._thu_ve_thanh_mot(game, ten, self.in_log):
                        self.in_log(f"{ten}: PMP không dùng được kỹ năng Quay về Đại Lý")
                    elif map_hien and not la_map_trong_pho_ban(map_hien):
                        self.in_log(f"{ten}: PMP thử lại về {MAP_DAI_LY} (đang ở [{map_hien}])")
                    else:
                        self.in_log(f"{ten}: PMP thử lại về {MAP_DAI_LY} sau boss")
                time.sleep(0.4)
            ten_chua = ", ".join(t for t, _, _ in chua)
            raise LoiPhoBan(f"sau boss chưa về {MAP_DAI_LY}: {ten_chua}")
        finally:
            if doi:
                doi.cho_ve_sau_boss = None

    def _doi_vien_lech_map(self):
        """Đội viên trong auto đang ở map khác đội trưởng: "tên (map), ...", rỗng nếu cả đội cùng map."""
        if not self.doi or not self.doi.cac_doi_vien:
            return ""
        m = self._map()
        if not m:
            return ""
        self.doi.lam_moi()
        lech = [f"{ten} ({mv})" for ten, mv in self.doi.map_doi_vien().items()
                if mv and chuan_hoa(mv) != chuan_hoa(m)]
        return ", ".join(lech)

    def _gom_doi_neu_lech_map(self):
        """
        Đầu vòng, đội trưởng ngoài Đại Lý (vd. Lạc Dương) mà đội viên ở map khác: cả đội cùng dùng kỹ năng Quay về Đại
        Lý để đứng chung một chỗ, rồi đội trưởng dẫn đội đi phó bản như bình thường. True nếu đã về.
        """
        m = self._map()
        if not self.doi or not m or la_dai_ly(m) or la_map_trong_pho_ban(m):
            return False
        lech = self._doi_vien_lech_map()
        if not lech:
            return False
        self.in_log(f"{self.ten}: PMP đội trưởng ở {m}, đội viên ở map khác ({lech}) — cả đội dùng kỹ năng về "
                    f"{MAP_DAI_LY} rồi đi lại từ đầu")
        bat_tap_hop(self.doi, MAP_DAI_LY)
        try:
            self._ca_doi_ve_thanh()
        finally:
            tat_tap_hop(self.doi)
        return True

    def _ca_doi_ve_thanh(self):
        """Đội trưởng dùng kỹ năng Về thành cho mọi đội viên trong auto cùng lúc với mình (không chờ luồng đội viên)."""
        try:
            self._ve_dai_ly_ca_doi_retry(self.doi)
        except LoiPhoBan:
            raise

    def _vao(self, buoc, het_so=False):
        map_o, ten_npc, xy, cac_dong, map_toi = buoc
        self._vao_het_so = het_so

        def da_toi():
            m = self._map()
            if not m or chuan_hoa(m) != chuan_hoa(map_toi):
                return False
            self.in_log(f"{self.ten}: PMP {ten_npc} đã đưa tới [{m}]")
            if self.doi:
                tat_tap_hop(self.doi)
                self.doi.npc_gom = None
                self.doi.di_lac_duong = False
            return True

        def gom_doi():
            try:
                self._cho_doi_gan_xy(xy, map_o, ten_npc)
            except _TruongSaiMap:
                if da_toi():
                    return True
                raise
            return False

        for lan in range(1, SO_LAN_THU + 1):
            if da_toi():
                return
            if self.doi and chuan_hoa(self._map() or "") == chuan_hoa(map_o) and gom_doi():
                return
            self._mo_ta(f"tới {ten_npc}")
            self._mo_hoi_thoai(ten_npc, xy, cac_dong[0], giu_theo=True)
            het = self._chu_het_luot()
            if het:
                self._het_luot(het)
                raise _Dung()
            for i, dong in enumerate(cac_dong):
                if i and not self._cho(lambda d=dong: (lambda ht: ht and any(
                        self._dong_khop(d, s, e, chu) for _, s, e, chu in ht[1]))(self._hoi_thoai()), GIAY_MO_HOI_THOAI):
                    break
                self._kiem_tra_het_pmp_so_hoi_thoai()
                self._chon_dong(dong)
                time.sleep(0.5)
                self._kiem_tra_het_pmp_so_hoi_thoai()
            else:
                def _sau_chon_vao_pmp():
                    self._kiem_tra_het_pmp_so_hoi_thoai()
                    m = self._map()
                    if m and chuan_hoa(m) != chuan_hoa(map_o):
                        return m
                    het = self._het_trong_hoi_thoai()
                    return het

                moi = self._cho(_sau_chon_vao_pmp, GIAY_CHO_DOI_MAP)
                if moi and not moi.startswith("#het:"):
                    self.in_log(f"{self.ten}: PMP {ten_npc} đưa tới [{moi}]")
                    if self.doi:
                        tat_tap_hop(self.doi)
                        self.doi.npc_gom = None
                        self.doi.di_lac_duong = False
                    return
                if moi:
                    self._het_luot(moi[len("#het:"):])
                    raise _Dung()
                het = self._chu_het_luot()
                if het:
                    self._het_luot(het)
                    raise _Dung()
                ly_do = [chu for chu in self._doc_thong_bao() if chu]
                if ly_do:
                    self._het_luot("; ".join(ly_do[-3:]))
                    raise _Dung()
            if getattr(self, "_vao_het_so", False):
                self._kiem_tra_het_pmp_so_hoi_thoai()
            if da_toi():
                return
            self.in_log(f"{self.ten}: PMP {ten_npc} chưa đưa đi, thử lại lần {lan + 1}" if lan < SO_LAN_THU else
                        f"{self.ten}: PMP {ten_npc} vẫn chưa đưa đi")
            if lan < SO_LAN_THU and self.doi:
                if gom_doi():
                    return
                time.sleep(GIAY_CHO_GOM_DOI_RETRY)
        if da_toi():
            return
        lech = self._doi_vien_lech_map()
        if lech:
            # NPC không đưa đi vì đội viên không ở cùng chỗ, không phải hết lượt: cả đội về Đại Lý gom lại.
            raise _TreoPMP(f"{ten_npc} chưa đưa đi vì đội viên không cùng map ({lech})")
        if map_toi == MAP_PMP and getattr(self, "_vao_het_so", False):
            ht = self._hoi_thoai()
            if ht:
                ly_do = self._chu_het_pmp_so([chu for _, _, _, chu in ht[1]])
                if ly_do:
                    raise _HetPmpSo(ly_do)
        if map_toi == MAP_PMP:
            # Chọn khiêu chiến đủ lần mà không vào được: coi như hết lượt để cả đội về Đại Lý đi tiếp Sát Tinh.
            self._het_luot(f"{ten_npc} {SO_LAN_THU} lần không đưa vào {MAP_PMP}")
            raise _Dung()
        raise LoiPhoBan(f"{ten_npc} không đưa tới {map_toi}")

    def _dat_buoc(self, so, giai, ai, vung=None):
        """Ghi step hiện tại cho cả đội: chỉ đánh khi giai == 'danh' và đúng quái của ải."""
        if self.doi:
            self.doi.dat_buoc(so, giai, ai.cac_quai, vung)
        if giai == "danh" and vung and not (self.doi and self.doi.truong_dang_khong_danh()):
            self.dat_vung_danh(vung)
        else:
            self.dat_vung_rieng(None)
            if self.doi:
                self.doi.vung = vung if giai == "danh" else None
        self._mo_ta(f"{ai.ten} ({so}/{len(CAC_AI)}) "
                    f"{'đánh ' + ', '.join(ai.cac_quai) if giai == 'danh' else ai.npc}")

    def _ai_tiep_theo(self):
        """
        Ải đang làm (1..5): còn quái sống của ải, còn hội thoại khiêu chiến, hoặc NPC ải gần nhất.
        Dùng lúc vào phó bản giữa chừng để không chạy lại ải đã xong.
        """
        quanh = list(self._quanh())
        ht = self._hoi_thoai()
        if ht:
            for so, ai in enumerate(CAC_AI, 1):
                if any((s, e) == ai.dong for _, s, e, _ in ht[1]):
                    return so
        for so, ai in enumerate(CAC_AI, 1):
            quai = {chuan_hoa(ten) for ten in ai.cac_quai}
            if any(ten in quai and d.hp > 0 and khoang_cach((d.x, d.y), ai.diem_danh) <= BAN_KINH_DANH + 5
                   for ten, d in quanh):
                return so
        gan = []
        for so, ai in enumerate(CAC_AI, 1):
            for ten, d in quanh:
                if ten == chuan_hoa(ai.npc) and d.hp > 0:
                    gan.append((khoang_cach((d.x, d.y), ai.xy), so))
        if gan:
            return min(gan)[1]
        tt = self._tt()
        if tt:
            vi = (tt["x"], tt["y"])
            return min(range(1, len(CAC_AI) + 1), key=lambda i: khoang_cach(vi, CAC_AI[i - 1].xy))
        return 1

    def _quai_ai(self, ai):
        """can_giet, {id: tên} còn sống, {id: tên} xác của ải."""
        can_giet = {chuan_hoa(ten) for ten in ai.cac_quai}
        song, xac = {}, {}
        for ten, d in self._quanh():
            if ten not in can_giet:
                continue
            (song if d.hp > 0 else xac)[d.id] = ten
        return can_giet, song, xac

    def _danh(self, so, ai, id_truoc=()):
        """
        Chờ quái của ải xuất hiện (còn sống) rồi đánh đến khi tất cả đã chết mới sang ải sau.
        NPC biến mất lúc hóa quái không được tính là đã chết.
        """
        can_giet = {chuan_hoa(ten) for ten in ai.cac_quai}
        id_truoc = set(id_truoc)
        da_thay = {}   # tên -> đã thấy sống (quái đánh, không phải NPC lúc nói chuyện)
        da_chet = {}   # tên -> lúc chết
        mau_cuoi = {}  # tên -> máu (0..1) lần cuối thấy sống
        dang_an = set()
        da_dat_vung = False
        bat_dau_danh = False
        luc_cho = time.time()
        het_han = luc_cho + (GIAY_DANH_AI_AN_THAN if ai.an_than else GIAY_DANH_MOT_AI)
        giay_treo = GIAY_TREO_AI_AN_THAN if ai.an_than else GIAY_TREO_PMP_KHONG_QUAI
        luc_bao = 0.0
        luc_co_quai = time.time()
        while True:
            self._kiem_tra()
            bay_gio = time.time()
            for chu in self._doc_thong_bao():
                if chu.strip() == THONG_BAO_BAT_DAU_DANH:
                    bat_dau_danh = True
            can_giet, song, xac = self._quai_ai(ai)
            quanh = list(self._quanh())
            if song or any(ten in can_giet for ten, _ in quanh):
                luc_co_quai = bay_gio
            elif bay_gio - luc_co_quai >= giay_treo:
                raise _TreoPMP()
            if ai.an_than:
                for ten, d in quanh:
                    if ten in can_giet and d.hp > 0 and d.id in song:
                        if ten in mau_cuoi and d.hp < mau_cuoi[ten] - 0.005:
                            het_han = max(het_han, bay_gio + GIAY_DANH_MOT_AI)
                        mau_cuoi[ten] = d.hp
            chap_id_cu = bat_dau_danh or bay_gio - luc_cho >= GIAY_CHO_QUAI_XUAT_HIEN
            for ma_id, ten in song.items():
                if ma_id in id_truoc and not chap_id_cu:
                    continue
                da_thay[ten] = ma_id
                bat_dau_danh = True
                da_chet.pop(ten, None)
                if not da_dat_vung:
                    self._dat_buoc(so, "danh", ai, (*ai.diem_danh, BAN_KINH_DANH))
                    da_dat_vung = True
            for ten in list(da_thay):
                if any(t == ten for t in song.values()):
                    da_chet.pop(ten, None)
                    if ten in dang_an:
                        dang_an.discard(ten)
                        self.in_log(f"{self.ten}: PMP {ai.ten}: {ten} hiện lại "
                                    f"({round(mau_cuoi.get(ten, 0) * 100)}% máu), đánh tiếp")
                elif ten in da_chet:
                    continue
                elif not ai.an_than or ten in xac.values() or mau_cuoi.get(ten, 1) <= MAU_COI_NHU_CHET:
                    da_chet[ten] = bay_gio
                elif ten not in dang_an:
                    dang_an.add(ten)
                    self.in_log(f"{self.ten}: PMP {ai.ten}: {ten} ẩn thân "
                                f"(còn {round(mau_cuoi.get(ten, 1) * 100)}% máu), cả đội đứng chờ hiện lại")
            if can_giet <= set(da_thay) and can_giet <= set(da_chet):
                if bay_gio - max(da_chet.values()) >= GIAY_SAU_CON_CUOI and not song:
                    self.in_log(f"{self.ten}: PMP {ai.ten}: đã giết {', '.join(ai.cac_quai)}")
                    return
            chua_ra = [ten for ten in ai.cac_quai if chuan_hoa(ten) not in da_thay]
            chua_chet = [ten for ten in ai.cac_quai if chuan_hoa(ten) not in da_chet]
            if bay_gio - luc_bao >= 8:
                luc_bao = bay_gio
                self._giu_thu()
                if chua_ra:
                    self._mo_ta(f"{ai.ten}: chờ {', '.join(chua_ra)} xuất hiện")
                elif dang_an:
                    self._mo_ta(f"{ai.ten}: {', '.join(sorted(dang_an))} ẩn thân, chờ hiện lại")
                else:
                    self._mo_ta(f"{ai.ten}: đánh {', '.join(chua_chet)}")
            if bay_gio >= het_han:
                thieu = chua_ra or chua_chet
                raise LoiPhoBan(f"{ai.ten} quá {round(het_han - luc_cho)} giây chưa "
                                f"{'thấy' if chua_ra else 'giết'} {', '.join(thieu)}")
            time.sleep(0.3)

    def _qua_ai(self, so, ai):
        self._dat_buoc(so, "di", ai)
        self.in_log(f"{self.ten}: PMP step {so}/{len(CAC_AI)} {ai.ten} → {ai.npc}")
        id_truoc = set()
        for lan in range(1, SO_LAN_THU_AI + 1):
            self.het_han_lan_thu = time.time() + GIAY_MOT_LAN_THU_AI
            try:
                da_mo = self._mo_hoi_thoai(ai.npc, ai.xy, ai.dong, bo_qua_neu_khong_co=True, duong=ai.duong,
                                           dan_doi=ai.dan_doi)
            except _HetGioLanThu:
                da_mo = False
            finally:
                self.het_han_lan_thu = None
            if da_mo:
                can_giet = {chuan_hoa(ten) for ten in ai.cac_quai}
                id_truoc = {d.id for ten, d in self._quanh() if ten in can_giet}
                self._dat_buoc(so, "noi", ai)
                self._chon(ai.dong)
                self.in_log(f"{self.ten}: PMP {ai.ten} ({so}/{len(CAC_AI)}) {ai.npc}: đã chọn khiêu chiến")
                time.sleep(GIAY_CHO_BO_THEO)
                if ai.giu_theo:
                    self._chay_qua(ai.duong_danh + (ai.diem_danh,), ai.diem_danh)
                    self._dung_tai(ai.diem_danh)
                break
            _, song, _ = self._quai_ai(ai)
            if song:
                self.in_log(f"{self.ten}: PMP {ai.ten}: không còn dòng khiêu chiến, quái đã ra, vào đánh")
                break
            if lan >= SO_LAN_THU_AI:
                raise _TreoPMP(f"step {so}/{len(CAC_AI)} {ai.ten} {ai.npc}: thử {SO_LAN_THU_AI} lần "
                               f"(mỗi lần {GIAY_MOT_LAN_THU_AI}s) chưa mở khiêu chiến")
            self.in_log(f"{self.ten}: PMP {ai.ten} {ai.npc}: chưa mở khiêu chiến, thử lại lần {lan + 1}/{SO_LAN_THU_AI} "
                        f"(tối đa {GIAY_MOT_LAN_THU_AI}s)")
        self._bo_theo_doi()
        self._giu_thu()
        self.game.lua.chay(f"AutoRunToTarget({ai.diem_danh[0]}, {ai.diem_danh[1]})")
        try:
            self._danh(so, ai, id_truoc)
        except LoiPhoBan as loi:
            if self.doi and self.doi.truong_dang_khong_danh():
                self.doi.truong_khong_danh = False
                self.doi.truong_vao_danh = True
                self.in_log(f"{self.ten}: PMP {loi}, đội trưởng xuống thú đánh cùng, thử đánh lại")
            else:
                self.in_log(f"{self.ten}: PMP {loi}, thử đánh lại")
            try:
                self._danh(so, ai, id_truoc)
            except LoiPhoBan as loi_2:
                # Ở lại trong ải nghỉ rồi thử tiếp chỉ lặp lại ải đó mãi: về Đại Lý chạy vòng mới.
                raise _TreoPMP(str(loi_2)) from loi_2
        finally:
            self._dat_buoc(so, "di", ai)

    def _het_luot(self, ly_do, so=None):
        if so is None:
            so = getattr(self, "_vao_het_so", False)
        loai = "Sơ Phiêu Miểu Phong" if so else "Phiêu Miểu Phong thường"
        self.in_log(f"{self.ten}: PMP {loai} hết lượt hôm nay: {ly_do}")
        try:
            self.game.lua.chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
        except LoiLua:
            pass

        def sua(cai_dat):
            pmp = cai_dat.setdefault("pho_ban_pmp", dict(cau_hinh.MAC_DINH_PHO_BAN_PMP))
            dem = hom_nay(pmp)
            if so:
                dem["so_het_luot"] = True
            else:
                dem["het_luot"] = True
            pmp["hom_nay"] = dem
        ten_ds = [self.ten]
        if self.doi:
            ten_ds += list(self.doi.cac_doi_vien)
            bat_tap_hop(self.doi, MAP_DAI_LY)
            self.doi.dat_buoc()
        for ten in ten_ds:
            cau_hinh.sua_nhan_vat(ten, sua)
        self.bao_doi()
        pmp = cai_dat_pmp(cau_hinh.cua_nhan_vat(self.ten))
        dem = hom_nay(pmp)
        if self._giu_lac_duong_sau_het_pmp(pmp, dem):
            if la_lac_duong(self._map()):
                self.in_log(f"{self.ten}: PMP hết lượt, giữ đội ở {MAP_LAC_DUONG} (NPC Sát Tinh cạnh PMP), "
                            f"không về {MAP_DAI_LY}")
                self._gom_sat_tinh_sau_het_pmp()
            else:
                self.in_log(f"{self.ten}: PMP hết lượt, đội viên đang ở {MAP_LAC_DUONG} — không triệu về {MAP_DAI_LY}")
        elif la_map_trong_pho_ban(self._map()):
            self.in_log(f"{self.ten}: PMP bỏ theo đội, cả đội về {MAP_DAI_LY}")
            try:
                self._ca_doi_ve_thanh()
            except LoiPhoBan as loi:
                self.in_log(f"{self.ten}: PMP hết lượt mà chưa về thành: {loi}")
            if self.doi:
                het_han = time.time() + GIAY_CHO_VE_THANH
                while time.time() < het_han:
                    if self.nen_dung():
                        break
                    if all(la_dai_ly(m) for m in self.doi.map_doi_vien().values()):
                        break
                    time.sleep(1)
        elif not con_sat_tinh(pmp, dem):
            self.in_log(f"{self.ten}: PMP bỏ theo đội, cả đội về {MAP_DAI_LY}")
            try:
                self._ca_doi_ve_thanh()
            except LoiPhoBan as loi:
                self.in_log(f"{self.ten}: PMP hết lượt mà chưa về thành: {loi}")
            if self.doi:
                het_han = time.time() + GIAY_CHO_VE_THANH
                while time.time() < het_han:
                    if self.nen_dung():
                        break
                    if all(la_dai_ly(m) for m in self.doi.map_doi_vien().values()):
                        break
                    time.sleep(1)
        if not con_sat_tinh(pmp, dem):
            self._xong_pho_ban_hom_nay(ten_ds)
        tat_tap_hop(self.doi)

    def _xong_vong(self, giay):
        def sua(cai_dat):
            pmp = cai_dat.setdefault("pho_ban_pmp", dict(cau_hinh.MAC_DINH_PHO_BAN_PMP))
            dem = hom_nay(pmp)
            dem["so_vong"] += 1
            pmp["hom_nay"] = dem
        moi = cau_hinh.sua_nhan_vat(self.ten, sua)
        if self._vong_vao_so:
            # Sơ Phiêu Miểu Phong chỉ đi được 1 lần/ngày: xong vòng Sơ thì các vòng sau vào PMP thường.
            self._vong_vao_so = False

            def het_so(cai_dat):
                pmp = cai_dat.setdefault("pho_ban_pmp", dict(cau_hinh.MAC_DINH_PHO_BAN_PMP))
                dem = hom_nay(pmp)
                dem["so_het_luot"] = True
                pmp["hom_nay"] = dem
            for ten in [self.ten] + list(self.doi.cac_doi_vien if self.doi else ()):
                moi_ten = cau_hinh.sua_nhan_vat(ten, het_so)
                if ten == self.ten:
                    moi = moi_ten
            self.in_log(f"{self.ten}: PMP đã xong 1 lượt Sơ Phiêu Miểu Phong hôm nay, các vòng sau đi PMP thường")
        self.in_log(f"{self.ten}: PMP xong vòng {hom_nay(moi['pho_ban_pmp'])['so_vong']} hôm nay "
                    f"({int(giay // 60)} phút {int(giay % 60)} giây)")
        self.bao_doi()

    # ---------- Thập Nhị Sát Tinh ----------

    @staticmethod
    def _chu_het_sat_tinh(cac_chu):
        """
        Chữ NPC SÁT TINH báo hết lượt, None nếu không có: "đã tham gia 20 lần rồi, xin ngày mai hãy quay lại", hoặc
        đội viên đã đủ lượt "Trong tổ đội của các hạ có A, B đã tham gia phụ bản 20 lần trong ngày hôm nay!" — coi như
        cả nhóm xong Sát Tinh để xoay vòng sang nhóm sau.
        """
        for chu in cac_chu:
            c = re.sub(r"#[ceg][0-9a-f]{6}|#[a-z]", "", chuan_hoa(chu))
            if "ngày mai hãy quay lại" in c or re.search(r"đã tham gia.{0,30}?\b20\s*lần", c) \
                    or re.search(r"đã tham gia.{0,30}?lần trong ngày hôm nay", c):
                return chu
        return None

    @staticmethod
    def _con_lai_sat_tinh(cac_chu):
        """Số lượt Sát Tinh còn lại NPC báo ("còn lại #G20 lượt nữa"), None nếu hội thoại không ghi."""
        for chu in cac_chu:
            khop = re.search(r"còn lại\s*(?:#g)?\s*(\d+)\s*lượt", chuan_hoa(chu))
            if khop:
                return int(khop.group(1))
        return None

    def _vao_sat_tinh(self):
        map_o, ten_npc, xy, (dong_1, dong_2), map_toi = BUOC_VAO_SAT_TINH
        for lan in range(1, SO_LAN_THU + 1):
            if self.doi:
                self._cho_doi_gan_xy(xy, map_o, ten_npc)
            self._mo_ta(f"Sát Tinh: tới NPC {ten_npc}")
            # Cả đội đã gom quanh NPC: bấm lại Theo đội lúc này chỉ chen vào thao tác click NPC.
            self._mo_hoi_thoai(ten_npc, xy, dong_1, dan_doi=not self.doi)
            self._chon(dong_1)
            ht = self._cho(lambda: (lambda h: h if h and (
                any((s, e) == dong_2 for _, s, e, _ in h[1])
                or self._chu_het_sat_tinh(chu for _, _, _, chu in h[1])) else None)(
                self._hoi_thoai()), GIAY_MO_HOI_THOAI)
            if ht:
                het = self._chu_het_sat_tinh(chu for _, _, _, chu in ht[1])
                if het:
                    raise _HetSatTinh(het)
                con_lai = self._con_lai_sat_tinh(chu for _, _, _, chu in ht[1])
                if con_lai == 0:
                    raise _HetSatTinh(next(chu for _, _, _, chu in ht[1] if "còn lại" in chuan_hoa(chu)))
                self._chon(dong_2)
                moi = self._cho(lambda: (lambda m: m if m and chuan_hoa(m) != chuan_hoa(map_o) else None)(
                    self._map()), GIAY_CHO_DOI_MAP)
                if moi:
                    self.in_log(f"{self.ten}: Sát Tinh {ten_npc} đưa tới [{moi}]"
                                + (f", còn {con_lai - 1} lượt" if con_lai else ""))
                    return
            else:
                h = self._hoi_thoai()
                if h and (self._chu_het_sat_tinh(chu for _, _, _, chu in h[1])
                          or self._con_lai_sat_tinh(chu for _, _, _, chu in h[1]) == 0):
                    raise _HetSatTinh("; ".join(chu for _, _, _, chu in h[1] if chu))
            ly_do = [chu for chu in self._doc_thong_bao() if "lượt" in chuan_hoa(chu)]
            if ly_do:
                raise _HetSatTinh("; ".join(ly_do[-3:]))
            self.in_log(f"{self.ten}: Sát Tinh {ten_npc} chưa đưa đi, thử lại lần {lan + 1}" if lan < SO_LAN_THU
                        else f"{self.ten}: Sát Tinh {ten_npc} vẫn chưa đưa đi")
            if lan < SO_LAN_THU and self.doi:
                self._cho_doi_gan_xy(xy, map_o, ten_npc)
                time.sleep(GIAY_CHO_GOM_DOI_RETRY)
        lech = self._doi_vien_lech_map()
        if lech:
            raise _TreoPMP(f"{ten_npc} chưa đưa đi vì đội viên không cùng map ({lech})")
        raise LoiPhoBan(f"{ten_npc} không đưa tới {map_toi}")

    def _sat_tinh_da_ra(self):
        """Có Sát Tinh còn sống quanh giữa lôi đài (Khô Vinh Đại Sư ở cửa nằm ngoài vùng này)."""
        return any(d.hp > 0 and khoang_cach((d.x, d.y), DIEM_SAT_TINH) <= BAN_KINH_SAT_TINH + 2
                   for _, d in self._quanh())

    def _dan_doi_toi_giua(self):
        """Vào lôi đài: chờ đội viên tới, bấm Theo đội, dẫn cả đội tới giữa; thấy Sát Tinh ra thì mới bỏ theo."""
        if self.doi:
            self.doi.dat_buoc(1, "di", (), None)
        self.dat_vung_danh(None)
        if self.doi and not self._sat_tinh_da_ra():
            self._mo_ta("Sát Tinh: chờ đội viên vào lôi đài")
            het_han = time.time() + GIAY_CHO_DOI_VIEN_TOI_MAP
            while time.time() < het_han and not all(la_sat_tinh(m) for m in self.doi.map_doi_vien().values()):
                self._kiem_tra()
                self.doi.lam_moi()
                thieu = [ten for ten, m in self.doi.map_doi_vien().items() if not la_sat_tinh(m)]
                if thieu:
                    self._mo_ta(f"Sát Tinh: chờ {', '.join(thieu)} vào lôi đài")
                time.sleep(GIAY_CHO_GOM_DOI_RETRY)
            self._cho_load_map(MAP_SAT_TINH)
            self._theo_doi(DIEM_SAT_TINH)
        self._mo_ta("Sát Tinh: dẫn đội tới giữa lôi đài, chờ Sát Tinh ra")
        het_han = time.time() + GIAY_CHO_SAT_TINH_RA
        luc_chay = 0.0
        while not self._sat_tinh_da_ra():
            self._kiem_tra()
            m = self._map()
            if m and not la_sat_tinh(m):
                return
            tt = self._tt()
            bay_gio = time.time()
            if tt and khoang_cach((tt["x"], tt["y"]), DIEM_SAT_TINH) > KHOANG_TOI_DIEM \
                    and bay_gio - luc_chay >= GIAY_CHAY_LAI:
                self.game.lua.chay(f"AutoRunToTarget({DIEM_SAT_TINH[0]}, {DIEM_SAT_TINH[1]})")
                luc_chay = bay_gio
            if bay_gio >= het_han:
                self.in_log(f"{self.ten}: Sát Tinh {GIAY_CHO_SAT_TINH_RA} giây chưa thấy Sát Tinh ra, bỏ theo đội")
                break
            time.sleep(0.3)
        self._bo_theo_doi()
        if self.doi:
            self.in_log(f"{self.ten}: Sát Tinh đã ra, bỏ theo đội để cả đội đánh")

    def _danh_sat_tinh(self):
        """Cả đội đánh quanh giữa lôi đài tới khi game đưa ra khỏi Lôi đài sinh tử."""
        vung = (*DIEM_SAT_TINH, BAN_KINH_SAT_TINH)
        self._dan_doi_toi_giua()
        self._bo_theo_doi()
        if self.doi:
            self.doi.dat_buoc(1, "danh", (), vung)
        self.dat_vung_danh(vung)
        self._mo_ta("Sát Tinh: đánh giữa lôi đài")
        so_sat_tinh = 0
        while True:
            self._kiem_tra()
            m = self._map()
            if m and not la_sat_tinh(m):
                self.in_log(f"{self.ten}: Sát Tinh xong, game đưa về [{m}] (đã đánh {so_sat_tinh} Sát Tinh)")
                return
            for chu in self._doc_thong_bao():
                if THONG_BAO_SAT_TINH_VAO in chuan_hoa(chu):
                    so_sat_tinh += 1
                    self._mo_ta(f"Sát Tinh: đánh {chu.split(THONG_BAO_SAT_TINH_VAO)[0].strip()} ({so_sat_tinh})")
                elif chu.startswith(THONG_BAO_SAT_TINH_XONG):
                    self._mo_ta("Sát Tinh: xong, chờ game đưa về")
            time.sleep(0.5)

    def _sua_dem(self, ten_ds, **gia_tri):
        def sua(cai_dat):
            pmp = cai_dat.setdefault("pho_ban_pmp", dict(cau_hinh.MAC_DINH_PHO_BAN_PMP))
            dem = hom_nay(pmp)
            for khoa, gt in gia_tri.items():
                dem[khoa] = gt(dem[khoa]) if callable(gt) else gt
            pmp["hom_nay"] = dem
        return [cau_hinh.sua_nhan_vat(ten, sua) for ten in ten_ds]

    def _het_sat_tinh(self, ly_do):
        self.in_log(f"{self.ten}: Sát Tinh hết lượt hôm nay: {ly_do}")
        ten_ds = [self.ten] + (list(self.doi.cac_doi_vien) if self.doi else [])
        self._sua_dem(ten_ds, st_het=True)
        self._xong_pho_ban_hom_nay(ten_ds)

    def _xong_pho_ban_hom_nay(self, ten_ds):
        """
        Hết việc phó bản hôm nay: bỏ theo đội (đang theo thì không dùng được vật phẩm dịch chuyển), tắt auto Phó bản,
        bật auto chuyển sinh để cả đội lên bãi train.
        """
        for game in [self.game] + [luong.game for luong in (self.doi.cac_doi_vien.values() if self.doi else ())]:
            try:
                game.lua.chay(MA_BO_THEO_DOI)
            except LoiLua:
                pass

        xoay_vong = cai_dat_pmp(cau_hinh.cua_nhan_vat(self.ten)).get("xoay_vong")

        def sua(cai_dat):
            cai_dat["pho_ban_pmp"] = dict(cai_dat_pmp(cai_dat), bat=False)
            if not xoay_vong:
                cai_dat["bat_chuyen_sinh"] = True
        for ten in ten_ds:
            cau_hinh.sua_nhan_vat(ten, sua)
        self.trang_thai.update(so_lan_that_bai=0, viec_da_in=None)
        for luong in (self.doi.cac_doi_vien.values() if self.doi else ()):
            luong.chay_lai()
        if xoay_vong:
            self.in_log(f"{self.ten}: hết lượt phó bản hôm nay, bỏ theo đội, TẮT auto Phó bản cho {', '.join(ten_ds)} "
                        "(xoay vòng lo giao dịch)")
        else:
            self.in_log(f"{self.ten}: hết lượt phó bản hôm nay, bỏ theo đội, TẮT auto Phó bản và BẬT auto chuyển sinh "
                        f"cho {', '.join(ten_ds)}")
        self.bao_doi()

    def _vong_sat_tinh(self, pmp):
        self.che_do = "sat_tinh"
        bat_dau = time.time()
        map_dau = self._map()
        if not la_dai_ly(map_dau) and not la_lac_duong(map_dau) and not la_sat_tinh(map_dau):
            self._ve_thanh()
        if la_lac_duong(self._map()):
            self._gom_doi_neu_lech_map()
        if la_dai_ly(self._map()):
            self._hoi_mau_dai_ly_neu_can()
            if self.doi:
                self.doi.dat_buoc(giai_doan="gom_sat_tinh")
                if self._doi_vien_dang_cho_sat_tinh_tai_lac_duong():
                    maps = self.doi.map_doi_vien()
                    ds = ", ".join(f"{ten} ({m or '?'})" for ten, m in maps.items())
                    self.in_log(f"{self.ten}: PMP đội viên đã ở {MAP_LAC_DUONG} chờ Sát Tinh ({ds}), "
                                f"đội trưởng Di Chuyển sang {MAP_LAC_DUONG} (không gom {MAP_DAI_LY})")
                    self.in_log(f"{self.ten}: PMP bấm Theo đội trước khi tới {BUOC_DI_CHUYEN_LAC_DUONG[1]}")
                    self._theo_doi(BUOC_DI_CHUYEN_LAC_DUONG[2])
                    self._cho_doi_theo()
                else:
                    self._chuan_bi_di_tu_dai_ly()
                bat_dau = time.time()
                self.het_han_vong = bat_dau + GIAY_MOT_VONG
            # Hết lượt PMP vẫn đi Di Chuyển (dòng PMP) sang Lạc Dương: NPC SÁT TINH đứng cạnh NPC PMP.
            buoc_di = BUOC_DI_CHUYEN_LAC_DUONG
            self._vao(buoc_di)
            self._cho_doi_sang_lac_duong()
            self._cho_doi_vien(buoc_di[4])
            self._cho_load_map(buoc_di[4])
        if la_lac_duong(self._map()):
            if self.doi:
                bat_tap_hop(self.doi, MAP_LAC_DUONG)
                self.doi.dat_buoc(giai_doan="gom_sat_tinh")
                self.doi.npc_gom = (MAP_LAC_DUONG, TEN_NPC_SAT_TINH, XY_NPC_SAT_TINH)
                try:
                    self._tap_hop_doi(MAP_LAC_DUONG)
                finally:
                    tat_tap_hop(self.doi)
            self._vao_sat_tinh()
            if self.doi:
                self.doi.npc_gom = None
        if not la_sat_tinh(self._map()):
            raise LoiPhoBan(f"đang ở [{self._map()}], không phải {MAP_SAT_TINH}")
        self._danh_sat_tinh()
        giay = time.time() - bat_dau
        moi = self._sua_dem([self.ten], st_vong=lambda v: v + 1)[0]
        self.in_log(f"{self.ten}: Sát Tinh xong vòng {hom_nay(moi['pho_ban_pmp'])['st_vong']} hôm nay "
                    f"({int(giay // 60)} phút {int(giay % 60)} giây)")
        self.bao_doi()

    def _vao_buoc_pmp(self, buoc, pmp, dem):
        if buoc[4] == MAP_PMP and buoc[3] is None:
            dem = hom_nay(pmp)
            if not con_pmp_thuong(dem):
                raise LoiPhoBan("hết lượt PMP thường")
            self.in_log(f"{self.ten}: PMP vào Phiêu Miểu Phong thường")
            buoc_vao = (buoc[0], buoc[1], buoc[2], (DONG_PMP_THUONG,), MAP_PMP)
            self._vao(buoc_vao, het_so=False)
        else:
            self._vao(buoc)

    def _mot_vong_pmp(self, pmp, ten, doi, bat_dau):
        self.che_do = "pmp"
        if doi:
            doi.truong_vao_danh = False
            doi.truong_khong_danh = bool(pmp["truong_khong_danh"] and self._co_thu())
            if doi.truong_dang_khong_danh():
                self.in_log(f"{ten}: PMP đội trưởng cưỡi thú dẫn đường, không đánh "
                            f"(để {', '.join(doi.cac_doi_vien)} đánh)")
        map_dau = chuan_hoa(self._map() or "")
        co_doi = doi is not None
        self._da_thu_mua_thu = False
        if not la_map_pho_ban(map_dau):
            self._ve_thanh()
        self._gom_doi_neu_lech_map()
        if la_dai_ly(self._map()):
            self._tu_dung_can_khon_ho()
        if co_doi and la_dai_ly(self._map()):
            self._dam_bao_thu_cuoi()
            self._chuan_bi_di_tu_dai_ly()
            bat_dau = time.time()
            self.het_han_vong = bat_dau + GIAY_MOT_VONG
        dem = hom_nay(pmp)
        self._vong_vao_so = False
        for buoc in CAC_BUOC_VAO:
            if chuan_hoa(self._map() or "") != chuan_hoa(buoc[0]):
                continue
            self._vao_buoc_pmp(buoc, pmp, dem)
            if buoc[4] == MAP_LAC_DUONG:
                self._cho_doi_sang_lac_duong()
            self._cho_doi_vien(buoc[4])
            self._cho_load_map(buoc[4])
            if self.doi and buoc[4] == MAP_LAC_DUONG:
                # Đổi map là mất theo đội: bấm lại để đội viên theo tới Trình Thanh Sương.
                self._theo_doi(XY_NPC_PMP)
        if chuan_hoa(self._map() or "") != chuan_hoa(MAP_PMP):
            raise LoiPhoBan(f"đang ở [{self._map()}], không phải {MAP_PMP}")
        if self.doi:
            self.doi.npc_gom = None
            self._theo_doi(CAC_AI[0].xy, dan_doi=True)
        so0 = self._ai_tiep_theo()
        if so0 > 1:
            self.in_log(f"{self.ten}: PMP đang ở {CAC_AI[so0 - 1].ten}, bỏ qua ải trước")
        for so, ai in enumerate(CAC_AI, 1):
            if so < so0:
                continue
            self._qua_ai(so, ai)
        bat_tap_hop(doi, MAP_DAI_LY)
        try:
            self._ve_dai_ly_ca_doi_retry(doi)
        finally:
            tat_tap_hop(doi)
        self._xong_vong(time.time() - bat_dau)

    # ---------- một vòng ----------

    def chay(self, ten, cai_dat_nhan_vat, trang_thai, nen_dung, dat_vung_danh, bao_doi, doi=None):
        """
        Đi một vòng (hoặc phần còn lại của vòng đang đi dở). Chặn tới khi xong / lỗi / bị tắt.
        doi: DoiPMP khi nhân vật này là đội trưởng dẫn các đội viên trong auto, None nếu đi một mình.
        """
        self.ten, self.trang_thai, self.nen_dung = ten, trang_thai, nen_dung
        self.bao_doi = bao_doi
        self.doi = doi
        if nen_dung():
            return

        def dat_vung(vung):
            if doi:
                doi.vung = vung
            dat_vung_danh(vung)
        self.dat_vung_danh = dat_vung
        self.dat_vung_rieng = dat_vung_danh
        pmp = cai_dat_pmp(cai_dat_nhan_vat)
        bat_dau = time.time()
        self.het_han_vong = bat_dau + GIAY_MOT_VONG
        self.thong_bao = []
        _dang_chay_vong.add(chuan_hoa(ten))
        try:
            self._doc_thong_bao()
            dem = hom_nay(pmp)
            chi_st = pmp.get("chi_sat_tinh")

            if chi_st:
                # Chỉ Sát Tinh: đang ở lôi đài thì đánh tiếp, còn không thì vào Sát Tinh.
                if la_sat_tinh(self._map()) or not con_luot_pmp_thuong(pmp, dem):
                    self._vong_sat_tinh(pmp)
                return

            # PMP rồi Sát Tinh: còn lượt PMP thường thì không nhảy Sát Tinh.
            if con_luot_pmp_thuong(pmp, dem):
                if la_sat_tinh(self._map()):
                    self.in_log(f"{self.ten}: còn lượt PMP thường, về thành trước khi vào Phiêu Miểu Phong")
                    self._ve_thanh()
                lan_treo = 0
                while con_luot_pmp_thuong(pmp, hom_nay(pmp)):
                    try:
                        try:
                            self._mot_vong_pmp(pmp, ten, doi, bat_dau)
                        except _TruongSaiMap as loi:
                            raise _TreoPMP(str(loi)) from loi
                        break
                    except _TreoPMP as treo:
                        lan_treo += 1
                        self.in_log(f"{ten}: PMP {treo.chu}, "
                                    f"về {MAP_DAI_LY} chạy vòng mới ({lan_treo}/{SO_LAN_CHAY_LAI_PMP_TREO})")
                        if lan_treo >= SO_LAN_CHAY_LAI_PMP_TREO:
                            raise LoiPhoBan(f"PMP treo {SO_LAN_CHAY_LAI_PMP_TREO} lần liên tiếp")
                        bat_tap_hop(doi, MAP_DAI_LY)
                        try:
                            self._ca_doi_ve_thanh()
                        finally:
                            tat_tap_hop(doi)
                        bat_dau = time.time()
                        self.het_han_vong = bat_dau + GIAY_MOT_VONG
                return

            if con_sat_tinh(pmp, dem):
                self.in_log(f"{self.ten}: PMP thường đã xong hôm nay ({dem['so_vong']} vòng"
                            f"{', hết lượt' if dem['het_luot'] else ''}), sang Sát Tinh")
                self._vong_sat_tinh(pmp)
                return
        except _HetLuot as het:
            self._het_luot(het.chu)
        except _HetSatTinh as het:
            self._het_sat_tinh(het.chu)
        except _Dung:
            pass
        except _TreoPMP as treo:
            self.in_log(f"{ten}: Sát Tinh {treo.chu}, cả đội về {MAP_DAI_LY} rồi đi lại")
            try:
                bat_tap_hop(doi, MAP_DAI_LY)
                try:
                    self._ca_doi_ve_thanh()
                finally:
                    tat_tap_hop(doi)
            except LoiPhoBan as loi:
                self.nghi_den = time.time() + GIAY_NGHI_KHI_LOI
                self.in_log(f"{ten}: Sát Tinh lỗi: {loi}. Nghỉ {GIAY_NGHI_KHI_LOI // 60} phút rồi thử lại")
        except LoiPhoBan as loi:
            self.nghi_den = time.time() + GIAY_NGHI_KHI_LOI
            self.in_log(f"{ten}: {'Sát Tinh' if self.che_do == 'sat_tinh' else 'PMP'} lỗi: {loi}. "
                        f"Nghỉ {GIAY_NGHI_KHI_LOI // 60} phút rồi thử lại")
        finally:
            _dang_chay_vong.discard(chuan_hoa(ten))
            if doi:
                doi.dat_buoc()
                doi.truong_khong_danh = False
                doi.truong_vao_danh = False
            dat_vung(None)
            self.doi = None
            trang_thai["mo_ta"] = ""


class _HoiMauDaiLy(PhoBanPMP):
    """Nói chuyện NPC Di Chuyển ở Đại Lý để hồi máu (không chọn dòng dịch chuyển)."""

    def __init__(self, game, ten, in_log, nen_dung=None):
        super().__init__(game, in_log or (lambda _: None))
        self.ten = ten
        self.nen_dung = nen_dung or (lambda: False)
        self.het_han_vong = time.time() + 120
        self.che_do = "hoi_mau"

    def thuc_hien(self, ty_le=TY_LE_HOI_MAU_DAI_LY):
        tt = self._tt()
        if not tt or not la_dai_ly(tt["map"]) or not can_hoi_mau_tai_dai_ly(tt, ty_le):
            return
        ten_npc, xy = TEN_NPC_HOI_MAU_DAI_LY, XY_NPC_HOI_MAU_DAI_LY
        try:
            self.in_log(f"{self.ten}: máu dưới {int(ty_le * 100)}% — tới NPC {ten_npc} hồi máu")
            self._mo_hoi_thoai(ten_npc, xy, (-1, -1), bo_qua_neu_khong_co=True, dan_doi=False)
            day = lambda: (lambda t: t and t["hp"] >= t["hp_toi_da"])(self._tt())
            if self._cho(day, GIAY_CHO_HOI_MAU_DAI_LY):
                self.in_log(f"{self.ten}: đã hồi máu ở NPC {ten_npc}")
            else:
                self.in_log(f"{self.ten}: nói chuyện NPC {ten_npc} nhưng máu chưa đầy")
        except LoiPhoBan as loi:
            self.in_log(f"{self.ten}: hồi máu Đại Lý: {loi}")
        finally:
            self.game.lua.chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
