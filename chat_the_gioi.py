"""
AUTO CHAT THẾ GIỚI - gửi một nội dung lên kênh Thế giới theo chu kỳ (tab Tiện ích).

Ô nhập chat của game gọi Talk:SendChatMessage(kênh, nội dung) (ChatFrame.lua); kênh Thế giới tên là "scene"
(CHANNEL_DATA_SCENE, nút ChannelWorld). Chat dồn quá nhanh thì game không gửi mà báo "Đề nghị không nên nói
chuyện với tốc độ quá nhanh!".
"""
from dang_nhap import LoiDangNhap, chuoi_lua

KENH_THE_GIOI = "scene"
GIAY_TOI_THIEU = 30


class LoiChat(Exception):
    pass


def ma_lua_chat(noi_dung):
    try:
        return f"Talk:SendChatMessage({chuoi_lua(KENH_THE_GIOI)}, {chuoi_lua(noi_dung)})"
    except LoiDangNhap as loi:
        raise LoiChat(str(loi)) from None


def gui_the_gioi(lua, noi_dung):
    lua.chay(ma_lua_chat(noi_dung))
