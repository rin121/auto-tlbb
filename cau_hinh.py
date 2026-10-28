"""
Đọc và ghi cau_hinh.json.

Cấu trúc file:
  - Các thông số chung nằm ngoài cùng (giây chờ, số lần thử...).
  - "mac_dinh": cài đặt mẫu. Lần đầu thấy một nhân vật, auto chép cài đặt này cho nhân vật đó.
  - "nhan_vat": cài đặt riêng của từng nhân vật, theo tên nhân vật.

Giao diện và các luồng auto cùng đọc/ghi, nên mọi hàm đều đi qua một khóa và trả về bản sao.

Tài khoản để tự đăng nhập lại khi bị diss nằm riêng trong tai_khoan.json (có mật khẩu, đừng chia sẻ file này).
"""
import copy
import json
import os
import re
import shutil
import sys
import threading
import time
import unicodedata

import psutil

from thu_muc import THU_MUC_APP

DUONG_DAN = os.path.join(THU_MUC_APP, "cau_hinh.json")
CAC_KHOA_KHONG_PHAI_CHUNG = ("mac_dinh", "nhan_vat")
MAP_HOA_DIEM_SON = "Hỏa Diệm Sơn"
CAC_MAP_MAC_DINH = ["Hạn Huyết Lĩnh", MAP_HOA_DIEM_SON, "Cao Xương Mê Cung"]
# Dùng khi cau_hinh.json cũ chưa có thông số này.
MAC_DINH_CHUNG = {"giay_cho_game_khoi_dong": 90, "bat_moi_nhom": False, "truong_nhom": "",
                  "bat_moi_nhan_vat_auto": True, "danh_sach_moi": [], "dong_minh": [],
                  "bat_vut_rac": False, "giay_giua_moi_lan_vut_rac": 60,
                  "vut_trang_bi_duoi_sao": True, "so_sao_toi_thieu": 9,
                  "tu_nhap_ma_tao_nhan_vat": True, "tu_duyet_popup": True, "tu_nhan_ty_thi": False,
                  "tu_dung_x2": False, "tu_dung_can_khon_ho": False, "tu_thoat_khi_mat_ket_noi": True,
                  "chat_the_gioi": False, "noi_dung_chat_the_gioi": "", "giay_chat_the_gioi": 300,
                  "nhan_vat_chat_the_gioi": "",
                  "tat_am_thanh": True, "giam_do_hoa": True, "danh_sach_map": CAC_MAP_MAC_DINH,
                  "thu_tu_tab": [], "tab_an": [], "thu_tu_nhan_vat": [], "cao_bang": {},
                  "so_nguoi_mot_nhom": 4, "xv_chi_sat_tinh": False,
                  "xv_so_round": 3, "xv_test": False, "xv_chuyen_do": True, "xv_ngay_moi": True,
                  "xv_truong_nhom": [], "xv_tien_trinh": {},
                  "proxy": {"bat": False, "so_acc_moi_ip": 4, "danh_sach": ""}}
DUONG_DAN_TAI_KHOAN = os.path.join(THU_MUC_APP, "tai_khoan.json")
MAC_DINH_TAI_KHOAN = {
    "bat_tu_dang_nhap": False,
    "thu_muc_game": os.path.dirname(THU_MUC_APP),
    "may_chu": "Máy Chủ Mới",
    "ma_kiem_tra": "1234",
    "giai_ma_kiem_tra": False,
    "giay_cho_truoc_khi_nap_dll": 20,
    "giay_toi_da_moi_buoc": 60,
    "so_lan_thu_toi_da": 3,
    "so_game_mo_cung_luc": 10,
    "so_game_moi_dot": 1,
    "giay_giua_moi_dot": 2,
    "tai_khoan_pho_ban": [],
    "tai_khoan_train": [],
    # Tab "Tạo nhân vật": tài khoản mới cần tạo nhân vật + nhận đồ tân thủ; da_xong {tài khoản: [nhân vật đã nhận đồ]};
    # ten_thuc {tài khoản: {tên định đặt: tên đã tạo}} khi tên định đặt không tạo được (trùng) phải thêm số.
    "tao_nhan_vat_moi": {"danh_sach": "", "so_nhan_vat": 3, "nhan_do_tan_thu": True,
                         "da_xong": {}, "ten_thuc": {}},
}

