"""
Step 17: plot the 13-node intra-Asia lead-lag network (Figure 1).

Does:
  - Cross-references the 24 core directed edges against two independent
    split-sample stability tests: the Granger F-test split (07) and the
    event-reaction t-test split (15), classifying each edge into 4 tiers:
      1. intersection      -- stable in both tests
      2. granger_only      -- stable in the Granger split only
      3. event_only        -- stable in the event-reaction split only
      4. rest               -- FDR-significant core edge, stable in neither
  - Draws a manually laid out directed network: node size = out-degree,
    edge color/weight = tier above, TSMC and Ibiden visually distinguished
    (solid vs. dashed border) despite both having out-degree 7.

Input:  data/results/granger/split_sample_granger.csv
        data/results/event_analysis/all24_split.csv
        data/results/network/intra_asia_centrality.csv
Output: data/results/figures/fig1_network.png (300 dpi)
"""
import os
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.patches import FancyArrowPatch, Circle
from matplotlib.lines import Line2D

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "data", "results")
FIGURES = os.path.join(RESULTS, "figures")
os.makedirs(FIGURES, exist_ok=True)

# ---- Chinese font ----
for cand in ["Microsoft JhengHei", "Microsoft YaHei", "SimHei", "Noto Sans CJK TC"]:
    hit = next((f for f in fm.fontManager.ttflist if f.name == cand), None)
    if hit:
        matplotlib.rcParams["font.family"] = fm.FontProperties(fname=hit.fname).get_name()
        break
matplotlib.rcParams["axes.unicode_minus"] = False

NAMES = {
    "2330.TW": "台積電", "3711.TW": "日月光", "6239.TW": "力成", "2449.TW": "京元電子",
    "3264.TWO": "欣銓", "3037.TW": "欣興", "8046.TW": "南電", "3189.TW": "景碩",
    "600584.SS": "長電", "002156.SZ": "通富", "002185.SZ": "華天", "005930.KS": "三星", "4062.T": "Ibiden",
}

g = pd.read_csv(os.path.join(RESULTS, "granger", "split_sample_granger.csv"))
e = pd.read_csv(os.path.join(RESULTS, "event_analysis", "all24_split.csv"))
cent = pd.read_csv(os.path.join(RESULTS, "network", "intra_asia_centrality.csv"))

g_stable = set(zip(g.loc[g["classification"] == "全期間穩定(兩段FDR顯著)", "cause"],
                    g.loc[g["classification"] == "全期間穩定(兩段FDR顯著)", "effect"]))
e_stable = set(zip(e.loc[e["classification"] == "全期間穩定", "leader"],
                    e.loc[e["classification"] == "全期間穩定", "follower"]))
all_edges = list(zip(g["cause"], g["effect"]))

inter = g_stable & e_stable
only_g = g_stable - e_stable
only_e = e_stable - g_stable

outdeg = dict(zip(cent["ticker"], cent["out_degree"]))

# manual hierarchical layout: leaders on top, followers on bottom, isolates to the side
pos = {
    "2330.TW": (0.0, 3.0), "4062.T": (9.0, 3.0),
    "005930.KS": (1.7, 1.7), "3711.TW": (3.6, 1.7), "3037.TW": (5.4, 1.7),
    "2449.TW": (7.1, 1.7), "600584.SS": (10.6, 1.7),
    "6239.TW": (4.5, 0.5),
    "3264.TWO": (2.3, -0.8), "3189.TW": (4.5, -0.8), "8046.TW": (6.7, -0.8),
    "002156.SZ": (9.4, -0.8), "002185.SZ": (10.6, 0.2),
}


def edge_style(pair):
    if pair in inter:
        return dict(color="#8B0000", lw=3.6, alpha=0.95, z=5, arrow=16)
    elif pair in only_g:
        return dict(color="#E07B00", lw=2.3, alpha=0.9, z=4, arrow=13)
    elif pair in only_e:
        return dict(color="#D4B106", lw=2.3, alpha=0.9, z=4, arrow=13)
    else:
        return dict(color="#B0B0B0", lw=0.9, alpha=0.6, z=1, arrow=9)


def node_r(tkr):
    return 0.28 + 0.052 * outdeg.get(tkr, 0)


fig, ax = plt.subplots(figsize=(13, 9.6), dpi=300)
ax.set_xlim(-1.6, 12.2)
ax.set_ylim(-1.8, 3.8)
ax.axis("off")

edge_pairs = set(all_edges)
for (a, b) in all_edges:
    st = edge_style((a, b))
    rad = 0.15 if (b, a) in edge_pairs else 0.06
    patch = FancyArrowPatch(
        pos[a], pos[b], connectionstyle=f"arc3,rad={rad}", arrowstyle="-|>",
        mutation_scale=st["arrow"], shrinkA=node_r(a) * 72, shrinkB=node_r(b) * 72,
        color=st["color"], linewidth=st["lw"], alpha=st["alpha"], zorder=st["z"],
        capstyle="round",
    )
    ax.add_patch(patch)

for tkr, (x, y) in pos.items():
    r = node_r(tkr)
    if tkr == "2330.TW":
        face, edge, ls, lw = "#0B3D91", "#0B3D91", "solid", 1.5
    elif tkr == "4062.T":
        face, edge, ls, lw = "#5B8DEF", "#0B3D91", "dashed", 2.2
    elif outdeg.get(tkr, 0) == 0:
        face, edge, ls, lw = "#D9E4F5", "#7A8AA0", "solid", 1.2
    else:
        face, edge, ls, lw = "#8FAADC", "#4A6FA5", "solid", 1.2
    ax.add_patch(Circle((x, y), r, facecolor=face, edgecolor=edge, linewidth=lw, linestyle=ls, zorder=10))
    label_color = "white" if tkr in ("2330.TW", "4062.T") else "black"
    ax.text(x, y + 0.02, NAMES[tkr], ha="center", va="center", fontsize=11,
            fontweight="bold", color=label_color, zorder=11)
    ax.text(x, y - r - 0.16, f"{tkr}\nout={outdeg.get(tkr, 0)}", ha="center", va="top",
            fontsize=8, color="#333333", zorder=11)

legend_elems = [
    Line2D([0], [0], color="#8B0000", lw=3.6, label="交集（2條）"),
    Line2D([0], [0], color="#E07B00", lw=2.3, label="僅Granger本身穩定（7條）"),
    Line2D([0], [0], color="#D4B106", lw=2.3, label="僅事件反應穩定（2條）"),
    Line2D([0], [0], color="#B0B0B0", lw=0.9, label="其餘核心關係（13條）"),
]
ax.legend(handles=legend_elems, loc="lower center", bbox_to_anchor=(0.5, -0.10), ncol=2,
          fontsize=9.5, frameon=True)

fig.suptitle("13個intra-Asia節點之核心領先-落後網絡", fontsize=15, fontweight="bold", y=0.97)
fig.text(0.5, 0.935, "節點大小＝out-degree", ha="center", fontsize=10, color="#333333")
fig.text(0.5, 0.008, "資料來源：granger/split_sample_granger.csv ＋ event_analysis/all24_split.csv",
         ha="center", fontsize=7, color="#777777")

plt.tight_layout(rect=[0, 0.02, 1, 0.92])
out_path = os.path.join(FIGURES, "fig1_network.png")
plt.savefig(out_path, dpi=300, facecolor="white")
print(f"saved {out_path}")
print(f"  intersection={len(inter)}  granger_only={len(only_g)}  event_only={len(only_e)}  "
      f"rest={len(all_edges) - len(inter) - len(only_g) - len(only_e)}")
