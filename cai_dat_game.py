"""
Tab Cài đặt: vào game thì tắt âm thanh và giảm đồ họa xuống thấp nhất.

Làm giống nút Duyệt của bảng Cài đặt âm thanh (SoundSetup.lua: Variable:SetVariable) và Thiết lập hiển thị
(ViewSetup.lua: SystemSetup:View_SetData), không mở bảng. Chỉ ghi mục đang khác, nên game đã ở mức thấp nhất
(các game dùng chung file cấu hình trong thư mục game) thì không đổi gì.

Trước khi mở Game.exe (nếu bật giảm đồ họa): chỉnh Bin/System.cfg, Accounts/System.cfg và *.pfc cho các
biến View_* còn sót (hiệu ứng, thời tiết, số mô hình trong profile…) và System_MaxFPS* (tab Cài đặt).
"""

import os
import re
from glob import glob

AM_THANH = (("DisableAllSound", "1"), ("EnableBGSound", "0"), ("Enable3DSound", "0"),
            ("EnableSKSound", "0"), ("EnableUISound", "0"))

# Các ô trong bảng Thiết lập hiển thị: 0 là mức thấp nhất (Không / Thấp / 1 / bỏ tích).
# Không đổi: Chất lượng màu sắc (yszl, 16 bit ở chế độ cửa sổ dễ làm game lỗi), Phân giải đồng bộ (cztb),
# FULLSCREEN (qpms), gamma và các mục không có trên bảng.
DO_HOA = (("dxyy", 0),  # Độ bóng
          ("fhj", 0),   # Khử răng cưa
          ("wtdh", 0),  # Hình động
          ("cy", 0),    # Cỏ / chi tiết mặt đất
          ("dbxs", 0),  # Hiển thị đa giác (ViewSetup slider 8)
          ("rwyy", 0),  # Độ bóng nhân vật
          ("ksfw", 0),  # Số mô hình (View_ModelShowLogic)
          ("wldx", 0),  # Mẫu loại
          ("qpfg", 0),  # Sáng toàn màn hình
          ("sdh", 0),   # Dịu
          ("miwu", 0))  # Hiển thị sương mù

# ViewSetup.lua CHECK_String: 0 = bỏ tích (tắt địa hình / nhân vật cao cấp).
DO_HOA_TICK = (("dxgg", 0),  # Địa hình cao cấp
               ("rwgg", 0))  # Nhân vật cao cấp

DO_HOA_BIEN = (
    ("View_PiFeng", "0"),  # Hồi Chiêu (hiện áo choàng)
    ("View_EffectLevel", "0"),
    ("View_ModelShowLogic", "0"),
    ("View_ModelEffect", "0"),
    ("View_Specular", "0"),
    ("View_UpdateQuality", "0"),
    ("View_VisibleRangeLevelNew", "0"),
    ("View_EffectQuality", "0"),
    ("View_Floodlight", "0"),
    ("View_HumanHighLight", "0"),
    ("View_WaterMove", "0"),
    ("View_WalkEffect", "0"),
    ("View_Weather", "0"),
    ("View_TextureFiltering", "0"),
    ("View_ModlePolygon", "0"),
    ("View_GroundHighLight", "0"),
    ("View_ObjectMove", "0"),
    ("View_EnableFog", "0"),
    ("View_LightmapQuality", "0"),
    ("View_HumanLightmap", "0"),
    ("View_Fanhunjiao", "0"),
    ("View_FullScreenLight", "0"),
    ("View_TextureQuality", "0"),
    ("View_Aplomb", "0"),
    ("View_Transparency", "0"),
    ("View_HDRFilter", "0"),
    ("View_MeticulousScene", "0"),
    ("View_PolygonQuantity", "0"),
    ("View_ColorQuality", "0"),
)

# Nút "Mặc định" trong ViewSetup.lua (ViewSetup_Default_Clicked), chỉ các mục auto đã hạ.
DO_HOA_MAC_DINH = (("dxyy", 2), ("wtdh", 2), ("ksfw", 2), ("wldx", 1), ("sdh", 1), ("miwu", 1))
DO_HOA_TICK_MAC_DINH = (("dxgg", 1), ("rwgg", 1))
DO_HOA_BIEN_MAC_DINH = (("View_PiFeng", "1"),)