THU_MUC_NGUON = os.path.dirname(os.path.abspath(__file__))
_THONG_BAO_PHUC_HOI = []
_khoa = threading.Lock()


def cac_thong_bao_phuc_hoi():
    return list(_THONG_BAO_PHUC_HOI)


def _duong_dan_mau(ten_file):
    goc = getattr(sys, "_MEIPASS", THU_MUC_NGUON) if getattr(sys, "frozen", False) else THU_MUC_NGUON
    return os.path.join(goc, ten_file)


def _ghi_nhat_ky_phuc_hoi(dong):
    try:
        with open(os.path.join(THU_MUC_APP, "nhat_ky_auto.log"), "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [cau_hinh] {dong}\n")
    except OSError:
        pass


def _doc_noi_dung_json(duong_dan):
    with open(duong_dan, encoding="utf-8") as f:
        chu = f.read().strip()
    if not chu:
        raise json.JSONDecodeError("File trống", chu, 0)
    return json.loads(chu)


def _doi_ten_file_hong(duong_dan):
    if not os.path.isfile(duong_dan):
        return None
    dich = f"{duong_dan}.hong_{time.strftime('%Y%m%d_%H%M%S')}"
    try:
        os.replace(duong_dan, dich)
        return dich
    except OSError:
        return None


def _ghi_json_an_toan(duong_dan, chu):
    """Ghi file tạm + thay thế; giữ .bak của bản trước (tránh file rỗng nếu máy treo giữa lúc ghi)."""
    tam = duong_dan + ".tmp"
    with open(tam, "w", encoding="utf-8", newline="\n") as f:
        f.write(chu)
        f.flush()
        try:
            os.fsync(f.fileno())
        except OSError:
            pass
    if os.path.isfile(duong_dan) and os.path.getsize(duong_dan) > 0:
        try:
            shutil.copy2(duong_dan, duong_dan + ".bak")
        except OSError:
            pass
    for lan in range(10):
        try:
            os.replace(tam, duong_dan)
            return
        except PermissionError:
            if lan == 9:
                raise
            time.sleep(0.1)


def _doc_json_voi_phuc_hoi(duong_dan, ten_hien_thi, tao_mac_dinh=None, duong_dan_mau=None, lam_chuoi=None):
    thu_tu = [duong_dan, duong_dan + ".tmp", duong_dan + ".bak"]
    if duong_dan_mau and os.path.isfile(duong_dan_mau):
        thu_tu.append(duong_dan_mau)
    for path in thu_tu:
        if not path or not os.path.isfile(path):
            continue
        try:
            du_lieu = _doc_noi_dung_json(path)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError) as loi:
            if os.path.abspath(path) == os.path.abspath(duong_dan):
                backup = _doi_ten_file_hong(duong_dan)
                if backup:
                    _ghi_nhat_ky_phuc_hoi(
                        f"{ten_hien_thi} hỏng ({loi}), đã đổi tên thành {os.path.basename(backup)}")
            continue
        thong_bao = None
        if os.path.abspath(path) != os.path.abspath(duong_dan):
            nguon = os.path.basename(path)
            thong_bao = (f"Đã phục hồi {ten_hien_thi} từ {nguon} "
                         "(file chính rỗng/hỏng — thường do máy treo khi đang lưu).")
            _ghi_nhat_ky_phuc_hoi(thong_bao)
            if lam_chuoi:
                _ghi_json_an_toan(duong_dan, lam_chuoi(du_lieu))
        return du_lieu, thong_bao
    if tao_mac_dinh:
        du_lieu = tao_mac_dinh()
        if lam_chuoi:
            _ghi_json_an_toan(duong_dan, lam_chuoi(du_lieu))
        thong_bao = f"Đã tạo {ten_hien_thi} mặc định (không đọc được file cũ)."
        _ghi_nhat_ky_phuc_hoi(thong_bao)
        return du_lieu, thong_bao
    raise json.JSONDecodeError(f"Không đọc được {ten_hien_thi}", "", 0)


