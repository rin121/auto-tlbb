"""
TỰ ĐỘNG TĂNG CẤP (tab Chiến đấu): đủ kinh nghiệm thì bấm nút Thăng cấp ở bảng nhân vật (Alt+C) như chơi tay.

Theo SelfEquip.lua (Data\\Interface2.axp):
    Nút SelfEquip_UpLevel sáng khi Player:GetData("EXP") >= Player:GetData("NEEDEXP") và cấp < LEVEL_MAX_ENABLE.
    Bấm nút gọi SelfEquip_AskLevelup() -> AskLevelUp(0); cấp 29 / 44 có sư phụ thì AskEvaluateAndLevelup().
Gọi chính SelfEquip_AskLevelup (trong môi trường cửa sổ SelfEquip) để giống hệt bấm tay; không thấy hàm đó thì
gọi thẳng AskLevelUp(0).
"""
from dang_nhap import trong_cua_so

GIAY_GIUA_MOI_LAN = 5

MA_TANG_CAP = trong_cua_so("SelfEquip", (
    'local lv = tonumber(Player:GetData("LEVEL")) or 0 '
    'local exp = tonumber(Player:GetData("EXP")) or 0 '
    'local can = tonumber(Player:GetData("NEEDEXP")) or 0 '
    'if can <= 0 or exp < can then return "" end '
    'if type(LEVEL_MAX_ENABLE) == "number" and lv >= LEVEL_MAX_ENABLE then return "" end '
    'if type(SelfEquip_AskLevelup) == "function" then SelfEquip_AskLevelup() else AskLevelUp(0) end '
    'return tostring(lv)'))


def thu_tang_cap(lua):
    """Đủ kinh nghiệm thì xin lên cấp. Trả về cấp lúc bấm (int), chưa đủ kinh nghiệm thì None."""
    ket_qua = lua.chay(MA_TANG_CAP).decode("ascii", "replace").strip()
    if not ket_qua:
        return None
    try:
        return int(float(ket_qua))
    except ValueError:
        return None
