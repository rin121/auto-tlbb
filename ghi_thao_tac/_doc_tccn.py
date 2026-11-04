import ctypes
import ctypes.wintypes as wt
OUT = r"d:\Games\ThienLongCityCSClientFull2026\AutoHoc\ghi_thao_tac\_live.txt"
PID = 2240
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
class MBI(ctypes.Structure):
    _fields_ = [
        ("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
        ("AllocationProtect", wt.DWORD), ("RegionSize", ctypes.c_size_t),
        ("State", wt.DWORD), ("Protect", wt.DWORD), ("Type", wt.DWORD),
    ]
needle = b"Packet_Temporary_Select("
handle = kernel32.OpenProcess(0x0010 | 0x0400, False, PID)
hits = []
addr = 0
mbi = MBI()
read = ctypes.c_size_t()
while addr < 0x80000000 and len(hits) < 8:
    if not kernel32.VirtualQueryEx(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
        break
    base = mbi.BaseAddress or 0
    size = mbi.RegionSize or 0
    if mbi.State == 0x1000 and not (mbi.Protect & 0x100) and mbi.Protect != 1 and 0 < size <= 16 * 1024 * 1024:
        buf = ctypes.create_string_buffer(size)
        if kernel32.ReadProcessMemory(handle, ctypes.c_void_p(base), buf, size, ctypes.byref(read)) and read.value:
            data = buf.raw[:read.value]
            pos = 0
            while len(hits) < 8:
                i = data.find(needle, pos)
                if i < 0:
                    break
                hits.append(data[i:i+80])
                pos = i + len(needle)
    nxt = base + size
    if nxt <= addr:
        break
    addr = nxt
kernel32.CloseHandle(handle)
open(OUT, "w", encoding="utf-8").write("\n".join(h.decode("latin-1", "replace") for h in hits) or "khong thay")
