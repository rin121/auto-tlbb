"""
AUTO CHUYỂN SINH - phần quyết định và dùng vật phẩm, gọi qua API Lua của game.
Giao diện (giao_dien.py) gọi xu_ly_nhan_vat() liên tục cho từng nhân vật đã bật auto.

Luật (mỗi nhân vật có cài đặt riêng, chỉnh trong giao diện):
  - Level >= level chuyển sinh -> dùng vật phẩm ở ô (1,1). Nếu tích "dịch chuyển trước khi chuyển sinh" thì
    chưa ở map đã chọn thì dùng vật phẩm ở hàng đã chọn để tới đó trước, tới nơi rồi mới dùng ô (1,1).
  - Thổ Linh Châu phải vận công: bị đánh ngắt vận công thì dùng lại đúng ô đó (cho_dich_chuyen).
  - Còn lại (kể cả ngay sau khi chuyển sinh): tìm mốc level cao nhất mà nhân vật đạt được,
    chưa ở map train của mốc đó thì dùng vật phẩm ở hàng túi của mốc để dịch chuyển.
  - Đã ở đúng map: không làm gì, để ChickenAuto tự đánh quái.
  - Mốc có "map_khi_bi_pk" (option 2): "dang_dung_map_pk" (ô "Đang dùng") chọn map phải đứng: tắt thì map chính,
    bật thì option 2; đứng ở map còn lại cũng dịch chuyển. Cờ tự đổi khi rời map train (sau chuyển sinh, chết):
      + Lúc chuyển sinh: đang đứng ở option 2 thì nhớ option 2, ở map chính thì nhớ map chính,
        ở map khác thì giữ nguyên.
      + Bị giết (HP = 0) ở map chính hoặc option 2: nhớ option 2.
  - Bị giết: bấm "Đầu thai" (Player:SendReliveMessage_OutGhost, Relive.lua).

Vật phẩm dịch chuyển chọn theo hàng trong túi: auto duyệt ô cột 1 tới cột 5 của hàng đó, ô trống thì bỏ qua;
dùng một ô mà không có tác dụng thì thử ô tiếp theo. Không so tên / mã vật phẩm vì mỗi server đặt mã khác nhau:
ô nào được chọn thì dùng đồ đang nằm ở ô đó.

Khi "chi_in_khong_bam" = true, auto vẫn đọc game và kiểm tra túi đồ, nhưng KHÔNG dùng vật phẩm.
"""
import time
import unicodedata

import cau_hinh
from game_api import SO_O_MOI_HANG
from lua_game import LoiLua

GIAY_GIUA_HAI_LAN_DAU_THAI = 5
# HP có thể đọc ra 0 thoáng qua lúc đang tải map: chưa thấy bảng Hồi sinh thì phải thấy HP = 0 đủ lâu mới coi là chết.
GIAY_HP_0_MOI_COI_LA_CHET = 3
# Thổ Linh Châu phải vận công: thanh vận công là ProgressBar_Progress (ProgressBar.lua). Hết vận công / bị đánh
# (PROGRESSBAR_BREAK) game chỉ làm mờ thanh đi, cửa sổ "ProgressBar" vẫn IsWindowShow = true, nên phải xem
# IsVisible() của thanh. Thanh tắt mà chưa tới map thì coi là bị ngắt và dùng lại đúng ô đó.
MA_DANG_VAN_CONG = ('if not IsWindowShow("ProgressBar") then return "0" end '
                    'local ok, hien = pcall(function() '
                    'return rawget(getfenv(0), "ProgressBar_Env").ProgressBar_Progress:IsVisible() end) '
                    'if ok and hien then return "1" end return "0"')
O_VAT_PHAM_CHUYEN_SINH = (1, 1)
GIAY_CHO_THANH_VAN_CONG = 3
GIAY_CHO_SAU_KHI_HET_VAN_CONG = 3
GIAY_CHO_TOI_MAP_KHI_LOADING = 15
SO_LAN_DUNG_LAI_KHI_BI_NGAT = 20
GIAY_NGHI_TRUOC_KHI_DUNG_LAI = 1


