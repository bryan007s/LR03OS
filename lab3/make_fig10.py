# -*- coding: utf-8 -*-
import csv, statistics
import numpy as np
import matplotlib.pyplot as plt

TOKEN = "LAB3-18-88"
TAGS = [("основний", "main"), ("manual1", "manual1"), ("manual2", "manual2")]

print("\n=== ДАНІ ДЛЯ ТАБЛИЦІ 10 ===")
print(f"{'Запуск':<10} | {'Δ faults C':>10} | {'Δ faults D':>10} | {'RSS після C, КБ':>15} | {'Медіана pass1':>13} | {'Медіана pass2':>13} | {'pass1-pass2':>11}")
for label, tag in TAGS:
    with open(f"phases_{tag}_{TOKEN}.csv", encoding="utf-8") as f:
        ph = {r["phase"]: r for r in csv.DictReader(f)}
    with open(f"pages_{tag}_{TOKEN}.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    w = int(0.05 * len(rows))
    p1 = [float(r["pass1_ns"]) for r in rows[w:]]
    p2 = [float(r["pass2_ns"]) for r in rows[w:]]
    m1, m2 = int(statistics.median(p1)), int(statistics.median(p2))
    print(f"{label:<10} | {ph['C']['delta_faults']:>10} | {ph['D']['delta_faults']:>10} | {ph['C']['rss_kb']:>15} | {m1:>13} | {m2:>13} | {m1 - m2:>11}")

with open(f"pages_main_{TOKEN}.csv", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
total_pages = len(rows)
w = int(0.05 * total_pages)
p1_all = np.array([float(r["pass1_ns"]) for r in rows[w:]])
p2_all = np.array([float(r["pass2_ns"]) for r in rows[w:]])

print(f"\n=== ДАНІ ДЛЯ ТАБЛИЦІ 11 (всього {total_pages} стор., відкинуто {w}) ===")
for name, arr in [("pass1 (перший дотик)", p1_all), ("pass2 (повторний дотик)", p2_all)]:
    print(f"{name:<24} | N={len(arr)} | min={np.min(arr):.0f} | медіана={np.median(arr):.0f} | "
          f"середнє={np.mean(arr):.0f} | p95={np.percentile(arr, 95):.0f} | p99={np.percentile(arr, 99):.0f} | max={np.max(arr):.0f}")

# Побудова Рисунка 10
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.5, 4.2), gridspec_kw={"width_ratios": [1.55, 1]})
fig.suptitle(f"Перший і повторний дотик до сторінок, {total_pages} стор. [{TOKEN}]", fontsize=10, fontweight="bold", x=0.38, y=0.97)

p1_pos = p1_all[p1_all > 0]
p2_pos = p2_all[p2_all > 0]
bins = np.logspace(np.log10(80), np.log10(max(p1_pos.max(), p2_pos.max()) * 1.1), 36)

ax1.hist(p1_pos, bins=bins, color="#4885d4", edgecolor="white", linewidth=0.4, label="pass1 (перший дотик)")
ax1.hist(p2_pos, bins=bins, color="#ef7d4b", edgecolor="white", linewidth=0.4, alpha=0.9, label="pass2 (повторний)")
ax1.set_xscale("log")
ax1.set_yscale("log")
ax1.set_xlabel("Час запису 1 байта в сторінку, нс (log)", fontsize=8.5)
ax1.set_ylabel("Кількість сторінок (log)", fontsize=8.5)
ax1.grid(True, which="major", linestyle="-", alpha=0.25)
ax1.legend(frameon=False, fontsize=8, loc="upper right")
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)

bp = ax2.boxplot([p1_pos, p2_pos], tick_labels=["pass1", "pass2"], showfliers=False, patch_artist=True, widths=0.22)
for patch, color in zip(bp["boxes"], ["#4885d4", "#ef7d4b"]):
    patch.set_facecolor(color)
    patch.set_edgecolor("#222222")
for median in bp["medians"]:
    median.set_color("#111111")
    median.set_linewidth(1.5)
ax2.set_yscale("log")
ax2.set_ylabel("нс (log), без викидів", fontsize=8.5)
ax2.grid(True, which="major", linestyle="-", alpha=0.25)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

plt.tight_layout(rect=[0, 0, 1, 0.93])
out_png = f"fig10_{TOKEN}.png"
plt.savefig(out_png, dpi=220)
print(f"\n-> Графік збережено у файл: {out_png}")
