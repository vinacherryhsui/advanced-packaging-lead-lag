"""
Step 3: flag China A-share limit-up / limit-down days.

Does:
  - Uses the 1,250-day intersection basis (panel through 2026-09-10, i.e. the
    intersection panel before its final 1-row extension) together with raw
    unadjusted OHLCV to compute each day's close-to-close return and intraday
    high/low vs. the prior close, for the 3 China A-share tickers.
  - Classifies each day as up_limit / down_limit / up_touch / down_touch /
    near_up / near_down / (no flag), using +/-9.85% as the limit threshold
    (China's +/-10% board limit, allowing for rounding) and +/-9.0% as the
    near-limit threshold. Flags only; no rows are dropped.

Input:  data/processed/panel_15co_usshift_intersection.csv
        data/raw/cn_raw_600584_SS.csv, cn_raw_002156_SZ.csv, cn_raw_002185_SZ.csv
Output: data/processed/cn_limit_days_all.csv          (every flagged day, all 3 tickers)
        data/processed/panel_15co_with_cn_flags.csv   (1,250 x 15 panel + 6 marker cols)
"""
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROCESSED = os.path.join(ROOT, "data", "processed")

CN = {"600584.SS": "JCET 長電科技", "002156.SZ": "Tongfu 通富微電", "002185.SZ": "Huatian 華天科技"}
LIMIT = 0.0985
NEAR = 0.090

panel = pd.read_csv(os.path.join(PROCESSED, "panel_15co_usshift_intersection.csv"),
                     index_col=0, parse_dates=True)
panel.index = pd.DatetimeIndex(panel.index).normalize()
panel = panel.iloc[:-1]  # 1,250-day basis (drop the final extended row)
panel_idx = panel.index

all_rows = []
marks = pd.DataFrame(index=panel_idx)

for tkr, name in CN.items():
    df = pd.read_csv(os.path.join(RAW, f"cn_raw_{tkr.replace('.', '_')}.csv"),
                      index_col=0, parse_dates=True).sort_index()
    df.index = pd.DatetimeIndex(df.index).normalize()

    prev_close = df["Close"].shift(1)
    ret = df["Close"] / prev_close - 1.0
    high_pct = df["High"] / prev_close - 1.0
    low_pct = df["Low"] / prev_close - 1.0
    gap_days = df.index.to_series().diff().dt.days

    def classify(r, hp, lp):
        tags = []
        if r >= LIMIT:
            tags.append("up_limit")
        elif r <= -LIMIT:
            tags.append("down_limit")
        else:
            if hp >= LIMIT:
                tags.append("up_touch")
            if lp <= -LIMIT:
                tags.append("down_touch")
            if not tags:
                if NEAR <= r < LIMIT:
                    tags.append("near_up")
                elif -LIMIT < r <= -NEAR:
                    tags.append("near_down")
        return "+".join(tags)

    flag = pd.Series([classify(r, hp, lp) for r, hp, lp in zip(ret, high_pct, low_pct)], index=df.index)
    flagged = flag[flag != ""]

    sub = pd.DataFrame({
        "ticker": tkr, "name": name,
        "prev_close": prev_close.reindex(flagged.index).round(2),
        "close": df["Close"].reindex(flagged.index).round(2),
        "ret_pct": (ret.reindex(flagged.index) * 100).round(2),
        "high_pct": (high_pct.reindex(flagged.index) * 100).round(2),
        "low_pct": (low_pct.reindex(flagged.index) * 100).round(2),
        "gap_days": gap_days.reindex(flagged.index).astype("Int64"),
        "flag": flagged.values,
        "in_panel": flagged.index.isin(panel_idx),
    })
    all_rows.append(sub)

    marks[f"{tkr}__ret_pct"] = (ret.reindex(panel_idx) * 100).round(2)
    marks[f"{tkr}__limit"] = flag.reindex(panel_idx).fillna("")

flags = pd.concat(all_rows).sort_index()
flags.index.name = "date"
flags.to_csv(os.path.join(PROCESSED, "cn_limit_days_all.csv"))

panel_out = panel.join(marks)
panel_out.to_csv(os.path.join(PROCESSED, "panel_15co_with_cn_flags.csv"))

print(f"saved cn_limit_days_all.csv          rows={len(flags)}")
print(f"saved panel_15co_with_cn_flags.csv   shape={panel_out.shape}")
