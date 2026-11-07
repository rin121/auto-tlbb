# Sau khi nhắn /start cho bot trên Telegram, chạy script này (PowerShell trong bot_quan_ly).
$envPath = Join-Path $PSScriptRoot ".env"
if (-not (Test-Path $envPath)) { throw "Thiếu .env" }
$token = $null
foreach ($line in Get-Content $envPath -Encoding UTF8) {
    if ($line -match '^\s*TELEGRAM_BOT_TOKEN=(.+)$') {
        $token = $Matches[1].Trim()
        break
    }
}
if (-not $token) { throw "Thiếu TELEGRAM_BOT_TOKEN trong .env" }
$r = Invoke-RestMethod -Uri "https://api.telegram.org/bot$token/getUpdates"
if (-not $r.result.Count) {
    Write-Host "result rỗng — mở @may_in_tien_tl_bot, gửi /start, chạy lại script."
    exit 1
}
$chatId = $r.result[-1].message.chat.id
Write-Host "TELEGRAM_CHAT_ID = $chatId"
$out = foreach ($line in Get-Content $envPath -Encoding UTF8) {
    if ($line -match '^\s*TELEGRAM_CHAT_ID=') { "TELEGRAM_CHAT_ID=$chatId" }
    else { $line }
}
$out | Set-Content $envPath -Encoding UTF8
Write-Host "Đã ghi vào .env"
