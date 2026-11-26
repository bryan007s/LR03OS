# -*- coding: utf-8 -*-
import ctypes, ctypes.wintypes as wintypes, mmap, os, subprocess, sys, time

SHM_MB = 128
SHM_BYTES = SHM_MB * 1024 * 1024
TOKEN = "LAB3-18-88"

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64), ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64), ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64), ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]

class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]

kernel32 = ctypes.WinDLL("kernel32")
psapi = ctypes.WinDLL("psapi")
kernel32.GlobalMemoryStatusEx.argtypes = [ctypes.POINTER(MEMORYSTATUSEX)]
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]

def free_ram_mb():
    ms = MEMORYSTATUSEX()
    ms.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    kernel32.GlobalMemoryStatusEx(ctypes.byref(ms))
    return ms.ullAvailPhys // (1024 * 1024)

def proc_mem_kb(pid):
    h = kernel32.OpenProcess(0x0410, False, pid)
    pmc = PROCESS_MEMORY_COUNTERS_EX()
    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb)
    kernel32.CloseHandle(h)
    ws = pmc.WorkingSetSize // 1024
    priv = pmc.PrivateUsage // 1024
    comm = priv + SHM_MB * 1024
    return ws, priv, ws - priv, comm

def run_child(mode, tag):
    mm = mmap.mmap(-1, SHM_BYTES, tagname=tag)
    if mode == "touch":
        acc = 0
        for off in range(0, SHM_BYTES, mmap.PAGESIZE):
            acc ^= mm[off]
    time.sleep(3.0)
    mm.close()

def run_parent(mode):
    tag = f"Local\\{TOKEN}_{mode}_{os.getpid()}"
    ram_before = free_ram_mb()
    mm = mmap.mmap(-1, SHM_BYTES, tagname=tag)
    for off in range(0, SHM_BYTES, mmap.PAGESIZE):
        mm[off] = 0x5A
    time.sleep(0.4)
    ram_after_parent = free_ram_mb()

    child = subprocess.Popen([sys.executable, os.path.abspath(__file__), "--child", mode, tag])
    time.sleep(1.5)
    ram_after_child = free_ram_mb()

    p_ws, p_priv, p_sh, p_comm = proc_mem_kb(os.getpid())
    c_ws, c_priv, c_sh, c_comm = proc_mem_kb(child.pid)
    child.wait()
    mm.close()

    t14 = [
        (mode, "батько", os.getpid(), p_ws, p_priv, p_sh, p_comm),
        (mode, "нащадок", child.pid, c_ws, c_priv, c_sh, c_comm),
    ]
    sum_ws_mb = round((p_ws + c_ws) / 1024)
    t15 = (mode, ram_before, ram_after_parent, ram_after_child, ram_before - ram_after_child, sum_ws_mb)
    return t14, t15

if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "--child":
        run_child(sys.argv[2], sys.argv[3])
    else:
        rows14, rows15 = [], []
        for m in ("write", "touch"):
            r14, r15 = run_parent(m)
            rows14.extend(r14)
            rows15.append(r15)
            time.sleep(0.5)

        print("\n=== ДАНІ ДЛЯ ТАБЛИЦІ 14 (блок 128 МБ) ===")
        print(f"{'Нащадок':<8} | {'Процес':<8} | {'PID':>6} | {'WorkingSet':>11} | {'Private':>9} | {'WS-Private':>11} | {'Committed':>10}")
        for r in rows14:
            print(f"{r[0]:<8} | {r[1]:<8} | {r[2]:>6} | {r[3]:>11} | {r[4]:>9} | {r[5]:>11} | {r[6]:>10}")

        print("\n=== ДАНІ ДЛЯ ТАБЛИЦІ 15 (МБ) ===")
        print(f"{'Нащадок':<8} | {'До':>7} | {'Після батька':>13} | {'Після нащадка':>14} | {'Спад RAM':>9} | {'Сума WS':>8}")
        for r in rows15:
            print(f"{r[0]:<8} | {r[1]:>7} | {r[2]:>13} | {r[3]:>14} | {r[4]:>9} | {r[5]:>8}")
