"""Vòng Telegram + HTTP 127.0.0.1. Chạy: python -m bot_quan_ly (thư mục AutoHoc)."""
import json
import logging
import os
import queue
import sys
import threading
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from bot_quan_ly.http_may import nhan_bao_cao
from bot_quan_ly.kho_may import KhoMay
from bot_quan_ly.lenh import cat_tin, phan_lenh, tra_loi

THU_MUC = os.path.dirname(os.path.abspath(__file__))
DUONG_DAN_ENV = os.path.join(THU_MUC, ".env")
DUONG_DAN_MAY = os.path.join(THU_MUC, "data", "may.json")
DUONG_DAN_LOG = os.path.join(THU_MUC, "bot_quan_ly.log")

log = logging.getLogger("bot_quan_ly")


def _loi_mang(loi):
    chu = str(loi)
    if "api.telegram.org" in chu or "bot" in chu and ":" in chu:
        return "lỗi mạng Telegram"
    return chu


def _cau_hinh_log():
    os.makedirs(THU_MUC, exist_ok=True)
    handlers = [logging.FileHandler(DUONG_DAN_LOG, encoding="utf-8")]
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=handlers,
    )


def _doc_dong_env(duong_dan):
    dong_goc = []
    gia = {}
    with open(duong_dan, encoding="utf-8") as f:
        for dong in f:
            dong_goc.append(dong.rstrip("\n"))
            s = dong.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            khoa, gia_tri = s.split("=", 1)
            gia[khoa.strip()] = gia_tri.strip().strip('"').strip("'")
    return dong_goc, gia


def _ghi_chat_id_env(duong_dan, chat_id):
    dong_goc, _ = _doc_dong_env(duong_dan)
    co = False
    out = []
    for dong in dong_goc:
        if dong.strip().startswith("TELEGRAM_CHAT_ID="):
            out.append(f"TELEGRAM_CHAT_ID={chat_id}")
            co = True
        else:
            out.append(dong)
    if not co:
        out.append(f"TELEGRAM_CHAT_ID={chat_id}")
    with open(duong_dan, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")


def tim_chat_id_tu_telegram(token):
    """Tin /start gần nhất tới bot → chat.id (chỉ chat riêng)."""
    try:
        cap_nhat = _goi_telegram(token, "getUpdates", {}, timeout=25).get("result") or []
    except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError):
        return None
    for tin in reversed(cap_nhat):
        chat = (tin.get("message") or {}).get("chat") or {}
        if str(chat.get("type")) == "private" and chat.get("id") is not None:
            return str(chat["id"])
    return None


def doc_env(duong_dan=DUONG_DAN_ENV):
    if not os.path.isfile(duong_dan):
        raise SystemExit(f"Thiếu {duong_dan} — copy .env.example thành .env rồi điền token và MA_KET_NOI.")
    _, gia = _doc_dong_env(duong_dan)
    token = gia.get("TELEGRAM_BOT_TOKEN", "")
    chat = gia.get("TELEGRAM_CHAT_ID", "")
    ma = gia.get("MA_KET_NOI", "")
    if token and not chat:
        chat = tim_chat_id_tu_telegram(token)
        if chat:
            _ghi_chat_id_env(duong_dan, chat)
            log.info("Đã lấy TELEGRAM_CHAT_ID=%s từ Telegram (ghi .env).", chat)
    if not token or not chat or not ma:
        raise SystemExit(
            "Thiếu cấu hình trong .env.\n"
            "- TELEGRAM_BOT_TOKEN và MA_KET_NOI: điền tay (một lần).\n"
            "- TELEGRAM_CHAT_ID: nhắn /start cho bot trên Telegram rồi chạy lại "
            "(bot tự lấy chat_id, không cần getUpdates trên trình duyệt)."
        )
    try:
        cong = int(gia.get("CONG") or 8787)
        giay_im = int(gia.get("GIAY_IM") or 90)
    except ValueError as loi:
        raise SystemExit(f"CONG hoặc GIAY_IM không phải số: {loi}") from loi
    return {
        "token": token,
        "chat_id": str(chat),
        "ma": ma,
        "cong": cong,
        "giay_im": max(15, giay_im),
    }


