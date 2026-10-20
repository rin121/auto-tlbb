"""
BƯỚC 2: Đọc thông tin nhân vật và túi đồ qua API Lua của game.

Dùng để kiểm tra kết nối với game, và xem mã loại (ma_loai) của vật phẩm ở từng ô
để điền vào cau_hinh.json.

Cách chạy:
    .venv\\Scripts\\python buoc2_doc_game.py
"""
from cua_so_game import tim_cua_so_game
from game_api import SO_O_MOI_HANG, SO_O_TUI_CO_BAN, Game


def main():
    danh_sach = tim_cua_so_game()
    if not danh_sach:
        print("Không tìm thấy cửa sổ game.")
        return

    for cua_so in danh_sach:
        game = Game(cua_so["hwnd"])
        x, y = game.toa_do()
        print(f"Nhân vật : {game.ten_nhan_vat()}")
        print(f"Level    : {game.level()}")
        print(f"Map      : {game.ten_map()} ({x}, {y})")
        print("Túi đồ (tab ĐC):")
        for chi_so in range(SO_O_TUI_CO_BAN):
            hang, cot = chi_so // SO_O_MOI_HANG + 1, chi_so % SO_O_MOI_HANG + 1
            vat_pham = game.vat_pham_o(hang, cot)
            if vat_pham:
                print(f"  hàng {hang}, cột {cot}: {vat_pham['ten']} x{vat_pham['so_luong']}"
                      f"  (ma_loai {vat_pham['ma_loai']})")
        print()


if __name__ == "__main__":
    main()
