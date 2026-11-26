# -*- coding: utf-8 -*-
import argparse, csv, ctypes, ctypes.wintypes as wintypes, sys, time

TOKEN = "LAB3-18-88"

class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]

psapi, kernel32 = ctypes.WinDLL("psapi"), ctypes.WinDLL("kernel32")
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]

def main():
    p = argparse.ArgumentParser()
    p.add_argument("pid", type=int)
    p.add_argument("--delta", type=float, default=0.4)
    p.add_argument("--points", type=int, default=65)
    p.add_argument("--label", default="mem")
    args = p.parse_args()

    h = kernel32.OpenProcess(0x0410, False, args.pid)
    if not h:
        sys.exit(f"Не вдалося відкрити процес PID={args.pid}")

    out_csv = f"monitor_{args.label}_{TOKEN}.csv"
    pmc = PROCESS_MEMORY_COUNTERS_EX()
    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    exit_code = wintypes.DWORD()
    rows = []
    t0 = time.perf_counter()

    for _ in range(args.points):
        kernel32.GetExitCodeProcess(h, ctypes.byref(exit_code))
        if exit_code.value != 259:  # STILL_ACTIVE
            break
        if psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
            rows.append((round(time.perf_counter() - t0, 2),
                         pmc.PagefileUsage // 1024,
                         pmc.WorkingSetSize // 1024,
                         pmc.PageFaultCount))
        time.sleep(args.delta)

    kernel32.CloseHandle(h)
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_sec", "vsz_kb", "rss_kb", "page_faults"])
        w.writerows(rows)
    print(f"Процес {args.pid} завершився; записано {len(rows)} з {args.points} точок -> {out_csv}")

if __name__ == "__main__":
    main()
