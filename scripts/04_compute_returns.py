"""
Step 4: compute daily log returns, in two versions.

Does:
  - RAW version: r_t = ln(P_t / P_{t-1}) taken across consecutive rows of the
    1,250-day intersection panel (drops the first row), plus a gap_days
    column recording how many calendar days each row actually spans.
  - CLEAN version: for each ticker, computes its own single-session log
    return on its own native trading calendar first (US tickers relabeled
    +1 business day to match the panel's alignment), then reindexes to the
    full 1,251-date panel. This is the primary analysis input used by every
    later step.
  - Diff report: how many cells differ between RAW and CLEAN on their shared
    dates, and by how much.

Input:  data/raw/raw_adjclose.csv
        data/processed/panel_15co_usshift_intersection.csv
Output: data/processed/panel_15co_returns_raw.csv     (1,249 x 16, incl. gap_days)
        data/processed/panel_15co_returns_clean.csv   (1,251 x 15)
        data/processed/raw_vs_clean_full_diff.csv
"""
import os
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROCESSED = os.path.join(ROOT, "data", "processed")

US = ["AMKR", "INTC"]
BDAY = pd.tseries.offsets.BDay(1)

panel_full = pd.read_csv(os.path.join(PROCESSED, "panel_15co_usshift_intersection.csv"),
                          index_col=0, parse_dates=True).sort_index()
panel_full.index = pd.DatetimeIndex(panel_full.index).normalize()
cols = list(panel_full.columns)

full = pd.read_csv(os.path.join(RAW, "raw_adjclose.csv"), index_col=0, parse_dates=True).sort_index()
full.index = pd.DatetimeIndex(full.index).normalize()

us_early = pd.read_csv(os.path.join(RAW, "us_early_history.csv"), index_col=0, parse_dates=True).sort_index()
us_early.index = pd.DatetimeIndex(us_early.index).normalize()
full = full.reindex(full.index.union(us_early.index)).sort_index()
for c in US:
    full[c] = us_early[c].combine_first(full[c]) if c in us_early.columns else full[c]

# ================= RAW version (1,250-day basis) =================
panel_1250 = panel_full.iloc[:-1]
idx_1250 = panel_1250.index
lr = np.log(panel_1250 / panel_1250.shift(1))
gap_days = idx_1250.to_series().diff().dt.days
raw_out = lr.iloc[1:].copy()
raw_out.insert(0, "gap_days", gap_days.iloc[1:].astype(int).values)
raw_out.index.name = "date"
raw_out.to_csv(os.path.join(PROCESSED, "panel_15co_returns_raw.csv"))
print(f"saved panel_15co_returns_raw.csv    shape={raw_out.shape}")

# ================= CLEAN version (full 1,251-date panel) =================
idx_full = panel_full.index
clean = pd.DataFrame(index=idx_full)
for c in cols:
    if c in US:
        s = full[c].dropna()
        r = np.log(s / s.shift(1))
        r.index = r.index + BDAY
        r = r[~r.index.duplicated(keep="last")]
    else:
        s = full[c].dropna()
        r = np.log(s / s.shift(1))
    clean[c] = r.reindex(idx_full)
clean.index.name = "date"
clean.to_csv(os.path.join(PROCESSED, "panel_15co_returns_clean.csv"))
print(f"saved panel_15co_returns_clean.csv  shape={clean.shape}  NaN={int(clean.isna().sum().sum())}")

# ================= RAW vs CLEAN diff report (shared 1,249-row basis) =================
shared = raw_out.index
diff = (lr.loc[shared, cols] - clean.loc[shared, cols])
long_rows = []
for c in cols:
    d = diff[c]
    hit = d[d.abs() > 1e-6]
    for dt, v in hit.items():
        long_rows.append(dict(date=dt, ticker=c, raw_minus_clean=v,
                               gap_days=int(gap_days.loc[dt]) if dt in gap_days.index else raw_out.loc[dt, "gap_days"]))
diff_df = pd.DataFrame(long_rows).sort_values(["date", "ticker"]).reset_index(drop=True)
diff_df.to_csv(os.path.join(PROCESSED, "raw_vs_clean_full_diff.csv"), index=False)
print(f"saved raw_vs_clean_full_diff.csv    rows={len(diff_df)}")
