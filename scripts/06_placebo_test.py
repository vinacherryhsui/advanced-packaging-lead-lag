"""
Step 6: timezone-alignment placebo test for the 54 US-touching directional tests.

Does:
  - Rebuilds the single-session return panel under three date-alignment
    conventions for the two US tickers (AMKR, INTC) only -- the 13 non-US
    series are never shifted:
      A: US label = native date + 1 business day  (headline convention)
      B: US label = native date - 1 business day  (reverse placebo)
      C: US label = native date, unshifted         (naive calendar)
  - Re-runs Granger causality (BIC lag over 1-10, ssr F-test + HAC) for all
    54 directional tests touching AMKR or INTC, under each alignment.
  - Reports how many of the 54 tests are significant under each alignment,
    split by direction group.

Input:  data/raw/raw_adjclose.csv (through 2026-09-10)
Output: data/results/placebo/placebo_alignment_results_long.csv
        data/results/placebo/placebo_pvalue_by_alignment.csv
        data/results/placebo/placebo_Fstat_by_alignment.csv
        data/results/placebo/placebo_hacp_by_alignment.csv
        data/results/placebo/placebo_summary_counts.csv
"""
import os
import warnings
import numpy as np
import pandas as pd
from statsmodels.tsa.stattools import grangercausalitytests
from statsmodels.tsa.api import VAR
from statsmodels.regression.linear_model import OLS

warnings.simplefilter("ignore")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PLACEBO = os.path.join(ROOT, "data", "results", "placebo")
os.makedirs(PLACEBO, exist_ok=True)

MAXLAG = 10
US = ["AMKR", "INTC"]
BDAY = pd.tseries.offsets.BDay(1)
ANALYSIS_END = "2026-09-10"

full = pd.read_csv(os.path.join(RAW, "raw_adjclose.csv"), index_col=0, parse_dates=True).sort_index()
full.index = pd.DatetimeIndex(full.index).normalize()

us_early = pd.read_csv(os.path.join(RAW, "us_early_history.csv"), index_col=0, parse_dates=True).sort_index()
us_early.index = pd.DatetimeIndex(us_early.index).normalize()
full = full.reindex(full.index.union(us_early.index)).sort_index()
for c in US:
    full[c] = us_early[c].combine_first(full[c])

full = full.loc[:ANALYSIS_END]
NON_US = [c for c in full.columns if c not in US and c != "6967.T"]

non_us_ret = {c: np.log(full[c].dropna() / full[c].dropna().shift(1)).dropna() for c in NON_US}
us_ret_native = {c: np.log(full[c].dropna() / full[c].dropna().shift(1)).dropna() for c in US}

ALIGNMENTS = {
    "A_plus1bday (headline)": 1,
    "B_minus1bday (reverse placebo)": -1,
    "C_noshift (naive calendar)": 0,
}


def build_panel(shift_n):
    cols = dict(non_us_ret)
    for c in US:
        r = us_ret_native[c].copy()
        if shift_n != 0:
            r.index = r.index + shift_n * BDAY
        cols[c] = r[~r.index.duplicated(keep="last")]
    allc = pd.DataFrame(cols)
    idx = allc.dropna(how="any").index
    return allc.reindex(idx), idx


def granger_row(df, effect, cause, L):
    data = df[[effect, cause]].dropna().values
    gc = grangercausalitytests(data, maxlag=[L], verbose=False)[L][0]
    F, pF, dfd, dfn = gc["ssr_ftest"]
    X = pd.DataFrame(index=df.index)
    X["const"] = 1.0
    cause_cols = []
    for k in range(1, L + 1):
        X[f"e_l{k}"] = df[effect].shift(k)
    for k in range(1, L + 1):
        nm = f"c_l{k}"
        X[nm] = df[cause].shift(k)
        cause_cols.append(nm)
    d = pd.concat([df[effect].rename("y"), X], axis=1).dropna()
    nwlags = int(np.floor(4 * (len(d) / 100) ** (2 / 9)))
    res = OLS(d["y"].values, d.drop(columns="y").values).fit(
        cov_type="HAC", cov_kwds={"maxlags": max(nwlags, 1), "use_correction": True})
    cols = list(d.drop(columns="y").columns)
    idxs = [cols.index(c) for c in cause_cols]
    R = np.zeros((len(idxs), len(cols)))
    for i, j in enumerate(idxs):
        R[i, j] = 1.0
    ft = res.f_test(R)
    return F, pF, float(np.squeeze(ft.fvalue)), float(ft.pvalue)


pairs = [(a, "AMKR") for a in NON_US] + [(a, "INTC") for a in NON_US] + [("AMKR", "INTC")]

all_rows = []
for label, shift_n in ALIGNMENTS.items():
    panel, idx = build_panel(shift_n)
    print(f"alignment {label}: n={len(idx)}  {idx.min().date()} -> {idx.max().date()}")
    for a, b in pairs:
        so = VAR(panel[[a, b]].values).select_order(maxlags=MAXLAG)
        bic_arr = np.asarray(so.ics["bic"])
        lag = int(np.argmin(bic_arr[1:]) + 1)
        for effect, cause in [(b, a), (a, b)]:
            F, pF, hacF, hacP = granger_row(panel, effect, cause, lag)
            all_rows.append(dict(alignment=label, cause=cause, effect=effect, n=len(idx), lag=lag,
                                  F=F, p=pF, hac_F=hacF, hac_p=hacP))

res = pd.DataFrame(all_rows)
res.to_csv(os.path.join(PLACEBO, "placebo_alignment_results_long.csv"), index=False)

order = list(ALIGNMENTS.keys())
piv_p = res.pivot(index=["cause", "effect"], columns="alignment", values="p")[order]
piv_F = res.pivot(index=["cause", "effect"], columns="alignment", values="F")[order]
piv_hp = res.pivot(index=["cause", "effect"], columns="alignment", values="hac_p")[order]
piv_p.to_csv(os.path.join(PLACEBO, "placebo_pvalue_by_alignment.csv"))
piv_F.to_csv(os.path.join(PLACEBO, "placebo_Fstat_by_alignment.csv"))
piv_hp.to_csv(os.path.join(PLACEBO, "placebo_hacp_by_alignment.csv"))

res["sig"] = res.p < 0.05
res["hac_sig"] = res.hac_p < 0.05
asian_to_us = res[res.effect.isin(US) & ~res.cause.isin(US)]
us_to_asian = res[res.cause.isin(US) & ~res.effect.isin(US)]
amkr_intc = res[(res.cause.isin(US)) & (res.effect.isin(US))]

summary_rows = []
for name, g in [("Asian -> AMKR/INTC", asian_to_us), ("AMKR/INTC -> Asian", us_to_asian), ("AMKR<->INTC", amkr_intc)]:
    t = g.groupby("alignment")[["sig", "hac_sig"]].sum().reindex(order)
    t["n_tests"] = g.groupby("alignment").size().reindex(order)
    t.insert(0, "direction_group", name)
    summary_rows.append(t.reset_index())
summary = pd.concat(summary_rows, ignore_index=True)
summary.to_csv(os.path.join(PLACEBO, "placebo_summary_counts.csv"), index=False)

print("\nsummary:")
print(summary.to_string(index=False))