def chuan_hoa(chu):
    """Để "Hạn huyết lĩnh" và "Hạn Huyết Lĩnh" được coi là giống nhau."""
    return unicodedata.normalize("NFC", chu).casefold().strip()


def cung_map(map_a, map_b):
    return chuan_hoa(map_a) == chuan_hoa(map_b)


def cac_o_cua_viec(hang):
    """Các ô sẽ dùng: hàng None là vật phẩm chuyển sinh ở ô (1,1), còn lại là cột 1 tới cột 5 của hàng đó."""
    if hang is None:
        return [O_VAT_PHAM_CHUYEN_SINH]
    return [(hang, cot) for cot in range(1, SO_O_MOI_HANG + 1)]


def mo_ta_o(hang):
    return "ô (1,1)" if hang is None else f"hàng {hang}"


def viec_can_lam(cai_dat, level, map_dang_o):
    """
    Quyết định việc cần làm dựa trên level và map hiện tại.
    Trả về (loại việc, hàng vật phẩm trong túi - None là ô (1,1), map đích) hoặc None nếu không cần làm gì.
    """
    cs = cai_dat["chuyen_sinh"]
    if level >= cs["level"]:
        map_truoc = cs.get("map_truoc_chuyen_sinh", "").strip()
        if cs.get("dich_chuyen_truoc_chuyen_sinh") and map_truoc and not cung_map(map_dang_o, map_truoc):
            return ("dich_chuyen", cs["hang_vat_pham_truoc_chuyen_sinh"], map_truoc)
        return ("chuyen_sinh", None, None)

    moc = moc_hien_tai(cai_dat, level)
    if moc is None:
        return None
    map_dich, hang = dich_cua_moc(moc)
    if not cung_map(map_dang_o, map_dich):
        return ("dich_chuyen", hang, map_dich)
    return None


def moc_hien_tai(cai_dat, level):
    """Mốc level cao nhất mà nhân vật đã đạt, hoặc None."""
    for moc in sorted(cai_dat["moc_level"], key=lambda m: m["level"], reverse=True):
        if level >= moc["level"]:
            return moc
    return None


def dich_cua_moc(moc):
    """(map, hàng vật phẩm trong túi) mốc đang dùng: map khi bị PK nếu đã chuyển sang, không thì map chính."""
    if moc.get("dang_dung_map_pk") and moc.get("map_khi_bi_pk"):
        return moc["map_khi_bi_pk"], moc["hang_vat_pham_khi_bi_pk"]
    return moc["map"], moc["hang_vat_pham_dich_chuyen"]


def o_map_nao_cua_moc(moc, map_dang_o):
    """"chinh" / "pk" nếu đang đứng ở map chính / option 2 của mốc, None nếu map khác."""
    if cung_map(map_dang_o, moc["map"]):
        return "chinh"
    if moc.get("map_khi_bi_pk") and cung_map(map_dang_o, moc["map_khi_bi_pk"]):
        return "pk"
    return None


def dat_co_map_pk(ten, level_moc, gia_tri):
    cai_dat = cau_hinh.cua_nhan_vat(ten)
    for moc in cai_dat["moc_level"]:
        if moc["level"] == level_moc and moc.get("map_khi_bi_pk"):
            moc["dang_dung_map_pk"] = gia_tri
    cau_hinh.dat_nhan_vat(ten, cai_dat)


def ghi_nho_map_truoc_chuyen_sinh(ten, level, map_dang_o, cai_dat, in_log, bao_doi_cai_dat):
    moc = moc_hien_tai(cai_dat, level)
    if not moc or not moc.get("map_khi_bi_pk"):
        return
    o_dau = o_map_nao_cua_moc(moc, map_dang_o)
    if o_dau is None:
        return
    muon = o_dau == "pk"
    if bool(moc.get("dang_dung_map_pk")) == muon:
        return
    if cai_dat["chi_in_khong_bam"]:
        in_log(f"  [THỬ] {ten}: sẽ nhớ [{map_dang_o}] để lên lại khi tới level {moc['level']}")
        return
    dat_co_map_pk(ten, moc["level"], muon)
    bao_doi_cai_dat()
    in_log(f"  {ten}: nhớ [{map_dang_o}], chuyển sinh xong tới level {moc['level']} sẽ lên lại map này")


