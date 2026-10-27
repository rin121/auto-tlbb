# AutoHoc

Auto client Thiên Long (chuyển sinh, phó bản, xoay vòng tài khoản, …). Thư mục chạy thật thường là `dong_goi\AutoHoc\` (exe + `cau_hinh.json`, `tai_khoan.json`, `dll\`).

Mọi lệnh dưới đây chạy trong PowerShell, **thư mục làm việc** = `AutoHoc` (thư mục có `.venv` và `giao_dien.py`).

## Chuẩn bị (lần đầu)

**64-bit** (máy dev / Windows x64):

```powershell
cd d:\Games\ThienLongCityCSClientFull2026\AutoHoc
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Cài thêm PyInstaller khi build exe: `.venv\Scripts\pip install pyinstaller`.

## Chạy từ mã nguồn (dev)

```powershell
.venv\Scripts\python.exe giao_dien.py
```

## Biên dịch DLL (32-bit, cho Game.exe)

Đóng game đang dùng DLL cũ nếu bị khóa file. Script tự đổi tên bản cũ rồi build bản mới.

```powershell
dll\bien_dich.bat
```

Chỉ một DLL:

```powershell
dll\bien_dich.bat autohoc_nhat
dll\bien_dich.bat autohoc_lua
```

## Build bản chính `AutoHoc.exe` (64-bit, Windows x64)

```powershell
powershell -ExecutionPolicy Bypass -File dong_goi\build_va_deploy.ps1
```

Hoặc chỉ PyInstaller:

```powershell
powershell -ExecutionPolicy Bypass -File dong_goi\build_exe.ps1 -Python .venv\Scripts\python.exe -DistPath dong_goi\build_moi -WorkPath dong_goi\build_tam -Spec dong_goi\AutoHoc.spec
```

Sau deploy: `dong_goi\AutoHoc\AutoHoc.exe` (Windows 10+).

**Windows 7 SP1 x64:** bản riêng ở `dong_goi\AutoHoc\win7\`. Captcha không chạy onnx trong exe (onnx đóng gói PyInstaller không load được trên Win7) mà qua tiến trình Python riêng trong `win7\ocr_py\` (Python 3.8 embeddable, tự chứa, không cần cài Python trên máy chơi).

Cấu trúc bắt buộc trên máy chơi:

```
win7\
  AutoHoc.exe
  ocr_py\          <- python.exe, giai_ocr.py, Lib\site-packages (ddddocr 1.4.11 + onnxruntime 1.6)
  dll\
  tools\
```

**Chỉ copy mỗi `AutoHoc.exe` thì không giải được mã kiểm tra** (log: «thiếu ocr_py\python.exe…», auto nhập mã cố định). Copy cả thư mục `dong_goi\AutoHoc\win7\` sang máy Win7 (khi cập nhật: xóa `ocr_py\` cũ trước rồi copy, tránh bị bỏ qua file trùng tên), giữ `cau_hinh.json`, `tai_khoan.json`, `license.dat` cạnh exe.

Build: tạo `.venv_win7` một lần (Python 3.8 amd64 → `py -3.8-64 -m venv .venv_win7` → `pip install -r requirements-win7-amd64.txt`), sau đó `build_va_deploy.ps1` tự build exe Win7, tạo lại `ocr_py` (`dong_goi\tao_ocr_py_win7.ps1`, gói lấy theo `requirements-ocr-win7.txt`), ghi thẳng vào `dong_goi\AutoHoc\win7\` (nén zip thủ công nếu cần: `dong_goi\tao_zip_win7.ps1`). Chỉ bản Win7: `build_va_deploy.ps1 -ChiWin7`.

Máy Win7 cần SP1 + KB2999226 (Universal CRT). `ocr_py` tự kèm runtime VC++ **14.29** (VS2019, từ wheel `msvc-runtime`) — không lấy `msvcp140.dll` từ System32 máy build vì bản 14.3x+ gọi API Win8 (`GetSystemTimePreciseAsFileTime`) → onnxruntime báo `get_all_providers` / `procedure not found` trên Win7. Nếu đã có `ocr_py` mà log báo «ocr_py dừng đột ngột: …», thử chạy `win7\ocr_py\python.exe -c "import onnxruntime"` để xem lỗi DLL.

## Deploy vào thư mục đang chạy

Sau khi build, deploy vào `dong_goi\AutoHoc\`. **Nếu `AutoHoc.exe` đang mở**, script đổi tên bản đang dùng thành `AutoHoc_cu.exe` rồi copy bản mới (không cần tắt trước). Mở lại `AutoHoc.exe` sau deploy để dùng bản mới.

```powershell
powershell -ExecutionPolicy Bypass -File dong_goi\deploy_autohoc.ps1
```

**Chỉ mở một** cửa sổ AutoHoc khi chạy auto.

Nếu `Copy-Item` DLL báo file đang bị process giữ: tắt game/auto đang dùng DLL, hoặc copy sau khi thoát AutoHoc; exe mới vẫn dùng được nếu hash exe đã đổi.

## Bản dùng thử (legacy, không dùng khi phân phối qua license)

Phân phối chính: bản `AutoHoc.exe` + file `license.dat` (tab **Kích hoạt**). Chỉ build zip hết hạn khi cần test cũ:

```powershell
powershell -ExecutionPolicy Bypass -File dong_goi\build_dung_thu.ps1 -SoNgay 3
# hoặc kèm deploy: build_va_deploy.ps1 -DungThu -SoNgay 3
```

## Ghi chú

- Cấu hình người dùng: `dong_goi\AutoHoc\cau_hinh.json`, `dong_goi\AutoHoc\tai_khoan.json` (không ghi đè khi build).
- Log: `dong_goi\AutoHoc\nhat_ky_auto.log`.
- Mật khẩu tài khoản lưu trong `tai_khoan.json` — không chia sẻ file này.


- Cấp license (GUI: HWID + số ngày, `0` = không giới hạn):
  `cd AutoHoc` → `.\.venv\Scripts\python.exe dong_goi\tao_license.py`
  Dòng lệnh: `dong_goi\tao_license.py <HWID> "ghi chú" <số_ngày> [license.dat]`


  ## Build:
  - powershell -ExecutionPolicy Bypass -File "d:\Games\ThienLongCityCSClientFull2026\AutoHoc\dong_goi\build_va_deploy.ps1"


# Win10/11
powershell -ExecutionPolicy Bypass -File ".\dong_goi\build_va_deploy.ps1" -KhongWin7

# Win7
powershell -ExecutionPolicy Bypass -File ".\dong_goi\build_va_deploy.ps1" -ChiWin7

# Cả hai (cần .venv + .venv_win7)
powershell -ExecutionPolicy Bypass -File ".\dong_goi\build_va_deploy.ps1"
