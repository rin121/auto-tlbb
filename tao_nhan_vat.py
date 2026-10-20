"""
TẠO NHÂN VẬT.

Bấm "Tạo nhân vật" ở màn hình chọn nhân vật thì server bắt nhập mã kiểm tra (4 chữ số trong ảnh) rồi mới mở
màn hình tạo nhân vật. Auto đọc ảnh (giai_captcha.py) và nhập giúp, bằng hàm Lua của giao diện game:
    Mở hộp mã : DataPool:AskCreateCharCode()                         (SelectRole.lua, nút Tạo nhân vật)
    Nhập mã   : TextValidate_Input, TextValidate_BtnCommitClick()     (TextValidate.lua)
    Đổi ảnh   : TextValidate_BtnChangePicClick()
Đúng thì hộp mã đóng và game mở cửa sổ LoginCreateRole; sai thì server tự gửi ảnh mới.

Hộp mã lúc đăng nhập (cùng cửa sổ TextValidate) do dang_nhap.py lo, nên game đang có luồng tự đăng nhập thì
không đụng tới.
"""
import time

from dang_nhap import dang_hien, giai_hop_ma_kiem_tra

GIAY_GIAI_MA_TOI_DA = 90
GIAY_CHO_MO_TAO_NHAN_VAT = 3


def dang_hoi_ma_kiem_tra(lua):
    """Hộp mã kiểm tra đang mở ở màn hình chọn nhân vật."""
    return lua.chay('if IsWindowShow("TextValidate") and IsWindowShow("LoginSelectRole") then return "1" end '
                    'return "0"') == b"1"


def giai_ma_kiem_tra(lua, in_log, nen_dung):
    """
    Nhập mã tới khi qua (game mở màn hình tạo nhân vật), hộp mã bị đóng, hoặc quá GIAY_GIAI_MA_TOI_DA giây.
    Trả về True nếu qua. Lỗi đọc ảnh (thiếu ddddocr, khác bản Game.exe) thì ném giai_captcha.LoiGiaiCaptcha.
    """
    bat_dau = time.time()
    so_lan_nhap = giai_hop_ma_kiem_tra(lua, nen_dung, GIAY_GIAI_MA_TOI_DA)
    if so_lan_nhap is None:
        if not nen_dung():
            in_log(f"Chưa qua mã kiểm tra tạo nhân vật sau {GIAY_GIAI_MA_TOI_DA} giây")
        return False
    het_han = time.time() + GIAY_CHO_MO_TAO_NHAN_VAT
    while time.time() < het_han and not dang_hien(lua, "LoginCreateRole"):
        time.sleep(0.5)
    if dang_hien(lua, "LoginCreateRole"):
        in_log(f"Qua mã kiểm tra tạo nhân vật (nhập {so_lan_nhap} lần, {time.time() - bat_dau:.0f} giây)")
        return True
    in_log("Hộp mã kiểm tra tạo nhân vật đã đóng")
    return False
