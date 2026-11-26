import csv
import sys
import threading
import time
from collections import Counter
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

BUGGY_CONSUMERS = 3
RUNS = 3
STOP = None


class BrokenRingBufferIf:
    """Навмисно помилковий кільцевий буфер: використано 'if' замість 'while'."""

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.buf = [None] * capacity
        self.head = 0
        self.tail = 0
        self.count = 0
        self.lock = threading.Lock()
        self.not_full = threading.Condition(self.lock)
        self.not_empty = threading.Condition(self.lock)

    def put(self, item, timeout: float = 1.0) -> bool:
        with self.not_full:
            if self.count >= self.capacity:  # ПОМИЛКА: if замість while
                if not self.not_full.wait(timeout=timeout):
                    return False
                if self.count >= self.capacity:
                    return False
            self.buf[self.tail] = item
            self.tail = (self.tail + 1) % self.capacity
            self.count += 1
            self.not_empty.notify_all()
            return True

    def get(self):
        with self.not_empty:
            if self.count <= 0:  # ПОМИЛКА: if замість while
                if not self.not_empty.wait(timeout=0.5):
                    raise TimeoutError("consumer wait timeout")
            # Після пробудження умова не перевіряється повторно -> читання зі старого індексу
            val = self.buf[self.head]
            self.head = (self.head + 1) % self.capacity
            self.count -= 1
            self.not_full.notify_all()
            return val


def run_buggy_experiment(run_idx: int):
    old_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        buf = BrokenRingBufferIf(BUF_SIZE)
        expected_items = [VAR_ID * i + 1 for i in range(ITEMS_TOTAL)]
        expected_set = set(expected_items)

        received = []
        recv_lock = threading.Lock()
        errors = []
        stop_put = 0
        stop_consumed = 0

        def producer():
            nonlocal stop_put
            for val in expected_items:
                if not buf.put(val, timeout=0.8):
                    errors.append("виробник не дочекався місця в буфері")
                    break
            for _ in range(BUGGY_CONSUMERS):
                if buf.put(STOP, timeout=0.5):
                    stop_put += 1

        def consumer():
            nonlocal stop_consumed
            while True:
                try:
                    val = buf.get()
                except Exception as exc:
                    errors.append(str(exc))
                    break
                if val is STOP:
                    with recv_lock:
                        stop_consumed += 1
                    break
                with recv_lock:
                    received.append(val)

        threads = [threading.Thread(target=consumer) for _ in range(BUGGY_CONSUMERS)]
        t_prod = threading.Thread(target=producer)
        for t in threads:
            t.start()
        t_prod.start()
        t_prod.join(timeout=3.0)
        for t in threads:
            t.join(timeout=2.0)

        counts = Counter(received)
        unique_cnt = len(counts)
        dup_cnt = sum(c - 1 for c in counts.values() if c > 1)
        missed_cnt = len(expected_set - set(counts.keys()))

        return {
            "run": run_idx,
            "received": len(received),
            "unique": unique_cnt,
            "duplicates": dup_cnt,
            "missed": missed_cnt,
            "stop_put": stop_put,
            "stop_done": stop_consumed,
            "end_count": buf.count,
            "exceptions": len(errors),
            "err_msg": errors[0] if errors else "",
        }
    finally:
        sys.setswitchinterval(old_interval)


def main():
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("=" * 72)
    print(f"{now_str}  buffer_if.py")
    print(f"n={VAR_ID} NT={NT} INC={INC} B={BUF_SIZE} P={PRODUCERS} C={CONSUMERS} MEM={MEM_MB} МБ DELTA={DELTA} с TOKEN={TOKEN}")
    print("=" * 72)
    print(f"Помилковий буфер: C={BUGGY_CONSUMERS}, ITEMS={ITEMS_TOTAL}, switchinterval=1e-6 с")

    results = []
    for r in range(1, RUNS + 1):
        res = run_buggy_experiment(r)
        results.append(res)
        print(
            f"  запуск {r}: отримано={res['received']}, унікальних={res['unique']}, "
            f"дублікатів={res['duplicates']}, пропущено={res['missed']}, помилок={res['exceptions']}"
        )
        if res["err_msg"]:
            print(f"    {res['err_msg']}")

    csv_name = f"buffer_if_{TOKEN}.csv"
    with open(csv_name, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "run", "received", "unique", "duplicates", "missed",
            "stop_put", "stop_done", "end_count", "exceptions"
        ])
        for res in results:
            writer.writerow([
                res["run"], res["received"], res["unique"], res["duplicates"],
                res["missed"], res["stop_put"], res["stop_done"],
                res["end_count"], res["exceptions"]
            ])

    print(f"  CSV: {csv_name}, рядків: {len(results)}")
    print("Готово. Цей код навмисно неправильний; його не використовуйте замість BoundedBuffer.")


if __name__ == "__main__":
    main()
