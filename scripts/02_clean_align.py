"""
Step 2: align the 15-company panel across five market calendars.

Does:
  - Drops Shinko (6967.T, delisted, kept only in raw data for transparency).
  - Relabels the two US tickers (AMKR, INTC) +1 business day, so a US session
    shares a panel row with the Asian session it can first influence.
  - Takes the common-date intersection across all 15 remaining tickers.

Input:  data/raw/raw_adjclose.csv
Output: data/processed/panel_15co_usshift_intersection.csv (1,251 rows x 15 cols)
"""
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROCESSED = os.path.join(ROOT, "data", "processed")
os.makedirs(PROCESSED, exist_ok=True)

US = ["AMKR", "INTC"]
SHINKO = "6967.T"

raw = pd.read_csv(os.path.join(RAW, "raw_adjclose.csv"), index_col=0, parse_dates=True).sort_index()
raw.index = pd.DatetimeIndex(raw.index).normalize()

non_shk = [c for c in raw.columns if c != SHINKO]


def shift_us(df):
    other = [c for c in df.columns if c not in US]
    us = df[[c for c in US if c in df.columns]].copy()
    us.index = pd.DatetimeIndex(us.index).normalize().shift(1, freq="B")
    us = us[~us.index.duplicated(keep="last")]
    return pd.concat([df[other], us], axis=1).sort_index()


shifted = shift_us(raw[non_shk])
idx = shifted.dropna(how="any").index
panel = shifted.reindex(idx)

panel.to_csv(os.path.join(PROCESSED, "panel_15co_usshift_intersection.csv"))
print(f"saved panel_15co_usshift_intersection.csv  shape={panel.shape}  "
      f"{idx.min().date()} -> {idx.max().date()}")
