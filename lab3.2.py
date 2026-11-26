import argparse
import csv
import os
import threading
import time
from collections import deque
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
ITEMS_TOTAL = 2000
TOKEN = "LAB3-18-88"
DEFAULT_RUNS = 3


class RingBufferSync:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.queue = deque()
        self.mtx = threading.Lock()
        self.not_full = threading.Condition(self.mtx)
        self.not_empty = threading.Condition(self.mtx)
        self.closed = False
        self.wait_full_events = 0
        self.wait_empty_events = 0

    def push(self, item: tuple):
        with self.not_full:
            while len(self.queue) >= self.capacity:
                self.wait_full_events += 1
                self.not_full.wait()
            self.queue.append(item)
            self.not_empty.notify()

    def pop(self):
        with self.not_empty:
            while not self.queue and not self.closed:
                self.wait_empty_events += 1
                self.not_empty.wait()
            if not self.queue and self.closed:
                return None
            val = self.queue.popleft()
            self.not_full.notify()
            return val

    def close(self):
        with self.not_empty:
            self.closed = True
            self.not_empty.notify_all()


def run_once(run_idx: int, prod_delay: float, cons_delay: float):
    buf = RingBufferSync(BUF_SIZE)
    expected_items = [VAR_ID * i + 1 for i in range(ITEMS_TOTAL)]
    expected_sum = sum(expected_items)

    received = []
    trace_rows = []
    tids = {}

    def producer_worker():
        tids["producer"] = threading.get_native_id()
        for seq_no, val in enumerate(expected_items):
            if prod_delay > 0:
                time.sleep(prod_delay)
            t_in = time.perf_counter_ns()
            buf.push((seq_no, val, t_in))
        buf.close()

    def consumer_worker():
        tids["consumer"] = threading.get_native_id()
        while True:
            entry = buf.pop()
            if entry is None:
                break
            t_out = time.perf_counter_ns()
            seq_no, val, t_in = entry
            if cons_delay > 0:
                time.sleep(cons_delay)
            received.append(val)
            wait_us = (t_out - t_in) / 1000.0
            trace_rows.append((run_idx, seq_no, val, round(wait_us, 3)))

    t_cons = threading.Thread(target=consumer_worker, name="consumer-0")
    t_prod = threading.Thread(target=producer_worker, name="producer-0")

    t0 = time.perf_counter()
    t_cons.start()
    t_prod.start()
    t_prod.join()
    t_cons.join()
    elapsed_s = time.perf_counter() - t0

    ok_count = (len(received) == ITEMS_TOTAL)
    ok_sum = (sum(received) == expected_sum)
    ok_once = (sorted(received) == expected_items)

    print(f"PID = {os.getpid()}")
    print(f"[TID] consumer-0: {tids.get('consumer')}")
    print(f"[TID] producer-0: {tids.get('producer')}")
    status = "ОК" if (ok_count and ok_sum and ok_once) else "FAIL"
    print(f"  запуск {run_idx}: кількість={ok_count}, сума={ok_sum}, усі номери один раз={ok_once} -> {status}")
    print(
        f"  waits_put={buf.wait_full_events}, waits_get={buf.wait_empty_events}, "
        f"час={elapsed_s:.2f} с, count у кінці={len(buf.queue)}"
    )
    return trace_rows


def main():
    parser = argparse.ArgumentParser(description="ЛР №3 — Завдання 3: Обмежений буфер (Варіант 18)")
    parser.add_argument("--all", action="store_true", help="Виконати всі режими a, b, c")
    parser.add_argument("--mode", choices=["a", "b", "c"], help="Обрати конкретний режим (a, b або c)")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="Кількість запусків (за замовчуванням 3)")
    parser.add_argument("--out", default=".", help="Каталог для CSV")
    args = parser.parse_args()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 72)
    print(f"{now_str}  lab3.2.py")
    print(f"n={VAR_ID} NT={NT} INC={INC} B={BUF_SIZE} P={PRODUCERS} C={CONSUMERS} MEM={MEM_MB} МБ DELTA={DELTA} с TOKEN={TOKEN}")
    print("=" * 72)

    all_modes = {
        "a": (0.0, 0.0),
        "b": (0.0, 0.001),
        "c": (0.005, 0.0),
    }

    selected = [args.mode] if args.mode else ["a", "b", "c"]
    os.makedirs(args.out, exist_ok=True)

    for mode_code in selected:
        p_del, c_del = all_modes[mode_code]
        print()
        print(f"Режим {mode_code} (запусків: {args.runs})")
        all_rows = []
        for r in range(1, args.runs + 1):
            all_rows.extend(run_once(r, p_del, c_del))

        csv_name = f"buffer_{mode_code}_{TOKEN}.csv"
        csv_path = os.path.join(args.out, csv_name)
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["run", "seq", "value", "wait_us"])
            writer.writerows(all_rows)
        print(f"  CSV: {csv_name}, рядків: {len(all_rows)}")


if __name__ == "__main__":
    main()