def dinh_dang_json(du_lieu):
    chu = json.dumps(du_lieu, ensure_ascii=False, indent=4)
    # Viết danh sách ô trên một dòng: "cac_o": [[5, 1], [5, 2]] thay vì mỗi số một dòng.
    chu = re.sub(r"\[\s*(-?\d+),\s*(-?\d+)\s*\]", r"[\1, \2]", chu)
    chu = re.sub(r"\[\s*(\[-?\d+, -?\d+\](?:,\s*\[-?\d+, -?\d+\])*)\s*\]",
                 lambda m: "[" + re.sub(r",\s*\[", ", [", m.group(1)) + "]", chu)
    return chu + "\n"


def _chu_tai_khoan(du_lieu):
    return json.dumps(du_lieu, ensure_ascii=False, indent=4) + "\n"


_du_lieu, _tb_cau_hinh = _doc_json_voi_phuc_hoi(
    DUONG_DAN, "cau_hinh.json", duong_dan_mau=_duong_dan_mau("cau_hinh_khoi_tao.json"),
    lam_chuoi=dinh_dang_json)
if _tb_cau_hinh:
    _THONG_BAO_PHUC_HOI.append(_tb_cau_hinh)


_khoa_ghi = threading.Lock()
_ban_moi_nhat = 0
_ban_da_ghi = 0


def _chup_ban_luu():
    """Gọi khi đang giữ _khoa: chụp nội dung cau_hinh.json cần ghi kèm số thứ tự bản."""
    global _ban_moi_nhat
    _ban_moi_nhat += 1
    return _ban_moi_nhat, dinh_dang_json(_du_lieu)


def _ghi_ban_luu(ban):
    """
    Ghi ra đĩa sau khi đã nhả _khoa (fsync + .bak file ~1MB mất vài chục ms, các luồng auto không phải chờ).
    Luồng khác đã ghi bản mới hơn thì bỏ qua, để file không bị bản cũ ghi đè.
    """
    global _ban_da_ghi
    so, chu = ban
    with _khoa_ghi:
        if so <= _ban_da_ghi:
            return
        _ghi_json_an_toan(DUONG_DAN, chu)
        _ban_da_ghi = so


def _luu():
    _ghi_ban_luu(_chup_ban_luu())


def _sao_chep(gia_tri):
    """Như copy.deepcopy nhưng nhanh hơn nhiều với dữ liệu JSON (luồng auto đọc cài đặt liên tục)."""
    loai = type(gia_tri)
    if loai is dict:
        return {k: _sao_chep(v) for k, v in gia_tri.items()}
    if loai is list:
        return [_sao_chep(v) for v in gia_tri]
    if gia_tri is None or loai in (str, int, float, bool):
        return gia_tri
    return copy.deepcopy(gia_tri)


def _them_map_khi_bi_pk(cai_dat):
    """
    Cài đặt cũ: Hạn huyết lĩnh dùng Thổ Linh Châu ô 6,1 6,2 6,3. Nay ô 6,1 6,2 là option 1 (Hạn huyết lĩnh),
    ô 6,3 6,4 6,5 là option 2 (Cao Xương Mê Cung) - bị giết ở option 1 thì chuyển sang option 2.
    Mốc đã được sửa tay thành Cao Xương Mê Cung thì coi như đang dùng option 2.
    """
    vat_pham = cai_dat["vat_pham"]
    if "tlc_cao_xuong_me_cung" in vat_pham:
        return False
    vat_pham["tlc_cao_xuong_me_cung"] = {"cac_o": [[6, 3], [6, 4], [6, 5]]}
    han_huyet_linh = vat_pham.get("tlc_han_huyet_linh")
    if han_huyet_linh and han_huyet_linh["cac_o"] == [[6, 1], [6, 2], [6, 3]]:
        han_huyet_linh["cac_o"] = [[6, 1], [6, 2]]
    for moc in cai_dat["moc_level"]:
        if moc.get("vat_pham_dich_chuyen") == "tlc_han_huyet_linh":
            da_sang_option_2 = unicodedata.normalize("NFC", moc["map"]).casefold() == "cao xương mê cung"
            moc.update({"map": "Hạn huyết lĩnh", "map_khi_bi_pk": "Cao Xương Mê Cung",
                        "vat_pham_khi_bi_pk": "tlc_cao_xuong_me_cung", "dang_dung_map_pk": da_sang_option_2})
    return True


