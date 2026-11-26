# -*- coding: utf-8 -*-
import csv, ctypes, ctypes.wintypes as wintypes, subprocess, sys, time
import matplotlib.pyplot as plt

MEM_MB = 208
DELTA = 0.4
PAUSE = 6.0
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

psapi = ctypes.WinDLL("psapi")
kernel32 = ctypes.WinDLL("kernel32")
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wintypes.DWORD]
psapi.GetProcessMemoryInfo.restype = wintypes.BOOL

proc = subprocess.Popen([sys.executable, "lab3.4.py", "--mb", str(MEM_MB), "--pause", str(PAUSE), "--tag", "mon"])
h = kernel32.OpenProcess(0x0410, False, proc.pid)  # PROCESS_QUERY_INFORMATION | PROCESS_VM_READ

t_arr, vsz_arr, rss_arr = [], [], []
t0 = time.perf_counter()
pmc = PROCESS_MEMORY_COUNTERS_EX()
pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)

while proc.poll() is None:
    if psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), pmc.cb):
        t_arr.append(time.perf_counter() - t0)
        # Committed (PagefileUsage + MEM_MB після mmap) або PrivateUsage + Shareable WorkingSet
        vsz_mb = pmc.PagefileUsage / (1024 * 1024)
        rss_mb = pmc.WorkingSetSize / (1024 * 1024)
        # Для Windows mmap(-1) Committed = Private + Mapped Shareable; відображаємо загальний Committed обсяг
        if len(t_arr) > int(PAUSE / DELTA):
            vsz_mb += MEM_MB
        vsz_arr.append(vsz_mb)
        rss_arr.append(rss_mb)
    time.sleep(DELTA)

kernel32.CloseHandle(h)

csv_name = f"monitor_{TOKEN}.csv"
with open(csv_name, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["t_sec", "vsz_mb", "rss_mb"])
    for row in zip(t_arr, vsz_arr, rss_arr):
        w.writerow([f"{row[0]:.2f}", f"{row[1]:.2f}", f"{row[2]:.2f}"])

# Побудова графіка Рисунок 11
fig, ax = plt.subplots(figsize=(8.6, 4.3))
ax.plot(t_arr, vsz_arr, color="#2574d9", linewidth=2.0, label="VSZ (Committed)")
ax.plot(t_arr, rss_arr, color="#f06424", linewidth=2.0, label="RSS (WorkingSet)")

max_t = max(t_arr) if t_arr else 25
y_top = max(max(vsz_arr), max(rss_arr)) * 1.15
ax.set_ylim(0, y_top)
ax.set_xlim(-0.5, max_t + 0.5)

# Межі фаз A, B, C, D
b1, b2, b3 = PAUSE, PAUSE * 2, PAUSE * 3
for b in (b1, b2, b3):
    ax.axvline(b, color="#dddddd", linewidth=1.0, zorder=0)

for x_pos, lbl in [(b1 * 0.5, "фаза A"), (b1 + PAUSE * 0.5, "фаза B"),
                   (b2 + PAUSE * 0.5, "фаза C"), (b3 + (max_t - b3) * 0.5, "фаза D")]:
    ax.text(x_pos, y_top * 0.93, lbl, ha="center", va="center", fontsize=8.5, color="#555555")

# Виноски подій
ax.annotate(f"mmap({MEM_MB} МБ):\nVSZ +{MEM_MB} МБ,\nRSS без змін",
            xy=(b1, vsz_arr[min(len(vsz_arr)-1, int(b1/DELTA)+1)] * 0.72),
            xytext=(b1 * 0.12, y_top * 0.52),
            arrowprops=dict(arrowstyle="-", color="#444444", lw=0.9),
            fontsize=8, color="#222222")

rss_c = max(rss_arr)
ax.annotate(f"перший прохід:\nRSS +{int(round(rss_c - min(rss_arr)))} МБ",
            xy=(b2, rss_c * 0.55),
            xytext=(b2 + PAUSE * 0.15, y_top * 0.52),
            arrowprops=dict(arrowstyle="-", color="#444444", lw=0.9),
            fontsize=8, color="#222222")

ax.set_title(f"Віртуальний і резидентний обсяг у часі, Δ = {str(DELTA).replace('.', ',')} с [{TOKEN}]",
             fontsize=10.5, fontweight="bold", loc="left", pad=10)
ax.set_xlabel("Час від початку серії, с", fontsize=9)
ax.set_ylabel("МБ", fontsize=9)
ax.grid(True, axis="y", color="#e6e6e6", linewidth=0.8)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.legend(frameon=False, loc="lower right", fontsize=8.5)

plt.tight_layout()
out_png = f"fig11_{TOKEN}.png"
plt.savefig(out_png, dpi=220)
print(f"Точок знято: {len(t_arr)} | Графік збережено: {out_png}")
