"""
TỰ MỜI NHÓM.

Một nhóm, không phụ thuộc ai làm trưởng nhóm (trưởng nhóm bị diss thì game chuyển quyền cho người khác):
  - Nhân vật trong auto đang là trưởng nhóm thật trong game: mời các nhân vật trong auto còn thiếu và người chơi trong
    danh sách mời (white list) đang ở gần.
  - Nhân vật chưa có nhóm: đồng ý lời mời của nhóm có nhân vật trong auto hoặc người trong danh sách mời.
  - Chưa nhân vật nào có nhóm: "người lập nhóm" (chọn ở tab Nhóm, không online thì người đầu tiên theo tên) lập nhóm.
  - Bị tách thành hai nhóm: trưởng nhóm nhỏ hơn rời nhóm để nhập vào nhóm lớn hơn.
  - Trưởng nhóm chọn ở tab Nhóm vào lại (sau khi bị diss) và đã ở trong nhóm: trưởng nhóm tạm nhường lại quyền.
Chạy liên tục trong luồng của từng cửa sổ game, nên ai bị diss vào lại cũng được mời lại.

Hàm Lua của game (Data\\Interface.axp):
    Mời theo tên     : Target:SendTeamRequest(ten), chưa có nhóm thì tự lập nhóm   (XunZong.lua)
    Đồng ý lời mời   : Player:AgreeJoinTeam(chỉ số lời mời)                        (TeamFrame.lua)
    Rời nhóm         : Player:LeaveTeam()                                          (TeamFrame.lua)
    Nhường trưởng    : Player:AppointLeader(chỉ số thành viên, như GetTeamMemInfoByIndex)   (TeamFrame.lua)
    Thành viên nhóm  : DataPool:GetTeamMemberCount(), GetTeamMemInfoByIndex(i); chỉ số 0 là trưởng nhóm
    Lời mời đang chờ : DataPool:GetInviteTeamCount(), GetInviteTeamMemberCount(t), GetInviteTeamMemberInfo(t, i)
    Người xung quanh : UpdatePlayerList(true = phe bạn / false = phe địch), rồi
                       GetPlayerFromList(i) -> id, tên, cấp, bang, môn phái, loại; tối đa 16 người   (PlayerList.lua)
Bản game này không có Player:IsInTeam, còn DataPool:IsTeamLeader không cho biết mình có phải trưởng nhóm không.
"""
import time

from auto_chuyen_sinh import chuan_hoa
from bang_ma_viscii import giai_ma
from dang_nhap import chuoi_lua

SO_NGUOI_TOI_DA = 6
GIAY_MOI_LAI = 15
# Người chơi thật có thể đang bận hoặc từ chối, mời thưa hơn để không làm phiền.
GIAY_MOI_LAI_NGUOI_NGOAI = 60
GIAY_GIUA_HAI_LAN_ROI_NHOM = 30
GIAY_GIUA_HAI_LAN_NHUONG_TRUONG = 15

MA_DOC_NHOM = (
    'local s = "" '
    'local so = tonumber(DataPool:GetTeamMemberCount()) or 0 '
    'if so > 6 then so = 6 end '
    'for i = 0, so - 1 do s = s .. tostring(DataPool:GetTeamMemInfoByIndex(i)) .. "\\n" end '
    's = s .. "\\t" '
    'local moi = tonumber(DataPool:GetInviteTeamCount()) or 0 '
    'for t = 0, moi - 1 do '
    'for i = 0, (tonumber(DataPool:GetInviteTeamMemberCount(t)) or 0) - 1 do '
    's = s .. t .. "|" .. tostring(DataPool:GetInviteTeamMemberInfo(t, i)) .. "\\n" end end '
    'return s')

MA_DOC_XUNG_QUANH = (
    'local s = "" '
    'for _, phe in ipairs({true, false}) do '
    'UpdatePlayerList(phe) '
    'for i = 0, 15 do '
    'local id, ten = GetPlayerFromList(i) '
    'if id and id ~= -1 and ten and ten ~= "" then s = s .. tostring(ten) .. "\\n" end end end '
    'return s')


def doc_nhom(lua):
    """{"thanh_vien": [tên, trưởng nhóm đứng đầu], "loi_moi": [(chỉ số lời mời, tên một người trong nhóm mời)]}."""
    phan_nhom, phan_moi = lua.chay(MA_DOC_NHOM).split(b"\t", 1)
    loi_moi = []
    for dong in phan_moi.split(b"\n"):
        if dong:
            chi_so, ten = dong.split(b"|", 1)
            loi_moi.append((int(chi_so), giai_ma(ten)))
    return {"thanh_vien": [giai_ma(ten) for ten in phan_nhom.split(b"\n") if ten], "loi_moi": loi_moi}


