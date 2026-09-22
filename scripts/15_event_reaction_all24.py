"""
Step 15: event-triggered reaction analysis, all 24 core edges.

Does:
  - Defines a leader's trigger day as |daily log return| >= 1.5x its own
    trailing 60-day standard deviation (excluding the trigger day itself).
  - For each edge, computes the follower's forward cumulative return at
    1/3/5/10-day horizons after each of the leader's trigger days (pooled,
    full 6-year sample): mean, one-sample t-test, win rate.
  - Splits triggers at 2023-09-01 and re-runs the 10-day test independently
    in each half, classifying each edge as fully stable / front-half-only /
    back-half-only / not stable.

Input:  data/processed/panel_15co_returns_clean.csv (full panel)
        data/results/granger/granger_significant_links_intra_asia.csv
Output: data/results/event_analysis/all24_pooled.csv
        data/results/event_analysis/all24_split.csv
        data/results/event_analysis/all24_master_table.csv
"""
import os
import sys
import numpy as np
import pandas as pd
from scipy import stats

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
GRANGER = os.path.join(ROOT, "data", "results", "granger")
EVENT = os.path.join(ROOT, "data", "results", "event_analysis")

NAMES = {
    "2330.TW": "台積電", "3711.TW": "日月光", "6239.TW": "力成", "2449.TW": "京元電子",
    "3264.TWO": "欣銓", "3037.TW": "欣興", "8046.TW": "南電", "3189.TW": "景碩",
    "4062.T": "Ibiden", "005930.KS": "三星", "600584.SS": "長電科技",
}
HORIZONS = [1, 3, 5, 10]
SPLIT = pd.Timestamp("2023-09-01")
ALPHA = 0.05

sig = pd.read_csv(os.path.join(GRANGER, "granger_significant_links_intra_asia.csv"))
EDGES = []
for r in sig.itertuples():
    a, b = r.dir1.split("->")
    EDGES.append((a, b))
    if r.type == "bidirectional":
        c, d = r.dir2.split("->")
        EDGES.append((c, d))

clean = pd.read_csv(os.path.join(PROCESSED, "panel_15co_returns_clean.csv"),
                     index_col=0, parse_dates=True).sort_index()
n = len(clean)
dates = clean.index

leaders = sorted(set(l for l, f in EDGES))
roll_std = {L: clean[L].shift(1).rolling(60).std() for L in leaders}
trigger_positions = {L: np.where((clean[L].abs() >= 1.5 * roll_std[L]).values)[0] for L in leaders}


def cum_fwd(series, pos, horizon):
    start, end = pos + 1, pos + horizon
    if end >= n:
        return np.nan
    return series.iloc[start:end + 1].sum()


def stats_for(positions, follower, horizon):
    fseries = clean[follower]
    vals = np.array([cum_fwd(fseries, p, horizon) for p in positions])
    vals = vals[~np.isnan(vals)]
    if len(vals) == 0:
        return dict(n=0, mean=np.nan, t=np.nan, p=np.nan, winrate=np.nan)
    t, p = stats.ttest_1samp(vals, 0.0)
    return dict(n=len(vals), mean=vals.mean(), t=t, p=p, winrate=(vals > 0).mean())


pooled_rows = []
for leader, follower in EDGES:
    rec = dict(leader=leader, leader_name=NAMES[leader], follower=follower, follower_name=NAMES[follower])
    for h in HORIZONS:
        s = stats_for(trigger_positions[leader], follower, h)
        rec[f"n_{h}d"], rec[f"mean_{h}d"], rec[f"t_{h}d"], rec[f"p_{h}d"], rec[f"winrate_{h}d"] = \
            s["n"], s["mean"], s["t"], s["p"], s["winrate"]
    pooled_rows.append(rec)
pooled = pd.DataFrame(pooled_rows)
pooled.to_csv(os.path.join(EVENT, "all24_pooled.csv"), index=False, encoding="utf-8")

split_rows = []
for leader, follower in EDGES:
    pos_all = trigger_positions[leader]
    pos1 = pos_all[dates[pos_all] < SPLIT]
    pos2 = pos_all[dates[pos_all] >= SPLIT]
    s1 = stats_for(pos1, follower, 10)
    s2 = stats_for(pos2, follower, 10)
    sig1 = (s1["p"] < ALPHA) if s1["n"] else False
    sig2 = (s2["p"] < ALPHA) if s2["n"] else False
    if sig1 and sig2:
        cls = "全期間穩定"
    elif sig2 and not sig1:
        cls = "僅後半段"
    elif sig1 and not sig2:
        cls = "僅前半段"
    else:
        cls = "兩段均不顯著"
    split_rows.append(dict(
        leader=leader, leader_name=NAMES[leader], follower=follower, follower_name=NAMES[follower],
        n1=s1["n"], t1=s1["t"], p1=s1["p"], n2=s2["n"], t2=s2["t"], p2=s2["p"], classification=cls,
    ))
split = pd.DataFrame(split_rows)
split.to_csv(os.path.join(EVENT, "all24_split.csv"), index=False, encoding="utf-8")

merged = pooled.merge(
    split[["leader", "follower", "n1", "t1", "p1", "n2", "t2", "p2", "classification"]],
    on=["leader", "follower"])
merged.to_csv(os.path.join(EVENT, "all24_master_table.csv"), index=False, encoding="utf-8")

print(split["classification"].value_counts().to_string())
