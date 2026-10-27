"""Hỗ trợ UI AutoHoc cho Proxy Broker (file JSON + subprocess)."""
import glob
import json
import os
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import psutil

from thu_muc import THU_MUC_APP

DUONG_DAN_CONFIG = os.path.join(THU_MUC_APP, "proxy_broker.json")
DUONG_DAN_STATE = os.path.join(THU_MUC_APP, "proxy_broker_state.json")
DUONG_DAN_LOG = os.path.join(THU_MUC_APP, "proxy_broker.log")
DUONG_DAN_PID = os.path.join(THU_MUC_APP, "proxy_broker.pid")
TEN_LOG_BROKER = "proxy_broker.log"
MAU_CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ProxyBroker",
                          "mau_proxy_broker.json")


def dam_bao_log_broker():
    """Log của Proxy Broker (không phải Proxifier) — luôn cạnh AutoHoc.exe."""
    os.makedirs(THU_MUC_APP, exist_ok=True)
    if not os.path.isfile(DUONG_DAN_LOG):
        with open(DUONG_DAN_LOG, "a", encoding="utf-8"):
            pass
    return DUONG_DAN_LOG


def mo_ta_log_broker():
    return os.path.join(THU_MUC_APP, TEN_LOG_BROKER)


def goc_repo():
    if getattr(sys, "frozen", False):
        return THU_MUC_APP
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _thu_muc_co_proxy_broker(thu_muc):
    return os.path.isfile(os.path.join(thu_muc, "ProxyBroker", "__main__.py"))


def _goi_pythonpath_proxy_broker():
    """Thư mục đặt trên PYTHONPATH (cha của package ProxyBroker)."""
    if _thu_muc_co_proxy_broker(THU_MUC_APP):
        return THU_MUC_APP
    long = os.path.join(THU_MUC_APP, "ProxyBroker")
    if os.path.isfile(os.path.join(long, "ProxyBroker", "__main__.py")):
        return long
    return None


def _nguon_proxy_broker_san_co():
    """Các thư mục nguồn có thể copy sang THU_MUC_APP/ProxyBroker."""
    ds = []
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", "") or ""
        if meipass:
            ds.append(os.path.join(meipass, "ProxyBroker"))
    ds.extend([
        os.path.normpath(os.path.join(THU_MUC_APP, "ProxyBroker")),
        os.path.normpath(os.path.join(THU_MUC_APP, "..", "..", "..", "ProxyBroker")),
        os.path.normpath(os.path.join(THU_MUC_APP, "..", "..", "ProxyBroker")),
        os.path.normpath(os.path.join(goc_repo(), "ProxyBroker")),
        os.path.normpath(os.path.join(goc_repo(), "..", "ProxyBroker")),
    ])
    ket = []
    for duong in ds:
        if duong in ket:
            continue
        if os.path.isfile(os.path.join(duong, "__main__.py")):
            ket.append(duong)
    return ket


def dam_bao_proxy_broker_tai_app():
    co = _goi_pythonpath_proxy_broker()
    if co:
        return co
    dich = os.path.join(THU_MUC_APP, "ProxyBroker")
    for nguon in _nguon_proxy_broker_san_co():
        if os.path.normpath(nguon) == os.path.normpath(dich):
            continue
        try:
            if os.path.isdir(dich):
                shutil.rmtree(dich, ignore_errors=True)
            shutil.copytree(nguon, dich)
            co = _goi_pythonpath_proxy_broker()
            if co:
                return co
        except OSError:
            continue
    return _goi_pythonpath_proxy_broker()


def tim_goc_module():
    """Thư mục cha của package ProxyBroker (để PYTHONPATH / cwd)."""
    co = dam_bao_proxy_broker_tai_app()
    if co:
        return co
    if not getattr(sys, "frozen", False):
        for thu_muc in (goc_repo(), os.path.normpath(os.path.join(THU_MUC_APP, "..", ".."))):
            if _thu_muc_co_proxy_broker(thu_muc):
                return thu_muc
    return None


