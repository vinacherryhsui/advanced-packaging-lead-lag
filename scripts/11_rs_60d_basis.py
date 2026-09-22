"""
Step 11: 60-day relative-strength basis for the 3 highest-in-degree followers.

Does:
  - Takes the last 60 trading days of the CLEAN return panel.
  - For Ardentec, Nan Ya PCB and Kinsus, computes cumulative RS against both
    TSMC (primary leader) and Ibiden (secondary, high-noise reference).

Input:  data/processed/panel_15co_returns_clean.csv (full panel)
Output: data/results/technical/rs_60d_15way_basis.csv
"""
import os
import sys
import pandas as pd

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
TECH = os.path.join(ROOT, "data", "results", "technical")

LEADER_PRIMARY = "2330.TW"
LEADER_SECONDARY = "4062.T"
FOLLOWERS = ["3264.TWO", "8046.TW", "3189.TW"]

clean = pd.read_csv(os.path.join(PROCESSED, "panel_15co_returns_clean.csv"),
                     index_col=0, parse_dates=True).sort_index()

win = clean.iloc[-60:][[LEADER_PRIMARY, LEADER_SECONDARY] + FOLLOWERS]
cum = win.cumsum()
cum0 = pd.DataFrame(0.0, index=[win.index[0] - pd.tseries.offsets.BDay(1)], columns=cum.columns)
cum_full = pd.concat([cum0, cum])

rows = []
for F in FOLLOWERS:
    for L, label in [(LEADER_PRIMARY, "TSMC"), (LEADER_SECONDARY, "Ibiden")]:
        s = cum_full[F] - cum_full[L]
        for dt in cum_full.index:
            rows.append(dict(date=dt, follower=F, leader=label,
                              cum_ret_follower=cum_full.loc[dt, F],
                              cum_ret_leader=cum_full.loc[dt, L], RS=s.loc[dt]))
out = pd.DataFrame(rows)
out.to_csv(os.path.join(TECH, "rs_60d_15way_basis.csv"), index=False, encoding="utf-8")
print(f"saved rs_60d_15way_basis.csv  rows={len(out)}  window={win.index.min().date()}->{win.index.max().date()}")