def _them_bat_chuyen_sinh(cai_dat):
    """
    Cài đặt cũ dùng chung "bat_auto" cho ô Auto và ô "Bật auto chuyển sinh". Nay tách riêng "bat_chuyen_sinh",
    mặc định tắt: ô Auto bật tự đánh / tiện ích, chuyển sinh chỉ chạy khi bật cả hai.
    """
    if "bat_chuyen_sinh" in cai_dat:
        return False
    cai_dat["bat_chuyen_sinh"] = False
    return True


def _hang_cua_vat_pham(cai_dat, ma, mac_dinh):
    cac_o = cai_dat.get("vat_pham", {}).get(ma, {}).get("cac_o")
    return cac_o[0][0] if cac_o else mac_dinh


def _doi_sang_hang_tui(cai_dat):
    """
    Cài đặt cũ chọn vật phẩm theo mã ("vat_pham_dich_chuyen" -> "vat_pham"[mã]["cac_o"]). Nay mỗi mốc chỉ ghi hàng
    trong túi ("hang_vat_pham_dich_chuyen", "hang_vat_pham_khi_bi_pk"): lấy hàng của ô đầu tiên đã khai báo.
    Chuyển sinh luôn dùng ô (1,1); dịch chuyển trước khi chuyển sinh là tùy chọn, mặc định tắt.
    """
    da_doi = False
    cs = cai_dat["chuyen_sinh"]
    for khoa, gia_tri in (("dich_chuyen_truoc_chuyen_sinh", False), ("map_truoc_chuyen_sinh", MAP_HOA_DIEM_SON),
                          ("hang_vat_pham_truoc_chuyen_sinh", _hang_cua_vat_pham(cai_dat, "tlc_hoa_diem_son", 5))):
        if khoa not in cs:
            cs[khoa] = gia_tri
            da_doi = True
    for moc in cai_dat["moc_level"]:
        if "hang_vat_pham_dich_chuyen" not in moc:
            moc["hang_vat_pham_dich_chuyen"] = _hang_cua_vat_pham(cai_dat, moc.pop("vat_pham_dich_chuyen", ""), 5)
            da_doi = True
        if moc.get("map_khi_bi_pk") and "hang_vat_pham_khi_bi_pk" not in moc:
            moc["hang_vat_pham_khi_bi_pk"] = _hang_cua_vat_pham(cai_dat, moc.pop("vat_pham_khi_bi_pk", ""), 6)
            da_doi = True
    return da_doi


MAC_DINH_CONG_DIEM = {"bat": False, "cac_chi_so": [], "tu_dung_hop_point": False}


def _them_cong_diem(cai_dat):
    """Tự cộng điểm tiềm năng / tự dùng Hộp Point (tab Chuyển sinh), mặc định tắt."""
    if "auto_cong_diem" in cai_dat:
        return False
    cai_dat["auto_cong_diem"] = copy.deepcopy(MAC_DINH_CONG_DIEM)
    return True


# so_vong: số vòng mỗi ngày (0 = tới khi hết lượt);
# sat_tinh: hết lượt PMP thì đi Thập Nhị Sát Tinh tới khi hết lượt;
# truong_khong_danh: trong PMP đội trưởng (có đội viên trong auto) chỉ cưỡi thú dẫn đường, để đội viên đánh;
# hom_nay: bộ đếm của luồng auto, sang ngày khác thì coi như chưa đi.
MAC_DINH_PHO_BAN_PMP = {"bat": False, "so_vong": 0, "to_doi": False,
                        "sat_tinh": True, "chi_sat_tinh": False, "truong_khong_danh": True,
                        "hom_nay": {"ngay": "", "so_vong": 0, "so_het_luot": False, "het_luot": False,
                                    "st_vong": 0, "st_het": False}}