def doc_xung_quanh(lua):
    """Tên những người chơi khác đang ở gần nhân vật (không tính bản thân)."""
    cac_ten = []
    for dong in lua.chay(MA_DOC_XUNG_QUANH).split(b"\n"):
        ten = giai_ma(dong) if dong else ""
        if ten and ten not in cac_ten:
            cac_ten.append(ten)
    return cac_ten


def _nhom_hon(truong_a, so_a, truong_b, so_b, nguoi_lap):
    """Nhóm của truong_a có nên giữ lại thay vì nhóm của truong_b không (đông hơn, rồi người lập nhóm, rồi theo tên)."""
    if so_a != so_b:
        return so_a > so_b
    a_lap, b_lap = chuan_hoa(truong_a) == chuan_hoa(nguoi_lap), chuan_hoa(truong_b) == chuan_hoa(nguoi_lap)
    if a_lap != b_lap:
        return a_lap
    return chuan_hoa(truong_a) < chuan_hoa(truong_b)


def _nhom_nen_nhap(ten, thanh_vien, nhom):
    """Tên trưởng một nhóm khác (do nhân vật trong auto làm trưởng) mà nhóm của ten nên nhập vào, hoặc None."""
    khoa = chuan_hoa(ten)
    trong_nhom = {chuan_hoa(nguoi) for nguoi in thanh_vien}
    for khoa_khac, tv_khac in nhom["cac_nhom"].items():
        if (khoa_khac == khoa or khoa_khac in trong_nhom or not tv_khac or chuan_hoa(tv_khac[0]) != khoa_khac
                or len(tv_khac) >= SO_NGUOI_TOI_DA):
            continue
        if _nhom_hon(tv_khac[0], len(tv_khac), ten, len(thanh_vien), nhom["nguoi_lap"]):
            return tv_khac[0]
    return None


def _moi_nguoi_con_thieu(lua, ten, thanh_vien, nhom, xung_quanh, trang_thai, in_log):
    khoa = chuan_hoa(ten)
    trong_nhom = {chuan_hoa(nguoi) for nguoi in thanh_vien}
    da_moi = trang_thai.setdefault("da_moi", {})
    for nguoi in [nguoi for nguoi in da_moi if chuan_hoa(nguoi) in trong_nhom]:
        del da_moi[nguoi]
    # Đang ở nhóm khác thì không nhận lời mời được; nhóm đó nhỏ hơn thì trưởng nhóm đó tự rời để nhập vào.
    o_nhom_khac = {k for k, tv in nhom["cac_nhom"].items() if tv and k not in trong_nhom}
    o_gan = {chuan_hoa(nguoi) for nguoi in xung_quanh}
    nguoi_ngoai = [nguoi for nguoi in nhom["nguoi_ngoai"] if chuan_hoa(nguoi) not in trong_nhom]
    can_moi = [(nguoi, GIAY_MOI_LAI) for nguoi in nhom["nhan_vat_auto"]
               if chuan_hoa(nguoi) not in trong_nhom and chuan_hoa(nguoi) != khoa
               and chuan_hoa(nguoi) not in o_nhom_khac]
    can_moi += [(nguoi, GIAY_MOI_LAI_NGUOI_NGOAI) for nguoi in nguoi_ngoai if chuan_hoa(nguoi) in o_gan]
    chua_gap = [nguoi for nguoi in nguoi_ngoai if chuan_hoa(nguoi) not in o_gan]
    so_nguoi = max(len(thanh_vien), 1)
    bay_gio = time.time()
    for nguoi, giay_moi_lai in can_moi:
        if so_nguoi >= SO_NGUOI_TOI_DA:
            break
        if bay_gio - da_moi.get(nguoi, 0) < giay_moi_lai:
            continue
        if nguoi not in da_moi:
            in_log(f"{ten}: mời {nguoi} vào nhóm")
        lua.chay(f"Target:SendTeamRequest({chuoi_lua(nguoi)})")
        da_moi[nguoi] = bay_gio
    mo_ta = f"Trưởng nhóm ({so_nguoi} người)" if thanh_vien else "Đang lập nhóm"
    if so_nguoi < SO_NGUOI_TOI_DA:
        if can_moi:
            mo_ta += f", đang mời {', '.join(nguoi for nguoi, _ in can_moi)}"
        if chua_gap:
            mo_ta += f", chưa thấy ở gần: {', '.join(chua_gap)}"
    return mo_ta


