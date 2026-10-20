"""
TRÂN THÚ: tự cho ăn và xuất chiến trân thú (tab Chiến đấu).

Dùng hàm Lua của bảng trân thú (Pet.lua), không cần mở bảng:
    Pet:GetPet_Count(), Pet:IsPresent(i), Pet:GetName(i), Pet:GetLevel(i)
    Pet:GetHappy(i)        : độ hoan hỉ 0..100
    Pet:GetIsFighting(i)   : đang xuất chiến
    Pet:Feed(i)            : nút "Ăn" - hoan hỉ tăng ngay (đo được +30 rồi +10)
    Pet:Go_Fight(i)        : nút "Xuất chiến" - vận công khoảng 3 giây, bấm kỹ năng / đánh trong lúc đó là bị cắt
"""
import time
from collections import namedtuple

from bang_ma_viscii import giai_ma

GIAY_GIUA_HAI_LAN_XEM = 5.0
GIAY_GIUA_HAI_LAN_AN = 1.0
GIAY_VAN_CONG_XUAT_CHIEN = 3.5
GIAY_NGHI_KHI_KHONG_XUAT_CHIEN_DUOC = 60.0
GIAY_THU_AN_LAI_KHI_KHONG_TANG = 60.0
MA_DOC = ('local kq = "" for i = 0, Pet:GetPet_Count() - 1 do if Pet:IsPresent(i) then '
          'kq = kq .. i .. "\\t" .. tostring(Pet:GetHappy(i)) .. "\\t" .. (Pet:GetIsFighting(i) and "1" or "0") '
          '.. "\\t" .. tostring(Pet:GetLevel(i)) .. "\\t" .. tostring(Pet:GetName(i)) .. "\\n" end end return kq')

TranThu = namedtuple("TranThu", "chi_so hoan_hi xuat_chien level ten")


def doc_tran_thu(lua):
    """Danh sách TranThu đang mang theo."""
    cac = []
    for dong in lua.chay(MA_DOC).split(b"\n"):
        phan = dong.split(b"\t", 4)
        if len(phan) < 5:
            continue
        try:
            cac.append(TranThu(int(phan[0]), int(float(phan[1])), phan[2] == b"1", int(float(phan[3])),
                               giai_ma(phan[4])))
        except ValueError:
            continue
    return cac


class TuXuatChien:
    """Trân thú chưa xuất chiến thì xuất chiến; hoan hỉ dưới mức thì bấm Ăn trước (cả khi đang xuất chiến)."""

    def __init__(self, lua, in_log):
        self.lua = lua
        self.in_log = in_log
        self.luc_xem = 0.0
        self.van_cong_den = 0.0
        self.cho_xac_nhan = None  # tên trân thú vừa bấm Xuất chiến, xem lại ở lần sau
        self.nghi_den = 0.0
        self.hoan_hi_truoc_khi_an = None
        self.thu_an_lai_luc = 0.0
        self.da_bao_an_khong_tang = False
        self.da_bao_khong_xuat_chien = False

    def buoc(self, hoan_hi_toi_thieu):
        """Gọi đều đặn. Trả về mô tả nếu đang vận công xuất chiến (lượt này đừng đánh / bấm kỹ năng), None nếu không."""
        bay_gio = time.time()
        if bay_gio < self.van_cong_den:
            return "Gọi trân thú xuất chiến"
        if bay_gio - self.luc_xem < GIAY_GIUA_HAI_LAN_XEM or bay_gio < self.nghi_den:
            return None
        self.luc_xem = bay_gio
        cac = doc_tran_thu(self.lua)
        if not cac:
            return None
        dang_xuat_chien = [tt for tt in cac if tt.xuat_chien]
        tt = dang_xuat_chien[0] if dang_xuat_chien else max(cac, key=lambda t: (t.level, -t.chi_so))

        if self.cho_xac_nhan is not None:
            ten, self.cho_xac_nhan = self.cho_xac_nhan, None
            if not dang_xuat_chien:
                self.nghi_den = bay_gio + GIAY_NGHI_KHI_KHONG_XUAT_CHIEN_DUOC
                if not self.da_bao_khong_xuat_chien:
                    self.da_bao_khong_xuat_chien = True
                    self.in_log(f"Trân thú: không xuất chiến được {ten} (hoan hỉ {tt.hoan_hi}), "
                                f"cứ {GIAY_NGHI_KHI_KHONG_XUAT_CHIEN_DUOC:.0f} giây thử lại")
                return None
            self.da_bao_khong_xuat_chien = False

        if tt.hoan_hi < hoan_hi_toi_thieu:
            if self.hoan_hi_truoc_khi_an is not None and tt.hoan_hi <= self.hoan_hi_truoc_khi_an:
                self.thu_an_lai_luc = bay_gio + GIAY_THU_AN_LAI_KHI_KHONG_TANG
                if not self.da_bao_an_khong_tang:
                    self.da_bao_an_khong_tang = True
                    self.in_log(f"Trân thú: cho {tt.ten} ăn mà hoan hỉ không tăng (còn {tt.hoan_hi}), có thể đã hết "
                                f"thức ăn, {GIAY_THU_AN_LAI_KHI_KHONG_TANG:.0f} giây sau thử lại")
            elif bay_gio >= self.thu_an_lai_luc:
                self.lua.chay(f"Pet:Feed({tt.chi_so})")
                if self.hoan_hi_truoc_khi_an is None and not self.da_bao_an_khong_tang:
                    self.in_log(f"Trân thú: {tt.ten} hoan hỉ {tt.hoan_hi} < {hoan_hi_toi_thieu}, cho ăn")
                self.hoan_hi_truoc_khi_an = tt.hoan_hi
                self.luc_xem = bay_gio - GIAY_GIUA_HAI_LAN_XEM + GIAY_GIUA_HAI_LAN_AN
                return None
        else:
            self.da_bao_an_khong_tang = False
        self.hoan_hi_truoc_khi_an = None
        if tt.xuat_chien:
            return None
        self.lua.chay(f"Pet:Go_Fight({tt.chi_so})")
        self.van_cong_den = bay_gio + GIAY_VAN_CONG_XUAT_CHIEN
        self.luc_xem = self.van_cong_den
        self.cho_xac_nhan = tt.ten
        if not self.da_bao_khong_xuat_chien:
            self.in_log(f"Trân thú: xuất chiến {tt.ten} (hoan hỉ {tt.hoan_hi})")
        return "Gọi trân thú xuất chiến"
