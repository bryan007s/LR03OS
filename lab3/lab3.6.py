# -*- coding: utf-8 -*-
import ctypes, ctypes.wintypes as wintypes, multiprocessing as mp, os, statistics, time
import numpy as np

PARENT_MB = 208
TEMP_FILE = "bench_io_LAB3-18-88.bin"

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

def get_rss_kb():
    pmc = PROCESS_MEMORY_COUNTERS_EX()
    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
    psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(pmc), pmc.cb)
    return pmc.WorkingSetSize // 1024

def child_worker(q, t_start):
    dt_ms = (time.perf_counter() - t_start) * 1000.0
    q.put((dt_ms, get_rss_kb(), "PARENT_DATA" in globals()))

def run_table16():
    # Виділяємо 208 МБ у батьківському процесі та торкаємося кожної сторінки
    global PARENT_DATA
    PARENT_DATA = bytearray(PARENT_MB * 1024 * 1024)
    for i in range(0, len(PARENT_DATA), 4096):
        PARENT_DATA[i] = 1
    parent_rss = get_rss_kb()

    print(f"\n=== ДАНІ ДЛЯ ТАБЛИЦІ 16 (spawn, дані батька - {PARENT_MB} МБ) ===")
    print(f"{'Запуск':<7} | {'Старт->готовий, мс':>18} | {'RSS нащадка, КБ':>16} | {'RSS батька, КБ':>15} | {'Дані батька':>12}")
    ctx = mp.get_context("spawn")
    for run_idx in range(1, 6):
        q = ctx.Queue()
        t0 = time.perf_counter()
        p = ctx.Process(target=child_worker, args=(q, t0))
        p.start()
        dt_ms, child_rss, has_data = q.get()
        p.join()
        ans = "так" if has_data else "ні"
        print(f"{run_idx:<7} | {dt_ms:>18.1f} | {child_rss:>16} | {parent_rss:>15} | {ans:>12}")
    del PARENT_DATA

def bench_io(block_size, ops, use_fsync):
    data = os.urandom(block_size)
    lat_us = []
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)
    fd = os.open(TEMP_FILE, os.O_CREAT | os.O_WRONLY | os.O_TRUNC | getattr(os, "O_BINARY", 0), 0o644)

    t_total_0 = time.perf_counter()
    for _ in range(ops):
        t0 = time.perf_counter()
        os.write(fd, data)
        if use_fsync:
            os.fsync(fd)
        lat_us.append((time.perf_counter() - t0) * 1e6)

    t_fsync_ms = None
    if not use_fsync:
        tf0 = time.perf_counter()
        os.fsync(fd)
        t_fsync_ms = (time.perf_counter() - tf0) * 1000.0
    t_total = time.perf_counter() - t_total_0
    os.close(fd)

    arr = np.array(lat_us)
    med = float(np.median(arr))
    p95 = float(np.percentile(arr, 95))
    p99 = float(np.percentile(arr, 99))
    iops = int(round(ops / t_total))
    mib_s = (ops * block_size) / (1024 * 1024) / t_total
    return med, p95, p99, iops, mib_s, t_fsync_ms

def run_table17():
    configs = [(512, 2000), (4096, 2000), (65536, 2000), (1048576, 256)]
    print("\n=== ДАНІ ДЛЯ ТАБЛИЦІ 17 (Запис: buffered та fsync) ===")
    print(f"{'Режим':<9} | {'Блок, Б':>8} | {'Опер.':>6} | {'Медіана, мкс':>12} | {'p95, мкс':>10} | {'p99, мкс':>10} | {'IOPS':>8} | {'МіБ/с':>8} | {'Фін. fsync, мс':>14}")
    for blk, ops in configs:
        for mode, flag in [("buffered", False), ("fsync", True)]:
            med, p95, p99, iops, mib_s, f_ms = bench_io(blk, ops, flag)
            f_str = f"{f_ms:.1f}" if f_ms is not None else "-"
            print(f"{mode:<9} | {blk:>8} | {ops:>6} | {med:>12.1f} | {p95:>10.1f} | {p99:>10.1f} | {iops:>8} | {mib_s:>8.1f} | {f_str:>14}")
    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)

if __name__ == "__main__":
    run_table16()
    run_table17()