def xu_ly_nhom(lua, ten, nhom, xung_quanh, trang_thai, in_log):
    """
    Làm một lượt mời / đồng ý / nhập nhóm cho nhân vật ten.
    nhom = {"nhan_vat_auto": [nhân vật trong auto được vào nhóm], "nguoi_lap": tên người lập nhóm khi chưa ai có nhóm,
            "truong_uu_tien": trưởng nhóm chọn ở tab Nhóm nếu đang chạy trong auto, không thì "",
            "nguoi_ngoai": [người chơi ngoài auto trong danh sách mời],
            "cac_nhom": {tên chuẩn hóa của nhân vật trong auto: danh sách thành viên nhóm lần đọc gần nhất}};
    xung_quanh = doc_xung_quanh() của nhân vật này.
    Trả về (mô tả trạng thái nhóm để hiện lên giao diện, thành viên nhóm hiện tại - trưởng nhóm đứng đầu).
    """
    khoa = chuan_hoa(ten)
    hien_tai = doc_nhom(lua)
    thanh_vien = hien_tai["thanh_vien"]
    khoa_auto = {chuan_hoa(nguoi) for nguoi in nhom["nhan_vat_auto"]}
    if khoa not in khoa_auto:
        return "Không mời (không có trong danh sách mời)", thanh_vien

    if thanh_vien:
        truong = thanh_vien[0]
        if chuan_hoa(truong) != khoa:
            return f"Trong nhóm của {truong} ({len(thanh_vien)} người)", thanh_vien
        uu_tien = chuan_hoa(nhom["truong_uu_tien"])
        chi_so_uu_tien = next((i for i, nguoi in enumerate(thanh_vien) if i > 0 and chuan_hoa(nguoi) == uu_tien), None)
        if uu_tien and chi_so_uu_tien is not None:
            if time.time() - trang_thai.get("luc_nhuong_truong", 0) >= GIAY_GIUA_HAI_LAN_NHUONG_TRUONG:
                trang_thai["luc_nhuong_truong"] = time.time()
                in_log(f"{ten}: nhường trưởng nhóm lại cho {thanh_vien[chi_so_uu_tien]}")
                lua.chay(f"Player:AppointLeader({chi_so_uu_tien})")
            return f"Nhường trưởng nhóm cho {thanh_vien[chi_so_uu_tien]}", thanh_vien
        nhom_lon = _nhom_nen_nhap(ten, thanh_vien, nhom)
        if nhom_lon:
            if time.time() - trang_thai.get("luc_roi_nhom", 0) >= GIAY_GIUA_HAI_LAN_ROI_NHOM:
                trang_thai["luc_roi_nhom"] = time.time()
                in_log(f"{ten}: đang có 2 nhóm, rời nhóm mình để vào nhóm của {nhom_lon}")
                lua.chay("Player:LeaveTeam()")
            return f"Rời nhóm để vào nhóm của {nhom_lon}", thanh_vien
        return _moi_nguoi_con_thieu(lua, ten, thanh_vien, nhom, xung_quanh, trang_thai, in_log), thanh_vien

    ai_moi_cung_nhan = khoa_auto | {chuan_hoa(nguoi) for nguoi in nhom["nguoi_ngoai"]}
    for chi_so, nguoi in hien_tai["loi_moi"]:
        if chuan_hoa(nguoi) in ai_moi_cung_nhan and chuan_hoa(nguoi) != khoa:
            lua.chay(f"Player:AgreeJoinTeam({chi_so})")
            in_log(f"{ten}: đồng ý lời mời vào nhóm có {nguoi}")
            return f"Đồng ý lời mời của nhóm có {nguoi}", thanh_vien

    for khoa_khac, tv_khac in nhom["cac_nhom"].items():
        if khoa_khac != khoa and tv_khac and len(tv_khac) < SO_NGUOI_TOI_DA:
            return f"Chờ {tv_khac[0]} mời", thanh_vien
    if chuan_hoa(nhom["nguoi_lap"]) == khoa:
        return _moi_nguoi_con_thieu(lua, ten, thanh_vien, nhom, xung_quanh, trang_thai, in_log), thanh_vien
    return f"Chờ {nhom['nguoi_lap']} lập nhóm", thanh_vien