def phat_hien_tu_exe(duong_exe):
    """
    Từ Proxifier.exe suy ra profile .ppx và log Proxifier (Portable PE / cài đặt thường).
    Trả về dict profile_ppx, log_file (chỉ key tìm được).
    """
    duong_exe = (duong_exe or "").strip().replace("/", os.sep)
    if not (duong_exe and os.path.isfile(duong_exe)):
        return {}
    goc = os.path.dirname(os.path.normpath(duong_exe))
    ket = {}
    uu_tien_ppx = [
        os.path.join(goc, "Profiles", "Default.ppx"),
        os.path.join(goc, "Profile", "Default.ppx"),
        os.path.join(goc, "Default.ppx"),
    ]
    for duong in uu_tien_ppx:
        if os.path.isfile(duong):
            ket["profile_ppx"] = duong
            break
    if "profile_ppx" not in ket:
        for thu_muc_ten in ("Profiles", "Profile"):
            thu_muc = os.path.join(goc, thu_muc_ten)
            if not os.path.isdir(thu_muc):
                continue
            ds = sorted(glob.glob(os.path.join(thu_muc, "*.ppx")))
            if ds:
                ket["profile_ppx"] = ds[0]
                break
    ppx = ket.get("profile_ppx")
    if ppx:
        try:
            root = ET.parse(ppx).getroot()
            for el in root.iter():
                tag = (el.tag or "").lower()
                if tag in ("logfile", "file") and el.text and el.text.strip():
                    txt = el.text.strip()
                    if "log" in tag or txt.lower().endswith((".txt", ".log")):
                        if os.path.isabs(txt) and os.path.isfile(txt):
                            ket["log_file"] = txt
                        elif not os.path.isabs(txt):
                            cand = os.path.normpath(os.path.join(goc, txt))
                            if os.path.isfile(cand):
                                ket["log_file"] = cand
        except (OSError, ET.ParseError):
            pass
    if "log_file" not in ket:
        for ten in ("Log.txt", "Proxifier.log", "log.txt"):
            cand = os.path.join(goc, ten)
            if os.path.isfile(cand):
                ket["log_file"] = cand
                break
    if "log_file" not in ket:
        for thu_muc_ten in ("Logs", "Log"):
            thu_muc = os.path.join(goc, thu_muc_ten)
            if not os.path.isdir(thu_muc):
                continue
            ds = glob.glob(os.path.join(thu_muc, "*.txt")) + glob.glob(os.path.join(thu_muc, "*.log"))
            if ds:
                ds.sort(key=lambda p: os.path.getmtime(p), reverse=True)
                ket["log_file"] = ds[0]
                break
    return ket


def ap_dung_phat_hien_len_config(duong_exe, cfg=None):
    """Gộp phát hiện vào dict config (không ghi đè ppx/log đã có nếu vẫn tồn tại file)."""
    cfg = dict(cfg or doc_config())
    ph = phat_hien_tu_exe(duong_exe)
    if ph.get("profile_ppx"):
        if not ((cfg.get("profile_ppx") or "").strip() and os.path.isfile((cfg.get("profile_ppx") or "").strip())):
            cfg["profile_ppx"] = ph["profile_ppx"]
    if ph.get("log_file"):
        if not ((cfg.get("log_file") or "").strip() and os.path.isfile((cfg.get("log_file") or "").strip())):
            cfg["log_file"] = ph["log_file"]
    if duong_exe:
        cfg["proxifier_exe"] = duong_exe
    return cfg


