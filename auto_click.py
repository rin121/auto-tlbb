"""
AUTO CLICK: bấm liên tục các ô F1-F10 trên thanh kỹ năng (tab "Auto click"), không cần đang đánh quái.

Dùng cùng cách với tự dùng kỹ năng ở chien_dau.py: Button_ActionN:DoAction() của cửa sổ MainMenuBar như bấm phím FN.
Mỗi lượt bấm mọi ô đã tích; ô chưa hồi / đang vận công thì game tự bỏ qua.
"""
from dang_nhap import trong_cua_so

CAC_PHIM = range(1, 11)
GIAY_TOI_THIEU, GIAY_TOI_DA = 0.2, 60.0
MAC_DINH = {"bat": False, "cac_phim": [], "giay": 0.5}


def cai_dat_auto_click(cai_dat_nhan_vat):
    """Cài đặt auto click của nhân vật, thêm giá trị mặc định cho khóa chưa có."""
    cai_dat = dict(MAC_DINH)
    cai_dat.update({khoa: gia_tri for khoa, gia_tri in cai_dat_nhan_vat.get("auto_click", {}).items()
                    if khoa in MAC_DINH})
    cai_dat["cac_phim"] = sorted({phim for phim in cai_dat["cac_phim"] if phim in CAC_PHIM})
    cai_dat["giay"] = min(max(float(cai_dat["giay"]), GIAY_TOI_THIEU), GIAY_TOI_DA)
    return cai_dat


def ma_bam_phim(cac_phim):
    """Đoạn Lua bấm lần lượt các ô trên thanh kỹ năng."""
    return trong_cua_so("MainMenuBar", " ".join(
        f"if DataPool:IsCanDoAction() then Button_Action{phim}:DoAction() end" for phim in cac_phim))


def mo_ta(cai_dat):
    return "Auto click " + " ".join(f"F{phim}" for phim in cai_dat["cac_phim"])
