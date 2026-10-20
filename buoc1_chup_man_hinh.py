"""
BƯỚC 1: Tìm các cửa sổ game đang mở và chụp ảnh từng cửa sổ.

Cách chạy (mở game lên trước, vào nhân vật, để cửa sổ game hiện trên màn hình):
    .venv\\Scripts\\python buoc1_chup_man_hinh.py

Ảnh sẽ được lưu vào thư mục anh_chup\\
"""
import os

from PIL import ImageGrab

from cua_so_game import bat_dpi_awareness, dua_cua_so_len_truoc, tim_cua_so_game, vung_client

THU_MUC_ANH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "anh_chup")


def chup_cua_so(hwnd):
    x, y, rong, cao = vung_client(hwnd)
    return ImageGrab.grab(bbox=(x, y, x + rong, y + cao), all_screens=True)


def main():
    bat_dpi_awareness()

    danh_sach = tim_cua_so_game()
    if not danh_sach:
        print("Không tìm thấy cửa sổ Game.exe nào. Hãy mở game và vào nhân vật trước.")
        return

    print(f"Tìm thấy {len(danh_sach)} cửa sổ game:")
    os.makedirs(THU_MUC_ANH, exist_ok=True)

    for thu_tu, cua_so in enumerate(danh_sach, start=1):
        hwnd = cua_so["hwnd"]
        dua_cua_so_len_truoc(hwnd)
        x, y, rong, cao = vung_client(hwnd)

        anh = chup_cua_so(hwnd)
        ten_file = os.path.join(THU_MUC_ANH, f"game_{thu_tu}_pid{cua_so['pid']}.png")
        anh.save(ten_file)

        print(f"  [{thu_tu}] hwnd={hwnd}  pid={cua_so['pid']}  tiêu đề='{cua_so['tieu_de']}'")
        print(f"      vị trí=({x}, {y})  kích thước={rong}x{cao}")
        print(f"      đã lưu ảnh: {ten_file}")


if __name__ == "__main__":
    main()