def _goi_telegram(token, phuong_thuc, payload, timeout):
    url = f"https://api.telegram.org/bot{token}/{phuong_thuc}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        du_lieu = json.loads(resp.read().decode("utf-8"))
    if not du_lieu.get("ok"):
        raise RuntimeError(du_lieu.get("description") or phuong_thuc)
    return du_lieu


def gui_telegram(token, chat_id, text):
    for doan in cat_tin(text):
        _goi_telegram(token, "sendMessage", {"chat_id": chat_id, "text": doan}, timeout=20)


def lay_cap_nhat(token, offset):
    payload = {"timeout": 15, "allowed_updates": ["message"]}
    if offset is not None:
        payload["offset"] = offset
    du_lieu = _goi_telegram(token, "getUpdates", payload, timeout=30)
    return du_lieu.get("result") or []


def tao_may_chu(kho, ma, cong, hang_tin):
    class XuLy(BaseHTTPRequestHandler):
        def do_POST(self):
            duong = self.path.split("?", 1)[0]
            if duong != "/bao-cao":
                self.send_response(404)
                self.end_headers()
                return
            try:
                n = int(self.headers.get("Content-Length", "0") or 0)
            except ValueError:
                n = 0
            if n < 0 or n > 200_000:
                self.send_response(413)
                self.end_headers()
                return
            body = self.rfile.read(n) if n else b""
            status, tin = nhan_bao_cao(self.headers.get("X-Ma-Ket-Noi", ""), body, ma, kho)
            for dong in tin:
                hang_tin.put(dong)
            self.send_response(status)
            self.end_headers()

        def log_message(self, dinh_dang, *tham_so):
            log.info("%s - %s", self.address_string(), dinh_dang % tham_so)

    return ThreadingHTTPServer(("127.0.0.1", cong), XuLy)


def _day_hang(hang, token, chat_id):
    while True:
        try:
            dong = hang.get_nowait()
        except queue.Empty:
            return
        try:
            gui_telegram(token, chat_id, dong)
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as loi:
            log.error("Không gửi được thông báo: %s", _loi_mang(loi))


def _vong_im(kho, hang, dung):
    while not dung.wait(15):
        for dong in kho.quet_im():
            hang.put(dong)


def _xu_ly_tin(kho, token, chat_id, cap_nhat):
    offset = None
    for tin in cap_nhat:
        offset = tin["update_id"] + 1
        msg = tin.get("message") or {}
        chat = str((msg.get("chat") or {}).get("id", ""))
        if chat != chat_id:
            continue
        lenh, ten = phan_lenh(msg.get("text") or "")
        if not lenh:
            continue
        try:
            gui_telegram(token, chat_id, tra_loi(kho, lenh, ten))
        except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as loi:
            log.error("Không trả lời được lệnh: %s", _loi_mang(loi))
    return offset


def main():
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            stream.reconfigure(encoding="utf-8", errors="replace")
    _cau_hinh_log()
    cfg = doc_env()
    kho = KhoMay(DUONG_DAN_MAY, cfg["giay_im"])
    hang = queue.Queue()
    try:
        may_chu = tao_may_chu(kho, cfg["ma"], cfg["cong"], hang)
    except OSError as loi:
        raise SystemExit(f"Không mở được cổng {cfg['cong']} trên 127.0.0.1: {loi}") from loi
    threading.Thread(target=may_chu.serve_forever, name="http-bao-cao", daemon=True).start()
    dung = threading.Event()
    threading.Thread(target=_vong_im, args=(kho, hang, dung), name="quet-im", daemon=True).start()
    log.info("Nghe báo cáo tại http://127.0.0.1:%s/bao-cao , %d máy đã lưu", cfg["cong"], len(kho.danh_sach()))
    offset = None
    try:
        while True:
            _day_hang(hang, cfg["token"], cfg["chat_id"])
            try:
                cap_nhat = lay_cap_nhat(cfg["token"], offset)
            except (urllib.error.URLError, TimeoutError, RuntimeError, json.JSONDecodeError) as loi:
                log.error("getUpdates lỗi: %s", _loi_mang(loi))
                dung.wait(5)
                continue
            moi = _xu_ly_tin(kho, cfg["token"], cfg["chat_id"], cap_nhat)
            if moi is not None:
                offset = moi
    except KeyboardInterrupt:
        log.info("Dừng bot quản lý")
    finally:
        dung.set()
        may_chu.shutdown()


if __name__ == "__main__":
    main()
