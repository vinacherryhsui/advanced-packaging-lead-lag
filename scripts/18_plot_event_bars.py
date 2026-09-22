"""
Step 18: plot split-sample event-reaction t-values for the 4 edges that are
stable in the event-reaction split test (Figure 2).

Does:
  - For the 4 edges classified "全期間穩定" in the event-reaction split
    (15_event_reaction_all24.py's output), plots front-half vs. back-half
    10-day cumulative-reaction t-values side by side, with the 5%
    significance threshold (t=1.99) marked.
  - This is a different stability test from the Granger split (07 /
    17_plot_network.py's red/orange/yellow/grey edge classification): here
    every bar is by construction "event-reaction stable"; the chart shows
    how much headroom each edge has above the significance threshold in
    each sub-period, not the 4-tier Granger-vs-event cross-classification.

Input:  data/results/event_analysis/all24_split.csv
Output: data/results/figures/fig2_event_bars.png (300 dpi)
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.lines import Line2D

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "data", "results")
FIGURES = os.path.join(RESULTS, "figures")
os.makedirs(FIGURES, exist_ok=True)

for cand in ["Microsoft JhengHei", "Microsoft YaHei", "SimHei", "Noto Sans CJK TC"]:
    hit = next((f for f in fm.fontManager.ttflist if f.name == cand), None)
    if hit:
        matplotlib.rcParams["font.family"] = fm.FontProperties(fname=hit.fname).get_name()
        break
matplotlib.rcParams["axes.unicode_minus"] = False

e = pd.read_csv(os.path.join(RESULTS, "event_analysis", "all24_split.csv"))

EDGES = [
    ("2330.TW", "3264.TWO", "台積電→欣銓"),
    ("2330.TW", "8046.TW", "台積電→南電"),
    ("2330.TW", "3711.TW", "台積電→日月光"),
    ("2449.TW", "3264.TWO", "京元電子→欣銓"),
]

t1_vals, t2_vals, labels = [], [], []
for leader, follower, label in EDGES:
    row = e[(e["leader"] == leader) & (e["follower"] == follower)].iloc[0]
    t1_vals.append(row["t1"])
    t2_vals.append(row["t2"])
    labels.append(label)

x = np.arange(len(labels))
width = 0.35

fig, ax = plt.subplots(figsize=(9, 6.5), dpi=300)
bars1 = ax.bar(x - width / 2, t1_vals, width, label="前半段 2020-09~2023-08", color="#2E5FA3")
bars2 = ax.bar(x + width / 2, t2_vals, width, label="後半段 2023-09~2026-09", color="#C0392B")

for b in list(bars1) + list(bars2):
    h = b.get_height()
    ax.text(b.get_x() + b.get_width() / 2, h + 0.08, f"{h:.2f}", ha="center", va="bottom", fontsize=9.5)

thresh = 1.99
ax.axhline(thresh, color="#555555", linestyle="--", linewidth=1.3, zorder=0)

ax.set_xticks(x)
ax.set_xticklabels(labels, fontsize=11)
ax.set_ylabel("事件反應 t 值（10日累積反應）", fontsize=11)
ax.set_title("事件反應分析：領先者觸發後10日累積反應t值", fontsize=14, fontweight="bold", pad=14)

handles, leg_labels = ax.get_legend_handles_labels()
handles.append(Line2D([0], [0], color="#555555", linestyle="--", linewidth=1.3))
leg_labels.append("5%顯著門檻 (約t=1.99)")
ax.legend(handles, leg_labels, loc="upper right", fontsize=9.5, frameon=True)

ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)
ax.set_ylim(0, max(t1_vals + t2_vals) * 1.2)

fig.text(0.5, 0.005, "資料來源：all24_split.csv", ha="center", fontsize=7.5, color="#555555")

plt.tight_layout(rect=[0, 0.03, 1, 1])
out_path = os.path.join(FIGURES, "fig2_event_bars.png")
plt.savefig(out_path, dpi=300, facecolor="white")
print(f"saved {out_path}")
