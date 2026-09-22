"""
Step 10: technical-analysis cross-check (RS, Momentum, RRG, Breadth vs TAIEX).

Does:
  - Fetches the TAIEX index (^TWII) and computes its own single-session log
    return, reindexed to the panel's dates.
  - Relative Strength: cumulative log return of each stock minus cumulative
    log return of TAIEX, over the full history.
  - Momentum: 20-day change in RS.
  - RRG coordinates: 60-day rolling z-score of RS and Momentum, sampled at
    each of the last 12 month-end dates, classified into 4 quadrants.
  - Breadth: % of constituents (overall, and per 4-tier supply-chain
    classification) trading above their own 60-day SMA.

Input:  data/processed/panel_15co_usshift_intersection.csv (full panel)
        data/processed/panel_15co_returns_clean.csv (full panel)
        (fetches ^TWII from Yahoo Finance)
Output: data/results/technical/rs_full_period.csv
        data/results/technical/momentum_full_period.csv
        data/results/technical/rrg_12month_trajectory.csv
        data/results/technical/breadth_full_period.csv
        data/results/technical/snapshot_RS_momentum_RRG.csv
"""
import os
import sys
import numpy as np
import pandas as pd
import yfinance as yf

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROCESSED = os.path.join(ROOT, "data", "processed")
TECH = os.path.join(ROOT, "data", "results", "technical")
os.makedirs(TECH, exist_ok=True)

NAMES = {
    "2330.TW": "TSMC 台積電", "3711.TW": "ASE 日月光", "6239.TW": "Powertech 力成",
    "2449.TW": "KYEC 京元電子", "3264.TWO": "Ardentec 欣銓", "3037.TW": "Unimicron 欣興",
    "8046.TW": "Nan Ya PCB 南電", "3189.TW": "Kinsus 景碩", "AMKR": "Amkor",
    "INTC": "Intel 英特爾", "600584.SS": "JCET 長電", "002156.SZ": "Tongfu 通富",
    "002185.SZ": "Huatian 華天", "005930.KS": "Samsung 三星", "4062.T": "Ibiden",
}
TIER = {
    "3711.TW": "T1_OSAT", "6239.TW": "T1_OSAT", "2449.TW": "T1_OSAT", "3264.TWO": "T1_OSAT",
    "600584.SS": "T1_OSAT", "002156.SZ": "T1_OSAT", "002185.SZ": "T1_OSAT", "AMKR": "T1_OSAT",
    "005930.KS": "T2_IDM", "INTC": "T2_IDM",
    "3037.TW": "T3_Substrate", "8046.TW": "T3_Substrate", "3189.TW": "T3_Substrate", "4062.T": "T3_Substrate",
    "2330.TW": "T4_TSMC",
}
TICKERS = list(NAMES.keys())

px = pd.read_csv(os.path.join(PROCESSED, "panel_15co_usshift_intersection.csv"),
                  index_col=0, parse_dates=True).sort_index()
ret = pd.read_csv(os.path.join(PROCESSED, "panel_15co_returns_clean.csv"),
                   index_col=0, parse_dates=True).sort_index()
print(f"px {px.shape} {px.index.min().date()}->{px.index.max().date()}   "
      f"ret {ret.shape} {ret.index.min().date()}->{ret.index.max().date()}")

twii = yf.Ticker("^TWII").history(start="2020-08-01", interval="1d", auto_adjust=True, actions=False)
twii.index = pd.DatetimeIndex(twii.index).tz_localize(None).normalize()
twii_close = twii["Close"].dropna()
twii_close = twii_close[~twii_close.index.duplicated(keep="last")]
twii_ret_native = np.log(twii_close / twii_close.shift(1)).dropna()
twii_ret = twii_ret_native.reindex(ret.index)
if twii_ret.isna().sum():
    twii_ret = twii_ret.fillna(0.0)

# ---- 1. Relative Strength ----
cum_stock = ret.cumsum()
cum_twii = twii_ret.cumsum()
RS = cum_stock.sub(cum_twii, axis=0)
RS.to_csv(os.path.join(TECH, "rs_full_period.csv"), encoding="utf-8")

# ---- 2. Momentum ----
MOM = RS - RS.shift(20)
MOM.to_csv(os.path.join(TECH, "momentum_full_period.csv"), encoding="utf-8")


# ---- 3. RRG ----
def rolling_z(s, window=60):
    m = s.rolling(window).mean()
    sd = s.rolling(window).std()
    return (s - m) / sd


RS_z = RS.apply(rolling_z)
MOM_z = MOM.apply(rolling_z)
month_ends = pd.Series(RS.index, index=RS.index).groupby(RS.index.to_period("M")).max()
last12 = month_ends.iloc[-12:]


def quadrant(rz, mz):
    if pd.isna(rz) or pd.isna(mz):
        return "NA"
    if rz >= 0 and mz >= 0:
        return "領先(Leading)"
    if rz >= 0 and mz < 0:
        return "轉弱(Weakening)"
    if rz < 0 and mz < 0:
        return "落後(Lagging)"
    return "轉強(Improving)"


rrg_rows = []
for t in TICKERS:
    for dt in last12:
        rz, mz = RS_z.loc[dt, t], MOM_z.loc[dt, t]
        rrg_rows.append(dict(ticker=t, name=NAMES[t], date=dt.date(),
                              RS_z=round(rz, 3) if pd.notna(rz) else np.nan,
                              Momentum_z=round(mz, 3) if pd.notna(mz) else np.nan,
                              quadrant=quadrant(rz, mz)))
pd.DataFrame(rrg_rows).to_csv(os.path.join(TECH, "rrg_12month_trajectory.csv"), index=False, encoding="utf-8")

# ---- 4. Breadth ----
sma60 = px.rolling(60).mean()
above = (px > sma60)
breadth_overall = above.sum(axis=1) / len(TICKERS)
tier_breadth = {}
for tier in sorted(set(TIER.values())):
    cols = [t for t in TICKERS if TIER[t] == tier]
    tier_breadth[tier] = above[cols].sum(axis=1) / len(cols)
tier_breadth_df = pd.DataFrame(tier_breadth)
tier_breadth_df.insert(0, "overall", breadth_overall)
tier_breadth_df.to_csv(os.path.join(TECH, "breadth_full_period.csv"), encoding="utf-8")

# ---- snapshot ----
latest = ret.index.max()
snap = pd.DataFrame({
    "ticker": TICKERS, "name": [NAMES[t] for t in TICKERS], "tier": [TIER[t] for t in TICKERS],
    "RS_latest": [RS.loc[latest, t] for t in TICKERS],
    "Momentum_latest(20d)": [MOM.loc[latest, t] for t in TICKERS],
    "RS_zscore_60d": [RS_z.loc[latest, t] for t in TICKERS],
    "Momentum_zscore_60d": [MOM_z.loc[latest, t] for t in TICKERS],
})
snap["quadrant"] = [quadrant(r, m) for r, m in zip(snap.RS_zscore_60d, snap.Momentum_zscore_60d)]
snap = snap.sort_values("RS_latest", ascending=False).reset_index(drop=True)
snap.to_csv(os.path.join(TECH, "snapshot_RS_momentum_RRG.csv"), index=False, encoding="utf-8")

print(f"saved rs_full_period.csv, momentum_full_period.csv, rrg_12month_trajectory.csv, "
      f"breadth_full_period.csv, snapshot_RS_momentum_RRG.csv  (as of {latest.date()})")
