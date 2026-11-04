"""Thử đổi phiếu trên GaoDẻLâu theo ô cố định 6/7 (ghi tay). Chỉ vài lần, không quét."""
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
        MA_BAM_O_DOI, MA_XAC_NHAN_DOI, MA_CUA_SO_DOI, NPC_TRAO_DOI,
        O_PHIEU_KNB_20K, O_PHIEU_KNB_30K, muc_phieu_knb, la_cong_thuc_phieu,
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

    def dem_phieu():
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

    ghi("===", ten_nv, "===")
    truoc = dem_phieu()
    ghi("truoc", truoc)

    mo = ""
    if chay('return tostring(IsWindowShow("XiaoXiang_DuiHuanUI2"))') == "true":
        mo = "XiaoXiang_DuiHuanUI2"
        ghi("cua so da mo")
    else:
        ghi("mo NPC Trao Doi...")
        try:
            game = Game(lua.hwnd)
            nd = NhanDoTanThu(game, ten_nv, lambda m: ghi("npc", m), lambda: False, lambda _: None)
            nd._noi_chuyen(NPC_TRAO_DOI, (("Hợp Thành Vật Phẩm",),))
            time.sleep(1.2)
            try:
                chay('if IsWindowShow("Quest") then CloseWindow("Quest", true) end')
            except Exception:
                pass
            mo = lua.chay(MA_CUA_SO_DOI, giay_cho=8).decode("utf-8", "replace").strip()
        except Exception as e:
            ghi("mo_loi", type(e).__name__, e)
            return

    ghi("mo=", repr(mo))
    if not mo:
        ghi("THAT BAI: khong mo duoc cua so doi")
        return
    if chay(f'return tostring(IsWindowShow("{mo}"))') != "true":
        ghi("THAT BAI: cua so khong show", mo)
        return

    ok_tong = 0
    for o, nhan in ((O_PHIEU_KNB_20K, "20K"), (O_PHIEU_KNB_30K, "30K")):
        ghi("--- thu o", o, nhan, "---")
        doi_o = 0
        for lan in range(3):
            truoc_lan = dem_phieu()
            if truoc_lan[100] <= 0 and truoc_lan[300] <= 0:
                ghi("het phieu nho, dung")
                break
            try:
                k1 = lua.chay(MA_BAM_O_DOI.replace("{mo}", mo).replace("{i}", str(o)), giay_cho=8)
                ghi("Clicked", o, "->", k1)
                time.sleep(0.3)
                k2 = lua.chay(MA_XAC_NHAN_DOI.replace("{mo}", mo), giay_cho=8)
                ghi("OK", "->", k2)
                time.sleep(0.45)
            except LoiLua as e:
                ghi("LoiLua", e)
                break
            sau_lan = dem_phieu()
            giam = (sau_lan[100] < truoc_lan[100]) or (sau_lan[300] < truoc_lan[300])
            ghi("sau_lan", sau_lan, "giam=", giam)
            if giam:
                doi_o += 1
                ok_tong += 1
            else:
                ghi("khong giam phieu nho — dung o nay")
                break
        ghi("o", o, "doi_duoc", doi_o, "lan")

    sau = dem_phieu()
    ghi("=== KET QUA ===")
    ghi("truoc", truoc)
    ghi("sau  ", sau)
    ghi("delta 100", sau[100] - truoc[100],
        "300", sau[300] - truoc[300],
        "20K", sau[20000] - truoc[20000],
        "30K", sau[30000] - truoc[30000])
    if ok_tong > 0:
        ghi("THANH CONG: doi duoc", ok_tong, "lan")
    else:
        ghi("THAT BAI: khong doi duoc lan nao")

    try:
        chay(f'if IsWindowShow("{mo}") then CloseWindow("{mo}", true) end')
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        raise