def da_chet_that(game, trang_thai):
    if trang_thai.get("luc_hp_0") is None:
        trang_thai["luc_hp_0"] = time.time()
    if game.lua.chay('return tostring(IsWindowShow("Relive"))') == b"true":
        return True
    return time.time() - trang_thai["luc_hp_0"] >= GIAY_HP_0_MOI_COI_LA_CHET


def xu_ly_khi_chet(game, ten, level, map_dang_o, cai_dat, chung, trang_thai, in_log, nen_dung, bao_doi_cai_dat):
    if not da_chet_that(game, trang_thai):
        trang_thai["mo_ta"] = "HP = 0, đang xem có phải đã chết"
        return
    trang_thai["mo_ta"] = "Đã chết, chờ Đầu thai"
    if time.time() - trang_thai.get("luc_dau_thai", 0) < GIAY_GIUA_HAI_LAN_DAU_THAI:
        return
    chi_thu = cai_dat["chi_in_khong_bam"]
    moc = moc_hien_tai(cai_dat, level)
    if moc and moc.get("map_khi_bi_pk") and not moc.get("dang_dung_map_pk") and o_map_nao_cua_moc(moc, map_dang_o):
        if chi_thu:
            if not trang_thai.get("da_in_chet"):
                in_log(f"  [THỬ] {ten}: bị giết ở [{map_dang_o}], sẽ chuyển mốc level {moc['level']} "
                       f"sang [{moc['map_khi_bi_pk']}]")
        else:
            dat_co_map_pk(ten, moc["level"], True)
            bao_doi_cai_dat()
            in_log(f"{ten} bị giết ở [{map_dang_o}], từ giờ mốc level {moc['level']} train ở "
                   f"[{moc['map_khi_bi_pk']}]")
    if chi_thu:
        if not trang_thai.get("da_in_chet"):
            in_log(f"  [THỬ] {ten}: đã chết ở [{map_dang_o}], sẽ bấm Đầu thai")
        trang_thai["da_in_chet"] = True
        trang_thai["mo_ta"] = "[Thử] sẽ bấm Đầu thai"
        return

    trang_thai["luc_dau_thai"] = time.time()
    in_log(f"{ten} đã chết ở [{map_dang_o}] -> Đầu thai")
    game.lua.chay("Player:SendReliveMessage_OutGhost()")
    if cho(lambda: game.hp() > 0, chung["giay_cho_toi_da"], nen_dung):
        in_log(f"  {ten}: đã sống lại ở [{game.ten_map()}]")
    else:
        in_log(f"  {ten}: bấm Đầu thai mà chưa sống lại, sẽ thử lại")


def tim_cac_o(game, cac_o):
    """
    Duyệt các ô [(hàng, cột)] theo đúng thứ tự.
    Trả về (các ô có đồ [(hàng, cột, tên)], lý do các ô bị bỏ qua).
    """
    cac_o_dung, bo_qua = [], []
    for hang, cot in cac_o:
        thong_tin = game.vat_pham_o(hang, cot)
        if thong_tin is None:
            bo_qua.append(f"({hang},{cot}) trống")
        else:
            cac_o_dung.append((hang, cot, thong_tin["ten"]))
    return cac_o_dung, bo_qua


def cho(dieu_kien, so_giay, nen_dung):
    """Chờ tới khi dieu_kien() đúng. Lúc đang loading game có thể không trả lời, nên bỏ qua lỗi."""
    for _ in range(so_giay):
        if nen_dung():
            return False
        time.sleep(1)
        try:
            if dieu_kien():
                return True
        except LoiLua:
            pass
    return False


def _doc_an_toan(ham):
    """Gọi ham(), lúc đang loading game không trả lời thì coi như None."""
    try:
        return ham()
    except LoiLua:
        return None


