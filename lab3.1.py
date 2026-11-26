import argparse
import csv
import os
import statistics
import sys
import threading
import time
from datetime import datetime

# Індивідуальні параметри варіанта №18
VAR_NUM = 18
THREADS_CNT = 2
INC_PER_THREAD = 560
BUF_CAP = 6
PROD_CNT = 1
CONS_CNT = 1
MEM_LIMIT_MB = 208
DELTA_SEC = 0.4
CTRL_TOKEN = "LAB3-18-88"

TARGET_SUM = THREADS_CNT * INC_PER_THREAD
TOTAL_RUNS = 1000
SKIP_WARMUP = 50


def get_quantile(sorted_seq, percent):
    if not sorted_seq:
        return 0.0
    idx = (percent / 100.0) * (len(sorted_seq) - 1)
    low = int(idx)
    high = min(low + 1, len(sorted_seq) - 1)
    weight = idx - low
    return sorted_seq[low] * (1.0 - weight) + sorted_seq[high] * weight


def probe_timer_cost(iterations=1000):
    samples = []
    for _ in range(iterations):
        start = time.perf_counter_ns()
        end = time.perf_counter_ns()
        samples.append(max(0, end - start))
    return int(round(statistics.median(samples)))


def single_trial(strategy, mtx=None, semaphore=None):
    total_val = 0

    def task_unsync():
        nonlocal total_val
        for _ in range(INC_PER_THREAD):
            total_val += 1

    def task_mutex():
        nonlocal total_val
        for _ in range(INC_PER_THREAD):
            with mtx:
                total_val += 1

    def task_sem():
        nonlocal total_val
        for _ in range(INC_PER_THREAD):
            with semaphore:
                total_val += 1

    def task_thread_local():
        nonlocal total_val
        partial = 0
        for _ in range(INC_PER_THREAD):
            partial += 1
        with mtx:
            total_val += partial

    handlers = {
        "unsync": task_unsync,
        "mutex": task_mutex,
        "sem": task_sem,
        "local": task_thread_local,
    }
    worker_fn = handlers[strategy]
    pool = [threading.Thread(target=worker_fn) for _ in range(THREADS_CNT)]

    t_begin = time.perf_counter_ns()
    for th in pool:
        th.start()
    for th in pool:
        th.join()
    duration_us = (time.perf_counter_ns() - t_begin) / 1000.0

    missed = TARGET_SUM - total_val
    return missed, duration_us


def compute_stats(seq):
    ordered = sorted(seq)
    return {
        "count": len(ordered),
        "min": ordered[0],
        "median": statistics.median(ordered),
        "mean": statistics.mean(ordered),
        "p95": get_quantile(ordered, 95),
        "p99": get_quantile(ordered, 99),
        "max": ordered[-1],
    }


def execute_batch(title, suffix, strategy, switch_dt, save_dir="."):
    sys.setswitchinterval(switch_dt)
    mtx = threading.Lock() if strategy in ("mutex", "local") else None
    semaphore = threading.Semaphore(1) if strategy == "sem" else None

    records = []
    for step in range(1, TOTAL_RUNS + 1):
        missed, dt_us = single_trial(strategy, mtx=mtx, semaphore=semaphore)
        records.append((step, missed, round(dt_us, 3)))

    os.makedirs(save_dir, exist_ok=True)
    csv_filename = f"sync_{suffix}_{CTRL_TOKEN}.csv"
    full_path = os.path.join(save_dir, csv_filename)
    with open(full_path, "w", newline="", encoding="utf-8") as fp:
        csv_out = csv.writer(fp)
        csv_out.writerow(["iteration", "lost_updates", "duration_us"])
        csv_out.writerows(records)

    steady = records[SKIP_WARMUP:]
    lost_series = [item[1] for item in steady]
    time_series = [item[2] for item in steady]

    bad_trials = sum(1 for v in lost_series if v > 0)
    stat_lost = compute_stats(lost_series)
    stat_time = compute_stats(time_series)

    dt_label = f"{switch_dt:g}"
    print(f"  Файл CSV: {csv_filename} (записів: {len(records)})")
    print(f"[{title}] switch_interval={dt_label} с -> втрати у {bad_trials}/{len(steady)} запусках")
    print(
        f"    lost: N={stat_lost['count']}, прогрів={SKIP_WARMUP}, "
        f"min={stat_lost['min']:.3f}, медіана={stat_lost['median']:.3f}, середнє={stat_lost['mean']:.3f}, "
        f"p95={stat_lost['p95']:.3f}, p99={stat_lost['p99']:.3f}, max={stat_lost['max']:.3f}"
    )
    print(
        f"    час (мкс): N={stat_time['count']}, прогрів={SKIP_WARMUP}, "
        f"min={stat_time['min']:.3f}, медіана={stat_time['median']:.3f}, середнє={stat_time['mean']:.3f}, "
        f"p95={stat_time['p95']:.3f}, p99={stat_time['p99']:.3f}, max={stat_time['max']:.3f}"
    )


def main():
    cli = argparse.ArgumentParser(description="ЛР №3 — Дослідження гонитви та синхронізації (Варіант 18)")
    cli.add_argument("--all", action="store_true", help="Виконати всі 5 експериментальних серій")
    cli.add_argument("--out", default=".", help="Папка для збереження CSV-результатів")
    opts = cli.parse_args()

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    timer_ns = probe_timer_cost()

    print("-" * 72)
    print(f"{ts} | Скрипт: sync_bench.py")
    print(f"Варіант: n={VAR_NUM} | NT={THREADS_CNT} INC={INC_PER_THREAD} B={BUF_CAP} P={PROD_CNT} C={CONS_CNT} MEM={MEM_LIMIT_MB} МБ DELTA={DELTA_SEC} с | TOKEN={CTRL_TOKEN}")
    print("-" * 72)
    print(f"Очікуваний результат лічильника: {TARGET_SUM} ({THREADS_CNT} x {INC_PER_THREAD})")
    print(f"Накладні витрати таймера: {timer_ns} нс\n")

    experiments = [
        ("Без синхронізації (стандарт)", "unsync_0.005", "unsync", 0.005),
        ("Без синхронізації (1e-6)", "unsync_1e-6", "unsync", 1e-6),
        ("L — Lock", "L_lock", "mutex", 1e-6),
        ("S — Semaphore", "S_sem", "sem", 1e-6),
        ("G — Локальне накопичення", "G_local", "local", 1e-6),
    ]

    for title, suffix, strategy, switch_dt in experiments:
        execute_batch(title, suffix, strategy, switch_dt, save_dir=opts.out)

    print("\nВиконання завершено.")


if __name__ == "__main__":
    main()
