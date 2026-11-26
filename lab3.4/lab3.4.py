# -*- coding: cp1251 -*-
import argparse
import csv
import ctypes
import ctypes.wintypes as wintypes
import mmap
import os
import statistics
import time
from datetime import datetime

# Індивідуальні параметри варіанта №18
VAR_ID = 18
NT = 2
INC = 560
BUF_SIZE = 6
PRODUCERS = 1
CONSUMERS = 1
MEM_MB = 208
DELTA = 0.4
TOKEN = "LAB3-18-88"


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def get_win_mem_stats():
    psapi = ctypes.WinDLL("psapi")
    kernel32 = ctypes.WinDLL("kernel32")
    h_proc = kernel32.GetCurrentProcess()
    pmc = PROCESS_MEMORY_COUNTERS_EX()
    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    psapi.GetProcessMemoryInfo(h_proc, ctypes.byref(pmc), pmc.cb)
    return {
        "vsz_kb": pmc.PagefileUsage // 1024,
        "private_kb": pmc.PrivateUsage // 1024,
        "rss_kb": pmc.WorkingSetSize // 1024,
        "faults": pmc.PageFaultCount,
    }


def main():
    parser = argparse.ArgumentParser(description="ЛР №3 — Завдання 4: Адресний простір і ліниве виділення пам'яті")
    parser.add_argument("--mb", type=int, default=MEM_MB, help="Обсяг відображення у МБ (за замовчуванням 208)")
    parser.add_argument("--pause", type=float, default=DELTA, help="Пауза між фазами у секундах (за замовчуванням 0.4)")
    parser.add_argument("--wait-key", action="store_true", help="Чекати Enter перед кожною фазою (для знімків у VMMap/Resource Monitor)")
    args = parser.parse_args()

    pid = os.getpid()
    page_size = mmap.PAGESIZE
    total_bytes = args.mb * 1024 * 1024
    num_pages = total_bytes // page_size

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 72)
    print(f"{now_str}  mem_touch.py")
    print(f"n={VAR_ID} NT={NT} INC={INC} B={BUF_SIZE} P={PRODUCERS} C={CONSUMERS} MEM={args.mb} МБ DELTA={args.pause} с TOKEN={TOKEN}")
    print("=" * 72)
    print(f"PID = {pid} | PAGESIZE = {page_size} Б | Обсяг = {args.mb} МБ ({num_pages} сторінок)")

    phases_summary = []
    prev_faults = None

    def record_phase(phase_code: str, note: str):
        nonlocal prev_faults
        if args.wait_key:
            input(f"  [Фаза {phase_code}] Натисніть Enter для продовження...")
        else:
            time.sleep(args.pause)
        st = get_win_mem_stats()
        delta_f = "-" if prev_faults is None else f"+{st['faults'] - prev_faults}"
        prev_faults = st["faults"]
        phases_summary.append((phase_code, st["vsz_kb"], st["private_kb"], st["rss_kb"], st["faults"], delta_f))
        print(
            f"Фаза {phase_code}: VSZ(Committed)={st['vsz_kb']} КБ | Private={st['private_kb']} КБ | "
            f"RSS(WorkingSet)={st['rss_kb']} КБ | PageFaults={st['faults']} ({delta_f}) | {note}"
        )

    # Фаза A: старт
    record_phase("A", "Старт інтерпретатора")

    # Фаза B: mmap.mmap
    mm = mmap.mmap(-1, total_bytes, access=mmap.ACCESS_WRITE)
    buf_obj = (ctypes.c_char * total_bytes).from_buffer(mm)
    base_addr = ctypes.addressof(buf_obj)
    print(f"  -> Адреса початку відображення (ctypes.addressof): 0x{base_addr:016X}")
    record_phase("B", f"mmap {args.mb} МБ виділено")

    # Фаза C: перший прохід (1 байт на сторінку)
    lat_c = []
    for p in range(num_pages):
        offset = p * page_size
        t0 = time.perf_counter_ns()
        mm[offset] = 1
        t1 = time.perf_counter_ns()
        lat_c.append((t1 - t0) / 1000.0)
    record_phase("C", f"Перший прохід (медіана={statistics.median(lat_c):.2f} мкс, p99={sorted(lat_c)[int(0.99*num_pages)]:.2f} мкс)")

    # Фаза D: другий прохід (1 байт на сторінку)
    lat_d = []
    for p in range(num_pages):
        offset = p * page_size
        t0 = time.perf_counter_ns()
        mm[offset] = 2
        t1 = time.perf_counter_ns()
        lat_d.append((t1 - t0) / 1000.0)
    record_phase("D", f"Другий прохід (медіана={statistics.median(lat_d):.2f} мкс, p99={sorted(lat_d)[int(0.99*num_pages)]:.2f} мкс)")

    # Збереження CSV
    summary_csv = f"mem_phases_{TOKEN}.csv"
    with open(summary_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["phase", "vsz_kb", "private_kb", "rss_kb", "page_faults", "delta_faults"])
        w.writerows(phases_summary)

    lat_csv = f"mem_latency_{TOKEN}.csv"
    with open(lat_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["page", "pass1_us", "pass2_us"])
        for p in range(num_pages):
            w.writerow([p, round(lat_c[p], 3), round(lat_d[p], 3)])

    del buf_obj
    mm.close()
    print(f"CSV збережено: {summary_csv}, {lat_csv} ({num_pages} сторінок)")


if __name__ == "__main__":
    main()