def cho_dich_chuyen(game, da_xong, giay_toi_da, nen_dung):
    """
    Chờ sau khi dùng Thổ Linh Châu. da_xong(tên map) cho biết đứng ở map đó là xong việc chưa. Trả về:
      "toi"            : đã tới map xong việc
      "bi_ngat"        : thanh vận công đã hiện rồi tắt mà chưa tới map (bị đánh, bị di chuyển...)
      "khong_tac_dung" : không thấy vận công và không tới map trong giay_toi_da giây
    """
    def da_toi():
        ten_map = _doc_an_toan(game.ten_map)
        return ten_map is not None and da_xong(ten_map)

    def dang_van_cong():
        return _doc_an_toan(lambda: game.lua.chay(MA_DANG_VAN_CONG)) == b"1"

    bat_dau = time.time()
    thay_van_cong = False
    while time.time() - bat_dau < GIAY_CHO_THANH_VAN_CONG:
        if nen_dung():
            return "khong_tac_dung"
        if da_toi():
            return "toi"
        if dang_van_cong():
            thay_van_cong = True
            break
        time.sleep(0.2)

    if not thay_van_cong:
        con_lai = max(int(giay_toi_da - (time.time() - bat_dau)), 1)
        return "toi" if cho(da_toi, con_lai, nen_dung) else "khong_tac_dung"

    while time.time() - bat_dau < giay_toi_da and dang_van_cong():
        if nen_dung():
            return "khong_tac_dung"
        if da_toi():
            return "toi"
        time.sleep(0.3)

    # Vận công xong thì game dịch chuyển ngay (đổi map hoặc đang loading không trả lời Lua).
    # Thanh đã tắt mà game vẫn trả lời và chưa đổi map thì là bị ngắt.
    het_han = time.time() + GIAY_CHO_SAU_KHI_HET_VAN_CONG
    while time.time() < het_han:
        if nen_dung():
            return "khong_tac_dung"
        ten_map = _doc_an_toan(game.ten_map)
        if ten_map is None:
            het_han = max(het_han, time.time() + GIAY_CHO_TOI_MAP_KHI_LOADING)
        elif da_xong(ten_map):
            return "toi"
        time.sleep(0.3)
    return "bi_ngat"