def tim_lenh_python():
    """
    Không dùng AutoHoc.exe làm Python (sẽ mở cửa sổ AutoHoc thứ hai).
    Trả về (argv_prefix, mo_ta) hoặc raise RuntimeError.
    """
    ocr_py = os.path.join(THU_MUC_APP, "ocr_py", "python.exe")
    if os.path.isfile(ocr_py):
        return [ocr_py], f"ocr_py ({ocr_py})"
    danh_sach_venv = [
        os.path.join(THU_MUC_APP, "..", ".venv", "Scripts", "python.exe"),
        os.path.join(THU_MUC_APP, "..", ".venv_win7", "Scripts", "python.exe"),
        os.path.join(THU_MUC_APP, "..", "..", ".venv", "Scripts", "python.exe"),
        os.path.join(THU_MUC_APP, "..", "..", "..", "AutoHoc", ".venv", "Scripts", "python.exe"),
        os.path.join(goc_repo(), "AutoHoc", ".venv", "Scripts", "python.exe"),
    ]
    for duong in danh_sach_venv:
        duong = os.path.normpath(duong)
        if os.path.isfile(duong):
            return [duong], duong
    py = shutil.which("py")
    if py:
        return [py, "-3"], "py -3"
    python = shutil.which("python") or shutil.which("python3")
    if python:
        return [python], python
    if not getattr(sys, "frozen", False) and sys.executable:
        return [sys.executable], sys.executable
    raise RuntimeError(
        "Không tìm thấy Python để chạy Proxy Broker.\n"
        "Bản Win7: cần thư mục ocr_py\\ (build deploy) hoặc cài Python 3.\n"
        "Dev: AutoHoc\\.venv hoặc chạy thủ công: py -3 -m ProxyBroker --daemon\n"
        f"(cần thư mục ProxyBroker cạnh {THU_MUC_APP})")


def dam_bao_config():
    if os.path.isfile(DUONG_DAN_CONFIG):
        return
    os.makedirs(os.path.dirname(DUONG_DAN_CONFIG), exist_ok=True)
    if os.path.isfile(MAU_CONFIG):
        with open(MAU_CONFIG, encoding="utf-8") as f:
            du_lieu = json.load(f)
    else:
        du_lieu = {}
    with open(DUONG_DAN_CONFIG, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=2)