# Sự kiện Ác Tặc (su_kien_ac_tac.py): map_uu_tien là các map đã chọn theo thứ tự đi, thu_tu_map là thứ tự hiện trong
# danh sách (cả map chưa chọn); route "moi" = [ACTAC] GAuto (nhanh), "cu" = [ACTACKIEUCU] (chậm mà không sót).
CAC_MAP_AC_TAC = ["Vô Lượng Sơn", "Kiếm Các", "Tây Hồ", "Đôn Hoàng", "Thái Hồ", "Tung Sơn"]
# chay_pathpoints / cho_party / tu_tim: GAuto tab Ác Tặc — cboxATRunPP (thường tắt), cboxChoParty, cboxIsTrungAc (Tự tìm).
# Tắt pathpoints = «Chạy tìm»: quét lỏng quanh mốc ACTAC, không đi từng điểm cố định.
MAC_DINH_AC_TAC = {"bat": False, "bo_khung_02h": False, "route": "moi", "ten_quai": "Ác Tặc",
                   "ten_npc": "Ác Tặc Tạo Phản", "dong_khieu": "chẳng lẽ",
                   "chay_pathpoints": False, "cho_party": True, "tu_tim": True,
                   "dung_gauto": False, "duong_dan_gauto": "", "phut_gauto": 30,
                   "map_uu_tien": list(CAC_MAP_AC_TAC), "thu_tu_map": list(CAC_MAP_AC_TAC)}


def _them_ac_tac(cai_dat):
    """Sự kiện Ác Tặc (tab "Phó bản"), mặc định tắt. Bản đầu ghi nhầm Kính Hồ: đổi sang Tây Hồ."""
    if "ac_tac" not in cai_dat:
        cai_dat["ac_tac"] = copy.deepcopy(MAC_DINH_AC_TAC)
        return True
    doi = False
    for khoa in ("map_uu_tien", "thu_tu_map"):
        ds = cai_dat["ac_tac"].get(khoa)
        if isinstance(ds, list) and "Kính Hồ" in ds:
            cai_dat["ac_tac"][khoa] = ["Tây Hồ" if m == "Kính Hồ" else m for m in ds]
            doi = True
    for khoa, gia_tri in MAC_DINH_AC_TAC.items():
        if khoa not in cai_dat["ac_tac"]:
            cai_dat["ac_tac"][khoa] = gia_tri
            doi = True
    return doi


def _them_pho_ban_pmp(cai_dat):
    """Tự đi phó bản Phiêu Miễu Phong (tab Phó bản), mặc định tắt."""
    sua = False
    if "pho_ban_pmp" not in cai_dat:
        cai_dat["pho_ban_pmp"] = copy.deepcopy(MAC_DINH_PHO_BAN_PMP)
        sua = True
    elif "chi_sat_tinh" not in cai_dat["pho_ban_pmp"]:
        cai_dat["pho_ban_pmp"]["chi_sat_tinh"] = False
        sua = True
    return sua


def _tat_chi_in_khong_bam(cai_dat):
    """Giao diện không còn ô "Chỉ thử": nhân vật nào đang ở chế độ thử thì tắt, kẻo không bao giờ dùng vật phẩm."""
    if not cai_dat.get("chi_in_khong_bam"):
        return False
    cai_dat["chi_in_khong_bam"] = False
    return True


def _them_xv_chung(du_lieu):
    sua = False
    for khoa, mac in (("so_nguoi_mot_nhom", 4), ("xv_chi_sat_tinh", False), ("xv_so_round", 3),
                      ("xv_test", False), ("xv_chuyen_do", True), ("xv_ngay_moi", True)):
        if khoa not in du_lieu:
            du_lieu[khoa] = mac
            sua = True
    return sua