def xu_ly_nhan_vat(game, ten, level, map_dang_o, hp, cai_dat, chung, trang_thai, in_log, nen_dung=lambda: False,
                   bao_doi_cai_dat=lambda: None):
    """
    Làm một bước auto cho một nhân vật.
    trang_thai là dict riêng của nhân vật, giữ lại giữa các lần gọi:
      so_lan_that_bai, so_lan_chuyen_sinh, viec_da_in (chế độ thử), mo_ta (dòng trạng thái trên giao diện).
    nen_dung() trả về True khi người dùng tắt auto giữa chừng.
    bao_doi_cai_dat() được gọi khi auto tự sửa "dang_dung_map_pk" đã lưu của nhân vật.
    """
    if hp <= 0:
        xu_ly_khi_chet(game, ten, level, map_dang_o, cai_dat, chung, trang_thai, in_log, nen_dung, bao_doi_cai_dat)
        return
    trang_thai["da_in_chet"] = False
    trang_thai["luc_hp_0"] = None

    toi_da = chung["so_lan_thu_toi_da"]
    if trang_thai.get("so_lan_that_bai", 0) >= toi_da:
        return

    viec = viec_can_lam(cai_dat, level, map_dang_o)
    if viec is None:
        trang_thai["mo_ta"] = f"Đang train ở {map_dang_o}"
        trang_thai["viec_da_in"] = None
        return
    chi_thu = cai_dat["chi_in_khong_bam"]
    if chi_thu and viec == trang_thai.get("viec_da_in"):
        return
    trang_thai["viec_da_in"] = viec
    loai_viec, hang_vat_pham, map_dich = viec
    ten_o = mo_ta_o(hang_vat_pham)

    if loai_viec == "dich_chuyen":
        trang_thai["mo_ta"] = f"Dịch chuyển tới {map_dich}"
        in_log(f"{ten} level {level} -> dịch chuyển tới [{map_dich}]")
    else:
        trang_thai["mo_ta"] = "Đang chuyển sinh"
        in_log(f"{ten} level {level} -> CHUYỂN SINH")
        ghi_nho_map_truoc_chuyen_sinh(ten, level, map_dang_o, cai_dat, in_log, bao_doi_cai_dat)

    cac_o_dung, bo_qua = tim_cac_o(game, cac_o_cua_viec(hang_vat_pham))
    if bo_qua and hang_vat_pham is None:
        in_log(f"  {ten}: {ten_o} bỏ qua ô " + ", ".join(bo_qua))

    if not cac_o_dung:
        in_log(f"  {ten}: {ten_o} trong túi không có vật phẩm")
    elif chi_thu:
        danh_sach = ", ".join(f"({hang},{cot})" for hang, cot, _ in cac_o_dung)
        in_log(f"  [THỬ] {ten}: sẽ dùng lần lượt các ô {danh_sach}")
        trang_thai["mo_ta"] = f"[Thử] sẽ dùng {ten_o}"
        trang_thai["so_lan_that_bai"] = 0
        return
    else:
        for hang, cot, ten_vat_pham in cac_o_dung:
            game.dung_o(hang, cot)
            in_log(f"  {ten}: đã dùng '{ten_vat_pham}' ở ô ({hang},{cot})")
            if loai_viec == "dich_chuyen":
                def da_xong(ten_map):
                    return cung_map(ten_map, map_dich) or viec_can_lam(cai_dat, level, ten_map) != viec

                ket_qua = cho_dich_chuyen(game, da_xong, chung["giay_cho_toi_da"], nen_dung)
                so_lan_bi_ngat = 0
                while ket_qua == "bi_ngat" and so_lan_bi_ngat < SO_LAN_DUNG_LAI_KHI_BI_NGAT and not nen_dung():
                    so_lan_bi_ngat += 1
                    in_log(f"  {ten}: vận công Thổ Linh Châu bị ngắt (bị đánh?), dùng lại ô ({hang},{cot}) "
                           f"- lần {so_lan_bi_ngat}/{SO_LAN_DUNG_LAI_KHI_BI_NGAT}")
                    time.sleep(GIAY_NGHI_TRUOC_KHI_DUNG_LAI)
                    game.dung_o(hang, cot)
                    ket_qua = cho_dich_chuyen(game, da_xong, chung["giay_cho_toi_da"], nen_dung)
                thanh_cong = ket_qua == "toi"
                if thanh_cong:
                    time.sleep(chung["giay_nghi_sau_khi_toi_map"])
            else:
                thanh_cong = cho(lambda: game.level() < level, chung["giay_cho_toi_da"], nen_dung)
                if thanh_cong:
                    trang_thai["so_lan_chuyen_sinh"] = trang_thai.get("so_lan_chuyen_sinh", 0) + 1
                    in_log(f"  {ten}: chuyển sinh xong (lần {trang_thai['so_lan_chuyen_sinh']} từ lúc mở auto)")
            if thanh_cong:
                trang_thai["so_lan_that_bai"] = 0
                return
            if nen_dung():
                return
            # Có thể game chỉ chậm hơn thời gian chờ: xem lại trước khi dùng ô kế tiếp, tránh dùng thừa.
            if viec_can_lam(cai_dat, game.level(), game.ten_map()) != viec:
                return
            in_log(f"  {ten}: ô ({hang},{cot}) không có tác dụng, thử ô tiếp theo")

    trang_thai["so_lan_that_bai"] = trang_thai.get("so_lan_that_bai", 0) + 1
    in_log(f"  {ten}: THẤT BẠI lần {trang_thai['so_lan_that_bai']}/{toi_da}")
    if trang_thai["so_lan_that_bai"] >= toi_da:
        trang_thai["mo_ta"] = "Tạm dừng: thất bại nhiều lần"
        in_log(f"  {ten}: tạm dừng auto để tránh dùng vật phẩm liên tục. Kiểm tra túi rồi bấm 'Chạy lại'.")