def doc_config():
    dam_bao_config()
    with open(DUONG_DAN_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def ghi_config(du_lieu):
    os.makedirs(os.path.dirname(DUONG_DAN_CONFIG), exist_ok=True)
    with open(DUONG_DAN_CONFIG, "w", encoding="utf-8") as f:
        json.dump(du_lieu, f, ensure_ascii=False, indent=2)


def doc_state():
    if not os.path.isfile(DUONG_DAN_STATE):
        return {}
    try:
        with open(DUONG_DAN_STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def ghi_state_phan(st):
    """Ghi merge vào proxy_broker_state.json (AutoHoc yêu cầu failover)."""
    os.makedirs(THU_MUC_APP, exist_ok=True)
    hien = doc_state()
    hien.update(st)
    with open(DUONG_DAN_STATE, "w", encoding="utf-8") as f:
        json.dump(hien, f, ensure_ascii=False, indent=2)


def yeu_cau_failover(ly_do=""):
    """AutoHoc / login: broker daemon sẽ đổi proxy (proxy chết hoặc IP đã dùng máy khác)."""
    ghi_state_phan({"yeu_cau_failover_luc": time.time(),
                    "yeu_cau_failover_ly_do": (ly_do or "login lỗi mạng")[:240]})


def doc_log_cuoi(so_dong=8):
    if not os.path.isfile(DUONG_DAN_LOG):
        return ""
    try:
        with open(DUONG_DAN_LOG, encoding="utf-8", errors="replace") as f:
            dong = f.readlines()
        return "".join(dong[-so_dong:]).strip()
    except OSError:
        return ""


def _doc_pid():
    if not os.path.isfile(DUONG_DAN_PID):
        return None
    try:
        with open(DUONG_DAN_PID, encoding="utf-8") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _ghi_pid(pid):
    os.makedirs(THU_MUC_APP, exist_ok=True)
    with open(DUONG_DAN_PID, "w", encoding="utf-8") as f:
        f.write(str(int(pid)))


def _xoa_pid():
    try:
        os.remove(DUONG_DAN_PID)
    except OSError:
        pass


def broker_dang_chay(proc=None):
    """(đang_chay, pid). Nhận diện qua subprocess UI, file .pid hoặc nhịp tim state."""
    if proc is not None and proc.poll() is None:
        return True, proc.pid
    pid = _doc_pid()
    if pid and psutil.pid_exists(pid):
        return True, pid
    st = doc_state()
    nhip = st.get("broker_nhip_tim")
    if nhip:
        try:
            if time.time() - float(nhip) < 120:
                return True, st.get("broker_pid") or pid
        except (TypeError, ValueError):
            pass
    return False, None


def mo_ta_hien_thi(proc=None):
    """Trả về (dong_trang_thai, mau, dang_chay)."""
    chay, pid = broker_dang_chay(proc)
    st = doc_state()
    health = st.get("health") or "—"
    if chay:
        tieu_de = f"● Broker ĐANG CHẠY (PID {pid or '?'})"
        mau = "#0a7a0a" if health == "healthy" else "#b8860b"
    else:
        tieu_de = "○ Broker không chạy"
        mau = "#888888"
    chi_tiet = mo_ta_state()
    return f"{tieu_de}\n{chi_tiet}", mau, chay


def mo_ta_state():
    st = doc_state()
    px = st.get("proxy_active") or {}
    gt = st.get("game_target") or {}
    if px:
        ms = px.get("latency_ms")
        tre = f" ~{ms}ms" if ms is not None else ""
        dong_px = f"{px.get('host', '—')}:{px.get('port', '—')}{tre}"
    else:
        dong_px = "—"
    dong_gt = f"{gt.get('host', '—')}:{gt.get('port', '—')}" if gt else "—"
    tb = (st.get("thong_bao") or "").strip()
    if len(tb) > 80:
        tb = tb[:77] + "..."
    phu = f" | {tb}" if tb else ""
    return (f"Health: {st.get('health', '—')} | Proxy: {dong_px} | Game: {dong_gt} | "
            f"Game.exe: {st.get('acc_online', 0)}/4 | "
            f"Login thêm: {'có' if st.get('cho_phep_login_them') else 'không'}{phu}")


def _argv_chay_broker(prefix, goc):
    """
    python -m ProxyBroker — ocr_py (embed) thường bỏ qua PYTHONPATH;
    chèn thư mục cha ProxyBroker vào sys.path trước khi run_module.
    """
    code = (f"import sys, runpy; sys.path.insert(0, {repr(goc)}); sys.argv=['ProxyBroker','--daemon']; "
            "runpy.run_module('ProxyBroker', run_name='__main__', alter_sys=True)")
    return prefix + ["-c", code]


def chay_broker_daemon():
    dam_bao_log_broker()
    goc = tim_goc_module()
    if not (goc and _thu_muc_co_proxy_broker(goc)):
        raise RuntimeError(
            f"Không thấy package ProxyBroker cạnh AutoHoc ({THU_MUC_APP}).\n"
            "Chạy lại build/deploy (cần thư mục ProxyBroker\\ cùng chỗ AutoHoc.exe) hoặc cập nhật bản AutoHoc mới.")
    prefix, mo_ta = tim_lenh_python()
    env = os.environ.copy()
    env["AUTOHOC_APP_DIR"] = THU_MUC_APP
    env["PYTHONPATH"] = goc + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUTF8"] = "1"
    os.makedirs(os.path.dirname(DUONG_DAN_LOG), exist_ok=True)
    log_f = open(DUONG_DAN_LOG, "a", encoding="utf-8")
    log_f.write(f"\n--- Khởi chạy broker {time.strftime('%Y-%m-%d %H:%M:%S')} | {mo_ta} | cwd={goc} ---\n")
    log_f.flush()
    proc = subprocess.Popen(
        _argv_chay_broker(prefix, goc),
        cwd=goc,
        env=env,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
    _ghi_pid(proc.pid)
    return proc


def dung_broker(proc=None):
    """Dừng process broker nếu biết pid."""
    da_dung = False
    if proc is not None and proc.poll() is None:
        proc.terminate()
        da_dung = True
    pid = _doc_pid()
    if pid:
        try:
            psutil.Process(pid).terminate()
            da_dung = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    _xoa_pid()
    return da_dung


def kiem_tra_vua_chay(proc, cho_giay=2.0):
    """Trả về (con_chay, thong_bao_loi)."""
    time.sleep(cho_giay)
    if proc.poll() is None:
        return True, ""
    log = doc_log_cuoi(15)
    return False, log or f"Broker thoát ngay (mã {proc.returncode}). Xem {DUONG_DAN_LOG}"
