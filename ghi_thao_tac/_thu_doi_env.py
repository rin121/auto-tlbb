"""Một lần đổi ô 6 trên GaoDẻLâu, gọi Clicked trong môi trường cửa sổ."""
import sys
import time

sys.path.insert(0, r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc")
OUT = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\ghi_thao_tac\_live.txt"


def ghi(*a):
    chu = " ".join(str(x) for x in a)
    print(chu)
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(chu + "\n")


def main():
    open(OUT, "w", encoding="utf-8").write("")
    import win32api
    import win32gui
    import win32process
    from bang_ma_viscii import giai_ma
    from cua_so_game import _la_cua_so_game_hop_le
    from lua_game import LuaGame, LoiLua
    import lua_game as lg
    from giao_acc_chinh import (
        MA_CUA_SO_DOI, NPC_TRAO_DOI, muc_phieu_knb, la_cong_thuc_phieu,
        ma_bam_o_doi, ma_xac_nhan_doi,
    )
    from game_api import Game
    from nhan_vat_moi import NhanDoTanThu
    from giao_dich import doc_tui

    lg.nap_dll = lambda pid: True
    _cu = win32api.PostMessage

    def _post(hwnd, msg, w=0, l=0):
        try:
            return win32gui.PostMessage(hwnd, msg, w, l)
        except Exception:
            return _cu(hwnd, msg, w, l)

    win32api.PostMessage = _post

    hwnds = []

    def cb(hwnd, _):
        if _la_cua_so_game_hop_le(hwnd):
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid and pid > 0:
                hwnds.append((hwnd, pid))
        return True

    win32gui.EnumWindows(cb, None)
    lua = None
    ten_nv = ""
    for hwnd, pid in hwnds:
        try:
            thu = LuaGame(hwnd)
            ten = giai_ma(thu.chay(
                'if not IsWindowShow("PlayerFrame") then return "" end return Player:GetName()',
                giay_cho=8))
            ghi("pid", pid, "ten", repr(ten))
            if "Dẻ" in ten or ("Gao" in ten and "Lâu" in ten):
                lua, ten_nv = thu, ten
                break
        except Exception as e:
            ghi("loi", pid, e)
    if lua is None:
        ghi("KHONG TIM THAY GaoDẻLâu")
        return

    def chay(ma, giay=8):
        return giai_ma(lua.chay(ma, giay_cho=giay))

    def dem():
        muc = {100: 0, 300: 0, 20000: 0, 30000: 0}
        for (_, _), (_, so, ten) in doc_tui(lua).items():
            m = muc_phieu_knb(ten)
            if m in (100, 300):
                muc[m] += so
            elif la_cong_thuc_phieu(ten, 20000):
                muc[20000] += so
            elif la_cong_thuc_phieu(ten, 30000):
                muc[30000] += so
        return muc

    if chay('return tostring(IsWindowShow("XiaoXiang_DuiHuanUI2"))') != "true":
        ghi("mo NPC")
        game = Game(lua.hwnd)
        nd = NhanDoTanThu(game, ten_nv, lambda m: ghi("npc", m), lambda: False, lambda _: None)
        nd._noi_chuyen(NPC_TRAO_DOI, (("Hợp Thành Vật Phẩm",),))
        time.sleep(1.2)
        try:
            chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
        except Exception:
            pass

    mo = "XiaoXiang_DuiHuanUI2"
    if chay(f'return tostring(IsWindowShow("{mo}"))') != "true":
        ghi("THAT BAI khong mo", chay(MA_CUA_SO_DOI))
        return

    truoc = dem()
    ghi("truoc", truoc)
    try:
        ghi("click", chay(ma_bam_o_doi(mo, 7)))
        time.sleep(0.5)
        ghi("ok", chay(ma_xac_nhan_doi(mo)))
        time.sleep(0.5)
    except LoiLua as e:
        ghi("LoiLua", e)
    sau = dem()
    ghi("sau", sau)
    ghi("delta 100", sau[100] - truoc[100], "300", sau[300] - truoc[300],
        "20K", sau[20000] - truoc[20000], "30K", sau[30000] - truoc[30000])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise
