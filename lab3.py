import sys
import time
import threading
import statistics

NT = 2
INC = 560
EXPECTED = NT * INC
REPEATS = 1000
WARMUP = 50


def percentile(data, p):
    s = sorted(data)
    idx = int(round((p / 100.0) * (len(s) - 1)))
    return s[idx]


def run_single(mode, lock=None, sem=None):
    counter = 0

    def worker_none():
        nonlocal counter
        for _ in range(INC):
            counter += 1

    def worker_lock():
        nonlocal counter
        for _ in range(INC):
            with lock:
                counter += 1

    def worker_sem():
        nonlocal counter
        for _ in range(INC):
            with sem:
                counter += 1

    def worker_local():
        nonlocal counter
        local_sum = 0
        for _ in range(INC):
            local_sum += 1
        with lock:
            counter += local_sum

    target_map = {
        "none": worker_none,
        "lock": worker_lock,
        "sem": worker_sem,
        "local": worker_local,
    }
    fn = target_map[mode]
    threads = [threading.Thread(target=fn) for _ in range(NT)]

    t0 = time.perf_counter_ns()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    dt_us = (time.perf_counter_ns() - t0) / 1000.0
    lost = EXPECTED - counter
    return lost, dt_us


def benchmark(label, mode, switch_interval):
    sys.setswitchinterval(switch_interval)
    lock = threading.Lock() if mode in ("lock", "local") else None
    sem = threading.Semaphore(1) if mode == "sem" else None

    losses = []
    times_us = []
    for _ in range(REPEATS):
        lost, dt = run_single(mode, lock=lock, sem=sem)
        losses.append(lost)
        times_us.append(dt)

    lost_runs = sum(1 for x in losses if x > 0)
    lost_after_warmup = sum(1 for x in losses[WARMUP:] if x > 0)

    return {
        "label": label,
        "lost_runs": lost_runs,
        "lost_pct": lost_runs / REPEATS * 100,
        "lost_warmup": lost_after_warmup,
        "lost_warmup_pct": lost_after_warmup / (REPEATS - WARMUP) * 100,
        "lost_med": int(statistics.median(losses)),
        "lost_p95": int(percentile(losses, 95)),
        "lost_max": max(losses),
        "time_med": statistics.median(times_us),
        "time_p95": percentile(times_us, 95),
    }


if __name__ == "__main__":
    print(f"Варіант 18: NT={NT}, INC={INC}, очікуване={EXPECTED}, повторів R={REPEATS}\n")
    res_def = benchmark("Без синхронізації, 0,005 с", "none", 0.005)
    res_fast = benchmark("Без синхронізації, 1e-6 с", "none", 1e-6)
    res_lock = benchmark("L (Lock)", "lock", 1e-6)
    res_sem = benchmark("S (Semaphore)", "sem", 1e-6)
    res_loc = benchmark("G (локальне накопичення)", "local", 1e-6)

    print("=== ТАБЛИЦЯ 3 (Дві серії без синхронізації) ===")
    for r in (res_def, res_fast):
        print(
            f"{r['label']} | Втрати: {r['lost_runs']} з {REPEATS} ({r['lost_pct']:.1f}%); "
            f"після розігріву: {r['lost_warmup']} з {REPEATS - WARMUP} ({r['lost_warmup_pct']:.1f}%) | "
            f"lost med={r['lost_med']}, p95={r['lost_p95']}, max={r['lost_max']} | "
            f"med_time={r['time_med']:.1f} мкс"
        )

    print("\n=== ТАБЛИЦЯ 4 (Порівняння засобів синхронізації) ===")
    base_fast = res_fast["time_med"]
    for idx, r in enumerate((res_def, res_fast, res_lock, res_sem, res_loc)):
        ratio = 1.00 if idx in (0, 1) else r["time_med"] / base_fast
        print(
            f"{r['label']} | Втрати: {r['lost_runs']} з {REPEATS} | "
            f"med={r['time_med']:.1f} мкс | p95={r['time_p95']:.1f} мкс | відносно={ratio:.2f}"
        )
