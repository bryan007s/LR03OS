# -*- coding: utf-8 -*-
import argparse, csv, ctypes, ctypes.wintypes as wintypes, mmap, os, statistics, time
from datetime import datetime

VAR_ID, NT, INC, BUF_SIZE, PRODUCERS, CONSUMERS = 18, 2, 560, 6, 1, 1
MEM_MB, DELTA, TOKEN = 208, 0.4, "LAB3-18-88"

class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]

psapi = ctypes.WinDLL("psapi")
kernel32 = ctypes.WinDLL("kernel32")
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

def get_win_mem_stats():
    pmc = PROCESS_MEMORY_COUNTERS_EX()
    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return {"vsz_kb": pmc.PagefileUsage // 1024, "private_kb": pmc.PrivateUsage // 1024,
            "rss_kb": pmc.WorkingSetSize // 1024, "faults": pmc.PageFaultCount}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mb", type=int, default=MEM_MB)
    p.add_argument("--pause", type=float, default=DELTA)
    p.add_argument("--wait-key", action="store_true")
    p.add_argument("--tag", default="main")
    args = p.parse_args()

    pid, page_size = os.getpid(), mmap.PAGESIZE
    total_bytes = args.mb * 1024 * 1024
    num_pages = total_bytes // page_size

    print("=" * 72)
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  mem_touch.py (tag={args.tag})")
    print(f"n={VAR_ID} NT={NT} INC={INC} B={BUF_SIZE} P={PRODUCERS} C={CONSUMERS} MEM={args.mb} МБ DELTA={args.pause} с TOKEN={TOKEN}")
    print("=" * 72)
    print(f"PID = {pid} | PAGESIZE = {page_size} Б | MEM = {args.mb} МБ ({num_pages} сторінок)")

    phases, prev_f = [], None
    def snap(code, title):
        nonlocal prev_f
        print(f"\n=== Фаза {code}: {title} ===")
        input(f"Зробіть знімок (PID={pid}) і натисніть Enter...") if args.wait_key else time.sleep(args.pause)
        st = get_win_mem_stats()
        diff = 0 if prev_f is None else st["faults"] - prev_f
        prev_f = st["faults"]
        phases.append((code, st["vsz_kb"], st["private_kb"], st["rss_kb"], st["faults"], diff))
        print(f"[знімок {code}] VSZ(committed)={st['vsz_kb']} КБ | Private={st['private_kb']} КБ | "
              f"RSS/WorkingSet={st['rss_kb']} КБ | page faults={st['faults']} (приріст з минулого знімка: {diff})")

    snap("A", "старт інтерпретатора")
    mm = mmap.mmap(-1, total_bytes, access=mmap.ACCESS_WRITE)
    buf = (ctypes.c_char * total_bytes).from_buffer(mm)
    print(f"Адреса початку відображення: {ctypes.addressof(buf):016X}")
    snap("B", f"mmap {args.mb} МБ")

    pass1_ns = []
    for i in range(num_pages):
        off = i * page_size
        t0 = time.perf_counter_ns()
        mm[off] = 1
        pass1_ns.append(time.perf_counter_ns() - t0)
    snap("C", "перший прохід")

    pass2_ns = []
    for i in range(num_pages):
        off = i * page_size
        t0 = time.perf_counter_ns()
        mm[off] = 2
        pass2_ns.append(time.perf_counter_ns() - t0)
    snap("D", "другий прохід")

    pages_csv, phases_csv = f"pages_{args.tag}_{TOKEN}.csv", f"phases_{args.tag}_{TOKEN}.csv"
    with open(pages_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["page", "pass1_ns", "pass2_ns"])
        for i in range(num_pages): w.writerow([i, pass1_ns[i], pass2_ns[i]])

    with open(phases_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["phase", "vsz_kb", "private_kb", "rss_kb", "page_faults", "delta_faults"])
        w.writerows(phases)

    warmup = int(0.05 * num_pages)
    p1, p2 = sorted(pass1_ns[warmup:]), sorted(pass2_ns[warmup:])
    n_t = len(p1)
    med1, med2 = statistics.median(p1), statistics.median(p2)
    print(f"pass1: N={n_t}, min={p1[0]:.0f}, медіана={med1:.0f}, середнє={statistics.mean(p1):.0f}, p95={p1[int(0.95*n_t)]:.0f}, p99={p1[int(0.99*n_t)]:.0f}, max={p1[-1]:.0f} нс")
    print(f"pass2: N={n_t}, min={p2[0]:.0f}, медіана={med2:.0f}, середнє={statistics.mean(p2):.0f}, p95={p2[int(0.95*n_t)]:.0f}, p99={p2[int(0.99*n_t)]:.0f}, max={p2[-1]:.0f} нс")
    print(f"Оцінка ціни одного minor fault = {med1 - med2:.0f} нс")
    del buf; mm.close()

if __name__ == "__main__":
    main()