# Tắt hết hiệu ứng: slider/check ViewSetup (hình động wtdh, phát sáng qpfg/rwyy…) + biến View_* hiệu ứng/skill.
HIeu_UNG_SLIDER = (("wtdh", 0), ("dxyy", 0), ("rwyy", 0), ("dbxs", 0), ("cy", 0), ("ksfw", 0), ("wldx", 0),
                   ("qpfg", 0), ("sdh", 0), ("miwu", 0), ("fhj", 0))
HIeu_UNG_CHECK = (("dxgg", 0), ("rwgg", 0))
HIeu_UNG_BIEN = (
    ("View_PiFeng", "0"),
    ("View_EffectLevel", "0"),
    ("View_EffectQuality", "0"),
    ("View_ModelEffect", "0"),
    ("View_ModelShowLogic", "0"),
    ("View_WalkEffect", "0"),
    ("View_WaterMove", "0"),
    ("View_Weather", "0"),
    ("View_ObjectMove", "0"),
    ("View_UpdateQuality", "0"),
    ("View_Specular", "0"),
    ("View_HumanHighLight", "0"),
    ("View_Floodlight", "0"),
    ("View_FullScreenLight", "0"),
    ("View_HDRFilter", "0"),
    ("View_GroundHighLight", "0"),
    ("View_Aplomb", "0"),
    ("View_Transparency", "0"),
    ("View_HumanLightmap", "0"),
    ("View_LightmapQuality", "0"),
)
GIAY_GIUA_AP_HIEU_UNG = 30

FPS_MAC_DINH = {"fps_max": 25, "fps_front": 25, "fps_back": 5}
FPS_KHOA_CFG = ("System_MaxFPS", "System_MaxFPS_Front", "System_MaxFPS_Back")


def _fps_so(chung, khoa):
    try:
        gia_tri = int(chung.get(khoa, FPS_MAC_DINH[khoa]))
    except (TypeError, ValueError):
        gia_tri = FPS_MAC_DINH[khoa]
    return max(5, min(100, gia_tri))


def fps_tu_cau_hinh(chung=None):
    """Giá trị System_MaxFPS* (string) từ cau_hinh.chung()."""
    if chung is None:
        import cau_hinh
        chung = cau_hinh.chung()
    return {FPS_KHOA_CFG[0]: str(_fps_so(chung, "fps_max")),
            FPS_KHOA_CFG[1]: str(_fps_so(chung, "fps_front")),
            FPS_KHOA_CFG[2]: str(_fps_so(chung, "fps_back"))}


def cap_do_hoa_fps(chung=None):
    cap = dict(DO_HOA_BIEN)
    cap.update(fps_tu_cau_hinh(chung))
    return cap


def _cap_nhat_tep_cfg(duong_dan, cap):
    """Ghi các biến View_* trong file .cfg/.pfc; trả về số dòng đã đổi hoặc thêm."""
    if not os.path.isfile(duong_dan):
        return 0
    with open(duong_dan, "r", encoding="utf-8", errors="replace") as tep:
        dong = tep.readlines()
    mau = {k: re.compile(rf"^\s*{re.escape(k)}\s*=", re.I) for k in cap}
    con_thieu = dict(cap)
    doi = 0
    moi = []
    for line in dong:
        khoa = next((k for k, rx in mau.items() if rx.match(line)), None)
        if not khoa:
            moi.append(line)
            continue
        gia_tri = cap[khoa]
        cu = line.rstrip("\r\n")
        if not re.search(rf"=\s*{re.escape(gia_tri)}\s*$", cu):
            doi += 1
        moi.append(f"{khoa}={gia_tri}\n")
        del con_thieu[khoa]
    if con_thieu:
        chen = False
        out = []
        for line in moi:
            out.append(line)
            if line.strip() == "[Variable]" and not chen:
                for k, v in con_thieu.items():
                    out.append(f"{k}={v}\n")
                    doi += 1
                chen = True
        if not chen:
            out = ["[Variable]\n"] + [f"{k}={v}\n" for k, v in con_thieu.items()] + moi
            doi += len(con_thieu)
        moi = out
    if doi:
        with open(duong_dan, "w", encoding="utf-8", errors="replace", newline="") as tep:
            tep.writelines(moi)
    return doi


def cap_hieu_ung_cfg():
    return dict(HIeu_UNG_BIEN)