def _them_proxy_chung(du_lieu):
    if "proxy" in du_lieu:
        return False
    du_lieu["proxy"] = copy.deepcopy(MAC_DINH_CHUNG["proxy"])
    return True


def _bat_tu_duyet_mot_lan(du_lieu):
    """Một lần: bật Tự duyệt popup (mặc định mới là bật); sau đó người dùng tắt thì giữ tắt."""
    if du_lieu.get("_da_bat_tu_duyet"):
        return False
    du_lieu["tu_duyet_popup"] = True
    du_lieu["_da_bat_tu_duyet"] = True
    return True


def _dong_bo_ac_tac_mac_dinh(du_lieu):
    """Ác Tặc lưu chung mac_dinh: nếu mac_dinh chưa bật mà có nhân vật đã bật thì copy cài đặt sang."""
    md = du_lieu["mac_dinh"]
    if (md.get("ac_tac") or {}).get("bat"):
        return False
    for cai_dat in du_lieu["nhan_vat"].values():
        at = cai_dat.get("ac_tac") or {}
        if at.get("bat"):
            md["ac_tac"] = copy.deepcopy(at)
            return True
    return False


def _ac_tac_mac_dinh_chay_tim_gauto(du_lieu):
    """Một lần: mac_dinh bật pathpoints (mặc định cũ) → tắt để khớp GAuto «Chạy tìm», không «Chạy pathpoints»."""
    md = du_lieu["mac_dinh"]
    at = md.get("ac_tac")
    if not at or at.get("_gauto_chay_tim") or not at.get("chay_pathpoints"):
        return False
    at = dict(at)
    at["chay_pathpoints"] = False
    at["_gauto_chay_tim"] = True
    md["ac_tac"] = at
    return True


if any([_them_map_khi_bi_pk(_du_lieu["mac_dinh"]), _them_bat_chuyen_sinh(_du_lieu["mac_dinh"]),
        _them_xv_chung(_du_lieu), _them_proxy_chung(_du_lieu), _bat_tu_duyet_mot_lan(_du_lieu)]
       + [_them_cong_diem(cai_dat) for cai_dat in [_du_lieu["mac_dinh"], *_du_lieu["nhan_vat"].values()]]
       + [_them_pho_ban_pmp(cai_dat) for cai_dat in [_du_lieu["mac_dinh"], *_du_lieu["nhan_vat"].values()]]
       + [_them_ac_tac(cai_dat) for cai_dat in [_du_lieu["mac_dinh"], *_du_lieu["nhan_vat"].values()]]
       + [_them_map_khi_bi_pk(cai_dat) for cai_dat in _du_lieu["nhan_vat"].values()]
       + [_them_bat_chuyen_sinh(cai_dat) for cai_dat in _du_lieu["nhan_vat"].values()]
       + [_doi_sang_hang_tui(cai_dat) for cai_dat in [_du_lieu["mac_dinh"], *_du_lieu["nhan_vat"].values()]]
       + [_tat_chi_in_khong_bam(cai_dat) for cai_dat in _du_lieu["nhan_vat"].values()]
       + [_dong_bo_ac_tac_mac_dinh(_du_lieu), _ac_tac_mac_dinh_chay_tim_gauto(_du_lieu)]):
    _luu()


def chung():
    with _khoa:
        gia_tri = _sao_chep(MAC_DINH_CHUNG)
        gia_tri.update({k: _sao_chep(v) for k, v in _du_lieu.items() if k not in CAC_KHOA_KHONG_PHAI_CHUNG})
        return gia_tri


def dat_chung(gia_tri):
    with _khoa:
        _du_lieu.update(_sao_chep(gia_tri))
        ban = _chup_ban_luu()
    _ghi_ban_luu(ban)


def cac_nhan_vat():
    with _khoa:
        return list(_du_lieu["nhan_vat"])


