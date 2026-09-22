"""
Step 1: fetch raw price data from Yahoo Finance.

Does:
  - Fetches daily adjusted close for 16 tickers (15 core supply-chain companies
    + Shinko, which is delisted and kept only for transparency), 2020-09-01
    through 2026-09-11.
  - Fetches raw (unadjusted) daily OHLCV for the 3 China A-share tickers
    (needed later for limit-up/limit-down detection, which must use
    unadjusted prices).
  - Separately fetches AMKR/INTC native-calendar closes back to 2020-08-01:
    computing each ticker's own single-session return on 2020-09-01 (the US
    native date that maps to the panel's first date, 2020-09-02) needs its
    prior session's close, which the main fetch does not cover.

Input:  none (hits the network).
Output: data/raw/raw_adjclose.csv        (1,570 rows x 16 tickers, from 2020-09-01)
        data/raw/us_early_history.csv    (AMKR, INTC closes, 2020-08-03 to 2020-09-01)
        data/raw/cn_raw_600584_SS.csv
        data/raw/cn_raw_002156_SZ.csv
        data/raw/cn_raw_002185_SZ.csv

Note: re-running this script hits Yahoo Finance live. Adjusted-close values
for past dates can be revised over time (e.g. after dividend reclassification),
so a fresh run may not be bit-identical to the shipped data/raw/ files. The
shipped files are the exact data used to produce every number in this
repository's results/ and REPRODUCE.md.
"""
import os
import sys
import time
import pandas as pd
import yfinance as yf

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW, exist_ok=True)

TICKERS = [
    "2330.TW", "3711.TW", "6239.TW", "2449.TW", "3264.TWO", "3037.TW",
    "8046.TW", "3189.TW", "AMKR", "INTC", "600584.SS", "002156.SZ",
    "002185.SZ", "005930.KS", "4062.T", "6967.T",
]
CN_RAW_TICKERS = ["600584.SS", "002156.SZ", "002185.SZ"]

START = "2020-09-01"
END = "2026-09-12"  # yfinance end is exclusive; this includes 2026-09-11


def fetch_adjclose(tkr, tries=4):
    for i in range(tries):
        try:
            df = yf.Ticker(tkr).history(start=START, end=END, interval="1d",
                                         auto_adjust=True, actions=False)
            if df is not None and len(df) > 0:
                s = df["Close"].copy()
                s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
                return s[~s.index.duplicated(keep="last")].rename(tkr)
        except Exception as e:
            print(f"  {tkr} attempt {i + 1} failed: {e}", file=sys.stderr)
        time.sleep(8 + 6 * i)
    return pd.Series(dtype="float64", name=tkr)


def fetch_raw_ohlcv(tkr, tries=4):
    for i in range(tries):
        try:
            df = yf.Ticker(tkr).history(start=START, end=END, interval="1d",
                                         auto_adjust=False, actions=True)
            if df is not None and len(df) > 0:
                df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
                return df[~df.index.duplicated(keep="last")]
        except Exception as e:
            print(f"  {tkr} attempt {i + 1} failed: {e}", file=sys.stderr)
        time.sleep(8 + 6 * i)
    return None


print("Fetching adjusted close for 16 tickers...")
series = {}
for tkr in TICKERS:
    s = fetch_adjclose(tkr)
    series[tkr] = s
    print(f"  {tkr:12s} n={len(s):5d}" + (f"  {s.index.min().date()} -> {s.index.max().date()}" if len(s) else "  NO DATA"))
    time.sleep(2)

raw = pd.concat(series.values(), axis=1).sort_index()
raw.to_csv(os.path.join(RAW, "raw_adjclose.csv"))
print(f"saved raw_adjclose.csv  shape={raw.shape}")

print("\nFetching AMKR/INTC early native-calendar history (2020-08-01 to 2020-09-01)...")
early = {}
for t in ["AMKR", "INTC"]:
    df = yf.Ticker(t).history(start="2020-08-01", end="2020-09-02", interval="1d",
                               auto_adjust=True, actions=False)
    s = df["Close"].copy()
    s.index = pd.to_datetime(s.index).tz_localize(None).normalize()
    early[t] = s[~s.index.duplicated(keep="last")]
    time.sleep(2)
early_df = pd.DataFrame(early).sort_index()
early_df.index.name = "Date"
early_df.to_csv(os.path.join(RAW, "us_early_history.csv"))
print(f"saved us_early_history.csv  shape={early_df.shape}")

print("\nFetching raw OHLCV for 3 China A-share tickers...")
for tkr in CN_RAW_TICKERS:
    df = fetch_raw_ohlcv(tkr)
    if df is None:
        print(f"  {tkr}: FAILED")
        continue
    keep = [c for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume",
                         "Dividends", "Stock Splits"] if c in df.columns]
    fn = os.path.join(RAW, f"cn_raw_{tkr.replace('.', '_')}.csv")
    df[keep].to_csv(fn)
    print(f"  {tkr:12s} n={len(df)}  {df.index.min().date()} -> {df.index.max().date()}  saved {os.path.basename(fn)}")
    time.sleep(2)
