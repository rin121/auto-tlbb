"""Thư mục của auto: nơi để cau_hinh.json, tai_khoan.json, dll\\, nhật ký."""
import os
import sys

# Bản đóng gói (AutoHoc.exe, PyInstaller) chạy code từ thư mục tạm, nên lấy thư mục chứa file .exe.
THU_MUC_APP = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