def cua_nhan_vat(ten):
    """Cài đặt của một nhân vật. Chưa có thì tạo từ "mac_dinh"."""
    ban = None
    with _khoa:
        if ten not in _du_lieu["nhan_vat"]:
            _du_lieu["nhan_vat"][ten] = _sao_chep(_du_lieu["mac_dinh"])
            ban = _chup_ban_luu()
        gia_tri = _sao_chep(_du_lieu["nhan_vat"][ten])
    if ban:
        _ghi_ban_luu(ban)
    return gia_tri


def dat_nhan_vat(ten, cai_dat):
    with _khoa:
        _du_lieu["nhan_vat"][ten] = _sao_chep(cai_dat)
        ban = _chup_ban_luu()
    _ghi_ban_luu(ban)


def sua_nhan_vat(ten, ham):
    """ham(cài đặt) sửa thẳng cài đặt đã lưu của nhân vật, trong cùng một lần khóa (luồng auto cập nhật bộ đếm)."""
    with _khoa:
        if ten not in _du_lieu["nhan_vat"]:
            _du_lieu["nhan_vat"][ten] = _sao_chep(_du_lieu["mac_dinh"])
        ham(_du_lieu["nhan_vat"][ten])
        ban = _chup_ban_luu()
        gia_tri = _sao_chep(_du_lieu["nhan_vat"][ten])
    _ghi_ban_luu(ban)
    return gia_tri


def cap_nhat_tat_ca_nhan_vat(ham):
    """
    ham(cài đặt) sửa từng nhân vật; trả về True nếu có thay đổi.
    Chỉ ghi cau_hinh.json một lần (dùng khi dọn cờ hàng loạt lúc mở app).
    """
    ban = None
    with _khoa:
        doi = False
        for cai_dat in _du_lieu["nhan_vat"].values():
            if ham(cai_dat):
                doi = True
        if doi:
            ban = _chup_ban_luu()
    if ban:
        _ghi_ban_luu(ban)
    return doi


def thay_tat_ca_nhan_vat(ham):
    """
    Như lặp cua_nhan_vat + dat_nhan_vat cho mọi nhân vật nhưng chỉ ghi cau_hinh.json một lần:
    ham(tên, bản sao cài đặt) trả về cài đặt mới. ham chạy khi đang giữ khóa nên không được gọi lại cau_hinh.
    """
    with _khoa:
        nhan_vat = _du_lieu["nhan_vat"]
        for ten in list(nhan_vat):
            nhan_vat[ten] = _sao_chep(ham(ten, _sao_chep(nhan_vat[ten])))
        ban = _chup_ban_luu()
    _ghi_ban_luu(ban)


def mac_dinh():
    with _khoa:
        return _sao_chep(_du_lieu["mac_dinh"])


def dat_mac_dinh(cai_dat):
    with _khoa:
        _du_lieu["mac_dinh"] = _sao_chep(cai_dat)
        ban = _chup_ban_luu()
    _ghi_ban_luu(ban)


KHOA_TK_PHO_BAN = "tai_khoan_pho_ban"
KHOA_TK_TRAIN = "tai_khoan_train"


def chuan_hoa_danh_sach_tai_khoan(du_lieu):
    """
    tai_khoan.json cũ chỉ có "tai_khoan": chuyển hết sang tai_khoan_pho_ban.
    Trả về True nếu đã đổi cấu trúc (cần lưu lại file).
    """
    doi = False
    if du_lieu.get(KHOA_TK_PHO_BAN) is None and du_lieu.get(KHOA_TK_TRAIN) is None:
        legacy = du_lieu.get("tai_khoan") or []
        du_lieu[KHOA_TK_PHO_BAN] = copy.deepcopy(legacy)
        du_lieu[KHOA_TK_TRAIN] = []
        doi = True
    du_lieu.setdefault(KHOA_TK_PHO_BAN, [])
    du_lieu.setdefault(KHOA_TK_TRAIN, [])
    if du_lieu.get("tai_khoan") is not None:
        du_lieu.pop("tai_khoan", None)
        doi = True
    return doi


def tai_khoan_pho_ban():
    return doc_tai_khoan()[KHOA_TK_PHO_BAN]


