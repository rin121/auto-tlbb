@echo off
chcp 65001 >nul
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
    echo Chưa có .venv trong thư mục AutoHoc — cài Python venv theo readme.md
    pause
    exit /b 1
)
if not exist "bot_quan_ly\.env" (
    echo Thiếu bot_quan_ly\.env — copy .env.example và điền TELEGRAM_BOT_TOKEN + MA_KET_NOI
    pause
    exit /b 1
)
echo Bot quản lý — giữ cửa sổ này mở. Tắt cửa sổ = ngừng nhận lệnh / báo cáo.
echo Nhắn /help cho bot trên Telegram khi đã chạy.
".venv\Scripts\python.exe" -m bot_quan_ly
pause
