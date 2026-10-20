"""
Đọc và điều khiển game qua API Lua có sẵn của chính game.
Không phụ thuộc màn hình, vị trí túi đồ hay độ phân giải, và không click chuột.

Các hàm Lua dùng ở đây được tìm thấy trong script giao diện của game (Data\Interface.axp):
    Player:GetName(), Player:GetData("LEVEL"), Player:GetPos()     -> PlayerFrame.lua, MiniMap.lua
    GetCurrentSceneName()                                          -> MiniMap.lua
    PlayerPackage:EnumItem("base", chỉ_số), PlayerPackage:UseItem(chỉ_số) -> Packet.lua, Item_TuDunZhu.lua
    Player:GetData("POINT_REMAIN"), Player:SendAskManualAttr(...)  -> SelfEquip.lua (bảng Alt+C)
"""
from bang_ma_viscii import giai_ma
from lua_game import LuaGame

SO_O_MOI_HANG = 5
SO_O_TUI_CO_BAN = 30


def chi_so_o(hang, cot):
    """Túi đồ có 5 cột, chỉ số đếm từ 0: (hàng 1, cột 1) -> 0, (hàng 5, cột 1) -> 20."""
    return (hang - 1) * SO_O_MOI_HANG + (cot - 1)


class Game:
    def __init__(self, hwnd):
        self.lua = LuaGame(hwnd)

    def ten_nhan_vat(self):
        return giai_ma(self.lua.chay("return Player:GetName()"))

    def level(self):
        return int(self.lua.chay('return Player:GetData("LEVEL")'))

    def hp(self):
        return int(float(self.lua.chay('return Player:GetData("HP")')))

    def ten_map(self):
        return giai_ma(self.lua.chay("return GetCurrentSceneName()"))

    def toa_do(self):
        x, y = self.lua.chay('local x, y = Player:GetPos(); return x .. "," .. y').split(b",")
        return int(float(x)), int(float(y))

    def thong_tin(self):
        """
        Đọc tên, level, map, tọa độ, HP, MP, môn phái, tài khoản trong một lệnh Lua (nhanh hơn gọi từng hàm).
        Trả về None nếu nhân vật chưa vào game: gọi hàm Player lúc đang ở màn hình đăng nhập có thể làm game văng.
        Khung nhân vật (PlayerFrame) chỉ hiện sau sự kiện PLAYER_ENTERING_WORLD.
        """
        ket_qua = self.lua.chay(
            'if not IsWindowShow("PlayerFrame") then return "" end '
            'local x, y = Player:GetPos() '
            'return Player:GetName() .. "|" .. Player:GetData("LEVEL") .. "|" .. GetCurrentSceneName() '
            '.. "|" .. x .. "|" .. y .. "|" .. Player:GetData("HP") .. "|" .. Player:GetData("MAXHP") '
            '.. "|" .. Player:GetData("MP") .. "|" .. Player:GetData("MAXMP") '
            '.. "|" .. tostring(Player:GetData("MEMPAI")) .. "|" .. tostring(Player:GetData("ACCOUNTNAME"))')
        if not ket_qua:
            return None
        phan = ket_qua.rsplit(b"|", 10)
        if not phan[0]:
            return None
        so = [int(float(p)) for p in phan[1:2] + phan[3:9]]
        try:
            mon_phai = int(float(phan[9]))
        except ValueError:
            mon_phai = None
        tai_khoan = phan[10].decode("latin-1")
        return {"ten": giai_ma(phan[0]), "level": so[0], "map": giai_ma(phan[2]), "x": so[1], "y": so[2],
                "hp": so[3], "hp_toi_da": so[4], "mp": so[5], "mp_toi_da": so[6], "mon_phai": mon_phai,
                "tai_khoan": "" if tai_khoan == "nil" else tai_khoan}

    def diem_tiem_nang(self):
        """Điểm tiềm năng chưa cộng (dòng "Điểm" của bảng Alt+C, SelfEquip.lua)."""
        return int(float(self.lua.chay('return Player:GetData("POINT_REMAIN")')))

    def cong_diem_tiem_nang(self, cong):
        """Như bấm Duyệt ở bảng Alt+C: cong = {"str", "spr", "con", "int", "dex": số điểm cộng thêm}."""
        so = ", ".join(str(int(cong.get(khoa, 0))) for khoa in ("str", "spr", "con", "int", "dex"))
        self.lua.chay(f"Player:SendAskManualAttr({so})")

    def vat_pham_o(self, hang, cot):
        """Trả về {ma_loai, so_luong, ten} của vật phẩm ở ô (hàng, cột) trong tab ĐC, hoặc None nếu ô trống."""
        ket_qua = self.lua.chay(
            f'local a = PlayerPackage:EnumItem("base", {chi_so_o(hang, cot)}) '
            'if a:GetID() == 0 then return "" end '
            'return a:GetDefineID() .. "|" .. a:GetNum() .. "|" .. a:GetName()')
        if not ket_qua:
            return None
        ma_loai, so_luong, ten = ket_qua.split(b"|", 2)
        return {"ma_loai": int(ma_loai), "so_luong": int(so_luong), "ten": giai_ma(ten)}

    def dung_o(self, hang, cot):
        """Dùng vật phẩm ở ô (hàng, cột), không qua hộp thoại nào.

        Với Thổ Linh Châu, chuột phải sẽ mở hộp thoại "Định vị / Dịch chuyển". Nút "Dịch chuyển"
        trong hộp thoại đó gọi đúng lệnh này (Item_TuDunZhu_Cancel_Clicked), còn "Định vị" gọi
        PlayerPackage:UseTulingzhuSetpos - auto không bao giờ gọi hàm đó.
        """
        self.lua.chay(f"PlayerPackage:UseItem({chi_so_o(hang, cot)})")