def tai_khoan_train():
    return doc_tai_khoan()[KHOA_TK_TRAIN]


def tat_ca_muc_tai_khoan(cai_dat=None):
    cai_dat = cai_dat or doc_tai_khoan()
    return list(cai_dat[KHOA_TK_PHO_BAN]) + list(cai_dat[KHOA_TK_TRAIN])


def muc_tai_khoan(ten_dang_nhap, cai_dat=None):
    """(bản ghi tài khoản, KHOA_TK_PHO_BAN|KHOA_TK_TRAIN) hoặc (None, None)."""
    cai_dat = cai_dat or doc_tai_khoan()
    ten = (ten_dang_nhap or "").strip()
    for khoa in (KHOA_TK_PHO_BAN, KHOA_TK_TRAIN):
        for tk in cai_dat[khoa]:
            if tk.get("ten_dang_nhap") == ten:
                return tk, khoa
    return None, None


def _luu_tai_khoan(du_lieu):
    chuan_hoa_danh_sach_tai_khoan(du_lieu)
    _ghi_json_an_toan(DUONG_DAN_TAI_KHOAN, _chu_tai_khoan(du_lieu))


def la_thu_muc_game(thu_muc):
    return bool(thu_muc) and os.path.isfile(os.path.join(thu_muc, "Bin", "Game.exe"))


def tim_thu_muc_game():
    """Thư mục có Bin\\Game.exe: thư mục chứa auto hoặc một thư mục cha của nó, không có thì lấy từ Game.exe đang chạy."""
    thu_muc = THU_MUC_APP
    while True:
        if la_thu_muc_game(thu_muc):
            return thu_muc
        cha = os.path.dirname(thu_muc)
        if cha == thu_muc:
            break
        thu_muc = cha
    for tien_trinh in psutil.process_iter(["name", "exe"]):
        duong_dan = tien_trinh.info["exe"]
        if (tien_trinh.info["name"] or "").lower() == "game.exe" and duong_dan:
            thu_muc = os.path.dirname(os.path.dirname(duong_dan))
            if la_thu_muc_game(thu_muc):
                return thu_muc
    return None


def doc_tai_khoan():
    """
    Đọc lại tai_khoan.json mỗi lần gọi, nên sửa file bằng tay cũng có tác dụng ngay.
    Thư mục game không có Bin\\Game.exe (vd. chép auto sang chỗ khác) thì tự tìm lại và lưu.
    """
    with _khoa:
        du_lieu, tb = _doc_json_voi_phuc_hoi(
            DUONG_DAN_TAI_KHOAN, "tai_khoan.json",
            tao_mac_dinh=lambda: copy.deepcopy(MAC_DINH_TAI_KHOAN),
            lam_chuoi=_chu_tai_khoan)
        if tb:
            _THONG_BAO_PHUC_HOI.append(tb)
        # Chuẩn hóa trên dữ liệu đọc từ file (chưa trộn mặc định), chỉ ghi lại khi file thật sự là dạng cũ.
        can_luu = chuan_hoa_danh_sach_tai_khoan(du_lieu)
        if not la_thu_muc_game(du_lieu.get("thu_muc_game")):
            thu_muc = tim_thu_muc_game()
            if thu_muc:
                du_lieu["thu_muc_game"] = thu_muc
                can_luu = True
        if can_luu:
            _luu_tai_khoan(du_lieu)
        gia_tri = copy.deepcopy(MAC_DINH_TAI_KHOAN)
        gia_tri.update(du_lieu)
        gia_tri["tao_nhan_vat_moi"] = copy.deepcopy(
            dict(MAC_DINH_TAI_KHOAN["tao_nhan_vat_moi"], **du_lieu.get("tao_nhan_vat_moi", {})))
        return gia_tri


def luu_tai_khoan(du_lieu):
    with _khoa:
        ban = copy.deepcopy(du_lieu)
        chuan_hoa_danh_sach_tai_khoan(ban)
        _luu_tai_khoan(ban)