def chuan_bi_thu_muc_game(thu_muc_game, chung=None):
    """
    Trước khi chạy Game.exe: hạ View_* / System_MaxFPS* trong Bin/System.cfg, Accounts/System.cfg và mọi *.pfc.
    Game đang chạy thì không gọi (file có thể bị khóa).
    """
    import cau_hinh
    if chung is None:
        chung = cau_hinh.chung()
    if not thu_muc_game:
        return 0
    cap = {}
    if chung.get("giam_do_hoa"):
        cap.update(cap_do_hoa_fps(chung))
    elif chung.get("tat_het_hieu_ung"):
        cap.update(cap_hieu_ung_cfg())
    if not cap:
        return 0
    tong = 0
    for duong_dan in (
        os.path.join(thu_muc_game, "Bin", "System.cfg"),
        os.path.join(thu_muc_game, "Accounts", "System.cfg"),
    ):
        tong += _cap_nhat_tep_cfg(duong_dan, cap)
    accounts = os.path.join(thu_muc_game, "Accounts")
    if os.path.isdir(accounts):
        for duong_dan in glob(os.path.join(accounts, "**", "*.pfc"), recursive=True):
            tong += _cap_nhat_tep_cfg(duong_dan, cap)
    return tong


def _ma_lua_ap_dung():
    return ['local doi = 0',
            'local function bien(k, v) if Variable:GetVariable(k) ~= v then '
            'Variable:SetVariable(k, v, 0) doi = doi + 1 end end',
            'local function hien_thi(k, v) if tonumber(SystemSetup:View_GetData(k)) ~= v then '
            'SystemSetup:View_SetData(k, v) doi = doi + 1 end end']


def ma_ap_dung_hieu_ung():
    """Lua: tắt tối đa hiệu ứng client (ViewSetup + View_*)."""
    dong = _ma_lua_ap_dung()
    dong += [f'hien_thi("{k}", {v})' for k, v in HIeu_UNG_SLIDER]
    dong += [f'hien_thi("{k}", {v})' for k, v in HIeu_UNG_CHECK]
    dong += [f'bien("{k}", "{v}")' for k, v in HIeu_UNG_BIEN]
    dong.append('return tostring(doi)')
    return "\n".join(dong)


def ap_dung_hieu_ung(lua):
    return int(lua.chay(ma_ap_dung_hieu_ung()) or b"0")


def ma_ap_dung(tat_am_thanh, giam_do_hoa, chung=None):
    """Code Lua đặt các mục đang khác; trả về số mục đã đổi."""
    dong = _ma_lua_ap_dung()
    if tat_am_thanh:
        dong += [f'bien("{k}", "{v}")' for k, v in AM_THANH]
    if giam_do_hoa:
        dong += [f'hien_thi("{k}", {v})' for k, v in DO_HOA]
        dong += [f'hien_thi("{k}", {v})' for k, v in DO_HOA_TICK]
        dong += [f'bien("{k}", "{v}")' for k, v in DO_HOA_BIEN]
        dong += [f'bien("{k}", "{v}")' for k, v in fps_tu_cau_hinh(chung).items()]
    dong.append('return tostring(doi)')
    return "\n".join(dong)


def ap_dung(lua, tat_am_thanh, giam_do_hoa, chung=None):
    """Trả về số mục đã đổi. Lỗi gọi game thì ném LoiLua."""
    if not (tat_am_thanh or giam_do_hoa):
        return 0
    return int(lua.chay(ma_ap_dung(tat_am_thanh, giam_do_hoa, chung)) or b"0")


def ma_khoi_phuc_do_hoa():
    """Đưa các mục auto đã hạ về mức nút Mặc định của bảng Thiết lập hiển thị."""
    dong = ['local doi = 0',
            'local function bien(k, v) if Variable:GetVariable(k) ~= v then '
            'Variable:SetVariable(k, v, 0) doi = doi + 1 end end',
            'local function hien_thi(k, v) if tonumber(SystemSetup:View_GetData(k)) ~= v then '
            'SystemSetup:View_SetData(k, v) doi = doi + 1 end end']
    dong += [f'hien_thi("{k}", {v})' for k, v in DO_HOA_MAC_DINH]
    dong += [f'hien_thi("{k}", {v})' for k, v in DO_HOA_TICK_MAC_DINH]
    dong += [f'bien("{k}", "{v}")' for k, v in DO_HOA_BIEN_MAC_DINH]
    dong.append('return tostring(doi)')
    return "\n".join(dong)


def khoi_phuc_do_hoa(lua):
    """Trả về số mục đã đổi. Lỗi gọi game thì ném LoiLua."""
    return int(lua.chay(ma_khoi_phuc_do_hoa()) or b"0")
