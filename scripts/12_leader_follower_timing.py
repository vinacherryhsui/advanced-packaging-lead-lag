"""
Step 12: leader-jump vs. follower-RS-peak timing, at a 2-standard-deviation
threshold, across all 24 core edges.

Does:
  - Takes the last 60 trading days of the CLEAN return panel.
  - For each edge's follower, finds the date its RS (cumulative return vs.
    that specific leader) peaks within the window.
  - For each edge's leader, flags any day where its own return deviates from
    its own 60-day mean by at least 2 standard deviations ("significant
    jump").
  - Classifies each edge by comparing the follower's RS-peak date to the
    leader's most recent qualifying jump at or before that peak (+/-1 day =
    concurrent; no qualifying jump at all = anomalous).

Input:  data/processed/panel_15co_returns_clean.csv (full panel)
        data/results/granger/granger_significant_links_intra_asia.csv
Output: data/results/network/leader_follower_timing_2sd.csv
"""
import os
import sys
import numpy as np
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
GRANGER = os.path.join(ROOT, "data", "results", "granger")
NETWORK = os.path.join(ROOT, "data", "results", "network")

NAMES = {
    "2330.TW": "TSMC 台積電", "3711.TW": "ASE 日月光", "6239.TW": "Powertech 力成",
    "2449.TW": "KYEC 京元電子", "3264.TWO": "Ardentec 欣銓", "3037.TW": "Unimicron 欣興",
    "8046.TW": "Nan Ya PCB 南電", "3189.TW": "Kinsus 景碩", "600584.SS": "JCET 長電",
    "005930.KS": "Samsung 三星", "4062.T": "Ibiden",
}

df = pd.read_csv(os.path.join(GRANGER, "granger_significant_links_intra_asia.csv"))
edges = []
for r in df.itertuples():
    a, b = r.dir1.split("->")
    edges.append((a, b))
    if r.type == "bidirectional":
        c, d = r.dir2.split("->")
        edges.append((c, d))

clean = pd.read_csv(os.path.join(PROCESSED, "panel_15co_returns_clean.csv"),
                     index_col=0, parse_dates=True).sort_index()
tickers = sorted(set([e[0] for e in edges] + [e[1] for e in edges]))
win = clean.iloc[-60:][tickers]
cum = win.cumsum()
cum0 = pd.DataFrame(0.0, index=[win.index[0] - pd.tseries.offsets.BDay(1)], columns=cum.columns)
cum_full = pd.concat([cum0, cum])
dates = list(cum_full.index)
day_index = {dt: i for i, dt in enumerate(dates)}

leaders = sorted(set(e[0] for e in edges))
jump_info = {}
for L in leaders:
    r = win[L]
    mu, sd = r.mean(), r.std()
    thresh = 2 * sd
    jump_info[L] = r[(r - mu).abs() >= thresh]

rows = []
for leader, follower in edges:
    rs = cum_full[follower] - cum_full[leader]
    peak_date = rs.idxmax()
    peak_idx = day_index[peak_date]
    peak_val = rs.loc[peak_date]

    flagged = jump_info[leader]
    if len(flagged) == 0:
        order = "領先者整個窗口無顯著跳空(2sd)"
        ref_jump_date, ref_jump_pct, diff = None, None, np.nan
    else:
        prior = flagged[[day_index[d] <= peak_idx + 1 for d in flagged.index]]
        if len(prior) == 0:
            next_jump = flagged.index.min()
            diff = peak_idx - day_index[next_jump]
            order = "⚠跟隨者先(異常): 高點前領先者無任何顯著跳空"
            ref_jump_date, ref_jump_pct = next_jump, flagged.loc[next_jump]
        else:
            ref_jump_date = prior.index.max()
            ref_jump_pct = prior.loc[ref_jump_date]
            diff = peak_idx - day_index[ref_jump_date]
            order = "同步" if diff <= 1 else "領先者先"
    rows.append(dict(
        leader=leader, leader_name=NAMES[leader], follower=follower, follower_name=NAMES[follower],
        follower_RS_peak_date=peak_date.date(), follower_RS_peak_pct=round(peak_val * 100, 2),
        leader_ref_jump_date=ref_jump_date.date() if ref_jump_date is not None else None,
        leader_ref_jump_pct=round(ref_jump_pct * 100, 2) if ref_jump_pct is not None else None,
        day_diff_peak_minus_jump=diff, n_leader_jumps_total=len(flagged), order=order,
    ))

out = pd.DataFrame(rows).sort_values(["order", "leader", "follower"])
out.to_csv(os.path.join(NETWORK, "leader_follower_timing_2sd.csv"), index=False, encoding="utf-8")
print(out["order"].value_counts().to_string())
