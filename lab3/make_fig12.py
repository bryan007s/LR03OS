# -*- coding: utf-8 -*-
import matplotlib.pyplot as plt

TOKEN = "LAB3-18-88"
blocks = [512, 4096, 65536, 1048576]

# Ваші точні виміри з Таблиці 17
buf_med = [2.2, 3.1, 17.3, 238.5]
buf_p99 = [13.6, 16.2, 41.1, 483.1]
fsync_med = [540.4, 540.3, 552.7, 1231.3]
fsync_p99 = [724.9, 893.6, 717.9, 2560.9]

buf_mbps = [131.1, 445.6, 1057.1, 1634.5]
fsync_mbps = [0.9, 6.9, 110.9, 789.6]

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.4, 4.3))
fig.suptitle(f"Запис: затримка та пропускна здатність від розміру блоку [{TOKEN}]",
             fontsize=10, fontweight="bold", x=0.38, y=0.97)

# Лівий графік: затримка (медіана та p99)
ax1.loglog(blocks, buf_med, "-o", color="#2574d9", markersize=4.5, linewidth=1.6, label="buffered: медіана")
ax1.loglog(blocks, buf_p99, "--s", color="#5a9bf0", markersize=4.0, linewidth=1.3, label="buffered: p99")
ax1.loglog(blocks, fsync_med, "-o", color="#f06424", markersize=4.5, linewidth=1.6, label="fsync: медіана")
ax1.loglog(blocks, fsync_p99, "--s", color="#f59264", markersize=4.0, linewidth=1.3, label="fsync: p99")

ax1.set_xlabel("Розмір блоку, Б (log)", fontsize=8.5)
ax1.set_ylabel("Затримка запису, мкс (log)", fontsize=8.5)
ax1.grid(True, which="major", color="#e6e6e6", linewidth=0.8)
ax1.legend(frameon=False, fontsize=7.8, loc="center left")
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)

# Правий графік: пропускна здатність (МіБ/с)
ax2.loglog(blocks, buf_mbps, "-o", color="#2574d9", markersize=4.5, linewidth=1.6, label="buffered")
ax2.loglog(blocks, fsync_mbps, "-o", color="#f06424", markersize=4.5, linewidth=1.6, label="fsync")

ax2.set_xlabel("Розмір блоку, Б (log)", fontsize=8.5)
ax2.set_ylabel("Пропускна здатність, МіБ/с (log)", fontsize=8.5)
ax2.grid(True, which="major", color="#e6e6e6", linewidth=0.8)
ax2.legend(frameon=False, fontsize=8, loc="upper left")
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)

plt.tight_layout(rect=[0, 0, 1, 0.93])
out_png = f"fig12_{TOKEN}.png"
plt.savefig(out_png, dpi=220)
print(f"Графік збережено: {out_png}")
