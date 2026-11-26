# -*- coding: utf-8 -*-
import os, subprocess, sys, threading, time
import numpy as np

DELTA_S = 0.4

def monitor_target(cmd, target_pts):
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ts = []
    t0 = time.perf_counter()
    for _ in range(target_pts):
        if proc.poll() is not None:
            break
        ts.append((time.perf_counter() - t0) * 1000.0)
        time.sleep(DELTA_S)
    proc.terminate()
    proc.wait()
    dt = np.diff(ts)
    dur_s = (ts[-1] - ts[0]) / 1000.0
    return len(ts), float(np.median(dt)), float(np.percentile(dt, 95)), float(np.max(dt)), dur_s

print("Збір >300 точок для Таблиці 20 (Δ = 400 мс, зачекайте ~2 хв)...")
mem_res, io_res = {}, {}

def run_m():
    mem_res["v"] = monitor_target([sys.executable, "lab3.4.py", "--pause", "42", "--tag", "t20"], 315)

def run_i():
    io_code = "import time; f=open('_tmp_io.bin','wb'); [(f.write(b'x'*4096), f.flush(), time.sleep(0.05)) for _ in range(3000)]"
    io_res["v"] = monitor_target([sys.executable, "-c", io_code], 308)

t1, t2 = threading.Thread(target=run_m), threading.Thread(target=run_i)
t1.start(); t2.start(); t1.join(); t2.join()
if os.path.exists("_tmp_io.bin"):
    os.remove("_tmp_io.bin")

print("\n=== ДАНІ ДЛЯ ТАБЛИЦІ 20 (задане Δ = 400 мс) ===")
print(f"{'Серія':<18} | {'Точок':>6} | {'Медіана, мс':>11} | {'p95, мс':>9} | {'Максимум, мс':>12} | {'Тривалість, с':>13}")
for name, r in [("mem (завдання 4)", mem_res["v"]), ("io (завдання 6)", io_res["v"])]:
    print(f"{name:<18} | {r[0]:>6} | {r[1]:>11.1f} | {r[2]:>9.1f} | {r[3]:>12.1f} | {r[4]:>13.1f}")

def run_deadlock_bench(ordered, repeats=100):
    deadlocks, times_ms = 0, []
    for _ in range(repeats):
        lock_a, lock_b = threading.Lock(), threading.Lock()
        dl_flag = [False]
        t0 = time.perf_counter()
        def w1():
            with lock_a:
                time.sleep(0.01)
                if lock_b.acquire(timeout=0.05):
                    lock_b.release()
                else:
                    dl_flag[0] = True
        def w2():
            first, second = (lock_a, lock_b) if ordered else (lock_b, lock_a)
            with first:
                time.sleep(0.01)
                if second.acquire(timeout=0.05):
                    second.release()
                else:
                    dl_flag[0] = True
        th1, th2 = threading.Thread(target=w1), threading.Thread(target=w2)
        th1.start(); th2.start(); th1.join(); th2.join()
        if dl_flag[0]:
            deadlocks += 1
        times_ms.append((time.perf_counter() - t0) * 1000.0)
    arr = np.array(times_ms)
    return repeats, deadlocks, float(np.median(arr)), float(np.percentile(arr, 95))

print("\n=== ДАНІ ДЛЯ ТАБЛИЦІ 21 (deadlock.py, 100 повторів) ===")
print(f"{'Версія':<34} | {'Повторів':>8} | {'Блокувань':>9} | {'Медіана, мс':>11} | {'p95, мс':>9}")
for lbl, ord_flag in [("протилежний порядок (A->B і B->A)", False), ("глобальний порядок (A->B в обох)", True)]:
    r = run_deadlock_bench(ord_flag, 100)
    print(f"{lbl:<34} | {r[0]:>8} | {r[1]:>9} | {r[2]:>11.1f} | {r[3]:>9.1f}")
